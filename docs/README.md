# Rent or Buy? — Documentation Index

A public decision tool that answers one question for one person: "should I buy this home, or rent and invest the difference?" A FastAPI backend wraps a vectorized NumPy engine and serves a no-build vanilla ES-module frontend from `src/simulator/static/`. Every surface — verdict, charts, breakeven, Monte Carlo — computes from the same liquidation-based Net Value series.

Hub: [../README.md](../README.md)

## Documentation

| Document | What it covers |
|---|---|
| [System Architecture](architecture.md) | Stack, static-JS module map, server middleware, API endpoints, tour & analytics flow, test layout |
| [Mathematical Reference](formulas.md) | The exact formulas behind `_net_value_series()`: Net Value, cash-flow matching, Monte Carlo, tax primitives |
| [Decision Records](adr/README.md) | 9 ADRs covering shipped and rejected decisions |
| [Project Vocabulary](../CONTEXT.md) | Canonical terms and what to call them |

### Historical specs

Kept as records of the design process — ancestry, not living documents. See [ADR-0008](adr/0008-fastapi-static-frontend.md) for the current state.

| Document | What it records |
|---|---|
| [Redesign Spec](redesign-spec.md) | The original redesign: verdict narrative, Net Value, horizon/term split, trust surface |
| [Multi-Region Spec](multi-region-spec.md) | Region bundles as data, tax primitives, currency, first-time-buyer relief; amends ADR-0007 |
| [Frontend Migration Design](frontend-migration-design.md) | The move from Streamlit to a static ES-module + FastAPI stack |
| [Frontend Migration Plan](frontend-migration-plan.md) | The task-level plan that shipped the migration |

## Tour & Tests

The 12-step onboarding tour (`static/js/tour.js`) is covered by `tests/tour.spec.js`. The suite is **12 pytest files** under `tests/` (engine, api, regions, Monte Carlo, tornado bounds, Umami) plus **5 Playwright spec files** (`tour.spec.js`, `welcome.spec.js`, `analytics.spec.js`, `a11y.spec.js`, `restore.spec.js`) running in headless mode (the default Playwright leaves in place) on port 8323.
