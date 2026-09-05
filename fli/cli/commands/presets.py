"""Save, inspect and replay searches without a scheduler or account."""

from typing import Annotated

import typer

from fli.cli.enums import OutputFormat
from fli.cli.utils import (
    display_date_results,
    display_flight_results,
    emit_json,
    serialize_date_result,
    serialize_flight_result,
)
from fli.presets import delete_preset, execute_preset, list_presets, load_preset, prepare_preset
from fli.search import SearchClientError, SearchFlights
from fli.search.links import search_url

presets_app = typer.Typer(help="List, inspect or remove local saved searches.")


def save(
    name: Annotated[str, typer.Argument(help="Local preset name.")],
    search_args: Annotated[
        list[str],
        typer.Argument(help="Search arguments after --; optionally begin with dates or flights."),
    ],
):
    """Save a search: glfi save work -- JAX IAD 2026-10-15 --starlink possible."""
    from typer.main import get_command

    from fli.cli.main import app

    args = list(search_args)
    if args and args[0] == "--":
        args.pop(0)
    if not args or args[0] not in ("flights", "dates"):
        args.insert(0, "flights")
    if any(arg == "--save" or arg.startswith("--save=") for arg in args):
        raise typer.BadParameter("Use the preset name argument, not a nested --save")
    get_command(app).main(args=[*args, "--save", name], standalone_mode=False)


@presets_app.command("list")
def list_saved(as_json: Annotated[bool, typer.Option("--json")] = False):
    """List local preset names."""
    names = list_presets()
    if as_json:
        emit_json({"success": True, "presets": names})
    else:
        typer.echo("\n".join(names) if names else "No saved presets.")


@presets_app.command("show")
def show_saved(name: str):
    """Show a preset's stored JSON, including expired travel dates."""
    try:
        emit_json({"name": name, "preset": load_preset(name).model_dump(mode="json")})
    except (ValueError, OSError) as exc:
        raise typer.BadParameter(str(exc)) from exc


@presets_app.command("delete")
def delete_saved(name: str):
    """Delete exactly one named local preset."""
    try:
        delete_preset(name)
        typer.echo(f"Deleted preset '{name}'.")
    except (ValueError, OSError) as exc:
        raise typer.BadParameter(str(exc)) from exc


def run(
    name: str,
    departure_date: Annotated[str | None, typer.Option("--date")] = None,
    return_date: Annotated[str | None, typer.Option("--return")] = None,
    start_date: Annotated[str | None, typer.Option("--from")] = None,
    end_date: Annotated[str | None, typer.Option("--to")] = None,
    output_format: Annotated[OutputFormat, typer.Option("--format", "-f")] = OutputFormat.TEXT,
):
    """Run a saved search; changing its first date shifts the other saved dates."""
    try:
        preset, filters = prepare_preset(
            name,
            departure_date=departure_date,
            return_date=return_date,
            start_date=start_date,
            end_date=end_date,
        )
        results = execute_preset(preset, filters)
        locale = {key: getattr(preset, key) for key in ("currency", "language", "country")}
        currency = preset.currency or "USD"
        if preset.kind == "flights":
            links = [
                SearchFlights().build_flight_booking_url(
                    result,
                    **locale,
                    seat_type=filters.seat_type,
                    passenger_info=filters.passenger_info,
                )
                for result in results
            ]
            serialized = [
                serialize_flight_result(result, default_currency=currency, booking_url=link)
                for result, link in zip(results, links, strict=True)
            ]
            if output_format == OutputFormat.TEXT and results:
                display_flight_results(
                    results,
                    trip_type=filters.trip_type,
                    default_currency=currency,
                    booking_url=search_url(filters, **locale),
                    booking_urls=links,
                )
        else:
            origin = ",".join(
                airport[0].name for airport in filters.flight_segments[0].departure_airport
            )
            destination = ",".join(
                airport[0].name for airport in filters.flight_segments[0].arrival_airport
            )
            kwargs = dict(
                default_currency=currency,
                origin=origin,
                destination=destination,
                search_filters=filters,
                **locale,
            )
            serialized = [
                serialize_date_result(result, filters.trip_type, **kwargs) for result in results
            ]
            if output_format == OutputFormat.TEXT and results:
                display_date_results(results, filters.trip_type, **kwargs)
        if output_format == OutputFormat.JSON:
            emit_json(
                {
                    "success": True,
                    "preset": name,
                    "trip_type": filters.trip_type.name,
                    "starlink_filter": filters.starlink,
                    "count": len(results),
                    preset.kind: serialized,
                }
            )
        elif not results:
            typer.echo("No flights found.")
            raise typer.Exit(1)
    except (ValueError, OSError, KeyError, SearchClientError) as exc:
        from fli.search.exceptions import search_error_type

        if output_format == OutputFormat.JSON:
            emit_json(
                {
                    "success": False,
                    "error": str(exc),
                    "error_type": search_error_type(exc)
                    if isinstance(exc, SearchClientError)
                    else "validation",
                }
            )
        else:
            typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1) from exc
