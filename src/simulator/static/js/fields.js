// Input field definitions: bounds, allowed values, and display metadata.
// Extracted into its own module (a leaf that imports only format.js) so
// its consumers can read the field metadata without forming an import
// cycle: inputs.js (rendering), state.js (share-URL validation) and
// charts.js (the tornado's perturbed-range hover).
//
// Two properties are load-bearing beyond the slider that declares them:
//
//   scale  converts STORED units to DISPLAYED ones. rent_inflation_rate
//          is stored as 0.03 and shown as "3.0%", so a consumer renders
//          `stored * scale` and validates `displayed / scale`. Fields
//          without it are stored in display units.
//   fmt    is the only formatter for that field anywhere in the app.
//          Changing it changes the slider readout AND the tornado hover.
//
// min/max are additionally mirrored in Python: _UI_MAXIMUM and
// _UI_MINIMUM in monte_carlo.py bound the tornado's perturbations to what
// these sliders can express. tests/test_tornado_bounds.py parses this
// file to keep those copies honest, as tests/test_regions.py does for
// region values -- so a value here is a contract, not a local default.
//
// Advanced entries are listed in display order. `group` names the
// collapsible group advanced.js renders them into.

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
  { key: "closingCostBuyerPct", label: "Buying costs (% of price)", min: 0, max: 15, step: 0.001, fmt: (v) => fmtPct(v), section: "advanced", group: "transaction", hint: "One-off costs when you buy: transfer tax, notary, legal and agent fees. In Germany these reach about 12%." },
  { key: "closingCostBuyerAmount", label: "Buying costs (fixed amount)", min: -20000, max: 20000, step: 100, fmt: fmtMoney, section: "advanced", group: "transaction", hint: "Added to the % above. A negative amount is a discount, as with the tax-free band of UK stamp duty." },
  { key: "closingCostSellerPct", label: "Selling costs (% of price)", min: 0, max: 10, step: 0.05, fmt: (v) => fmtPct(v), section: "advanced", group: "transaction", hint: "Agent and legal fees when you sell, taken from the sale price." },
  { key: "propertyTaxRate", label: "Property levy (% of value per year)", min: 0, max: 5, step: 0.0005, fmt: (v) => fmtPct(v, 2), section: "advanced", group: "yearly", hint: "A yearly tax on the home that grows with its value, such as US property tax." },
  { key: "annualPropertyLevy", label: "Property levy (fixed per year)", min: 0, max: 10000, step: 1, fmt: fmtMoney, section: "advanced", group: "yearly", hint: "A yearly tax that does not follow the home's value, such as UK council tax or German Grundsteuer." },
  { key: "levyPaidByOccupier", label: "Renter pays the levy too", type: "checkbox", section: "advanced", group: "yearly", hint: "Turn on where whoever lives in the home pays the levy, as with UK council tax. It then no longer favours renting." },
  { key: "annualHomeInsurance", label: "Home insurance (per year)", min: 0, max: 5000, step: 10, fmt: fmtMoney, section: "advanced", group: "yearly", hint: "Insurance the owner pays. It rises each year with cost inflation." },
  { key: "annualMaintenancePct", label: "Maintenance (% of value per year)", min: 0, max: 5, step: 0.1, fmt: (v) => fmtPct(v), section: "advanced", group: "yearly", hint: "Repairs and upkeep. A common rule of thumb is 1% of the home's value." },
  { key: "annualMaintenanceAmount", label: "Maintenance (fixed per year)", min: 0, max: 10000, step: 50, fmt: fmtMoney, section: "advanced", group: "yearly", hint: "Upkeep as a fixed amount, such as charges for a shared building." },
  { key: "costInflationRate", label: "Cost inflation", min: 0, max: 10, step: 0.1, scale: 100, fmt: (v) => fmtPct(v), section: "advanced", group: "yearly", hint: "How fast the fixed amounts in this group rise each year. The % amounts follow the home's value instead." },
  { key: "interestDeductionEnabled", label: "Deduct mortgage interest from income tax", type: "checkbox", section: "advanced", group: "mortgage-relief", hint: "On where homeowners can deduct mortgage interest, as in the US and the Netherlands." },
  { key: "marginalTaxRatePct", label: "Your top income-tax rate", min: 0, max: 60, step: 0.01, fmt: (v) => fmtPct(v, 0), section: "advanced", group: "mortgage-relief", hint: "The rate on the top slice of your income. Each 1,000 you deduct saves you this % of it." },
  { key: "levyDeductionCap", label: "Levy is also deductible", min: -1000, max: 50000, step: 1000, fmt: (v) => (v < 0 ? "uncapped" : fmtMoney(v)), section: "advanced", group: "mortgage-relief", hint: "Whether the property levy can be deducted too, and up to what amount per year." },
  { key: "saleCgRegime", label: "When is profit on the home taxed?", type: "select", options: [["exempt_amount", "Tax-free up to a fixed amount"], ["exempt_after_years", "Tax-free after you've owned it N years"], ["fully_exempt", "Always tax-free"]], section: "advanced", group: "home-sale" },
  { key: "saleCgExemptAmount", label: "Tax-free profit", min: 0, max: 1000000, step: 10000, fmt: fmtCompact, section: "advanced", group: "home-sale", hint: "Profit up to this amount is tax-free. The US allows $250,000 for a single person." },
  { key: "saleCgExemptAfterYears", label: "Tax-free after (years owned)", min: 0, max: 30, step: 1, fmt: (v) => `${v} yrs`, section: "advanced", group: "home-sale", hint: "If you sell sooner, the whole profit is taxed." },
  { key: "saleCgRatePct", label: "Tax rate on taxable profit", min: 0, max: 40, step: 0.1, fmt: (v) => fmtPct(v), section: "advanced", group: "home-sale" },
  { key: "portfolioCgRatePct", label: "Tax on investment profit", min: 0, max: 40, step: 0.025, fmt: (v) => fmtPct(v), section: "advanced", group: "investments", hint: "Charged on the profit when the investments are cashed in. It applies to whichever side invests." },
  { key: "portfolioDeemedReturnPct", label: "Wealth tax: assumed return", min: 0, max: 15, step: 0.05, fmt: (v) => fmtPct(v, 2), section: "advanced", group: "investments", hint: "Some countries tax an assumed return instead of real profit, such as the Netherlands (box 3). Leave it at 0 elsewhere." },
  { key: "portfolioDragRatePct", label: "Wealth tax: rate", min: 0, max: 60, step: 0.5, fmt: (v) => fmtPct(v, 1), section: "advanced", group: "investments", hint: "Charged every year on the assumed return, or on your real return if that is lower." },
];
