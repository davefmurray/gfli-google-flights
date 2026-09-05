"""Premium comparisons use full same-search fares, never inferred currency."""

import pytest
from pydantic import ValidationError

from fli.cli.utils import serialize_flight_result
from fli.mcp.server import _serialize_flight_result
from fli.models import FlightSearchFilters
from fli.models.starlink import StarlinkFilter
from fli.search import SearchFlights
from fli.search.premium import compare_starlink_fares
from tests.search.test_reliability import query
from tests.search.test_starlink import flight

pytest_plugins = ["tests.search.test_starlink"]


def priced(price, day, *, qualifies=True, currency="USD"):
    result = flight("QR" if qualifies else "DL")
    result.price = price
    result.currency = currency
    result.legs[0].departure_datetime = day
    return result


def test_premium_same_currency_only(fresh_rules):
    baseline = priced(100, fresh_rules, qualifies=False)
    candidate = priced(142.35, fresh_rules)
    other_currency = priced(1, fresh_rules, qualifies=False, currency="EUR")
    assert compare_starlink_fares([baseline, other_currency, candidate], "likely") == [candidate]
    assert candidate.starlink_premium.amount == 42.35
    assert candidate.starlink_premium.baseline_price == 100


@pytest.mark.parametrize("price,currency", [(None, "USD"), (100, None)])
def test_missing_quote_or_currency_has_no_premium(price, currency, fresh_rules):
    result = priced(price, fresh_rules, currency=currency)
    assert compare_starlink_fares([result], "likely") == [result]
    assert result.starlink_premium is None


def test_cheapest_qualifier_has_zero_premium(fresh_rules):
    result = priced(0, fresh_rules)
    compare_starlink_fares([result], "likely")
    assert result.starlink_premium.amount == 0


def test_roundtrip_final_quote_and_every_leg(fresh_rules):
    nonqualifying = (priced(1, fresh_rules), priced(300, fresh_rules, qualifies=False))
    qualifying = (priced(9999, fresh_rules), priced(342, fresh_rules))
    assert compare_starlink_fares([nonqualifying, qualifying], "likely") == [qualifying]
    assert qualifying[-1].starlink_premium.amount == 42
    cli = serialize_flight_result(qualifying)
    mcp = _serialize_flight_result(qualifying, True)
    assert cli["starlink_premium"] == mcp["starlink_premium"]
    assert cli["starlink_premium"]["baseline_price"] == 300


def test_one_way_serialization(fresh_rules):
    result = priced(100, fresh_rules)
    compare_starlink_fares([result], "likely")
    assert (
        serialize_flight_result(result)["starlink_premium"]
        == _serialize_flight_result(result)["starlink_premium"]
    )


def test_search_fetches_unfiltered_board_once_preserving_other_filters(monkeypatch, fresh_rules):
    filters = query("flights")
    filters.starlink = StarlinkFilter.LIKELY
    filters.starlink_premium = True
    captured = []

    def fetch(self, current, **kwargs):
        captured.append(current)
        return [priced(100, fresh_rules, qualifies=False), priced(150, fresh_rules)]

    monkeypatch.setattr(SearchFlights, "_fetch_flights", fetch)
    results = SearchFlights().search(filters)
    assert len(captured) == 1
    assert captured[0].starlink == "any"
    assert captured[0].passenger_info == filters.passenger_info
    assert captured[0].flight_segments == filters.flight_segments
    assert filters.starlink == "likely"
    assert len(results) == 1
    assert results[0].starlink_premium.amount == 50


def test_premium_requires_threshold_and_uncapped_expansion(fresh_rules):
    filters = query("flights")
    with pytest.raises(ValidationError, match="requires"):
        FlightSearchFilters(**{**filters.model_dump(), "starlink_premium": True})
    filters.starlink = StarlinkFilter.LIKELY
    filters.starlink_premium = True
    with pytest.raises(ValueError, match="uncapped"):
        SearchFlights().search(filters, top_n=1)
