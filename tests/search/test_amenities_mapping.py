"""Verified amenity fields are independent of each other and seat quality."""

import pytest

from fli.search._decoders import _parse_amenities


@pytest.mark.parametrize(
    "tier,wifi,label",
    [
        (0, False, None),
        (1, True, "available"),
        (2, True, "free"),
        (3, True, "paid"),
        (4, True, "available"),
    ],
)
def test_wifi_tier(tier, wifi, label):
    slots = [None] * 12
    slots[11] = tier
    result = _parse_amenities(slots)
    assert result.wifi is wifi
    assert result.wifi_type == label
    assert result.power is None


@pytest.mark.parametrize(
    "index,label,usb",
    [
        (1, "plug_usb", True),
        (2, "some_seats_plug_usb", True),
        (3, "plug", False),
        (4, "some_seats_plug", False),
        (5, "usb", True),
        (6, "some_seats_usb", True),
    ],
)
def test_power_variants(index, label, usb):
    slots = [None] * 12
    slots[index] = 1
    result = _parse_amenities(slots)
    assert result.power is True
    assert result.power_type == label
    assert result.usb_power is usb
    assert result.wifi is None


@pytest.mark.parametrize(
    "index,label,in_seat,on_demand",
    [(10, "streaming", False, False), (9, "on_demand", True, True), (8, "live_tv", True, False)],
)
def test_video_variants(index, label, in_seat, on_demand):
    slots = [None] * 12
    slots[index] = 1
    result = _parse_amenities(slots)
    assert result.video_type == label
    assert result.in_seat_video is in_seat
    assert result.on_demand_video is on_demand


def test_reported_precedence_and_seat_independence():
    slots = [None] + [1] * 11
    result = _parse_amenities(slots, 3)
    assert result.power_type == "plug_usb"
    assert result.video_type == "streaming"
    assert result.legroom_rating == 3
    assert result.wifi_type == "available"


def test_missing_signals_remain_unknown():
    assert _parse_amenities(None) is None
    assert _parse_amenities([None] * 12) is None
    assert _parse_amenities([None] * 12, 5).wifi is None
