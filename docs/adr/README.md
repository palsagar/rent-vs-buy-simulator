# Architecture Decision Records

Each ADR records one load-bearing decision and why the alternatives lost. "Implemented" tracks whether the decision is in the shipped code — a decision can be settled without being built yet.

| # | Title | Status | Implemented |
|---|-------|--------|-------------|
| [0001](0001-liquidation-based-net-value.md) | Net Value is liquidation-based, symmetric, and the only outcome metric | Accepted | Yes |
| [0002](0002-two-strategies-cash-flow-matching.md) | Exactly two strategies, compared under cash-flow matching | Accepted | Yes |
| [0003](0003-monte-carlo-auto-run-fixed-calibration.md) | Monte Carlo runs automatically with fixed, app-owned calibration | Accepted | Yes |
| [0004](0004-horizon-decoupled-from-mortgage-term.md) | Horizon is decoupled from mortgage term | Accepted | Yes |
| [0005](0005-results-page-verdict-narrative.md) | Results page is a verdict narrative, not a dashboard | Accepted | Yes |
| [0006](0006-stay-on-streamlit-for-redesign.md) | The redesign ships on Streamlit; a client-side rewrite is deferred, not rejected | Superseded by [0008](0008-fastapi-static-frontend.md) | No — the deferred path arrived as a FastAPI + static-JS stack |
| [0007](0007-multi-region-via-tax-primitives.md) | Multi-region support via parameterized tax primitives, not per-country logic | Accepted, amended by the [multi-region spec](../multi-region-spec.md) | Yes |
| [0008](0008-fastapi-static-frontend.md) | The frontend migrates from Streamlit to a FastAPI + static JavaScript stack | Accepted | Yes (supersedes [0006](0006-stay-on-streamlit-for-redesign.md)) |
| [0009](0009-portfolio-tax-wrappers-out-of-scope.md) | Portfolio tax wrappers are out of scope; every region models a plain taxable account | Accepted | Yes |

The vocabulary in [CONTEXT.md](../../CONTEXT.md) covers both shipped and target-state features. The one deliberate omission that remains a known bias — unsheltered portfolios understating after-tax returns in every region — is recorded in ADR-0009 and disclosed per region in `regions.py`'s `notes`.

The four design specs under `docs/` ([redesign-spec](../redesign-spec.md), [multi-region-spec](../multi-region-spec.md), [frontend-migration-design](../frontend-migration-design.md), [frontend-migration-plan](../frontend-migration-plan.md)) are historical records of how these decisions were reached, not living documents — see [the docs index](../README.md).
