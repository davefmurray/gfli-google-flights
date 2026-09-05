"""Compare final itinerary quotes within a single search, never across currencies."""

from decimal import Decimal

from fli.models.google_flights.base import StarlinkPremium
from fli.search.starlink import annotate_and_match


def compare_starlink_fares(results, mode):
    """Filter full itineraries and attach same-currency known-fare differences."""
    baselines = {}
    for result in results:
        quote = result[-1] if isinstance(result, tuple) else result
        if quote.price is not None and quote.currency:
            price = Decimal(str(quote.price))
            baselines[quote.currency] = min(baselines.get(quote.currency, price), price)
    matched = []
    for result in results:
        segments = result if isinstance(result, tuple) else (result,)
        if not all(annotate_and_match(segment, mode) for segment in segments):
            continue
        quote = segments[-1]
        quote.starlink_premium = None
        if quote.price is not None and quote.currency in baselines:
            baseline = baselines[quote.currency]
            quote.starlink_premium = StarlinkPremium(
                baseline_price=baseline,
                amount=Decimal(str(quote.price)) - baseline,
                currency=quote.currency,
            )
        matched.append(result)
    return matched
