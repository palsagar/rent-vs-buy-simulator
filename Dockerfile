FROM python:3.12-slim

# Install system dependencies including Chromium for Kaleido (PDF chart rendering)
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Copy project files needed for install
COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src/ ./src/

# Create venv and install the package (hatchling needs src/ to build the wheel)
RUN uv venv /app/.venv && uv pip install --python /app/.venv/bin/python --no-cache .

# Expose Streamlit port
EXPOSE 8501

# Run Streamlit
CMD ["/app/.venv/bin/streamlit", "run", "src/simulator/app.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.enableCORS=false", "--server.enableXsrfProtection=false"]
