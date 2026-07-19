"""Phase-1 no-regression gate: the US preset must not move.

Every value here was captured by running ``calculate_scenarios`` on the
US region bundle's defaults at commit f585e98, BEFORE any multi-region
engine primitive existed (docs/multi-region-spec.md 7.2). A failure here
means a "default-inert" primitive is not inert. Never regenerate these
numbers to make a test pass -- find the primitive that leaked instead.
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
    "final_net_buy": -190046.1963301368,
    "final_net_rent": -191294.19028574793,
    "final_difference": 1247.9939556111349,
    "breakeven_year": 9.985013469190408,
    "monthly_mortgage_payment": 2528.2720939718615,
    "monthly_cost_buy_year1": 3558.802383151073,
    "monthly_cost_rent_year1": 2433.2765530805855,
    "total_closing_costs_buyer": 15000.0,
    "total_closing_costs_seller": 40480.60641572473,
    "total_property_tax_paid": 69870.70943816642,
    "total_insurance_paid": 13617.194024549852,
    "total_maintenance_paid": 58225.591198472015,
    "total_mortgage_interest_paid": 242497.15672867812,
    "total_tax_savings": 74968.2878800427,
}

# The 8 tornado bars, in rank order, captured at the same commit. T9
# changes how the levy delta is computed; these pin that the US chart
# does not move. _compute_sensitivity orders by descending impact
# range, so a reordering is itself a regression.
TORNADO_NAMES = [
    "Equity Growth",
    "Property Appreciation",
    "Monthly Rent",
    "Property Price",
    "Mortgage Rate",
    "Property Tax Rate",
    "Rent Inflation",
    "Down Payment %",
]
TORNADO_LOW = [
    245518.11238156457,
    -302415.7909909935,
    -93421.86072197475,
    88181.87658442234,
    43093.40687027981,
    33706.69579412212,
    -29181.80117805692,
    4054.6262869769125,
]
TORNADO_HIGH = [
    -890777.8509134441,
    579807.9025580233,
    95917.84863319725,
    -85685.88867319992,
    -41503.53846349695,
    -31976.807946117828,
    34725.09155147744,
    -1558.6383757545846,
]
TORNADO_BASE = 1247.9939556111349


class TestUsPresetUnchanged:
    def test_all_summary_fields_match_goldens(self):
        results = calculate_scenarios(SimulationConfig(**US_PRESET))
        for name, expected in GOLDENS.items():
            actual = getattr(results, name)
            assert abs(actual - expected) < 1e-6, (
                f"{name}: got {actual!r}, golden {expected!r}"
            )

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
    base of 1.2, so these hold bit-for-bit (plan ambiguity A7)."""

    def test_names_and_order(self):
        names, _, _, _ = _compute_sensitivity(SimulationConfig(**US_PRESET))
        assert names == TORNADO_NAMES

    def test_values_match_goldens_exactly(self):
        _, low, high, base = _compute_sensitivity(SimulationConfig(**US_PRESET))
        assert list(low) == TORNADO_LOW
        assert list(high) == TORNADO_HIGH
        assert base == TORNADO_BASE
