# Multi-Region Spec — France, Germany, Netherlands, United Kingdom

Status: proposed. Supersedes nothing; amends [ADR-0007](adr/0007-multi-region-via-tax-primitives.md) (see §9).
Scope discipline: this document is written against the repo's `CLAUDE.md` mandate — *"Minimum code that solves the problem. Nothing speculative. No abstractions for single-use code."* Every primitive below is justified inline by a named, quantified defect in a named shipped region. §3 records what was rejected and why; that section is the enforcement mechanism, not an afterthought.

---

## 1. Summary and scope

### 1.1 What ships

Four new region bundles — France, Germany, Netherlands, United Kingdom (England & NI) — flipped from `"available": False` (`regions.py:40-55`) to real preset data, plus the minimum engine work that makes those four honest.

**Six new engine primitives. All scalar. All default to a value that leaves the US preset arithmetically inert.**

| # | Field | Type | Default | Fixes | Regions |
|---|---|---|---|---|---|
| P1 | `annual_property_levy` | `float` | `0.0` | D1, D2 | UK, DE, FR |
| P2 | `levy_paid_by_occupier` | `bool` | `False` | D3 | UK, DE |
| P3 | `annual_maintenance_amount` | `float` | `0.0` | D7 | FR, DE, UK |
| P4 | `closing_cost_buyer_amount` | `float` | `0.0` | D5 | UK, FR |
| P5a | `portfolio_deemed_return_pct` | `float` | `0.0` | D4 | NL |
| P5b | `portfolio_drag_rate_pct` | `float` | `0.0` | D4 | NL |

Everything else is data, a wire fix, or a documentation change:

- **D6 (first-time buyer)** costs **zero engine primitives** — it is a region-bundle override set plus a UI pill (§2.6, §6.3).
- **D8 (sale CG regime)** costs **zero changes** — `exempt_after_years` stays, unused-but-reachable (§2.7).
- **D9 (mortgage product)** costs **zero engine changes** — a `notes` list per bundle (§2.8). It also forces one correction to the research bundle: `mortgageTermYears` is the **amortisation** term, not the fixing period (§4.0).
- One **latent wire bug** must be fixed for NL to be expressible at all: the `levyDeductionCap` `0 → null` sentinel in `api.js:4-9` (§6.1).
- One **defensive hole** in `api.py:99` must be closed, because the whole design's safety rests on the invariant that every config field is a scalar (§6.2).
- One **tornado-chart defect** is introduced by P1 and must be neutralised in the same phase (§5.6).

### 1.2 Locked decisions carried in verbatim

1. Exactly FR/DE/NL/UK. No Custom region, no other countries.
2. Extend primitives where a country genuinely does not fit; never fudge with a fake effective rate.
3. First-time-buyer defaults **TRUE**, visible toggle, no-op in Germany (no FTB statute enacted).
4. **All regions model plain taxable portfolios.** No wrapper primitive. ISA/PEA/Sparer-Pauschbetrag/heffingsvrij vermogen are not modelled. This understates real after-tax returns for wrapper users **in every region, including the US** — recorded in §8 and in every bundle's notes.
5. **Phase 1** = all engine primitives + tests proving no regression against the US preset. **Phase 2** = the four bundles as pure data. Matches ADR-0007's "countries are data, not code."

### 1.3 What the constraint bought

Research proposed ~20 candidate primitives. This spec ships **5**, by finding four consolidations:

- **D1 + D2 collapse into one field.** The engine already has the exact mechanism needed — `annual_home_insurance` is an absolute amount indexed by `cost_inflation_rate` (`engine.py:184-186`). Giving the levy that same shape fixes *both* "no flat-amount path exists" and "levy is welded to appreciating home value."
- **D5's two sub-defects collapse into one field.** The ~£3,100 of price-invariant UK fees demand a fixed-amount companion field. Once that field exists, UK SDLT is *exactly* linear in price over £250k–£925k — `SDLT(P) = 0.05P − 10,000` — so the existing `closing_cost_buyer_pct` plus the new amount reproduce SDLT with zero error over the dominant range. No band schedule, no list-shaped config, no new widget.
- **D6 collapses to zero fields.** FTB relief changes only *which closing-cost numbers apply* — that is region data, not engine behaviour.
- **The NL eigenwoningforfait collapses to zero fields**, via an exact algebraic identity rather than a fudge (§5.5).

---

## 2. The minimal primitive set

Insertion points are cited against the current `engine.py`. All money math lives in `_net_value_series()` (`engine.py:76-286`); both `calculate_scenarios` (`engine.py:399`) and `monte_carlo._simulate_single_path` (`monte_carlo.py:189`) call it, so each primitive has exactly one consumption site.

---

### P1 — `annual_property_levy: float = 0.0`

**Semantics.** A flat annual property levy in the region's currency, paid monthly, indexed by `cost_inflation_rate` — identical in shape to `annual_home_insurance`. **Additive** to the existing ad-valorem `property_tax_rate` path, which is untouched.

**Insertion point.** `engine.py:181-182`.

```python
# hoisted: three cost lines now share this index
cost_index = (1 + config.cost_inflation_rate / 12) ** (t_arr[1:] - 1)

levy = np.zeros(h + 1)
levy[1:] = (
    home_value[:-1] * (config.property_tax_rate / 100) / 12
    + (config.annual_property_levy / 12) * cost_index
)
```

Both components land in the **same `levy` array**, deliberately. That keeps `total_property_tax_paid` (`engine.py:439`), the deduction base (`engine.py:226`), and the ownership-cost breakdown chart correct without touching any of them.

**Defect fixed — D1 (levy unit).** The engine has no flat-amount path (`engine.py:182` is ad-valorem only). Quantified:
- **UK.** England average Band D 2026/27 = **£2,392** (£2,343 excluding parish precepts). Council tax bands are fixed on **1 April 1991** values and band amounts are ninths of Band D (LGFA 1992 s.5, A = 6/9 … H = 18/9). The engine's only expressible form is 2,392/289,106 = **0.827% ad valorem**. A user who drags the price slider to £600,000 — a London semi — gets a modelled council tax of **£4,962/yr**. A £600k England home is typically Band E–F, i.e. **£2,924–£3,455**. The engine overstates by **~50%**, and the error grows without bound with the slider.
- **DE.** Post-2025 Grundsteuer reform runs **eight different state models**; Bayern's Flächenmodell ignores property value **entirely**. There is no ad-valorem rate that is even approximately right there.

**Defect fixed — D2 (levy base indexation).** The engine ties the levy to appreciating `home_value` (`engine.py:182`). No new region's levy base tracks market prices: FR taxe foncière is assessed on *valeur locative cadastrale* (a notional 1970 rent, statutorily uprated); DE on Grundsteuerwert; UK council tax on 1991 bands tracking council budgets. Quantified honestly, because the magnitude depends on the outlook preset:
- **UK, Historical outlook (3% appreciation), 25 yr:** ad-valorem cumulative £87,200 vs cost-indexed £81,700 — a **6.7%** overstatement. Modest.
- **UK, Optimistic outlook (5% appreciation, `inputs.js:11`), 25 yr:** ad-valorem cumulative **£114,200** vs cost-indexed **£81,700** — a **40%** overstatement, i.e. **£32,500** wrongly charged to the buy side.

**Residual bias, stated rather than engineered away.** Indexing at `cost_inflation_rate` (default 2.5%) is not each country's statutory uprate. FR's VLC coefficient is ~+0.8%/yr; 25-year cumulative at 0.8% is €33,700 vs €41,700 at 2.5% — this fix recovers roughly 30% of the FR gap, not all of it. **Rejected:** a dedicated `levy_escalation_rate` field. It would be a sixth primitive whose only job is to split one already-existing inflation knob three ways, and `cost_inflation_rate` is already exposed in Advanced (`fields.js:23`) for a user who wants to move it. Bias direction recorded in §8.

---

### P2 — `levy_paid_by_occupier: bool = False`

**Semantics.** When `True`, the levy is charged to **both** arms — the buyer pays it as owner-occupier, the renter pays it as resident. When `False` (default, and the US case), buyer-only, exactly as today.

**Insertion point.** `engine.py:196-197`.

```python
housing_cost_rent = np.zeros(h + 1)
housing_cost_rent[1:] = rent_level[:-1]
# Occupier-borne levies (UK council tax; DE umlagefähige Grundsteuer) are
# owed by whoever lives there, so the renter bears them too.
if config.levy_paid_by_occupier:
    housing_cost_rent = housing_cost_rent + levy
```

**The invariant — stated correctly, because the previous revision stated it backwards.** Earlier drafts claimed the Verdict is "invariant to this flag". **That is false.** With the flag OFF the buyer pays `L` and the renter pays nothing, so the difference is `(b+L) − r`; with it ON the difference is `(b+L) − (r+L) = b − r`. Toggling therefore moves the Verdict by the compounded levy — **£7,159 on a 5-year UK fixture**, against a claimed tolerance of 1e-12. The algebra `(b+L) − (r+L) = b − r` was always correct; it simply does not describe the toggle.

**The real theorem is the one this section's rejected alternative already names:**

```
(annual_property_levy = L, levy_paid_by_occupier = True)  ≡  (annual_property_levy = 0)
```

for the **difference** series, verified to hold at exactly 0.0. Charging a levy to both arms is economically identical to charging it to neither. Proof: `surplus = (b+L) − (r+L) = b − r`, so contributions, both portfolios and both bases are unchanged; `cash_committed` (`engine.py:212-214`) rises by `ΣL` on **both** arms, so `net_buy` and `net_rent` each shift down by `ΣL` and their difference is untouched.

**One condition, which the test must honour: the levy must be non-deductible.** `cum_tax_savings` reads the `levy` array (`engine.py:226`), so if `interest_deduction_enabled` is on with a non-zero rate and cap, the `L` and `0` configs credit different deductions and the equivalence breaks. It holds for UK and DE — the only two regions that set the flag — because both ship `interestDeductionEnabled: False`.

**Levels are not invariant, only the difference.** Both nets shift by `ΣL`, and `cash_committed` changes magnitude, so the subtraction re-rounds; on values reaching ~1e7 one ulp is ~2e-9 and an absolute 1e-9 assertion would be tighter than one ulp. The test uses a **relative** tolerance (§7.3).

**So why is it a primitive at all?** Because the surfaces it *does* move are headline surfaces:
- `monthly_cost_buy_year1` / `monthly_cost_rent_year1` (`engine.py:432-433`, wired to the verdict stat row at `api.py:209-210` and `index.html:196-206`). For the UK, £2,392/yr = **£199/mo = 13.9% of the £1,431 England semi rent**, currently shown on the buy side only.
- The "Where the money goes" cumulative-outflow chart (`outflow_buy`/`outflow_rent`, `engine.py:215-216`) — misstated by **~£81,700** over 25 years for the UK. (The previous revision said ~£60,000, which was the unindexed `2,392 × 25`; the correct figure is the cost-indexed cumulative already computed in P1's D2 table and must agree with it.)

**Rejected alternative: set the UK/DE levy to 0 and note it.** Verdict-equivalent and costs zero fields, but it encodes a modelling trick in the *data* — a future reader sees `annualPropertyLevy: 0` for a country with £2,392 council tax, "fixes" it, and silently breaks the model. ADR-0007's thesis is that countries are data; the data must state the fact (£2,392) and the flag must state the incidence.

**DE nuance, resolved explicitly.** Grundsteuer (BetrKV §2 Nr.1) and Wohngebäudeversicherung (BetrKV §2 Nr.13) are *umlagefähig*, so German Kaltmiete excludes them and the tenant bears them. Both are handled: Grundsteuer via `levy_paid_by_occupier = True`, Wohngebäudeversicherung via `annualHomeInsurance = 0` (a Cologne condo carries it inside the WEG's Hausgeld anyway). **Nebenkosten dominated by heating and water are deliberately NOT zeroed and NOT modelled** — both parties pay them, they are decision-neutral, and adding them to both sides would only inflate `cash_committed` symmetrically. The DE `annual_maintenance_amount` (P3) is scoped to the **non-umlagefähig** components only: Instandhaltungsrücklage, Verwaltervergütung, Sondereigentum.

**UK nuance, flagged as a simplification not a fact.** This models English rents as quoted **exclusive** of council tax. That premise is **unverifiable** — ONS never states it, and PIPR uses *achieved* rents for England and Wales, not advertised ones. Shipped as a documented modelling simplification (§8, and the UK bundle's `notes`).

**Insurance is deliberately not given an occupier flag.** UK buildings insurance is the landlord's cost, not the tenant's; DE condo insurance is already £0/€0. No named region needs one. Rejected (§3).

---

### P3 — `annual_maintenance_amount: float = 0.0`

**Semantics.** Flat annual maintenance in currency, cost-indexed. Additive to `annual_maintenance_pct`, which is untouched.

**Insertion point.** `engine.py:187-188`.

```python
maintenance = np.zeros(h + 1)
maintenance[1:] = (
    home_value[:-1] * (config.annual_maintenance_pct / 100) / 12
    + (config.annual_maintenance_amount / 12) * cost_index
)
```

**Defect fixed — D7 (maintenance unit).** The engine expresses maintenance as a percentage of an appreciating home value (`engine.py:188`), a modelling choice `FORMULAS.md` §3 defends explicitly as "the 1% rule". The evidence contradicts it outside the US:
- **UK.** 1.0% of £289,106 = **£2,891/yr**. ONS Family Spending FYE2025 puts England maintenance-and-repair at **£634/yr** across all households; scaled to ~65% owner-occupation, **~£900/yr**. The percentage form overstates by **3.2×**. More structurally, ONS shows England maintenance spend varying ~1.9× across regions while house prices vary 3–4× — the two are not proportional.
- **DE.** §28 Abs.2 II. BV states the convention in **€/m²/yr (€9.00)**, explicitly not value-linked. Cross-check: €9.00 × 80 m² = €720 Instandhaltungsrücklage + Verwalter + Sondereigentum ≈ **€1,700/yr**, which independently agrees with the research's "~0.5% of €339,000 = €1,695". Two derivations converging is worth more than either alone.

**Decision: the US preset stays on the percentage path** (`annualMaintenancePct: 1.0`, `annualMaintenanceAmount: 0.0`). **Rejected:** converting the US bundle to an absolute amount in Phase 1. Two reasons: (a) the evidence base above is European, and the "1% of value" rule is the genuine US convention; (b) it would change the US verdict and therefore break the Phase-1 no-regression gate (§7.2), which is the single most valuable test in this change. The percentage path is a **supported mechanism**, not a deprecated compatibility shim.

**Why P3 is a field at all, when it is shape-identical to `annual_home_insurance`.** This is the strongest objection to P3 and the previous revision never answered it: `annual_home_insurance` (`engine.py:184-186`) is already an absolute, cost-indexed, buyer-only cost at the same consumption site. §5.5 rejects a `deduction_income_addback` field on exactly this ground — "an existing field already expresses it exactly" — so consistency demands the same test here.

**It passes, and the distinction is observable, not aesthetic.** The EWF case collapses with *zero observable difference*: it folds into an existing labelled category (the levy) and every output — series, `totals`, chart — is numerically and semantically unchanged. Reusing `annual_home_insurance` for maintenance does **not**: `_insurance` and `_maintenance` are separate series (`engine.py:282-283`), `total_insurance_paid` and `total_maintenance_paid` are separate wire fields (`api.py:215-216`), and they render as separate slices of the ownership-cost breakdown chart (redesign-spec §3.4). Folding £900 of UK maintenance into the insurance line would show a UK user £1,210 of "insurance" and £0 of "maintenance" — a visibly wrong chart. The field buys a correct category split on a shipped surface, used by three regions, at the cost of one scalar. **Honest counter:** if the breakdown chart were ever cut, P3's justification would go with it, and the field should then be re-examined rather than inherited.

**The Netherlands ships on the percentage path too, for the same reason.** The rule governing which path a region takes is **the unit the region's own evidence is collected in** — not a global preference for absolute amounts:

| Region | Native evidence unit | Path |
|---|---|---|
| UK | £/yr observed spend (ONS Family Spending FYE2025) | amount |
| DE | €/m²/yr (§28 Abs.2 II. BV) — area is fixed, so absolute is exact | amount |
| FR | €/m²/yr copropriété charges — likewise area-proportional | amount |
| **NL** | **% of value (Nibud "ruim 1%"; VEH 1% of WOZ)** | **pct** |
| US | % of value (the "1% rule") | pct |

Converting NL's 1.0% into €4,900 at the default price would **launder the value-proportional convention into an absolute number that then fails to rescale** when the user moves the price slider — reintroducing the exact unit confusion D7 exists to remove, while destroying the one property the Dutch sources actually assert. Storing the evidence in the unit it was collected in is the honest option; P3 exists because **three** regions have natively absolute or area-proportional evidence, not because the percentage path is wrong everywhere. The residual — that two of five shipped regions inherit a unit D7's own evidence argues against — is recorded in §8.1 (S16), not engineered away.

---

### P4 — `closing_cost_buyer_amount: float = 0.0`

**Semantics.** A fixed buyer transaction cost in currency, added to the percentage-of-price term, charged once at `t = 0`. **May be negative** — it is the intercept of the buyer's cost line, and a transfer tax with a zero-rate band has a negative intercept. Clamped at zero in aggregate.

**Insertion point.** `engine.py:152`.

```python
buyer_closing = max(
    config.property_price * (config.closing_cost_buyer_pct / 100)
    + config.closing_cost_buyer_amount,
    0.0,
)
```

`buyer_closing` also feeds `SimulationResults.total_closing_costs_buyer`, which is currently recomputed independently at `engine.py:434-435`. **That recomputation must be replaced**, or the reported total silently contradicts the series. Export it alongside `_monthly_payment` (`engine.py:285`):

```python
"_buyer_closing": np.array([buyer_closing]),
```

and read `total_closing_costs_buyer=float(series["_buyer_closing"][0])` at `engine.py:434`.

Note the field moves **both arms at t = 0**: `initial_outlay` (`engine.py:153`) seeds the renter's portfolio `V0` (`engine.py:206`) and the shared `cash_committed` (`engine.py:212`).

**Defect fixed — D5 (progressive transaction costs), part 1: price-invariant fees.** UK buyer costs include **~£3,100** of fixed fees — conveyancing, searches, survey, Land Registry, lender product fee. Folding these into a percentage is wrong at both ends of the slider: at £50,000 (the slider floor, `fields.js:9`) a 2.6% blend charges £1,300 against a true £3,100; at £2,000,000 (the ceiling) it charges £52,000 against a true £3,100.

**Defect fixed — D5, part 2: UK SDLT slice-progressivity.** This falls out of part 1 for free. SDLT 2026/27 (England & NI), standard single dwelling: 0% to £125,000, 2% to £250,000, 5% to £925,000, 10% to £1.5m, 12% above. For any `P ∈ (250,000, 925,000]`:

```
SDLT(P) = 0.02 × 125,000 + 0.05 × (P − 250,000)
        = 2,500 + 0.05P − 12,500
        = 0.05P − 10,000
```

Total buyer cost with the £3,100 fixed fees:

```
C(P) = 0.05P − 6,900          →  pct = 5.0,  amount = −6,900
```

This is **exact**, not fitted, across the whole £250k–£925k band — which covers the overwhelming majority of England transactions. Check at the preset price: `0.05 × 289,106 − 6,900 = £7,555.30`, of which SDLT alone is £4,455.30, matching the verified figure. Contrast the status quo: a flat 2.613% calibrated at the preset price under-charges by **44%** at £1,000,000, and for a first-time buyer at the preset price it is wrong by an infinite factor (actual SDLT = £0).

**Four documented divergences the two-parameter form cannot represent, all quantified in §8. The previous revision claimed two and got both numbers wrong; these are recomputed and machine-checked:**

1. **Below £250,000** (S6). The model is exact only from £250,000 up. Across the whole £125k–£250k band it under-charges, because true SDLT rises at 2% while the model's 5% line is still climbing out of its −£6,900 intercept. Worst point is **£138,000: model £0 vs true £3,360** (£260 SDLT + £3,100 fees) — the clamp binds. The error spans the entire £50k–£250k slider range, not "below £138,000", and the bound is **£3,360, not £3,100**.
2. **Above £925,000** (S18, new). The marginal rate steps to 10% and then 12%; the model stays at 5%. At £1,000,000: model £43,100 vs true £46,850, **understating £3,750**. At the slider ceiling of £2,000,000 (`fields.js:9`): model £93,100 vs true £156,850 — **£63,750, 41% understated, toward buying**. Disclosing this matters because §1.3 criticises the status quo for under-charging 44% at £1M; the replacement is far better there (8% vs 44%) but is **not** uniformly better, and the previous revision claimed only "two cliffs" while shipping this one silently.
3. **FTB between £300,000 and £500,000** (S19, new). Relief is 0% only to £300,000, then **5% on £300,001–500,000**. The shipped override (pct 0, amount 3,100) charges £3,100 at every price, understating **£5,000 at £400k, £7,500 at £450k, £10,000 at £500k** — all toward buying, with FTB defaulting TRUE.
   **Trade-off, stated explicitly because the previous revision made this choice silently.** The alternative override `(pct 5.0, amount −11,900)` is exact on £300k–500k but wrong below it, including **£545 wrong at the shipped preset price of £289,106** and £3,100 wrong at £150,000. **Choice: keep `(0, 3,100)`.** The preset price sits below £300,000, so this is exact at the default every user sees first and is the value the §7.4 fixture asserts; and the sub-£300k band is where England FTB volume actually concentrates. The £300k–500k error is disclosed rather than traded for a wrong headline.
4. **FTB withdrawn entirely above £500,000** (S5, corrected). gov.uk, verbatim: *"If the price is over £500,000, you cannot claim the relief."* At £501,000 an FTB owes full non-FTB SDLT of £15,050, so the true total is **£18,150** against the model's £3,100 — an understatement of **£15,050, not the £11,950 previously stated** (that figure wrongly netted the £3,100 of fees against the SDLT). This remains the sharpest single bias in the change.

**Rejected: putting the cliff in the engine.** A price-conditional relief withdrawal is per-country logic in `_net_value_series` — precisely what ADR-0007 forbids. It goes in the UK bundle's `notes` (§4.5) instead.

**FR uses the same field.** Notaire *débours* of ~€1,300 are genuinely price-invariant. The degressive emolument scale (four bands, ~1.0–1.1% of a 7.9% total) is **not** modelled — a ≤0.2pp error on a 7.9% cost, well inside the confidence band of the DMTO figure itself.

---

### P5 — `portfolio_deemed_return_pct: float = 0.0` + `portfolio_drag_rate_pct: float = 0.0`

**Semantics.** An annual tax on portfolio **value** (not on realised gains, not at exit), assessed on the **lesser of a deemed return and the actual return, floored at nil**, applied per year as a reduction to that year's monthly compounding rate, **symmetrically to both strategies' portfolios**.

**Why this is two fields, not one pre-multiplied `portfolio_annual_drag_pct: 2.16`.** Wet IB 2001 art. 5.25 lid 1 assesses the taxpayer on `min(deemed, actual)` return; lid 2 floors the result at nil; art. 5.26/5.28 define actual return on an **accrual** basis including unrealised gains. The tax is therefore **concave in the return** — and by Jensen's inequality, applying it to the mean return overstates the mean of the tax. A single pre-multiplied 2.16% cannot express `min()`; it has already thrown away the operand.

**Quantified, against this app's own MC calibration (`monte_carlo.py:256`, mean 7%, σ 15%):**

```
taxable(R) = max(min(6%, R), 0)
E[taxable(R)] = E[R·1{0 ≤ R < 6%}] + 6%·P(R ≥ 6%)
             = 0.00467 + 0.06 × 0.5266  =  0.03626
expected drag = 0.03626 × 36%           =  1.31 %/yr
```

against the flat **2.16%/yr** — an **overtax of ~1.65×**. `P(R < 6%) = Φ((6−7)/15) = 47.3%` analytically, i.e. the min binds in roughly half of all simulated years, not rarely. *(A reviewer's simulation reported 50.1% and ~1.25%/yr; the gap is sampling noise at n=500 — σ ≈ 2.2pp — and the analytic figures are used here because they are reproducible.)*

This is not a calibration quibble. It penalises Rent & Invest and biases **every NL Monte Carlo verdict toward Buy**, and MC auto-runs on every config change (ADR-0003), so it is a headline surface, not a detail.

**It clears the primitive bar.** Named region: NL. Named defect: a ~1.65× overtax of the renter's portfolio on an auto-running headline chart. Quantified. One consumption site. No other region needs it — and the split costs one scalar, not a new shape.

**Insertion point.** `engine.py:205`.

```python
# NL box 3 (Wet IB 2001 art. 5.25): taxed on min(deemed, actual) return,
# floored at nil. Both operands are proportional to wealth, so the min
# reduces to a rate comparison and the closed form survives.
# Annual return per year, in the engine's arithmetic monthly convention:
annual_return = eq_rate_monthly.reshape(config.horizon_years, 12).sum(axis=1)
deemed = config.portfolio_deemed_return_pct / 100
taxable = np.clip(np.minimum(deemed, annual_return), 0.0, None)
drag_monthly = np.repeat(taxable * (config.portfolio_drag_rate_pct / 100) / 12, 12)
eq_growth = np.concatenate([[1.0], np.cumprod(1 + eq_rate_monthly - drag_monthly)])
```

`annual_return` is summed, not compounded, because `engine.py:402` and `monte_carlo.py:187` both feed `annual/100/12` — arithmetic monthly division. Summing 12 of them returns the annual draw **exactly** for both callers; compounding would return 7.229% for a 7% input and silently shift the `min` comparison.

**MC correctness — a required property, not an optimisation.** The `min` is evaluated per year against **each path's own drawn return**, inside `_net_value_series`, which every MC path already calls with its own rate array (`monte_carlo.py:189`). No `monte_carlo.py` change. **Substituting a single averaged drag would be wrong**, because the tax feeds back into compounding wealth — averaging the drag and averaging the outcome are different numbers whenever the drag varies, which is the entire point of the primitive.

**The deterministic engine is unaffected, and the golden values are preserved.** With `equity_growth_annual = 7.0`, `annual_return = 0.07 > deemed = 0.06` in every year, so `taxable = 0.06` and the drag collapses to exactly `0.06 × 0.36 = 2.16%/yr` — bit-identical to the single-field version. The US preset has both fields at `0.0`, giving `min(0, R) ≤ 0 → clipped to 0` for every R, so the drag is exactly zero and `eq_growth` is unchanged. Both properties are asserted in §7.2 and §7.3.

**Defect fixed — D4 (annual portfolio drag).** The portfolio compounds **gross** (`engine.py:205-207`); tax is computed at candidate-exit `t` (`engine.py:247-249`) and never fed back into the balance. No annual drag mechanism exists anywhere in the engine.

- **The asymmetry is the whole NL story, and it is structural.** Confirmed against Wet IB 2001 art. 2.14 lid 2: the owner-occupied dwelling sits in **box 1 and is entirely outside box 3**, and the box-1 mortgage does **not** offset box-3 assets. The Netherlands taxes the renter's wealth annually and exempts the buyer's completely. No other country in the set points this hard at one arm.
- **No terminal rate can reproduce it.** A base tax that compounds has an equivalent terminal rate depending on the horizon *and* the realised path — under MC it is not even a single number. Deterministic magnitude at 7% gross over 30 years, in the engine's monthly form: `((1 + 0.07/12 − 0.0216/12)/(1 + 0.07/12))^360 = 0.524757`, a **47.52% terminal shortfall**.

**Statute verification.** 6.00% forfait, 36% rate and the €59,357 allowance are all **enacted** and in force at 2026-01-01 (Wet IB 2001 art. 5.2 lid 2 / 5.5 / 2.13). The 7.78% / €51,396 figures circulating elsewhere were Belastingplan 2026 **as introduced** and were struck by adopted amendment nr. 47 — real documents, never law. Do not reintroduce them.

**Approximation, corrected.** Real box 3 uses the 1 January peildatum (annual); this applies the drag monthly. Annual application gives `((1.07 − 0.0216)/1.07)^30 = 0.542372`; monthly gives `0.524757`. The gap is **3.36%** of the terminal portfolio over 30 years (~3.5% on a fully engine-consistent basis), **not the 0.66% claimed in the previous revision**, which omitted the growth cross-term and understated it ~5×. Direction is unchanged — monthly application overstates the drag, biasing **toward buying** (S10).

**Rejected: modelling the heffingsvrij vermogen (€59,357 pp) — and this rejection is now load-bearing.** With the allowance, the comparison is between *amounts*: `deemed = 6% × (W − 59,357)` against `actual = R × W`, on full wealth, because under tegenbewijs the allowance is **not** available (Hoge Raad). That makes the `min` wealth-dependent, which breaks the closed-form portfolio update at `engine.py:206` and forces a month loop — against `CLAUDE.md`'s no-Python-loops rule. Omitting the allowance is what keeps both operands proportional to `W`, so the `min` reduces to a pure rate comparison and the closed form survives. Verified effective drags **with** the allowance: **€250k → 0.99%, €500k → 1.12%, €1M → 1.19%**, against this model's ~1.31%. The residual overstatement is **0.12–0.32pp**, biased toward buying (S2) — an order of magnitude smaller than the old 6–8% figure, because the tegenbewijs fix absorbs most of what the allowance used to be compensating for. The schuldendrempel (€3,800 / €7,600) is likewise not modelled; the box-1 mortgage does not offset box 3, so it is inert here.

**Rejected: using P5 for the German Vorabpauschale.** ~0.41%/yr for 2026 (Basiszins 3.20%), but it is **creditable against tax at exit** — a timing drag, not a permanent tax. P5 models a permanent tax, so applying it to Germany would overstate the German cost by construction. DE ships both fields at `0.0`. The clearest case in the set of a primitive that *exists* and still should not be used.

---

### 2.6 D6 — First-time buyer: zero engine primitives

FTB relief changes only **which buyer-cost numbers apply**. That is region data. Adding a `first_time_buyer` field to `SimulationConfig` would create a config field the engine cannot consume — the relief depends on region-specific statute the engine must never know (ADR-0007).

**Design.** Each bundle gains a sibling of `taxPrimitives`:

```python
"firstTimeBuyerOverrides": {"closingCostBuyerPct": 0.0, "closingCostBuyerAmount": 3100.0},
```

The toggle applies or omits that dict when a region is applied (`inputs.js:140`). DE and US ship `{}` — the toggle is visible and inert, which is exactly what keeps it consistent across regions per locked decision 3.

**Share-URL behaviour.** The toggle changes only real config fields, so a shared URL reproduces the numbers exactly. The toggle's own on/off state is *not* persisted — identical to the existing outlook pills (`inputs.js:148-160`), which also apply a preset without persisting which pill was pressed. Consistent with the shipped design; no new machinery.

**Magnitudes justifying default-TRUE:** UK £0 vs £4,455 at the preset price. NL startersvrijstelling 0% vs 2% (age 18–35, own occupancy, value ≤ €555,000) — a **~€9,000** swing. FR primo-accédant carve-out from the departmental increase, worth **~0.51pp** (*not* the 1.5pp claimed in earlier research — the arithmetic was checked and corrected). DE: none enacted.

### 2.7 D8 — Sale CG regime: keep, do not deprecate

All four new regions resolve to `fully_exempt`: FR (CGI art. 150 U II 1, **no duration condition**), DE (§23 Abs.1 Nr.1 Satz 3 EStG owner-occupier limb — exempt at **any** holding period), NL (eigen woning, box 1), UK (Private Residence Relief). Consequence: **`exempt_after_years` is used by no shipped preset.**

**Decision: keep it, change nothing.** Removing it means touching `models.py:10` (the `Literal`), `models.py:256` (the hand-duplicated tuple), `engine.py:241-243`, `fields.js:27` (the select options), and the tests — all for zero user benefit, on a branch that remains reachable through the Advanced drawer for a user outside the five regions. `CLAUDE.md`: don't refactor things that aren't broken.

**Recorded trap, not fixed:** `models.py:256` hand-duplicates the regime tuple that `models.py:10` declares via `Literal`. Adding a fourth regime value requires editing both or it is silently rejected at validation. This change adds no regime value, so the trap does not bite here. Noted for whoever does.

### 2.8 D9 — Mortgage product: disclosure, plus one real correction

The engine holds one fixed rate for the full term (`engine.py:155`). Real conventions differ: Germany has **no mass-market 25-year fix** — 10/15/20yr Zinsbindung then Anschlussfinanzierung, plus a §489 BGB penalty-free exit right after 10 years. UK convention is 2/5yr fixes reverting to SVR (currently 6.60%, **195bp** above the 5yr fix). NL is similar.

**Treatment: a `notes` list per bundle, rendered in the methodology footer.** No engine change, no refinancing model. Explicitly rejected: modelling reversion. It needs a forward-rate assumption the tool has no basis for and would be the single largest unfounded assumption in the app.

**But one part of D9 is not disclosure — it is a maths input that the research bundle gets wrong.** `mortgage_term_years` drives amortisation (`engine.py:156, 170-172`). Shipping DE with `mortgageTermYears: 15` would amortise the loan fully over 15 years, inflating the German monthly payment far above reality and badly biasing DE toward renting. The 15 is the **Zinsbindung**, not the amortisation term. Corrected values in §4.0.

---

## 3. Rejected primitives

Each was a plausible candidate. Each is rejected against the simplicity constraint, with the fallback stated.

| Rejected | Why | Fallback |
|---|---|---|
| **Band-schedule buyer cost** (`list[[threshold, rate]]`) | Non-scalar, so it needs a hand-written `api.py` validation branch (§6.2), a new frontend widget shape (only slider/segmented/checkbox/select exist, `inputs.js:22-107`), and a share-URL encoding. Used by exactly one region. | P4's two-parameter form is **exact** over £250k–£925k. |
| **`levy_escalation_rate`** | A sixth primitive to split one existing inflation knob. `cost_inflation_rate` is already user-exposed (`fields.js:23`). | Document the FR residual (recovers ~30% of the gap); §8. |
| **`insurance_paid_by_occupier`** | No region needs it. UK buildings insurance is the landlord's; DE condo insurance is already €0. | — |
| **`closing_cost_seller_amount`** | No named, quantified defect. All four seller costs (FR 6.0%, DE 4.0%, NL 1.4%, UK 1.75%) are genuinely percentage-shaped. | — |
| **Portfolio tax wrapper primitive** (ISA/PEA/Sparer-Pauschbetrag) | Locked decision 4. PEA is EU-equity-only, so it assumes a portfolio the user is not buying; ISA and Sparer-Pauschbetrag caps bind inside the horizon, so a flat 0% is wrong past year ~3. | Plain taxable everywhere, including the US. Understatement documented in §8 and in every bundle's `notes`. |
| **Heffingsvrij vermogen in P5** | Breaks the vectorised closed form; needs a month loop. | Documented 6–8% bias toward buying (§8). |
| **P5 applied to the German Vorabpauschale** | It is creditable at exit — a timing drag. P5 models a permanent tax; using it would overstate the German cost. | DE drag = 0. |
| **FTB as a `SimulationConfig` field** | The engine cannot consume it without knowing region statute. A field the engine ignores is semantic pollution that survives `config_to_dict` round-trip tests. | Region-bundle overrides + UI pill (§2.6). |
| **UK FTB £500k cliff in the engine** | Price-conditional per-country logic in `_net_value_series` — the thing ADR-0007 exists to prevent. | UK `notes`; quantified in §8. |
| **`sale_cg_regime` deprecation** | Five files touched for zero user benefit. | Keep; §2.7. |
| **German Bundesland sub-region selector** | Provenance does not support it (§8.4): of 16 GrESt rates only Bremen is primary-sourced. Also a second selector dimension on a UI capped at 8 visible inputs. | Single national default at NRW 6.5%, labelled. The 3pp spread (≈€12,000 on €400k) is recorded as a known gap. |
| **Mortgage reversion / refinancing model** | Needs an unfounded forward-rate assumption. | Per-region `notes` (§2.8). |
| **Rent-regulation modelling** (encadrement, Mietpreisbremse) | Would need a per-region rent-growth cap; the outlook presets own rent inflation by design. | Known gap (§8). |

---

## 4. Region bundle data

### 4.0 Bundle contract (enforced by test, §7.4)

Four hard rules, each preventing a real failure mode:

1. **Every bundle must supply the complete `taxPrimitives` key set.** `applyPreset` is `Object.assign` (`state.js:52-55`), so any key a bundle omits **leaks from the previously selected region**. Switching US → UK today would carry `saleCgExemptAmount: 250000` into the UK config: inert under `fully_exempt`, but live the instant a user changes the regime, under a UK label. Same rule for `typical`.
2. **Regions must not set the outlook trio** (`propertyAppreciationAnnual`, `equityGrowthAnnual`, `rentInflationRate`). Those belong to the outlook presets (`inputs.js:8-12`, redesign-spec §2). Two preset systems writing the same keys would fight, and whichever pill was clicked last would win non-deterministically from the user's point of view.
3. **`mortgageTermYears` is the amortisation term.** Moved into `typical` (all four values are already in the segmented options, `fields.js:12`):

| Region | Term | Basis |
|---|---|---|
| FR | 25 | Genuinely a 25-year fully-amortising loan. |
| DE | 30 | 4.0% rate with the conventional 2% anfängliche Tilgung fully repays in ~29 years. The 15 in the research is the **Zinsbindung**. |
| NL | 30 | Annuity; also the statutory 30-year interest-deduction period. |
| UK | 25 | 5yr fix on a 25-year amortisation. The 5 is the fix, not the term. |
| US | 30 | Unchanged. |

4. **Every bundle value must lie inside its `INPUT_DEFS` range** (`fields.js`), and every enum value inside its allowed set. **This rule is the real defect the previous revision was missing**, and it caught a live one.

   **The violation: DE `closingCostBuyerPct: 12.07` against `fields.js:18` `max: 10`.** `state.js:84-89` drops out-of-range values on share-URL restore and `readUrl` falls back to `DEFAULT_CONFIG`, i.e. the **US 3.0%**. A shared German link therefore silently reopens with buyer costs 9.07pp low — **€30,747 on €339,000, toward buying, with no visible symptom** (the number simply reads 3.0%). The Advanced slider also cannot represent 12.07 at all. **Fix: widen `fields.js:18` to `max: 15`.** A reviewer range-checked all four bundles against every bound; this is the only violation, but the absence of the rule is what let it through.

   **Grid sub-rule (SHOULD, not MUST).** Values off the slider's `step` grid make the thumb and the label disagree, and the first drag mutates the config. Affected values **include** `marginalTaxRatePct: 37.56` (step 1) and `propertyTaxRate: 0.2815` (step 0.05); this list is illustrative, not exhaustive — several other bundle values sit off their grids, which is tolerated by design because this is a SHOULD-rule, not the MUST-rule above. **Fix the two named:** `marginalTaxRatePct` step → 0.01, `propertyTaxRate` step → 0.0005. `propertyPrice: 289106` (step 5000) is left off-grid **deliberately** — it is a sourced HM Land Registry figure and the §7.4 SDLT fixture asserts against it; the label renders the true config value (`inputs.js:39`) and only the thumb position rounds.

Confidence legend: **H** primary-sourced · **M** secondary or derived, reproducible · **M-H** credible institutional secondary source · **L** derived with a wide band (ships, but the caveat goes in the bundle's `notes` and in §8). No shipped value is unsourced; nothing here gates a region.

---

### 4.1 France — Lyon, 65 m² existing apartment

```python
{
    "id": "fr",
    "label": "France (Lyon)",
    "available": True,
    "currencySymbol": "€",
    "typical": {
        "propertyPrice": 290000,      # M — Lyon existing apartment
        "monthlyRent": 812,           # M — see note
        "mortgageRateAnnual": 3.45,   # M — aggregator-corroborated only
        "mortgageTermYears": 25,      # H — standard FR amortisation
    },
    "taxPrimitives": {
        "closingCostBuyerPct": 7.468,      # H — DMTO 6.318 + CSI 0.10 + emoluments ~1.05
        "closingCostBuyerAmount": 1300.0,  # H — débours
        "closingCostSellerPct": 6.0,       # M
        "propertyTaxRate": 0.0,
        "annualPropertyLevy": 1220.0,      # M — 0.42% x 290,000; Lyon combined TFPB 32.44%
        "levyPaidByOccupier": False,       # H — taxe d'habitation on main residences abolished 2023
        "annualHomeInsurance": 220.0,      # M — multirisque habitation
        "annualMaintenancePct": 0.0,
        "annualMaintenanceAmount": 1300.0, # L — see caveat
        "interestDeductionEnabled": False, # H — abolished 2011
        "marginalTaxRatePct": 0.0,
        "levyDeductionCap": 0.0,
        "saleCgRegime": "fully_exempt",    # H — CGI art. 150 U II 1, no duration condition
        "saleCgExemptAmount": 0.0,
        "saleCgExemptAfterYears": 30,      # inert; the PS taper period, recorded for documentation
        "saleCgRatePct": 36.2,             # H — 19% IR + 17.2% PS
        "portfolioCgRatePct": 31.4,        # H — 12.8% PFU + 18.6% PS
        "portfolioDeemedReturnPct": 0.0,
        "portfolioDragRatePct": 0.0,
    },
    "firstTimeBuyerOverrides": {"closingCostBuyerPct": 6.958},  # H — -0.51pp primo-accédant carve-out
}
```

Derivation checks: non-primo total at €290,000 = `7.468% × 290,000 + 1,300 = €22,957 = 7.916%`, inside the verified 7.90–8.00% band. Primo = `€21,478 = 7.406%`, matching the verified ~7.4%.

**Rent — corrected, do not reintroduce the old figure.** €812/mo, from Observatoires Locaux des Loyers 2024 microdata (n = 9,362, zone-3 median €12.50/m²). The superseded €1,100 was above the *encadrement* majored ceiling in **every** Lyon zone. P/R = 29.8.

**`saleCgRatePct: 36.2` — correction.** The 2026 social-levy rise does **not** apply to plus-values immobilières, which stay at 17.2%. `portfolioCgRatePct: 31.4` does move (CSG 9.2 → 10.6 via LFSS 2026, LOI 2025-1403 art. 12), superseding ADR-0007's "30% PFU" (§9).

**Maintenance caveat (L).** €1,300 is the owner-only estimate. The research figure (copropriété charges €25/m²/yr + fonds travaux) **conflates consumption a French tenant also bears** — in France a large share of copropriété charges are *récupérables* from the tenant. The shipped number is the non-récupérable + fonds-travaux estimate. If it still includes récupérables, it overstates the owner's cost and biases toward renting. Listed in §8 as a research item that should be closed but does not block ship, because the figure is bounded above by the full charge and below by the fonds travaux alone.

---

### 4.2 Germany — Köln, 80 m² existing condo

```python
{
    "id": "de",
    "label": "Germany (Köln)",
    "available": True,
    "currencySymbol": "€",
    "typical": {
        "propertyPrice": 339000,      # H — €4,239/m² x 80 m² = €339,120, rounded
        "monthlyRent": 992,           # H — €12.40/m² x 80 m², same matched pair
        "mortgageRateAnnual": 4.0,    # M — 15yr Zinsbindung; see notes
        "mortgageTermYears": 30,      # M — 2% anfängliche Tilgung => ~29yr full repayment
    },
    "taxPrimitives": {
        "closingCostBuyerPct": 12.07,      # M — GrESt 6.5 (NRW) + Notar/Grundbuch 2.0 + Makler 3.57
        "closingCostBuyerAmount": 0.0,
        "closingCostSellerPct": 4.0,       # M
        "propertyTaxRate": 0.0,
        "annualPropertyLevy": 339.0,       # L — ~0.1% of market value; Köln Hebesatz 550% for 2026
        "levyPaidByOccupier": True,        # H — BetrKV §2 Nr.1, umlagefähig
        "annualHomeInsurance": 0.0,        # H — condo: inside Hausgeld, and umlagefähig (BetrKV §2 Nr.13)
        "annualMaintenancePct": 0.0,
        "annualMaintenanceAmount": 1700.0, # M — §28 Abs.2 II.BV €9.00/m² x 80 + Verwalter + Sondereigentum
        "interestDeductionEnabled": False, # H — owner-occupied
        "marginalTaxRatePct": 0.0,
        "levyDeductionCap": 0.0,
        "saleCgRegime": "fully_exempt",    # H — §23 Abs.1 Nr.1 Satz 3 EStG, owner-occupier limb
        "saleCgExemptAmount": 0.0,
        "saleCgExemptAfterYears": 10,      # inert; the §23 speculation period for non-owner-occupied
        "saleCgRatePct": 0.0,              # inert; a taxable DE sale is taxed at the personal income rate
        "portfolioCgRatePct": 26.375,      # H — 25% x 1.055 Soli
        "portfolioDeemedReturnPct": 0.0,   # Vorabpauschale deliberately not modelled (§2 P5)
        "portfolioDragRatePct": 0.0,
    },
    "firstTimeBuyerOverrides": {},         # H — no FTB relief enacted
}
```

**Price and rent — shipped values changed from the previous revision to reproduce their own derivation.** The research's headline pair (€345,000 / €1,020) does **not** reconcile with the matched-pair inputs it cites: €4,239/m² × 80 m² = **€339,120**, and €12.40/m² × 80 m² = **€992**. The headline price is 1.7% above what its own €/m² implies.

**Resolution: ship the derivation-consistent pair (€339,000 / €992).** The decisive evidence is the price-to-rent ratio: `339,120 / (992 × 12) = 28.49`, which reproduces the research's own stated **P/R of 28.5 exactly**, while the headline pair gives 28.2. A derivation that regenerates the source's headline ratio is more trustworthy than a rounded price that does not. Both figures come from the same matched pair over the **same 259 sold-and-rented condos**, so this is an internal-consistency fix, not a new source.

*Flagging this as a judgement call that goes beyond "note the discrepancy":* the alternative was to keep €345,000 and record a 1.7% unreconciled gap. That was rejected because the gap silently propagates into `annualPropertyLevy`, `closingCostBuyerPct` and the §7.4 fixture, and a spec that ships a number contradicting its own stated derivation invites exactly the kind of "correction" §4.0 rule 1 exists to prevent. **Do not reintroduce €400,000** (the earlier superseded figure) or €345,000.

The P/R of 28.5 is genuine and **not a Kaltmiete artefact** — on the most conservative Warmmiete basis it is 36.6.

**Hebesatz — corrected.** Köln 550% for 2026. Superseded: 475% (TY2025) and 515% (2012–2024).

**`annualPropertyLevy: 339.0` is the weakest number in the whole set (L).** The post-reform effective rate is unsourceable at precision, and ~0.1% is likely **understated** at a 550% Hebesatz. It is roughly one-twelfth the US 1.2%, so even a 2× error moves the German verdict by ~€10k over 25 years — material but not decision-flipping at a €339,000 price. Flagged in §8 and in the DE `notes`.

**`closingCostBuyerPct` conditionality.** The Makler buyer-half (3.57% incl. USt) is **conditional** — a maklerfrei sale drops the total to **8.50%**, a €12,102 swing on this price. Recorded in `notes`, not modelled as a toggle (rejected: it is a transaction circumstance, not a tax primitive, and the Advanced slider already exposes the field).

**ADR-0007 correction.** "Germany: sale tax-free after a 10-year hold" is **wrong for the owner-occupied case this tool models** — §23 Abs.1 Nr.1 Satz 3 exempts at any holding period. See §9.

---

### 4.3 Netherlands — national average existing home

```python
{
    "id": "nl",
    "label": "Netherlands",
    "available": True,
    "currencySymbol": "€",
    "typical": {
        "propertyPrice": 490000,      # H — CBS, verified 487,383
        "monthlyRent": 2300,          # L — derived, ±11% band; see caveat
        "mortgageRateAnnual": 4.3,    # M — non-NHG (above the €470,000 NHG cap)
        "mortgageTermYears": 30,      # H — annuity; also the 30yr deduction period
    },
    "taxPrimitives": {
        "closingCostBuyerPct": 3.2,        # H — overdrachtsbelasting 2% + ~1.2% other
        "closingCostBuyerAmount": 0.0,
        "closingCostSellerPct": 1.4,       # M
        "propertyTaxRate": 0.2815,         # H — 0.15% owner charges + 0.1315% EWF; derivation §5.5
        "annualPropertyLevy": 0.0,
        "levyPaidByOccupier": False,
        "annualHomeInsurance": 550.0,      # M — opstalverzekering; Moving.nl. €1.30 per €1,000
                                          #     herbouwwaarde x ~€350k rebuild x 1.21 assurantiebelasting
        "annualMaintenancePct": 1.0,      # M-H — Nibud "ruim 1%"/yr; VEH 1% of WOZ. Value-proportional
                                          #     by source; kept in that unit deliberately (§2 P3)
        "annualMaintenanceAmount": 0.0,
        "interestDeductionEnabled": True,  # H
        "marginalTaxRatePct": 37.56,       # H — 2026 tariefsaanpassing maximum, NOT the 49.5% top rate
        "levyDeductionCap": 0.0,           # H — NL levy is not deductible; REQUIRES the §6.1 sentinel fix
        "saleCgRegime": "fully_exempt",    # H — eigen woning, box 1
        "saleCgExemptAmount": 0.0,
        "saleCgExemptAfterYears": 0,
        "saleCgRatePct": 0.0,              # H — no securities/property CGT
        "portfolioCgRatePct": 0.0,         # H — the burden is box 3, not CGT
        "portfolioDeemedReturnPct": 6.0,   # H — Wet IB 2001 art. 5.2 lid 2, enacted, in force 2026-01-01
        "portfolioDragRatePct": 36.0,     # H — art. 5.5. Taxed on min(deemed, actual), floored at nil (art. 5.25)
    },
    "firstTimeBuyerOverrides": {"closingCostBuyerPct": 1.2},  # H — startersvrijstelling 0% vs 2%
}
```

**Maintenance and insurance: sourced, and NL ships (M).** Insurance €550/yr is derived from Moving.nl (€1.30 per €1,000 herbouwwaarde against a ~€350k rebuild value, × 1.21 assurantiebelasting) — the same commercial-aggregator basis as FR's €220 and UK's £310. Maintenance is 1.0% of value, cited to **Nibud** (the Dutch national budget institute, "ruim 1%" per year) and **Vereniging Eigen Huis** (1% of WOZ) — credible secondary sourcing on a par with the copropriété basis behind FR's figure and stronger than the commercial basis behind FR's insurance figure. There is no defensible standard on which NL gets gated and FR ships.

**It stays on the percentage path, and that is the substantive point.** The objection worth making here is not that NL's maintenance figure is *missing* — it isn't — but that it would be **unsound in unit** if mechanically converted. 1.0% × €490,000 = €4,900/yr; freezing that as an absolute number at the default price both (a) discards the rescaling behaviour Nibud and VEH actually assert, and (b) launders a value-proportional convention into the storage unit D7 introduced to escape it. So NL ships `annualMaintenancePct: 1.0` (§2 P3). The unit tension is real and is recorded as S16 in §8.1 rather than hidden inside a converted constant.

**One cross-region inconsistency to be aware of when reading the four maintenance figures side by side.** They are not all the same measurement: NL 1.0% (≈ €4,900) and the US 1.0% are **recommended budgeting reserves** including amortised capital replacement (roof, kozijnen, cv-ketel); UK £900 is **observed annual spend** from a recall-based survey; DE €1,700 and FR €1,300 are **owner-only recurring charges** with the tenant-recoverable share stripped out. The bases differ by construction, so a reader comparing €4,900 against £900 is not comparing like with like. Recorded as S17 in §8.1.

**`levyDeductionCap: 0.0` is unrepresentable on today's wire.** `api.js:7` maps client `0 → null`, and `null` means *uncapped* (`models.py:59-61`). Left unfixed, NL would silently deduct its own levy: `0.2815% × 490,000 × 37.56% = €518/yr`, ~**€5,200** wrongly credited to the buy arm over a 10-year horizon, in the **wrong direction** (NL's levy is genuinely not deductible). Fix in §6.1.

**Rent (L).** €2,300/mo free-sector is an admitted derivation with a ±11% band, because free-sector stock comparable to a 120 m² owner-occupied home barely exists. Fact-checking found the blended rate **overstates** rent for a large home, so **true P/R is higher than the stated 17.8** — i.e. the shipped bundle is biased toward buying. §8.

**Deduction limits — both satisfied automatically, no modelling needed.** The 30-year maximum deduction period cannot be breached: the mortgage-term picker caps at 30 (`fields.js:12`) and the balance freezes at payoff, so `interest == 0` thereafter (`engine.py:171-178`) — there is no interest past year 30 to over-deduct, even at the 40-year horizon ceiling. The post-2013 annuity/linear repayment requirement is likewise inert, because the engine's mortgage **is** an annuity (`npf.pmt`, `engine.py:170`). *(An earlier revision claimed a horizon > 30 over-deducts; that scenario is unreachable, and the corresponding S9 row is withdrawn in §8.1 for the same reason.)* Hillen (71.867% in 2026, stepping **4.80pp** for 2026 — corrected from the "4.85pp/yr" claim; it was 3.3333pp/yr through 2025 then a one-off accelerated step, completing **2041**, not 2048) is inert at the default because interest exceeds EWF throughout — condition and threshold in §5.5.

---

### 4.4 United Kingdom (England & NI) — England semi-detached

```python
{
    "id": "uk",
    "label": "United Kingdom (England & NI)",
    "available": True,
    "currencySymbol": "£",
    "typical": {
        "propertyPrice": 289106,      # H — HM Land Registry UKHPI, England semi-detached, Apr 2026
        "monthlyRent": 1431,          # H — ONS PIPR, England semi-detached, May 2026
        "mortgageRateAnnual": 4.65,   # M — 5yr fix, 75% LTV
        "mortgageTermYears": 25,      # amortisation; the 5 is the fix (§2.8)
    },
    "taxPrimitives": {
        "closingCostBuyerPct": 5.0,        # H — SDLT marginal slice 250k-925k
        "closingCostBuyerAmount": -6900.0, # H — SDLT nil-rate intercept (-10,000) + ~3,100 fixed fees
        "closingCostSellerPct": 1.75,      # H — agent 1.42% VAT-INCLUSIVE + legal
        "propertyTaxRate": 0.0,
        "annualPropertyLevy": 2392.0,      # H — England avg Band D 2026/27 (2,343 excl. parish precepts)
        "levyPaidByOccupier": True,        # H — LGFA 1992 s.6(2), resident liable
        "annualHomeInsurance": 310.0,      # M
        "annualMaintenancePct": 0.0,
        "annualMaintenanceAmount": 900.0,  # M — ONS Family Spending FYE2025, LOWER bound
        "interestDeductionEnabled": False, # H — MIRAS withdrawn 2000
        "marginalTaxRatePct": 0.0,
        "levyDeductionCap": 0.0,
        "saleCgRegime": "fully_exempt",    # H — Private Residence Relief
        "saleCgExemptAmount": 0.0,
        "saleCgExemptAfterYears": 0,
        "saleCgRatePct": 24.0,             # inert; the residential rate absent PRR
        "portfolioCgRatePct": 24.0,        # H — unwrapped higher rate (18% basic)
        "portfolioDeemedReturnPct": 0.0,
        "portfolioDragRatePct": 0.0,
    },
    "firstTimeBuyerOverrides": {"closingCostBuyerPct": 0.0, "closingCostBuyerAmount": 3100.0},
}
```

**Scope, and why the label carries it.** SDLT applies to **England & NI only**. Scotland uses LBTT and Wales uses LTT, with different bands and **no FTB relief in Wales**. A bundle labelled plain "United Kingdom" would silently misprice ~16% of the population. The label is part of the correctness of this bundle, not cosmetics.

Derivation check, non-FTB at £289,106: `0.05 × 289,106 − 6,900 = £7,555.30`, of which SDLT = £4,455.30 ✓ and fees = £3,100 ✓. FTB: `0 × 289,106 + 3,100 = £3,100`, SDLT = £0 ✓.

**Seller cost — do not "add VAT".** The 1.42% agent fee is already VAT-inclusive; the Property Ombudsman has required VAT-inclusive quoting since October 2016. Adding 20% double-counts.

**Surcharges not modelled** (both are `+pp` on `closingCostBuyerPct` if a user needs them, and both are noted): additional-dwelling **+5pp** (raised from 3pp on 31 Oct 2024) and non-resident **+2pp**. Rejected as primitives — they describe the buyer, not the region, and the tool models a single owner-occupied primary residence.

**Required `notes` entries** (all four divergences of §2 P4 must reach the user, not just this document): SDLT is modelled exactly between £250,000 and £925,000 and **under-charges above £925,000** (£63,750 at £2m); FTB relief is **0% only to £300,000**, then 5% to £500,000, and is **withdrawn entirely above £500,000**; the mortgage rate is a 5-year fix held for the full 25-year amortisation, with SVR currently 195bp above it.

**Maintenance is a lower bound.** ONS is recall-based and under-captures lumpy repairs. Bias: toward buying. §8.

---

### 4.5 United States — unchanged, plus inert new fields

The US bundle (`regions.py:14-39`) gains exactly the six new keys at their defaults and `mortgageTermYears: 30` in `typical`. Every existing value is untouched. This is what the Phase-1 regression gate (§7.2) asserts.

```python
"typical":       { ..., "mortgageTermYears": 30 },
"taxPrimitives": { ..., "closingCostBuyerAmount": 0.0, "annualPropertyLevy": 0.0,
                        "levyPaidByOccupier": False, "annualMaintenanceAmount": 0.0,
                        "portfolioDeemedReturnPct": 0.0, "portfolioDragRatePct": 0.0 },
"firstTimeBuyerOverrides": {},
```

---

## 5. Engine changes — the maths

### 5.1 Buyer transaction cost (`engine.py:152`)

```
buyer_closing = max(property_price × (closing_cost_buyer_pct / 100)
                    + closing_cost_buyer_amount, 0)
initial_outlay = down_payment + buyer_closing
```

The clamp is load-bearing: with the UK non-FTB pair (5.0, −6,900) the expression turns negative below **P = 138,000**, and the price slider floor is 50,000 (`fields.js:9`). Without the clamp, `net_buy(0)` (`engine.py:253-262`) would report a *profit* on an instantaneous buy-and-sell.

### 5.2 Ongoing ownership costs (`engine.py:180-190`)

```
cost_index(t)  = (1 + cost_inflation_rate / 12)^(t−1)                       t ≥ 1

levy(t)        = home_value(t−1) × (property_tax_rate / 100) / 12
                 + (annual_property_levy / 12) × cost_index(t)

insurance(t)   = (annual_home_insurance / 12) × cost_index(t)               (unchanged)

maintenance(t) = home_value(t−1) × (annual_maintenance_pct / 100) / 12
                 + (annual_maintenance_amount / 12) × cost_index(t)

housing_cost_buy(t) = payment(t) + levy(t) + insurance(t) + maintenance(t)  (unchanged)
```

`cost_index` is hoisted out of the existing insurance line because three cost lines now need it. This is a refactor of lines already being edited — inside the "clean up only your own mess" boundary.

### 5.3 Occupier-borne levy (`engine.py:196-197`)

```
housing_cost_rent(t) = rent_level(t−1)                          t ≥ 1
                     + levy(t)      if levy_paid_by_occupier
```

**Equivalence proof (asserted in test, §7.3). Note what is being compared:** not flag-off against flag-on — those legitimately differ — but `(levy = L, occupier = True)` against `(levy = 0)`. `surplus = (b+L) − (r+L) = b − r`, so `contrib_rent`/`contrib_buy` (`engine.py:200-202`), both portfolios and both bases are unchanged; `max(b+L, r+L) = max(b,r) + L`, so `cash_committed` (`engine.py:212-214`) rises by `ΣL` on both arms; therefore `net_buy` and `net_rent` each fall by `ΣL` and `net_buy − net_rent` is unchanged **in exact arithmetic**, equal up to floating-point rounding in the engine. Requires the levy to be non-deductible, which holds for both regions that set the flag (§2 P2).

### 5.4 Annual portfolio drag (`engine.py:205`) — the maths written out

A wealth tax at annual rate `d` on the start-of-period balance:

```
V(t) = V(t−1)·(1 + g) − V(t−1)·d = V(t−1)·(1 + g − d)
```

so it is exactly a reduction in the compounding rate, with no change to the closed form (`FORMULAS.md` §5). With the `min()` of art. 5.25 evaluated **per year `y`**, against that year's own return:

```
R(y)      = Σ_{m in year y} eq_rate_monthly[m]        # arithmetic; matches engine.py:402
taxable(y) = max( min(deemed, R(y)), 0 )              # art. 5.25 lid 1 + lid 2
d_m(y)     = taxable(y) × (portfolio_drag_rate_pct / 100) / 12

G(0)      = 1
G(t)      = ∏_{m=1..t} (1 + eq_rate_monthly[m] − d_m(year of m))

rent_portfolio(t) = G(t) × ( initial_outlay + Σ_{m=1..t} contrib_rent(m)/G(m) )
buy_portfolio(t)  = G(t) × Σ_{m=1..t} contrib_buy(m)/G(m)

basis_rent(t), basis_buy(t)   unchanged — contributions, not returns
```

Both operands of the `min` are proportional to wealth (deemed `= deemed_rate × W`, actual `= R × W`), so the comparison reduces to rates and `G(t)` remains a pure cumulative product — no month loop, no wealth feedback term. **This is only true because the heffingsvrij vermogen is not modelled**; see §2 P5.

Applied to **both** portfolios; the NL asymmetry (renter taxed, buyer's box-1 dwelling exempt) emerges from the portfolios' different sizes, not from a branch.

**Terminal effect at NL defaults, `g = 7%`, deemed 6%, rate 36%, 30 years.** In the deterministic engine `R(y) = 0.07 > 0.06` every year, so `taxable = 0.06` and `d = 2.16%/yr`. The engine applies it **monthly** at the `engine.py:205` insertion point, so the monthly form governs:

```
monthly (what the engine computes):
  ((1 + 0.07/12 − 0.0216/12) / (1 + 0.07/12))^360 = 0.524757   →  47.52% shortfall

annual (what real box 3 does, peildatum 1 Jan):
  ((1 + 0.07 − 0.0216) / (1 + 0.07))^30            = 0.542372   →  45.76% shortfall
```

**The previous revision stated 0.5434 / 45.7% and was wrong on both counts** — it evaluated the annual expression incorrectly (the correct annual value is 0.542372) *and* used the annual form where the engine applies the drag monthly. The engine-correct figure is **0.524757 / 47.52%**. The monthly-vs-annual gap is **3.36%**, not the 0.66% previously claimed (S10).

**No clamp is needed on `1 + g − d_m`.** `models.py:213-217` floors `equity_growth_annual` at −50 (monthly −0.04167); a −99% annual MC draw gives monthly −0.0825. And `taxable ≥ 0` by the lid-2 floor with `taxable ≤ deemed`, so `d_m ≤ deemed × rate / 12 ≤ 1.0 × 1.0 / 12 = 0.0833` at the validation ceilings. Worst case `1 − 0.0825 − 0.0833 = 0.834`, comfortably above −1. Recorded so the next reader does not add a defensive clamp that would silently alter results.

### 5.5 The NL eigenwoningforfait — an exact identity, not a fudge

EWF adds 0.35% of WOZ to box-1 income, taxed at the marginal rate and netted against deductible interest. In cash terms that is **identical** to a levy of:

```
0.35% × 37.56% = 0.13146% of WOZ
```

Total NL ad-valorem levy:

```
propertyTaxRate = 0.15%  (owner-specific public charges)
                + 0.13146%  (EWF, expressed as its cash equivalent)
                = 0.28146%  →  ships as 0.2815
```

This is **not** a "fake effective rate" of the kind locked decision 2 forbids — it is an exact algebraic reduction, valid under two stated conditions, both of which hold at the NL defaults:

1. **Deductible interest exceeds EWF throughout** (so Hillen relief is inactive). EWF = 0.35% × 490,000 = **€1,715/yr**. Year-1 interest on an 80% LTV at 4.3% ≈ **€16,900**. Hillen would only bite if the balance fell below `1,715 / 0.043 = €39,900`, i.e. a down payment above **91.9%**. A user who sets that gets an overstated NL cost; noted in the NL `notes`.
2. **The same marginal rate applies to the addback and the deduction** — true by construction, both at 37.56%.

**Rejected alternative:** a `deduction_income_addback` primitive. It would be a sixth field, used by one region, to express something an existing field already expresses exactly. **Also rejected:** the research's original 0.27% hack, which folded in an unexplained 0.12% — the number above is derived, checkable, and 0.0015pp different.

NL therefore keeps the **ad-valorem** levy path with `annualPropertyLevy = 0`. This is deliberate and correct: WOZ is a market-value assessment (waardepeildatum 1 January of the prior year), so unlike FR's 1970 VLC, DE's Grundsteuerwert, or UK's 1991 bands, the NL base genuinely does track prices. **The research's D2 claim is materially wrong for the Netherlands** — the defect there is a one-year lag, which is second-order and not worth a primitive.

### 5.6 Tornado-chart repair (`monte_carlo.py:268`) — required in Phase 1

`_compute_sensitivity` perturbs `property_tax_rate` by ±0.5 (`monte_carlo.py:268`), with the low side floored at 0.001 (`monte_carlo.py:285`). For UK, DE, and FR — which ship `propertyTaxRate: 0.0` — this manufactures a bar showing sensitivity to a levy form those regions do not have. Quantified for the UK: 0.5% × £289,106 = **£1,445/yr** of phantom levy, which would rank high on an 8-bar tornado.

**The zero-skip alone is only half a fix, as the previous revision left it.** NL's base is **0.2815** — non-zero, so it would still be perturbed by an absolute ±0.5pp, i.e. a range of `[0.001, 0.7815]`, a **±178% relative swing** implying WOZ regimes the Netherlands does not have.

**Fix (two parts, ~4 lines):**

1. **Make the levy delta proportional to its own base**, calibrated so the US is preserved: `delta = base_val × (0.5 / 1.2)`. At the US base of 1.2 this is 0.5, exactly the current absolute delta; NL gets ±0.117 (±41.7%); every region is perturbed by a proportionate amount rather than a US-sized one.
2. **Keep the zero-skip**, because a proportional delta at a zero base gives `delta = 0`, and `monte_carlo.py:285` would then floor the low side at 0.001 while the high side stays 0 — producing a tiny *inverted* bar rather than no bar.

**The fix is free for the US preset — verified, not assumed.** `1.2 × (0.5/1.2)` evaluates to **exactly `0.5`** in IEEE double (`Decimal(1.2*(0.5/1.2)) == 0.5`), because the US `property_tax_rate` base of 1.2 is precisely the value that makes the proportional form collapse to the original constant. The US perturbation bounds stay **0.7 and 1.7**, bit-identical to today's fixed ±0.5, while NL's 0.2815 base correctly scales to ±0.117 instead of a ±178% relative swing. **No regression-gate relaxation is required or permitted** — §7.2 item 3 stays bit-identical.

*(An earlier revision of this spec claimed the product was `0.5000000000000001` and relaxed the gate to `rel_tol=1e-12` on that basis. The premise was false. A gate loosened for a reason that turns out to be false is a gate nobody ever tightens again, so the assertion is restored and made explicit below.)*

**Rejected:** a generic "skip any zero-valued parameter" rule (blunter than the reason justifies); adding `annual_property_levy` as a ninth tornado bar (speculative — the flat levy is a minor driver, and the chart is already at 8); and leaving the delta absolute with a disclosure (the bar is auto-run and ranked by magnitude, so a wrong bar does not merely mislead, it can top the chart).

### 5.7 `FORMULAS.md` updates

`FORMULAS.md` is the stated mathematical reference and a trust surface (redesign-spec §6). Required edits, all matching the above verbatim: §2 (initial values — the buyer-closing intercept and clamp), §3 (ownership costs — `cost_index`, both additive levy and maintenance terms), §3 rent subsection (the occupier-levy term, with the invariance proof), §5 (`G(t)` gains the `− d_m` term), and a new §6 subsection stating that the levy deduction base includes both levy components and that a cap of 0 means "not deductible" while `None` means uncapped.

---

## 6. Wire, API, and frontend

### 6.1 `api.js` — the `levyDeductionCap` sentinel (blocking for NL)

Today (`api.js:4-9`) client `0` becomes wire `null`, and `null` means **uncapped** (`models.py:59-61, 249-253`). NL needs to say "the levy is not deductible at all", i.e. a cap of exactly **0**. That value is currently unreachable.

**Fix — move the sentinel off zero:**

```js
// api.js:7 — negative means "uncapped"; 0 now genuinely means "not deductible"
levyDeductionCap: cfg.levyDeductionCap >= 0 ? cfg.levyDeductionCap : null,
```

```js
// fields.js:26
{ key: "levyDeductionCap", label: "Levy deduction cap", min: -1000, max: 50000, step: 1000,
  fmt: (v) => (v < 0 ? "uncapped" : fmtMoney(v)), section: "advanced",
  hint: "Leftmost = uncapped · 0 = levy not deductible · US SALT cap is $10k" },
```

`state.js:78-82` derives `NUMERIC_RANGES` from these bounds, so the share-URL validator picks the new range up automatically. `DEFAULT_CONFIG.levyDeductionCap` stays `10000`; the US bundle is unchanged.

**Cost of not fixing it:** NL silently deducts its own levy — ~€518/yr, ~€5,200 over a 10-year horizon, credited to the wrong arm (§4.3).

**The migration hazard this creates, which the previous revision missed.** Today `levyDeductionCap: 0` means *uncapped*, `fields.js:26` renders it as "uncapped", and `state.js:59-66` writes non-default values into share URLs — so URLs carrying `levyDeductionCap=0` **already exist in the wild**. After the sentinel move, `0` is inside the new range, passes validation, and means the **opposite extreme**: levy not deductible. A US user's shared "uncapped SALT" scenario silently reopens with SALT at zero, changing the verdict with no visible cause. This is precisely the failure class §2 P2's rejected alternative and §4.0 rule 1 exist to police, so it cannot be waved through here.

**Fix — migrate on read (`state.js:91-112`, one guarded line):**

```js
// Legacy share URLs used 0 to mean "uncapped"; that sentinel moved to
// negative in <this release>. Values written before the change must keep
// their original meaning.
if (key === "levyDeductionCap" && Number(raw) === 0 && !params.has("v")) {
  restored[key] = -1;   // uncapped, new encoding
  continue;
}
```

**Rejected: versioning the whole param set** (`?v=2`). Heavier, and it would have to be threaded through `writeUrl` and every future codec change for one field's one-time migration. **Rejected: leaving it undocumented** — a silent verdict flip on existing links is the single worst outcome in this section. Test in §7.5.

### 6.2 `api.py` — close the non-scalar fall-through

`_validate_value` (`api.py:35-99`) has no branch for non-scalar annotations and falls through to `return value` **unvalidated** at `api.py:99`. Every primitive in this spec is a scalar precisely so this hole is never exercised — and that is exactly why the code should now enforce the invariant the design depends on:

```python
# api.py:99 — replace the silent fall-through.
# Every SimulationConfig field is scalar by design (see docs/multi-region-spec.md
# §3). A non-scalar field would arrive here unvalidated; fail loudly instead.
raise TypeError(f"{name}: unsupported field annotation {annotation!r}")
```

Safe today: every field is `int`, `float`, `bool`, `float | None`, or a `Literal`, all handled at `api.py:71-97`. `server.py:104` and `server.py:114-115` already catch `TypeError` and return 422. Test in §7.5.

### 6.3 `models.py` — field declarations and validation

Six fields appended to `SimulationConfig` (after `cost_inflation_rate`, `models.py:119`), with NumPy-style docstring entries matching the existing block (`models.py:38-77`):

```python
annual_property_levy: float = 0.0
levy_paid_by_occupier: bool = False
annual_maintenance_amount: float = 0.0
closing_cost_buyer_amount: float = 0.0
portfolio_deemed_return_pct: float = 0.0
portfolio_drag_rate_pct: float = 0.0
```

`_CAMEL_TO_SNAKE` and `_TYPE_HINTS` (`api.py:28-32`) derive from `fields(SimulationConfig)`, so all six wire **automatically** — no `api.py` codec change beyond §6.2.

New `__post_init__` checks (`models.py:130-289`):

| Field | Bound | Note |
|---|---|---|
| `annual_property_levy` | `0 ≤ v ≤ 100_000` | |
| `annual_maintenance_amount` | `0 ≤ v ≤ 100_000` | |
| `closing_cost_buyer_amount` | `−100_000 ≤ v ≤ 100_000` | **Must permit negatives** — the UK SDLT nil-rate intercept is −6,900. A `>= 0` check would make the UK bundle unconstructible. |
| `portfolio_deemed_return_pct` | `0 ≤ v ≤ 100` | With the rate cap below, keeps `d_m ≤ 1.0 × 1.0/12 = 0.0833` and `1 + g − d_m` above −1 (§5.4). |
| `portfolio_drag_rate_pct` | `0 ≤ v ≤ 100` | |
| `levy_paid_by_occupier` | type only | Enforced at `api.py:77-80`. |

**Recommended in the same phase, as a separate commit:** five sibling fields have **no validation at all** today — `closing_cost_buyer_pct`, `closing_cost_seller_pct`, `property_tax_rate`, `annual_home_insurance`, `annual_maintenance_pct`. A negative property tax rate currently passes and produces a subsidy. This change does not worsen that, so it is not strictly in scope; but leaving four validated new fields sitting beside five unvalidated siblings is a worse invariant than either extreme, and the checks are five range assertions in the function being edited anyway. Keep it as a discrete commit so the no-regression gate stays legible.

### 6.4 `fields.js` / `state.js` — six new Advanced inputs

All six use the existing slider and checkbox builders (`inputs.js:22-48, 74-88`). **No new widget shape.**

```js
{ key: "closingCostBuyerAmount", label: "Buyer fixed costs", min: -20000, max: 20000, step: 100,
  fmt: fmtMoney, section: "advanced",
  hint: "Flat costs on top of the percentage. Negative where a transfer tax has a zero-rate band (UK SDLT)." },
{ key: "annualPropertyLevy", label: "Property levy /yr (flat)", min: 0, max: 10000, step: 50,
  fmt: fmtMoney, section: "advanced",
  hint: "Flat annual levy that does not scale with the home's value (UK council tax, DE Grundsteuer)." },
{ key: "levyPaidByOccupier", label: "Levy paid by occupier", type: "checkbox", section: "advanced",
  hint: "Charge the levy to the renter as well as the buyer (UK council tax, DE umlagefähige Grundsteuer)." },
{ key: "annualMaintenanceAmount", label: "Maintenance /yr (flat)", min: 0, max: 10000, step: 50,
  fmt: fmtMoney, section: "advanced" },
{ key: "portfolioDeemedReturnPct", label: "Deemed return (wealth tax)", min: 0, max: 15, step: 0.05,
  fmt: (v) => fmtPct(v, 2), section: "advanced",
  hint: "Assumed return the wealth tax is charged on. Taxed on the LESSER of this and your actual return (NL box 3)." },
{ key: "portfolioDragRatePct", label: "Wealth-tax rate", min: 0, max: 60, step: 0.5,
  fmt: (v) => fmtPct(v, 1), section: "advanced",
  hint: "Rate applied to that deemed return, annually, on portfolio value — not on realised gains." },
```

**Two existing labels must change to avoid collisions the new fields create.** `fields.js:20` currently reads "Property levy" and would sit next to the new "Property levy /yr (flat)" — two Advanced sliders reading as the same quantity in different units. Rename `fields.js:20` to **"Property levy (% of value)"**. Likewise apply the §4.0 rule-4 grid fixes here: `marginalTaxRatePct` step `1 → 0.01`, `propertyTaxRate` step `0.05 → 0.0005`, and `closingCostBuyerPct` **`max: 10 → 15`** (the DE blocker).

`state.js` `DEFAULT_CONFIG` (`state.js:5-29`) gains the same six keys at the same defaults. `state.js:99-107` dispatches on the default's `typeof`, so `levyPaidByOccupier: false` takes the boolean path and the five numbers take the numeric path — including the negative range, which `NUMERIC_RANGES` picks up from `fields.js` automatically (`state.js:78-82`).

### 6.5 The FTB toggle and the visible-input budget

Redesign-spec §2 caps visible inputs at 8: *Region · Home price · Down payment % · Mortgage rate · Mortgage term · Monthly rent · Horizon · Market-outlook preset*. FTB would be a 9th.

**It does not displace anything, because the shipped layout is not what §2 describes.** Region and outlook are pills in the header bar (`index.html:173-182`), not sliders; `core-inputs` holds six controls (`fields.js:9-14`). **Place the FTB toggle as a pill in the region row**, immediately after the region pills:

```
Region [US] [FR] [DE] [NL] [UK]   [✓ First-time buyer]   Outlook [Conservative] ...
```

Rationale: FTB is semantically a *modifier of the region*, and putting it there costs no slider slot and no new builder — it reuses the `preset-btn` styling that `buildPresetPills` (`inputs.js:127-146`) already emits.

**The "~15 lines" of the previous revision hid three real defects. Specified properly:**

**(a) Toggling FTB must apply a delta, not re-apply the bundle.** `applyPreset({...typical, ...taxPrimitives, ...overrides})` on every toggle resets `propertyPrice`, `monthlyRent`, `mortgageRateAnnual`, `mortgageTermYears` and every tax field. A UK user drags price to £450,000, toggles FTB to compare, and the price snaps back to £289,106 — destroying the comparison the toggle exists to enable. **Only the override keys may move**, and turning FTB off must restore those same keys from the base bundle, not from defaults:

```js
function applyFtb(region, on) {
  const keys = Object.keys(region.firstTimeBuyerOverrides);
  if (keys.length === 0) return;                       // DE, US: inert by data
  applyPreset(Object.fromEntries(keys.map((k) =>
    [k, on ? region.firstTimeBuyerOverrides[k] : region.taxPrimitives[k]])));
}
```

**(b) The active region pill must be derived on URL restore, not assumed.** `inputs.js:146` marks the **first available pill (US)** active on load regardless of the restored config. So a recipient of a UK share URL sees a UK config under a US-highlighted pill, and the first FTB click calls `applyFtb(US, ...)` — silently rewriting the page to US values. **Fix:** after `readUrl()`, select the pill whose `taxPrimitives` match the restored config (falling back to no pill active if none matches, rather than defaulting to US). A restored config that matches no bundle is a legitimate state — a hand-edited URL — and must render as "no region selected", not as a wrong one.

**(c) The pill's displayed state must be derived, not assumed TRUE.** FTB is unpersisted (it changes only real config fields), so a restored non-FTB UK config would render with the pill visually ON — misrepresenting the very config being displayed. **Fix:** derive the pill's checked state by comparing the restored values of the override keys against `firstTimeBuyerOverrides`; show it ON only on an exact match. Where `firstTimeBuyerOverrides` is `{}` (DE, US) the pill renders disabled with a tooltip — inert by data, and *visibly* inert rather than silently so.

**Rejected: the Advanced drawer.** FTB defaults **TRUE**, so hiding it there means a UK user's buyer cost is silently £4,455 lower than the headline SDLT they will read anywhere else, with no visible cause. A default-on relief must be visible.

**Rejected: making it a `SimulationConfig` field to reuse the generic checkbox builder.** That builder reads `getConfig()[def.key]` and calls `setParam` (`inputs.js:81-84`), so it requires a config field — and §2.6 rejects that field. Bespoke code either way; the pill is the smaller and better-placed version.

### 6.6 `regions.py` shape change

Two new keys per bundle: `firstTimeBuyerOverrides: dict` and `notes: list[str]`. `/api/regions` (`server.py:93-96`) returns the bundles verbatim with no validation, and neither key is a `SimulationConfig` field, so nothing else changes server-side. The `notes` render into the methodology footer (redesign-spec §3.6).

### 6.7 Currency display — scheduled into Phase 2, not caveated away

**`currencySymbol` is declared in all five bundles and consumed by nothing.** Verified: three occurrences in the tree, all inside `regions.py` itself. Ship the bundles as previously specified and every European preset renders in dollars — the UK's SDLT-exact £7,555.30 displays as **"$7,555"**, in a verdict hero whose entire job is to state one number credibly. ADR-0007's Consequences explicitly promise *"Currency is formatting only ($, €, £)"*; that promise is currently unimplemented, and shipping four European regions is the moment it becomes false rather than merely pending.

**This is scheduled into Phase 2, not deferred to §8.** A ship-with-caveat was considered and rejected: a caveat cannot repair a headline number, and "the currency is wrong" is not a modelling simplification with a bias direction — it is a defect. The work is bounded:

- **`format.js`** — `fmtMoney`, `fmtCompact` and the `en-US` locale are hardcoded at `format.js:5, 11, 12` (three `$` literals; line 17 is the percent formatter). Parameterise on a module-level current-region symbol and locale, set once when a region is applied.
- **`charts.js`** — `$` is baked into Plotly `tickformat` and `hovertemplate` strings at `charts.js:20, 30, 31, 146, 162, 163, 203`, across four chart builders. **This is the non-trivial half**: d3 format specifiers do not take an arbitrary currency token, so `$,.0f` cannot simply become `£,.0f`. Use `tickprefix` with a plain numeric `tickformat`, and rebuild the hovertemplates to interpolate the symbol.
- **`charts.js:65-72` — `fmtTick`, the compact symlog tick formatter**, which postdates the original file survey (added by `f585e98`, the adaptive-symlog commit). It hardcodes `$` at lines **70, 71 and 72**, and **a grep for `\$`, `$,` or `$%` will not isolate them** because they are template-literal interpolations of the form `` `${sign}$${...}` ``. Without this, a UK symlog axis keeps ticking in dollars and no test catches it — the sole reason this line is called out separately.
- **`results.js`** — `results.js:18, 32-33` push the symbol into the verdict hero and stat row.

**Scope boundary, unchanged:** formatting only. No FX, no conversion, no locale-specific digit grouping beyond what `Intl` gives for free. The engine stays currency-agnostic (ADR-0007).

---

## 7. Test strategy

`pytest`, 80% coverage floor enforced (`pyproject.toml`, `fail_under = 80`). Existing helpers `taxfree_config` / `run_flat` (`tests/test_engine_core.py:15-49`) are the right base for primitive fixtures.

### 7.1 Why source-cited fixtures, not narrative trust

During research, a WebFetch summarizer **fabricated a plausible but entirely fictitious Wet IB 2001 article**. Statute text was only trustworthy when pulled as raw HTML. **Every statute quote in the research chain is unverified unless re-checked against raw source.** The practical consequence for this repo: a shipped value's justification must live in a test with a citation next to it, where a wrong number fails a build — not in prose, where it decays silently. This is the strongest argument in the whole document for the fixture tests below.

### 7.2 Phase 1 — no-regression gate (write first, before any engine edit)

1. **Capture goldens on the pre-change commit.** Run `calculate_scenarios` on the US bundle at `DEFAULT_CONFIG`, record `final_net_buy`, `final_net_rent`, `final_difference`, `breakeven_year`, `monthly_mortgage_payment`, both year-1 monthly costs, and all seven `totals`. Hard-code them into `tests/test_regions.py::test_us_preset_unchanged` with a comment naming the commit they came from. Assert to 1e-6.
2. **Defaults-are-inert.** The full existing suite (`test_engine_core.py`, `test_engine_taxes.py`, `test_calculate_scenarios.py`) must pass **unmodified**. Any edit to an existing assertion is a regression, not a test update — this is the gate's whole point.
3. **Tornado bit-identical for the US.** Assert `_compute_sensitivity(us_config)` returns the same 8 parameter names in the same order with values matching the goldens to the 1e-6 standard of item 1. **Additionally assert exact float equality on the perturbation bounds** — `1.2 - delta == 0.7` and `1.2 + delta == 1.7` — because §5.6's proportional delta evaluates to exactly `0.5` at the US base of 1.2. This is a deliberate, standalone bit-identity assertion: if drift ever appears here, someone should have to decide to accept it rather than inherit a silent allowance.
4. **Monte Carlo needs no `monte_carlo.py` change** — `_simulate_single_path` passes `config=base_config` through unchanged (`monte_carlo.py:384`), and P1-P4 are static. Assert: `run_monte_carlo` on a config with the new fields at non-default values must produce paths whose terminal values match `calculate_scenarios` when all stds are zeroed.
5. **P5 is path-dependent and must be tested as such.** With `portfolio_deemed_return_pct=6.0`, `portfolio_drag_rate_pct=36.0` and MC stds at their defaults, assert that the mean realised drag across paths is **below** the deterministic 2.16% — the Jensen effect of `min()`, and the entire reason P5 is two fields. A run in which every path drags exactly 2.16% means the `min` is not being evaluated per path, which is the failure mode this primitive exists to prevent.
6. **Both P5 defaults are inert.** With both fields at `0.0`, `min(0, R) <= 0` is clipped to `0` for every `R` including negative draws, so `eq_growth` must be elementwise identical to a pre-change run. Assert on a config with a negative `equity_growth_annual` too, so the lid-2 floor is exercised rather than assumed.

### 7.3 Hand-computed fixtures, one per primitive

- **P1 unit.** `annual_property_levy=1200`, `cost_inflation_rate=0` → `levy[1] == 100.0` exactly. With `cost_inflation_rate=0.12` → `levy[13] == 100 × 1.01**12`.
- **P1 additivity.** A run with `(rate=1.2, amount=1200)` equals the elementwise sum of `(1.2, 0)` and `(0, 1200)` runs — proving the two paths are independent and the US path is untouched.
- **P2 equivalence.** **Compare `(annual_property_levy=2392, levy_paid_by_occupier=True)` against `(annual_property_levy=0)`** — *not* flag-off against flag-on, which differ by the compounded levy (£7,159 on a 5-year UK fixture) and would fail any tolerance. The fixture must set `interest_deduction_enabled=False` so the levy is non-deductible; otherwise `cum_tax_savings` diverges between the two configs and the equivalence does not hold (§2 P2).
  - `final_difference` equal at **`math.isclose(..., rel_tol=1e-12)`** — *relative*, because `cash_committed` changes magnitude and both nets are re-rounded before the subtraction. An absolute 1e-9 on values reaching ~1e7 is tighter than one ulp (~2e-9).
  - the elementwise `net_buy − net_rent` series equal at `rtol=1e-12` **with a small `atol`** (~1e-6): the difference series crosses zero around the breakeven, and a pure relative tolerance is meaningless at those months.
  - `net_buy` and `net_rent` each **lower** in the `L` config by `Σlevy` — asserting that the levels genuinely move while the difference does not, which is the whole point of the flag.
  - `monthly_cost_rent_year1` higher in the `L` config by exactly `mean(levy[1:13])` — the headline stat row this primitive exists to correct.
- **P3.** Mirror of P1.
- **P4 exactness.** `closing_cost_buyer_pct=5.0`, `closing_cost_buyer_amount=-6900`, `property_price=289106` → `total_closing_costs_buyer == 7555.30`. The SDLT band arithmetic goes in the test as a comment with the gov.uk citation.
- **P4 clamp.** Same pair at `property_price=100_000` → `0.0`, not negative; and `net_buy[0] == -(0 + seller_cost)`.
- **P5 closed form — non-circular.** Set `down_payment_pct=100` so `payment == 0` and levy/insurance/maintenance are zero. Then `housing_cost_buy == 0 < rent`, so `contrib_rent == 0` and `rent_portfolio(t) == initial_outlay × G(t)` — pure `V0` compounding with no contributions. With `deemed=6.0`, `rate=36.0`, `equity_growth_annual=7.0`, horizon 30 (so `min` binds at 6% every year and `d = 2.16%/yr`), assert:
  - `rent_portfolio[360] / initial_outlay == (1 + 0.07/12 − 0.0216/12)**360` to `rel_tol=1e-12`;
  - the ratio against a zero-drag run equals **0.5247574800635896 ± 1e-9**, i.e. a **47.52%** shortfall, matching §5.4.
  **The previous revision asserted `0.5434 ± 0.0005` and would have failed by ~0.018 — 37× its own tolerance.** It used the annual closed form (and mis-evaluated it) where the engine applies the drag monthly. The monthly value governs because `engine.py:402` feeds arithmetic `annual/100/12`.
- **P5 `min` selection.** With `equity_growth_annual=4.0` (below the 6% deemed), assert the realised drag is `0.04 × 0.36 = 1.44%/yr`, not 2.16% — the `min` binding on the actual-return side. With `equity_growth_annual=-10.0`, assert the drag is exactly **zero** (art. 5.25 lid 2 floor), not negative — a negative drag would silently *credit* the portfolio.

### 7.4 Region bundle tests (`tests/test_regions.py`, new)

- **Key-set equality.** Every bundle's `taxPrimitives` has an identical key set; same for `typical`. Prevents the `Object.assign` leak documented in §4.0 rule 1. **This is the highest-value structural test in the change.**
- **Every bundle is constructible.** For each available region, `config_from_dict({**DEFAULT-ish, **typical, **taxPrimitives})` returns a valid `SimulationConfig` — and again with `firstTimeBuyerOverrides` applied.
- **Regions never set the outlook trio.** Assert none of `propertyAppreciationAnnual`, `equityGrowthAnnual`, `rentInflationRate` appears in any `typical` or `taxPrimitives` (§4.0 rule 2).
- **Source-cited value fixtures, one class per region**, each asserting a *derived* quantity so a typo in an input fails:
  - FR: non-primo buyer cost at €290,000 == €22,957 (7.916%); primo == €21,478 (7.406%).
  - DE: buyer cost at €339,000 == €40,917.30 (12.07%); `propertyPrice / (monthlyRent * 12) == 28.48` to 2dp, the matched-pair P/R check of §4.2; `saleCgRegime == "fully_exempt"` with a comment citing §23 Abs.1 Nr.1 Satz 3.
  - NL: `propertyTaxRate == 0.15 + 0.35 × 0.3756` to 1e-9 — the EWF identity of §5.5 asserted as arithmetic, not prose; `levyDeductionCap == 0.0`; `portfolioDeemedReturnPct == 6.0` and `portfolioDragRatePct == 36.0` shipped as **separate** operands (a test asserting a pre-multiplied 2.16 would lock in the defect of §2 P5); `annualMaintenancePct == 1.0` **and** `annualMaintenanceAmount == 0.0`, with the Nibud/VEH citation and a comment stating that the percentage unit is deliberate (§2 P3) so the assertion is not "corrected" into €4,900 by a later reader.
  - UK: non-FTB == £7,555.30 and FTB == £3,100.00 at £289,106; `annualPropertyLevy == 2392.0`; `levyPaidByOccupier is True`. Plus three **divergence** fixtures that pin the known errors so they cannot silently drift: at £2,000,000 model == £93,100 against true £156,850; at £400,000 FTB model == £3,100 against true £8,100; at £138,000 model == £0 against true £3,360. These assert the *model's* value and record the true one in a comment — they document the gap, they do not bless it.
- **Bundle values lie inside their `INPUT_DEFS` ranges** (§4.0 rule 4). Parse `fields.js` bounds (or mirror them in a test constant with a comment pointing at the file) and range-check every value in every bundle. This is the test that would have caught DE's `closingCostBuyerPct: 12.07` against `max: 10`.
- **All five regions are available.** Assert `all(r["available"] for r in list_regions())`. Phase 2 delivers four new regions, not three — this test is what stops a bundle being quietly shipped disabled.
- **Maintenance path is exclusive.** For every bundle, assert exactly one of `annualMaintenancePct` / `annualMaintenanceAmount` is non-zero, and that the region takes the path its evidence unit dictates (§2 P3 table: UK/DE/FR amount, NL/US pct). Guards against a future contributor "tidying" NL onto the absolute path and silently freezing a value-proportional convention at one price.

### 7.5 Wire tests (`tests/test_api.py`, extend)

- `config_from_dict({..., "levyDeductionCap": 0.0})` → `0.0`, **not** `None`; `{..., "levyDeductionCap": None}` → `None`. Guards the §6.1 semantic directly on the Python side, since there is no JS test harness in this repo — noted as a gap in §8.
- **Legacy share-URL migration (§6.1).** The `readUrl` migration is JS and therefore untestable here; record it as a manual pre-merge check with the exact steps: open a pre-change share URL containing `levyDeductionCap=0`, confirm the restored config reports *uncapped* and the Verdict matches the pre-change value. Untested migrations of a sentinel that inverts meaning are how silent verdict flips ship.
- `closingCostBuyerAmount: -6900` round-trips through `config_from_dict` / `config_to_dict`.
- `levyPaidByOccupier: "yes"` → `ValueError` (`api.py:77-80`).
- Every new field appears in `config_to_dict` output with the expected camelCase key.
- **Fall-through guard:** assert `_validate_value("x", [1,2], list[int])` raises `TypeError` (§6.2).

### 7.6 Coverage

New engine code is ~20 lines, all on paths the fixtures above exercise; new `models.py` validation is ~30 lines with one test per branch; `regions.py` is data, covered by construction in §7.4. The 80% floor is not at risk.

---

## 8. Known gaps, simplifications, and bias directions

"Bias" = which side of the Buy-vs-Rent verdict the error favours.

### 8.1 Deliberate modelling simplifications

| # | Simplification | Region | Magnitude | Bias |
|---|---|---|---|---|
| S1 | Portfolios are plain taxable; no ISA / PEA / Sparer-Pauschbetrag / heffingsvrij vermogen (locked decision 4) | **All, incl. US** | UK ISA alone removes a 24% CGT on the renter's gains | **Toward buying, in every region** |
| S2 | Heffingsvrij vermogen (€59,357 pp) not modelled inside P5 — **and not modellable in closed form**, since under tegenbewijs the allowance is unavailable (Hoge Raad), making the `min` wealth-dependent | NL | **Restated after the P5 split.** Verified effective drags *with* the allowance: €250k → 0.99%, €500k → 1.12%, €1M → 1.19%, against this model's ~1.31%. Residual **0.12–0.32pp**, an order of magnitude below the 6–8% previously stated — the tegenbewijs fix absorbed most of what the allowance was compensating for | Toward buying |
| S3 | Flat levy indexed at `cost_inflation_rate`, not each country's statutory uprate | FR, DE, UK | FR: recovers ~30% of the gap; residual ~€8k over 25yr | Toward renting (FR over-indexed) |
| S4 | Rents modelled as exclusive of council tax — **unverifiable**, ONS never states it; PIPR uses *achieved* rents | UK | £199/mo = 13.9% of rent | Neutral on verdict (P2 invariance); shifts displayed levels |
| S5 | FTB relief withdrawal above £500,000 not modelled | UK | At £501,000 true total £18,150 vs model £3,100: **£15,050 understated** (previously stated as £11,950, which wrongly netted the £3,100 of fees against the SDLT) | Toward buying, above £500k only |
| S6 | Non-FTB buyer cost under-charged across the whole **£125k–£250k** band, clamped to zero below £138,000 | UK | Worst point **£138,000: model £0 vs true £3,360**. Both the range and the bound were understated previously ("below £138,000", "≤£3,100") | Toward buying, below the target range |
| S7 | FR degressive notaire emoluments modelled as flat | FR | ≤0.2pp of a 7.9% cost | Negligible |
| S8 | DE Vorabpauschale not modelled (creditable at exit) | DE | ~0.41%/yr timing only | Slightly toward renting |
| S9 | ~~NL 30-year deduction cap and annuity requirement not modelled~~ **— withdrawn, the scenario is unreachable** | NL | The term picker caps at 30 (`fields.js:12`) and the balance freezes at payoff so `interest == 0` thereafter (`engine.py:171-178`): there is no interest past year 30 to over-deduct, so the 30-year limit is satisfied automatically. The post-2013 annuity requirement is likewise inert — the engine's mortgage **is** an annuity (`npf.pmt`, `engine.py:170`) | None |
| S10 | Monthly-ised box 3 vs the 1 January peildatum | NL | **~3.36%** of terminal portfolio over 30yr (0.542372 annual vs 0.524757 monthly; ~3.5% on a fully engine-consistent basis). The previously stated **0.66% omitted the growth cross-term and understated this ~5×** | Toward buying |
| S11 | Mortgage rate held fixed for the full amortisation term; no Zinsbindung/SVR reversion (D9) | DE, UK, NL | UK SVR is 195bp above the 5yr fix | Toward buying |
| S12 | Rent regulation (encadrement, Mietpreisbremse) not modelled; rent grows at the outlook rate | FR, DE | Unquantified | Toward buying |
| S13 | DE Bundesland GrESt spread not selectable | DE | 3pp ≈ **€10,170 on the shipped €339,000** (previously quantified on the superseded €400,000 price, which §8.4 forbids reintroducing) | Either, depending on state |
| S14 | UK additional-dwelling (+5pp) and non-resident (+2pp) surcharges not modelled | UK | Out of scope: single owner-occupied residence | n/a |
| S15 | DE heating/water Nebenkosten omitted from both arms | DE | Decision-neutral by construction | Neutral |

| S16 | **Maintenance stays value-proportional in NL and the US** — the unit D7's own evidence argues against. **FR is contingent**: its two source figures are in different units (€25/m²/yr area-proportional → €1,625, vs "~1.0%" value-proportional → €2,900) and do not reconcile; the shipped €1,300 takes the area basis, so if the value basis is the true one, FR inherits this row too | NL, US, **FR (contingent)** | D7's ONS finding — England maintenance spend varies ~1.9× regionally against a 3–4× house-price spread — implies the elasticity is well below 1. If it is, a value-proportional figure over-charges maintenance as price rises and under-charges as it falls | **Toward renting**, and it *grows* with the price slider and with the appreciation rate. **Two of five shipped regions carry this unit regardless of which storage field the engine uses — changing the engine's unit does not change where the evidence came from** |
| S17 | **The four maintenance figures are not a like-for-like series** | all | NL/US 1.0% are recommended budgeting *reserves* incl. amortised capital replacement; UK £900 is *observed* recall-based spend; DE €1,700 and FR €1,300 are *owner-only recurring charges* net of tenant-recoverable shares | Toward renting in NL/US relative to UK; toward buying in UK relative to NL/US. **Not a common scale — cross-region maintenance differences should not be read as real** |
| S18 | **SDLT under-charged above £925,000**, where the marginal rate steps to 10% then 12% but the model's line stays at 5% | UK | £1,000,000: model £43,100 vs true £46,850 (**£3,750**). Slider ceiling £2,000,000: model £93,100 vs true £156,850 (**£63,750, 41%**) | Toward buying, and growing without bound above £925k |
| S19 | **FTB SDLT under-charged between £300,000 and £500,000**, where relief is 5% rather than 0% | UK | **£5,000 at £400k, £7,500 at £450k, £10,000 at £500k**. The shipped override `(0, 3,100)` was chosen for exactness at the £289,106 preset price over exactness on this band — trade-off stated in §2 P4(3) | Toward buying, **with FTB defaulting TRUE** |
| S20 | **Outlook presets are US-calibrated and inherited unchanged by all four new regions** | FR, DE, NL, UK | §4.0 rule 2 forbids regions setting the outlook trio, so all four inherit `inputs.js:8-12` — 3% property, 7% equity, 3% rent, all US historical priors. **Property appreciation is the top bar of the app's own tornado chart**, so this is first-order for some regions: German real house prices were roughly flat for decades pre-2010, while UK long-run nominal growth ran well above 3% | Unquantified and **region-dependent** — toward buying where 3% understates local appreciation (UK), toward renting where it overstates it (DE) |

**On S20 specifically — recorded, not fixed.** Keeping one outlook vocabulary across regions is a defensible product decision: the presets are user-adjustable, three sliders wide, and per-region outlook priors would multiply the preset surface by five while inviting exactly the fictional-average problem ADR-0007 rejects. **No behaviour change is proposed.** But the previous revision spent precision on ±0.2pp of notaire emoluments (S7) while leaving a first-order, region-dependent assumption unexamined, and this spec's own standard is that such things get an S-row rather than being engineered away silently. If a follow-up ever revisits it, the honest framing is per-region *historical* priors as a fourth outlook pill — not a rewrite of the existing three.

### 8.2 Forward risk — the NL box-3 regime is explicitly temporary

The 6%/36% figures are correct and enacted for **2026 only**, and two scheduled events will break them inside the horizon of a typical simulation:

1. **The 2027 forfait is a live fiscal target.** Amendment nr. 47 (which struck the 7.78% / €51,396 introduction figures) left a **€1,267m/yr** gap that Kamerstukken 36 812 nr. 113 states *"wordt verwerkt in de Voorjaarsnota"* — i.e. the deemed return is an identified funding lever for next year.
2. **The whole forfait-plus-tegenbewijs system is slated for replacement** by the *Wet werkelijk rendement box 3* from **1 January 2028**, moving to actual-return taxation.

**Consequence for this tool:** a 10-, 25- or 30-year simulation should not be read as assuming either 2.16%/yr or the ~1.31% expected drag persists. The NL bundle's `notes` must say so — this is the one shipped value with a known expiry date on the record, and it is a headline driver of the NL verdict.

### 8.3 Open research items (none blocking)

**No shipped value is unsourced.** The weakest figures — DE `annualPropertyLevy` (L), FR `annualMaintenanceAmount` (L), NL `monthlyRent` (L) — are documented at their confidence level in §4 and carry the bias directions recorded above and in §8.4. Two items would materially improve the model; neither gates ship:

1. **FR maintenance basis.** The research supplies two figures that do not reconcile: €25/m²/yr × 65 m² + fonds travaux ≈ **€1,625**, versus "~1.0%" of €290,000 = **€2,900**. The shipped €1,300 is the owner-only (non-récupérable + fonds travaux) estimate. Closing the charges-récupérables split resolves both the discrepancy and the confidence rating.
2. **A maintenance elasticity check on a common basis.** S16 and S17 both exist because there is no cross-country maintenance dataset measured the same way. One would let the spec replace two national conventions and one recall survey with a single defensible unit — which is what D7 was reaching for and did not have the evidence to finish.

### 8.4 Provenance caveats recorded for the record

- **Fabrication incident.** A WebFetch summarizer produced a plausible but entirely fictitious Wet IB 2001 article. Statute text was trustworthy only as raw HTML. **Treat every statute quote in the research chain as unverified until re-checked against raw source.** This is why §7.4 puts citations inside tests.
- **Germany's 16-state GrESt table is mostly secondary-sourced.** Only Bremen is primary. Thüringen is secondary (cut to 5.0% on 01.01.2024 — many 2026 blog tables are stale at 6.5%). NRW 6.5% is verified via Landtag Drucksache 16/7147 (bill text, effective 01.01.2015; consolidated text not re-verified). Bayern 3.5% is the unmodified federal default (GrEStG §11 Abs.1). This provenance is the reason the Bundesland selector is rejected (§3).
- **Corrected values — do not reintroduce the superseded figures:** FR rent €812 (was €1,100, above the encadrement ceiling in every Lyon zone); FR buyer cost 7.90–8.00% (was 6.4–6.5%, arithmetically inconsistent); FR primo relief 0.51pp (was 1.5pp); DE price €339,000 (was €400,000, then €345,000 — the latter did not reproduce from its own €4,239/m²; see §4.2); DE Hebesatz 550% (was 475% TY2025 / 515% 2012–2024); DE regime `fully_exempt` (was `exempt_after_years: 10`); UK maintenance £900 (was 1.0% of value, 3–4.5× the evidence); NL Hillen step 4.80pp for 2026 completing 2041 (was "4.85pp/yr" completing 2048); FR portfolio CG 31.4% (was 30%).
- **Residual unsourced items:** England semi-detached rent-vs-sales population mismatch (PIPR measures rented stock including sitting tenants; UKHPI measures transactions — **biases P/R up, i.e. toward renting**); NL rent derivation (**overstates rent for a large home → true P/R higher → toward buying**); primary-source mortgage rates for all three of BoE/DNB/Banque de France (blocked or JS-only; corroborated only via aggregators); Rhône's actual DMTO rate; Lyon arrêté préfectoral ceiling values; UK maintenance is a **lower** bound (recall-based survey under-captures lumpy repairs → **toward buying**).
- **No JS test harness exists in this repo.** The `api.js` and `state.js` changes (§6.1, §6.4) are unit-untested; §7.5 covers the Python side of the same semantics. Recorded as a gap, not solved here.

---

## 9. ADR amendments

### 9.1 ADR-0007 — amend in place

ADR-0007 line 3 contains **two factual errors** that this work must correct:

1. *"Germany: sale tax-free after a 10-year hold"* — **wrong for the owner-occupied case this tool models.** §23 Abs.1 Nr.1 Satz 3 EStG exempts the owner-occupier limb at **any** holding period. The 10-year speculation period applies to non-owner-occupied property, which this tool does not model. The error is not cosmetic: it is the reason the research initially proposed `saleCgRegime: "exempt_after_years", saleCgExemptAfterYears: 10` for Germany, which would have taxed the entire German home gain for any horizon under 10 years.
2. *"France: 30% PFU"* — now **31.4%** (12.8% + 18.6% PS; the PS rise came via LFSS 2026, LOI 2025-1403 art. 12, CSG 9.2 → 10.6).

Line 3 also states "five neutral primitives"; this change makes it seven categories (buyer transaction costs **incl. a fixed component**, seller transaction costs, annual property levy **incl. a flat component, an incidence flag, and a maintenance amount**, interest deductibility + rate, CG treatment at exit incl. portfolio gains rate, **annual portfolio drag**).

**Recommendation: amend ADR-0007 in place** with a dated `## Amendment (2026-07, Phase 1)` section that corrects both facts and restates the primitive list.

**Rejected: a superseding ADR.** Superseding signals that the *decision* changed. It did not — "five primitives cover all five markets; countries are data, not code" is exactly what this spec implements, and no country branch enters `_net_value_series`. The errors are in the context paragraph's factual claims, not in the decision. Amending context in place is normally discouraged for decision records, but leaving a known-false statute claim standing in the document that governs region work is worse: the next contributor would read it and re-derive the German bug.

### 9.2 ADR-0009 (new) — portfolio tax wrappers are out of scope

Locked decision 4 is a **genuine architectural commitment ADR-0007 never made**, and it needs a durable record because it is the single largest systematic bias in the shipped model (§8.1, S1) and because it will be re-litigated the first time a UK user notices ISA is missing.

Proposed content: all regions model plain taxable brokerage accounts. Rejected: per-region sheltered defaults (ISA 0%, PEA 18.6%) — PEA is EU-equity-only, so it assumes a portfolio the user is not buying; ISA and Sparer-Pauschbetrag caps bind inside the horizon, so a flat sheltered rate is wrong from roughly year 3. Consequence: the tool understates after-tax portfolio returns for wrapper users **consistently across all regions including the US**, which biases every region's verdict toward buying; this is disclosed in each region's `notes` and in the methodology footer.

### 9.3 `CONTEXT.md`

The **Tax primitives** entry (`CONTEXT.md:42`) enumerates the primitive set as vocabulary. Extend it with the five new fields and the "annual portfolio drag" concept, using the same phrasing as §2.

---

## 10. Phasing and definition of done

**Phase 1 — engine primitives.** Six fields + validation (§6.3), the engine edits (§5.1–5.4), `total_closing_costs_buyer` sourced from `_buyer_closing` (§2 P4), the tornado repair (§5.6), the `api.py` fall-through guard (§6.2), the `api.js`/`fields.js` sentinel fix **plus its legacy-URL migration** (§6.1), the six Advanced inputs and the three `fields.js` bound/label/step fixes (§6.4, §4.0 rule 4), `FORMULAS.md` (§5.7). **Done when:** the whole pre-existing suite passes unmodified, `test_us_preset_unchanged` passes against goldens captured on the parent commit, the US tornado is bit-identical (§7.2 item 3), every primitive has its hand-computed fixture including the two P5 `min`-selection cases (§7.3), and no region bundle has changed.

**Phase 2 — all four bundles as data, plus currency.** `regions.py` bundles (§4), `firstTimeBuyerOverrides` + `notes` (§6.6), the FTB pill with delta application and derived pill state (§6.5), **the currency plumbing (§6.7)**, ADR amendments (§9), `tests/test_regions.py` (§7.4). **Done when:** **all four of FR, DE, NL, UK are `available: True`** with passing source-cited fixtures; the key-set equality, maintenance-path and `INPUT_DEFS`-range tests pass; every European preset renders in its own currency symbol; and every value rated **L**, every UK SDLT divergence (S5, S6, S18, S19) and the NL forward-risk note (§8.2) carry their caveat in the bundle's `notes`. Phase 2 delivers four regions — the locked scope — and nothing in §8 gates any of them.

The split is not cosmetic: Phase 1 is provably a no-op on shipped behaviour, so if a region's numbers turn out to be wrong, Phase 2 reverts cleanly without touching the engine.
