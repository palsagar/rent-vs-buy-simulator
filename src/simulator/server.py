"""FastAPI server for the rent-vs-buy simulator.

Serves the static frontend and the JSON API wrapping the simulation
engine. Mirrors the structure of the author's other apps (health
endpoint, no-cache middleware for static assets during development).

Run with: uv run uvicorn simulator.server:app --reload
"""

import logging
import os
import re
import threading
from pathlib import Path
from typing import Annotated, Any
from urllib.parse import urlsplit

from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from .api import config_from_dict, monte_carlo_payload, simulate_payload
from .regions import list_regions

_logger = logging.getLogger(__name__)


def _umami_config() -> tuple[str, str]:
    """Read and validate the Umami env vars; malformed values are inert."""
    domain = os.environ.get("UMAMI_DOMAIN", "").rstrip("/")
    website_id = os.environ.get("UMAMI_ID", "")
    if not (domain and website_id):
        return "", ""
    try:
        parts = urlsplit(domain)
        if (
            parts.scheme != "https"
            or parts.username is not None
            or parts.password is not None
            or parts.path != ""
            or parts.query != ""
            or parts.fragment != ""
            or parts.netloc.endswith(":")
            or parts.hostname is None
            or not (parts.port is None or 1 <= parts.port <= 65535)
            or not all(32 < ord(c) < 127 for c in parts.hostname)
            or ";" in parts.hostname
        ):
            raise ValueError
    except ValueError:
        _logger.warning("Umami env vars are set but malformed — analytics disabled")
        return "", ""
    if not re.fullmatch(
        r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
        website_id,
    ):
        _logger.warning("Umami env vars are set but malformed — analytics disabled")
        return "", ""
    return domain, website_id


UMAMI_DOMAIN, UMAMI_ID = _umami_config()

# Content-Security-Policy: same-origin by default, plus the Plotly CDN for
# scripts and inline styles for the HTML's style="..." attributes. The Umami
# origin joins script-src AND connect-src (the tag's script.js beacons to the
# same origin) only when analytics is configured; otherwise the CSP is unchanged.
_script_src = "script-src 'self' https://cdn.plot.ly"
_connect_src = "connect-src 'self'"
if UMAMI_DOMAIN:
    _script_src += f" {UMAMI_DOMAIN}"
    _connect_src += f" {UMAMI_DOMAIN}"
_CSP = (
    "default-src 'self'; "
    f"{_script_src}; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; "
    f"{_connect_src}; "
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


class UmamiInjectionMiddleware(BaseHTTPMiddleware):
    """Inject the Umami analytics tag into HTML responses when configured."""

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        """Splice the tag before </body> on GET 200 text/html; else pass through."""
        response = await call_next(request)
        if not (UMAMI_DOMAIN and UMAMI_ID):
            return response
        # HEAD passes through untouched: StaticFiles sends no body for HEAD,
        # so rebuilding would zero Content-Length.
        if request.method != "GET":
            return response
        if response.status_code != 200:
            return response
        if "text/html" not in response.headers.get("content-type", ""):
            return response
        body = b""
        async for chunk in response.body_iterator:
            body += chunk
        tag = (
            f'<script defer src="{UMAMI_DOMAIN}/script.js" '
            f'data-website-id="{UMAMI_ID}"></script>'
        ).encode()
        # Anchor: just before </body>, AFTER the app module tag. Deferred
        # scripts execute in document order, so a slow analytics fetch can
        # never delay main.js.
        body = body.replace(b"</body>", tag + b"</body>", 1)
        headers = dict(response.headers)
        # The rewritten body differs from the file on disk — StaticFiles'
        # validators must not survive onto it.
        for h in ("etag", "last-modified", "accept-ranges"):
            headers.pop(h, None)
        headers["content-length"] = str(len(body))
        return Response(content=body, status_code=response.status_code, headers=headers)


app = FastAPI(title="Rent or Buy?")
app.add_middleware(NoCacheMiddleware)
app.add_middleware(UmamiInjectionMiddleware)


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
