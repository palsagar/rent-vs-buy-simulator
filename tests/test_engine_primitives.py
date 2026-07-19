"""Hand-computed fixtures for the multi-region engine primitives.

Each class pins one primitive's arithmetic against a worked example, so
a sign flip or a misplaced /12 fails a build rather than shipping.
"""

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
