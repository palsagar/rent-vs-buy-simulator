"""Tests for the shared Net Value engine core (no-tax invariants)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import numpy as np
import numpy_financial as npf

from simulator.engine import _net_value_series
from simulator.models import SimulationConfig


def taxfree_config(**overrides):
    """Config with every tax and ongoing cost zeroed, flat 0% growth."""
    base = dict(
        horizon_years=2,
        property_price=120_000,
        down_payment_pct=25,
        mortgage_rate_annual=6.0,
        mortgage_term_years=30,
        property_appreciation_annual=0.0,
        equity_growth_annual=0.0,
        monthly_rent=500,
        rent_inflation_rate=0.0,
        closing_cost_buyer_pct=2.0,
        closing_cost_seller_pct=5.0,
        property_tax_rate=0.0,
        annual_home_insurance=0.0,
        annual_maintenance_pct=0.0,
        cost_inflation_rate=0.0,
        interest_deduction_enabled=False,
        sale_cg_regime="fully_exempt",
        portfolio_cg_rate_pct=0.0,
    )
    base.update(overrides)
    return SimulationConfig(**base)


def run_flat(config):
    """Run the core with constant monthly rates derived from the config."""
    h = config.horizon_years * 12
    return _net_value_series(
        config,
        np.full(h, config.property_appreciation_annual / 100 / 12),
        np.full(h, config.equity_growth_annual / 100 / 12),
        np.full(h, config.rent_inflation_rate / 12),
    )


class TestTransactionCostInvariant:
    def test_net_buy_at_t0_is_minus_transaction_costs(self):
        # Buying and selling instantly loses exactly buyer + seller costs
        cfg = taxfree_config()
        s = run_flat(cfg)
        expected = -(120_000 * 0.02 + 120_000 * 0.05)  # -8,400
        assert abs(s["net_buy"][0] - expected) < 1e-6

    def test_net_rent_at_t0_is_zero(self):
        cfg = taxfree_config()
        s = run_flat(cfg)
        assert abs(s["net_rent"][0]) < 1e-6


class TestRentInvariant:
    def test_net_rent_equals_minus_rent_paid_under_zero_growth(self):
        # With 0% equity growth and 0% inflation the renter's net value
        # is exactly -(rent paid so far): invested cash comes back at par
        cfg = taxfree_config()
        s = run_flat(cfg)
        months = np.arange(25)
        np.testing.assert_allclose(s["net_rent"], -500.0 * months, atol=1e-6)


class TestMortgageSchedule:
    def test_payment_matches_npf_over_term_not_horizon(self):
        cfg = taxfree_config()
        s = run_flat(cfg)
        pmt = -npf.pmt(0.06 / 12, 360, 90_000)  # term = 360 months
        # Buyer housing cost is only the payment (all other costs zeroed)
        np.testing.assert_allclose(s["housing_cost_buy"][1:], pmt, atol=1e-6)

    def test_balance_closed_form_at_24_months(self):
        cfg = taxfree_config()
        s = run_flat(cfg)
        r, pmt = 0.06 / 12, -npf.pmt(0.06 / 12, 360, 90_000)
        expected = 90_000 * (1 + r) ** 24 - pmt * ((1 + r) ** 24 - 1) / r
        assert abs(s["mortgage_balance"][24] - expected) < 1e-4

    def test_payment_stops_after_payoff_and_buyer_invests(self):
        # 40y horizon on a 15y term: after month 180 the buyer's housing
        # cost drops below rent, so the buy-side portfolio starts growing
        cfg = taxfree_config(horizon_years=40, mortgage_term_years=15)
        s = run_flat(cfg)
        assert abs(s["mortgage_balance"][180]) < 1e-6
        assert np.all(s["housing_cost_buy"][181:] < 1e-9)
        assert s["buy_portfolio"][181] > 0  # rent - 0 invested by buyer
        assert s["buy_portfolio"][-1] > s["buy_portfolio"][181]


class TestCashFlowMatching:
    def test_committed_cash_is_max_of_both_sides(self):
        cfg = taxfree_config()
        s = run_flat(cfg)
        pmt = -npf.pmt(0.06 / 12, 360, 90_000)
        expected_monthly = max(pmt, 500.0)
        assert abs(s["cash_committed"][24] - (32_400 + 24 * expected_monthly)) < 1e-4

    def test_renter_invests_surplus_when_buying_costs_more(self):
        cfg = taxfree_config()
        s = run_flat(cfg)
        pmt = -npf.pmt(0.06 / 12, 360, 90_000)
        surplus = pmt - 500.0
        # 0% growth: portfolio = initial capital + accumulated surplus
        expected = 32_400 + 24 * surplus
        assert abs(s["rent_portfolio"][24] - expected) < 1e-4
