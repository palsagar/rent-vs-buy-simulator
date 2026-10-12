<div align="center">

# 🏠 Rent or Buy?

**The buy-vs-rent decision simulator — which strategy leaves you wealthier, and how sure can you be.**

</div>

![Rent or Buy? verdict — how far apart buying and renting end at your horizon, how often each wins across simulated futures, and when it is too close to call](https://raw.githubusercontent.com/palsagar/rent-vs-buy-simulator/main/src/simulator/static/screenshots/verdict.png)

## Run it

Install from PyPI and start the app:

```bash
pip install rent-vs-buy-simulator
rent-vs-buy            # serves the app at http://localhost:8501 (set PORT to change it)
```

Or run it from a clone of the repo:

```bash
uv run uvicorn simulator.server:app --port 8000
```

Open http://localhost:8000.

## Using Rent or Buy?

- A **12-step tour** walks you through every feature on first visit; replay it anytime via **Replay the Tour** in the guide.
- The **`?` button** opens the in-app guide — the concepts behind the verdict, one click away.
- **Region presets** — United States, France (Lyon), Germany (Köln), Netherlands, United Kingdom (England & NI) — fill in tax rules, buyer costs and typical prices, rendered in each market's currency.
- **First-time-buyer relief** where a region enacts it — on by default, withdrawing itself above the statutory price cap.
- **Market outlook** — conservative, historical, or optimistic growth and inflation assumptions.
- **Advanced** — five groups at the end of the inputs panel (buying and selling costs, yearly costs of owning, mortgage tax relief, tax when you sell, tax on investments); every default follows the selected region.

Every slider input updates the charts live, and the address bar is always a shareable link to your exact scenario.

![Rent or Buy? guide — built-in documentation with the Replay the Tour entry point](https://raw.githubusercontent.com/palsagar/rent-vs-buy-simulator/main/src/simulator/static/screenshots/guide.png)

## Understanding & hacking Rent or Buy?

- [docs/README.md](https://github.com/palsagar/rent-vs-buy-simulator/blob/main/docs/README.md) — full annotated index
- [docs/architecture.md](https://github.com/palsagar/rent-vs-buy-simulator/blob/main/docs/architecture.md) — system + module map
- [docs/formulas.md](https://github.com/palsagar/rent-vs-buy-simulator/blob/main/docs/formulas.md) — the math behind the engine (Net Value, Monte Carlo, tax primitives)
- [docs/adr/README.md](https://github.com/palsagar/rent-vs-buy-simulator/blob/main/docs/adr/README.md) — 9 design decisions
- [CONTEXT.md](https://github.com/palsagar/rent-vs-buy-simulator/blob/main/CONTEXT.md) — project vocabulary
- [DEPLOYMENT.md](https://github.com/palsagar/rent-vs-buy-simulator/blob/main/DEPLOYMENT.md) — Docker + analytics wiring

## Numbers

Verified from source, not asserted:

- **12 tour steps** (`src/simulator/static/js/tour.js`) — welcome → region presets → first-time-buyer relief → outlook → situation → verdict → decision chart → fan/tornado → advanced → numbers → guide → all set.
- **5 region bundles** (`src/simulator/regions.py`) — United States, France (Lyon), Germany (Köln), Netherlands, United Kingdom (England & NI); **United States** is the shipped default on a fresh load.
- **Monte Carlo defaults** (`src/simulator/models.py`, `MonteCarloConfig`) — **500** simulations, seed **42**, property-appreciation σ **8.0 pp**, equity-growth σ **15.0 pp**, rent-inflation σ **1.5 pp**, correlation ρ **0.3**.
- **12 pytest files** (`tests/test_*.py`), **5 Playwright spec files** (`tests/*.spec.js`): `tour`, `welcome`, `analytics`, `a11y`, `restore`.
- Package **rent-vs-buy-simulator** on PyPI. The version lives in `pyproject.toml`, and release-please bumps it (see `CHANGELOG.md`).

## Develop

- No build step — a vanilla ES-module frontend served straight from `static/`.
- `uv run pytest tests/ -q` — engine, API, region, Monte Carlo, and Umami tests.
- `npx playwright test` — headless E2E (the config leaves Playwright's default headless mode) over the welcome modal, 12-step tour, analytics contract, a11y, and share/restore specs.
- `Dockerfile` for deploy (FastAPI + static files, `PORT` selects the listen port).

See [docs/formulas.md](https://github.com/palsagar/rent-vs-buy-simulator/blob/main/docs/formulas.md) for the mathematical reference and [CONTEXT.md](https://github.com/palsagar/rent-vs-buy-simulator/blob/main/CONTEXT.md) for the vocabulary.
