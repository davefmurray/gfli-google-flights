# GLFI Future Features

Unimplemented ideas, not release promises or additional pre-push requirements.
The selected pre-push additions are saved presets, Starlink fare comparisons,
installation diagnostics, and connection controls. Release gates remain in
[PRELAUNCH.md](PRELAUNCH.md).

## Work-Friendly Flight Ranking

Rank itineraries by Starlink evidence, reported power and legroom, duration,
and connections. Display explicit tradeoffs instead of an unexplained score.
Missing amenities must stay unknown, not become a negative claim. Let users
choose weights or an understandable ordering; preserve cheapest sorting.

## Price Alerts

Build on saved presets with price history, a scheduler and explicit notification
destinations. Define polling budgets, backoff, duplicate suppression, currency
and passenger identity, and expired-date handling before adding delivery.
Provider failures must never become price drops or "no flights" alerts.
Presets currently store preferences only: no monitoring runs in the background.

## Flight-Confirmed Starlink

Requires a reliable, licensed flight/tail assignment source plus installation
data, freshness and aircraft-swap handling. Keep onboard service availability
separate from installed hardware. Do not upgrade fleet inference to "confirmed"
without flight-specific evidence. Expand the current curated airline catalog
only after reviewing primary airline sources; see [STARLINK.md](STARLINK.md).

## Explore / Anywhere Search

Provider transport is blocked in the evaluated implementation. Resume only
when a bounded diagnostic proves usable destination results, not merely HTTP
200 or a parseable error payload. Do not add a fake successful empty tool.

## Multi-City And Booking Data

- True multi-city results, requiring a working provider transport and pricing
  the complete trip rather than showing a first-leg one-way quote.
- Reliable booking-price/vendor lookup, with session handling and live checks.
- Baggage-inclusive pricing and basic-economy/emissions enforcement, requiring
  dependable fare data. Current unsupported-filter warnings are not enforcement.
  A nearer correctness improvement is rejecting unsupported requested filters
  explicitly, with a documented compatibility change and CLI/MCP regressions.

## Distribution And Parity

- Homebrew formula after an owned, published GLFI artifact exists.
- ICAO input with authoritative airport mappings and disambiguation tests.
- TypeScript search transport parity before enabling npm publication.
- Authenticated hosted MCP with authorization, request limits and per-user preset
  isolation. Current local MCP presets belong to the server's OS user, not a
  remote caller; do not expose them through a public unauthenticated endpoint.

## Further Preset And Connection Improvements

- Explicit preference overrides beyond dates, schema migrations and opt-in sync.
- Airport timezone data for DST-aware elapsed connection times and airport
  transfers. Current connection timing uses Google's airport-local timestamps;
  transfers are excluded when timing/overnight constraints cannot be established.
- Date-grid Starlink premiums with same-date-pair baseline quotes. Current fare
  comparisons are for fixed-date flight searches, including round trips.
