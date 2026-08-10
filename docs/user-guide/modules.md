# Modules

Modules are operator-triggered HTML and JavaScript payload definitions. They
are stored in the module library and may be assigned to campaigns.

## Library operations

Each module defines a name, description, category, optional icon and link,
input descriptors, and a payload. The backend validates size and shape before
persistence.

Module inputs are resolved when an authorized operator executes the module for
a selected active session. The backend wraps visual content in a managed
overlay and supplies cleanup behavior.

## Safety

Modules are active code. Review them for:

- engagement scope and expected user-visible behavior;
- safe parameter handling;
- bounded output;
- campaign-local data submission;
- reliable cleanup;
- absence of hard-coded secrets or unrelated external endpoints.

Do not use library examples as authorization to execute a module. Scope and
operator approval remain external requirements.

See the [module format reference](../reference/module-format.md).
