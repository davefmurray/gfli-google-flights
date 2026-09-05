"""Enforce connection constraints on every stop, including airport transfers."""

from fli.models.google_flights.base import FlightResult, LayoverRestrictions


def matches_connections(flight: FlightResult, rules: LayoverRestrictions | None) -> bool:
    """Require every connection to meet the requested airport and wait constraints."""
    if rules is None or not rules.active:
        return True
    if not flight.legs:
        return False
    allowed = set(rules.airports or [])
    excluded = set(rules.exclude_airports or [])
    for arrival, departure in zip(flight.legs, flight.legs[1:], strict=False):
        airports = {arrival.arrival_airport, departure.departure_airport}
        if (allowed and not airports <= allowed) or airports & excluded:
            return False
        # Google supplies airport-local timestamps, without timezone offsets.
        # A transfer between airports may cross timezones: do not guess its wait.
        if arrival.arrival_airport != departure.departure_airport:
            if rules.min_duration or rules.max_duration or rules.exclude_overnight:
                return False
            continue
        minutes = (departure.departure_datetime - arrival.arrival_datetime).total_seconds() / 60
        if minutes < 0:
            return False
        if rules.min_duration is not None and minutes < rules.min_duration:
            return False
        if rules.max_duration is not None and minutes > rules.max_duration:
            return False
        if (
            rules.exclude_overnight
            and arrival.arrival_datetime.date() != departure.departure_datetime.date()
        ):
            return False
    return True
