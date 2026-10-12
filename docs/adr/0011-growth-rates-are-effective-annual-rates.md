# Yearly growth rates compound as stated

Every growth rate a person types is a yearly rate: home appreciation, equity growth, rent inflation and cost inflation. The engine turned each into a monthly rate by dividing by 12 and compounding twelve times, which is worth more than the number typed: 7% a year became 7.23%, and 15% over 40 years grew money 388.7 times instead of 267.9 times (#36). The overstatement grows with the rate, so the renter's equity return, usually the highest rate in the model, was inflated the most. Each yearly growth rate now converts to the monthly rate that compounds back to it exactly, `(1 + r)^(1/12) − 1` (`monthly_rate_from_annual` in `engine.py`), so a 7% input is worth exactly 7% after twelve months.

## Considered Options

- Keep dividing by 12 and say so in the copy: rejected. The sliders say "per year", and a person who types 7% means 7% more after a year. Documenting a convention that contradicts the label does not make the label true.
- Compound every rate from its yearly figure, the mortgage rate included: rejected. Mortgage rates are quoted as a nominal yearly rate split over twelve payments, and `numpy_financial.pmt` and the closed-form balance expect exactly that. Some European lenders also publish an effective rate (the French TAEG, the German Effektivzins); modelling it is a separate decision.
- Compound growth rates as stated, keep the mortgage rate nominal, and split yearly charges into twelve equal bills: chosen.

## Consequences

- Each yearly input converts by kind:

  | Input | Kind | Monthly form |
  |---|---|---|
  | Property appreciation, equity growth, rent inflation | Growth rate | `(1 + r)^(1/12) − 1` |
  | Cost inflation, which indexes the fixed costs | Growth rate | `cost_index(t) = (1 + r)^((t − 1)/12)` |
  | Mortgage rate | Nominal yearly rate | `r / 12` |
  | Property levy, insurance, maintenance, mortgage insurance, box-3 drag | Yearly charge | one twelfth each month |

- Monte Carlo converts each yearly draw with the same helper, so twelve months compound back to exactly the draw, and a run with no volatility still equals the deterministic engine. The helper floors a draw at −99%, where the twelfth root is undefined; the tornado's floor for growth rates was already −99%.
- The NL box-3 yearly return is the product of the year's twelve monthly factors, which is exactly the yearly rate. The sum of the twelve, which matched the old division by 12, now falls short of it.
- Monte Carlo moves more than the deterministic Verdict. Dividing by 12 gave a year drawn at `r` a growth of about `r + (11/24) r²`, a bonus that rose with the spread of the draws: about 1.26% a year on average for equity, against 0.22% for a steady 7%. Removing it lowered the renter's simulated wealth most, so buying's share of simulated futures rose at every region's defaults (US: 46.4% to 49.0%).
- At the US default the Verdict moves from +$1,248 to +$4,060 and stays a toss-up. The change is largest at long horizons and high equity rates: 40 years at 15% moves from −$56.9M to −$39.2M. The other regions' defaults move by less than 2,000 in their currency (UK −£286, FR +€1,325, DE +€1,864, NL +€416).
- The US regression goldens were regenerated once for this ADR. The three fields no growth rate reaches (`monthly_mortgage_payment`, `total_closing_costs_buyer`, `total_mortgage_interest_paid`) are pinned at their old values, bit for bit.
- The box-3 drag is still a twelfth of the yearly charge each month. A drag that reproduces the 1 January assessment exactly, `d_m = (1 + R)^(1/12) − (1 + R − d)^(1/12)`, would close known gap S10 (the annual form is now 3.37% above the monthly one over 30 years, from 3.36%). It is a possible follow-up, not part of this decision.
