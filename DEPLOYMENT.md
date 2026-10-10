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
<script defer src="${UMAMI_DOMAIN}/script.js" data-website-id="${UMAMI_ID}" data-before-send="umamiBeforeSend"></script>
```

into the HTML page just before `</body>`, with the values read from the
container env at process start. `data-before-send` names a hook in
`static/js/analytics.js` that Umami calls before it sends anything (see
**Events** below). The hook requires Umami 2.18.0 or newer; older trackers
ignore the attribute.

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
# → <script defer src="https://analytics.example.com/script.js" data-website-id="123e4567-e89b-42d3-a456-426614174000" data-before-send="umamiBeforeSend">

# The Umami instance supports the hook (2.18.0 or newer). Use your UMAMI_DOMAIN.
curl -s https://analytics.example.com/script.js | grep -c before-send   # must print 1
```

Then load the site and confirm a hit appears in Umami's Realtime view. To see a
custom event, clear the `rvb.tour.v1` localStorage key, reload, and click
**Take the Tour** — a `tour-started` event should arrive.

### Events

Umami records page views automatically, and it records a new one each time
the address bar changes. The app rewrites the address bar after every change
to the inputs, so the `umamiBeforeSend` hook does three things:

- It removes the app's own parameters (the input values, `r` and `v`) from the
  URL of every page view and event, and from every referrer. Other
  parameters, such as `utm_*` and `ref`, stay.
- It sends only the first page view for a path. Each page load therefore counts
  as one view of `/` (or `/?utm_source=...` for a campaign link). That first
  page view reports the URL the visitor landed on, saved when the page loads,
  because the tracker can start after the app's first address-bar rewrite.
- It sends `link-opened` when that landing URL carries the app's parameters.

Custom events. Interaction events are sent only for real (trusted) user
actions, so the tour's clicks do not count. The tour events are sent whenever
the tour starts or ends.

- `tour-started`
- `tour-completed`
- `tour-skipped`
- `region-changed` (`{ region }`)
- `outlook-changed` (`{ outlook }`)
- `ftb-toggled` (`{ on }`)
- `inputs-opened` — the **Edit your numbers** button opens the phone inputs sheet
- `advanced-opened` — the **Advanced** drawer opens (closing it is not sent)
- `value-changed` (`{ field, via }`) — sent when a slider is released, or
  500 ms after the last keyboard step (`via: "slider"`), or when an exact value
  is typed (`via: "typed"`); `field` is the input's config key
- `link-shared` — the **Share this scenario** button
- `link-opened` — the visitor arrived through a link that carries the app's
  parameters (a shared scenario); sent once per page load, after the page view

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
