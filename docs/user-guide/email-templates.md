# Email templates

Email templates store the subject, HTML body, optional text body, attachments,
category, tags, and declared variables used by complete campaigns.

## Authoring

Create a template in **Email Templates**, then preview both the content and the
resolved campaign link before use. Keep a plain-text alternative when the
exercise requires broad mail-client compatibility.

Template content is size-limited and validated by the backend. Response-only
fields such as IDs, counters, and timestamps are not accepted in create or
update payloads.

## Template variables

`{{first_name}}`, `{{last_name}}`, `{{email}}`, and `{{position}}` are
resolved per target. `{{company}}` is resolved from the target list's own
company field (set on the list, not per target), since a list represents a
single engagement. `{{tracking_url}}` and `{{tracking_pixel}}` are generated
per recipient at send time.

## Operational guidance

- Use only approved branding and wording.
- Avoid embedding real secrets or personal data.
- Confirm that links resolve to the intended campaign hostname.
- Test rendering with designated internal recipients before launch.
- Duplicate a template when you need an independently editable variant.
