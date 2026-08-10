# Storage and database

P-BitM uses SQLite and filesystem storage rooted at the configured `storage/`
directory.

## Ownership

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
