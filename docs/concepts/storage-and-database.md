# Storage and database

P-BitM uses SQLite and filesystem storage rooted at the configured `storage/`
directory.

## Ownership

On rootful Linux, P-BitM selects a positive host UID/GID and builds every
unprivileged process that writes shared storage with those numeric IDs. A
normal launch follows the current user, a `sudo` launch follows the original
user, and a direct root launch still selects a non-root container identity.
Linux checks numeric IDs rather than account names, so the containers can keep
their internal names (`bitm` or `abc`) without requiring a host account with
the same name.

The host `storage/` directory remains a bind mount so operators can inspect,
back up, and manage files directly. The admin backend receives the full tree;
each campaign and victim container receives only its own scoped subdirectory
at `/storage`. Top-level storage and campaign directories use mode `0700`, so
unrelated host users cannot traverse engagement data.

The admin backend owns the primary database, transactions, and stored
artifacts. Campaign services send authenticated events to it instead of
writing through a separate public database interface.

## Layout

The default host layout includes:

```text
storage/
├── p-bitm.db
├── logs/
└── campaigns/
```

Runtime paths inside containers use `/storage`; `HOST_STORAGE_PATH` identifies
the same location from Docker host operations.

## Consistency

Campaign and participant creation is committed atomically. File metadata and
filesystem writes use bounded validation and cleanup paths to avoid leaving a
successful database record for a failed artifact write.

## Retention

Container restarts do not erase storage. P-BitM does not assume an automatic
retention period; operators must implement the engagement's backup and
deletion policy.
