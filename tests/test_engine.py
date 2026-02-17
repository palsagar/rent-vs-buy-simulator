"""Unit tests for the simulation engine.

Tests edge cases and validates calculation accuracy.
"""

import sys
from pathlib import Path

# Add src to path to import our modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import numpy as np
import pytest

from simulator.engine import (
    _find_breakeven,
    calculate_scenarios,
    _is_close_to_zero,
    _is_close,
)
from simulator.models import SimulationConfig, SimulationResults


class TestSimulationConfig:
    """Tests for SimulationConfig validation."""

    def test_valid_config(self):
        """Test that valid configuration is accepted."""
        config = SimulationConfig(
            duration_years=30,
            property_price=500000,
            down_payment_pct=20,
            mortgage_rate_annual=4.5,
            property_appreciation_annual=3.0,
            equity_growth_annual=7.0,
            monthly_rent=2000,
        )
        assert config.duration_years == 30
        assert config.property_price == 500000

    def test_negative_duration_raises_error(self):
        """Test that negative duration raises ValueError."""
        with pytest.raises(ValueError, match="duration_years must be positive"):
            SimulationConfig(
                duration_years=-5,
                property_price=500000,
                down_payment_pct=20,
                mortgage_rate_annual=4.5,
                property_appreciation_annual=3.0,
                equity_growth_annual=7.0,
                monthly_rent=2000,
            )

    def test_zero_duration_raises_error(self):
        """Test that zero duration raises ValueError."""
        with pytest.raises(ValueError, match="duration_years must be positive"):
            SimulationConfig(
                duration_years=0,
                property_price=500000,
                down_payment_pct=20,
                mortgage_rate_annual=4.5,
                property_appreciation_annual=3.0,
                equity_growth_annual=7.0,
                monthly_rent=2000,
            )

    def test_zero_property_price_raises_error(self):
        """Test that zero property price raises ValueError."""
        with pytest.raises(ValueError, match="property_price must be positive"):
            SimulationConfig(
                duration_years=30,
                property_price=0,
                down_payment_pct=20,
                mortgage_rate_annual=4.5,
                property_appreciation_annual=3.0,
                equity_growth_annual=7.0,
                monthly_rent=2000,
            )

    def test_negative_property_price_raises_error(self):
        """Test that negative property price raises ValueError."""
        with pytest.raises(ValueError, match="property_price must be positive"):
            SimulationConfig(
                duration_years=30,
                property_price=-100000,
                down_payment_pct=20,
                mortgage_rate_annual=4.5,
                property_appreciation_annual=3.0,
                equity_growth_annual=7.0,
                monthly_rent=2000,
            )

    def test_invalid_down_payment_pct_too_high_raises_error(self):
        """Test that down payment > 100% raises ValueError."""
        with pytest.raises(
            ValueError, match="down_payment_pct must be between 5 and 100"
        ):
            SimulationConfig(
                duration_years=30,
                property_price=500000,
                down_payment_pct=150,
                mortgage_rate_annual=4.5,
                property_appreciation_annual=3.0,
                equity_growth_annual=7.0,
                monthly_rent=2000,
            )

    def test_invalid_down_payment_pct_too_low_raises_error(self):
        """Test that down payment < 5% raises ValueError."""
        with pytest.raises(
            ValueError, match="down_payment_pct must be between 5 and 100"
        ):
            SimulationConfig(
                duration_years=30,
                property_price=500000,
                down_payment_pct=3,
                mortgage_rate_annual=4.5,
                property_appreciation_annual=3.0,
                equity_growth_annual=7.0,
                monthly_rent=2000,
            )

    def test_zero_down_payment_pct_raises_error(self):
        """Test that 0% down payment raises ValueError."""
        with pytest.raises(
            ValueError, match="down_payment_pct must be between 5 and 100"
        ):
            SimulationConfig(
                duration_years=30,
                property_price=500000,
                down_payment_pct=0,
                mortgage_rate_annual=4.5,
                property_appreciation_annual=3.0,
                equity_growth_annual=7.0,
                monthly_rent=2000,
            )

    def test_zero_mortgage_rate_raises_error(self):
        """Test that 0% mortgage rate raises ValueError."""
        with pytest.raises(ValueError, match="mortgage_rate_annual must be positive"):
            SimulationConfig(
                duration_years=30,
                property_price=500000,
                down_payment_pct=20,
                mortgage_rate_annual=0.0,
                property_appreciation_annual=3.0,
                equity_growth_annual=7.0,
                monthly_rent=2000,
            )

    def test_negative_mortgage_rate_raises_error(self):
        """Test that negative mortgage rate raises ValueError."""
        with pytest.raises(ValueError, match="mortgage_rate_annual must be positive"):
            SimulationConfig(
                duration_years=30,
                property_price=500000,
                down_payment_pct=20,
                mortgage_rate_annual=-1.0,
                property_appreciation_annual=3.0,
                equity_growth_annual=7.0,
                monthly_rent=2000,
            )

    def test_zero_monthly_rent_raises_error(self):
        """Test that zero monthly rent raises ValueError."""
        with pytest.raises(ValueError, match="monthly_rent must be positive"):
            SimulationConfig(
                duration_years=30,
                property_price=500000,
                down_payment_pct=20,
                mortgage_rate_annual=4.5,
                property_appreciation_annual=3.0,
                equity_growth_annual=7.0,
                monthly_rent=0,
            )

    def test_negative_monthly_rent_raises_error(self):
        """Test that negative monthly rent raises ValueError."""
        with pytest.raises(ValueError, match="monthly_rent must be positive"):
            SimulationConfig(
                duration_years=30,
                property_price=500000,
                down_payment_pct=20,
                mortgage_rate_annual=4.5,
                property_appreciation_annual=3.0,
                equity_growth_annual=7.0,
                monthly_rent=-1000,
            )

    def test_rent_inflation_rate_too_high_raises_error(self):
        """Test that rent inflation rate > 1 raises ValueError."""
        with pytest.raises(
            ValueError, match="rent_inflation_rate must be between 0 and 1"
        ):
            SimulationConfig(
                duration_years=30,
                property_price=500000,
                down_payment_pct=20,
                mortgage_rate_annual=4.5,
                property_appreciation_annual=3.0,
                equity_growth_annual=7.0,
                monthly_rent=2000,
                rent_inflation_rate=1.5,
            )

    def test_negative_rent_inflation_rate_raises_error(self):
        """Test that negative rent inflation rate raises ValueError."""
        with pytest.raises(
            ValueError, match="rent_inflation_rate must be between 0 and 1"
        ):
            SimulationConfig(
                duration_years=30,
                property_price=500000,
                down_payment_pct=20,
                mortgage_rate_annual=4.5,
                property_appreciation_annual=3.0,
                equity_growth_annual=7.0,
                monthly_rent=2000,
                rent_inflation_rate=-0.01,
            )

    def test_valid_rent_inflation_rate_boundary(self):
        """Test that boundary rent inflation rates are accepted."""
        config_0 = SimulationConfig(
            duration_years=30,
            property_price=500000,
            down_payment_pct=20,
            mortgage_rate_annual=4.5,
            property_appreciation_annual=3.0,
            equity_growth_annual=7.0,
            monthly_rent=2000,
            rent_inflation_rate=0.0,
        )
        assert config_0.rent_inflation_rate == 0.0

        config_100 = SimulationConfig(
            duration_years=30,
            property_price=500000,
            down_payment_pct=20,
            mortgage_rate_annual=4.5,
            property_appreciation_annual=3.0,
            equity_growth_annual=7.0,
            monthly_rent=2000,
            rent_inflation_rate=1.0,
        )
        assert config_100.rent_inflation_rate == 1.0

    def test_valid_5_percent_down_payment(self):
        """Test that 5% down payment is accepted (minimum)."""
        config = SimulationConfig(
            duration_years=30,
            property_price=500000,
            down_payment_pct=5,
            mortgage_rate_annual=4.5,
            property_appreciation_annual=3.0,
            equity_growth_annual=7.0,
            monthly_rent=2000,
        )
        assert config.down_payment_pct == 5

    def test_valid_100_percent_down_payment(self):
        """Test that 100% down payment is accepted (all cash)."""
        config = SimulationConfig(
            duration_years=30,
            property_price=500000,
            down_payment_pct=100,
            mortgage_rate_annual=4.5,
            property_appreciation_annual=3.0,
            equity_growth_annual=7.0,
            monthly_rent=2000,
        )
        assert config.down_payment_pct == 100


class TestCalculateScenarios:
    """Tests for calculate_scenarios function."""

    def test_basic_calculation(self):
        """Test basic calculation with standard inputs."""
        config = SimulationConfig(
            duration_years=30,
            property_price=500000,
            down_payment_pct=20,
            mortgage_rate_annual=4.5,
            property_appreciation_annual=3.0,
            equity_growth_annual=7.0,
            monthly_rent=2000,
        )

        results = calculate_scenarios(config)
        assert isinstance(results, SimulationResults)
        assert len(results.data) == 30 * 12 + 1

        required_cols = [
            "Month",
            "Year",
            "Home_Value",
            "Equity_Value",
            "Mortgage_Balance",
            "Outflow_Buy",
            "Outflow_Rent",
            "Net_Buy",
            "Net_Rent",
        ]
        for col in required_cols:
            assert col in results.data.columns

        initial_home = results.data["Home_Value"].iloc[0]
        final_home = results.data["Home_Value"].iloc[-1]
        assert final_home > initial_home

        initial_equity = results.data["Equity_Value"].iloc[0]
        final_equity = results.data["Equity_Value"].iloc[-1]
        assert final_equity > initial_equity

    def test_very_small_property_value(self):
        """Test calculation with very small property value."""
        config = SimulationConfig(
            duration_years=30,
            property_price=10000,
            down_payment_pct=20,
            mortgage_rate_annual=4.5,
            property_appreciation_annual=3.0,
            equity_growth_annual=7.0,
            monthly_rent=100,
        )

        results = calculate_scenarios(config)
        assert results.data is not None
        assert len(results.data) == 30 * 12 + 1
        initial_home = results.data["Home_Value"].iloc[0]
        assert abs(initial_home - 10000) < 1

    def test_very_high_property_value(self):
        """Test calculation with very high property value."""
        config = SimulationConfig(
            duration_years=30,
            property_price=10000000,
            down_payment_pct=20,
            mortgage_rate_annual=4.5,
            property_appreciation_annual=3.0,
            equity_growth_annual=7.0,
            monthly_rent=25000,
        )

        results = calculate_scenarios(config)
        assert results.data is not None
        assert len(results.data) == 30 * 12 + 1
        initial_home = results.data["Home_Value"].iloc[0]
        assert abs(initial_home - 10000000) < 1

    def test_very_low_mortgage_rate(self):
        """Test calculation with very low but positive mortgage rate."""
        config = SimulationConfig(
            duration_years=30,
            property_price=500000,
            down_payment_pct=20,
            mortgage_rate_annual=0.01,
            property_appreciation_annual=3.0,
            equity_growth_annual=7.0,
            monthly_rent=2000,
        )

        results = calculate_scenarios(config)
        assert results.data is not None
        final_balance = results.data["Mortgage_Balance"].iloc[-1]
        assert final_balance < 1

    def test_zero_appreciation(self):
        """Test calculation with 0% property appreciation."""
        config = SimulationConfig(
            duration_years=30,
            property_price=500000,
            down_payment_pct=20,
            mortgage_rate_annual=4.5,
            property_appreciation_annual=0.0,
            equity_growth_annual=7.0,
            monthly_rent=2000,
        )

        results = calculate_scenarios(config)
        initial_home = results.data["Home_Value"].iloc[0]
        final_home = results.data["Home_Value"].iloc[-1]
        assert abs(final_home - initial_home) < 1

    def test_100_percent_down_payment(self):
        """Test calculation with 100% down payment (no mortgage)."""
        config = SimulationConfig(
            duration_years=30,
            property_price=500000,
            down_payment_pct=100,
            mortgage_rate_annual=4.5,
            property_appreciation_annual=3.0,
            equity_growth_annual=7.0,
            monthly_rent=2000,
        )

        results = calculate_scenarios(config)
        assert results.data["Mortgage_Balance"].max() < 1
        final_outflow = results.data["Outflow_Buy"].iloc[-1]
        assert abs(final_outflow - 500000) < 1
        assert results.scenario_c_enabled is False

    def test_short_duration(self):
        """Test calculation with short duration (10 years)."""
        config = SimulationConfig(
            duration_years=10,
            property_price=500000,
            down_payment_pct=20,
            mortgage_rate_annual=4.5,
            property_appreciation_annual=3.0,
            equity_growth_annual=7.0,
            monthly_rent=2000,
        )

        results = calculate_scenarios(config)
        assert len(results.data) == 10 * 12 + 1
        assert results.data["Year"].iloc[-1] == 10.0

    def test_outflows_are_positive(self):
        """Test that all outflows are positive."""
        config = SimulationConfig(
            duration_years=30,
            property_price=500000,
            down_payment_pct=20,
            mortgage_rate_annual=4.5,
            property_appreciation_annual=3.0,
            equity_growth_annual=7.0,
            monthly_rent=2000,
        )

        results = calculate_scenarios(config)
        assert (results.data["Outflow_Buy"] >= 0).all()
        assert (results.data["Outflow_Rent"] >= 0).all()

    def test_mortgage_balance_decreases(self):
        """Test that mortgage balance decreases over time."""
        config = SimulationConfig(
            duration_years=30,
            property_price=500000,
            down_payment_pct=20,
            mortgage_rate_annual=4.5,
            property_appreciation_annual=3.0,
            equity_growth_annual=7.0,
            monthly_rent=2000,
        )

        results = calculate_scenarios(config)
        balances = results.data["Mortgage_Balance"].values
        assert all(balances[i] >= balances[i + 1] for i in range(len(balances) - 1))
        assert balances[-1] < 1


class TestEdgeCaseMetrics:
    """Tests for edge case metrics in SimulationResults."""

    def test_negative_equity_months_normal_case(self):
        """Test negative_equity_months in normal scenario."""
        config = SimulationConfig(
            duration_years=30,
            property_price=500000,
            down_payment_pct=20,
            mortgage_rate_annual=4.5,
            property_appreciation_annual=3.0,
            equity_growth_annual=7.0,
            monthly_rent=2000,
        )

        results = calculate_scenarios(config)
        assert results.negative_equity_months == 0
        assert results.min_equity_achieved > 0

    def test_negative_equity_with_depreciation(self):
        """Test negative_equity_months with property depreciation."""
        config = SimulationConfig(
            duration_years=10,
            property_price=500000,
            down_payment_pct=5,
            property_appreciation_annual=-5.0,
            equity_growth_annual=7.0,
            monthly_rent=2000,
            mortgage_rate_annual=4.5,
        )

        results = calculate_scenarios(config)
        assert hasattr(results, "negative_equity_months")
        assert hasattr(results, "min_equity_achieved")

    def test_final_ltv_ratio(self):
        """Test final_ltv_ratio calculation."""
        config = SimulationConfig(
            duration_years=30,
            property_price=500000,
            down_payment_pct=20,
            mortgage_rate_annual=4.5,
            property_appreciation_annual=3.0,
            equity_growth_annual=7.0,
            monthly_rent=2000,
        )

        results = calculate_scenarios(config)
        assert results.final_ltv_ratio >= 0
        assert results.final_ltv_ratio < 0.1

    def test_final_ltv_ratio_100_percent_down(self):
        """Test final_ltv_ratio with 100% down payment."""
        config = SimulationConfig(
            duration_years=30,
            property_price=500000,
            down_payment_pct=100,
            mortgage_rate_annual=4.5,
            property_appreciation_annual=3.0,
            equity_growth_annual=7.0,
            monthly_rent=2000,
        )

        results = calculate_scenarios(config)
        assert results.final_ltv_ratio == 0.0

    def test_max_monthly_payment(self):
        """Test max_monthly_payment calculation."""
        config = SimulationConfig(
            duration_years=30,
            property_price=500000,
            down_payment_pct=20,
            mortgage_rate_annual=4.5,
            property_appreciation_annual=3.0,
            equity_growth_annual=7.0,
            monthly_rent=2000,
        )

        results = calculate_scenarios(config)
        assert results.max_monthly_payment >= results.monthly_mortgage_payment
        assert results.max_monthly_payment > 0


class TestBreakeven:
    """Tests for breakeven calculation."""

    def test_breakeven_with_crossover(self):
        """Test breakeven calculation when lines cross."""
        years = np.array([0, 1, 2, 3, 4, 5])
        net_buy = np.array([-100, -50, 0, 50, 100, 150])
        net_rent = np.array([0, 25, 50, 75, 100, 125])

        breakeven = _find_breakeven(years, net_buy, net_rent)
        assert breakeven is not None
        assert 0 < breakeven < 5

    def test_breakeven_no_crossover(self):
        """Test breakeven when lines never cross."""
        years = np.array([0, 1, 2, 3, 4, 5])
        net_buy = np.array([0, 10, 20, 30, 40, 50])
        net_rent = np.array([0, 5, 10, 15, 20, 25])

        breakeven = _find_breakeven(years, net_buy, net_rent)
        assert breakeven is None

    def test_breakeven_exact_match(self):
        """Test breakeven when lines cross at an exact point."""
        years = np.array([0, 1, 2, 3, 4, 5])
        net_buy = np.array([0, 10, 20, 30, 40, 50])
        net_rent = np.array([0, 5, 20, 35, 50, 65])

        breakeven = _find_breakeven(years, net_buy, net_rent)
        assert breakeven is not None
        assert abs(breakeven - 2.0) < 0.1

    def test_breakeven_floating_point_tolerance(self):
        """Test breakeven handles floating-point values near zero."""
        years = np.array([0, 1, 2, 3, 4, 5])
        net_buy = np.array([1e-10, 10, 20, 30, 40, 50])
        net_rent = np.array([0, 5, 20, 35, 50, 65])

        breakeven = _find_breakeven(years, net_buy, net_rent)
        assert breakeven is None or breakeven >= 0


class TestFloatingPointHelpers:
    """Tests for floating-point comparison helpers."""

    def test_is_close_to_zero_true(self):
        """Test _is_close_to_zero returns True for near-zero values."""
        assert _is_close_to_zero(0.0) is True
        assert _is_close_to_zero(1e-10) is True
        assert _is_close_to_zero(-1e-10) is True

    def test_is_close_to_zero_false(self):
        """Test _is_close_to_zero returns False for non-zero values."""
        assert _is_close_to_zero(1.0) is False
        assert _is_close_to_zero(0.01) is False
        assert _is_close_to_zero(-0.001) is False

    def test_is_close_true(self):
        """Test _is_close returns True for close values."""
        assert _is_close(1.0, 1.0000000001) is True
        assert _is_close(100.0, 100.0000000001) is True

    def test_is_close_false(self):
        """Test _is_close returns False for different values."""
        assert _is_close(1.0, 2.0) is False
        assert _is_close(1.0, 1.01) is False


class TestScenarioC:
    """Tests for Scenario C: Rent & Invest Monthly Savings."""

    def test_scenario_c_enabled_when_mortgage_exceeds_rent(self):
        """Test that Scenario C is enabled when mortgage payment > rent."""
        config = SimulationConfig(
            duration_years=30,
            property_price=500000,
            down_payment_pct=20,
            mortgage_rate_annual=4.5,
            property_appreciation_annual=3.0,
            equity_growth_annual=7.0,
            monthly_rent=2000,
        )

        results = calculate_scenarios(config)
        assert results.scenario_c_enabled
        assert results.final_net_rent_savings is not None

    def test_scenario_c_disabled_when_rent_exceeds_mortgage(self):
        """Test that Scenario C is disabled when rent >= mortgage payment."""
        config = SimulationConfig(
            duration_years=30,
            property_price=500000,
            down_payment_pct=100,
            mortgage_rate_annual=4.5,
            property_appreciation_annual=3.0,
            equity_growth_annual=7.0,
            monthly_rent=2000,
        )

        results = calculate_scenarios(config)
        assert results.scenario_c_enabled is False
        assert results.final_net_rent_savings is None

    def test_savings_portfolio_starts_at_zero(self):
        """Test that savings portfolio starts at zero."""
        config = SimulationConfig(
            duration_years=30,
            property_price=500000,
            down_payment_pct=20,
            mortgage_rate_annual=4.5,
            property_appreciation_annual=3.0,
            equity_growth_annual=7.0,
            monthly_rent=2000,
        )

        results = calculate_scenarios(config)
        assert results.data["Savings_Portfolio_Value"].iloc[0] == 0

    def test_savings_portfolio_grows_over_time(self):
        """Test that savings portfolio increases as savings compound."""
        config = SimulationConfig(
            duration_years=10,
            property_price=500000,
            down_payment_pct=20,
            mortgage_rate_annual=4.5,
            property_appreciation_annual=3.0,
            equity_growth_annual=7.0,
            monthly_rent=2000,
        )

        results = calculate_scenarios(config)
        savings_portfolio = results.data["Savings_Portfolio_Value"].values
        assert savings_portfolio[0] == 0
        assert savings_portfolio[-1] > 0

    def test_scenario_c_net_value_formula(self):
        """Test that Net_Rent_Savings formula is correct."""
        config = SimulationConfig(
            duration_years=10,
            property_price=500000,
            down_payment_pct=20,
            mortgage_rate_annual=4.5,
            property_appreciation_annual=3.0,
            equity_growth_annual=7.0,
            monthly_rent=2000,
        )

        results = calculate_scenarios(config)
        down_payment = 500000 * 0.20
        for idx in [0, 60, 120]:
            expected_net = (
                down_payment
                + results.data["Savings_Portfolio_Value"].iloc[idx]
                - results.data["Outflow_Rent"].iloc[idx]
            )
            actual_net = results.data["Net_Rent_Savings"].iloc[idx]
            assert abs(expected_net - actual_net) < 1


class TestIntegration:
    """Integration tests for full workflow."""

    def test_typical_scenario(self):
        """Test a typical real-world scenario."""
        config = SimulationConfig(
            duration_years=30,
            property_price=500000,
            down_payment_pct=20,
            mortgage_rate_annual=4.5,
            property_appreciation_annual=3.0,
            equity_growth_annual=7.0,
            monthly_rent=2000,
            rent_inflation_rate=0.03,
        )

        results = calculate_scenarios(config)
        assert results.final_net_buy is not None
        assert results.final_net_rent is not None
        assert results.final_difference == results.final_net_buy - results.final_net_rent
        assert abs(results.final_difference) > 0

    def test_high_appreciation_scenario(self):
        """Test scenario where property appreciates faster than stocks."""
        config = SimulationConfig(
            duration_years=30,
            property_price=500000,
            down_payment_pct=20,
            mortgage_rate_annual=4.5,
            property_appreciation_annual=10.0,
            equity_growth_annual=7.0,
            monthly_rent=2000,
        )

        results = calculate_scenarios(config)
        assert results.final_net_buy > results.final_net_rent
        assert results.final_difference > 0
