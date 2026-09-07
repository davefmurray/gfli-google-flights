# Starlink Evidence

This is a fleet-based inference feature, not an airline flight-status integration.
Google's decoded Wi-Fi tier does not identify its satellite provider. There is no
supported tail-number or per-flight Starlink confirmation feed in this transport.

## Reviewed Sources

Reviewed 2026-09-05. Rules live in `fli/search/starlink.py`; `gfli starlink --json`
exposes their exact operator, aircraft, status, source, and date scope.

| Scope | Inference | Airline-owned evidence |
| --- | --- | --- |
| Hawaiian A330/A330-200, A321neo | Likely | [Airbus fleet rollout complete](https://news.alaskaair.com/releases/hawaiian-airlines-now-offering-fast-and-free-starlink-wi-fi-across-entire-airbus-fleet/) |
| Qatar A350, 777, 787-8 | Likely | [Completed programmes and August 2026 update](https://www.qatarairways.com/press-releases/en-WW/269475-qatar-airways-150-starlink-equipped-widebody-aircraft-now-include-world-s-first-starlink-equipped-boeing-787-9/) |
| Qatar 787-9 or unspecific 787 | Possible | Same update reports partial Dreamliner coverage; generic aircraft names cannot establish the variant. |
| United 737-800 | Possible | [Mainline launch and partial rollout](https://united.mediaroom.com/2025-10-14-United-Schedules-First-Starlink-Equipped-Mainline-Flight-for-Take-Off) |
| United 777-200/200ER | Possible | [First widebody customer service](https://united.mediaroom.com/2026-06-22-United-Accelerates-Starlink-Wi-Fi-Rollout-with-First-Widebody-Transatlantic-Flight) |
| United-marketed E170/E175/CRJ550/CRJ700, operated by UA/OO/YX/G7 | Possible | [Most two-cabin regional jets equipped](https://united.mediaroom.com/2026-02-02-United-Spotlights-Starlink-Wi-Fi-in-New-Big-Game-Ad-as-Airline-Completes-Installation-on-300-Regional-Aircraft) |

The status labels are GFLI's interpretation of these sources, not statements from
the airline about an individual flight. A completed programme does not exclude
equipment swaps, leased subfleets, new aircraft, outages, or geographic restrictions.
An announced future installation target is never treated as a completed rollout.

## Matching Rules

1. Prefer the reported operating carrier; otherwise use the marketing carrier as
   a fallback inference. Do not transfer parent-company or alliance coverage.
2. Match explicit aircraft names conservatively. A 737 MAX 8 is not a 737-800.
   Generic ambiguous names stay unknown unless fleet evidence covers that family.
3. Require reviewed, unexpired evidence and travel within its dated window.
   No matching rule means unknown, not a negative equipment finding.
4. A Google no-Wi-Fi flag conflicts with positive fleet evidence: return unknown.
   Missing Wi-Fi information neither proves nor disproves the inferred provider.
5. Require every leg to pass a requested threshold. A known outbound cannot make
   an unknown connection or return qualify. The itinerary label uses its weakest leg.

`likely` is reserved for completed-programme evidence; even a majority partial
rollout stays `possible`. Neither is a calibrated probability. No confirmed mode
is offered without a per-flight source. Final verification belongs with the airline
before booking and again close to departure.

## Maintenance

Rules expire 90 days after review. The initial travel horizon/review deadline is
2026-12-04. Filtering beyond that window fails explicitly; unfiltered search keeps
working. This intentionally trades coverage for avoiding stale confident claims.

To refresh or expand coverage, re-read current primary airline sources, inspect
subfleet exceptions and operating-carrier scope, then update the rule dates and
aircraft scopes with regression tests. Never advance `checked_on` just to bypass
expiry. No background scraping or silent catalog updates run during searches.

Useful next integrations, not shipped: airline flight-status equipment details,
dated tail-level installation records with licensing permission, and actual
flight-assignment matching. Those are prerequisites for a future confirmed filter.
