"""Phase-1 no-regression gate: the US preset must not move.

Every value here was captured by running ``calculate_scenarios`` on the
US region bundle's defaults at commit f585e98, BEFORE any multi-region
engine primitive existed (docs/multi-region-spec.md 7.2). A failure here
means a "default-inert" primitive is not inert. Never regenerate these
numbers to make a test pass -- find the primitive that leaked instead.

The GOLDENS block below is engine output. It was regenerated once,
deliberately, for ADR-0011: yearly growth rates now compound as stated
instead of as annual/12. That is an engine convention, not a primitive.
Diffed by name, three fields do not depend on any growth rate and are
bit-identical before and after -- monthly_mortgage_payment,
total_closing_costs_buyer, total_mortgage_interest_paid -- because the
mortgage rate stays a nominal rate split over twelve months;
test_fields_untouched_by_the_rate_convention pins them at their old
values. Every other field moved, because the home value, the rent, the
cost index and the portfolios all compound at the stated yearly rate.

The TORNADO_* constants are perturbation output, and have been
regenerated three times, deliberately: twice when the perturbation rule
itself was redefined and once for ADR-0011; see the note above them for
the standard that applies.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from simulator.engine import calculate_scenarios
from simulator.models import SimulationConfig
from simulator.monte_carlo import _compute_sensitivity

# Mirrors state.js DEFAULT_CONFIG, which is the US bundle applied to the
# app's shipped defaults. Every field omitted here takes the same value
# from SimulationConfig's own defaults.
US_PRESET = dict(
    horizon_years=10,
    property_price=500000,
    down_payment_pct=20,
    mortgage_rate_annual=6.5,
    property_appreciation_annual=3.0,
    equity_growth_annual=7.0,
    monthly_rent=2400,
)

GOLDENS = {
    "final_net_buy": -192348.12944373256,
    "final_net_rent": -196408.41741621884,
    "final_difference": 4060.287972486287,
    "breakeven_year": 8.999823497118234,
    "monthly_mortgage_payment": 2528.2720939718615,
    "monthly_cost_buy_year1": 3558.616384594503,
    "monthly_cost_rent_year1": 2432.8238813857533,
    "total_closing_costs_buyer": 15000.0,
    "total_closing_costs_seller": 40317.49138032407,
    "total_property_tax_paid": 69723.9984056755,
    "total_insurance_paid": 13597.417828637674,
    "total_maintenance_paid": 58103.33200472958,
    "total_mortgage_interest_paid": 242497.15672867812,
    "total_tax_savings": 74933.07723224488,
}

# The three fields no growth rate reaches, at their values from before
# ADR-0011. The mortgage payment, the buyer's closing costs and the
# interest all follow from the price, the down payment and the nominal
# mortgage rate alone.
RATE_INDEPENDENT_GOLDENS = {
    "monthly_mortgage_payment": 2528.2720939718615,
    "total_closing_costs_buyer": 15000.0,
    "total_mortgage_interest_paid": 242497.15672867812,
}

# The 8 tornado bars, in rank order. _compute_sensitivity orders by
# descending impact range, so a reordering is itself a regression.
#
# REGENERATED deliberately, when the tornado's delta for the three
# stochastic drivers became the standard error of the long-run average
# (std / sqrt(horizon)) instead of the raw annual std. The annual figure
# is what run_monte_carlo needs for year-to-year draws; the tornado holds
# its shift for the whole horizon, so it needs the uncertainty of the
# AVERAGE. Diffed by NAME, since the rank order moves:
#
#   - the three stochastic bars move on BOTH sides, because the delta
#     itself shrank: Equity Growth, Property Appreciation, Rent Inflation
#   - the five fixed-step bars are bit-identical on both sides: Monthly
#     Rent, Property Price, Mortgage Rate, Property Levy (% of value),
#     Down Payment % -- their deltas are absolute steps, not standard
#     deviations, so sqrt(horizon) does not apply
#   - the summary GOLDENS block above is untouched
#
# Do not regenerate these to make a failure pass. Diff by NAME and
# justify every value that moves: an engine change should move nothing
# here, and a deliberate perturbation change should move exactly the
# fields it redefines.
#
# REGENERATED again, deliberately, when home price and monthly rent moved
# from fixed steps (100k, 500) to 20% of their own value. At the US preset
# the price step is still exactly 100k, so only Monthly Rent moves (its
# step goes from 500 to 480), and the rank order holds.
#
# REGENERATED a third time, deliberately, for ADR-0011 (yearly growth
# rates compound as stated). Every bar is a re-run of the engine, so all
# eight move on both sides, and the base moves with the verdict above.
# The tested INPUTS are bit-identical: no perturbation rule changed. The
# rank order moves once: Property Appreciation now ranks above Equity
# Growth. Equity's higher side tests 11.74%, which annual/12 compounded
# to 12.40% a year, so its bar was the most inflated of the eight; it
# narrows from 271.5k to 247.6k while Property Appreciation's narrows
# from 268.8k to 261.1k.
#
# Moved once more, deliberately, for ADR-0012 (the taxed home-sale profit
# is net of buying and selling costs): exactly ONE value, Property
# Appreciation's higher side, 142,634.58 -> 152,592.99. Its 5.53% test
# grows the home to ~$856k, a profit above the $250k exclusion, so the
# sale is taxed; netting out the $15,000 paid to buy and the ~$51,389
# paid to sell lowers that tax by 15% of $66,389 = $9,958. Every other
# bar, the base and the summary GOLDENS stay bit-identical: at the US
# default the profit is under the exclusion either way.
TORNADO_NAMES = [
    "Property Appreciation",
    "Equity Growth",
    "Monthly Rent",
    "Property Price",
    "Mortgage Rate",
    "Property Levy (% of value)",
    "Rent Inflation",
    "Down Payment %",
]
TORNADO_LOW = [
    -118458.07718956331,
    105699.40307721135,
    -85744.64550278307,
    89395.62214526985,
    45461.37478180759,
    36065.72384167119,
    -5546.580837710353,
    6236.65391019854,
]
TORNADO_HIGH = [
    152592.98506998102,
    -141912.00960823428,
    93865.22144775564,
    -81275.04620029719,
    -38227.09712143912,
    -28675.280619678786,
    13912.243867753597,
    1883.9220347741502,
]
TORNADO_BASE = 4060.287972486287


class TestUsPresetUnchanged:
    def test_all_summary_fields_match_goldens(self):
        results = calculate_scenarios(SimulationConfig(**US_PRESET))
        for name, expected in GOLDENS.items():
            actual = getattr(results, name)
            assert abs(actual - expected) < 1e-6, (
                f"{name}: got {actual!r}, golden {expected!r}"
            )

    def test_fields_untouched_by_the_rate_convention(self):
        # ADR-0011 changed how yearly GROWTH rates become monthly ones and
        # deliberately left the mortgage rate a nominal rate split over
        # twelve months. These three fields depend on no growth rate, so
        # they must still equal their pre-ADR-0011 values bit for bit;
        # exact equality is the assertion, as no arithmetic changed.
        results = calculate_scenarios(SimulationConfig(**US_PRESET))
        for name, expected in RATE_INDEPENDENT_GOLDENS.items():
            assert getattr(results, name) == expected, name

    def test_us_config_uses_only_default_optional_fields(self):
        # Guards the goldens' provenance: if a future default changes,
        # this fails loudly instead of the goldens drifting silently.
        config = SimulationConfig(**US_PRESET)
        assert config.mortgage_term_years == 30
        assert config.closing_cost_buyer_pct == 3.0
        assert config.property_tax_rate == 1.2
        assert config.annual_maintenance_pct == 1.0
        assert config.levy_deduction_cap == 10000.0
        assert config.sale_cg_regime == "exempt_amount"


class TestUsTornadoUnchanged:
    """Pins the 8 tornado bars so T9's proportional-delta change is
    provably US-inert. The proportional delta is exactly 0.5 at the US
    base of 1.2, so these hold bit-for-bit (plan ambiguity A7). The 20%
    price step is exactly 100k at the US price of 500k, so Property Price
    holds too; only Monthly Rent was regenerated."""

    def test_names_and_order(self):
        sens = _compute_sensitivity(SimulationConfig(**US_PRESET))
        names = sens.params
        assert names == TORNADO_NAMES

    def test_values_match_goldens_exactly(self):
        sens = _compute_sensitivity(SimulationConfig(**US_PRESET))
        low = sens.low
        high = sens.high
        base = sens.base
        assert list(low) == TORNADO_LOW
        assert list(high) == TORNADO_HIGH
        assert base == TORNADO_BASE
