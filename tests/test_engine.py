"""Unit tests for the simulation engine.

Tests edge cases and validates calculation accuracy.
"""

import sys
from pathlib import Path

# Add src to path to import our modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import numpy as np
import pytest

from simulator.engine import _find_breakeven, calculate_scenarios
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

    def test_invalid_down_payment_pct_raises_error(self):
        """Test that invalid down payment percentage raises ValueError."""
        with pytest.raises(
            ValueError, match="down_payment_pct must be between 0 and 100"
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

        # Check that results object is returned
        assert isinstance(results, SimulationResults)

        # Check that DataFrame has correct shape
        assert len(results.data) == 30 * 12 + 1  # Monthly + initial

        # Check that all required columns exist
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

        # Check that home value appreciates
        initial_home = results.data["Home_Value"].iloc[0]
        final_home = results.data["Home_Value"].iloc[-1]
        assert final_home > initial_home

        # Check that equity value grows
        initial_equity = results.data["Equity_Value"].iloc[0]
        final_equity = results.data["Equity_Value"].iloc[-1]
        assert final_equity > initial_equity

    def test_zero_interest_rate(self):
        """Test calculation with 0% mortgage interest rate."""
        config = SimulationConfig(
            duration_years=30,
            property_price=500000,
            down_payment_pct=20,
            mortgage_rate_annual=0.0,  # Zero interest
            property_appreciation_annual=3.0,
            equity_growth_annual=7.0,
            monthly_rent=2000,
        )

        results = calculate_scenarios(config)

        # Should still work without errors
        assert results.data is not None
        assert len(results.data) == 30 * 12 + 1

        # With 0% interest, mortgage balance should decrease linearly
        initial_balance = results.data["Mortgage_Balance"].iloc[0]
        final_balance = results.data["Mortgage_Balance"].iloc[-1]
        assert initial_balance > final_balance
        assert final_balance < 1  # Should be paid off

    def test_zero_appreciation(self):
        """Test calculation with 0% property appreciation."""
        config = SimulationConfig(
            duration_years=30,
            property_price=500000,
            down_payment_pct=20,
            mortgage_rate_annual=4.5,
            property_appreciation_annual=0.0,  # Zero appreciation
            equity_growth_annual=7.0,
            monthly_rent=2000,
        )

        results = calculate_scenarios(config)

        # Home value should remain constant
        initial_home = results.data["Home_Value"].iloc[0]
        final_home = results.data["Home_Value"].iloc[-1]
        assert abs(final_home - initial_home) < 1  # Should be very close

    def test_100_percent_down_payment(self):
        """Test calculation with 100% down payment (no mortgage)."""
        config = SimulationConfig(
            duration_years=30,
            property_price=500000,
            down_payment_pct=100,  # Pay cash
            mortgage_rate_annual=4.5,
            property_appreciation_annual=3.0,
            equity_growth_annual=7.0,
            monthly_rent=2000,
        )

        results = calculate_scenarios(config)

        # All mortgage balance should be zero
        assert results.data["Mortgage_Balance"].max() < 1

        # Outflow for buying should just be the down payment (no monthly payments)
        final_outflow = results.data["Outflow_Buy"].iloc[-1]
        assert abs(final_outflow - 500000) < 1  # Should be just the property price

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

        # Check correct number of data points
        assert len(results.data) == 10 * 12 + 1

        # Check that final year is 10
        assert results.data["Year"].iloc[-1] == 10.0

    def test_outflows_are_positive(self):
        """Test that all outflows are positive (money leaving pocket)."""
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

        # All outflows should be non-negative
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

        # Mortgage balance should be monotonically decreasing
        balances = results.data["Mortgage_Balance"].values
        assert all(balances[i] >= balances[i + 1] for i in range(len(balances) - 1))

        # Should be nearly zero at the end
        assert balances[-1] < 1


class TestBreakeven:
    """Tests for breakeven calculation."""

    def test_breakeven_with_crossover(self):
        """Test breakeven calculation when lines cross."""
        years = np.array([0, 1, 2, 3, 4, 5])
        net_buy = np.array([-100, -50, 0, 50, 100, 150])
        net_rent = np.array([0, 25, 50, 75, 100, 125])

        breakeven = _find_breakeven(years, net_buy, net_rent)

        # Should find a crossover point
        assert breakeven is not None
        assert 0 < breakeven < 5

    def test_breakeven_no_crossover(self):
        """Test breakeven when lines never cross."""
        years = np.array([0, 1, 2, 3, 4, 5])
        net_buy = np.array([0, 10, 20, 30, 40, 50])
        net_rent = np.array([0, 5, 10, 15, 20, 25])

        breakeven = _find_breakeven(years, net_buy, net_rent)

        # Should return None (no crossover)
        assert breakeven is None

    def test_breakeven_exact_match(self):
        """Test breakeven when lines cross at an exact point."""
        years = np.array([0, 1, 2, 3, 4, 5])
        net_buy = np.array([0, 10, 20, 30, 40, 50])
        net_rent = np.array([0, 5, 20, 35, 50, 65])  # Crosses exactly at year 2

        breakeven = _find_breakeven(years, net_buy, net_rent)

        # Should find the crossover
        assert breakeven is not None
        assert abs(breakeven - 2.0) < 0.1  # Should be close to 2


class TestIntegration:
    """Integration tests for full workflow."""

    def test_typical_scenario(self):
        """Test a typical real-world scenario."""
        # Typical scenario: $500k house, 20% down, 30 years
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

        # Basic sanity checks
        assert results.final_net_buy is not None
        assert results.final_net_rent is not None
        assert (
            results.final_difference == results.final_net_buy - results.final_net_rent
        )

        # In typical scenarios with 7% equity returns vs 3% property appreciation,
        # renting usually wins due to higher returns on invested capital
        # (though this can vary based on specific parameters)
        assert (
            abs(results.final_difference) > 0
        )  # There should be a meaningful difference

    def test_high_appreciation_scenario(self):
        """Test scenario where property appreciates faster than stocks."""
        config = SimulationConfig(
            duration_years=30,
            property_price=500000,
            down_payment_pct=20,
            mortgage_rate_annual=4.5,
            property_appreciation_annual=10.0,  # Very high appreciation
            equity_growth_annual=7.0,
            monthly_rent=2000,
        )

        results = calculate_scenarios(config)

        # With very high property appreciation, buying should win
        assert results.final_net_buy > results.final_net_rent
        assert results.final_difference > 0
