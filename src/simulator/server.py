"""FastAPI server for the rent-vs-buy simulator.

Serves the static frontend and the JSON API wrapping the simulation
engine. Mirrors the structure of the author's other apps (health
endpoint, no-cache middleware for static assets during development).

Run with: uv run uvicorn simulator.server:app --reload
"""

import os
import threading
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

# Content-Security-Policy: same-origin by default, plus the Plotly CDN for
# scripts and inline styles for the HTML's style="..." attributes. frame
# ancestors and object embedding are denied outright.
_CSP = (
    "default-src 'self'; "
    "script-src 'self' https://cdn.plot.ly; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; "
    "connect-src 'self'; "
    "base-uri 'self'; "
    "frame-ancestors 'none'; "
    "object-src 'none'"
)

# Applied to every response; none of these can alter app behavior.
_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "X-Frame-Options": "DENY",
    "Content-Security-Policy": _CSP,
}

# In-app safety limits. These are a dependency-free backstop only; per-IP rate
# limiting is expected at the reverse-proxy / edge (Coolify/Traefik) in
# production.
_MAX_BODY_BYTES = 64 * 1024  # real config payloads are ~1-2 KB; this is generous

# Monte Carlo is CPU-bound (~500 engine runs). Bounding concurrency protects the
# shared anyio threadpool and CPU so health checks and static serving keep
# responding under load.
_MAX_CONCURRENT_MC = max(2, os.cpu_count() or 4)
_mc_semaphore = threading.BoundedSemaphore(_MAX_CONCURRENT_MC)


class NoCacheMiddleware(BaseHTTPMiddleware):
    """Attach security headers to all responses; no-cache to static assets."""

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        """Add security headers to every response and no-cache to assets."""
        # Reject oversized bodies up front. Covers the Content-Length case; a
        # chunked client without Content-Length can bypass this, which is out
        # of scope for a dependency-free guard.
        length = request.headers.get("content-length")
        if length and length.isdigit() and int(length) > _MAX_BODY_BYTES:
            return JSONResponse({"detail": "Request body too large"}, status_code=413)
        response = await call_next(request)
        response.headers.update(_SECURITY_HEADERS)
        path = request.url.path
        if path.endswith((".js", ".css", ".html")) or path == "/":
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
        return response


app = FastAPI(title="Rent or Buy?")
app.add_middleware(NoCacheMiddleware)


@app.get("/api/health")
async def health() -> JSONResponse:
    """Liveness probe used by Docker healthchecks and Coolify.

    Async so it runs on the event loop and cannot be starved by a
    saturated threadpool under Monte Carlo load.
    """
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
    # Validate before acquiring so invalid requests never consume a compute
    # slot; then guard only the expensive run behind the concurrency cap.
    if not _mc_semaphore.acquire(blocking=False):
        raise HTTPException(
            status_code=503,
            detail="Server busy — too many simulations in progress; retry shortly.",
        )
    try:
        return monte_carlo_payload(config)
    finally:
        _mc_semaphore.release()


_STATIC_DIR = Path(__file__).parent / "static"
app.mount(
    "/",
    StaticFiles(directory=_STATIC_DIR, html=True, check_dir=False),
    name="static",
)
