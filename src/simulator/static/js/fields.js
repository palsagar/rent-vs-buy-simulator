// Input field definitions: bounds, allowed values, and display metadata.
// Extracted into its own module (a leaf that imports only format.js) so
// both inputs.js (rendering) and state.js (share-URL validation) can read
// the field bounds without forming an import cycle.

import { fmtCompact, fmtMoney, fmtPct } from "./format.js";

export const INPUT_DEFS = [
  { key: "propertyPrice", label: "Home price", min: 50000, max: 2000000, step: 5000, fmt: fmtCompact, section: "core", hint: "Purchase price of the property" },
  { key: "downPaymentPct", label: "Down payment", min: 5, max: 50, step: 1, fmt: (v) => fmtPct(v, 0), section: "core" },
  { key: "mortgageRateAnnual", label: "Mortgage rate", min: 1, max: 10, step: 0.05, fmt: (v) => fmtPct(v, 2), section: "core" },
  { key: "mortgageTermYears", label: "Mortgage term", type: "segmented", options: [15, 20, 25, 30], section: "core", hint: "Amortization period — independent of the horizon" },
  { key: "monthlyRent", label: "Monthly rent", min: 500, max: 10000, step: 50, fmt: fmtMoney, section: "core" },
  { key: "horizonYears", label: "Horizon", min: 2, max: 40, step: 1, fmt: (v) => `${v} yrs`, section: "core", hint: "Years until you'd sell — the chart x-axis ends here" },
  { key: "propertyAppreciationAnnual", label: "Property appreciation", min: 0, max: 10, step: 0.1, fmt: (v) => fmtPct(v), section: "assumptions" },
  { key: "equityGrowthAnnual", label: "Equity growth (CAGR)", min: 0, max: 15, step: 0.1, fmt: (v) => fmtPct(v), section: "assumptions" },
  { key: "rentInflationRate", label: "Rent inflation", min: 0, max: 10, step: 0.1, scale: 100, fmt: (v) => fmtPct(v), section: "assumptions" },
  { key: "closingCostBuyerPct", label: "Buyer closing costs", min: 0, max: 15, step: 0.1, fmt: (v) => fmtPct(v), section: "advanced", hint: "German buyer costs reach ~12% with Grunderwerbsteuer and Makler" },
  { key: "closingCostSellerPct", label: "Seller closing costs", min: 0, max: 10, step: 0.1, fmt: (v) => fmtPct(v), section: "advanced" },
  { key: "propertyTaxRate", label: "Property levy (% of value)", min: 0, max: 5, step: 0.0005, fmt: (v) => fmtPct(v, 2), section: "advanced" },
  { key: "annualHomeInsurance", label: "Home insurance /yr", min: 0, max: 5000, step: 50, fmt: fmtMoney, section: "advanced" },
  { key: "annualMaintenancePct", label: "Maintenance", min: 0, max: 5, step: 0.1, fmt: (v) => fmtPct(v), section: "advanced" },
  { key: "costInflationRate", label: "Cost inflation", min: 0, max: 10, step: 0.1, scale: 100, fmt: (v) => fmtPct(v), section: "advanced" },
  { key: "interestDeductionEnabled", label: "Interest deductible", type: "checkbox", section: "advanced", hint: "Deduct mortgage interest (and capped levy) from taxable income" },
  { key: "marginalTaxRatePct", label: "Marginal tax rate", min: 0, max: 60, step: 0.01, fmt: (v) => fmtPct(v, 0), section: "advanced" },
  { key: "levyDeductionCap", label: "Levy deduction cap", min: -1000, max: 50000, step: 1000, fmt: (v) => (v < 0 ? "uncapped" : fmtMoney(v)), section: "advanced", hint: "Leftmost = uncapped · 0 = levy not deductible · US SALT cap is $10k" },
  { key: "saleCgRegime", label: "Home-sale CG rule", type: "select", options: [["exempt_amount", "Exempt up to a fixed amount"], ["exempt_after_years", "Exempt after N years"], ["fully_exempt", "Always exempt"]], section: "advanced" },
  { key: "saleCgExemptAmount", label: "Exempt gain amount", min: 0, max: 1000000, step: 10000, fmt: fmtCompact, section: "advanced" },
  { key: "saleCgExemptAfterYears", label: "Exempt after (years)", min: 0, max: 30, step: 1, fmt: (v) => `${v} yrs`, section: "advanced" },
  { key: "saleCgRatePct", label: "Home-sale CG rate", min: 0, max: 40, step: 0.5, fmt: (v) => fmtPct(v), section: "advanced" },
  { key: "portfolioCgRatePct", label: "Investment CG rate", min: 0, max: 40, step: 0.5, fmt: (v) => fmtPct(v), section: "advanced" },
  { key: "closingCostBuyerAmount", label: "Buyer fixed costs", min: -20000, max: 20000, step: 100, fmt: fmtMoney, section: "advanced", hint: "Flat costs on top of the percentage. Negative where a transfer tax has a zero-rate band (UK SDLT)." },
  { key: "annualPropertyLevy", label: "Property levy /yr (flat)", min: 0, max: 10000, step: 50, fmt: fmtMoney, section: "advanced", hint: "Flat annual levy that does not scale with the home's value (UK council tax, DE Grundsteuer)." },
  { key: "levyPaidByOccupier", label: "Levy paid by occupier", type: "checkbox", section: "advanced", hint: "Charge the levy to the renter as well as the buyer (UK council tax, DE umlagefähige Grundsteuer)." },
  { key: "annualMaintenanceAmount", label: "Maintenance /yr (flat)", min: 0, max: 10000, step: 50, fmt: fmtMoney, section: "advanced" },
  { key: "portfolioDeemedReturnPct", label: "Deemed return (wealth tax)", min: 0, max: 15, step: 0.05, fmt: (v) => fmtPct(v, 2), section: "advanced", hint: "Assumed return the wealth tax is charged on. Taxed on the LESSER of this and your actual return (NL box 3)." },
  { key: "portfolioDragRatePct", label: "Wealth-tax rate", min: 0, max: 60, step: 0.5, fmt: (v) => fmtPct(v, 1), section: "advanced", hint: "Rate applied to that deemed return, annually, on portfolio value — not on realised gains." },
];
