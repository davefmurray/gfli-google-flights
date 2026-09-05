"""Flight search CLI command."""

from typing import Annotated, Any

import typer

from fli.cli.enums import OutputFormat
from fli.cli.errors import json_error_payload, report_cli_error
from fli.cli.utils import (
    build_json_error_response,
    build_json_success_response,
    display_flight_results,
    emit_json,
    normalize_cli_date,
    normalize_cli_time_range,
    serialize_flight_result,
    validate_currency,
)
from fli.core import (
    build_flight_segments,
    parse_airlines,
    parse_alliances,
    parse_cabin_class,
    parse_emissions,
    parse_max_stops,
    parse_sort_by,
)
from fli.core.parsers import ParseError, resolve_airports
from fli.models import (
    BagsFilter,
    FlightSearchFilters,
    LayoverRestrictions,
    PassengerInfo,
)
from fli.search import SearchClientError, SearchFlights
from fli.search.links import search_url


def _search_flights_core(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: str | None = None,
    departure_window: str | tuple[int, int] | None = None,
    passengers: int = 1,
    children: int = 0,
    infants_in_seat: int = 0,
    infants_on_lap: int = 0,
    airlines: list[str] | None = None,
    cabin_class: str = "ECONOMY",
    max_stops: str = "ANY",
    sort_by: str = "CHEAPEST",
    exclude_basic_economy: bool = False,
    layover: list[str] | None = None,
    emissions: str = "ALL",
    checked_bags: int = 0,
    carry_on: bool = False,
    all_results: bool = True,
    output_format: OutputFormat = OutputFormat.TEXT,
    currency: str = "USD",
    language: str | None = None,
    country: str | None = None,
    exclude_airlines: list[str] | None = None,
    alliance: list[str] | None = None,
    exclude_alliance: list[str] | None = None,
    min_layover: int | None = None,
    max_layover: int | None = None,
    return_departure_window: str | tuple[int, int] | None = None,
    starlink: str = "any",
    starlink_premium: bool = False,
    exclude_layover: list[str] | None = None,
    no_overnight_layovers: bool = False,
    save_as: str | None = None,
    replace_preset: bool = False,
) -> None:
    """Core flight search functionality."""
    query: dict[str, Any] = {
        "origin": origin.upper(),
        "destination": destination.upper(),
        "departure_date": departure_date,
        "return_date": return_date,
        "departure_window": None,
        "airlines": None,
        "passengers": passengers,
        "children": children,
        "infants_in_seat": infants_in_seat,
        "infants_on_lap": infants_on_lap,
        "cabin_class": cabin_class.upper(),
        "max_stops": max_stops.upper(),
        "sort_by": sort_by.upper(),
        "starlink": starlink,
        "starlink_premium": starlink_premium,
        "min_layover": min_layover,
        "max_layover": max_layover,
        "exclude_layover": exclude_layover,
        "no_overnight_layovers": no_overnight_layovers,
    }

    try:
        departure_date = normalize_cli_date(departure_date)
        return_date = normalize_cli_date(return_date)
        departure_window = normalize_cli_time_range(departure_window)
        return_departure_window = normalize_cli_time_range(return_departure_window)
        query["return_departure_window"] = (
            f"{return_departure_window[0]}-{return_departure_window[1]}"
            if return_departure_window
            else None
        )
        query["departure_date"] = departure_date
        query["return_date"] = return_date
        query["departure_window"] = (
            f"{departure_window[0]}-{departure_window[1]}" if departure_window else None
        )

        # Parse parameters using shared utilities
        origin_airport = resolve_airports(origin)
        destination_airport = resolve_airports(destination)
        query["origin"] = ",".join(a.name for a in origin_airport)
        query["destination"] = ",".join(a.name for a in destination_airport)
        seat_type = parse_cabin_class(cabin_class)
        stops = parse_max_stops(max_stops)
        parsed_airlines = parse_airlines(airlines)
        parsed_exclude_airlines = parse_airlines(exclude_airlines)
        parsed_alliances = parse_alliances(alliance)
        parsed_exclude_alliances = parse_alliances(exclude_alliance)
        query["airlines"] = (
            [airline.name.lstrip("_") for airline in parsed_airlines] if parsed_airlines else None
        )
        query["exclude_airlines"] = (
            [a.name.lstrip("_") for a in parsed_exclude_airlines]
            if parsed_exclude_airlines
            else None
        )
        query["alliances"] = [a.value for a in parsed_alliances] if parsed_alliances else None
        query["exclude_alliances"] = (
            [a.value for a in parsed_exclude_alliances] if parsed_exclude_alliances else None
        )
        sort = parse_sort_by(sort_by)
        emissions_filter = parse_emissions(emissions)

        # Build time restrictions from tuple
        time_restrictions = None
        if departure_window:
            from fli.models import TimeRestrictions

            time_restrictions = TimeRestrictions(
                earliest_departure=departure_window[0],
                latest_departure=departure_window[1],
            )

        # Create flight segments using shared builder
        from fli.models import TimeRestrictions

        return_time_restrictions = (
            TimeRestrictions(
                earliest_departure=return_departure_window[0],
                latest_departure=return_departure_window[1],
            )
            if return_departure_window
            else False
        )
        segments, trip_type = build_flight_segments(
            origin=origin_airport,
            destination=destination_airport,
            departure_date=departure_date,
            return_date=return_date,
            time_restrictions=time_restrictions,
            return_time_restrictions=return_time_restrictions,
        )

        # Parse layover constraints (airports, min duration, max duration).
        layover_restrictions = None
        layover_airports = resolve_airports(",".join(layover)) if layover else None
        if (
            layover_airports
            or min_layover is not None
            or max_layover is not None
            or exclude_layover
            or no_overnight_layovers
        ):
            layover_restrictions = LayoverRestrictions(
                airports=layover_airports,
                exclude_airports=resolve_airports(",".join(exclude_layover))
                if exclude_layover
                else None,
                exclude_overnight=no_overnight_layovers,
                min_duration=min_layover,
                max_duration=max_layover,
            )

        # Build bags filter
        bags_filter = None
        if checked_bags > 0 or carry_on:
            bags_filter = BagsFilter(checked_bags=checked_bags, carry_on=carry_on)

        # Create search filters
        filters = FlightSearchFilters(
            trip_type=trip_type,
            passenger_info=PassengerInfo(
                adults=passengers,
                children=children,
                infants_in_seat=infants_in_seat,
                infants_on_lap=infants_on_lap,
            ),
            flight_segments=segments,
            stops=stops,
            seat_type=seat_type,
            airlines=parsed_airlines,
            airlines_exclude=parsed_exclude_airlines,
            alliances=parsed_alliances,
            alliances_exclude=parsed_exclude_alliances,
            sort_by=sort,
            exclude_basic_economy=exclude_basic_economy,
            layover_restrictions=layover_restrictions,
            emissions=emissions_filter,
            bags=bags_filter,
            show_all_results=all_results,
            starlink=starlink,
            starlink_premium=starlink_premium,
        )

        if save_as is not None:
            from fli.presets import save_preset

            saved = save_preset(
                save_as,
                filters,
                replace=replace_preset,
                currency=currency,
                language=language,
                country=country,
            )
            if output_format == OutputFormat.JSON:
                emit_json(saved)
            else:
                typer.echo(f"Saved preset '{save_as}' (no search performed).")
            return

        # Perform search; `currency` doubles as Google's `curr=` URL param so
        # results come back priced in the requested currency.
        booking_url = search_url(filters, currency=currency, language=language, country=country)
        search_client = SearchFlights()
        results = search_client.search(
            filters,
            currency=currency,
            language=language,
            country=country,
        )

        if not results:
            if output_format == OutputFormat.JSON:
                emit_json(
                    build_json_success_response(
                        search_type="flights",
                        trip_type=trip_type,
                        query=query,
                        results_key="flights",
                        results=[],
                        booking_url=booking_url,
                    )
                )
                return

            typer.echo("No flights found.")
            raise typer.Exit(1)

        # Build per-flight booking deep-links (tfs; never raises).
        booking_urls = [
            search_client.build_flight_booking_url(
                result,
                currency=currency,
                language=language,
                country=country,
                seat_type=seat_type,
                passenger_info=filters.passenger_info,
            )
            for result in results
        ]

        if output_format == OutputFormat.JSON:
            emit_json(
                build_json_success_response(
                    search_type="flights",
                    trip_type=trip_type,
                    query=query,
                    results_key="flights",
                    results=[
                        serialize_flight_result(result, default_currency=currency, booking_url=burl)
                        for result, burl in zip(results, booking_urls, strict=False)
                    ],
                    booking_url=booking_url,
                )
            )
            return

        display_flight_results(
            results,
            trip_type=trip_type,
            default_currency=currency,
            booking_url=booking_url,
            booking_urls=booking_urls,
        )

    except ParseError as e:
        if output_format == OutputFormat.JSON:
            emit_json(
                build_json_error_response(
                    search_type="flights",
                    message=str(e),
                    query=query,
                )
            )
            raise typer.Exit(1) from e

        typer.echo(f"Error: {str(e)}")
        raise typer.Exit(1) from e
    except (AttributeError, ValueError) as e:
        if output_format == OutputFormat.JSON:
            emit_json(
                build_json_error_response(
                    search_type="flights",
                    message=str(e),
                    error_type="search_error",
                    query=query,
                )
            )
            raise typer.Exit(1) from e

        typer.echo(f"Error: {str(e)}")
        raise typer.Exit(1) from e
    except SearchClientError as e:
        if output_format == OutputFormat.JSON:
            message, error_type, log_path = json_error_payload(e, command="flights")
            payload = build_json_error_response(
                search_type="flights",
                message=message,
                error_type=error_type,
                query=query,
            )
            payload["error"]["log_path"] = str(log_path) if log_path else None
            emit_json(payload)
            raise typer.Exit(1) from e
        raise report_cli_error(e, command="flights") from e
    except Exception as e:  # noqa: BLE001 — fall back to clean reporting
        if output_format == OutputFormat.JSON:
            message, error_type, log_path = json_error_payload(e, command="flights")
            payload = build_json_error_response(
                search_type="flights",
                message=message,
                error_type=error_type,
                query=query,
            )
            payload["error"]["log_path"] = str(log_path) if log_path else None
            emit_json(payload)
            raise typer.Exit(1) from e
        raise report_cli_error(e, command="flights") from e


def flights(
    origin: Annotated[
        str, typer.Argument(help="Departure IATA codes, comma-separated (e.g., JFK,LGA)")
    ],
    destination: Annotated[
        str, typer.Argument(help="Arrival IATA codes, comma-separated (e.g., LHR,CDG)")
    ],
    departure_date: Annotated[str, typer.Argument(help="Travel date (YYYY-MM-DD)")],
    return_date: Annotated[
        str | None,
        typer.Option(
            "--return",
            "-r",
            help="Return date (YYYY-MM-DD)",
        ),
    ] = None,
    save_as: Annotated[
        str | None, typer.Option("--save", help="Save a preset without searching.")
    ] = None,
    replace_preset: Annotated[
        bool, typer.Option("--replace-preset", help="Allow replacing an existing preset.")
    ] = False,
    starlink_premium: Annotated[
        bool,
        typer.Option(
            "--starlink-premium",
            help="Compare with cheapest same-search fare; requires --starlink likely/possible.",
        ),
    ] = False,
    exclude_layover: Annotated[
        list[str] | None,
        typer.Option(
            "--exclude-layover", help="Exclude connecting airports; repeat or comma-separate codes."
        ),
    ] = None,
    no_overnight_layovers: Annotated[
        bool,
        typer.Option(
            "--no-overnight-layovers",
            help="Exclude connections crossing local midnight, not overnight flights.",
        ),
    ] = False,
    starlink: Annotated[
        str,
        typer.Option(
            "--starlink",
            help="Starlink fleet evidence on EVERY leg: likely, possible, any. Not confirmed.",
        ),
    ] = "any",
    departure_window: Annotated[
        str | None,
        typer.Option(
            "--time",
            "-t",
            help="Departure time window in 24h format (e.g., 6-20)",
        ),
    ] = None,
    return_departure_window: Annotated[
        str | None,
        typer.Option(
            "--return-time", "-T", help="Return departure hours (e.g., 16-23); requires --return"
        ),
    ] = None,
    passengers: Annotated[
        int,
        typer.Option(
            "--passengers",
            "--adults",
            "-p",
            help="Number of adult passengers",
            min=1,
        ),
    ] = 1,
    children: Annotated[
        int,
        typer.Option(
            "--children",
            help="Number of children",
            min=0,
        ),
    ] = 0,
    infants_in_seat: Annotated[
        int,
        typer.Option(
            "--infants-in-seat",
            help="Number of infants in seat",
            min=0,
        ),
    ] = 0,
    infants_on_lap: Annotated[
        int,
        typer.Option(
            "--infants-on-lap",
            help="Number of infants on lap",
            min=0,
        ),
    ] = 0,
    airlines: Annotated[
        list[str] | None,
        typer.Option(
            "--airlines",
            "-a",
            help="Airline IATA codes (e.g., BA,KL or repeated --airlines BA --airlines KL)",
        ),
    ] = None,
    cabin_class: Annotated[
        str,
        typer.Option(
            "--class",
            "-c",
            help="Cabin class (ECONOMY, PREMIUM_ECONOMY, BUSINESS, FIRST)",
        ),
    ] = "ECONOMY",
    max_stops: Annotated[
        str,
        typer.Option(
            "--stops",
            "-s",
            help="Maximum stops (ANY, 0 for non-stop, 1 for one stop, 2+ for two stops)",
        ),
    ] = "ANY",
    sort_by: Annotated[
        str,
        typer.Option(
            "--sort",
            "-o",
            help="Sort by: TOP_FLIGHTS, BEST, CHEAPEST, DEPARTURE_TIME,"
            " ARRIVAL_TIME, DURATION, EMISSIONS",
        ),
    ] = "CHEAPEST",
    exclude_basic_economy: Annotated[
        bool,
        typer.Option(
            "--exclude-basic",
            "-e",
            help="Exclude basic economy fares",
        ),
    ] = False,
    layover: Annotated[
        list[str] | None,
        typer.Option(
            "--layover",
            "-l",
            help="Restrict layover to these airports (e.g., -l ORD -l MDW)",
        ),
    ] = None,
    emissions: Annotated[
        str,
        typer.Option(
            "--emissions",
            help="Filter by emissions level (ALL, LESS)",
        ),
    ] = "ALL",
    checked_bags: Annotated[
        int,
        typer.Option(
            "--bags",
            "-b",
            help="Number of checked bags to include in price (0, 1, or 2)",
            min=0,
            max=2,
        ),
    ] = 0,
    carry_on: Annotated[
        bool,
        typer.Option(
            "--carry-on",
            help="Include carry-on bag fee in price",
        ),
    ] = False,
    all_results: Annotated[
        bool,
        typer.Option(
            "--all/--no-all",
            help="Show all available results (default) or only ~30 curated results",
        ),
    ] = True,
    output_format: Annotated[
        OutputFormat,
        typer.Option(
            "--format",
            help="Output format: text or json",
            case_sensitive=False,
        ),
    ] = OutputFormat.TEXT,
    currency: Annotated[
        str,
        typer.Option(
            "--currency",
            callback=validate_currency,
            help="Currency code (USD, EUR, GBP, JPY...). Passed to Google as `curr=`.",
        ),
    ] = "USD",
    language: Annotated[
        str | None,
        typer.Option(
            "--language",
            help="Optional BCP-47 language code (e.g., 'en-GB') passed to Google as `hl=`.",
        ),
    ] = None,
    country: Annotated[
        str | None,
        typer.Option(
            "--country",
            help="Optional ISO 3166-1 alpha-2 country code (e.g., 'GB') passed to Google as `gl=`.",
        ),
    ] = None,
    exclude_airlines: Annotated[
        list[str] | None,
        typer.Option(
            "--exclude-airlines",
            "-A",
            help=(
                "Airline IATA codes to EXCLUDE from results (e.g., BA,KL "
                "or repeated --exclude-airlines BA --exclude-airlines KL)."
            ),
        ),
    ] = None,
    alliance: Annotated[
        list[str] | None,
        typer.Option(
            "--alliance",
            help=(
                "Restrict results to one or more airline alliances: "
                "ONEWORLD, SKYTEAM, STAR_ALLIANCE (comma-separated allowed)."
            ),
        ),
    ] = None,
    exclude_alliance: Annotated[
        list[str] | None,
        typer.Option(
            "--exclude-alliance",
            help="Alliance names to EXCLUDE (ONEWORLD, SKYTEAM, STAR_ALLIANCE).",
        ),
    ] = None,
    min_layover: Annotated[
        int | None,
        typer.Option(
            "--min-layover",
            help="Minimum layover duration in minutes (multi-stop trips only).",
            min=1,
        ),
    ] = None,
    max_layover: Annotated[
        int | None,
        typer.Option(
            "--max-layover",
            help="Maximum layover duration in minutes (multi-stop trips only).",
            min=1,
        ),
    ] = None,
):
    """Search for flights on a specific date.

    Example:
        glfi flights JFK LHR 2026-10-25 --time 6-20 --airlines BA,KL --stops NON_STOP
        glfi flights JFK LHR 2026-10-25 --format json
        glfi flights JFK LHR 2026-10-25 --exclude-basic
        glfi flights JFK LAX 2026-10-25 --bags 1 --carry-on
        glfi flights JFK LAX 2026-10-25 --emissions LESS
        glfi flights JFK LAX 2026-10-25 --all
        glfi flights JFK FRA 2026-10-25 --alliance ONEWORLD
        glfi flights JFK LAX 2026-10-25 --exclude-airlines DL
        glfi flights BUF ATH 2026-10-25 --min-layover 120

    """
    _search_flights_core(
        origin=origin,
        destination=destination,
        departure_date=departure_date,
        return_date=return_date,
        departure_window=departure_window,
        return_departure_window=return_departure_window,
        starlink=starlink,
        starlink_premium=starlink_premium,
        exclude_layover=exclude_layover,
        no_overnight_layovers=no_overnight_layovers,
        save_as=save_as,
        replace_preset=replace_preset,
        passengers=passengers,
        children=children,
        infants_in_seat=infants_in_seat,
        infants_on_lap=infants_on_lap,
        airlines=airlines,
        cabin_class=cabin_class,
        max_stops=max_stops,
        sort_by=sort_by,
        exclude_basic_economy=exclude_basic_economy,
        layover=layover,
        emissions=emissions,
        checked_bags=checked_bags,
        carry_on=carry_on,
        all_results=all_results,
        output_format=output_format,
        currency=currency,
        language=language,
        country=country,
        exclude_airlines=exclude_airlines,
        alliance=alliance,
        exclude_alliance=exclude_alliance,
        min_layover=min_layover,
        max_layover=max_layover,
    )
