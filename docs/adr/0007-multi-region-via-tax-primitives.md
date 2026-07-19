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

**The primitive list has grown.** "Five neutral primitives" is now seven categories: buyer transaction costs **including a fixed component**, seller transaction costs, annual property levy **including a flat component, an incidence flag, and a maintenance amount**, interest deductibility + rate, CG treatment at exit including the portfolio gains rate, and **annual portfolio drag, expressed as a deemed return and a rate applied to the lesser of that and the actual return**. All remain scalar, and the "countries are data, not code" decision is unaffected — no per-country branch exists in the engine.

See `docs/multi-region-spec.md` for the full derivation and `tests/test_regions.py` for the source-cited fixtures.
