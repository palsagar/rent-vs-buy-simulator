"""Hand-computed fixtures for the multi-region engine primitives.

Each class pins one primitive's arithmetic against a worked example, so
a sign flip or a misplaced /12 fails a build rather than shipping.
"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import numpy as np

from simulator.engine import calculate_scenarios
from tests.test_engine_core import run_flat, taxfree_config


class TestBuyerClosingAmount:
    def test_buyer_closing_is_a_single_element_series(self):
        # Uses np so `ruff --fix` does not delete the import before T6
        # needs it: pyproject.toml selects F with fixable = ["ALL"], so
        # an unused numpy import is auto-removed and T6's expected
        # failure becomes a NameError instead.
        series = run_flat(_uk_like_config(property_price=289_106))
        assert isinstance(series["_buyer_closing"], np.ndarray)
        assert series["_buyer_closing"].shape == (1,)

    def test_uk_sdlt_linear_identity_is_exact(self):
        # SDLT 2026/27 England & NI, standard single dwelling (gov.uk):
        #   0% to 125,000 | 2% to 250,000 | 5% to 925,000
        # For P in (250,000, 925,000]:
        #   SDLT(P) = 0.02*125,000 + 0.05*(P - 250,000) = 0.05P - 10,000
        # Plus ~3,100 of price-invariant fees (conveyancing, searches,
        # survey, Land Registry, lender product fee):
        #   C(P) = 0.05P - 6,900
        # At the England semi-detached preset price of 289,106:
        #   0.05 * 289,106 - 6,900 = 7,555.30, of which SDLT = 4,455.30
        results = calculate_scenarios(_uk_like_config(property_price=289_106))
        assert abs(results.total_closing_costs_buyer - 7555.30) < 1e-6

    def test_aggregate_clamps_at_zero_below_the_crossover(self):
        # 0.05P - 6,900 turns negative below P = 138,000, and the price
        # slider floor is 50,000 (fields.js). Without the clamp an
        # instantaneous buy-and-sell would report a profit.
        results = calculate_scenarios(_uk_like_config(property_price=100_000))
        assert results.total_closing_costs_buyer == 0.0

    def test_clamped_net_buy_at_t0_is_minus_seller_cost_only(self):
        cfg = _uk_like_config(property_price=100_000)
        series = run_flat(cfg)
        expected = -(100_000 * cfg.closing_cost_seller_pct / 100)
        assert abs(series["net_buy"][0] - expected) < 1e-6

    def test_reported_total_matches_the_series(self):
        # total_closing_costs_buyer used to be recomputed independently
        # of the series; the two can no longer disagree.
        cfg = _uk_like_config(property_price=289_106)
        series = run_flat(cfg)
        results = calculate_scenarios(cfg)
        assert (
            abs(results.total_closing_costs_buyer - float(series["_buyer_closing"][0]))
            < 1e-9
        )


def _uk_like_config(**overrides: object):
    """Tax-free config carrying the UK non-FTB buyer-cost pair."""
    base = dict(
        closing_cost_buyer_pct=5.0,
        closing_cost_buyer_amount=-6900.0,
        closing_cost_seller_pct=1.75,
    )
    base.update(overrides)
    return taxfree_config(**base)


class TestFlatPropertyLevy:
    def test_flat_levy_is_one_twelfth_per_month_with_no_indexation(self):
        cfg = taxfree_config(annual_property_levy=1200.0, cost_inflation_rate=0.0)
        series = run_flat(cfg)
        assert abs(series["_levy"][1] - 100.0) < 1e-9

    def test_flat_levy_is_indexed_by_cost_inflation(self):
        # cost_index(t) = (1 + cir/12) ** (t - 1); at 12% annual the
        # month-13 charge has compounded for 12 months.
        cfg = taxfree_config(
            horizon_years=3, annual_property_levy=1200.0, cost_inflation_rate=0.12
        )
        series = run_flat(cfg)
        assert abs(series["_levy"][13] - 100.0 * 1.01**12) < 1e-9

    def test_ad_valorem_and_flat_paths_are_independently_additive(self):
        # Proves the US ad-valorem path is untouched by the new term.
        kwargs = dict(horizon_years=3, property_appreciation_annual=3.0)
        both = run_flat(
            taxfree_config(property_tax_rate=1.2, annual_property_levy=1200.0, **kwargs)
        )
        rate_only = run_flat(
            taxfree_config(property_tax_rate=1.2, annual_property_levy=0.0, **kwargs)
        )
        amount_only = run_flat(
            taxfree_config(property_tax_rate=0.0, annual_property_levy=1200.0, **kwargs)
        )
        assert np.allclose(
            both["_levy"], rate_only["_levy"] + amount_only["_levy"], atol=1e-9
        )


class TestFlatMaintenanceAmount:
    def test_flat_maintenance_is_one_twelfth_per_month(self):
        cfg = taxfree_config(annual_maintenance_amount=1200.0, cost_inflation_rate=0.0)
        series = run_flat(cfg)
        assert abs(series["_maintenance"][1] - 100.0) < 1e-9

    def test_flat_maintenance_is_indexed_by_cost_inflation(self):
        cfg = taxfree_config(
            horizon_years=3,
            annual_maintenance_amount=1200.0,
            cost_inflation_rate=0.12,
        )
        series = run_flat(cfg)
        assert abs(series["_maintenance"][13] - 100.0 * 1.01**12) < 1e-9

    def test_pct_and_amount_paths_are_independently_additive(self):
        kwargs = dict(horizon_years=3, property_appreciation_annual=3.0)
        both = run_flat(
            taxfree_config(
                annual_maintenance_pct=1.0, annual_maintenance_amount=1200.0, **kwargs
            )
        )
        pct_only = run_flat(taxfree_config(annual_maintenance_pct=1.0, **kwargs))
        amount_only = run_flat(
            taxfree_config(annual_maintenance_amount=1200.0, **kwargs)
        )
        assert np.allclose(
            both["_maintenance"],
            pct_only["_maintenance"] + amount_only["_maintenance"],
            atol=1e-9,
        )


class TestOccupierBorneLevy:
    """Occupier-borne levies (UK council tax, DE umlagefaehige Grundsteuer)
    are owed by whoever lives there, so the renter bears them too.

    TWO DIFFERENT PAIRINGS, testing two different properties. Do not
    merge them -- each is false under the other's comparison.
    """

    @staticmethod
    def _incidence_pair():
        """Same levy, flag off vs on. Tests WHO PAYS.

        Not verdict-invariant: with the flag off the buyer alone bears L,
        with it on both do, so the surplus and hence the portfolios move.
        """
        kwargs = dict(
            horizon_years=5,
            annual_property_levy=2392.0,
            equity_growth_annual=7.0,
            property_appreciation_annual=3.0,
            rent_inflation_rate=0.03,
        )
        off = taxfree_config(levy_paid_by_occupier=False, **kwargs)
        on = taxfree_config(levy_paid_by_occupier=True, **kwargs)
        return off, on

    @staticmethod
    def _invariance_pair():
        """No levy at all vs an occupier-borne levy. Tests THE VERDICT.

        This is the comparison the invariance proof is actually about:
        surplus = (b+L) - (r+L) = b - r, so contributions and both
        portfolios are unchanged, and cash_committed rises identically on
        both arms and cancels in the difference.

        interest_deduction_enabled is set EXPLICITLY, not inherited: the
        equivalence holds only while the levy does not feed the deduction
        block at engine.py:226, which adds the yearly levy to the
        deductible base. With deduction on, the levy config accrues
        cum_tax_savings the zero-levy config does not and net_buy
        diverges -- see test_equivalence_requires_a_non_deductible_levy.
        UK and DE both ship interestDeductionEnabled False, so the
        shipped regions satisfy this; a test resting on that as an
        inherited default would be resting on an unstated assumption.
        """
        kwargs = dict(
            horizon_years=5,
            equity_growth_annual=7.0,
            property_appreciation_annual=3.0,
            rent_inflation_rate=0.03,
            interest_deduction_enabled=False,
        )
        none = taxfree_config(annual_property_levy=0.0, **kwargs)
        both = taxfree_config(
            annual_property_levy=2392.0, levy_paid_by_occupier=True, **kwargs
        )
        return none, both

    def test_verdict_is_invariant(self):
        # Relative tolerance, not absolute: cash_committed changes
        # magnitude and both nets are re-rounded before the subtraction,
        # and one ulp at ~1e7 is already ~2e-9.
        none, both = self._invariance_pair()
        assert math.isclose(
            calculate_scenarios(none).final_difference,
            calculate_scenarios(both).final_difference,
            rel_tol=1e-12,
        )

    def test_net_value_series_are_invariant_at_every_month(self):
        none, both = self._invariance_pair()
        s_none, s_both = run_flat(none), run_flat(both)
        diff_none = s_none["net_buy"] - s_none["net_rent"]
        diff_both = s_both["net_buy"] - s_both["net_rent"]
        # atol carries the near-zero months: the difference series passes
        # close to zero around breakeven, where a pure rtol has no room.
        assert np.allclose(diff_none, diff_both, rtol=1e-12, atol=1e-6)

    def test_levy_lands_on_both_arms(self):
        # NOT redundant with the two invariance tests above -- it is what
        # makes them meaningful. A flag that did nothing at all would
        # leave the DIFFERENCE unchanged and pass both of them trivially.
        # This pins the levels: each arm must drop by the full levy, so
        # the levy is proved to have landed rather than cancelled by
        # never being applied. Verified exact: 2392/yr x 5 = 11,960.00.
        none, both = self._invariance_pair()
        s_none, s_both = run_flat(none), run_flat(both)
        total_levy = float(np.sum(s_both["_levy"]))
        assert abs(total_levy - 2392.0 * 5) < 1e-9
        for arm in ("net_buy", "net_rent"):
            assert abs(s_none[arm][-1] - s_both[arm][-1] - total_levy) < 1e-6, (
                f"{arm} did not drop by the full levy"
            )

    def test_equivalence_requires_a_non_deductible_levy(self):
        # Pins the precondition above rather than leaving it in a comment.
        # This is NOT hypothetical: the US ships interestDeductionEnabled
        # True with levyDeductionCap 10000, so a US flat-levy component
        # would be one data change away from making the invariance
        # premise false while the test above still passed on its own
        # non-deductible fixture.
        kwargs = dict(
            horizon_years=5,
            equity_growth_annual=7.0,
            property_appreciation_annual=3.0,
            rent_inflation_rate=0.03,
            interest_deduction_enabled=True,
            marginal_tax_rate_pct=24.0,
        )
        none = taxfree_config(annual_property_levy=0.0, **kwargs)
        both = taxfree_config(
            annual_property_levy=2392.0, levy_paid_by_occupier=True, **kwargs
        )
        r_none, r_both = calculate_scenarios(none), calculate_scenarios(both)
        # The gap is exactly the tax shield on the levy:
        #   2392/yr x 5 years x 24% = 2,870.40
        shield = 2392.0 * 5 * 0.24
        assert abs(r_both.final_difference - r_none.final_difference - shield) < 1e-6
        assert abs(r_both.total_tax_savings - r_none.total_tax_savings - shield) < 1e-6

    def test_renter_year1_monthly_cost_rises_by_exactly_the_mean_levy(self):
        off, on = self._incidence_pair()
        levy = run_flat(on)["_levy"]
        expected = float(np.mean(levy[1:13]))
        assert (
            abs(
                calculate_scenarios(on).monthly_cost_rent_year1
                - calculate_scenarios(off).monthly_cost_rent_year1
                - expected
            )
            < 1e-9
        )

    def test_buyer_side_is_untouched_by_the_flag(self):
        # Under the INCIDENCE pairing the buyer pays L either way, so the
        # flag moves the renter only. (Under the invariance pairing both
        # sides move by L -- which is the point of that comparison.)
        off, on = self._incidence_pair()
        assert (
            abs(
                calculate_scenarios(on).monthly_cost_buy_year1
                - calculate_scenarios(off).monthly_cost_buy_year1
            )
            < 1e-9
        )

    def test_default_is_buyer_only(self):
        cfg = taxfree_config(annual_property_levy=2392.0)
        series = run_flat(cfg)
        # Renter pays rent only; the levy is nowhere in that line.
        assert abs(series["housing_cost_rent"][1] - cfg.monthly_rent) < 1e-9
