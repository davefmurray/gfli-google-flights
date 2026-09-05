"""CLI error reporting helpers.

Turns ugly tracebacks into a one-line message for the user plus a
self-contained log file under ~/.glfi/logs/ that captures the full
traceback for debugging.
"""

from __future__ import annotations

import logging
import os
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

import typer

from fli.cli.console import console
from fli.search.exceptions import (
    SearchClientError,
    SearchConnectionError,
    SearchHTTPError,
    SearchTimeoutError,
    search_error_type,
)

_LOG_DIR = Path.home() / ".glfi" / "logs"
_logger = logging.getLogger("fli")


def _friendly_message(exc: BaseException) -> str:
    """Return the short, user-facing message for ``exc``."""
    if isinstance(exc, SearchTimeoutError):
        return f"Request timed out. {exc}"
    if isinstance(exc, SearchConnectionError):
        return f"Network error. {exc}"
    if isinstance(exc, SearchHTTPError):
        return f"Google Flights error. {exc}"
    if isinstance(exc, SearchClientError):
        return f"Search failed. {exc}"
    return f"Unexpected error: {exc.__class__.__name__}: {exc}"


def _write_log(exc: BaseException, *, command: str | None = None) -> Path | None:
    """Write a private traceback, without hiding the original error on write failure."""
    # Microsecond precision so rapid-fire errors (e.g. tests, parallel
    # legs) don't collide on the same filename and silently overwrite.
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    log_path = _LOG_DIR / f"glfi-error-{timestamp}.log"

    lines: list[str] = []
    lines.append(f"timestamp: {datetime.now(timezone.utc).isoformat()}")
    if command:
        lines.append(f"command: {command}")
    lines.append(f"argv: {sys.argv}")
    lines.append(f"error_type: {exc.__class__.__module__}.{exc.__class__.__name__}")
    lines.append(f"error_message: {exc}")
    lines.append("")
    lines.append("traceback:")
    lines.append("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))

    try:
        _LOG_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
        # Exclusive creation prevents following an existing file or symlink.
        fd = os.open(log_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as log:
            log.write("\n".join(lines))
    except OSError:
        return None
    return log_path


def report_cli_error(
    exc: BaseException,
    *,
    command: str | None = None,
    exit_code: int = 1,
) -> typer.Exit:
    """Print a clean message for ``exc``, write a log file, and return a ``typer.Exit``.

    Callers should ``raise`` the returned :class:`typer.Exit` so typer
    handles the exit code (and the original exception is suppressed from
    the user's terminal).
    """
    log_path = _write_log(exc, command=command)
    message = _friendly_message(exc)

    console.print(f"[red]Error:[/red] {message}")
    if log_path is not None:
        console.print(f"[dim]Full traceback written to {log_path}[/dim]")
    else:
        console.print("[dim]Could not write the diagnostic log.[/dim]")

    # Still log at debug for anyone who wired up python logging.
    _logger.debug("CLI error", exc_info=exc)

    return typer.Exit(exit_code)


def json_error_payload(
    exc: BaseException, *, command: str | None = None
) -> tuple[str, str, Path | None]:
    """Return ``(message, error_type, log_path)`` for JSON-mode error output."""
    log_path = _write_log(exc, command=command)
    if isinstance(exc, SearchClientError):
        return str(exc), search_error_type(exc), log_path
    return f"{exc.__class__.__name__}: {exc}", "unexpected_error", log_path
