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

    def test_valid_config_with_tax_params(self):
        """Test that valid configuration with tax parameters is accepted."""
        config = SimulationConfig(
            duration_years=30,
            property_price=500000,
            down_payment_pct=20,
            mortgage_rate_annual=4.5,
            property_appreciation_annual=3.0,
            equity_growth_annual=7.0,
            monthly_rent=2000,
            tax_bracket=24.0,
            enable_mortgage_deduction=True,
            enable_capital_gains_exclusion=True,
            capital_gains_exemption_limit=250000,
            property_tax_rate=1.2,
        )
        assert config.tax_bracket == 24.0
        assert config.enable_mortgage_deduction is True
        assert config.capital_gains_exemption_limit == 250000

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

    def test_invalid_tax_bracket_raises_error(self):
        """Test that invalid tax bracket raises ValueError."""
        with pytest.raises(ValueError, match="tax_bracket must be between 0 and 100"):
            SimulationConfig(
                duration_years=30,
                property_price=500000,
                down_payment_pct=20,
                mortgage_rate_annual=4.5,
                property_appreciation_annual=3.0,
                equity_growth_annual=7.0,
                monthly_rent=2000,
                tax_bracket=150,
            )

    def test_negative_tax_bracket_raises_error(self):
        """Test that negative tax bracket raises ValueError."""
        with pytest.raises(ValueError, match="tax_bracket must be between 0 and 100"):
            SimulationConfig(
                duration_years=30,
                property_price=500000,
                down_payment_pct=20,
                mortgage_rate_annual=4.5,
                property_appreciation_annual=3.0,
                equity_growth_annual=7.0,
                monthly_rent=2000,
                tax_bracket=-10,
            )

    def test_negative_exemption_limit_raises_error(self):
        """Test that negative capital gains exemption limit raises ValueError."""
        with pytest.raises(
            ValueError, match="capital_gains_exemption_limit cannot be negative"
        ):
            SimulationConfig(
                duration_years=30,
                property_price=500000,
                down_payment_pct=20,
                mortgage_rate_annual=4.5,
                property_appreciation_annual=3.0,
                equity_growth_annual=7.0,
                monthly_rent=2000,
                capital_gains_exemption_limit=-100000,
            )

    def test_100_percent_down_payment_config(self):
        """Test configuration with 100% down payment."""
        config = SimulationConfig(
            duration_years=30,
            property_price=500000,
            down_payment_pct=100,  # All cash
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

    def test_tax_columns_exist(self):
        """Test that tax-related columns exist when tax benefits enabled."""
        config = SimulationConfig(
            duration_years=30,
            property_price=500000,
            down_payment_pct=20,
            mortgage_rate_annual=4.5,
            property_appreciation_annual=3.0,
            equity_growth_annual=7.0,
            monthly_rent=2000,
            tax_bracket=24.0,
            enable_mortgage_deduction=True,
        )

        results = calculate_scenarios(config)

        tax_cols = [
            "Annual_Interest",
            "Annual_Property_Tax",
            "Annual_Tax_Savings",
            "Cumulative_Tax_Savings",
            "Net_Buy_Tax_Adjusted",
        ]
        for col in tax_cols:
            assert col in results.data.columns

    def test_very_low_interest_rate(self):
        """Test calculation with very low mortgage interest rate."""
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

        # With near 0% interest, mortgage balance should decrease
        initial_balance = results.data["Mortgage_Balance"].iloc[0]
        final_balance = results.data["Mortgage_Balance"].iloc[-1]
        assert initial_balance > final_balance
        assert final_balance < 1  # Should be paid off

        # With very low interest, minimal tax savings from mortgage deduction
        assert results.total_tax_savings >= 0

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
            property_tax_rate=0.0,  # No property tax for this test
            closing_cost_buyer_pct=0.0,  # No closing costs for this test
            annual_home_insurance=0.0,  # No insurance for this test
            annual_maintenance_pct=0.0,  # No maintenance for this test
        )

        results = calculate_scenarios(config)

        # All mortgage balance should be zero
        assert results.data["Mortgage_Balance"].max() < 1

        # Outflow for buying should just be the down payment (no monthly payments, no tax, no closing costs, no insurance, no maintenance)
        final_outflow = results.data["Outflow_Buy"].iloc[-1]
        assert abs(final_outflow - 500000) < 1  # Should be just the property price

        # Scenario C should be disabled (no mortgage payment)
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


class TestTaxCalculations:
    """Tests for tax benefit calculations."""

    def test_tax_savings_with_deductions(self):
        """Test that tax savings are calculated correctly with deductions."""
        config = SimulationConfig(
            duration_years=10,
            property_price=500000,
            down_payment_pct=20,
            mortgage_rate_annual=4.5,
            property_appreciation_annual=3.0,
            equity_growth_annual=7.0,
            monthly_rent=2000,
            tax_bracket=24.0,
            enable_mortgage_deduction=True,
            property_tax_rate=1.2,
        )

        results = calculate_scenarios(config)

        # Tax savings should be positive
        assert results.total_tax_savings > 0

        # Cumulative tax savings should be non-decreasing
        cumulative = results.data["Cumulative_Tax_Savings"].values
        assert all(cumulative[i] <= cumulative[i + 1] for i in range(len(cumulative) - 1))

    def test_no_tax_savings_when_disabled(self):
        """Test that no tax savings when deductions disabled."""
        config = SimulationConfig(
            duration_years=10,
            property_price=500000,
            down_payment_pct=20,
            mortgage_rate_annual=4.5,
            property_appreciation_annual=3.0,
            equity_growth_annual=7.0,
            monthly_rent=2000,
            tax_bracket=24.0,
            enable_mortgage_deduction=False,
            property_tax_rate=1.2,
        )

        results = calculate_scenarios(config)

        # Tax savings should be zero
        assert results.total_tax_savings == 0
        assert results.data["Annual_Tax_Savings"].sum() == 0

    def test_tax_savings_with_zero_tax_bracket(self):
        """Test that no tax savings with 0% tax bracket."""
        config = SimulationConfig(
            duration_years=10,
            property_price=500000,
            down_payment_pct=20,
            mortgage_rate_annual=4.5,
            property_appreciation_annual=3.0,
            equity_growth_annual=7.0,
            monthly_rent=2000,
            tax_bracket=0.0,
            enable_mortgage_deduction=True,
            property_tax_rate=1.2,
        )

        results = calculate_scenarios(config)

        # Tax savings should be zero with 0% tax rate
        assert results.total_tax_savings == 0

    def test_tax_adjusted_net_value(self):
        """Test that tax-adjusted net value is higher than regular net value."""
        config = SimulationConfig(
            duration_years=10,
            property_price=500000,
            down_payment_pct=20,
            mortgage_rate_annual=4.5,
            property_appreciation_annual=3.0,
            equity_growth_annual=7.0,
            monthly_rent=2000,
            tax_bracket=24.0,
            enable_mortgage_deduction=True,
            property_tax_rate=1.2,
        )

        results = calculate_scenarios(config)

        # Tax-adjusted net value should be higher than regular net value
        assert results.final_net_buy_tax_adjusted > results.final_net_buy

        # The difference should equal total tax savings
        diff = results.final_net_buy_tax_adjusted - results.final_net_buy
        assert abs(diff - results.total_tax_savings) < 1

    def test_annual_interest_calculation(self):
        """Test that annual interest is calculated correctly."""
        config = SimulationConfig(
            duration_years=5,
            property_price=500000,
            down_payment_pct=20,
            mortgage_rate_annual=4.5,
            property_appreciation_annual=3.0,
            equity_growth_annual=7.0,
            monthly_rent=2000,
            tax_bracket=24.0,
            enable_mortgage_deduction=True,
        )

        results = calculate_scenarios(config)

        # Annual interest should be positive for first few years
        annual_interest = results.data["Annual_Interest"].values
        assert annual_interest[12] > 0  # End of year 1
        assert annual_interest[24] > 0  # End of year 2

        # Interest should decrease over time as principal is paid down
        assert annual_interest[24] < annual_interest[12]

    def test_property_tax_calculation(self):
        """Test that property tax is calculated correctly."""
        config = SimulationConfig(
            duration_years=5,
            property_price=500000,
            down_payment_pct=20,
            mortgage_rate_annual=4.5,
            property_appreciation_annual=3.0,
            equity_growth_annual=7.0,
            monthly_rent=2000,
            property_tax_rate=1.2,  # 1.2% annual
        )

        results = calculate_scenarios(config)

        # Annual property tax should be approximately 1.2% of home value
        year1_tax = results.data["Annual_Property_Tax"].iloc[12]
        expected_tax = 500000 * 0.012  # ~$6,000
        assert abs(year1_tax - expected_tax) < 500  # Allow for appreciation

    def test_capital_gains_exclusion(self):
        """Test capital gains tax exclusion calculation."""
        config = SimulationConfig(
            duration_years=10,
            property_price=500000,
            down_payment_pct=20,
            mortgage_rate_annual=4.5,
            property_appreciation_annual=5.0,  # Higher appreciation for gains
            equity_growth_annual=7.0,
            monthly_rent=2000,
            tax_bracket=24.0,
            enable_capital_gains_exclusion=True,
            capital_gains_exemption_limit=250000,
        )

        results = calculate_scenarios(config)

        # Capital gains tax saved should be non-negative
        assert results.capital_gains_tax_saved >= 0

    def test_capital_gains_no_exclusion_when_disabled(self):
        """Test no capital gains exclusion when disabled."""
        config = SimulationConfig(
            duration_years=10,
            property_price=500000,
            down_payment_pct=20,
            mortgage_rate_annual=4.5,
            property_appreciation_annual=5.0,
            equity_growth_annual=7.0,
            monthly_rent=2000,
            tax_bracket=24.0,
            enable_capital_gains_exclusion=False,
            capital_gains_exemption_limit=250000,
        )

        results = calculate_scenarios(config)

        # Capital gains tax saved should be zero when disabled
        assert results.capital_gains_tax_saved == 0

    def test_married_filing_status_higher_exemption(self):
        """Test that married filing status allows higher exemption."""
        config_single = SimulationConfig(
            duration_years=20,
            property_price=800000,
            down_payment_pct=20,
            mortgage_rate_annual=4.5,
            property_appreciation_annual=4.0,
            equity_growth_annual=7.0,
            monthly_rent=3000,
            tax_bracket=24.0,
            enable_capital_gains_exclusion=True,
            capital_gains_exemption_limit=250000,  # Single
        )

        config_married = SimulationConfig(
            duration_years=20,
            property_price=800000,
            down_payment_pct=20,
            mortgage_rate_annual=4.5,
            property_appreciation_annual=4.0,
            equity_growth_annual=7.0,
            monthly_rent=3000,
            tax_bracket=24.0,
            enable_capital_gains_exclusion=True,
            capital_gains_exemption_limit=500000,  # Married
        )

        results_single = calculate_scenarios(config_single)
        results_married = calculate_scenarios(config_married)

        # Married couples should save more in capital gains tax (or equal)
        assert results_married.capital_gains_tax_saved >= results_single.capital_gains_tax_saved


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
            tax_bracket=24.0,
            enable_mortgage_deduction=True,
            property_tax_rate=1.2,
        )

        results = calculate_scenarios(config)

        # Basic sanity checks
        assert results.final_net_buy is not None
        assert results.final_net_rent is not None
        assert (
            results.final_difference == results.final_net_buy - results.final_net_rent
        )

        # Tax benefits should be positive
        assert results.total_tax_savings > 0
        assert results.final_net_buy_tax_adjusted > results.final_net_buy

        # There should be a meaningful difference
        assert abs(results.final_difference) > 0

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

    def test_high_tax_bracket_increases_benefit(self):
        """Test that higher tax bracket increases tax benefits."""
        base_config = {
            "duration_years": 15,
            "property_price": 600000,
            "down_payment_pct": 20,
            "mortgage_rate_annual": 4.5,
            "property_appreciation_annual": 3.0,
            "equity_growth_annual": 7.0,
            "monthly_rent": 2500,
            "enable_mortgage_deduction": True,
            "property_tax_rate": 1.2,
        }

        config_low_tax = SimulationConfig(**base_config, tax_bracket=12.0)
        config_high_tax = SimulationConfig(**base_config, tax_bracket=35.0)

        results_low = calculate_scenarios(config_low_tax)
        results_high = calculate_scenarios(config_high_tax)

        # Higher tax bracket should result in more tax savings
        assert results_high.total_tax_savings > results_low.total_tax_savings
