# GFLI Development

GFLI is an independent MIT-licensed derivative of punitarani/fli. Preserve
upstream history and license notices. Public commands and distribution use
`gfli`; Python imports stay under `fli` for now. Do not install the original
`flights` distribution in the same environment.

## Commands

- Dependencies: `uv sync --all-extras`
- Lint: `make lint`
- Deterministic tests: `make test-offline`
- CLI: `uv run gfli --help`
- MCP stdio: `uv run gfli-mcp`
- MCP HTTP: `uv run gfli-mcp-http` (loopback by default, port 8000)
- Build: `uv build`
- TypeScript offline checks: `cd fli-js && bun install && bun run ci`

## Boundaries

- No database or other persistent service is required.
- Preserve existing separately installed `fli` until explicitly asked to replace it.
- Google is unofficial and volatile. Never treat provider failures as proof of no flights.
- Multi-city is unsupported by the public search-page transport.
- Booking-price RPC can be rejected by Google; deep links are separate from live prices.
- TypeScript transport is not yet ported. Its package is private/unpublished.
- HTTP MCP has no built-in authentication. Never deploy it publicly without a gateway.
- Do not publish packages, containers, or documentation automatically on push.
- README.md and RELEASING.md supersede inherited upstream installation/release instructions.

## Testing

`make test-offline` excludes mixed/live-Google test modules, including the
legacy MCP live-search module. It includes fixture decoders, protocol encoders, mocked
transport tests, CLI tests, and localhost MCP HTTP integration tests. Use a few
future-date live searches separately; do not run broad live date sweeps by default.
