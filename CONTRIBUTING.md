# Contributing to P-BitM

Thank you for helping improve P-BitM. Contributions should preserve the
project's focus on controlled, authorized security assessments and should be
small enough to review and test safely.

## Authorized use

Do not submit examples, fixtures, screenshots, logs, or documentation produced
from systems you did not have explicit permission to test. Never include real
credentials, browser profiles, session material, tracking identifiers,
collected data, or personal information.

## Before starting

- Search existing issues and pull requests before proposing substantial work.
- Discuss architectural changes before implementing them.
- Keep unrelated refactors out of focused fixes.
- Do not commit generated runtime state, certificates, secrets, storage, build
  output, or dependency directories.

## Development setup

Follow the [development setup guide](docs/development/setup.md). Run the tests
relevant to the area you changed. The main verification commands are:

```bash
python3 -m pytest tests
PYTHONPATH=server/backend python3 -m pytest server/backend/tests
PYTHONPATH=server/backend-phishing/app python3 -m pytest server/backend-phishing/tests
```

For frontend changes:

```bash
cd server/frontend
npm ci
npm run lint
npm test
npm run build
```

Documentation-only changes should at minimum pass:

```bash
git diff --check
```

If a test cannot be run, state that clearly in the pull request.

## Code and documentation

- Follow the style and structure of the surrounding code.
- Add or update tests when behavior changes.
- Keep security boundaries and authorization checks explicit.
- Avoid logging credentials, tokens, cookies, collected content, or other
  sensitive values.
- Keep public documentation in English.
- Update the documentation when changing supported configuration, CLI
  behavior, deployment requirements, or user-visible workflows.

## Licensing and third-party material

P-BitM's original code is licensed under the GNU General Public License
version 3 only (`GPL-3.0-only`). By submitting a contribution, you confirm that
you have the right to provide it and agree that it will be distributed under
that license.

Do not submit code, text, images, configuration, or other material copied from
a project with no license or with terms incompatible with P-BitM. When a
contribution incorporates, modifies, or is materially based on another
project:

1. identify the upstream project and canonical URL;
2. state whether the material was copied, modified, or used only as design
   inspiration;
3. preserve upstream copyright and license notices;
4. document the affected files;
5. update [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) when third-party
   material is distributed with P-BitM;
6. update the
   [credits and acknowledgements](docs/CREDITS.md) when the project
   materially influenced the implementation.

Package-manager dependencies do not normally need a credits entry, but
their licenses must still be compatible with the way P-BitM uses and
distributes them.

## Reporting vulnerabilities

Do not open a public issue or pull request containing an undisclosed
vulnerability. Follow [`SECURITY.md`](SECURITY.md) and send in-scope reports
to the private contact listed there.

## Pull requests

Describe:

- the problem and intended outcome;
- the important implementation choices;
- the tests or checks performed;
- any migration, deployment, security, licensing, or compatibility impact.

Keep commits reviewable and do not rewrite unrelated files merely to change
formatting.
