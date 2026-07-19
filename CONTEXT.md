# Rent-vs-Buy Simulator

A public web app that answers one question for one person: "should I buy this home or keep renting?" It is a decision tool, not a simulation workbench — every surface serves the verdict.

## Language

**Verdict**:
The single headline answer the app produces for a given set of inputs: which strategy leaves you wealthier at the horizon, and by how much.
_Avoid_: Winner, difference, result

**Net Value**:
The wealth you would walk away with if you exited a strategy at year t, minus all cash you put in through t. Exit is priced fully and symmetrically: for Buy, home value − mortgage balance − seller closing costs − capital-gains tax beyond the Section 121 exclusion + accrued tax savings; for Rent, portfolio value − capital-gains tax on gains − cumulative rent. One formula, applied at every t, used by the verdict, the charts, the breakeven, and Monte Carlo alike.
_Avoid_: Net worth, equity, asset value minus outflows

**Breakeven**:
The year at which the Buy and Rent Net Value series cross. Derived from the same series as the Verdict — never computed from a different definition.

**Horizon**:
The number of years the person expects to stay before exiting the strategy.
_Avoid_: Duration, simulation period

**Buy strategy**:
Purchase the home with a mortgage. Monthly cost is mortgage + property tax + insurance + maintenance. When buying is the cheaper side in a given month, the surplus is invested in equities within this strategy.
_Avoid_: Scenario A

**Rent strategy**:
Rent the home and invest the capital not spent on buying: the down payment and buyer closing costs at t=0 (in equities), plus the monthly surplus whenever renting is the cheaper side. There is exactly one Rent strategy.
_Avoid_: Scenario B, Scenario C, Rent + Invest Savings

**Confidence**:
The share of simulated futures in which the Verdict's winning strategy still wins, produced by the auto-run Monte Carlo over the same Net Value series. Always presented alongside the Verdict, never as a separate analysis with its own answer.
_Avoid_: Buy wins %, probability tab

**Cash-flow matching**:
The rule that makes the two strategies comparable: both spend the same total cash each month, and whichever side has lower housing costs invests the difference in equities in its own scenario. Symmetric — it can flow to either side, and flips over the life of the mortgage.
_Avoid_: Monthly savings (the old mortgage−rent-only formula)

**Region**:
A named bundle of trustworthy defaults — currency formatting plus tax-primitive and cost values — for one housing market. Ships US, France (Lyon), Germany (Köln), Netherlands, United Kingdom (England & NI). Regions configure the engine; the engine contains no per-country logic.
_Avoid_: Country mode, locale

**Tax primitives**:
The neutral, scalar parameters through which every region's rules are expressed: buyer transaction costs (a percentage of price **plus a fixed amount, which may be negative where a transfer tax has a zero-rate band**), seller transaction costs, annual property levy (**ad-valorem, plus a flat cost-indexed amount, plus a flag for whether the occupier rather than the owner bears it**), maintenance (**a percentage of value or a flat cost-indexed amount, whichever unit the region's own evidence is collected in**), mortgage-interest deductibility (on/off + rate + a cap where 0 means "not deductible" and None means uncapped), capital-gains treatment at each exit (exemption amount, exempt-after-N-years, or fully exempt; plus a portfolio gains rate), and **annual portfolio drag** — a tax on portfolio *value* rather than on realised gains, applied symmetrically to both strategies, expressed as a deemed return plus a rate and charged on the **lesser of that deemed return and the actual return, floored at nil** (NL box 3).
_Avoid_: per-country logic, effective-rate fudges

**Portfolio tax wrappers**:
Deliberately out of scope in every region — ISA, PEA, Sparer-Pauschbetrag, heffingsvrij vermogen and 401(k)/IRA are not modelled, so every portfolio is a plain taxable brokerage account (ADR-0009). This understates after-tax returns for wrapper users and biases every region toward buying; it is disclosed in each region's `notes`.
_Avoid_: treating a sheltered rate as a region default

## Example dialogue

> **Dev:** The chart shows Buy ahead at year 30 but the verdict says Rent wins — which is right?
> **Expert:** Then there's a bug: the Verdict *is* Net Value at the Horizon. If a chart disagrees with the verdict, that chart isn't plotting Net Value.
> **Dev:** Should the breakeven marker account for selling costs?
> **Expert:** It already must — Net Value prices the exit at every year, so breakeven inherits it for free.
