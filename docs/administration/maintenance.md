# Maintenance

## Routine checks

```bash
python3 p-bitm.py status
python3 p-bitm.py doctor
```

Review container health, disk capacity, certificate expiry, database
integrity, image freshness, and unexpected campaign workloads.

## Rebuild after updates

```bash
python3 -m pip install -r requirements.txt
python3 p-bitm.py up --build
python3 p-bitm.py doctor --strict
```

## Clean inactive workloads

Remove application-owned participant containers:

```bash
python3 p-bitm.py cleanup
```

Also remove all application-owned campaign workloads and isolated networks:

```bash
python3 p-bitm.py cleanup --campaigns
```

The second form is destructive and asks for confirmation when
`cli.confirm_destructive` is enabled.

## Reset images

`reset` stops application services, removes application-owned containers and
configured Docker images, but keeps the database and logs:

```bash
python3 p-bitm.py reset
python3 p-bitm.py up --build
```

Use it only when a full image rebuild is intended.
