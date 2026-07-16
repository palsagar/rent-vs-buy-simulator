# Monte Carlo runs automatically with fixed, app-owned calibration

Uncertainty analysis exists to qualify the Verdict ("Buying wins in N% of simulated futures"), not to be a configurable stats lab. Monte Carlo therefore runs automatically (debounced/cached as needed) and exposes zero knobs: no simulation count, seed, correlation, or volatility sliders. Volatility calibration is the app's responsibility and is set to historically-grounded values — notably equity volatility ~15%/yr (the old 5% default understated equity risk and made renting look artificially safe) — documented in the guide.

## Considered Options

- Keeping user-tunable std/seed/correlation sliders: rejected — users shouldn't need to know market volatilities to get a trustworthy answer, and bad inputs silently produce misleading confidence numbers.
- A coarse "uncertainty: low/typical/high" selector: deferred — add only if users ask.

## Consequences

- Results are presented as a percentile fan chart of the Net Value difference (median + 50%/90% bands) and a tornado chart ("which assumption to stress-test hardest"), both Plotly; the matplotlib spaghetti chart and the standalone probability-over-time curve are removed.
- Reproducibility is an internal concern (fixed internal seed), no longer a user-facing feature.
