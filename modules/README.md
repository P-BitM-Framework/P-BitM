# Modules

This directory contains JSON module definitions loaded by the backend seed
process. Treat every module as active code and review it against the written
assessment scope before use.

Canonical documentation:

- [Module user guide](../docs/user-guide/modules.md)
- [Module format reference](../docs/reference/module-format.md)

Files beginning with `_` are templates. Invalid definitions are skipped and
logged. Existing database records are not overwritten during reseeding.
