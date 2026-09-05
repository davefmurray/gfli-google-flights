# GLFI

Flight search for your terminal and AI assistants. Independently maintained
from [Fli](https://github.com/punitarani/fli), with its MIT license and history preserved.

**Pre-release:** Python CLI and MCP are the supported starting point. No PyPI,
npm, Homebrew, or container-registry release has been published yet.

## Install From Source

Requires Python 3.10+ and [uv](https://docs.astral.sh/uv/).

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

Same-day validation uses a conservative `UTC today - 1 day` allowance because
the dataset lacks airport time zones. This avoids rejecting evening departures
west of UTC but can also permit a date that is already past locally.

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
`find_airports`, and `get_booking_options` (subject to the limitation below).
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

## Current Limits

- Google Flights is an unofficial, reverse-engineered data source, not a stable API.
  Provider changes, consent pages, throttling, and geography can affect results.
- Multi-city search is explicitly rejected: Google's public page does not supply
  the required results. Returning only the first leg would be misleading.
- Booking-price lookup still depends on a Google RPC that can reject requests.
  Google Flights deep links are available and preserve the requested cabin.
- Date scans make a search request per date/stay combination. Return-time filters
  require additional return searches for up to five outbound candidates per pair.
  Prices are the cheapest among the candidates checked, not an exhaustive guarantee.
  Start with a short range; the 366-combination limit is not a 366-request limit.
- Some passenger combinations, particularly infants, may produce no inline results.
- The inherited TypeScript library in `fli-js/` has not received the Python
  search-page transport repair. It is experimental and publishing is disabled.

## Development

```sh
uv sync --all-extras
make lint
make test-offline
uv run glfi --help
uv build
```

The public distribution and executable are `glfi`. Python imports remain under
`fli` initially to simplify upstream fixes. Install GLFI in a separate virtual
environment from the original `flights` distribution; `uv tool` and `pipx` do this.
Historical API documentation under `docs/` may retain upstream names or describe
capabilities that are currently unavailable. This README is the supported setup guide.

See [RELEASING.md](RELEASING.md) for release gates and [NOTICE](NOTICE) for attribution.
See [PRELAUNCH.md](PRELAUNCH.md) for completed fixes and the remaining backlog.
