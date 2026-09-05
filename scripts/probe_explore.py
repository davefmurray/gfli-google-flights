"""Bounded diagnostic for upstream PR #226's Explore request, not a supported tool.

Based on punitarani/fli PR #226 (0567a3a). Run with a future date:
    uv run python scripts/probe_explore.py JAX 2026-10-15
    uv run python scripts/probe_explore.py LHR 2026-10-15 --extended

One request by default; extended mode tests the documented Referer/service
parameters and a public-page priming request, for three POSTs total. Outputs
only status/diagnostics, never cookies or raw response identifiers. Parseable
chunks are evidence of transport availability, not verified destination results.
"""

import argparse
import json
import urllib.parse
from datetime import datetime

from fli.core.builders import normalize_date
from fli.core.parsers import resolve_airport
from fli.models.google_flights.base import earliest_searchable_date
from fli.search._wire import iter_wrb_chunks
from fli.search.client import get_client
from fli.search.exceptions import SearchClientError, SearchParseError, search_error_type

ENDPOINT = (
    "https://www.google.com/_/FlightsFrontendUi/data/travel.frontend.flights."
    "FlightsFrontendService/GetExploreDestinations"
)


def request_body(origin: str, departure: str) -> str:
    """Build the captured one-adult/economy/one-way/Anywhere probe request."""
    origin = resolve_airport(origin).name
    departure = normalize_date(departure)
    if datetime.strptime(departure, "%Y-%m-%d").date() < earliest_searchable_date():
        raise ValueError("Probe departure date cannot be in the past")
    segment = [[[[origin, 0]]], [[["/m/02j71", 6]]], None, 0, None, None, departure, None]
    inner = [None] * 26
    inner[2], inner[4], inner[5], inner[6] = 2, [], 1, [1, 0, 0, 0]
    inner[13], inner[17], inner[24], inner[25] = [segment], 1, 1, 1
    outer = [[], None, None, inner, None, 1, None, 0, None, 0, [447, 712], 3]
    return "f.req=" + urllib.parse.quote(
        json.dumps([None, json.dumps(outer, separators=(",", ":"))], separators=(",", ":"))
    )


def probe(origin: str, departure: str, *, extended: bool = False) -> list[dict]:
    """Run a small, fixed probe matrix and return sanitized evidence."""
    body = request_body(origin, departure)
    client = get_client()
    variants = ["baseline", "referer_service", "primed"] if extended else ["baseline"]
    results = []
    for variant in variants:
        record = {"variant": variant, "origin": origin.upper(), "departure_date": departure}
        headers = {
            "content-type": "application/x-www-form-urlencoded;charset=UTF-8",
            "x-same-domain": "1",
            "origin": "https://www.google.com",
        }
        url = ENDPOINT + "?curr=USD&hl=en&gl=US"
        if variant != "baseline":
            headers["referer"] = "https://www.google.com/travel/explore"
        if variant == "referer_service":
            url += "&soc-app=162&soc-platform=1&soc-device=1&rt=c"
        try:
            if variant == "primed":
                client.get(
                    "https://www.google.com/travel/explore",
                    impersonate="chrome",
                    allow_redirects=True,
                )
            response = client.post(
                url=url, data=body, headers=headers, impersonate="chrome", allow_redirects=True
            )
            record["http_status"] = response.status_code
            response.raise_for_status()
            chunks = list(iter_wrb_chunks(response.text, strict=True))
            if not chunks:
                raise SearchParseError("Explore returned no result payloads")
            record.update(transport_available=True, payload_chunks=len(chunks))
        except SearchClientError as exc:
            record.update(
                transport_available=False,
                error_type=search_error_type(exc),
                provider_code=getattr(exc, "code", None),
            )
        results.append(record)
    return results


def main() -> None:
    """Run an explicit probe; nonzero exit means no variant returned payloads."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("origin")
    parser.add_argument("departure_date")
    parser.add_argument("--extended", action="store_true")
    args = parser.parse_args()
    results = probe(args.origin, args.departure_date, extended=args.extended)
    print(json.dumps(results, indent=2))
    raise SystemExit(0 if any(r["transport_available"] for r in results) else 1)


if __name__ == "__main__":
    main()
