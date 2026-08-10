# Module format

Seed modules are JSON files in `modules/`. The backend also exposes equivalent
fields in the authenticated module editor.

```json
{
  "name": "Assessment notice",
  "description": "Displays an approved test notice.",
  "category": "Awareness",
  "icon": null,
  "inputs": [
    {
      "id": 0,
      "label": "Message",
      "type": "string",
      "required": true
    }
  ],
  "payload": "<div class=\"notice\">{{ params[0] }}</div>",
  "link": null
}
```

## Fields

| Field | Constraints |
|---|---|
| `name` | Required, 1–120 characters |
| `description` | Optional, at most 4,000 characters |
| `category` | Required, 1–80 characters |
| `icon` | Optional, at most 1 MiB of text |
| `inputs` | At most 64 strict input objects |
| `payload` | Required, 1 byte–1 MiB |
| `link` | Optional, at most 2,048 characters |

Each input requires an integer `id` from 0 through 10,000, a label, a type
string, and a boolean `required`.

## Runtime placeholders

The runtime resolves declared input placeholders such as
`{{ params[0] }}` and campaign-owned identifiers. Treat all parameter values
as untrusted input and keep payload behavior within the approved assessment
scope.

Files beginning with `_` are templates and are not intended as production
modules. Seed data remains enabled by default in the supplied Compose files.
