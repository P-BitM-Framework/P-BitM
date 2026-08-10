# Initial configuration

P-BitM separates operator configuration from generated runtime state.

## `config.yaml`

This is the human-managed source for deployment mode, paths, image build
definitions, DNS challenge settings, session limits, cleanup policy, and CLI
behavior.

## `server/.env`

This generated and ignored file contains runtime paths, the initial
administrator bootstrap values, and application secrets. Manage it through:

```bash
python3 p-bitm.py setup
```

Do not copy values from `.env.example` into production unchanged. Runtime
validation requires:

- an administrator password of at least 16 characters;
- an internal API key of at least 32 characters;
- a data-encryption key of at least 32 characters;
- values that do not contain known placeholder markers.

## Seed data

The supplied Compose configurations set `SEED_DATA=true`. Keep this default
unless the application behavior is intentionally changed and tested.

## Development mode

Set `app.environment: development` in `config.yaml` before running setup. The
CLI then selects `server/docker-compose-dev.yml`, which includes MailHog on
ports `1025` and `8025`.

## Detailed references

- [Configuration reference](../reference/configuration.md)
- [Environment variables](../administration/environment-variables.md)
- [Networking and TLS](../administration/networking-and-tls.md)
