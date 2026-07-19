# Redesign Spec — Rent or Buy? as a Decision Tool

Product identity: a public web app that answers one question for one person — "should I buy this home or keep renting?" Every surface serves the Verdict. Terminology in [CONTEXT.md](../CONTEXT.md); decisions recorded in [docs/adr/](./adr/) (0001–0008).

> **Status (2026-07-18): Implemented.** The engine-truth model (§1) and the output-page narrative (§3) ship in the current app. The visual system (§4) and stack (§5) were delivered by the Streamlit → FastAPI migration ([ADR-0008](adr/0008-fastapi-static-frontend.md) / [frontend-migration-design.md](frontend-migration-design.md)), which replaced §4's light editorial theme with the GitHub-dark system. §6 (code impact) and §9 (phasing) describe the original Streamlit-era plan and are retained as a historical record — the code is the source of truth.

## Why (audit summary, July 2026)

The production app showed three contradictory answers on one screen (headline: "Rent wins by $62k"; chart: Buy ahead for 27 years, "no breakeven"; Monte Carlo: "Buy wins 69.2%") because three surfaces used three definitions of net value. Scenario C understated the renter's investable surplus (ignored the buyer's tax/insurance/maintenance), equity gains were never taxed while home gains got the §121 exclusion, headline metric values rendered truncated ("$-415…"), and the UI was stock-Streamlit-dark with per-chart color semantics that flipped meaning.

## 1. Engine

### 1.1 Net Value series (ADR-0001)
One series per strategy, computed at every month t, used by verdict, charts, breakeven, and MC alike:

- **Buy(t)** = [home value − mortgage balance − seller transaction costs − CG tax on the home gain per region rules + accrued tax savings from deductibility] − all cash paid in through t (down payment, buyer transaction costs, mortgage payments, levy, insurance, maintenance) + liquidated value of the buyer-side matched portfolio (§1.2), net of portfolio CG tax.
- **Rent(t)** = [portfolio value − portfolio CG tax on gains] − cumulative rent paid through t.

Exit is priced at *every* t, not only the horizon. Buy is deeply negative early (transaction drag) — by design; that is the breakeven story.

### 1.2 Cash-flow matching (ADR-0002)
Exactly two strategies. Each month, compare renter cost (rent) vs buyer cost (mortgage + levy + insurance + maintenance); the cheaper side invests the difference in equities within its own scenario. Renter additionally invests down payment + buyer transaction costs at t=0. One equity CAGR governs all invested capital (no money-market rate). Scenarios B and C are deleted.

### 1.3 Horizon ≠ mortgage term (ADR-0004)
Mortgage amortizes over its own term (15/20/30, default 30); the simulation truncates and liquidates at the Horizon (2–40 years, default 10). Remaining balance settles from sale proceeds.

### 1.4 Tax primitives + regions (ADR-0007)
Engine exposes: buyer transaction %, seller transaction %, annual property levy %, interest deductibility (on/off + marginal rate; cap-on-levy-deduction as an optional field for the US), CG-at-exit rule (exempt amount | exempt after N years | fully exempt) and portfolio CG rate. Region presets fill these; SALT cap logic lives in the US preset values, not in engine branches.

### 1.5 Monte Carlo (ADR-0003)
Auto-runs (debounced + cached on config hash), fixed internal seed, no user knobs. Calibration owned by the app: equity σ ≈ 15%/yr, property σ ≈ 8%/yr, rent-inflation σ ≈ 1.5%/yr, property–equity ρ = 0.3 — documented in the guide. Randomizes the same Net Value series as §1.1.

## 2. Inputs (sidebar)

**Visible (8):** Region · Home price · Down payment % · Mortgage rate · Mortgage term · Monthly rent · Horizon · Market-outlook preset.

**Assumptions group (3, visible, pre-set):** property appreciation, equity CAGR, rent inflation. Outlook presets (Conservative / Historical average / Optimistic equities) set only this trio.

**Advanced (collapsed, defaults from Region):** levy %, insurance, maintenance %, cost inflation, buyer/seller transaction %, deductibility + marginal rate, CG rule fields, portfolio CG rate.

**Removed:** Scenario C toggle, down-payment investment rate, all MC knobs, Save Scenario section.

**Defaults (US):** $500k home, 20% down, 6.5% rate, 30-yr term, ~$2,400/mo rent (~210× ratio), 10-yr horizon. FR/DE/NL/UK defaults are a research task (§7) — every shipped value verified, not guessed.

## 3. Output page (ADR-0005)

Single scrolling narrative, no tabs:

1. **Verdict hero** — plain-language sentence with the untruncated number: "Renting leaves you ~€62,000 wealthier if you sell after 10 years", subline: "Buying pulls ahead if you stay ≥ 14 years · Buying wins in 43% of simulated futures" (Verdict, Breakeven, Confidence). Stat row: Buy net value, Rent net value, first-year monthly cost of each side.
2. **Decision chart** — the two Net Value lines, breakeven annotated on-chart, x-axis ends at Horizon.
3. **"How sure is this?"** — percentile fan chart of the Net Value difference (median, 50%/90% bands) + tornado ("which assumption to stress-test hardest").
4. **"Where the money goes"** — cumulative outflows comparison + ownership-cost breakdown (single muted hue).
5. **"The numbers"** — data table + CSV, collapsed.
6. Footer: privacy line (kept verbatim), GitHub link (demoted from header), region/methodology note.

**Deleted:** Asset Growth chart (gross value contradicts Net Value semantics — do not reintroduce), welcome modal (content folds into hero copy + "?" guide), PDF report, scenario save/compare + comparison expander, matplotlib spaghetti chart, probability-over-time chart, "This chart shows…" bullet blocks.

**New: shareable URLs** — full config encoded in URL query params, restored on load. Replaces save/compare (two tabs = comparison; bookmark = save) and enables sharing. No storage, preserves the privacy stance.

## 4. Visual system (light theme)

> **Superseded 2026-07-17** by [frontend-migration-design.md](frontend-migration-design.md) §4: the visual system ships as the GitHub-dark token set of the author's other apps (single dark theme, not light editorial), with Buy `#f0883e` / Rent `#58a6ff`.

- **Two strategy hues everywhere**: Buy = warm terracotta/amber, Rent = cool teal/blue — every line, badge, and accent; neutrals for reference elements; no red/green = bad/good; colorblind-safe.
- **Light editorial theme** (single theme; no dark variant maintained): Streamlit `config.toml` palette/fonts/radii + the existing CSS-injection path for the hero.
- **Typography**: display face for the verdict headline, clean sans for UI, tabular numerals for all figures.
- **No emoji in UI chrome** (favicon 🏠 stays).
- **One Plotly template**: direct line labels over legend boxes, $250K/$1.2M axis formatting, minimal gridwork.
- **Branding**: H1 "Rent or buy?" + one-line subtitle; page title matches domain.

## 5. Stack (ADR-0006)

Ships as FastAPI + static ES-module frontend with Plotly.js (ADR-0008, which supersedes ADR-0006). The engine remains Python server-side; a TS/Pyodide client port is no longer the recorded path.

## 6. Code impact

- `engine.py` — rewrite around §1 (Net Value series, matching, horizon/term split, primitives). `FORMULAS.md` updated to match and linked from the guide (trust feature).
- `models.py` — config gains region/term/primitive fields; drops Scenario C fields; results carry the two series + verdict/breakeven/confidence.
- `monte_carlo.py` — recalibrated, knobless config, cached.
- `app.py` — restructured per §2–3; loses ~half its surface.
- **Deleted:** `utils.py` (PDF), `scenario_manager.py`, `mc_visualization.py` matplotlib parts; matplotlib + fpdf2 dependencies exit.
- New: `regions.py` (preset bundles as data), share-URL encode/restore.
- Tests: engine tests rewritten against §1 with hand-computed fixtures; region bundles get source-cited test values.

## 7. Research tasks (before regions ship)

Per region — verify with citable sources, encode as data + tests: typical buyer/seller transaction %, levy basis, deductibility rules (NL), CG-at-exit rule (DE 10-year rule, FR/UK primary-residence exemption, US §121 + SALT), portfolio CG rate (DE ~26.4%, FR 30% PFU, UK CGT, US LTCG), plus credible default price/rent/rate bundles.

**Status: complete (2026-07).** All five regions ship with source-verified values. The research, its corrections, and the per-region confidence ratings are recorded in `docs/multi-region-spec.md`; the shipped values carry their citations in `tests/test_regions.py`, so a wrong number fails a build rather than decaying in prose. Known gaps, simplifications and bias directions are enumerated in that spec's §8 and surfaced to users in each region's `notes`.

## 8. Non-goals

Regions beyond the five · FX conversion · dark theme · PDF export · server-side storage/accounts · client-side rewrite (deferred) · changes to PyPI/CLI packaging.

## 9. Suggested phasing

1. **Engine truth** (§1 + tests + FORMULAS.md) — the contradictions die here.
2. **Page restructure** (§2–3, cuts + share URLs) — still default-themed.
3. **Visual system** (§4).
4. **Regions** (§7 research → `regions.py` → selector).

Each phase ships independently; phase 1 alone fixes the worst production defect.
