"""Tests for tax primitives: deduction savings + symmetric capital gains."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import numpy as np

from tests.test_engine_core import run_flat, taxfree_config


class TestInterestDeduction:
    def test_savings_credited_after_each_completed_year(self):
        cfg = taxfree_config(
            interest_deduction_enabled=True,
            marginal_tax_rate_pct=25.0,
            levy_deduction_cap=None,
        )
        s = run_flat(cfg)
        year1_interest = float(np.sum(s["_interest"][1:13]))
        expected = year1_interest * 0.25  # levy is zero in taxfree_config
        assert abs(s["cum_tax_savings"][12] - expected) < 1e-6
        # Not credited mid-year: month 11 still has zero
        assert abs(s["cum_tax_savings"][11]) < 1e-9

    def test_levy_deduction_respects_cap(self):
        capped = taxfree_config(
            interest_deduction_enabled=True,
            marginal_tax_rate_pct=25.0,
            property_tax_rate=1.2,
            levy_deduction_cap=500.0,
        )
        uncapped = taxfree_config(
            interest_deduction_enabled=True,
            marginal_tax_rate_pct=25.0,
            property_tax_rate=1.2,
            levy_deduction_cap=None,
        )
        s_cap, s_unc = run_flat(capped), run_flat(uncapped)
        year1_levy = float(np.sum(s_cap["_levy"][1:13]))
        assert year1_levy > 500.0  # cap actually binds in this fixture
        gap = s_unc["cum_tax_savings"][12] - s_cap["cum_tax_savings"][12]
        assert abs(gap - (year1_levy - 500.0) * 0.25) < 1e-6

    def test_disabled_means_zero(self):
        s = run_flat(taxfree_config(property_tax_rate=1.2))
        assert np.all(np.abs(s["cum_tax_savings"]) < 1e-9)


class TestSaleCapitalGains:
    def test_exempt_amount_taxes_only_excess_gain(self):
        # 12% flat annual appreciation for 2y on 120k: gain well over 10k
        cfg = taxfree_config(
            property_appreciation_annual=12.0,
            sale_cg_regime="exempt_amount",
            sale_cg_exempt_amount=10_000.0,
            sale_cg_rate_pct=20.0,
        )
        s = run_flat(cfg)
        base = run_flat(
            taxfree_config(property_appreciation_annual=12.0)
        )  # fully_exempt
        gain = s["home_value"][-1] - 120_000
        expected_tax = (gain - 10_000) * 0.20
        assert abs((base["net_buy"][-1] - s["net_buy"][-1]) - expected_tax) < 1e-4

    def test_exempt_after_years_boundary(self):
        kwargs = dict(
            property_appreciation_annual=12.0,
            sale_cg_regime="exempt_after_years",
            sale_cg_exempt_after_years=1,
            sale_cg_rate_pct=20.0,
        )
        s = run_flat(taxfree_config(**kwargs))
        base = run_flat(taxfree_config(property_appreciation_annual=12.0))
        # Before the holding period: taxed. At/after it: exempt.
        assert s["net_buy"][11] < base["net_buy"][11] - 1.0
        assert abs(s["net_buy"][12] - base["net_buy"][12]) < 1e-6
        assert abs(s["net_buy"][-1] - base["net_buy"][-1]) < 1e-6


class TestPortfolioCapitalGains:
    def test_renter_gains_taxed_at_portfolio_rate(self):
        taxed = taxfree_config(equity_growth_annual=7.0, portfolio_cg_rate_pct=30.0)
        free = taxfree_config(equity_growth_annual=7.0)
        s_taxed, s_free = run_flat(taxed), run_flat(free)
        gains = s_free["rent_portfolio"][-1] - s_free["_basis_rent"][-1]
        assert gains > 0
        gap = s_free["net_rent"][-1] - s_taxed["net_rent"][-1]
        assert abs(gap - gains * 0.30) < 1e-4

    def test_no_tax_when_no_gains(self):
        s = run_flat(taxfree_config(portfolio_cg_rate_pct=30.0))
        # 0% growth -> zero gains -> tax changes nothing
        months = np.arange(25)
        np.testing.assert_allclose(s["net_rent"], -500.0 * months, atol=1e-6)
