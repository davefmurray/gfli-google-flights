# GLFI Pre-Launch Work

Local development only. No GitHub push, registry publication, or public deployment.

## Completed In The First Batch

- **#131 / PR #160:** regenerated airport and airline enums after fixing duplicate
  names. Every shipped code has its own identity; TRI no longer resolves to PSC.
- **PR #193 equivalent:** require `curl-cffi>=0.15.0`; lock now resolves 0.16.3.
  Addresses the dependency range in [GHSA-qw2m-4pqf-rmpp](https://github.com/advisories/GHSA-qw2m-4pqf-rmpp).
- **#127, name only:** W4 now identifies Wizz Air Malta in Python and TypeScript.
  Source: [Israel Airports Authority](https://www.iaa.gov.il/en/companies/airline-companies/wizz-air-malta/).
  The separate W4 price/currency report is not declared resolved.
- **PR #215:** UTC-tolerant same-day validation, reject backwards return dates,
  and preserve specific Pydantic messages in MCP errors. The date transport now
  uses the same date allowance instead of skipping valid west-of-UTC dates.
- **PR #103:** adult/child/infant controls in flights/dates CLI and MCP. Added
  `--adults` and `-p` aliases. Booking MCP also accepts the same family fields.
- **Booking links:** per-itinerary flight links preserve passenger mix and cabin.
  Generic search links, including date-result links, still lack cabin/party fidelity.
- **Date scans:** apply airline/time/price/duration post-filters to decoded rows;
  preserve exclusions and alliances when splitting long date ranges.

PRs #160, #215, and #103 were merged with history retained. The dependency floor
and additional integration fixes are GLFI changes, not merges of PRs #193/#194/#210.
The earlier baseline already incorporated #230, #231, and #232.

## Remaining Before A Release Decision

- Separate return-flight time control (#196).
- Flexible trip-duration range (#195).
- Multi-airport CLI input (#199).
- Explore search (#226), subject to fresh live transport verification.
- Remaining amenities mapping (#217) and provider error/empty-result distinctions.
- Round-trip completeness: only five outbound candidates are expanded by default (#142).
- Unsupported baggage/emissions/basic-economy options still warn rather than enforce.
- Multi-city, booking-price RPC, and reseller lookup remain provider limitations.
- TypeScript public-page search transport is not ported; npm publishing stays disabled.
- ICAO input, Homebrew distribution, and container verification are outstanding.
- Generic search links need cabin and passenger fidelity.
- Review the remaining dependency/security surface before deployment; one patched
  dependency is not a complete security audit. HTTP still requires an authenticated
  gateway before public exposure.

## Verification

First-batch checks on 2026-09-05: 821 Python tests passed (3.11 full suite;
3.10/3.13 full 818-test suite plus the three final validation tests). TypeScript
passed 322 tests, lint/typechecking, and build. Ruff checks and Python wheel/sdist
builds passed; both distributions passed Twine checks. Live JAX-JFK searches for
2026-10-15 with two adults and one child returned results; a two-day Delta-only
afternoon date scan also returned results. Docker remains unverified.

Run `make test-offline`, `make lint`, `uv build`, and `uv run twine check dist/*`.
TypeScript: `bun run ci` and `bun run build` from `fli-js/`.
Use short, future-date live CLI/MCP searches separately. Do not treat passing
fixture tests as evidence that blocked Google endpoints have recovered.
