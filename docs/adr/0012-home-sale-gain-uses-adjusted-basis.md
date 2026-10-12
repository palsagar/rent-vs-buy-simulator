# The taxed home-sale profit is net of buying and selling costs

The engine taxed a home sale on the gross rise in value, `home_value − property_price`. The seller's costs came out of the proceeds separately, and the buyer's costs were never added to what the home cost (#37). So tax was charged on money the seller never received, which understated Buy wherever a sale is taxed and could flip such a verdict. The taxed profit is now what the sale brings in over what the home cost:

```
home_gain(t) = max((home_value(t) − seller_cost(t)) − (property_price + buyer_closing), 0)
```

The region's regime (tax-free up to an amount, tax-free after N years, or always tax-free) and its rate then apply unchanged.

## Considered Options

- Keep the gross rise and document it: rejected. No regime the app ships taxes it (table below), and it taxes money the seller never receives.
- Let each region choose which costs count: rejected. Every shipped regime already nets both costs out, so the choice could only select a wrong rule.
- Tax the profit after buying and selling costs in every region: chosen. It is also the counterpart of the portfolio rule (ADR-0001), which taxes value over what was paid in: both exits tax what comes out over what went in.

## Consequences

- Where a sale is taxed, the change always favours buying. The US default is unchanged: its profit, $116,641 after costs ($171,958 before), is under the $250,000 exclusion either way. In the tornado at the US default only one value moves, Property Appreciation's higher side (+$9,958), whose test grows the home above the exclusion.
- An instant resale is a loss of exactly both fees and is never taxed, and a sale that does not cover its costs is not taxed at all.
- Every regime the app ships nets these costs out. Each source was checked against the primary text or the tax administration's own doctrine:

  | Region | Shipped regime | Rule in law |
  |---|---|---|
  | US | Tax-free up to $250,000, then 15% | Gain is the amount realized (sale price less selling expenses) over the adjusted basis, which includes the settlement fees and closing costs paid at purchase, except financing costs (IRS Publication 523, 2025) |
  | UK | Always tax-free (Private Residence Relief) | The incidental costs of acquisition and of disposal are allowable, stamp duty land tax included (TCGA 1992 s.38(1)(a), (c) and (2)) |
  | FR | Always tax-free (CGI art. 150 U II 1°) | The sale price is reduced by the seller's costs (CGI art. 150 VA III; BOI-RFPI-PVI-20-10-10 §80, which lists the agency commission), and the purchase price is increased by the purchase costs, actual or a flat 7.5% (art. 150 VB II 3°; BOI-RFPI-PVI-20-10-20-20 §30) |
  | DE | Always tax-free (§23 Abs. 1 Satz 1 Nr. 1 Satz 3 EStG) | Gain is the Veräußerungspreis less the Anschaffungskosten and the Werbungskosten (§23 Abs. 3 Satz 1 EStG) |
  | NL | Always tax-free (box 1) | No capital-gains tax on the home |

  Outside the US the rule matters only if a person changes the regime in Advanced. No new primitive was needed, so ADR-0007's "countries are data" holds.

  CGI art. 150 VA and 150 VB were verified through the French tax administration's published doctrine (BOFiP, the two BOI-RFPI-PVI documents cited above, which quote and apply them), because Légifrance, the official text, could not be reached when this was written. The other rows were checked against the primary text.
- Two simplifications remain. The whole buyer closing cost counts towards what the home cost, while US law leaves out financing costs such as loan points; that overstates the US cost slightly and favours buying when the profit exceeds the exclusion. France's optional flat 7.5% for purchase costs is not modelled; the actual buyer costs are used.
