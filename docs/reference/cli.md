# CLI reference

Run commands from the repository root with the project environment activated:

```bash
python3 p-bitm.py COMMAND
```

## Global options

| Option | Purpose |
|---|---|
| `--version` | Print the CLI version |
| `--debug` | Include a traceback for unexpected errors |
| `--install-completion` | Display/install bash or zsh completion guidance |

## Deployment

| Command | Purpose |
|---|---|
| `setup` | Provision or reconcile runtime files |
| `setup --rotate-dns-secrets` | Replace configured DNS credentials |
| `up` | Build missing images and start services |
| `up --build` | Force all configured image rebuilds |
| `down` | Stop the selected Compose stack |
| `down --volumes` | Also request Compose volume removal |
| `status [--format table\|json]` | Show service and image status |
| `doctor [--strict] [--format table\|json]` | Run read-only diagnostics |
| `cleanup [--campaigns]` | Remove app-owned participant workloads; optionally campaigns |
| `reset` | Stop workloads and remove configured application images |

## Campaigns

```text
campaign list [--format table|json]
campaign <id> status [--format table|json]
campaign <id> start
campaign <id> stop
campaign <id> logs [--follow|-f] [--tail N]
campaign <id> remove [--force]
campaign <id> dump [--output PATH|-o PATH]
```

Campaign dump output is JSON. CSV is not implemented.

## Participant sessions

```text
campaign <campaign-id> victim list [--format table|json]
campaign <campaign-id> victim <victim-id> status [--format table|json]
campaign <campaign-id> victim <victim-id> start
campaign <campaign-id> victim <victim-id> stop
campaign <campaign-id> victim <victim-id> logs [--follow|-f] [--tail N]
```

## Administration

```text
admin config [--edit]
admin reset-password [--username USERNAME]
admin users [--format table|json]
admin users create USERNAME --email ADDRESS [--role admin|operator]
admin users set-role USERNAME --role admin|operator
admin users enable USERNAME
admin users disable USERNAME
admin users delete USERNAME [--force]
```

Password entry is interactive and is not accepted as a command-line argument.
