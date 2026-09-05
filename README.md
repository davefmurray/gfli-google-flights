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
glfi dates --help
```

Use future dates. Searches support one-way and round-trip itineraries, cabin,
airline, airport, and stop filters. Run `glfi flights --help` for exact options.
No Google API key is required. Availability and prices must be confirmed on
the airline or booking site before purchasing.

`flights` and `dates` accept `--passengers` (aliases `--adults`, `-p`),
`--children`, `--infants-in-seat`, and `--infants-on-lap`. MCP flight/date/booking
tools expose the corresponding `passengers`, `children`, `infants_in_seat`, and
`infants_on_lap` fields. Per-itinerary flight booking links preserve both cabin
and passenger mix. Generic search links, including date-result links, do not yet
preserve cabin or passenger mix.

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
- Date scans make a search request per candidate date. Start with a short range.
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
