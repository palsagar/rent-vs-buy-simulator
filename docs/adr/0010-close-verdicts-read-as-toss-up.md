# Close verdicts read as a toss-up

When the Verdict's winning strategy wins in 40% to 60% of simulated futures (the Confidence, rounded as displayed), the headline stops naming a winner and says the result is too close to call, while still showing the gap: "Too close to call: buying and renting end within ~$1,248 of each other after 10 years". The default US scenario is such a case — a $1,248 gap on a $500,000 home, with buying ahead in 46% of futures — and the old headline, "Buying leaves you ~$1,248 wealthier", told a first-time visitor the opposite of what the confidence line beside it said.

## Considered Options

- Keep the winner headline and add a "close call" note under it: rejected — the headline is what people read and repeat, and a note does not stop it from naming a winner the simulation does not back.
- A threshold on the size of the gap (for example, a share of the home price): rejected — the gap alone does not say how sure the result is. Confidence already measures that, and CONTEXT.md requires it to travel with the Verdict.
- A toss-up headline when Confidence is 40–60%: chosen.

## Consequences

- The headline can change when Monte Carlo finishes, a few hundred milliseconds after the deterministic run. While a slider is dragged, the toss-up state carries over to each new deterministic result until the matching Monte Carlo result replaces it, so a drag inside a toss-up does not flash the winner headline. Any other change (a region, an outlook, the first-time-buyer pill, a typed value, a checkbox, a dropdown, the mortgage-term buttons) can land far from the result Monte Carlo judged, so it drops the toss-up state: the new result names its winner until its own Monte Carlo result says otherwise. A Monte Carlo result that was still on its way when such a change happened is not shown.
- Below 40% the deterministic winner loses in most simulated futures, and the headline still names it. That case is left for a separate decision.
- The Verdict itself (winner, difference, breakeven) is unchanged and still computed server-side only (ADR-0008). Only the headline wording depends on Confidence.

## Amendment (2026-10): an exact tie

A gap under half a unit of currency (`TIE_TOLERANCE`, 0.5) is reported as `winner: "tie"`, because every surface would print it as "~$0". The headline then reads "Buying and renting leave you equally well off after N years", with no amount and no colour, and it takes precedence over the toss-up wording. The breakeven line says neither pulls ahead, and the confidence line shows buying's share. Monte Carlo counts a tied future as half a win for each side, with the same boundary, so buying's share and renting's still add up to 100%. A Verdict that is not a finite number is an error (HTTP 500) and never a winner: NaN fails every comparison, so the old `> 0` rule reported it as Rent. The toss-up rule is unchanged and applies to every Verdict that is not a tie.
