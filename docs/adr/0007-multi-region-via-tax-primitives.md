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
