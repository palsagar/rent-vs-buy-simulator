FROM python:3.12-slim

# Install system dependencies including Chromium for Kaleido (PDF chart rendering)
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    && rm -rf /var/lib/apt/lists/*

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

# Expose Streamlit port
EXPOSE 8501

# Run Streamlit
CMD ["/app/.venv/bin/streamlit", "run", "src/simulator/app.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.enableCORS=false", "--server.enableXsrfProtection=false"]
