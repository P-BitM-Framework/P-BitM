# Collected data

The victim dashboard organizes approved assessment telemetry by participant.
Available panels can include:

- event timeline and connection metadata;
- submitted form records;
- keylog segments;
- captured files;
- manually requested screenshots;
- plugin and module results.

Empty records are not intended to appear as copyable keylog blocks. Session
and timestamp markers provide context, while only actual key content is
copyable.

## Handling requirements

Collected data may contain highly sensitive information. Limit access to
assigned operators, export only when required, store exports securely, and
delete both live data and copies according to the engagement agreement.

The administrative UI retrieves stored records through authenticated backend
requests. Internal collection endpoints are not public integration APIs.
