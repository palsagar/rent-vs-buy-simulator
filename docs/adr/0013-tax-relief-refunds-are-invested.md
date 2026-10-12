# Tax-relief refunds are invested in the buyer's portfolio

Where mortgage interest (and in the US the property levy) is deductible, the buyer gets a tax refund at the end of each year. The engine counted those refunds at face value: they were added to Buy's Net Value and earned nothing, while every other spare amount in the model, the renter's and the buyer's alike, is invested (ADR-0002). That understated Buy by the growth the refunds would have earned, about $24,600 at the US defaults, six times the default Verdict (#44 item 12). Each refund now joins the buyer's portfolio in the month it arrives, the month that closes the year. It then grows and is taxed like the rest of that portfolio: its gain at the portfolio capital-gains rate when the portfolio is cashed in (ADR-0001), and the NL box-3 drag every year.

## Considered Options

- Keep the face value and disclose it: rejected. It was the one place where money the model hands a strategy sat idle, and at the US defaults the bias was larger than the Verdict itself.
- Net each refund against the buyer's cost in the month it arrives, so that cash-flow matching does the investing: rejected, although it gives the same Verdict. When buying is the dearer side, the lower cost means the renter invests that much less; when buying is the cheaper side, the buyer invests that much more. Either way the refund's growth after tax lands on the buyer's side of Buy − Rent, and both portfolio taxes are proportional to the money invested. On the engine the two give the same Verdict to the cent at the US defaults, at 10% down, at 40 years and 15%, with buying the cheaper side, over 30 years where the cheaper side changes, and for the NL defaults with box 3. They can differ only where a portfolio ends below what was paid in, because the capital-gains tax stops at zero. But netting shows a refund as a lower cost: the month that closes each year would have a negative buyer cost (−$4,096 at the US defaults), "Buy cost · yr 1" would fall from $3,559 to $2,920 a month, and the outflow chart and the cash both sides commit would change in every refund month.
- Credit each refund to the buyer's portfolio in the month it arrives: chosen. A refund is money coming back, not a lower cost, so no cost, outflow or cash committed changes, and it is invested like the buyer's other spare money.

## Consequences

- Wherever the deduction is on (the US and NL bundles, or any region where Advanced turns it on), Buy rises by the refunds' growth after tax. The US default moves from +$4,060 to +$28,656, and buying wins in 54% of simulated futures, so it is still a toss-up. The NL default moves from +€237,527 to +€251,996. FR, DE and UK ship the deduction off and do not move.
- The effect grows with the horizon and the equity rate: 30 years at 10% equity moves from −$1.68M to −$0.85M, and 40 years at 15% from −$39.2M to −$28.4M.
- `cum_tax_savings` still records the refunds received, at face value. It feeds `totals.taxSavings` and the "Tax savings (offset)" bar in the cost breakdown. Net Value no longer adds it, because the refunds are inside the buyer's portfolio.
- The last year's refund arrives at the Horizon, has no time to grow and counts at face value, as before.
- The model assumes the buyer invests the refund. The US and NL notes say so: a buyer who spends it does worse than shown.
- The US regression goldens were regenerated for this decision. Only `final_net_buy` and `final_difference` (+24,595.62 each) and `breakeven_year` (9.000 to 6.979) moved.
