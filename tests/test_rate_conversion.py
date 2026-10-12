"""Yearly growth rates compound as stated (ADR-0011).

A growth rate typed as 7% must be worth exactly 7% after twelve months.
Each test here would fail under the old nominal ``annual / 12``
conversion, which turned 7% into 7.23% a year. The mortgage rate is the
exception: it stays a nominal rate split over twelve months.
"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import numpy as np
import numpy_financial as npf

from simulator.engine import (
    _FLOAT_TOLERANCE,
    calculate_scenarios,
    monthly_rate_from_annual,
)
from simulator.monte_carlo import _simulate_single_path
from tests.test_engine_core import run_flat, taxfree_config
from tests.test_models import make_config


class TestHelper:
    def test_twelve_months_compound_back_to_the_yearly_rate(self):
        for annual in (0.07, 0.03, 0.0, -0.5):
            monthly = monthly_rate_from_annual(annual)
            assert abs((1 + monthly) ** 12 - (1 + annual)) < 1e-12, annual

    def test_floors_at_minus_99_pct(self):
        # Below -100% the twelfth root is undefined. A Monte Carlo draw
        # can in principle land there, so the helper floors it.
        floored = monthly_rate_from_annual(-1.5) - monthly_rate_from_annual(-0.99)
        assert abs(floored) < _FLOAT_TOLERANCE
        assert 1 + monthly_rate_from_annual(-0.99) > 0

    def test_scalar_in_float_out_and_arrays_elementwise(self):
        assert isinstance(monthly_rate_from_annual(0.07), float)
        rates = np.array([0.07, -0.1, 0.0])
        out = monthly_rate_from_annual(rates)
        assert isinstance(out, np.ndarray)
        for annual, monthly in zip(rates, out, strict=True):
            assert abs(monthly - monthly_rate_from_annual(float(annual))) < 1e-15


class TestDeterministicEngine:
    def test_home_value_after_one_year_is_exactly_one_plus_rate(self):
        results = calculate_scenarios(
            make_config(horizon_years=1, property_appreciation_annual=3.0)
        )
        growth = results.data["Home_Value"].iloc[12] / 500_000
        assert abs(growth - 1.03) < 1e-12

    def test_home_value_after_n_years_is_the_yearly_rate_compounded(self):
        results = calculate_scenarios(
            make_config(horizon_years=25, property_appreciation_annual=5.0)
        )
        growth = results.data["Home_Value"].iloc[300] / 500_000
        assert math.isclose(growth, 1.05**25, rel_tol=1e-10)
        # Under the old conversion the factor was (1 + 0.05/12) ** 300,
        # 3.4% higher; this test cannot pass on that convention.
        assert abs((1 + 0.05 / 12) ** 300 / growth - 1) > 1e-3

    def test_rent_after_one_year_is_exactly_one_plus_rate(self):
        # Rent is set at the end of month 12 and paid in month 13.
        series = run_flat(taxfree_config(rent_inflation_rate=0.03))
        assert abs(series["housing_cost_rent"][13] - 500 * 1.03) < _FLOAT_TOLERANCE

    def test_fixed_costs_after_one_year_follow_cost_inflation_exactly(self):
        series = run_flat(
            taxfree_config(annual_home_insurance=1200.0, cost_inflation_rate=0.12)
        )
        assert abs(series["_insurance"][13] - 100.0 * 1.12) < _FLOAT_TOLERANCE

    def test_invested_lump_sum_grows_at_the_yearly_rate(self):
        # All cash and no running costs: the renter's portfolio is the
        # initial outlay compounding alone, with no contributions.
        series = run_flat(
            taxfree_config(
                horizon_years=30, down_payment_pct=100, equity_growth_annual=7.0
            )
        )
        growth = series["rent_portfolio"][360] / series["rent_portfolio"][0]
        assert math.isclose(growth, 1.07**30, rel_tol=1e-10)

    def test_mortgage_rate_is_still_a_nominal_rate_split_over_twelve_months(self):
        # Mortgage rates are quoted as a yearly rate divided by twelve for
        # each monthly payment, and npf.pmt expects exactly that.
        results = calculate_scenarios(make_config())
        expected = -npf.pmt(0.065 / 12, 360, 400_000)
        assert abs(results.monthly_mortgage_payment - expected) < _FLOAT_TOLERANCE


class TestMonteCarloPaths:
    def test_each_yearly_draw_compounds_back_to_itself(self):
        # All cash, so the renter's portfolio is the 120,000 outlay alone:
        #   net_rent(t) = 120,000 * G(t) - 120,000 - 500 * t
        # with G the product of the yearly draws so far.
        config = taxfree_config(
            down_payment_pct=100,
            closing_cost_buyer_pct=0.0,
            closing_cost_seller_pct=0.0,
        )
        _, net_rent = _simulate_single_path(
            config, np.zeros(2), np.array([7.0, -10.0]), np.zeros(2)
        )
        outlay = 120_000
        growth = (net_rent + outlay + 500 * np.arange(25)) / outlay
        assert math.isclose(growth[12], 1.07, rel_tol=1e-12)
        assert math.isclose(growth[24], 1.07 * 0.90, rel_tol=1e-12)


class TestWealthTaxYear:
    def test_the_yearly_return_is_the_compounded_year_not_a_sum(self):
        # Box 3 taxes min(deemed, actual). At 6.1% actual against a 6%
        # deemed return the min binds on the deemed side, so the drag is
        # 6% x 36% = 2.16% a year. Summing the twelve monthly rates would
        # give 5.94%, below the deemed 6%, and a smaller drag.
        series = run_flat(
            taxfree_config(
                horizon_years=30,
                down_payment_pct=100,
                equity_growth_annual=6.1,
                portfolio_deemed_return_pct=6.0,
                portfolio_drag_rate_pct=36.0,
            )
        )
        monthly = monthly_rate_from_annual(0.061) - 0.0216 / 12
        growth = series["rent_portfolio"][360] / series["rent_portfolio"][0]
        assert math.isclose(growth, (1 + monthly) ** 360, rel_tol=1e-12)
