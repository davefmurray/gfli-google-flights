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

The four planned local implementation batches are complete. This is not a release
approval: repository visibility, remote CI/container verification, and registry
setup remain explicit gates. Provider-blocked features and TypeScript parity are
not automatically part of the first release.

- Explore (#226) remains deferred after the blocked live evaluation below.
- Unsupported baggage/emissions/basic-economy options still warn rather than enforce.
- Multi-city, booking-price RPC, and reseller lookup remain provider limitations.
- TypeScript public-page search transport is not ported; npm publishing stays disabled.
- ICAO input and Homebrew distribution are deferred feature/distribution work.
- Container execution remains unverified locally because Docker is unavailable.
  CI now requires its build, health, and non-root checks before publishing.
- Dependency advisory review is complete for the current lock, not a comprehensive
  security audit. Re-run the audit before release. HTTP still requires an
  authenticated gateway and abuse controls before public exposure.

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
  Batch three below removes that five-candidate cutoff.
- **Selected fares:** CLI text/JSON and MCP now show the selected return's complete
  quote rather than the outbound starting fare. Cheapest ordering uses final fares;
  unknown final fares are not replaced with a misleading starting price.
- **Concurrency:** nested date/return searches run inline within shared-pool
  workers, preventing pool-exhaustion deadlocks. A subprocess regression test
  verifies nested success, error propagation, and worker reuse.

These are GLFI adaptations of proposals #195/#196/#199, not merges of their PR
heads. The upstream return-time sentinel design is retained with attribution in
NOTICE; duration execution is adapted to the current public-page transport.

## Completed In The Third Batch

- **Provider reliability:** shared strict search-board decoding for flights and
  dates. Malformed pages and even partially undecodable boards raise typed errors.
  A failed date fails the scan rather than disappearing from apparently complete
  results. Matching flights without usable date prices raise `price_unavailable`.
  Valid empty boards still produce normal empty results.
- **CLI/MCP parity:** stable error categories distinguish timeout, connection,
  HTTP, parse, rejected-provider, unavailable-price, and unsupported-search errors.
  Booking RPC framing now rejects malformed/truncated streams; failed fresh
  searches cannot reuse a previous booking session.
- **#142 cutoff:** round trips now expand every decoded outbound by default,
  including return-time-constrained date scans. An explicit Python `top_n` cap
  must be positive and warns when incomplete. This increases request counts and
  does not guarantee complete market inventory beyond Google's supplied board.
- **#217 amenities:** corrected numeric amenity flags, Wi-Fi tiers, all six power
  types, and video-type precedence. New optional labels supplement boolean fields.
  Seat quality remains a separate raw code, never inferred from Wi-Fi.
- **#226 evaluated, not integrated:** tested upstream head `0567a3a` with its
  baseline request, Referer/service parameters, and public-page priming. JAX and
  LHR probes still returned HTTP 200 with provider error 13, not empty destinations.
  Explore remains unavailable; its CLI/MCP tools are not advertised or shipped.

Repeat the bounded transport diagnostic with a future date:

```sh
uv run python scripts/probe_explore.py JAX 2026-10-15 --extended
```

Default mode makes one POST; extended mode makes three POSTs and one priming GET,
subject to the shared client's retries. Output contains sanitized status/category
only. Nonzero exit means every variant failed. Even parseable payloads would still
require destination decoding and end-to-end verification before integrating Explore.

## Completed In The Fourth Batch

- **Dependency review:** replaced affected runtime and development packages.
  Initial audits reported 51 advisory matches in 13 runtime packages and 30 in
  five additional development packages, including duplicate advisory records.
  The complete updated export passes pip-audit on 3.10/3.13 with no ignored IDs.
  See SECURITY.md for scope and limits; this is not proof of exploitability or
  complete security coverage.
- **Supported versions:** Python 3.10-3.13, now including a local 3.12 test run.
  Restrict unverified 3.14+ rather than allow its older MCP dependency fallback.
  Raise applicable direct dependency floors and keep FastMCP within tested majors
  3/4. Locked tests use 3.2.0; fresh installs resolve 4.0.3.
- **Runtime safeguards:** reject non-finite timeouts; create diagnostic logs with
  owner-only permissions; retain the original CLI/JSON error if logging fails.
- **Install gates:** `make verify-install` builds and checks wheel/sdist, checks
  license/NOTICE inclusion, installs into disposable environments outside the
  checkout, and exercises core CLI plus stdio/localhost HTTP MCP. No Google calls
  or changes to global installs are made by this target.
- **Release gates:** SHA-pinned actions, non-persisted checkout credentials,
  bounded job timeouts, advisory checks, fresh-install checks, and container CI.
  Publishing remains manual and additionally checks owned repository, GLFI tag,
  version/lock agreement, verification jobs, and protected PyPI environment.
  Corrected Dependabot ownership. Environment protection/trusted publishing still
  need account-side setup; no remote workflows have run yet.
- **Container configuration:** non-editable install, non-root runtime, health
  probe, read-only Compose root filesystem, dropped capabilities, no-new-privileges,
  loopback-only published port, and excluded secret-file patterns. Runtime remains
  unverified on this host; public container distribution also needs an OS-image scan.

## Verification

Fourth-batch checks on 2026-09-05: all 971 offline Python tests passed on 3.10,
3.11, 3.12, and 3.13. The 322 TypeScript tests, lint/typecheck, and build passed;
its live transport is still not ported. Ruff and actionlint passed. Updated
runtime/dev dependency audits passed on Python 3.10/3.13. Fresh core wheel, MCP
wheel, and MCP sdist installs passed, including stdio and HTTP; a separate sdist
MCP check passed on 3.12. Live JAX-JFK for 2026-10-15 with two adults and one child
returned ten flights using the updated development lock. Docker is unavailable;
container/remote CI checks remain pending, not marked passed.
The rebuilt installed wheel also returned ten flights, passed stdio/HTTP checks,
and had no known advisories in its 81 registry dependencies (the unpublished GLFI
package itself is not in the advisory database). Original `fli` is untouched.
No servers were left running, and nothing was pushed or published.

Third-batch checks on 2026-09-05: all 951 offline Python tests passed on 3.10,
3.11, and 3.13 with the Makefile's terminal environment. Ruff lint/formatting,
wheel/sdist builds, and Twine checks passed. Live JAX to JFK/LGA (2026-10-15
outbound, 2026-10-19 return, two adults and one child) returned six itineraries
with morning outbound/evening return departures and sorted selected fares. The
same constrained 3-4 day flexible scan returned both date pairs. Installed
FastMCP 4.0.3 stdio returned a live SFO-JFK search with amenity labels; all four
tool names, localhost HTTP health, and HTTP tool listing passed. No servers left
running. Explore's three probe variants all returned error 13; not integrated.
TypeScript was unchanged and not rerun; Docker remains unavailable/unverified.

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
