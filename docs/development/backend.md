# Admin backend

The admin backend is the trusted control plane. It owns:

- administrator authentication and authorization;
- reusable campaign resources;
- campaign and participant state;
- primary database transactions;
- stored artifacts and exports;
- Docker runtime orchestration.

## Boundaries

Route or service entry points own transactions. Lower-level helpers may mutate
or flush records but must not commit unless their contract explicitly owns the
whole operation.

Campaign creation persists the campaign and participants atomically. If
persistence fails after runtime provisioning, the transaction is rolled back
and the new runtime is removed.

The backend connects to Docker through `docker-proxy`, not a direct writable
socket mount. Every workload operation must validate application labels and
resource ownership.

## Request models

Create and update schemas use strict Pydantic models with unknown fields
forbidden. Do not send response-only properties such as IDs, timestamps, or
usage counters back in mutation payloads.
