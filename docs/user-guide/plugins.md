# Plugins

Plugins are Firefox extension packages stored in the admin library and
selected when creating a campaign.

## Library operations

The dashboard supports creating, editing, importing, exporting, and deleting
plugins. A plugin contains:

- a name and description;
- at most 128 files;
- validated relative file names;
- text content for each file.

At minimum, a usable extension normally includes `manifest.json` and the
scripts or assets referenced by that manifest.

## Review checklist

Before enabling a plugin:

- inspect every file;
- request only necessary Firefox permissions;
- use campaign-local communication paths;
- avoid hard-coded credentials, public tokens, and unrelated remote hosts;
- validate all externally supplied data;
- confirm that cleanup occurs when the session ends.

Plugins execute inside assessment browser containers and must be treated as
trusted active code. Use only plugins reviewed for the current engagement.

## Built-in runtime extensions

P-BitM also packages a small set of built-in Firefox extensions into each
session container. Their source remains in
`bitm-images/common/firefox/bad_firefox_extensions` so deployment maintainers
can review and adapt them. They are separate from plugins imported through the
dashboard.

See the [plugin format reference](../reference/plugin-format.md).
