#!/usr/bin/env python3
"""CLI entry point for GLFI."""

import sys
from importlib.metadata import version
from typing import Annotated

import typer

from fli.cli.commands.airports import airports
from fli.cli.commands.dates import dates
from fli.cli.commands.flights import flights
from fli.cli.commands.multi import multi

app = typer.Typer(
    help="GLFI: flight search for your terminal and AI assistants.",
    add_completion=True,
)

# Register commands
app.command(name="airports")(airports)
app.command(name="dates")(dates)
app.command(name="flights")(flights)
app.command(name="multi")(multi)


def _show_version(value: bool) -> None:
    """Print the installed distribution version and exit."""
    if value:
        typer.echo(f"glfi {version('glfi')}")
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    show_version: Annotated[
        bool,
        typer.Option("--version", callback=_show_version, is_eager=True, help="Show version."),
    ] = False,
):
    """Search for flights using Google Flights data.

    If no command is provided, show help.
    """
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()


def cli():
    """Entry point for the CLI that handles default command."""
    args = sys.argv[1:]
    if not args:
        sys.argv.append("--help")
        args.append("--help")

    # If the first argument isn't a command, treat as flights search
    if args[0] not in [
        "airports",
        "dates",
        "flights",
        "multi",
        "--help",
        "--version",
        "-h",
        "--show-completion",
        "--install-completion",
    ]:
        sys.argv.insert(1, "flights")

    app()


if __name__ == "__main__":
    cli()
