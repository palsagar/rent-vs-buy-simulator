# Exactly two strategies, compared under cash-flow matching

The app previously modeled three scenarios: A (buy), B (rent, invest only the down payment), and C (rent, invest down payment at a money-market rate plus monthly mortgage−rent savings). B ignored the renter's monthly surplus; C understated it by ignoring the buyer's property tax, insurance, and maintenance — so the two "rent" numbers diverged by hundreds of thousands of dollars and confused rather than informed. We collapsed to one Buy and one Rent strategy compared at equal total monthly outlay: whichever side has lower housing costs in a month invests the difference in equities in its own scenario (symmetric — late in the mortgage the surplus usually flows to the buyer). The renter invests the down payment and buyer closing costs in equities at t=0.

## Considered Options

- Keeping B as a "renter who doesn't invest the difference": rejected — that is a behavioral failure mode, not a strategy; a footnote can acknowledge it.
- Separate money-market rate for the renter's down payment (old Scenario C): rejected — an arbitrary conservatism knob with no stated rationale; one equity CAGR governs invested capital.

## Consequences

- The "Show Scenario C" toggle, "Down Pmt Investment Rate" slider, two summary tiles, and one chart line per chart are removed.
- The Rent strategy is strictly the industry-standard methodology (NYT calculator et al.), which makes the verdict defensible.
