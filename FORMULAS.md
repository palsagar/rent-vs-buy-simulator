# Mathematical Formulas Reference

This document is the mathematical reference for the engine's single source of
truth, `_net_value_series()` in `src/simulator/engine.py`. Both the
deterministic engine (`calculate_scenarios`) and Monte Carlo
(`monte_carlo.py`) call this one function — every formula below is exactly
what it computes, not an approximation of it. Terms in **bold** are used as
defined in `CONTEXT.md`.

## 1. Time Vector

All calculations use monthly granularity, indexed from purchase/move-in (0)
to the **Horizon**:

```
t ∈ {0, 1, 2, ..., H}   where H = horizon_years × 12
```

The Horizon is the number of years the person expects to stay before
exiting — it is **not** the mortgage term (ADR-0004). The two are separate
inputs: a 10-year Horizon with a 30-year mortgage term is the common case,
and the mortgage may be paid off before or still outstanding at the Horizon.

## 2. Mortgage

### Initial values

```
down_payment   = property_price × (down_payment_pct / 100)
buyer_closing  = max(property_price × (closing_cost_buyer_pct / 100)
                     + closing_cost_buyer_amount, 0)
initial_outlay = down_payment + buyer_closing

L = property_price - down_payment         # loan amount
r = (mortgage_rate_annual / 100) / 12     # monthly rate
n_term = mortgage_term_years × 12         # amortization term, in months
```

`closing_cost_buyer_amount` may be **negative**: a transfer tax with a
zero-rate band has a negative intercept. UK SDLT is exactly linear over
£250k–£925k with `pct = 5.0` and `amount = −6,900`. The clamp is on the
**aggregate**, not on the amount term — the UK pair turns negative below a
price of 138,000 against a slider floor of 50,000, and without the clamp an
instantaneous buy-and-sell would report a profit.

### Monthly payment (PMT)

The payment amortizes the loan over `n_term`, independent of the Horizon:

```
if L ≈ 0:            PMT = 0
elif r ≈ 0:           PMT = L / n_term
else:                 PMT = -npf.pmt(r, n_term, L)
```

(`npf.pmt` is `numpy_financial.pmt`; the engine negates its sign convention.)

### Remaining balance B(t)

Closed form, capped at zero and evaluated at `min(t, n_term)` so the balance
freezes at payoff even if the Horizon extends past the mortgage term:

```
if L ≈ 0:     B(t) = 0
elif r ≈ 0:   B(t) = max(L - PMT × t, 0)
else:
    growth(t) = (1 + r)^min(t, n_term)
    B(t) = max(L × growth(t) - PMT × (growth(t) - 1) / r, 0)
```

### Payment and interest paid during month t

The payment made *during* month t (t = 1..n_term) is `PMT`; it is zero once
the loan is paid off or once t exceeds the Horizon-truncated series has no
more months to charge:

```
payment(t) = PMT   if 1 ≤ t ≤ n_term, else 0
interest(t) = B(t-1) × r    for t ≥ 1;  interest(0) = 0
```

Interest accrues on the *prior* month's balance — `B(t-1)`, not `B(t)`.

## 3. Housing Costs

### Home value

Compounds with the (possibly month-varying, e.g. stochastic) monthly
appreciation rate `prop_rate_monthly[m]`:

```
home_growth(0) = 1
home_growth(t) = ∏_{m=1}^{t} (1 + prop_rate_monthly[m])
home_value(t)  = property_price × home_growth(t)
```

### Ownership costs (buyer)

Levy, insurance, and maintenance are all costs *paid during* month t
(t ≥ 1; zero at t = 0). Levy and maintenance are priced off the **prior**
month's home value — the value base a bill for month t would actually be
computed against:

```
cost_index(t)  = (1 + cost_inflation_rate / 12)^(t-1)              t ≥ 1

levy(t)        = home_value(t-1) × (property_tax_rate / 100) / 12
                 + (annual_property_levy / 12) × cost_index(t)

insurance(t)   = (annual_home_insurance / 12) × cost_index(t)

maintenance(t) = home_value(t-1) × (annual_maintenance_pct / 100) / 12
                 + (annual_maintenance_amount / 12) × cost_index(t)

housing_cost_buy(t) = payment(t) + levy(t) + insurance(t) + maintenance(t)
```

The **flat** components are cost-indexed rather than tied to the
appreciating home value, because no shipped region's flat-levy base tracks
market prices: France assesses the *valeur locative cadastrale*, Germany the
*Grundsteuerwert*, and the UK uses 1991 valuation bands. Both levy
components land in the same `levy(t)` term, so the reported property-tax
total, the deduction base (§6) and the ownership-cost breakdown all stay
consistent.

**Deliberate modeling change:** maintenance tracks the home's appreciation
only, through `home_value(t-1)`. It is *not* separately compounded by
`cost_inflation_rate` on top of that. The previous engine applied both
appreciation (via the home-value base) and `cost_inflation_rate` to
maintenance, effectively double-inflating it. This is intentional, not a
bug — maintenance cost is modeled as a fixed percentage of the (appreciating)
home value, matching how the "1% of home value per year" rule of thumb is
usually meant. Insurance, by contrast, has no home-value base and is
inflated by `cost_inflation_rate` directly, as before.

### Rent (renter)

Rent is set at the end of the prior month and paid during the current one;
`rent_growth_monthly` may itself vary month to month:

```
rent_level(0) = monthly_rent
rent_level(t) = monthly_rent × ∏_{m=1}^{t} (1 + rent_growth_monthly[m])

housing_cost_rent(0) = 0
housing_cost_rent(t) = rent_level(t-1)                             for t ≥ 1
                     + levy(t)      if levy_paid_by_occupier
```

> **The Verdict is invariant to an occupier-borne levy**, in the sense that
> charging `L` to both arms leaves it unchanged: `surplus = (b + L) − (r + L)
> = b − r`, so contributions and both portfolios are unchanged; and
> `max(b + L, r + L) = max(b, r) + L`, so `cash_committed` rises identically
> on both arms and cancels in the difference. Only the displayed monthly
> costs and the cumulative-outflow chart move. The equivalence holds while
> the levy is not deductible; where it is, the buyer additionally accrues
> the tax shield on it (§6).
>
> It is **not** invariant to toggling the flag at a fixed levy — that moves
> the cost from one arm to two, which is a real change in who pays.

Note the shift: the cost paid *during* month t uses `rent_level(t-1)`, the
level fixed at the *end* of month t-1 — mirroring the buyer's cost base.

## 4. Cash-Flow Matching

Both strategies spend the same total cash every month; whichever side is
cheaper in a given month invests the difference in equities within its own
strategy (**Cash-flow matching**, CONTEXT.md):

```
surplus(t) = housing_cost_buy(t) - housing_cost_rent(t)

contrib_rent(t) = max(surplus(t), 0)    # renting is cheaper -> renter invests the gap
contrib_buy(t)  = max(-surplus(t), 0)   # buying is cheaper -> buyer invests the gap
```

The renter also invests the capital not spent on buying — `initial_outlay`
(down payment + buyer closing costs) — as a lump sum at t = 0; this seeds
the rent portfolio's `V0` (Section 5).

Cash committed is, by construction, identical for both strategies at every
t (only its split between "spent" and "invested" differs):

```
cash_committed(t) = initial_outlay + Σ_{m=1}^{t} max(housing_cost_buy(m), housing_cost_rent(m))
```

The charted cumulative outflows (money actually spent on housing, excluding
what gets invested) are:

```
outflow_buy(t)  = initial_outlay + Σ_{m=1}^{t} housing_cost_buy(m)
outflow_rent(t) = Σ_{m=1}^{t} housing_cost_rent(m)
```

## 5. Portfolios with Varying Rates

Both the rent portfolio and the buy-side surplus portfolio use the same
closed-form update for a portfolio earning a possibly time-varying monthly
rate `rate_m` and receiving contribution `c[m]` during month m:

```
G(0) = 1
G(t) = ∏_{m=1}^{t} (1 + rate_m)                 # cumulative growth factor

V(t) = G(t) × ( V0 + Σ_{m=1}^{t} c[m] / G(m) )
```

### Annual portfolio drag (wealth tax)

An annual wealth tax charged on portfolio *value* is exactly a reduction in
the compounding rate:

```
V(t) = V(t-1)(1 + g) − V(t-1)·d = V(t-1)(1 + g − d)
```

The Netherlands (box 3, Wet IB 2001 art. 5.25) assesses the taxpayer on the
**lesser** of a deemed return and the actual return, floored at nil, so `d`
is evaluated per year against that year's own return:

```
R(y)       = Σ_{m in year y} eq_rate_monthly[m]        # arithmetic SUM
taxable(y) = max( min(deemed_rate, R(y)), 0 )          # art. 5.25 lid 1 + lid 2
d_m(y)     = taxable(y) × (portfolio_drag_rate_pct / 100) / 12

G(0) = 1
G(t) = ∏_{m=1}^{t} (1 + eq_rate_monthly[m] − d_m(year of m))
```

Four things this form depends on:

- **`R(y)` is a sum, not a compound.** The engine feeds arithmetic
  `annual / 100 / 12` monthly rates, so twelve of them sum back to the
  annual figure exactly. Compounding them would return 7.229% for a 7%
  input and silently shift the `min` against a 6% deemed return.
- **Both operands of the `min` are proportional to wealth**, so the
  comparison reduces to a comparison of *rates* and `G(t)` stays a pure
  cumulative product — no month loop and no wealth-feedback term. This
  holds only because the exemption allowance is not modelled.
- **The `min` is evaluated per year against each path's own realised
  return**, so the drag is path-dependent under Monte Carlo and must not be
  pre-averaged. The tax is concave in the return, so by Jensen's inequality
  a single pre-multiplied rate overstates the mean tax.
- **The bases are contribution sums and are correctly unaffected** — a user
  who also sets a portfolio CG rate is then taxed on a smaller gain.

The drag applies symmetrically to both portfolios; any asymmetry between
the two strategies emerges from their different sizes, not from a branch.

Applied with `eq_rate_monthly` as the rate and `c = contrib_rent` /
`contrib_buy`:

```
eq_growth(t)     = G(t) using eq_rate_monthly

rent_portfolio(t) = eq_growth(t) × ( initial_outlay + Σ_{m=1}^{t} contrib_rent(m) / eq_growth(m) )
buy_portfolio(t)  = eq_growth(t) × Σ_{m=1}^{t} contrib_buy(m) / eq_growth(m)
```

(`rent_portfolio` starts with `V0 = initial_outlay`; `buy_portfolio` starts
with `V0 = 0` — the buyer has no lump sum to invest at t = 0.)

Cost basis (principal contributed, used for capital-gains tax in Section 6)
is the un-discounted running total of contributions:

```
basis_rent(t) = initial_outlay + Σ_{m=1}^{t} contrib_rent(m)
basis_buy(t)  = Σ_{m=1}^{t} contrib_buy(m)
```

## 6. Taxes

This section documents the app's **Tax primitives** (CONTEXT.md): the deductibility of mortgage interest and property levy, the home-sale capital-gains regime, and the symmetric portfolio capital-gains treatment at exit.

### Deduction savings (buyer)

Mortgage interest and (capped) property levy paid are deductible at the
marginal rate. Savings are credited once per completed year — not smoothed
across the months of that year — using the year the month falls in,
`t // 12` (only enabled when `interest_deduction_enabled` and
`marginal_tax_rate_pct > 0`):

```
yearly_interest(y) = Σ_{month in year y} interest(month)     # y = 0..horizon_years-1
yearly_levy(y)      = Σ_{month in year y} levy(month)
yearly_levy(y)      = min(yearly_levy(y), levy_deduction_cap)   # if levy_deduction_cap is set

yearly_savings(y) = (yearly_interest(y) + yearly_levy(y)) × (marginal_tax_rate_pct / 100)

cum_by_year(0) = 0
cum_by_year(y) = cum_by_year(y-1) + yearly_savings(y-1)   for y ≥ 1

cum_tax_savings(t) = cum_by_year(t // 12)
```

`cum_tax_savings(t)` is therefore a step function: it holds flat through
the 12 months of a year and jumps once, at the year boundary, by that
year's full savings.

`yearly_levy(y)` sums the **whole** `levy(t)` term, so the deduction base
includes both the ad-valorem component and the flat `annual_property_levy`.
The cap has three distinct settings:

| `levy_deduction_cap` | Meaning |
|---|---|
| `None` | Uncapped — the full levy is deductible |
| `0` | The levy is **not deductible at all** (Netherlands) |
| `> 0` | Deductible up to that amount (US SALT cap: 10,000) |

On the client a **negative** value encodes "uncapped" and is sent as
`null`; zero is a real, reachable value.

### Sale capital gains (buyer, at exit)

Taxable gain depends on the region's `sale_cg_regime` (ADR-0007):

```
home_gain(t) = max(home_value(t) - property_price, 0)

fully_exempt:        taxable_gain(t) = 0
exempt_amount:       taxable_gain(t) = max(home_gain(t) - sale_cg_exempt_amount, 0)
exempt_after_years:   taxable_gain(t) = 0            if t ≥ sale_cg_exempt_after_years × 12
                      taxable_gain(t) = home_gain(t)  otherwise

sale_cg_tax(t) = taxable_gain(t) × (sale_cg_rate_pct / 100)
```

### Portfolio capital gains (both strategies, at exit)

Applied symmetrically to whichever portfolio the strategy is holding, on
gains over its own cost basis:

```
portfolio_tax_rent(t) = max(rent_portfolio(t) - basis_rent(t), 0) × (portfolio_cg_rate_pct / 100)
portfolio_tax_buy(t)  = max(buy_portfolio(t) - basis_buy(t), 0)  × (portfolio_cg_rate_pct / 100)
```

## 7. Net Value, Verdict, and Breakeven

**Net Value** at t is the wealth you would walk away with if you exited at
t, minus all cash committed through t. Exit is priced fully at every t —
this is what makes it liquidation-based (ADR-0001):

```
seller_cost(t) = home_value(t) × (closing_cost_seller_pct / 100)

Net_Buy(t) = home_value(t) - B(t) - seller_cost(t) - sale_cg_tax(t)
             + buy_portfolio(t) - portfolio_tax_buy(t)
             + cum_tax_savings(t)
             - cash_committed(t)

Net_Rent(t) = rent_portfolio(t) - portfolio_tax_rent(t) - cash_committed(t)
```

The **Verdict** is simply this same series read at the Horizon:

```
Verdict = Net_Buy(H) - Net_Rent(H)
```

`Verdict > 0` means Buy wins; `Verdict < 0` means Rent wins.

The **Breakeven** is the year where the two series cross — computed from
the identical `Net_Buy`/`Net_Rent` arrays used for the Verdict and the
charts, so it can never disagree with either. `diff(t) = Net_Buy(t) -
Net_Rent(t)`; the engine scans for a sign change between consecutive months
i, i+1 and linearly interpolates in *years* (`year = t / 12`):

```
t* = year_i - diff_i × (year_{i+1} - year_i) / (diff_{i+1} - diff_i)
```

(If `diff` lands exactly on zero at some month i > 0 rather than crossing
between two months, the Breakeven is that month's year directly, no
interpolation needed.) If no sign change occurs across the whole Horizon,
there is no Breakeven (one strategy dominates throughout). The search skips
any trivial t=0 equality, and when a sign change is detected but the
bracketing values are numerically close, it reports the crossing at the
earlier point to avoid dividing by a near-zero denominator.

## 8. Monte Carlo

Monte Carlo (`monte_carlo.py`) draws year-varying rates and feeds them
through the *exact same* `_net_value_series()` core used above — it cannot
compute a different Net Value than the deterministic engine (ADR-0001,
ADR-0003).

### Annual draws

Property appreciation and equity growth are drawn jointly from a bivariate
normal (annual, percentage-point units), correlated because both track the
same broad economy:

```
mean = (property_appreciation_annual, equity_growth_annual)
cov  = [[σ_prop², ρ·σ_prop·σ_eq],
        [ρ·σ_prop·σ_eq, σ_eq²]]

(prop_annual(y), eq_annual(y)) ~ MultivariateNormal(mean, cov)   for each simulation, each year y
```

with the app's fixed calibration: `σ_prop = 8`, `σ_eq = 15`, `ρ = 0.3`
(ADR-0003 — not user-configurable). Rent inflation is drawn independently
and clamped non-negative:

```
rent_annual(y) ~ Normal(rent_inflation_rate × 100, σ_rent),  σ_rent = 1.5
rent_annual(y) = max(rent_annual(y), 0)
```

### Expansion to monthly rates

Each annual percentage draw is held constant across its 12 months and
converted to a monthly decimal rate before being handed to
`_net_value_series`:

```
rate_monthly[m] = annual_draw(y) / 100 / 12    for every month m in year y
```

`net_buy`/`net_rent` for that simulation path are exactly the Section 7
series computed with these month-varying rates in place of the
deterministic engine's constant ones. Percentiles and the buy-win share
derive from these same per-path Net Value series — never a separately
defined metric.

The tornado chart does not. It is one-at-a-time sensitivity on the
*deterministic* engine: for each candidate parameter it re-runs
`calculate_scenarios` at ±1 standard deviation and reads
`final_difference`. The MC paths are not involved.

Two details are region-specific. Both levy fields — ad-valorem
`property_tax_rate` and flat `annual_property_levy` — take a **relative**
swing of `0.5 / 1.2` (≈ ±41.7%) rather than an absolute one, so a
region's measured sensitivity does not depend on which unit its bundle
expresses the levy in. An absolute ±0.5pp on the Netherlands' folded-EWF
0.2815 would be a ±178% swing implying a regime it does not have; the
relative factor is calibrated so the US base of 1.2 keeps its historical
delta of exactly 0.5.

A levy bar is dropped when it would carry no information: at a zero base
(the region carries its levy in the other field), when the low side would
clamp against the positive-only floor and so misrepresent its own
direction, and — for the flat levy — when the swing is negligible against
the Verdict, which happens exactly when the levy is occupier-borne and
therefore cancels between the two arms.
