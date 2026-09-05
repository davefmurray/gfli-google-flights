"""Typed errors raised by the search client.

These exist so the CLI (and library consumers) can react to network
failures with a clear, user-facing message instead of a raw curl-cffi
traceback. They are intentionally light wrappers — the original
exception is kept as ``__cause__`` for logging.
"""

from __future__ import annotations


class SearchClientError(Exception):
    """Base class for errors talking to the Google Flights backend."""


class SearchTimeoutError(SearchClientError):
    """The request to Google Flights timed out before any data arrived."""


class SearchConnectionError(SearchClientError):
    """A network/DNS issue prevented us from reaching Google Flights."""


class SearchParseError(SearchClientError):
    """Google responded, but its result payload could not be decoded reliably."""


class SearchPriceUnavailableError(SearchClientError):
    """Matching flights exist, but Google did not provide a usable price."""


def search_error_type(exc: SearchClientError) -> str:
    """Stable categories shared by CLI JSON and MCP responses."""
    if isinstance(exc, SearchTimeoutError):
        return "timeout"
    if isinstance(exc, SearchConnectionError):
        return "connection_error"
    if isinstance(exc, SearchHTTPError):
        return "http_error"
    if isinstance(exc, SearchParseError):
        return "parse_error"
    if isinstance(exc, SearchPriceUnavailableError):
        return "price_unavailable"
    if isinstance(exc, SearchRejectedError):
        return "provider_rejected"
    if isinstance(exc, SearchUnsupportedError):
        return "unsupported_search"
    return "search_error"


class SearchHTTPError(SearchClientError):
    """Google Flights returned a non-2xx HTTP response."""

    def __init__(self, message: str, *, status_code: int | None = None):
        """Store the HTTP status alongside the message for richer logging."""
        super().__init__(message)
        self.status_code = status_code


class SearchRejectedError(SearchClientError):
    """Google answered HTTP 200 but declined to serve results.

    The response carries a ``wrb.fr`` row with no payload and an error
    code (13 = INTERNAL). Since 2026-08 ``GetShoppingResults`` requires an
    ``x-goog-batchexecute-bgr`` header signed by the page's own JavaScript
    over the exact request bytes, so a plain HTTP client always lands here.
    Without this error the caller saw an empty list and reported "no
    flights found", which is indistinguishable from a route with no service.
    """

    def __init__(self, code: int | None = None):
        """Record the numeric error code alongside the user-facing message."""
        self.code = code
        suffix = f" (error {code})" if code is not None else ""
        super().__init__(
            f"Google Flights declined the request{suffix} and returned no data. "
            "The endpoint may require browser state or request signing, or its "
            "request format may have changed. This is not an empty search result."
        )


class SearchUnsupportedError(SearchClientError):
    """The requested search cannot be served by the current transport.

    Distinct from an empty result: the query is well formed and Google
    would answer it in a browser, but the public search page carries no
    inline payload for it, so this client has nothing to read.
    """
