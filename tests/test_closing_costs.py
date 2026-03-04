"""Tests for closing costs and homeownership expenses."""

import sys
from pathlib import Path

# Add src to path to import our modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


from simulator.engine import calculate_scenarios
from simulator.models import SimulationConfig


class TestClosingCosts:
    """Tests for closing costs and homeownership expenses."""

    def test_buyer_closing_costs_added_to_initial_outflow(self):
        """Test that buyer closing costs are added to initial outflow."""
        config = SimulationConfig(
            duration_years=10,
            property_price=500000,
            down_payment_pct=20,
            mortgage_rate_annual=4.5,
            property_appreciation_annual=3.0,
            equity_growth_annual=7.0,
            monthly_rent=2000,
            closing_cost_buyer_pct=3.0,
            closing_cost_seller_pct=0.0,
            property_tax_rate=0.0,
            annual_home_insurance=0.0,
            annual_maintenance_pct=0.0,
        )

        results = calculate_scenarios(config)

        # Buyer closing costs = 3% of $500k = $15k
        expected_closing_costs = 15000

        # Initial outflow should include down payment + closing costs
        # Down payment = 20% of $500k = $100k
        # Total initial outflow = $115k
        initial_outflow = results.data["Outflow_Buy"].iloc[0]
        assert abs(initial_outflow - 115000) < 100

        # Verify total_closing_costs_buyer is tracked
        assert abs(results.total_closing_costs_buyer - expected_closing_costs) < 1

    def test_seller_closing_costs_deducted_at_sale(self):
        """Test that seller closing costs are deducted at sale."""
        config = SimulationConfig(
            duration_years=10,
            property_price=500000,
            down_payment_pct=20,
            mortgage_rate_annual=4.5,
            property_appreciation_annual=3.0,
            equity_growth_annual=7.0,
            monthly_rent=2000,
            closing_cost_buyer_pct=0.0,
            closing_cost_seller_pct=6.0,
            property_tax_rate=0.0,
            annual_home_insurance=0.0,
            annual_maintenance_pct=0.0,
        )

        results = calculate_scenarios(config)

        # Seller closing costs = 6% of final home value
        # With 3% appreciation for 10 years: $500k * (1.03)^10 ≈ $672k
        # Closing costs ≈ $40k
        assert results.total_closing_costs_seller > 0
        assert results.total_closing_costs_seller > 25000

        # Verify final net value accounts for seller closing costs
        final_home_value = results.data["Home_Value"].iloc[-1]
        expected_seller_costs = final_home_value * 0.06
        assert abs(results.total_closing_costs_seller - expected_seller_costs) < 1

    def test_property_tax_calculation(self):
        """Test that property taxes are calculated correctly."""
        config = SimulationConfig(
            duration_years=5,
            property_price=500000,
            down_payment_pct=20,
            mortgage_rate_annual=4.5,
            property_appreciation_annual=3.0,
            equity_growth_annual=7.0,
            monthly_rent=2000,
            closing_cost_buyer_pct=0.0,
            closing_cost_seller_pct=0.0,
            property_tax_rate=1.2,
            annual_home_insurance=0.0,
            annual_maintenance_pct=0.0,
            cost_inflation_rate=0.03,
        )

        results = calculate_scenarios(config)

        # Annual tax = 1.2% of $500k = $6k
        # Monthly tax = $500
        # Over 5 years with inflation, total should be > $30k
        assert results.total_property_tax_paid > 30000

        # Verify tax is tracked in data
        final_tax = results.data["Property_Tax_Paid"].iloc[-1]
        assert abs(final_tax - results.total_property_tax_paid) < 1

    def test_home_insurance_calculation(self):
        """Test that home insurance is calculated correctly."""
        config = SimulationConfig(
            duration_years=5,
            property_price=500000,
            down_payment_pct=20,
            mortgage_rate_annual=4.5,
            property_appreciation_annual=3.0,
            equity_growth_annual=7.0,
            monthly_rent=2000,
            closing_cost_buyer_pct=0.0,
            closing_cost_seller_pct=0.0,
            property_tax_rate=0.0,
            annual_home_insurance=1200,
            annual_maintenance_pct=0.0,
            cost_inflation_rate=0.03,
        )

        results = calculate_scenarios(config)

        # Annual insurance = $1200
        # Over 5 years with 3% inflation, total should be > $6000
        assert results.total_insurance_paid > 6000

        # Verify insurance is tracked in data
        final_insurance = results.data["Insurance_Paid"].iloc[-1]
        assert abs(final_insurance - results.total_insurance_paid) < 1

    def test_maintenance_calculation(self):
        """Test that maintenance costs are calculated correctly."""
        config = SimulationConfig(
            duration_years=5,
            property_price=500000,
            down_payment_pct=20,
            mortgage_rate_annual=4.5,
            property_appreciation_annual=3.0,
            equity_growth_annual=7.0,
            monthly_rent=2000,
            closing_cost_buyer_pct=0.0,
            closing_cost_seller_pct=0.0,
            property_tax_rate=0.0,
            annual_home_insurance=0.0,
            annual_maintenance_pct=1.0,
        )

        results = calculate_scenarios(config)

        # Annual maintenance = 1% of $500k = $5k
        # Over 5 years with appreciation, total should be > $25k
        assert results.total_maintenance_paid > 25000

        # Verify maintenance is tracked in data
        final_maintenance = results.data["Maintenance_Paid"].iloc[-1]
        assert abs(final_maintenance - results.total_maintenance_paid) < 1

    def test_zero_closing_costs(self):
        """Test simulation with zero closing costs."""
        config = SimulationConfig(
            duration_years=10,
            property_price=500000,
            down_payment_pct=20,
            mortgage_rate_annual=4.5,
            property_appreciation_annual=3.0,
            equity_growth_annual=7.0,
            monthly_rent=2000,
            closing_cost_buyer_pct=0.0,
            closing_cost_seller_pct=0.0,
            property_tax_rate=0.0,
            annual_home_insurance=0.0,
            annual_maintenance_pct=0.0,
        )

        results = calculate_scenarios(config)

        # Closing costs should be zero
        assert results.total_closing_costs_buyer == 0.0
        assert results.total_closing_costs_seller == 0.0

        # Initial outflow should be just down payment
        initial_outflow = results.data["Outflow_Buy"].iloc[0]
        assert abs(initial_outflow - 100000) < 1000  # Allow for rounding

    def test_cost_columns_in_dataframe(self):
        """Test that cost columns exist in results DataFrame."""
        config = SimulationConfig(
            duration_years=5,
            property_price=500000,
            down_payment_pct=20,
            mortgage_rate_annual=4.5,
            property_appreciation_annual=3.0,
            equity_growth_annual=7.0,
            monthly_rent=2000,
        )

        results = calculate_scenarios(config)

        # Check that all cost columns exist
        cost_columns = [
            "Property_Tax_Paid",
            "Insurance_Paid",
            "Maintenance_Paid",
            "Closing_Costs_Buyer",
            "Closing_Costs_Seller",
        ]
        for col in cost_columns:
            assert col in results.data.columns, f"Column {col} not found in DataFrame"

    def test_inflating_costs_over_time(self):
        """Test that costs with inflation increase over time."""
        config = SimulationConfig(
            duration_years=10,
            property_price=500000,
            down_payment_pct=20,
            mortgage_rate_annual=4.5,
            property_appreciation_annual=3.0,
            equity_growth_annual=7.0,
            monthly_rent=2000,
            closing_cost_buyer_pct=0.0,
            closing_cost_seller_pct=0.0,
            property_tax_rate=1.2,
            annual_home_insurance=1200,
            annual_maintenance_pct=1.0,
            cost_inflation_rate=0.03,
        )

        results = calculate_scenarios(config)

        # Get costs at year 1 and year 10
        year_1_idx = 12  # Month 12 = Year 1
        year_10_idx = 120  # Month 120 = Year 10

        # Costs should increase over time due to inflation
        early_tax = results.data["Property_Tax_Paid"].iloc[year_1_idx]
        late_tax = results.data["Property_Tax_Paid"].iloc[year_10_idx]
        assert late_tax > early_tax * 5  # More than 5x due to inflation

        early_insurance = results.data["Insurance_Paid"].iloc[year_1_idx]
        late_insurance = results.data["Insurance_Paid"].iloc[year_10_idx]
        assert late_insurance > early_insurance * 5

    def test_total_cost_of_ownership_calculation(self):
        """Test that total cost of ownership is calculated correctly."""
        config = SimulationConfig(
            duration_years=5,
            property_price=500000,
            down_payment_pct=20,
            mortgage_rate_annual=4.5,
            property_appreciation_annual=3.0,
            equity_growth_annual=7.0,
            monthly_rent=2000,
            closing_cost_buyer_pct=3.0,
            closing_cost_seller_pct=6.0,
            property_tax_rate=1.2,
            annual_home_insurance=1200,
            annual_maintenance_pct=1.0,
        )

        results = calculate_scenarios(config)

        # Total costs should include all components
        total_costs = (
            results.total_closing_costs_buyer
            + results.total_closing_costs_seller
            + results.total_property_tax_paid
            + results.total_insurance_paid
            + results.total_maintenance_paid
        )

        # Total costs should be substantial (over $50k for 5 years)
        assert total_costs > 50000

        # Verify individual components are tracked
        assert results.total_closing_costs_buyer > 0
        assert results.total_closing_costs_seller > 0
        assert results.total_property_tax_paid > 0
        assert results.total_insurance_paid > 0
        assert results.total_maintenance_paid > 0
