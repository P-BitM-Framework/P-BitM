# Testing

## CLI

From the repository root:

```bash
python3 -m pytest tests
```

## Admin backend

```bash
PYTHONPATH=server/backend python3 -m pytest server/backend/tests
```

## Campaign backend

```bash
PYTHONPATH=server/backend-phishing/app \
  python3 -m pytest server/backend-phishing/tests
```

## Frontend

```bash
cd server/frontend
npm ci
npm run lint
npm test
npm run build
```

Use `npm run lint:fix` to apply ESLint's safe automatic fixes, then rerun
`npm run lint` to confirm the result.

## Static and deployment checks

```bash
python3 -m compileall cli server/backend server/backend-phishing/app
python3 scripts/release_checks.py
docker compose -f server/docker-compose.yml config
docker compose -f server/docker-compose-dev.yml config
git diff --check
```

Tests must use temporary storage and must not require a running production
stack. Add regression coverage for every security or lifecycle fix.
