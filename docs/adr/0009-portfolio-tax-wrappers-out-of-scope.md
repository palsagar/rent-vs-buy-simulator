# Portfolio tax wrappers are out of scope; every region models a plain taxable account

Every shipped region models the equity portfolio as a plain taxable brokerage account. ISA (UK), PEA (FR), Sparer-Pauschbetrag (DE), heffingsvrij vermogen (NL) and 401(k)/IRA (US) are not modelled. ADR-0007 never made this decision — it enumerated tax primitives without saying whether sheltered accounts were among them — and the omission is the single largest systematic bias in the shipped model, so it needs a durable record rather than a line in a spec.

## Considered Options

- Per-region sheltered defaults (ISA 0%, PEA 18.6%): rejected — PEA is EU-equity-only, so it assumes a portfolio the user is not buying; ISA and Sparer-Pauschbetrag caps bind inside the horizon, so a flat sheltered rate is wrong from roughly year 3 onward.
- A `portfolio_wrapper` primitive with a contribution cap: rejected — a cap is not a scalar rate, it needs a per-month allowance loop against the vectorised portfolio update, and it would be the sixth primitive serving a case no region's *default* needs.
- Plain taxable everywhere: chosen. The portfolio CG rate is already a user-editable Advanced field, so a wrapper user can set it to 0 themselves.

## Consequences

- The tool **understates after-tax portfolio returns for wrapper users in every region, including the US**. Because the renter holds the larger portfolio in most configurations, this biases every region's verdict **toward buying**.
- The bias is disclosed in each region's `notes` and rendered in the methodology footer, so it is visible to the user rather than buried here.
- This will be re-litigated the first time a UK user notices ISA is missing. The answer is the second bullet under Considered Options: caps bind inside the horizon, so a flat rate is not a fix.
