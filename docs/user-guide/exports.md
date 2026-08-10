# Exports

P-BitM supports campaign-level and per-session exports for authorized evidence
handling.

## Campaign export

Use the dashboard or CLI:

```bash
python3 p-bitm.py campaign <campaign-id> dump
python3 p-bitm.py campaign <campaign-id> dump --output ./campaign-export.json
```

The CLI export is JSON. CSV is not currently implemented.

## Browser-profile export

When a live browser container is available, its Firefox profile is read as a
bounded TAR stream and converted directly to a ZIP file on disk. The backend
does not hold the complete TAR, ZIP, or a Base64 representation in memory.
Archive paths and member types are validated and configured export limits are
enforced.

## Evidence handling

Exports are not automatically sanitized. Store them in an approved encrypted
location, record who created each copy, and remove them at the end of the
retention period.
