# Storage and backups

## Persistent data

The host `storage/` directory contains the SQLite database, logs, campaign
artifacts, screenshots, uploaded files, and browser-profile exports. It is
mounted into the admin backend at `/storage`.

## Consistent backup

1. Stop or pause active campaigns.
2. Stop the base stack with `python3 p-bitm.py down`.
3. Copy the complete `storage/` directory to an approved encrypted location.
4. Record the application version and backup checksum.
5. Restart with `python3 p-bitm.py up`.

Copying only `p-bitm.db` can omit artifacts referenced by database rows.

## Restore

Restore the database and campaign directories as one set while the stack is
stopped. Preserve directory accessibility for the host operator and container
UID used by the backend. Run `doctor` before starting.

## Capacity

```bash
du -sh storage
df -h storage
```

Exports and screenshots can grow independently of the database. Monitor both
free disk space and the engagement retention deadline.

## Deletion

Use dashboard lifecycle controls and approved retention procedures. Do not use
unreviewed recursive shell commands against the repository or storage root.
