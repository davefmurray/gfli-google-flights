# GFLI — Google Flights Search CLI & MCP

**Find a better flight. Keep your standards.**

[![CI](https://github.com/davefmurray/gfli-google-flights/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/davefmurray/gfli-google-flights/actions/workflows/ci.yml)
[![Python 3.10-3.13](https://img.shields.io/badge/python-3.10%20%E2%80%93%203.13-3776AB)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/license-MIT-16803C)](LICENSE.txt)

Search Google Flights from your terminal or AI assistant. Find **likely or possible
Starlink-equipped flights**, see what that preference costs, rule out bad
connections, and save the whole search for next time.

**One CLI. Seven MCP tools. No Google API key. No database.**

```sh
gfli JAX IAD 2026-10-15 \
  --starlink possible --starlink-premium \
  --min-layover 60 --max-layover 180 \
  --no-overnight-layovers
```

> **Source preview:** Install from this repository, not PyPI. The Python CLI and
> MCP server are supported; no registry release has been published.
> Starlink labels are **sourced fleet estimates, not flight guarantees**.

[Install](#install) | [Starlink](#starlink-finder) | [Connections](#connection-controls) | [Presets](#saved-searches) | [MCP](#mcp-for-ai-assistants) | [Limits](#know-the-limits)

## What You Get

| Capability | What it does |
| --- | --- |
| **Starlink Finder** | Matches operator and aircraft against reviewed airline evidence. Every leg must qualify. |
| **Starlink premium** | Shows the extra fare versus the cheapest known comparable result in the same search. |
| **Connection controls** | Sets minimum/maximum waits, includes or excludes airports, and avoids overnight layovers. |
| **Flexible dates** | Searches departure windows and stay-length ranges, including multiple origin/destination airports. |
| **Saved searches** | Preserves passengers, cabin, filters, locale, and date preferences. Reuse them from CLI or MCP. |
| **Flight details** | Shows reported aircraft, legroom, Wi-Fi, power, and video. Missing information stays unknown. |
| **Agent-ready output** | Structured JSON, typed provider errors, booking deep links, and seven MCP tools. |

## Install

The project name is **GFLI** (`gfli`); the earlier `glfi` spelling was a typo.
If you installed that preview, uninstall it before installing `gfli`, update
your MCP command and `GLFI_*` environment variables to `GFLI_*`, and move any
saved presets from `~/.config/glfi/presets` to `~/.config/gfli/presets`
(or the equivalent directory under `XDG_CONFIG_HOME`).

Requires [uv](https://docs.astral.sh/uv/getting-started/installation/).
GFLI supports **Python 3.10-3.13**; this command selects 3.11 and installs into an
isolated tool environment:

```sh
uv tool install --python 3.11 \
  'gfli[mcp] @ git+https://github.com/davefmurray/gfli-google-flights.git'

gfli --version
gfli doctor
```

That installs `gfli`, `gfli-mcp`, and `gfli-mcp-http`. Omit `[mcp]` for the
CLI without optional server dependencies. If your shell cannot find the commands,
run `uv tool update-shell` and restart it.

Prefer a checkout?

```sh
git clone https://github.com/davefmurray/gfli-google-flights.git
cd gfli-google-flights
uv tool install --python 3.11 '.[mcp]'
```

To refresh a source installation, rerun the GitHub install command with
`--force --reinstall`. For a reproducible installation, append `@COMMIT_SHA` to
the Git URL. **Do not install `gfli` from PyPI until a package release is announced.**

## First Flights

Use future travel dates in these examples.

```sh
# Find an airport.
gfli airports Jacksonville

# One way. "flights" is the default command.
gfli JAX JFK 2026-10-15

# Two adults, one child, multiple destination airports.
gfli JAX JFK,LGA 2026-10-15 --adults 2 --children 1

# Morning outbound, evening return.
gfli JAX JFK 2026-10-15 --return 2026-10-19 \
  --time 6-12 --return-time 16-23

# Structured output for scripts and agents.
gfli JAX JFK 2026-10-15 --format json
```

Cabin, airline, alliance, stop, and locale options: `gfli flights --help`.
Passenger flags also include `--infants-in-seat` and `--infants-on-lap`;
`--passengers`, `--adults`, and `-p` all mean adult count.

Round-trip prices use the **final selected itinerary quote**, not the outbound
starting price or the sum of two quotes. Booking links preserve cabin, passenger
mix, and selected flights. Always confirm the final fare with the seller.

## Starlink Finder

```sh
gfli JAX IAD 2026-10-15 --starlink possible
gfli DOH LHR 2026-10-15 --return 2026-10-19 --starlink likely
gfli starlink
```

| Mode | Meaning |
| --- | --- |
| `likely` | Matches an airline-reported completed fleet/subfleet installation. Still not flight-confirmed. |
| `possible` | Includes likely matches plus documented partial rollouts. |
| `any` | Default. No Starlink filtering; available evidence is still attached. |

**Every connection and both directions must qualify.** Operating airlines take
precedence over marketing codes. Free Wi-Fi does not prove Starlink, and unknown
does not mean absent.

Initial coverage includes selected **Hawaiian, Qatar, and United/United Express**
aircraft. Results carry the reason, source URL, checked date, and review deadline.
`gfli starlink --json` exposes the exact catalog; [STARLINK.md](STARLINK.md)
documents the aircraft scopes and evidence.

Evidence was reviewed **September 5, 2026**, with a **December 4, 2026** review
deadline and travel horizon. Stale evidence or travel beyond that horizon causes
an explicit error when filtering, until the catalog is re-reviewed. Unfiltered
searches remain available. Aircraft swaps, outages, and route restrictions can
still change the onboard experience.

### What Does Starlink Cost You?

```sh
gfli JAX IAD 2026-10-15 --starlink possible --starlink-premium
```

GFLI compares qualifying flights with the cheapest **known same-currency fare
in the same search**, with other filters unchanged. A $243 qualifying fare against
a $93 baseline is a **$150 premium**. Those figures illustrate the comparison,
not a fare promise.

The comparison is for the entire passenger party. It is **not a Wi-Fi fee**, a
currency conversion, or a claim about every flight on the market. Missing price
or currency means no comparison. Works on fixed-date one-way and round-trip
searches, not date grids. JSON/MCP output includes `starlink_premium` with
`baseline_price`, `amount`, `currency`, and `scope`.

## Connection Controls

```sh
gfli JAX LHR 2026-10-15 \
  --min-layover 60 --max-layover 180 \
  --exclude-layover JFK,EWR \
  --no-overnight-layovers
```

| Flag | Rule |
| --- | --- |
| `--min-layover 60` | At least 60 minutes at every connection. |
| `--max-layover 180` | At most 180 minutes at every connection. |
| `--layover ATL,ORD` | Connect only through these airports. |
| `--exclude-layover JFK,EWR` | Never connect through these airports. |
| `--no-overnight-layovers` | No connection crossing local midnight. Red-eye flights can still qualify. |

Bounds are inclusive. Airport flags accept comma-separated codes or repeated
flags. Nonstop flights remain eligible. Rules apply to both directions and are
also available on `gfli dates` and MCP flight/date/booking tools.

Timing uses airport-local timestamps, so daylight-saving ambiguities remain.
Airport transfers are excluded when requested timing rules cannot be established.

## Flexible Dates

```sh
# Depart within a window, stay three to five days.
gfli dates JAX JFK,LGA \
  --from 2026-10-15 --to 2026-10-17 \
  --round --min-duration 3 --max-duration 5

# Four-day trip, likely Starlink on every leg.
gfli dates DOH LHR \
  --from 2026-10-15 --to 2026-10-16 \
  --round --duration 4 --starlink likely
```

Stay ranges require both `--min-duration` and `--max-duration`; do not combine
them with fixed `--duration`. Round trips default to a three-day stay when neither
is supplied. `--return-time` overrides the outbound time preference on the return;
otherwise the return inherits `--time`.

**Start with a short window.** Date scans make multiple requests. Return-time,
Starlink, and connection constraints require expanding actual return candidates;
ordinary unconstrained round-trip date prices remain outbound-board starting
quotes. The 366 date/stay-combination ceiling is not a 366-request ceiling.

## Saved Searches

Set your preferences once. Change the dates when the next trip comes up.

```sh
gfli save work-trip -- JAX IAD 2026-10-15 \
  --starlink possible --starlink-premium \
  --no-overnight-layovers

gfli run work-trip
gfli run work-trip --date 2026-11-05 --format json

gfli presets list
gfli presets show work-trip
gfli presets delete work-trip
```

Saving performs **no search**. You can also add `--save NAME` to a flight/date
command, or use `gfli save NAME -- dates ...`. Add `--replace-preset` to the search
arguments to explicitly replace an existing preset.

`run --date` shifts the saved flight dates together; `--return` overrides the
return. Date-search presets use `--from` and `--to`; changing `--from` shifts the
window. Overrides are revalidated in memory and **never rewrite the saved file**.

Presets are versioned JSON in `~/.config/gfli/presets`, respecting
`XDG_CONFIG_HOME` or `GFLI_PRESET_DIR`. Writes are atomic, with owner-only file
permissions on POSIX. They contain travel preferences and dates, not booking
tokens or credentials. They are not encrypted. **No background monitoring,
price alerts, or cloud account is involved.**

## MCP For AI Assistants

Install with `[mcp]`, then add this entry to your MCP client's configuration:

```json
{
  "mcpServers": {
    "gfli": {
      "command": "gfli-mcp"
    }
  }
}
```

If the client does not inherit your shell's `PATH`, replace `gfli-mcp` with the
absolute path returned by `command -v gfli-mcp`.

| Tool | Purpose |
| --- | --- |
| `search_flights` | Search a fixed-date trip with flight details and booking links. |
| `search_dates` | Find fares across departure dates and stay lengths. |
| `find_airports` | Resolve airport names and codes. |
| `get_booking_options` | Request vendor/fare options; Google's booking RPC may reject this. |
| `save_search_preset` | Save exactly one structured `flights` or `dates` request, without searching. |
| `run_search_preset` | Run a saved search with optional date overrides. |
| `manage_search_presets` | List, show, or explicitly delete presets. |

Try asking your assistant:

> Find JAX to IAD flights for October 15, 2026 with possible Starlink. Compare
> the fare premium and exclude overnight connections. Show the evidence.

CLI and MCP share the same local preset store. MCP parameter names include
`starlink`, `starlink_premium`, `min_layover`, `max_layover`, `exclude_layover`,
and `no_overnight_layovers`. Starlink premium comparison is flight-search only.

<details>
<summary>Local HTTP transport and configuration</summary>

```sh
gfli-mcp-http
```

MCP endpoint: `http://127.0.0.1:8000/mcp/`. Health: `/health`.
`HOST` and `PORT` override the bind address. Defaults use `GFLI_MCP_` variables,
including `GFLI_MCP_DEFAULT_CURRENCY`, `GFLI_MCP_DEFAULT_PASSENGERS`, and
`GFLI_MCP_MAX_RESULTS`.

**HTTP has no built-in authentication. Keep it on loopback.** Public hosting
requires authentication, abuse controls, and per-user preset isolation. Presets
belong to the server's OS user, not an authenticated remote caller.

`docker compose up --build` provides a non-root, read-only container with a
loopback port. See the [container verification gate](RELEASING.md#container-gate)
and [CI results](https://github.com/davefmurray/gfli-google-flights/actions/workflows/ci.yml).
Container registry publication is not enabled.

</details>

## Troubleshooting

```sh
gfli doctor                   # Local checks only; no network, no file changes.
gfli doctor --json            # Machine-readable diagnostics.
gfli doctor --check-provider  # Explicitly test a live search.
gfli flights --help
gfli dates --help
```

Doctor checks installation, dependencies/MCP configuration, preset files, and
Starlink freshness. Optional-dependency/stale-evidence warnings differ from
configuration failures. Provider checking runs a nonstop JAX-JFK search 30 days
ahead, subject to normal retries; it does not verify your MCP client's setup.

`GFLI_TIMEOUT` sets a positive, finite **per-request** timeout in seconds
(default 60). Retries and multi-request searches can take longer. Error logs
under `~/.gfli/logs` include arguments and tracebacks: review them before sharing.

## Know The Limits

- **Unofficial provider.** Google changes its endpoints. Consent pages, geography,
  rate limiting, and provider changes can affect results. GFLI is not affiliated
  with Google, Starlink, SpaceX, or any airline.
- **Errors are not empty results.** Provider, parsing, and unavailable-price errors
  are explicit. CLI JSON uses `error.type`; MCP uses `error_type`. A failed date
  request fails the scan rather than disappearing from it.
- **Returned inventory, not the whole market.** Round-trip searches expand every
  decoded outbound by default; Google still controls the supplied inventory.
  Python's optional `top_n` trades coverage for fewer requests and warns when
  incomplete. Starlink premium comparisons reject that cap.
- **Some filters are not enforceable yet.** Baggage, emissions, and basic-economy
  options currently warn rather than reliably enforce. Do not rely on them.
- **No multi-city or Explore search.** Their provider paths are unavailable.
  Booking-price RPC can also be rejected; booking deep links remain separate.
- **Links do not preserve every filter.** GFLI-only Starlink, time, and connection
  exclusions may not survive in Google links. Recheck the itinerary before booking.
- **Timezones and passenger edge cases.** Same-day validation uses a conservative
  UTC-minus-one-day allowance, not airport timezones. Some infant/passenger
  combinations may yield no inline results. Unknown amenities remain unknown.
- **Python first.** The inherited `fli-js/` transport is experimental, lacks Python
  live-search parity, and is not published to npm.

## Development

```sh
git clone https://github.com/davefmurray/gfli-google-flights.git
cd gfli-google-flights
uv sync --python 3.11 --all-extras
make lint
make test-offline
make audit
make verify-install
```

The latest local feature verification passed **1,075 offline tests on each of
Python 3.10, 3.11, 3.12, and 3.13**, plus clean wheel/sdist and CLI/MCP checks.
The badge above reports GitHub CI status separately. Live smoke checks are
documented in [PRELAUNCH.md](PRELAUNCH.md); they are not uptime guarantees.

The distribution and commands are `gfli`; Python imports remain `fli` for
upstream compatibility. Do not install GFLI and the original `flights` package
in the same environment. `uv tool` keeps them isolated.

Found a bug? [Open an issue](https://github.com/davefmurray/gfli-google-flights/issues) with
your version, redacted command, and diagnostic output. Keep travel details and
credentials out of public reports. Contributions should include regression tests;
provider failures must never be presented as successful empty searches.

| More | Where |
| --- | --- |
| What's next | [Future features](FUTURE_FEATURES.md) |
| Starlink evidence and refresh rules | [Starlink catalog notes](STARLINK.md) |
| Completed work and verification | [Prelaunch record](PRELAUNCH.md) |
| Package release process | [Releasing](RELEASING.md) |
| Security and deployment boundaries | [Security](SECURITY.md) |

Historical `docs/` and examples may use upstream names or unavailable APIs.
This README is the supported setup guide.

## Credits And License

GFLI is an independently maintained derivative of
[Fli](https://github.com/punitarani/fli), created by Punit Arani and its
contributors. GFLI preserves the upstream history and MIT notices, with
additional work maintained by Dave Murray.

[MIT license](LICENSE.txt). [Attribution and incorporated work](NOTICE).
