"""Tests for calculate_scenarios: assembly, verdict/chart consistency."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import numpy as np

from simulator.engine import calculate_scenarios
from tests.test_models import make_config


class TestConsistency:
    def test_verdict_is_the_last_point_of_the_charted_series(self):
        # THE regression test for the production bug: the headline,
        # the chart, and the breakeven all read the same series
        res = calculate_scenarios(make_config())
        assert res.final_net_buy == res.data["Net_Buy"].iloc[-1]
        assert res.final_net_rent == res.data["Net_Rent"].iloc[-1]
        assert res.final_difference == res.final_net_buy - res.final_net_rent

    def test_breakeven_sign_agrees_with_series(self):
        res = calculate_scenarios(make_config(horizon_years=30))
        diff = res.data["Net_Buy"] - res.data["Net_Rent"]
        if res.breakeven_year is None:
            # No crossing => the sign never flips after t=0
            signs = np.sign(diff.iloc[1:])
            assert len(set(signs[np.abs(diff.iloc[1:]) > 1e-6])) <= 1
        else:
            assert 0 < res.breakeven_year <= 30


class TestAssembly:
    def test_dataframe_shape_and_columns(self):
        res = calculate_scenarios(make_config(horizon_years=10))
        assert len(res.data) == 121  # H months + 1
        for col in [
            "Month",
            "Year",
            "Home_Value",
            "Equity_Value",
            "Buy_Portfolio_Value",
            "Mortgage_Balance",
            "Outflow_Buy",
            "Outflow_Rent",
            "Cash_Committed",
            "Net_Buy",
            "Net_Rent",
        ]:
            assert col in res.data.columns

    def test_year1_monthly_costs(self):
        res = calculate_scenarios(make_config())
        assert res.monthly_cost_rent_year1 > 0
        # Buyer cost must include levy+insurance+maintenance, not just PMT
        assert res.monthly_cost_buy_year1 > res.monthly_mortgage_payment

    def test_cost_totals_positive(self):
        res = calculate_scenarios(make_config())
        assert res.total_closing_costs_buyer == 500_000 * 0.03
        assert res.total_property_tax_paid > 0
        assert res.total_insurance_paid > 0
        assert res.total_maintenance_paid > 0
        assert res.total_closing_costs_seller > 0
