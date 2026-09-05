"""Inspect the offline, reviewed Starlink evidence catalog."""

import json
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from typing import Annotated

import typer
from rich.table import Table

from fli.cli.console import console
from fli.search.starlink import RULES


def starlink(
    as_json: Annotated[bool, typer.Option("--json", help="Show evidence catalog as JSON.")] = False,
):
    """Show reviewed Starlink fleet evidence and sources. Not flight confirmation."""
    today = datetime.now(timezone.utc).date()
    rows = [
        {
            **asdict(rule),
            "review_after": rule.checked_on + timedelta(days=90),
            "stale": not rule.checked_on <= today <= rule.checked_on + timedelta(days=90),
        }
        for rule in RULES
    ]
    if as_json:
        typer.echo(json.dumps({"basis": "fleet_inference", "rules": rows}, default=str, indent=2))
        return
    table = Table(title="Starlink fleet evidence (not flight-confirmed)")
    for name in ("Operator", "Aircraft", "Evidence", "Review By"):
        table.add_column(name)
    for row in rows:
        carrier = row["carrier"] + (
            f" / marketed {row['marketing_carrier']}" if row["marketing_carrier"] else ""
        )
        table.add_row(
            carrier,
            ", ".join(row["aircraft"]),
            "stale" if row["stale"] else row["status"],
            str(row["review_after"]),
        )
    console.print(table)
    for source in dict.fromkeys(row["source_url"] for row in rows):
        console.print(source, markup=False)
