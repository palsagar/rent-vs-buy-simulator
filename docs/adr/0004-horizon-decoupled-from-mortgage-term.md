# Horizon is decoupled from mortgage term

One slider previously set both the loan term and the simulation length, so "simulate 10 years" silently meant "take out a 10-year mortgage". Horizon now means "years until you'd sell" (range ~2–40, default 10 — a realistic stay), while Mortgage Term is a separate input (15/20/30, default 30). Exiting mid-mortgage is priced by the liquidation-based Net Value: the remaining balance is settled from sale proceeds at the Horizon.

## Consequences

- The default verdict describes a realistic 10-year stay, not a full 30-year amortization — this is the regime where buy-vs-rent is genuinely close and the tool is most useful.
- The engine must amortize over the mortgage term but truncate/liquidate the series at the Horizon.
