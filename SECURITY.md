# GFLI Security Notes

GFLI is pre-release and has no public service deployment. Do not interpret passing
tests or an empty advisory scan as a comprehensive security certification.

## Review On 2026-09-05

- The initial locked CLI/MCP audit reported 51 advisory matches across 13 runtime
  packages. A subsequent development-tool audit identified 30 matches across five
  additional packages. Counts include duplicate advisory records, not necessarily
  distinct vulnerabilities or exploitable GFLI paths.
- Updated affected packages and necessary dependency constraints, including Click,
  MCP SDK, Starlette/FastAPI, Authlib, cryptography, requests/urllib3, multipart,
  dotenv, and documentation/test tooling. No advisories were suppressed.
- The resulting full runtime/development export passed pip-audit 2.10.1 on Python
  3.10 and 3.13 on the development host with no known advisory matches. Audits query
  the current PyPI advisory service; results can change. CI repeats them on Linux.
- The independently resolved installed MCP environment also had no known advisory
  matches across its 81 registry dependencies. The unpublished `gfli` package itself
  was skipped by the registry scanner and remains subject to source review/tests.
- [pip-audit](https://github.com/pypa/pip-audit) reports known dependency advisories.
  It does not establish reachability, detect every malicious package, audit native
  system libraries, or prove absence of unknown vulnerabilities.

Run `make audit` to check the fully pinned, hashed lock export without running a
dependency resolver in the scanner. Registry installations resolve independently
of `uv.lock`; `make verify-install` separately exercises newly resolved installs.

## Deployment Boundary

- Prefer stdio for local AI clients. HTTP has no built-in authentication and must
  not be publicly exposed. Loopback is the default; a gateway with authentication,
  access controls, and request limits is required before remote hosting.
- Google requests use fixed Google endpoints, TLS verification, a shared rate
  limiter, finite request timeouts, and bounded retries. A date scan may make many
  requests; its combination limit is not a total request/deadline budget. No
  multi-user abuse protection or service-wide admission control is provided.
- CLI diagnostic logs may contain travel details, arguments, and provider errors.
  New logs are owner-only files. Existing historical logs are not retroactively
  chmodded or deleted; inspect them before sharing. No environment dump is logged.
- Containers are non-root; Compose is loopback-only with a read-only root filesystem
  and dropped capabilities. Docker execution and OS-image scanning still require a
  Docker-equipped host. The local host has no container runtime.
- Publication requires explicit approval, passing CI/install/audit/container checks,
  a matching GFLI tag, and a protected trusted-publisher environment. See RELEASING.md.

## Reporting

Do not put secrets or exploit-sensitive data in public issues. GitHub private
vulnerability reporting is enabled for this repository: [report a vulnerability
privately](https://github.com/davefmurray/gfli/security/advisories/new).
No response-time commitment is established yet.
