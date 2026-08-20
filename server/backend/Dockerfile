FROM python:3.11-slim

ARG PBITM_UID=1000
ARG PBITM_GID=1000

LABEL org.pbitm.runtime.uid="${PBITM_UID}" \
      org.pbitm.runtime.gid="${PBITM_GID}"

WORKDIR /app

RUN case "${PBITM_UID}" in ''|*[!0-9]*) exit 1 ;; esac \
    && case "${PBITM_GID}" in ''|*[!0-9]*) exit 1 ;; esac \
    && test "${PBITM_UID}" -gt 0 \
    && test "${PBITM_GID}" -gt 0 \
    && groupadd --non-unique --gid "${PBITM_GID}" bitm \
    && useradd --non-unique --uid "${PBITM_UID}" --gid bitm \
        --create-home --shell /usr/sbin/nologin bitm

# Install Python dependencies before copying the source for layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application source.
COPY --chown=bitm:bitm . .

# Install the container entry point.
COPY --chown=bitm:bitm entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

USER bitm

CMD ["/entrypoint.sh"]
