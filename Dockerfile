FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Copy dependency files first (for layer caching)
COPY pyproject.toml .
COPY uv.lock .

# Create venv and install dependencies
RUN uv venv /app/.venv && uv pip install --python /app/.venv/bin/python --no-cache .

# Copy application code
COPY src/ ./src/
COPY app.py .

# Expose Streamlit port
EXPOSE 8501

# Run Streamlit
CMD ["/app/.venv/bin/streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.enableCORS=false", "--server.enableXsrfProtection=false"]
