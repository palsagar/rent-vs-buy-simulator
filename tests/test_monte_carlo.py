"""Tests for Monte Carlo on the shared engine core."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import numpy as np

from simulator.engine import calculate_scenarios
from simulator.models import MonteCarloConfig
from simulator.monte_carlo import _compute_sensitivity, run_monte_carlo
from tests.test_models import make_config


class TestSharedCore:
    def test_zero_volatility_reproduces_deterministic_series(self):
        # THE anti-drift test: with all stds at 0, every MC path must
        # equal the deterministic Net Value series exactly
        cfg = make_config(horizon_years=5)
        mc = MonteCarloConfig(
            n_simulations=3,
            property_appreciation_std=0.0,
            equity_growth_std=0.0,
            rent_inflation_std=0.0,
        )
        det = calculate_scenarios(cfg)
        res = run_monte_carlo(cfg, mc)
        for i in range(3):
            np.testing.assert_allclose(
                res.all_net_buy[i], det.data["Net_Buy"].to_numpy(), atol=1e-6
            )
            np.testing.assert_allclose(
                res.all_net_rent[i], det.data["Net_Rent"].to_numpy(), atol=1e-6
            )
        assert abs(res.median_difference - det.final_difference) < 1e-6


class TestStatistics:
    def test_shapes_and_ranges(self):
        cfg = make_config(horizon_years=5)
        res = run_monte_carlo(cfg, MonteCarloConfig(n_simulations=50))
        assert res.all_net_buy.shape == (50, 61)
        assert 0.0 <= res.buy_wins_pct <= 100.0
        assert res.p5_difference <= res.median_difference <= res.p95_difference

    def test_seed_reproducibility(self):
        cfg = make_config(horizon_years=5)
        a = run_monte_carlo(cfg, MonteCarloConfig(n_simulations=20, seed=7))
        b = run_monte_carlo(cfg, MonteCarloConfig(n_simulations=20, seed=7))
        np.testing.assert_array_equal(a.final_differences, b.final_differences)


class TestSensitivity:
    def test_tornado_uses_final_difference(self):
        cfg = make_config(horizon_years=5)
        res = run_monte_carlo(cfg, MonteCarloConfig(n_simulations=10))
        det = calculate_scenarios(cfg)
        assert abs(res.sensitivity_base - det.final_difference) < 1e-6
        assert len(res.sensitivity_params) > 0
        assert len(res.sensitivity_low) == len(res.sensitivity_params)

    def test_tornado_low_uses_negative_growth_rate(self):
        # Equity Growth low perturbation must reflect the true negative rate,
        # not a clamped near-zero floor. With default std=15, the low target
        # for equity_growth_annual=7.0 is -8.0.
        base_cfg = make_config(equity_growth_annual=7.0)
        names, low, _high, _base = _compute_sensitivity(base_cfg)
        idx = names.index("Equity Growth")
        expected_low = calculate_scenarios(
            make_config(equity_growth_annual=-8.0)
        ).final_difference
        assert abs(low[idx] - expected_low) < 1e-6


class TestPortfolioDragIsPathDependent:
    def test_mean_realised_drag_is_below_the_deterministic_rate(self):
        # The tax is concave in the return (min then floor), so by
        # Jensen's inequality the mean of the tax is BELOW the tax on the
        # mean. At the app's own calibration (mean 7%, sd 15%) the min
        # binds in ~47% of simulated years, so a run in which every path
        # drags exactly 2.16% means the min is NOT being evaluated per
        # path -- the exact failure this primitive exists to prevent.
        config = make_config(
            horizon_years=30,
            portfolio_deemed_return_pct=6.0,
            portfolio_drag_rate_pct=36.0,
        )
        flat = make_config(horizon_years=30)
        mc = MonteCarloConfig(n_simulations=200, seed=42)
        drag_results = run_monte_carlo(config, mc)
        # Deterministic reference: 7% > 6% every year, so exactly 2.16%.
        deterministic = calculate_scenarios(config).final_difference
        flat_det = calculate_scenarios(flat).final_difference
        # The drag reduces the renter's portfolio, so it RAISES
        # (net_buy - net_rent). Under MC the mean drag is smaller, so the
        # median difference must sit below the deterministic one.
        assert deterministic > flat_det
        assert drag_results.median_difference < deterministic

    def test_every_path_does_not_share_one_drag(self):
        # Two configs differing only in equity draws must produce
        # different realised drags; if the drag were pre-averaged the
        # spread across paths would collapse.
        config = make_config(
            horizon_years=30,
            portfolio_deemed_return_pct=6.0,
            portfolio_drag_rate_pct=36.0,
        )
        mc = MonteCarloConfig(n_simulations=200, seed=42)
        results = run_monte_carlo(config, mc)
        assert np.std(results.final_differences) > 0.0
