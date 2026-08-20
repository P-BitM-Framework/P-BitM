# Storage and database

P-BitM uses SQLite and filesystem storage rooted at the configured `storage/`
directory.

## Ownership

The current host user that owns the repository directory and every
unprivileged container process that writes shared storage use the same numeric
UID/GID, `1000:1000`, on rootful Linux. Linux checks those numbers rather than
the account names (`bitm` or `abc`). The top-level storage and campaign
directories use mode `0700`, so unrelated host users cannot traverse
engagement data.

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
