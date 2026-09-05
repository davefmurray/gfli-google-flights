"""Import-light local diagnostics; provider access is always opt-in."""

import importlib.metadata
import importlib.util
import json
import math
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from typing import Annotated

import typer


def diagnose(*, check_provider=False):
    """Return redacted local checks and an optional bounded provider probe."""
    checks = []

    def add(name, status, detail):
        checks.append({"name": name, "status": status, "detail": detail})

    add(
        "python",
        "ok" if (3, 10) <= sys.version_info[:2] <= (3, 13) else "error",
        sys.version.split()[0],
    )
    try:
        add("distribution", "ok", f"glfi {importlib.metadata.version('glfi')}")
    except importlib.metadata.PackageNotFoundError:
        add("distribution", "error", "GLFI distribution metadata missing; reinstall GLFI.")
    try:
        timeout = float(os.environ.get("GLFI_TIMEOUT", "60"))
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError
        add("search_configuration", "ok", "Timeout is valid; cookie value is not displayed.")
        valid_config = True
    except ValueError:
        add("search_configuration", "error", "GLFI_TIMEOUT must be a finite positive number.")
        valid_config = False
    for package in ("curl_cffi", "typer", "pydantic"):
        add(
            package,
            "ok" if importlib.util.find_spec(package) else "error",
            "Installed" if importlib.util.find_spec(package) else "Missing; reinstall GLFI.",
        )
    if importlib.util.find_spec("fastmcp") and importlib.util.find_spec("mcp"):
        try:
            probe = subprocess.run(
                [sys.executable, "-c", "from fli.mcp.server import CONFIG, mcp"],
                capture_output=True,
                timeout=20,
            )
            add(
                "mcp",
                "ok" if probe.returncode == 0 else "error",
                "Dependencies and configuration import successfully; no server started."
                if probe.returncode == 0
                else "MCP import/configuration failed; check GLFI_MCP_ settings "
                "and reinstall glfi[mcp].",
            )
        except (OSError, subprocess.TimeoutExpired):
            add("mcp", "error", "MCP import check could not finish within 20 seconds.")
    else:
        add(
            "mcp",
            "warning",
            "Optional MCP dependencies missing; install glfi[mcp] for MCP commands.",
        )
    if valid_config:
        try:
            from fli.search.starlink import RULES

            today = datetime.now(timezone.utc).date()
            stale = [
                rule
                for rule in RULES
                if not rule.checked_on <= today <= rule.checked_on + timedelta(days=90)
            ]
            add(
                "starlink_evidence",
                "warning" if stale or not RULES else "ok",
                f"{len(stale)} stale of {len(RULES)} rules; inspect glfi starlink "
                "for sources and review dates.",
            )
        except Exception:
            add("starlink_evidence", "error", "Unable to load evidence catalog; reinstall GLFI.")
    else:
        add("starlink_evidence", "warning", "Not loaded until search configuration is fixed.")
    from fli.presets import list_presets, load_preset, preset_directory

    try:
        names = list_presets()
        for name in names:
            load_preset(name)
        add(
            "presets",
            "ok",
            f"{len(names)} readable presets at {preset_directory()}; no files modified.",
        )
    except (ValueError, OSError):
        add(
            "presets",
            "error",
            "Preset file is unreadable or malformed; inspect glfi presets show NAME.",
        )
    if check_provider and valid_config:
        try:
            from fli.core import build_flight_segments
            from fli.models import Airport, FlightSearchFilters, MaxStops, PassengerInfo
            from fli.search import SearchFlights

            segments, trip_type = build_flight_segments(
                origin=[Airport.JAX],
                destination=[Airport.JFK],
                departure_date=(datetime.now(timezone.utc).date() + timedelta(days=30)).isoformat(),
            )
            results = SearchFlights().search(
                FlightSearchFilters(
                    flight_segments=segments,
                    trip_type=trip_type,
                    passenger_info=PassengerInfo(),
                    stops=MaxStops.NON_STOP,
                ),
                currency="USD",
            )
            add(
                "provider",
                "ok",
                f"Search response decoded: {len(results or [])} itineraries. "
                "Not an availability guarantee.",
            )
        except Exception as exc:
            add(
                "provider",
                "error",
                f"Provider check failed ({type(exc).__name__}); not proof of no flights.",
            )
    else:
        add(
            "provider",
            "skipped",
            "Not contacted. Use --check-provider for a bounded live search."
            if not check_provider
            else "Fix search configuration before checking the provider.",
        )
    return {"success": not any(check["status"] == "error" for check in checks), "checks": checks}


def doctor(
    as_json: Annotated[bool, typer.Option("--json", help="Machine-readable diagnostics.")] = False,
    check_provider: Annotated[
        bool,
        typer.Option(
            "--check-provider",
            help="Opt in to one live nonstop search, with normal timeout/retries.",
        ),
    ] = False,
):
    """Check local installation, MCP configuration, presets and Starlink evidence."""
    result = diagnose(check_provider=check_provider)
    if as_json:
        typer.echo(json.dumps(result, indent=2))
    else:
        for check in result["checks"]:
            typer.echo(f"{check['status'].upper():7} {check['name']}: {check['detail']}")
    if not result["success"]:
        raise typer.Exit(1)
