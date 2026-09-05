"""CLI module for the fli package."""


def cli():
    """Keep doctor usable even when search configuration prevents imports."""
    import sys

    if sys.argv[1:2] == ["doctor"]:
        import typer

        from fli.cli.doctor import doctor

        sys.argv.pop(1)
        typer.run(doctor)
    else:
        from fli.cli.main import cli as main_cli

        main_cli()


__all__ = ["cli"]
