# Campaigns

A campaign binds reusable content, delivery settings, routing, and browser
session options into one controlled assessment.

## Before creating a campaign

Prepare the target list, landing page, and—unless the campaign is
standalone—the email template and SMTP profile. Plugins and modules are
optional.

## Wizard

The campaign wizard has four stages:

1. **Setup** — name, description, campaign type, and production hostname.
2. **Content** — SMTP profile, email template, landing page, plugins, and
   modules.
3. **Launch** — target list, target URL, schedule, tracking parameter, protocol,
   and streaming options.
4. **Review** — final confirmation.

Target URLs must be complete HTTP or HTTPS URLs. Production campaigns also
require a hostname without a scheme, port, path, query, or fragment.

## Campaign types

- **Complete** campaigns use the selected delivery resources and can launch
  immediately or on a schedule.
- **Standalone** campaigns launch immediately and do not require an SMTP
  profile or email template.

A scheduled campaign requires both a timezone-aware start and end time. The
start must be in the future and the end must follow the start.

## Runtime controls

Campaign states include `draft`, `scheduled`, `active`, `paused`, `completed`,
and `error`. Pause stops active runtime workloads; resume recreates the
required runtime. Stop completes the campaign and removes its runtime.

Use the dashboard for routine lifecycle management. CLI equivalents are listed
in the [CLI reference](../reference/cli.md).
