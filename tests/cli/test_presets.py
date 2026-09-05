"""Presets round-trip through the shared CLI/MCP store without implicit searches."""

import json
import os
import stat
from datetime import date, timedelta

import pytest
from typer.testing import CliRunner

from fli.cli.main import app
from fli.models import Airport, LayoverRestrictions
from fli.presets import delete_preset, list_presets, load_preset, prepare_preset, save_preset
from tests.search.test_reliability import query

runner = CliRunner()


@pytest.fixture(autouse=True)
def isolated_presets(tmp_path, monkeypatch):
    monkeypatch.setenv("GLFI_PRESET_DIR", str(tmp_path / "presets"))
    monkeypatch.setattr(
        "fli.search.SearchFlights.search",
        lambda *args, **kwargs: pytest.fail("Unexpected network search"),
    )
    monkeypatch.setattr(
        "fli.search.SearchDates.search",
        lambda *args, **kwargs: pytest.fail("Unexpected network search"),
    )
    return tmp_path / "presets"


def test_save_inspect_replace_delete(isolated_presets):
    filters = query("flights")
    filters.layover_restrictions = LayoverRestrictions(exclude_airports=[Airport.ATL])
    saved = save_preset("work", filters, currency="USD")
    assert saved["success"]
    assert list_presets() == ["work"]
    assert load_preset("work").currency == "USD"
    if os.name == "posix":
        assert stat.S_IMODE((isolated_presets / "work.json").stat().st_mode) == 0o600
    with pytest.raises(ValueError, match="already exists"):
        save_preset("work", filters)
    save_preset("work", filters, replace=True, currency="EUR")
    assert load_preset("work").currency == "EUR"
    _, restored = prepare_preset("work")
    assert restored == filters
    delete_preset("work")
    assert list_presets() == []


@pytest.mark.parametrize("name", ["../escape", "a/b", "", "x" * 65, ".hidden"])
def test_names_cannot_escape_store(name):
    with pytest.raises(ValueError, match="names"):
        save_preset(name, query("flights"))


def test_symlinks_rejected(isolated_presets, tmp_path):
    isolated_presets.mkdir()
    target = tmp_path / "outside"
    target.write_text("untouched")
    (isolated_presets / "work.json").symlink_to(target)
    with pytest.raises(ValueError, match="Symlink"):
        save_preset("work", query("flights"), replace=True)
    assert list_presets() == []
    assert target.read_text() == "untouched"


def test_selected_flight_tokens_never_saved():
    from tests.search.test_expand_multi_leg import _result

    filters = query("flights")
    chosen = _result(Airport.JFK, Airport.LHR)
    chosen.booking_token = "private-session-token"
    filters.flight_segments[0].selected_flight = chosen
    save_preset("work", filters)
    assert "private-session-token" not in load_preset("work").model_dump_json()
    assert filters.flight_segments[0].selected_flight is chosen


@pytest.mark.parametrize("kind", ["flights", "dates"])
def test_first_date_override_shifts_trip_without_modifying_file(kind):
    filters = query(kind, round_trip=True)
    save_preset("work", filters)
    original = load_preset("work").model_dump_json()
    old = date.fromisoformat(filters.flight_segments[0].travel_date)
    new = (old + timedelta(days=7)).isoformat()
    _, shifted = prepare_preset(
        "work", **{"departure_date" if kind == "flights" else "start_date": new}
    )
    assert shifted.flight_segments[0].travel_date == new
    for before, after in zip(filters.flight_segments, shifted.flight_segments, strict=True):
        assert date.fromisoformat(after.travel_date) - date.fromisoformat(
            before.travel_date
        ) == timedelta(days=7)
    assert load_preset("work").model_dump_json() == original


def test_invalid_override_rejected():
    save_preset("work", query("flights", round_trip=True))
    with pytest.raises(ValueError):
        prepare_preset("work", return_date="2000-01-01")
    with pytest.raises(ValueError, match="date range"):
        prepare_preset("work", start_date="2030-01-01")


def test_old_preset_can_be_shown_and_reused(isolated_presets):
    save_preset("work", query("flights"))
    path = isolated_presets / "work.json"
    data = json.loads(path.read_text())
    data["filters"]["flight_segments"][0]["travel_date"] = "2000-01-01"
    path.write_text(json.dumps(data))
    assert load_preset("work")
    with pytest.raises(ValueError, match="past"):
        prepare_preset("work")
    prepare_preset("work", departure_date=(date.today() + timedelta(days=30)).isoformat())


def test_cli_save_alias_and_run(monkeypatch):
    day = (date.today() + timedelta(days=30)).isoformat()
    result = runner.invoke(
        app,
        [
            "save",
            "work",
            "--",
            "JAX",
            "IAD",
            day,
            "--starlink",
            "possible",
            "--starlink-premium",
            "--no-overnight-layovers",
            "--exclude-layover",
            "ATL,ORD",
            "--children",
            "1",
        ],
    )
    assert result.exit_code == 0, result.output
    stored = load_preset("work")
    assert stored.filters["starlink"] == "possible"
    assert stored.filters["starlink_premium"]
    assert stored.filters["passenger_info"]["children"] == 1
    captured = []
    monkeypatch.setattr(
        "fli.search.SearchFlights.search",
        lambda self, filters, **kwargs: captured.append(filters) or [],
    )
    result = runner.invoke(app, ["run", "work", "--format", "json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["success"]
    assert captured[0].layover_restrictions.exclude_airports == [Airport.ATL, Airport.ORD]
    assert captured[0].layover_restrictions.exclude_overnight


def test_date_preset_keeps_weekdays_and_duration_range(monkeypatch):
    day = (date.today() + timedelta(days=30)).isoformat()
    result = runner.invoke(
        app,
        [
            "save",
            "weekend",
            "--",
            "dates",
            "JAX",
            "JFK",
            "--from",
            day,
            "--to",
            day,
            "--round",
            "--min-duration",
            "3",
            "--max-duration",
            "4",
            "--friday",
            "--no-overnight-layovers",
        ],
    )
    assert result.exit_code == 0, result.output
    stored = load_preset("weekend")
    assert stored.durations == [3, 4]
    assert stored.weekdays == [4]
    captured = []
    monkeypatch.setattr(
        "fli.search.SearchDates.search",
        lambda self, filters, **kwargs: captured.append(kwargs) or [],
    )
    result = runner.invoke(app, ["run", "weekend", "--format", "json"])
    assert result.exit_code == 0, result.output
    assert captured[0]["durations"] == [3, 4]


def test_cli_management():
    save_preset("work", query("flights"))
    assert json.loads(runner.invoke(app, ["presets", "list", "--json"]).output)["presets"] == [
        "work"
    ]
    assert (
        json.loads(runner.invoke(app, ["presets", "show", "work"]).output)["preset"]["version"] == 1
    )
    assert runner.invoke(app, ["presets", "delete", "work"]).exit_code == 0
    result = runner.invoke(app, ["run", "missing", "--format", "json"])
    assert result.exit_code == 1
    assert not json.loads(result.output)["success"]


@pytest.mark.parametrize("mutation", ["segments", "unknown_filter", "selected"])
def test_malformed_preset_rejected_before_execution(isolated_presets, mutation):
    save_preset("work", query("flights"))
    path = isolated_presets / "work.json"
    data = json.loads(path.read_text())
    if mutation == "segments":
        data["filters"]["flight_segments"] = []
    elif mutation == "unknown_filter":
        data["filters"]["unsupported_magic"] = True
    else:
        data["filters"]["flight_segments"][0]["selected_flight"] = {"booking_token": "secret"}
    path.write_text(json.dumps(data))
    result = runner.invoke(app, ["run", "work", "--format", "json"])
    assert result.exit_code == 1
    assert not json.loads(result.output)["success"]


def test_concurrent_saves_do_not_overwrite_or_leave_partial_json():
    from concurrent.futures import ThreadPoolExecutor

    def save(currency):
        try:
            save_preset("work", query("flights"), currency=currency)
            return True
        except ValueError:
            return False

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(save, ["USD", "EUR"]))
    assert results.count(True) == 1
    assert load_preset("work").currency in ("USD", "EUR")
