# Deployment

Hub: [README.md](README.md) · Index: [docs/README.md](docs/README.md)

Rent or Buy? ships as a single Docker container (FastAPI + static files). `PORT`
selects the listen port (default `8501`); `/api/health` backs the Docker
HEALTHCHECK.

## Analytics (Umami) — wiring runbook

The Umami tracking tag is **injected at request time by the FastAPI app itself**,
driven by two runtime env vars — nothing about Umami lives in the repo or the
image. `UmamiInjectionMiddleware` (see `server.py`) inserts:

```html
<script defer src="${UMAMI_DOMAIN}/script.js" data-website-id="${UMAMI_ID}"></script>
```

into the HTML page just before `</body>`, with the values read from the
container env at process start.

### One-time setup

1. **In your Umami dashboard**: add a website for `rent-or-buy-sim.com`.
   Copy its **Website ID** (a UUID).
2. **In Coolify** → this app → **Environment Variables**, add two variables
   (plain **runtime** vars — do *not* tick "Build Variable"):

   | Var | Value | Notes |
   |---|---|---|
   | `UMAMI_DOMAIN` | `https://analytics.example.com` | Full origin of the Umami instance. Must include `https://`; a trailing slash is stripped. |
   | `UMAMI_ID` | `xxxxxxxx-xxxx-...` | The Website ID (UUID) from step 1. |

3. **Redeploy** (or just Restart) the app in Coolify. Env-var changes take effect
   on process start — **no rebuild needed**.

### Validation rules

- `UMAMI_DOMAIN` must be a plain HTTPS origin (`https://host[:port]`) with no path, query, fragment, or CSP delimiters, after stripping a trailing slash.
- `UMAMI_ID` must be a canonical UUID (`8-4-4-4-12` hex, case-insensitive).
- Empty vars pass through silently (no warning); if both are set but malformed,
  the middleware logs a warning and serves the page without the tag — local dev and CI are never tracked.

### Verify

```bash
# Inert default: no tag is injected when the vars are unset.
uv run uvicorn simulator.server:app --port 8011
curl -s http://localhost:8011/ | grep -c 'data-website-id'
# → 0

# With analytics configured: the tag appears just before </body>.
UMAMI_DOMAIN="https://analytics.example.com" \
  UMAMI_ID="123e4567-e89b-42d3-a456-426614174000" \
  uv run uvicorn simulator.server:app --port 8011
curl -s http://localhost:8011/ | grep -o '<script defer src="[^"]*"[^>]*>'
# → <script defer src="https://analytics.example.com/script.js" data-website-id="123e4567-e89b-42d3-a456-426614174000">
```

Then load the site and confirm a hit appears in Umami's Realtime view. To see a
custom event, clear the `rvb.tour.v1` localStorage key, reload, and click
**Take the Tour** — a `tour-started` event should arrive.

### Events

Pageviews are automatic. Custom events:

- `tour-started`
- `tour-completed`
- `tour-skipped`
- `region-changed` (`{ region }`)
- `outlook-changed` (`{ outlook }`)
- `ftb-toggled` (`{ on }`)

### Notes

- **Change or disable analytics:** edit/remove the env vars + Restart. No rebuild.
- With either var unset the middleware is a pass-through — local dev and the
  Playwright suite are never tracked.
- Malformed values (bad scheme, whitespace/quotes, non-UUID ID) are treated as
  unconfigured — the app logs a warning at startup and serves untracked pages.
- **Umami is cookieless** — no consent banner required.
- If you enable *domain enforcement* on the Umami website, make sure
  `rent-or-buy-sim.com` is in its allowed-domains list, or events are dropped.
- The audience is technical (ad-blocker-heavy), so expect some undercount.
- Optional hardening: add `data-domains="rent-or-buy-sim.com"` to the injected tag
  in `server.py` if the env vars are ever set on a non-prod deployment.
