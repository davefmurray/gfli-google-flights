"""Conservative, dated Starlink fleet evidence from airline-owned sources.

No network requests or inferred tail numbers. Announced future installations are
not evidence of present availability. Re-review rules within 90 days.
"""

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from fli.models.starlink import StarlinkAssessment, StarlinkFilter
from fli.search.exceptions import SearchUnsupportedError


@dataclass(frozen=True)
class FleetRule:
    """A reviewed operator/aircraft scope, with no arbitrary probability score."""

    carrier: str
    aircraft: tuple[str, ...]
    status: str
    reason: str
    source_url: str
    checked_on: date = date(2026, 9, 5)
    effective_from: date = date(2026, 9, 5)
    marketing_carrier: str | None = None


HA_SOURCE = "https://news.alaskaair.com/releases/hawaiian-airlines-now-offering-fast-and-free-starlink-wi-fi-across-entire-airbus-fleet/"
QR_SOURCE = "https://www.qatarairways.com/press-releases/en-WW/269475-qatar-airways-150-starlink-equipped-widebody-aircraft-now-include-world-s-first-starlink-equipped-boeing-787-9/"
UA_REGIONAL = "https://united.mediaroom.com/2026-02-02-United-Spotlights-Starlink-Wi-Fi-in-New-Big-Game-Ad-as-Airline-Completes-Installation-on-300-Regional-Aircraft"
UA_737 = "https://united.mediaroom.com/2025-10-14-United-Schedules-First-Starlink-Equipped-Mainline-Flight-for-Take-Off"
UA_777 = "https://united.mediaroom.com/2026-06-22-United-Accelerates-Starlink-Wi-Fi-Rollout-with-First-Widebody-Transatlantic-Flight"

RULES = (
    FleetRule(
        "HA",
        ("A330", "A330-200", "A321NEO"),
        "likely",
        "Hawaiian reports completed Starlink installation on its passenger Airbus fleet.",
        HA_SOURCE,
    ),
    FleetRule(
        "QR",
        ("A350", "A350-900", "A350-1000", "B787-8"),
        "likely",
        "Qatar reports completed A350 and 787-8 Starlink programmes.",
        QR_SOURCE,
    ),
    FleetRule(
        "QR",
        ("B777", "B777-200", "B777-200LR", "B777-300", "B777-300ER"),
        "likely",
        "Qatar reports its 777 programme complete; leased subfleets may differ.",
        QR_SOURCE,
    ),
    FleetRule(
        "QR",
        ("B787", "B787-9"),
        "possible",
        "Qatar has equipped 787-9s, but the Dreamliner rollout remains partial.",
        QR_SOURCE,
    ),
    FleetRule(
        "UA",
        ("B737-800",),
        "possible",
        "United has Starlink-equipped 737-800s, not a confirmed whole-fleet fit.",
        UA_737,
    ),
    FleetRule(
        "UA",
        ("B777-200", "B777-200ER"),
        "possible",
        "United has Starlink-equipped 777-200s; its widebody rollout is partial.",
        UA_777,
    ),
    # United Express equipment must be marketed as UA; these operators also fly
    # for other brands, whose equipment cannot inherit United's rollout evidence.
    *(
        FleetRule(
            code,
            ("E170", "E175", "CRJ550", "CRJ700"),
            "possible",
            "United reports most two-cabin regional jets equipped; no tail-level confirmation.",
            UA_REGIONAL,
            marketing_carrier="UA",
        )
        for code in ("UA", "OO", "YX", "G7")
    ),
)


def normalize_aircraft(value: str | None) -> str:
    """Normalize known display names without guessing ambiguous aircraft families."""
    value = re.sub(r"\s+", "", (value or "").upper())
    for prefix, replacement in (
        ("AIRBUS", ""),
        ("BOEING", "B"),
        ("EMBRAER", "E"),
        ("CANADAIRRJ", "CRJ"),
        ("BOMBARDIER", ""),
    ):
        if value.startswith(prefix):
            value = replacement + value[len(prefix) :]
            break
    return value.replace("ERJ-", "E").replace("CRJ-", "CRJ").replace("EE", "E")


def validate_starlink_filter(filters) -> None:
    """Fail explicitly when the catalog cannot support the requested travel dates."""
    if filters.starlink == StarlinkFilter.ANY:
        return
    today = datetime.now(timezone.utc).date()
    fresh = [r for r in RULES if r.checked_on <= today <= r.checked_on + timedelta(days=90)]
    if not fresh:
        raise SearchUnsupportedError(
            "Starlink fleet evidence is stale; review the catalog before filtering."
        )
    latest = max(r.checked_on + timedelta(days=90) for r in fresh)
    dates = [segment.parsed_travel_date.date() for segment in filters.flight_segments]
    if hasattr(filters, "parsed_to_date"):
        stay = getattr(filters, "duration", None) or (dates[-1] - dates[0]).days
        dates.append(filters.parsed_to_date.date() + timedelta(days=stay))
    if any(day > latest for day in dates):
        raise SearchUnsupportedError(
            f"Starlink filtering is only reviewed through {latest}; "
            "use --starlink any or refresh the evidence."
        )


def assess_starlink(leg, *, today: date | None = None) -> StarlinkAssessment:
    """Assess one leg using operating carrier, aircraft, freshness and contradictions."""
    today = today or datetime.now(timezone.utc).date()
    carrier = (leg.operating_airline or leg.airline).name
    aircraft = normalize_aircraft(leg.aircraft)
    rule = next(
        (
            r
            for r in RULES
            if r.carrier == carrier
            and aircraft in r.aircraft
            and (r.marketing_carrier is None or r.marketing_carrier == leg.airline.name)
        ),
        None,
    )
    if rule is None:
        return StarlinkAssessment(
            reason="No reviewed evidence for this operator/aircraft combination."
        )
    review_after = rule.checked_on + timedelta(days=90)
    evidence = {
        "source_url": rule.source_url,
        "checked_on": rule.checked_on,
        "review_after": review_after,
    }
    if not rule.checked_on <= today <= review_after:
        return StarlinkAssessment(reason="Fleet evidence needs review before use.", **evidence)
    if not rule.effective_from <= leg.departure_datetime.date() <= review_after:
        return StarlinkAssessment(
            reason="Departure is outside the reviewed evidence window.", **evidence
        )
    if leg.amenities is not None and leg.amenities.wifi is False:
        return StarlinkAssessment(
            reason="Google reports no Wi-Fi, conflicting with fleet evidence.", **evidence
        )
    return StarlinkAssessment(status=rule.status, reason=rule.reason, **evidence)


def annotate_and_match(flight, mode: StarlinkFilter = StarlinkFilter.ANY) -> bool:
    """Annotate all legs; filtered itineraries require every leg to meet the threshold."""
    mode = StarlinkFilter(mode)
    for leg in flight.legs:
        leg.starlink = assess_starlink(leg)
    if mode == StarlinkFilter.ANY:
        return True
    allowed = {"likely"} if mode == StarlinkFilter.LIKELY else {"likely", "possible"}
    return bool(flight.legs) and all(leg.starlink.status in allowed for leg in flight.legs)


def itinerary_status(legs) -> str:
    """Use the weakest leg's evidence, including both halves of a round trip."""
    statuses = [leg.starlink.status if leg.starlink else "unknown" for leg in legs]
    return (
        min(statuses, key={"unknown": 0, "possible": 1, "likely": 2}.get) if statuses else "unknown"
    )
