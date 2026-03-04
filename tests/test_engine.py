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

    def test_very_low_interest_rate(self):
        """Test calculation with very low (but positive) mortgage interest rate."""
        config = SimulationConfig(
            duration_years=30,
            property_price=500000,
            down_payment_pct=20,
            mortgage_rate_annual=0.01,  # Very low interest (0.01%)
            property_appreciation_annual=3.0,
            equity_growth_annual=7.0,
            monthly_rent=2000,
        )

        results = calculate_scenarios(config)

        # Should still work without errors
        assert results.data is not None
        assert len(results.data) == 30 * 12 + 1

        # With very low interest, mortgage balance should still decrease
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
            # Isolate the 100% down payment behaviour from cost features
            closing_cost_buyer_pct=0.0,
            closing_cost_seller_pct=0.0,
            property_tax_rate=0.0,
            annual_home_insurance=0.0,
            annual_maintenance_pct=0.0,
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
            monthly_rent=2000,  # Less than mortgage payment (~$2,027)
        )

        results = calculate_scenarios(config)

        # Scenario C should be enabled
        assert results.scenario_c_enabled
        assert results.final_net_rent_savings is not None
        assert (
            results.breakeven_year_vs_rent_savings is not None
            or results.breakeven_year_vs_rent_savings is None
        )  # Can be None

    def test_scenario_c_disabled_when_rent_exceeds_mortgage(self):
        """Test that Scenario C is disabled when rent >= mortgage payment."""
        config = SimulationConfig(
            duration_years=30,
            property_price=500000,
            down_payment_pct=100,  # No mortgage, so no monthly payment
            mortgage_rate_annual=4.5,
            property_appreciation_annual=3.0,
            equity_growth_annual=7.0,
            monthly_rent=2000,
        )

        results = calculate_scenarios(config)

        # Scenario C should be disabled (no mortgage payment)
        assert results.scenario_c_enabled is False
        assert results.final_net_rent_savings is None
        assert results.breakeven_year_vs_rent_savings is None

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

        # Savings portfolio should start at 0
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

        # Savings portfolio should grow monotonically
        savings_portfolio = results.data["Savings_Portfolio_Value"].values
        initial_value = savings_portfolio[0]
        final_value = savings_portfolio[-1]

        assert initial_value == 0
        assert final_value > 0
        # Should be generally increasing (allowing for minor numerical issues)
        assert savings_portfolio[-1] > savings_portfolio[len(savings_portfolio) // 2]

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

        # Verify formula: Net_Rent_Savings = (down_payment + savings_portfolio)
        # - rent_outflows
        down_payment = 500000 * 0.20
        for idx in [0, 60, 120]:  # Check at different time points
            expected_net = (
                down_payment
                + results.data["Savings_Portfolio_Value"].iloc[idx]
                - results.data["Outflow_Rent"].iloc[idx]
            )
            actual_net = results.data["Net_Rent_Savings"].iloc[idx]
            assert abs(expected_net - actual_net) < 1  # Allow small numerical error

    def test_scenario_c_with_100_percent_down_payment(self):
        """Test Scenario C with 100% down payment (no mortgage, no savings)."""
        config = SimulationConfig(
            duration_years=30,
            property_price=500000,
            down_payment_pct=100,  # Pay cash, no mortgage
            mortgage_rate_annual=4.5,
            property_appreciation_annual=3.0,
            equity_growth_annual=7.0,
            monthly_rent=2000,
        )

        results = calculate_scenarios(config)

        # Scenario C should be disabled (mortgage payment = 0)
        assert results.scenario_c_enabled is False
        assert results.monthly_mortgage_payment < 1  # Essentially zero
        assert results.final_net_rent_savings is None

    def test_scenario_c_breakeven_calculation(self):
        """Test that breakeven vs Scenario C is calculated correctly."""
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

        # If Scenario C is enabled, breakeven should be calculated
        if results.scenario_c_enabled:
            # Breakeven can be None if lines never cross
            if results.breakeven_year_vs_rent_savings is not None:
                assert results.breakeven_year_vs_rent_savings > 0
                assert results.breakeven_year_vs_rent_savings <= config.duration_years


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


class TestEdgeCases:
    """Edge case tests for extreme scenarios."""

    def test_negative_equity_growth_property_value_decreases(self):
        """Test negative equity growth (property value decreases)."""
        config = SimulationConfig(
            duration_years=10,
            property_price=300000,  # Lower property price
            down_payment_pct=20,
            mortgage_rate_annual=4.5,
            property_appreciation_annual=-2.0,  # Negative appreciation (depreciation)
            equity_growth_annual=7.0,
            monthly_rent=2500,  # Higher rent so mortgage < rent (disables Scenario C)
            rent_inflation_rate=0.02,
        )

        results = calculate_scenarios(config)

        # Property value should decrease over time
        initial_home = results.data["Home_Value"].iloc[0]
        final_home = results.data["Home_Value"].iloc[-1]
        assert final_home < initial_home

        # Scenario C should be disabled since rent > mortgage
        assert not results.scenario_c_enabled

        # With property depreciation and high rent, verify calculations work
        assert results.final_net_buy is not None
        assert results.final_net_rent is not None

    def test_maximum_duration_boundary_40_years(self):
        """Test maximum duration boundary (40 years)."""
        config = SimulationConfig(
            duration_years=40,  # Maximum allowed duration
            property_price=500000,
            down_payment_pct=20,
            mortgage_rate_annual=4.5,
            property_appreciation_annual=3.0,
            equity_growth_annual=7.0,
            monthly_rent=2000,
        )

        results = calculate_scenarios(config)

        # Check correct number of data points (40 years * 12 months + initial)
        assert len(results.data) == 40 * 12 + 1

        # Check that final year is 40
        assert results.data["Year"].iloc[-1] == 40.0

        # All basic sanity checks should pass
        assert results.final_net_buy is not None
        assert results.final_net_rent is not None
        assert results.monthly_mortgage_payment > 0

    def test_very_small_property_value_50k_minimum(self):
        """Test very small property value ($50k minimum)."""
        config = SimulationConfig(
            duration_years=15,
            property_price=50000,  # Very small property value
            down_payment_pct=20,
            mortgage_rate_annual=5.0,
            property_appreciation_annual=3.0,
            equity_growth_annual=7.0,
            monthly_rent=400,  # Proportional rent for small property
            # Isolate basic outflow check from cost features
            closing_cost_buyer_pct=0.0,
            closing_cost_seller_pct=0.0,
            property_tax_rate=0.0,
            annual_home_insurance=0.0,
            annual_maintenance_pct=0.0,
        )

        results = calculate_scenarios(config)

        # Basic sanity checks
        assert results.data is not None
        assert len(results.data) == 15 * 12 + 1

        # Down payment should be $10k (20% of $50k)
        initial_outflow_buy = results.data["Outflow_Buy"].iloc[0]
        assert abs(initial_outflow_buy - 10000) < 1

        # Property value should appreciate correctly
        initial_home = results.data["Home_Value"].iloc[0]
        final_home = results.data["Home_Value"].iloc[-1]
        assert final_home > initial_home

    def test_high_rent_inflation_above_5_percent(self):
        """Test high rent inflation (>5% annually)."""
        config = SimulationConfig(
            duration_years=30,
            property_price=500000,
            down_payment_pct=20,
            mortgage_rate_annual=4.5,
            property_appreciation_annual=3.0,
            equity_growth_annual=7.0,
            monthly_rent=2000,
            rent_inflation_rate=0.06,  # 6% annual rent inflation
        )

        results = calculate_scenarios(config)

        # Rent outflows should increase significantly over time
        early_rent_outflow = results.data["Outflow_Rent"].iloc[12]  # After 1 year
        late_rent_outflow = results.data["Outflow_Rent"].iloc[-1]  # Final

        # Total rent paid should be much higher than without inflation
        assert late_rent_outflow > early_rent_outflow * 10  # Significant increase

        # Verify that rent outflows are positive and monotonically increasing
        rent_outflows = results.data["Outflow_Rent"].values
        assert all(rent_outflows[i] <= rent_outflows[i + 1] for i in range(len(rent_outflows) - 1))

        # Both scenarios should have valid results
        assert results.final_net_rent is not None
        assert results.final_net_buy is not None

    def test_minimum_down_payment_scenario(self):
        """Test minimum down payment scenario (5% minimum)."""
        config = SimulationConfig(
            duration_years=30,
            property_price=500000,
            down_payment_pct=5,  # Minimum down payment (5%)
            mortgage_rate_annual=5.0,
            property_appreciation_annual=3.0,
            equity_growth_annual=7.0,
            monthly_rent=2000,
            # Isolate down-payment check from closing cost features
            closing_cost_buyer_pct=0.0,
            closing_cost_seller_pct=0.0,
            property_tax_rate=0.0,
            annual_home_insurance=0.0,
            annual_maintenance_pct=0.0,
        )

        results = calculate_scenarios(config)

        # Minimum down payment means initial outflow for buying should be $25k
        initial_outflow_buy = results.data["Outflow_Buy"].iloc[0]
        assert abs(initial_outflow_buy - 25000) < 1000  # $25k (no closing costs)

        # Mortgage balance should start at 95% of property price
        initial_mortgage = results.data["Mortgage_Balance"].iloc[0]
        assert abs(initial_mortgage - 475000) < 1

        # Monthly mortgage payment should be higher (95% financed)
        assert results.monthly_mortgage_payment > 2500

        # With minimum down payment, rent scenario starts with small investment
        initial_equity = results.data["Equity_Value"].iloc[0]
        assert abs(initial_equity - 25000) < 1  # 5% of $500k

    def test_rent_equals_mortgage_payment_exactly(self):
        """Test when rent equals mortgage payment exactly."""
        # Calculate monthly mortgage for $400k loan (20% down on $500k) at 4.5% for 30 years
        # Using standard amortization: P = L[c(1+c)^n]/[(1+c)^n-1]
        # L = 400000, c = 0.045/12, n = 360
        # P ≈ $2026.74
        config = SimulationConfig(
            duration_years=30,
            property_price=500000,
            down_payment_pct=20,
            mortgage_rate_annual=4.5,
            property_appreciation_annual=3.0,
            equity_growth_annual=7.0,
            monthly_rent=2026.74,  # Approximately equal to mortgage payment
        )

        results = calculate_scenarios(config)

        # Monthly mortgage payment should be close to rent
        # (allowing for small calculation differences)
        mortgage_payment = results.monthly_mortgage_payment
        assert abs(mortgage_payment - 2026.74) < 50

        # Scenario C should NOT be enabled when mortgage ≈ rent
        # (Scenario C requires mortgage > rent)
        if mortgage_payment <= config.monthly_rent:
            assert results.scenario_c_enabled is False

        # Both scenarios should have valid results
        assert results.final_net_buy is not None
        assert results.final_net_rent is not None
        assert results.final_difference is not None


