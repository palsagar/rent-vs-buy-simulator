# Net Value is liquidation-based, symmetric, and the only outcome metric

The app previously showed three conflicting "net value for Buy" definitions at once: the headline subtracted seller closing costs but ignored tax benefits, the charts and breakeven ignored both, and Monte Carlo included both — producing contradictory verdicts on one screen. We decided that Net Value(t) is defined as the wealth you would walk away with if you exited the strategy at year t (exit priced fully: seller closing costs and capital-gains tax beyond the Section 121 exclusion for Buy; capital-gains tax on portfolio gains for Rent) minus all cash put in through t, and that every surface — verdict, charts, breakeven, Monte Carlo — computes from this one series.

## Considered Options

- Keep "asset − outflows" and mention exit costs separately: rejected because sign-flip contradictions between chart and verdict remain possible.
- Average-monthly-cost framing (NYT style): rejected as a full rewrite that loses the wealth-trajectory story.

## Consequences

- Buy is deeply negative in early years (transaction costs) — this is honest and is what makes the breakeven meaningful, not a bug.
- Taxes apply to both exits symmetrically; the old "no taxes on investment gains" footnote asymmetry is gone.
