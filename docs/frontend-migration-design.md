# Frontend Migration Design — Streamlit → FastAPI + Static Frontend

Date: 2026-07-17 · Status: **Implemented** (2026-07-18) — this design ships in the current app · Supersedes: ADR-0006 (superseded by ADR-0008)

> **Two parts of this document no longer describe the shipped app.** The port change to 8000 was reverted before ship — the app serves on **8501** via CLI, Docker and compose alike (ADR-0008). And the region scope here ("US only", "FR/DE/NL/UK declared with `available: false`") was superseded by the multi-region work: all five bundles now ship available, in their own currencies. See [`multi-region-spec.md`](./multi-region-spec.md).

## Context

The app currently ships on Streamlit ([ADR-0006](adr/0006-stay-on-streamlit-for-redesign.md)), which recorded a client-side rewrite as the future path. That path is now being taken. The engine completed the Phase 1 "Engine Truth" redesign (one liquidation-based Net Value shared by engine and Monte Carlo, ADR-0001..0005); the Streamlit UI around it is still the pre-redesign surface. This migration replaces the entire frontend with the stack and aesthetic of the author's other two apps (`webgpu-fluid-solver`, `webgpu-gray-scott`): FastAPI serving a `static/` directory of hand-rolled HTML/CSS/JS in a GitHub-dark visual system. Product surface follows the approved [redesign spec](redesign-spec.md) §2–3 (single scrolling narrative), with its §4 light theme superseded by the dark system below. Terminology per [CONTEXT.md](../CONTEXT.md).

## Validated decisions (brainstorming record)

| # | Question | Decision |
|---|----------|----------|
| 1 | Compute location | **FastAPI + Python engine** — tested NumPy engine stays; frontend calls the API. Rejected: JS/TS port (re-validation cost), Pyodide (heavy, exotic). |
| 2 | Page scope | **Redesign-spec target** — build §2–3 narrative directly; the old tabbed UI is never ported. |
| 3 | Charting | **Plotly.js via CDN** — near-1:1 port of the existing Plotly specs; one shared dark theme. |
| 4 | Strategy hues | **Buy `#f0883e` (orange), Rent `#58a6ff` (blue)** — exact GitHub-dark palette values, colorblind-safe pair. |
| 5 | Cutover | **Full replacement** — Streamlit deleted in the same change; no transition duality. |
| 6 | Layout | **Hybrid (option C)** — core inputs pinned left, advanced fields in the signature right drawer. Validated via browser mockups. |
| 7 | Regions | **Plumbing + US only** — selector ships with FR/DE/NL/UK disabled until spec §7 research is done. |

## 1. Architecture

```
Browser (static ES modules, Plotly.js)
   │  POST /api/simulate · POST /api/monte-carlo · GET /api/regions
   ▼
FastAPI server.py ── api.py (Pydantic schemas ↔ dataclasses)
   ▼
engine.py · monte_carlo.py · models.py   (untouched, as tested)
```

- **`src/simulator/server.py`** — same shape as the reference apps' `server.py`: `NoCacheMiddleware` (no-store for `.js/.css/.html` and `/`), `GET /api/health`, `StaticFiles` mount. Adds the three compute endpoints, delegating schema work to `api.py`. It lives inside the package (unlike the reference apps' root-level file) because this project ships to PyPI: the `rent-vs-buy` CLI and the Docker image both run `uvicorn simulator.server:app`, which requires the app module to be installed with the package.
- **`src/simulator/static/`** — `index.html`, `css/style.css`, `js/*.js`. Lives inside the Python package (hatch package-data) so the PyPI wheel ships it; the server resolves it via `Path(__file__).parent / "static"`. No framework, no build step; Plotly.js basic bundle from CDN.
- **`src/simulator/api.py`** (new) — request/response models, JSON↔`SimulationConfig` conversion (camelCase wire format), orchestration of engine/MC calls.
- **`src/simulator/regions.py`** (new) — region preset bundles as data. US ships verified (values from current defaults); FR/DE/NL/UK declared with `available: false`.
- **Deleted**: `app.py`, `explainers.py` (content moves to the static guide overlay), `visualization.py`, `mc_visualization.py`. Dependencies removed: `streamlit`, `kaleido`, `plotly`. Kept: `numpy`, `numpy-financial`, `pandas` (engine), plus `fastapi`, `uvicorn`. `cli.py` rewritten as a uvicorn launcher (`rent-vs-buy` serves on `$PORT`, default 8000).

## 2. API contract

All numbers on the wire are raw floats/ints; every currency/percent formatting decision is client-side. Request body for both POSTs is the same config object, fields mapping 1:1 to `SimulationConfig` (camelCase). Validation happens by reconstructing the dataclass; failures return 422 with per-field detail.

| Endpoint | Returns |
|----------|---------|
| `POST /api/simulate` | `verdict` (winner, difference, horizon), `breakeven_year` (nullable), year-1 monthly cost of each strategy, and the monthly series needed by every chart: `net_buy`, `net_rent`, cumulative outflows both sides, mortgage balance, home value, portfolio values, ownership-cost breakdown components |
| `POST /api/monte-carlo` | `buy_wins_pct`, `median_difference`, `p5_difference`, `p95_difference`, yearly fan percentiles of the Buy−Rent difference (p5/p25/p50/p75/p95), tornado bar data (name, low, high). Server runs `MonteCarloConfig()` defaults with fixed seed — knobless per ADR-0003 |
| `GET /api/regions` | Array of region bundles: id, label, currency symbol/format, tax-primitive values, default price/rent/rate bundle, `available` flag |

- **Share URLs**: full config ↔ query params, encoded/decoded client-side, applied on load with auto-run. Replaces save/compare (spec §3); no server storage, privacy stance preserved.
- **CSV export**: generated in the browser from the returned series (Blob download) — no server endpoint.

## 3. Frontend modules

Following the reference apps' file layout (`main.js` bootstrap + focused modules):

| File | Responsibility |
|------|----------------|
| `js/main.js` | Bootstrap: restore config from query params, wire modules, first run |
| `js/state.js` | Config state, query-param codec, debounce timers, in-flight `AbortController`, client-side result cache keyed by a hash of the serialized config JSON |
| `js/api.js` | Fetch wrappers, error normalization |
| `js/inputs.js` | Sliders/number fields, preset pills (Region, Outlook), region-default filling of advanced fields |
| `js/charts.js` | One Plotly dark theme + five builders: decision chart (Net Value lines + breakeven annotation), percentile fan, tornado, cumulative outflows, ownership-cost breakdown |
| `js/results.js` | Verdict hero, stat cards, data table, CSV download |
| `js/ui.js` | Advanced drawer, welcome modal, guide accordion, error banner |

## 4. Layout & visual system

**Layout** (validated via mockups): title-bar (🏠 "Rent or buy?" + `decision tool` badge + author link + GitHub stars pill) → preset-bar (Region pills, Outlook pills, spacer, red `⚙ Advanced` toggle, `? Guide`) → body: persistent left input panel (~280px; 6 core inputs — home price, down payment %, mortgage rate, mortgage term, monthly rent, horizon — plus the assumptions trio; Region and Outlook preset live in the preset-bar), scrolling results narrative center, advanced drawer sliding from the right (`translateX`, 280px, `#161b22`). Mobile ≤900px: left panel collapses into the same drawer pattern; preset-bar scrolls horizontally.

**Results narrative** (redesign spec §3, in order): verdict hero (plain-language sentence, untruncated number; subline with breakeven + confidence; stat row: Buy/Rent net value, year-1 monthly costs) → decision chart → "How sure is this?" (fan + tornado) → "Where the money goes" (outflows + cost breakdown) → "The numbers" (collapsed table + CSV) → footer (privacy line verbatim, GitHub link, region/methodology note).

**Visual tokens** — verbatim from the reference apps' CSS: page `#0d1117`, surface `#161b22`, raised `#21262d`, border `#30363d`, text `#e6edf3` / `#b1bac4` / `#8b949e`, accent `#1f6feb` (active fills, slider thumbs), slider values `#7ee787` mono, primary action `#238636`, error `#da3633`. Strategy hues: Buy `#f0883e`, Rent `#58a6ff` — every line, legend chip, and hero accent; never red/green = bad/good. Accent `#1f6feb` is chrome fill; Rent `#58a6ff` is data; strategy lines carry direct on-chart labels so the two blues never collide. Typography: system sans (`-apple-system, 'Segoe UI'`), verdict headline 700 with `-0.5px` tracking, SF Mono/Cascadia tabular numerals for all figures. Plotly theme: `paper_bgcolor`/`plot_bgcolor` `#161b22`, grid `rgba(48,54,61,0.6)`, muted axis text, `$250k`/`$1.2M` tick formatting. No emoji in UI chrome (favicon keeps 🏠).

**Ported components**: welcome modal (first visit, `localStorage` flag), guide overlay with accordion sections ("?" button; content ported from `explainers.py`), sliding advanced drawer, pill presets, slider rows (name + green mono value + 4px track + 12px `#1f6feb` thumb), error banner (device-lost pattern).

## 5. Behavior & data flow

1. Any input change → state updates → query params rewritten (`history.replaceState`) → 300 ms debounce → `POST /api/simulate` (prior in-flight request aborted) → verdict hero, stat cards, decision chart, outflows/breakdown render.
2. Monte Carlo fires on a separate 600 ms debounce in parallel; the confidence subline and "How sure is this?" section fill in when it lands. Both results cached client-side by config hash so back-and-forth tweaks are instant.
3. Region pill → fills advanced tax/cost fields with the bundle's values (user edits after that are kept; switching region re-fills). Outlook pill → sets only the assumptions trio (appreciation, equity CAGR, rent inflation).
4. Errors: 422 → inline field hints; network/500 → top `#da3633` banner with retry. Loading: subtle spinner in the results area; stale results never shown after a config change (aborted responses are dropped).
5. First visit → welcome modal (dismiss sets `localStorage`); "?" toggles the guide overlay.

## 6. Error handling & testing

- **Server**: dataclass validation → 422 with field detail; unexpected exceptions → 500 with a sanitized message (no internals). Engine is pure compute — no I/O, no hangs.
- **Python tests**: existing engine/model/Monte-Carlo suites untouched. New `tests/test_api.py` (FastAPI `TestClient`): health; simulate happy path checked against a hand-computed fixture; 422 on invalid config; regions shape (US available, others not); MC determinism (same config → identical response) and response shape. Serialization round-trip test: JSON config → `SimulationConfig` produces the same numbers as direct construction.
- **Frontend**: manual smoke checklist (no JS test infra — matches the reference apps): initial load, slider tweak → verdict/chart update, share-URL round-trip, region switch, advanced drawer, welcome/guide, error banner on killed server, mobile width.
- **Quality gates**: `ruff check`/`ruff format`/`ty` clean; coverage gate stays 80% and now covers `server.py` + `api.py` (the `app.py` omit entry is removed).

## 7. Cutover & docs

Same-change cutover: delete `app.py`, `explainers.py`, `visualization.py`, `mc_visualization.py`; drop `streamlit`/`kaleido`/`plotly` deps; rewrite `cli.py` as the uvicorn launcher. Both Dockerfiles switch to the reference pattern (`uvicorn simulator.server:app --host 0.0.0.0 --port ${PORT}`, `ENV PORT=8000`, `/api/health` healthcheck); `docker-compose.yml` updated to 8000. Docs: new **ADR-0008** records this migration and marks ADR-0006 superseded; `redesign-spec.md` §4/§5 amended (dark GitHub-dark system replaces the light editorial theme; "ships on Streamlit" removed); README, CLAUDE.md, CONTEXT.md updated. Deployment (Coolify) only needs the port change 8501 → 8000.

## 8. Non-goals

No JS/TS engine port · no accounts or server-side storage · no light theme variant · no FR/DE/NL/UK data (selector ships disabled) · no PDF export · no scenario save/compare (share URLs replace it) · no frontend test framework · no engine math changes · no regions beyond the five.

## 9. Implementation phasing (preview for the plan)

1. **Server + API**: `src/simulator/server.py`, `api.py`, `regions.py` (US), `tests/test_api.py` — engine untouched, Streamlit still runnable meanwhile.
2. **Static shell + visual system**: `index.html`, `style.css`, title/preset bars, left panel, drawer, welcome/guide (content port).
3. **Results + charts**: `state.js`/`api.js` wiring, verdict hero, all five Plotly charts, MC flow, share URLs, CSV.
4. **Cutover**: deletions, deps, CLI, Dockerfiles, docs/ADR updates, smoke checklist.
