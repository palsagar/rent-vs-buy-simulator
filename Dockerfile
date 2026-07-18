FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Copy dependency metadata first (for layer caching)
COPY pyproject.toml uv.lock README.md LICENSE ./

# Install dependencies only (cached until pyproject.toml or uv.lock change)
RUN uv sync --frozen --no-install-project --no-dev

# Copy source and install the local package
COPY src/ ./src/
RUN uv sync --frozen --no-dev

ENV PORT=8000
EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT}/api/health')" || exit 1

CMD /app/.venv/bin/uvicorn simulator.server:app --host 0.0.0.0 --port ${PORT}
