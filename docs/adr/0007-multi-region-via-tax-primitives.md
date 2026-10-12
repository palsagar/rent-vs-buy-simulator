# Multi-region support via parameterized tax primitives, not per-country logic

The tool targets two audiences, US and Europe — but "Europe" is not one tax system (Germany: ~10% buyer costs, no interest deduction, sale tax-free after a 10-year hold; France: frais de notaire, immediate primary-residence CG exemption, 30% PFU on equities; Netherlands: interest deduction exists). The engine therefore expresses all tax/cost rules through five neutral primitives (buyer transaction costs, seller transaction costs, annual property levy, interest deductibility + rate, CG treatment at exit incl. portfolio gains rate), and a first-class Region selector fills them from preset bundles. v1 ships US, France, Germany, Netherlands, UK; "Custom" keeps every other country reachable via Advanced.

## Considered Options

- US-only scope: rejected — half the target audience.
- A generic "Europe" profile: rejected — fictional averages dressed as advice.
- Per-country engine code paths: rejected — five primitives cover all five markets; countries are data, not code.

## Consequences

- The US-specific SALT cap becomes a detail of the US preset, not engine logic.
- Currency is formatting only ($, €, £) — no FX, the engine is currency-agnostic.
- Each shipped region's default values are a research-and-verify liability; wrong tax defaults are worse than none.

## Amendment (2026-07, multi-region Phase 1/2)

Two factual claims in the context paragraph above are wrong and are corrected here. The decision itself stands unchanged.

1. **"Germany: sale tax-free after a 10-year hold" is wrong for the owner-occupied case this tool models.** §23 Abs.1 Nr.1 Satz 3 EStG exempts the owner-occupier limb at **any** holding period. The 10-year speculation period applies to non-owner-occupied property, which this tool does not model. This error is not cosmetic: it is why research initially proposed `saleCgRegime: "exempt_after_years", saleCgExemptAfterYears: 10` for Germany, which would have taxed the entire German home gain for any horizon under 10 years. Germany ships `fully_exempt`.

2. **"France: 30% PFU" is now 31.4%** — 12.8% PFU + 18.6% prélèvements sociaux, the PS rise coming via LFSS 2026 (LOI 2025-1403 art. 12, CSG 9.2 → 10.6). Note that the rise does **not** apply to plus-values immobilières, which stay at 17.2%, so the home-sale rate is 36.2%.

3. **No "Custom" region ships.** The context paragraph promises one; it was dropped during design. The Advanced drawer already keeps every other country reachable by hand, so a Custom bundle would have been an empty preset with no values to offer. Five bundles ship: US, FR, DE, NL, UK.

**The primitive list has grown.** "Five neutral primitives" is now six categories: buyer transaction costs **including a fixed component**, seller transaction costs, annual property levy **including a flat component, an incidence flag, and a maintenance amount**, interest deductibility + rate, CG treatment at exit including the portfolio gains rate, and **annual portfolio drag, expressed as a deemed return and a rate applied to the lesser of that and the actual return**. All remain scalar, and the "countries are data, not code" decision is unaffected — no per-country branch exists in the engine.

See `docs/multi-region-spec.md` for the full derivation and `tests/test_regions.py` for the source-cited fixtures.

## Amendment (2026-10): mortgage insurance, and the profit a home sale is taxed on

**One more primitive: mortgage insurance** (`mortgage_insurance_rate_pct`). It is a yearly percentage of the original loan, billed monthly, on a down payment under 20%, while the scheduled balance a month starts with is above 78% of the price. Both thresholds follow US practice: the CFPB states the under-20% trigger, and the Homeowners Protection Act ends the insurance automatically on the date the balance is "first scheduled to reach 78 percent of the original value" (12 U.S.C. 4901(18)). The US ships 0.5%, inside Freddie Mac's "$30 to $70 per month for every $100,000 you borrowed" (0.36–0.84% a year). FR, DE, NL and UK ship 0, because their lenders price a small deposit another way (a one-off guarantee or a higher interest rate), and each region's notes say so.

- It is part of the buyer's monthly cost, so cash-flow matching hands the renter the difference (ADR-0002).
- It is not tax-deductible. US rules on deducting it have changed several times; modelling them would be a separate, sourced decision.
- It has no tornado bar. It is zero in four regions and at the US default 20% down, so a bar would come and go with the down-payment slider; the Down Payment bar already measures it, because its lower test crosses the 20% line at the US default; and a premium is a quote, not a guess about the future.
- The Act's other end date, the midpoint of the loan term, is not modelled: at every slider setting the 78% point comes first.

**The home-sale gain is the profit after buying and selling costs** since ADR-0012. The capital-gains regimes and rates are unchanged.
