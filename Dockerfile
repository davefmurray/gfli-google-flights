# Stage 1: dependency resolver
FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.11.28 /uv /bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock README.md LICENSE.txt NOTICE ./
COPY fli/ ./fli/

RUN uv sync --frozen --no-dev --no-cache --extra mcp --no-editable


# Stage 2: minimal runtime
FROM python:3.12-slim AS runtime

WORKDIR /app

# The non-editable install contains the source and packaged data.
COPY --from=builder /app/.venv /app/.venv

ENV PATH="/app/.venv/bin:$PATH"
ENV VIRTUAL_ENV="/app/.venv"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV HOST="0.0.0.0"
ENV PORT="8000"

EXPOSE 8000

# Run as non-root
RUN useradd --no-create-home --shell /bin/false appuser
USER appuser

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"

CMD ["glfi-mcp-http"]
