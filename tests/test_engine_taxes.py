"""Tests for tax primitives: deduction savings + symmetric capital gains."""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import numpy as np
import numpy_financial as npf

from simulator.engine import monthly_rate_from_annual
from simulator.models import SimulationConfig
from tests.test_engine_core import run_flat, taxfree_config


class TestInterestDeduction:
    def test_savings_credited_after_each_completed_year(self):
        # cum_tax_savings records the refunds received, at face value. The
        # refunds themselves are invested (TestRefundsAreInvested).
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


def _yearly_refunds(rate: float) -> tuple[float, float]:
    """The two yearly refunds of the taxfree_config mortgage, by npf.

    90,000 borrowed at 6% over 30 years; the refund is the year's
    interest times the marginal rate (taxfree_config has no levy).

    Examples
    --------
    .. code-block:: python

        r1, r2 = _yearly_refunds(0.25)   # about 1,342 and 1,325

    """
    interest = [-npf.ipmt(0.06 / 12, per, 360, 90_000) for per in range(1, 25)]
    return rate * sum(interest[:12]), rate * sum(interest[12:])


class TestRefundsAreInvested:
    """Each year's tax refund joins the buyer's portfolio in the month it
    arrives, then grows and is taxed like the rest of it (ADR-0013).

    In taxfree_config the buyer pays 539.60 a month against 500 rent, so
    buying is the dearer side throughout and the buyer invests nothing
    else: the buyer's portfolio holds the refunds alone.
    """

    @staticmethod
    def _pair(**overrides: object) -> tuple[dict, dict]:
        kwargs = dict(marginal_tax_rate_pct=25.0, equity_growth_annual=7.0)
        kwargs.update(overrides)
        on = run_flat(taxfree_config(interest_deduction_enabled=True, **kwargs))
        off = run_flat(taxfree_config(interest_deduction_enabled=False, **kwargs))
        return on, off

    def test_a_refund_compounds_to_the_horizon_and_its_gain_is_taxed(self):
        # Refund 1 arrives at month 12 and grows exactly 7% by month 24.
        # Refund 2 arrives at month 24 and has not grown. At a 15% rate
        # only refund 1's gain is taxed when the portfolio is cashed in.
        r1, r2 = _yearly_refunds(0.25)
        on, off = self._pair(portfolio_cg_rate_pct=15.0)
        expected = r1 * 1.07 + r2 - 0.15 * (r1 * 0.07)
        assert abs((on["net_buy"][24] - off["net_buy"][24]) - expected) < 1e-6
        np.testing.assert_allclose(on["net_rent"], off["net_rent"], atol=1e-9)

    def test_a_refund_counts_at_face_value_in_the_month_it_arrives(self):
        r1, _ = _yearly_refunds(0.25)
        on, off = self._pair()
        assert abs(on["net_buy"][11] - off["net_buy"][11]) < 1e-9
        assert abs((on["net_buy"][12] - off["net_buy"][12]) - r1) < 1e-6

    def test_refunds_pay_the_wealth_tax_like_other_investments(self):
        # NL box 3: at 7% against a 6% deemed return the portfolio loses
        # 6% x 36% = 2.16% a year, refunds included.
        r1, r2 = _yearly_refunds(0.25)
        on, off = self._pair(
            portfolio_deemed_return_pct=6.0, portfolio_drag_rate_pct=36.0
        )
        growth = (1 + monthly_rate_from_annual(0.07) - 0.06 * 0.36 / 12) ** 12
        expected = r1 * growth + r2
        assert abs((on["net_buy"][24] - off["net_buy"][24]) - expected) < 1e-6

    def test_refunds_change_no_cost_and_no_cash_committed(self):
        # A refund is money coming back, not a lower cost: what each side
        # pays and commits each month, and the renter's portfolio, are the
        # same with or without it. Only what the buyer invests grows.
        r1, r2 = _yearly_refunds(0.25)
        on, off = self._pair()
        for key in (
            "housing_cost_buy",
            "housing_cost_rent",
            "cash_committed",
            "rent_portfolio",
        ):
            np.testing.assert_allclose(on[key], off[key], atol=1e-9, err_msg=key)
        assert abs((on["_basis_buy"][24] - off["_basis_buy"][24]) - (r1 + r2)) < 1e-6


def _taxed_sale(**overrides: object) -> SimulationConfig:
    """taxfree_config with every pound of home-sale profit taxed at 20%."""
    base = dict(
        sale_cg_regime="exempt_amount",
        sale_cg_exempt_amount=0.0,
        sale_cg_rate_pct=20.0,
    )
    base.update(overrides)
    return taxfree_config(**base)


class TestSaleCapitalGains:
    """The taxed profit is the sale price less selling costs, over the
    price paid plus buying costs (ADR-0012). taxfree_config charges 2% to
    buy (2,400 on 120,000) and 5% of the sale price to sell."""

    def test_exempt_amount_taxes_only_excess_gain(self):
        # 12% a year for 2 years on 120k: the home is worth 150,528. Net
        # of 5% selling costs and the 122,400 paid in, the profit is
        # 20,601.60, so 10,601.60 is taxed above the 10k exemption.
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
        gain = s["home_value"][-1] * 0.95 - (120_000 + 2_400)
        expected_tax = (gain - 10_000) * 0.20
        assert expected_tax > 0
        assert abs((base["net_buy"][-1] - s["net_buy"][-1]) - expected_tax) < 1e-4

    def test_gain_is_net_of_both_transaction_costs(self):
        # Against a tax on the gross rise in value, the tax falls by
        # exactly the rate times what was paid to buy and to sell.
        taxed = run_flat(_taxed_sale(property_appreciation_annual=12.0))
        exempt = run_flat(taxfree_config(property_appreciation_annual=12.0))
        tax = exempt["net_buy"][-1] - taxed["net_buy"][-1]
        home_value = taxed["home_value"][-1]
        gross_rule_tax = (home_value - 120_000) * 0.20
        costs = home_value * 0.05 + 120_000 * 0.02
        assert abs((gross_rule_tax - tax) - costs * 0.20) < 1e-6

    def test_instant_resale_is_never_taxed(self):
        # At t=0 the sale recovers neither fee: a loss of exactly both.
        s = run_flat(_taxed_sale())
        assert abs(s["net_buy"][0] - -(120_000 * 0.02 + 120_000 * 0.05)) < 1e-6

    def test_a_sale_that_does_not_cover_its_costs_is_not_taxed(self):
        # 3% a year for 2 years: the home gains 7,308, less than the 2,400
        # paid to buy plus the ~6,365 paid to sell, so there is no profit
        # to tax in any month even with no exemption at all.
        taxed = run_flat(_taxed_sale(property_appreciation_annual=3.0))
        exempt = run_flat(taxfree_config(property_appreciation_annual=3.0))
        np.testing.assert_allclose(taxed["net_buy"], exempt["net_buy"], atol=1e-6)

    def test_exempt_after_years_taxes_the_net_gain_before_the_holding_period(self):
        s = run_flat(
            _taxed_sale(
                property_appreciation_annual=12.0,
                sale_cg_regime="exempt_after_years",
                sale_cg_exempt_after_years=1,
            )
        )
        exempt = run_flat(taxfree_config(property_appreciation_annual=12.0))
        net_gain = s["home_value"][11] * 0.95 - (120_000 + 2_400)
        assert net_gain > 0
        tax = exempt["net_buy"][11] - s["net_buy"][11]
        assert abs(tax - net_gain * 0.20) < 1e-6

    def test_uk_pair_with_private_residence_relief_switched_off(self):
        # The UK buying cost is 5% of the price less 6,900 (the stamp duty
        # slice plus fees, clamped at zero) and selling costs 1.75%. With
        # the relief off, every pound of profit is taxed at 24%.
        price = 289_106
        kwargs = dict(
            horizon_years=20,
            property_price=price,
            property_appreciation_annual=3.0,
            closing_cost_buyer_pct=5.0,
            closing_cost_buyer_amount=-6900.0,
            closing_cost_seller_pct=1.75,
        )
        taxed = run_flat(_taxed_sale(sale_cg_rate_pct=24.0, **kwargs))
        exempt = run_flat(taxfree_config(**kwargs))
        home_value = taxed["home_value"][-1]
        cost = price + max(0.05 * price - 6900, 0)
        expected = max(home_value * (1 - 0.0175) - cost, 0) * 0.24
        assert expected > 0
        tax = exempt["net_buy"][-1] - taxed["net_buy"][-1]
        assert abs(tax - expected) < 1e-6

    def test_home_and_portfolio_are_taxed_by_the_same_rule(self):
        # ADR-0001: both exits tax what comes out over what went in. With
        # no transaction costs an all-cash home and the renter's lump sum
        # (the same 120,000) grow at the same 5%, so at the same rate the
        # two taxes are equal. Holds with or without ADR-0012, whose cost
        # adjustments are zero here; the tests above are what pin them.
        kwargs = dict(
            horizon_years=10,
            down_payment_pct=100,
            closing_cost_buyer_pct=0.0,
            closing_cost_seller_pct=0.0,
            property_appreciation_annual=5.0,
            equity_growth_annual=5.0,
        )
        untaxed = run_flat(taxfree_config(**kwargs))
        home_taxed = run_flat(_taxed_sale(**kwargs))
        portfolio_taxed = run_flat(taxfree_config(portfolio_cg_rate_pct=20.0, **kwargs))
        home_tax = untaxed["net_buy"][-1] - home_taxed["net_buy"][-1]
        portfolio_tax = untaxed["net_rent"][-1] - portfolio_taxed["net_rent"][-1]
        assert home_tax > 0
        assert math.isclose(home_tax, portfolio_tax, rel_tol=1e-12)

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
