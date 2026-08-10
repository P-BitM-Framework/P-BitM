# Security Policy

## Supported versions

Security fixes are applied to the latest version in the default branch.

## Out of scope

- issues confined to the intended privileges, data, and current session of an
  already authorized administrative user, without crossing an authorization
  or campaign boundary;
- self-XSS that requires an authorized user to paste or execute untrusted code
  in their own browser;
- cosmetic, wording, or general usability defects without a security impact.

Reports outside this scope may be considered as maintenance feedback, but
there is no commitment that they will be accepted, assigned, or patched.

## Reporting a vulnerability

Do not open a public issue, discussion, or pull request for a suspected
vulnerability. Report it by email to
[GiacoLenzo2109@proton.me](mailto:GiacoLenzo2109@proton.me) and include:

- the affected component and version;
- the conditions required to reproduce the issue;
- a minimal proof of concept using non-sensitive test data;
- the expected security impact;
- any suggested mitigation.

Do not include real credentials, captured data, production targets, tracking
identifiers, browser profiles, or personal information. Submission of a report
does not guarantee acceptance, a response, or a patch.

## Deployment scope

P-BitM is intended for authorized security testing in isolated environments.
Operators are responsible for obtaining permission, protecting collected data,
and complying with applicable laws and policies.
