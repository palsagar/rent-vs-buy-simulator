"""Tests for SimulationConfig validation and defaults."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest

from simulator.models import MonteCarloConfig, SimulationConfig


def make_config(**overrides: object) -> SimulationConfig:
    """Minimal valid config; overrides applied on top."""
    base = dict(
        horizon_years=10,
        property_price=500_000,
        down_payment_pct=20,
        mortgage_rate_annual=6.5,
        property_appreciation_annual=3.0,
        equity_growth_annual=7.0,
        monthly_rent=2_400,
    )
    base.update(overrides)
    return SimulationConfig(**base)


class TestConfigValidation:
    def test_valid_config_constructs(self):
        cfg = make_config()
        assert cfg.mortgage_term_years == 30
        assert cfg.sale_cg_regime == "exempt_amount"

    def test_horizon_must_be_positive(self):
        with pytest.raises(ValueError, match="horizon_years"):
            make_config(horizon_years=0)

    def test_term_must_be_positive(self):
        with pytest.raises(ValueError, match="mortgage_term_years"):
            make_config(mortgage_term_years=0)

    def test_down_payment_range(self):
        with pytest.raises(ValueError, match="down_payment_pct"):
            make_config(down_payment_pct=4)
        make_config(down_payment_pct=100)  # all-cash allowed

    def test_invalid_regime_rejected(self):
        with pytest.raises(ValueError, match="sale_cg_regime"):
            make_config(sale_cg_regime="whatever")

    def test_negative_cap_rejected_but_none_allowed(self):
        with pytest.raises(ValueError, match="levy_deduction_cap"):
            make_config(levy_deduction_cap=-1)
        assert make_config(levy_deduction_cap=None).levy_deduction_cap is None

    def test_cg_rates_are_percentages(self):
        with pytest.raises(ValueError, match="portfolio_cg_rate_pct"):
            make_config(portfolio_cg_rate_pct=-5)
        with pytest.raises(ValueError, match="sale_cg_rate_pct"):
            make_config(sale_cg_rate_pct=101)


class TestMonteCarloDefaults:
    def test_recalibrated_defaults(self):
        mc = MonteCarloConfig()
        assert mc.equity_growth_std == 15.0
        assert mc.property_appreciation_std == 8.0
        assert mc.rent_inflation_std == 1.5
        assert mc.appreciation_equity_correlation == 0.3
        assert mc.n_simulations == 500


class TestMultiRegionPrimitiveValidation:
    def test_new_fields_default_to_inert_values(self):
        config = make_config()
        assert config.annual_property_levy == 0.0
        assert config.levy_paid_by_occupier is False
        assert config.annual_maintenance_amount == 0.0
        assert config.closing_cost_buyer_amount == 0.0
        assert config.portfolio_deemed_return_pct == 0.0
        assert config.portfolio_drag_rate_pct == 0.0

    def test_negative_annual_property_levy_rejected(self):
        with pytest.raises(ValueError, match="annual_property_levy"):
            make_config(annual_property_levy=-1.0)

    def test_annual_property_levy_upper_bound(self):
        with pytest.raises(ValueError, match="annual_property_levy"):
            make_config(annual_property_levy=100_001.0)

    def test_negative_annual_maintenance_amount_rejected(self):
        with pytest.raises(ValueError, match="annual_maintenance_amount"):
            make_config(annual_maintenance_amount=-1.0)

    def test_closing_cost_buyer_amount_permits_negative(self):
        # The UK SDLT nil-rate band gives the buyer cost line a negative
        # intercept (-6,900). A >= 0 check would make the UK bundle
        # unconstructible -- see docs/multi-region-spec.md P4.
        config = make_config(closing_cost_buyer_amount=-6900.0)
        assert config.closing_cost_buyer_amount == -6900.0

    def test_closing_cost_buyer_amount_bounded_both_sides(self):
        with pytest.raises(ValueError, match="closing_cost_buyer_amount"):
            make_config(closing_cost_buyer_amount=-100_001.0)
        with pytest.raises(ValueError, match="closing_cost_buyer_amount"):
            make_config(closing_cost_buyer_amount=100_001.0)

    def test_portfolio_deemed_return_pct_bounded(self):
        with pytest.raises(ValueError, match="portfolio_deemed_return_pct"):
            make_config(portfolio_deemed_return_pct=-0.1)
        with pytest.raises(ValueError, match="portfolio_deemed_return_pct"):
            make_config(portfolio_deemed_return_pct=100.1)

    def test_portfolio_drag_rate_pct_bounded(self):
        with pytest.raises(ValueError, match="portfolio_drag_rate_pct"):
            make_config(portfolio_drag_rate_pct=-0.1)
        with pytest.raises(ValueError, match="portfolio_drag_rate_pct"):
            make_config(portfolio_drag_rate_pct=100.1)

    def test_netherlands_operands_are_constructible(self):
        config = make_config(
            portfolio_deemed_return_pct=6.0, portfolio_drag_rate_pct=36.0
        )
        assert config.portfolio_deemed_return_pct == 6.0
        assert config.portfolio_drag_rate_pct == 36.0
