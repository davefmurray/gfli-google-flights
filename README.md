# GLFI

Flight search for your terminal and AI assistants. Independently maintained
from [Fli](https://github.com/punitarani/fli), with its MIT license and history preserved.

**Pre-release:** Python CLI and MCP are the supported starting point. No PyPI,
npm, Homebrew, or container-registry release has been published yet.

## Install From Source

Requires Python 3.10-3.13 and [uv](https://docs.astral.sh/uv/).
The pre-release package rejects Python 3.14+ until its dependency set is verified.

The GitHub installation below becomes available once the independent repository
is published. Until then, run `uv tool install '.[mcp]'` from your local checkout.

```sh
git clone https://github.com/davefmurray/glfi.git
cd glfi
uv tool install '.[mcp]'
glfi --version
glfi --help
```

Alternatively, install a built wheel with `pipx install 'path/to/glfi-0.1.0-py3-none-any.whl[mcp]'`.
After the first PyPI release, the intended command will be `uv tool install 'glfi[mcp]'`.
Do not use that registry command before a release is announced here.

## Search

```sh
glfi airports Jacksonville
glfi JAX JFK 2026-10-15
glfi flights JAX JFK 2026-10-15 --format json
glfi JAX JFK 2026-10-15 --adults 2 --children 1
glfi JAX JFK,LGA 2026-10-15 --return 2026-10-19 --time 6-12 --return-time 16-23
glfi dates JAX JFK,LGA --from 2026-10-15 --to 2026-10-17 --round --min-duration 3 --max-duration 5
glfi dates --help
```

Use future dates. Searches support one-way and round-trip itineraries, cabin,
airline, airport, and stop filters. Run `glfi flights --help` for exact options.
No Google API key is required. Availability and prices must be confirmed on
the airline or booking site before purchasing.

`GLFI_TIMEOUT` sets a positive, finite per-request timeout in seconds (default 60).
Retries and multi-request searches can take longer than that individual timeout.
CLI error logs are created owner-only under `~/.glfi/logs`; they contain command
arguments and traceback details. Review them before sharing. A log-write failure
does not suppress the original error; JSON then reports `log_path: null`.

`flights` and `dates` accept `--passengers` (aliases `--adults`, `-p`),
`--children`, `--infants-in-seat`, and `--infants-on-lap`. MCP flight/date/booking
tools expose the corresponding `passengers`, `children`, `infants_in_seat`, and
`infants_on_lap` fields. Both itinerary booking links and search/date links preserve
cabin and passenger mix. Search links also preserve every selected airport;
client-side-only filters such as time windows are not encoded in those links.

Both CLI searches accept comma-separated origin and destination airports. Empty
entries are rejected; repeated codes are deduplicated. MCP uses the same parser.

Use `--return-time` (`-T`) for independent return departure hours; it requires
`--return DATE` on flights or `--round` on dates. MCP exposes
`return_departure_window` on flight, date, and booking tools. When omitted,
the return inherits `--time` / `departure_window`, preserving existing behavior.

Date searches accept `--min-duration` and `--max-duration` together, or MCP
`min_duration` and `max_duration`. These require a round trip and cannot be combined
with `--duration` / `trip_duration`. Stay lengths are inclusive, 1-366 days; the
departure-date count multiplied by the number of stay lengths must not exceed
366. Flexible results contain departure/return pairs sorted by price. Without
a range or explicit duration, round trips still default to a three-day stay.

Round-trip flight results quote the selected return option's complete itinerary
fare, not the outbound board's starting fare and not the sum of both quotes.
An unavailable selected fare remains unknown.

Round trips expand every decoded outbound candidate by default, including in
return-time-constrained date scans. Python callers can explicitly pass
`top_n=N` to trade coverage for fewer requests; skipping candidates emits a warning.
This removes GLFI's former five-outbound cutoff, not Google's own inventory limits.

Flight-leg amenities include `wifi_type` (free/paid/available), `power_type`, and
`video_type` alongside the existing boolean fields. Missing provider information
remains unknown. `legroom_rating` is Google's raw seat-quality code, not an ordered
comfort score or the Wi-Fi tier.

Provider failures are not empty searches. CLI JSON reports `success: false` with
`error.type`; MCP uses `success: false` with `error_type`. Categories include
`timeout`, `connection_error`, `http_error`, `parse_error`, `provider_rejected`,
`price_unavailable`, and `unsupported_search`. Malformed or partially undecodable
boards fail instead of returning a misleading subset. A date scan fails if any
date request fails, or matching flights have no usable prices; valid empty days
are still omitted normally.

Same-day validation uses a conservative `UTC today - 1 day` allowance because
the dataset lacks airport time zones. This avoids rejecting evening departures
west of UTC but can also permit a date that is already past locally.

## Starlink Finder

```sh
glfi JAX IAD 2026-10-15 --starlink possible
glfi DOH LHR 2026-10-15 --return 2026-10-19 --starlink likely
glfi dates DOH LHR --from 2026-10-15 --to 2026-10-16 --round --duration 4 --starlink likely
glfi starlink
glfi starlink --json
```

- `likely`: airline-reported completed fleet/subfleet installation, matched to
  the flight's operator and aircraft. This is an estimate, not flight confirmation.
- `possible`: includes likely results plus documented partial rollouts.
- `any`: default; no Starlink filtering. Results still carry available assessments.

Every leg must qualify, including connections and both directions. Operating
airlines take precedence over marketing codes; United Express rules additionally
require a United marketing code. Free Wi-Fi does **not** prove Starlink. Unknown
aircraft, unreviewed operators, contradictory no-Wi-Fi reports, and stale evidence
are not promoted to positive matches. Unknown does not mean "no Starlink."

Initial reviewed coverage: Hawaiian passenger A330/A321neo, Qatar A350/777/787
subfleets, and selected United/United Express aircraft. Other operators are unknown,
not a claim that they lack Starlink. Each JSON/MCP flight leg includes `starlink`
with status, reason, airline-owned source URL, review dates, and an explicit caveat.
Use `glfi starlink` to inspect the exact aircraft scopes. See [STARLINK.md](STARLINK.md).

The current evidence was reviewed on **2026-09-05**, with a **2026-12-04** review
deadline and travel horizon. Beyond that window, filtering raises an explicit
unsupported-search error until evidence is re-reviewed. Normal `--starlink any`
searches continue and mark stale inferences unknown. No automatic web scraping,
tail-number lookup, numeric probabilities, or per-flight confirmation is claimed.

MCP `search_flights`, `search_dates`, and `get_booking_options` accept the same
`starlink` values. Round-trip date filtering expands actual return candidates even
without return-time restrictions, so it costs more requests; start with a short
date range. Date results are matching fare/date pairs; run a flight search for
per-leg evidence. Google booking/search links do not preserve this GLFI-only filter.
Aircraft swaps, outages, route restrictions, and access requirements still apply.

## Connection Controls

```sh
glfi JAX LHR 2026-10-15 --min-layover 60 --max-layover 180 --exclude-layover JFK,EWR --no-overnight-layovers
glfi dates JAX LHR --from 2026-10-15 --to 2026-10-16 --round --duration 4 --max-layover 180 --no-overnight-layovers
```

Bounds are inclusive minutes at **each** connection, not total trip duration.
`--layover ATL,ORD` allows only those connecting airports; `--exclude-layover`
excludes them. Both accept repeated flags. Nonstop flights still qualify.
`--no-overnight-layovers` excludes waits crossing local midnight, not red-eye
flights. Constraints apply to both directions of a round trip. Constrained
round-trip date searches expand returns and can make substantially more requests.
Timing uses Google's airport-local timestamps, not a timezone database; DST
elapsed-time ambiguities remain. Airport transfers are excluded when requested
timing/overnight rules cannot be verified. Google links may not preserve local
exclusions; always check the selected itinerary before booking.

## Starlink Fare Comparison

```sh
glfi JAX IAD 2026-10-15 --starlink possible --starlink-premium
```

Adds a `starlink_premium` to each qualifying itinerary: the difference from the
cheapest **known same-currency fare in the same search**, with all other filters
unchanged. Round trips use the final selected complete-trip fare; prices are for
the entire passenger party. Zero means the candidate is already cheapest.
No cross-currency conversion, guessed currency, or missing-price substitution.
If its quote/currency is missing, the comparison is omitted. This is a comparison
of returned inventory, not the whole market or an onboard internet fee.
The baseline search includes non-Starlink outbound candidates, so round-trip
comparisons can require more requests. Supported on fixed-date flight searches,
not date grids. JSON and MCP expose the baseline, difference, currency and scope.

## Saved Presets

```sh
glfi save work-trip -- JAX IAD 2026-10-15 --starlink possible --starlink-premium --no-overnight-layovers
glfi run work-trip
glfi run work-trip --date 2026-11-05 --format json
glfi presets list
glfi presets show work-trip
glfi presets delete work-trip
```

Saving performs **no search**. `glfi flights ... --save NAME` and
`glfi dates ... --save NAME` are equivalent; `glfi save NAME -- dates ...`
also works. Add `--replace-preset` to the search arguments to explicitly replace
an existing name. Presets preserve filters, passenger mix, cabin, locale,
connection/Starlink preferences, and date-scan weekday/stay-duration settings.

`run --date` moves a flight preset's first date and shifts its return by the same
amount; `--return` can override that return. Date presets use `--from` / `--to`;
moving `--from` shifts the saved window. Overrides do not rewrite the preset.
Old dates remain inspectable but must be updated before running. Starlink
freshness and all ordinary search validation still apply.

Versioned JSON files live in `~/.config/glfi/presets` by default, respecting
`XDG_CONFIG_HOME`; `GLFI_PRESET_DIR` overrides the directory. New directories are
owner-only and files are mode 0600 on POSIX, with atomic writes and no silent
overwrites. Files contain travel preferences and dates, not credentials or
booking tokens. They are not encrypted and have no scheduler or notification
service. MCP shares the same store under the server's OS user; use separate
directories/users for separate trust boundaries.

MCP `save_search_preset` takes `name` and exactly one structured `flights` or
`dates` request. `run_search_preset` accepts the same date overrides as the CLI;
`manage_search_presets` supports `list`, `show`, and explicit `delete`.

## Installation Diagnostics

```sh
glfi doctor
glfi doctor --json
glfi doctor --check-provider
```

Checks Python/distribution, dependencies and MCP configuration, preset files,
and Starlink evidence freshness. Default diagnostics make no network requests
and change no files. Missing optional MCP dependencies or stale evidence are
warnings; configuration/install errors exit nonzero. Cookie values and captured
MCP stderr are never printed. The opt-in provider check performs one nonstop
JAX-JFK search 30 days ahead, subject to the normal timeout and retry policy.
It does not start an MCP server or verify a remote client's configuration.

Deferred ideas and their prerequisites are tracked in
[FUTURE_FEATURES.md](FUTURE_FEATURES.md).

## MCP

Install with the `[mcp]` extra. The same package supplies the CLI and both MCP transports.

For a local MCP client, add this server entry to its configuration:

```json
{
  "mcpServers": {
    "glfi": {
      "command": "glfi-mcp"
    }
  }
}
```

Use the absolute path returned by `command -v glfi-mcp` if the client does not
inherit your shell's PATH. Tools: `search_flights`, `search_dates`,
`find_airports`, and `get_booking_options` (subject to the limitation below), plus
`save_search_preset`, `run_search_preset`, and `manage_search_presets`.
Configuration uses `GLFI_MCP_` environment variables, such as
`GLFI_MCP_DEFAULT_CURRENCY=USD` and `GLFI_MCP_MAX_RESULTS=10`.

For local HTTP:

```sh
glfi-mcp-http
```

Endpoint: `http://127.0.0.1:8000/mcp/`. Health check: `/health`.
`HOST` and `PORT` override the bind address. **HTTP has no built-in authentication**;
keep it on loopback or place it behind an authenticated gateway. Do not expose
it directly to the public internet. Docker Compose publishes to loopback only:

```sh
docker compose up --build
```

Compose uses a read-only filesystem, dropped capabilities, a small temporary
filesystem, and a non-root process. Container execution is a required CI gate;
it has not been verified on the local development host, which has no Docker runtime.

## Current Limits

- Google Flights is an unofficial, reverse-engineered data source, not a stable API.
  Provider changes, consent pages, throttling, and geography can affect results.
- Multi-city search is explicitly rejected: Google's public page does not supply
  the required results. Returning only the first leg would be misleading.
- Booking-price lookup still depends on a Google RPC that can reject requests.
  Google Flights deep links are available and preserve the requested cabin.
- Explore is not available. Upstream PR #226's endpoint returned provider error
  13 in live checks; no Explore CLI command or MCP tool is shipped.
- Date scans make a search request per date/stay combination. Return-time filters
  require additional return searches for every decoded outbound candidate per pair.
  Without a return-time constraint, date prices remain outbound-board starting quotes.
  Prices are the cheapest published among candidates checked, not an exhaustive guarantee.
  Start with a short range; the 366-combination limit is not a 366-request limit.
- Some passenger combinations, particularly infants, may produce no inline results.
- The inherited TypeScript library in `fli-js/` has not received the Python
  search-page transport repair. It is experimental and publishing is disabled.

## Development

```sh
uv sync --all-extras
make lint
make test-offline
make audit
make verify-install
uv run glfi --help
uv build
```

The public distribution and executable are `glfi`. Python imports remain under
`fli` initially to simplify upstream fixes. Install GLFI in a separate virtual
environment from the original `flights` distribution; `uv tool` and `pipx` do this.
Historical API documentation under `docs/` may retain upstream names or describe
capabilities that are currently unavailable. This README is the supported setup guide.

See [RELEASING.md](RELEASING.md) for release gates and [NOTICE](NOTICE) for attribution.
See [SECURITY.md](SECURITY.md) for the security review scope and deployment limits.
See [PRELAUNCH.md](PRELAUNCH.md) for completed fixes and the remaining backlog.
