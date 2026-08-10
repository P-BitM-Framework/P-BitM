# Development setup

## Frontend toolchain

Running P-BitM through Docker does not require Node.js or npm on the host.
They are needed only for direct frontend development. The supported range is
Node.js `^22.18.0 || >=24.11.0`; no exact npm version is imposed.

CI follows the current Node.js 24 LTS line. Local development can use any
environment in the supported range.

## CLI environment

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 -m pip install pytest
```

Set `app.environment: development` in `config.yaml`, then provision and start:

```bash
python3 p-bitm.py setup
python3 p-bitm.py up --build
```

Development Compose adds MailHog:

- SMTP: `localhost:1025`
- Web UI: `http://localhost:8025`

## Repository boundaries

- `cli/` and `p-bitm.py` own local lifecycle tooling.
- `server/backend/` is the trusted admin control plane.
- `server/backend-phishing/app/` is the per-campaign service.
- `server/frontend/` is the Vue dashboard.
- `bitm-images/` contains browser runtimes.
- `modules/` contains seedable module definitions.

Do not commit generated `.env`, DNS secret files, certificates, storage, or
campaign artifacts.
