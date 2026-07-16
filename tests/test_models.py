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
