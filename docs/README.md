# Persistent Browser-In-The-Middle

P-BitM is a containerized platform for controlled browser-in-the-middle
security assessments. It provides an administrative dashboard, campaign
orchestration, isolated browser sessions, event collection, and live session
viewing.

{% hint style="danger" %}
Use P-BitM only in environments you own or where you have explicit written
authorization. You are responsible for complying with applicable law, the
assessment scope, data-handling requirements, and retention rules.
{% endhint %}

## Start here

- [Understand the platform](getting-started/overview.md)
- [Check the requirements](getting-started/requirements.md)
- [Install P-BitM](getting-started/installation.md)
- [Complete the quick start](getting-started/quick-start.md)

## Documentation map

The **User guide** covers dashboard workflows. **Concepts** explains system
boundaries and runtime behavior. **Administration** covers deployment,
maintenance, and troubleshooting. **Development** is for contributors, while
**Reference** records stable CLI and configuration contracts.

## Release status

This documentation describes the actively developed P-BitM `0.1.0` codebase.
Interfaces, configuration, deployment procedures, and stored data formats may
change before the first stable release. Internal HTTP endpoints are not a
public compatibility contract; use the dashboard and CLI unless a page
explicitly documents another supported interface.

P-BitM's original code is distributed under the GNU General Public License
version 3 only (`GPL-3.0-only`). The canonical license text is the `LICENSE`
file at the repository root. Third-party components retain their own licenses;
see the repository's `THIRD_PARTY_NOTICES.md` and the
[credits and acknowledgements](CREDITS.md).
