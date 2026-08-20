# Doctor

`doctor` is the read-only deployment and release preflight command. It does not
create directories, change permissions, generate secrets, build images, start
containers, or modify the database.

## Usage

```bash
python3 p-bitm.py doctor
python3 p-bitm.py doctor --strict
python3 p-bitm.py doctor --strict --format json
```

The default command fails on `FAIL`. Strict mode also treats `WARN` as
blocking. JSON mode is suitable for release evidence and omits the CLI banner.

## Checks

Doctor validates:

- configuration structure and version consistency;
- generated environment values and permissions;
- DNS secret files and generated Traefik configuration;
- storage paths, ownership/accessibility, and disk capacity;
- SQLite integrity;
- certificate validity, key matching, and permissions;
- Python, Docker Engine 23.0+, Docker Buildx, BuildKit configuration, the
  Docker Compose plugin, Git, and OpenSSL;
- Compose rendering and network boundaries;
- required images and non-blocking source-versus-image timestamp drift;
- generated or sensitive paths accidentally tracked by Git.

## Remediation

Doctor reports state; setup reconciles generated runtime state:

```bash
python3 p-bitm.py setup
python3 p-bitm.py doctor
```

Source timestamp drift is informational because BuildKit may safely reuse
content-addressed layers whose creation timestamp predates the host file
mtime. When source content has changed, rebuild explicitly:

```bash
python3 p-bitm.py up --build
```
