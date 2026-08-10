# Database

P-BitM uses SQLAlchemy with SQLite as the default persistence layer.

## Timestamps

- Persist timestamps through `UTCDateTime`.
- Accept timezone-aware values and compare in UTC.
- Serialize timestamps as ISO 8601 at API boundaries.
- Use `utc_now` as a callable column default.

SQLite stores UTC timestamps without an offset internally; `UTCDateTime`
restores UTC awareness when values are read.

## Structured values

Use SQLAlchemy `JSON` columns for structured objects and arrays. Assign Python
`dict` and `list` values directly and validate size and shape in request
models. Do not manually encode JSON before persistence.

## Identifiers

Public identifiers remain strings because they are also used in routes,
container names, labels, network names, and tracking contracts.

## Migrations

`Base.metadata.create_all` creates new databases but does not upgrade released
schemas. Put in-place changes in ordered, idempotent, tested migrations in
`schema_migrations.py`.
