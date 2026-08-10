# Plugin format

A plugin is a library record containing metadata and UTF-8 text files.

## Editable representation

```json
{
  "name": "Approved extension",
  "description": "Purpose and review record.",
  "files": [
    {
      "name": "manifest.json",
      "content": "{\"manifest_version\": 2, \"name\": \"Approved extension\", \"version\": \"1.0\"}"
    }
  ]
}
```

File names are canonical relative POSIX paths. Absolute paths, backslashes,
empty segments, `.`/`..`, control characters, duplicate paths, symlinks, and
non-UTF-8 content are rejected.

## Limits

- 128 plugin files;
- 2 MiB per file;
- 10 MiB total uncompressed file content;
- 240 characters per relative path;
- 128 characters per path segment.

## ZIP import/export

The archive layout is:

```text
plugin.json
files/
├── manifest.json
└── ...
```

Imports accept at most 10 MiB of archive data and 512 ZIP members. Encrypted
entries and symlinks are rejected. `plugin.json` contains the plugin name and
description; extension files live below `files/`.

Review Firefox permissions and every script before assigning an imported
plugin to a campaign.
