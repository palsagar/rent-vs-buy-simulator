"""FastAPI server for the rent-vs-buy simulator.

Serves the static frontend and the JSON API wrapping the simulation
engine. Mirrors the structure of the author's other apps (health
endpoint, no-cache middleware for static assets during development).

Run with: uv run uvicorn simulator.server:app --reload
"""

from pathlib import Path
from typing import Annotated, Any

from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from .api import config_from_dict, monte_carlo_payload, simulate_payload
from .regions import list_regions


class NoCacheMiddleware(BaseHTTPMiddleware):
    """Disable browser caching for JS/CSS/HTML during development."""

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        """Add no-cache headers to static asset responses."""
        response = await call_next(request)
        path = request.url.path
        if path.endswith((".js", ".css", ".html")) or path == "/":
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
        return response


app = FastAPI(title="Rent or Buy?")
app.add_middleware(NoCacheMiddleware)


@app.get("/api/health")
def health() -> JSONResponse:
    """Liveness probe used by Docker healthchecks and Coolify."""
    return JSONResponse({"status": "ok"})


@app.get("/api/regions")
def regions() -> list[dict[str, Any]]:
    """List region preset bundles (ADR-0007)."""
    return list_regions()


@app.post("/api/simulate")
def simulate(payload: Annotated[dict[str, Any], Body(...)]) -> dict[str, Any]:
    """Run the deterministic engine; 422 on invalid configuration."""
    try:
        config = config_from_dict(payload)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return simulate_payload(config)


@app.post("/api/monte-carlo")
def monte_carlo(payload: Annotated[dict[str, Any], Body(...)]) -> dict[str, Any]:
    """Run the knobless Monte Carlo analysis; 422 on invalid config."""
    try:
        config = config_from_dict(payload)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return monte_carlo_payload(config)


_STATIC_DIR = Path(__file__).parent / "static"
app.mount(
    "/",
    StaticFiles(directory=_STATIC_DIR, html=True, check_dir=False),
    name="static",
)
