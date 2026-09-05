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
  Generic search links were addressed in batch two below.
- **Date scans:** apply airline/time/price/duration post-filters to decoded rows;
  preserve exclusions and alliances when splitting long date ranges.

PRs #160, #215, and #103 were merged with history retained. The dependency floor
and additional integration fixes are GLFI changes, not merges of PRs #193/#194/#210.
The earlier baseline already incorporated #230, #231, and #232.

## Remaining Before A Release Decision

The remaining work is roughly two batches: search reliability/Explore evaluation,
then release hardening. Provider-blocked features and TypeScript parity are not
automatically part of the first release.

- Explore search (#226), subject to fresh live transport verification.
- Remaining amenities mapping (#217) and provider error/empty-result distinctions.
- Round-trip completeness: only five outbound candidates are expanded by default (#142).
- Unsupported baggage/emissions/basic-economy options still warn rather than enforce.
- Multi-city, booking-price RPC, and reseller lookup remain provider limitations.
- TypeScript public-page search transport is not ported; npm publishing stays disabled.
- ICAO input, Homebrew distribution, and container verification are outstanding.
- Review the remaining dependency/security surface before deployment; one patched
  dependency is not a complete security audit. HTTP still requires an authenticated
  gateway before public exposure.

## Completed In The Second Batch

- **#196 equivalent:** independent return-time controls in flights/dates CLI and
  all three relevant MCP tools. Missing return dates/round-trip mode are rejected.
  Default behavior still inherits the outbound window.
- **#195 equivalent:** inclusive min/max stay ranges, shared validation, merged
  date-pair results sorted by price, and a 366 date/stay-combination limit. Both
  bounds are required; fixed and ranged durations cannot be combined. The shared
  transport rate limiter applies; no duplicated CLI/MCP search loops.
- **#199 equivalent:** multi-airport CLI inputs for flights and dates, with the
  same strict parser as MCP. All airports survive in search links, rather than
  silently keeping only the first origin/destination.
- **Generic links:** search and date links use `tfs` encoding to preserve party,
  cabin, dates, and airport sets. They do not claim to preserve client-only filters.
- **Date transport:** return-time-constrained dates expand actual return options
  from the five cheapest outbound candidates and quote complete itinerary prices.
  This fixes enforcement of the new control but does not resolve #142 completeness.
- **Selected fares:** CLI text/JSON and MCP now show the selected return's complete
  quote rather than the outbound starting fare. Cheapest ordering uses final fares;
  unknown final fares are not replaced with a misleading starting price.
- **Concurrency:** nested date/return searches run inline within shared-pool
  workers, preventing pool-exhaustion deadlocks. A subprocess regression test
  verifies nested success, error propagation, and worker reuse.

These are GLFI adaptations of proposals #195/#196/#199, not merges of their PR
heads. The upstream return-time sentinel design is retained with attribution in
NOTICE; duration execution is adapted to the current public-page transport.

## Verification

Second-batch checks on 2026-09-05: all 873 offline Python tests passed on 3.10,
3.11, and 3.13. Ruff lint/formatting, wheel/sdist builds, and Twine checks passed.
Live JAX to JFK/LGA (2026-10-15 outbound, 2026-10-19 return) returned four
itineraries, all with morning outbound/evening return departures and sorted
selected fares. A 3-4 day flexible stay search returned both date pairs. The
rebuilt installed MCP wheel passed a live flexible search, encoded-link checks,
HTTP health, and tool-schema checks under FastMCP 4.0.3. No servers left running.
TypeScript was unchanged in batch two; its previous 322-test result is below.

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
