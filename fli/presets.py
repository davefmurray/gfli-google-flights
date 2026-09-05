"""Versioned, inspectable local search presets shared by CLI and MCP."""

import json
import os
import re
import tempfile
from datetime import date
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from fli.models import DateSearchFilters, FlightSearchFilters


class Preset(BaseModel):
    """A versioned search descriptor, without fares or session credentials."""

    model_config = ConfigDict(extra="forbid")

    version: Literal[1] = 1
    kind: Literal["flights", "dates"]
    filters: dict[str, Any]
    currency: str | None = None
    language: str | None = None
    country: str | None = None
    durations: list[Annotated[int, Field(ge=1, le=366)]] | None = Field(None, max_length=366)
    weekdays: list[Annotated[int, Field(ge=0, le=6)]] = Field(default_factory=list)
    sort_by_price: bool = False


def preset_directory() -> Path:
    """Resolve the shared preset directory without creating it."""
    override = os.environ.get("GLFI_PRESET_DIR")
    if override:
        return Path(override).expanduser()
    return (
        Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "glfi" / "presets"
    )


def _path(name: str) -> Path:
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}", name):
        raise ValueError("Preset names must be 1-64 letters, numbers, hyphens or underscores")
    path = preset_directory() / f"{name}.json"
    if path.is_symlink():
        raise ValueError("Symlink presets are not supported")
    return path


def save_preset(name: str, filters, *, replace: bool = False, **settings) -> dict:
    """Persist a validated search with private permissions and explicit replacement."""
    # Tokens and selected itineraries belong to a search session, never a preset.
    data = filters.model_dump(mode="json")
    for segment in data["flight_segments"]:
        segment["selected_flight"] = None
    preset = Preset(
        kind="dates" if isinstance(filters, DateSearchFilters) else "flights",
        filters=data,
        **settings,
    )
    path = _path(name)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    content = preset.model_dump_json(indent=2) + "\n"
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".preset-")
    try:
        with os.fdopen(fd, "w") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        if replace:
            os.replace(temporary, path)
        else:
            # Link a fully written file without overwriting another process's save.
            try:
                os.link(temporary, path)
            except FileExistsError:
                raise ValueError(
                    f"Preset '{name}' already exists; use replace explicitly"
                ) from None
    finally:
        Path(temporary).unlink(missing_ok=True)
    return {
        "success": True,
        "name": name,
        "path": str(path),
        "preset": preset.model_dump(mode="json"),
    }


def load_preset(name: str) -> Preset:
    """Read a descriptor without rejecting old dates needed for inspection."""
    path = _path(name)
    try:
        if path.stat().st_size > 1_000_000:
            raise ValueError("Preset exceeds the 1 MB size limit")
        return Preset.model_validate_json(path.read_text())
    except FileNotFoundError:
        raise ValueError(f"Preset '{name}' does not exist") from None
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise ValueError(f"Invalid preset '{name}'") from exc


def list_presets() -> list[str]:
    """List saved names without following symlinks."""
    return sorted(p.stem for p in preset_directory().glob("*.json") if not p.is_symlink())


def delete_preset(name: str) -> None:
    """Remove only the named preset."""
    path = _path(name)
    if not path.exists():
        raise ValueError(f"Preset '{name}' does not exist")
    path.unlink()


def prepare_preset(
    name: str, *, departure_date=None, return_date=None, start_date=None, end_date=None
):
    """Apply date overrides in memory, then revalidate before any network access."""
    preset = load_preset(name)
    data = preset.filters
    segments = data.get("flight_segments")
    if (
        not isinstance(segments, list)
        or not segments
        or any(
            not isinstance(segment, dict) or not isinstance(segment.get("travel_date"), str)
            for segment in segments
        )
    ):
        raise ValueError("Preset requires dated flight segments")
    model = FlightSearchFilters if preset.kind == "flights" else DateSearchFilters
    if set(data) - set(model.model_fields):
        raise ValueError("Preset contains unknown search filters")
    if any(segment.get("selected_flight") is not None for segment in segments):
        raise ValueError("Preset cannot contain a selected itinerary or booking session")
    if preset.kind == "flights":
        if start_date or end_date:
            raise ValueError("Flight presets use departure_date/return_date, not a date range")
        if departure_date:
            shift = date.fromisoformat(departure_date) - date.fromisoformat(
                segments[0]["travel_date"]
            )
            for segment in segments:
                segment["travel_date"] = (
                    date.fromisoformat(segment["travel_date"]) + shift
                ).isoformat()
        if return_date:
            if len(segments) != 2:
                raise ValueError("A return override requires a round-trip preset")
            segments[1]["travel_date"] = return_date
        filters = FlightSearchFilters.model_validate(data)
    else:
        if departure_date or return_date:
            raise ValueError("Date presets use start_date/end_date, not fixed flight dates")
        if start_date:
            shift = date.fromisoformat(start_date) - date.fromisoformat(data["from_date"])
            data["from_date"] = start_date
            data["to_date"] = (date.fromisoformat(data["to_date"]) + shift).isoformat()
            for segment in segments:
                segment["travel_date"] = (
                    date.fromisoformat(segment["travel_date"]) + shift
                ).isoformat()
        if end_date:
            data["to_date"] = end_date
        filters = DateSearchFilters.model_validate(data)
    return preset, filters


def execute_preset(preset: Preset, filters):
    """Run a prepared descriptor through the ordinary search engines."""
    from fli.search import SearchDates, SearchFlights

    locale = {key: getattr(preset, key) for key in ("currency", "language", "country")}
    if preset.kind == "flights":
        return SearchFlights().search(filters, **locale) or []
    results = (
        SearchDates().search(
            filters, **locale, **({"durations": preset.durations} if preset.durations else {})
        )
        or []
    )
    if preset.weekdays:
        results = [result for result in results if result.date[0].weekday() in preset.weekdays]
    if preset.sort_by_price:
        results.sort(key=lambda result: result.price)
    return results
