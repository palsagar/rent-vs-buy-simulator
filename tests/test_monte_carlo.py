"""Unit tests for Monte Carlo simulation."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import numpy as np
import pytest

from simulator.models import MonteCarloConfig, MonteCarloResults


class TestMonteCarloConfig:
    """Tests for MonteCarloConfig validation and defaults."""

    def test_default_values(self):
        """Test that defaults are set correctly."""
        mc = MonteCarloConfig()
        assert mc.n_simulations == 500
        assert mc.seed == 42
        assert mc.randomize_property_appreciation is True
        assert mc.property_appreciation_std == 5.0
        assert mc.randomize_equity_growth is True
        assert mc.equity_growth_std == 5.0
        assert mc.randomize_rent_inflation is True
        assert mc.rent_inflation_std == 1.5
        assert mc.appreciation_equity_correlation == 0.3

    def test_custom_values(self):
        """Test that custom values override defaults."""
        mc = MonteCarloConfig(
            n_simulations=1000,
            seed=None,
            property_appreciation_std=8.0,
            appreciation_equity_correlation=0.5,
        )
        assert mc.n_simulations == 1000
        assert mc.seed is None
        assert mc.property_appreciation_std == 8.0
        assert mc.appreciation_equity_correlation == 0.5

    def test_invalid_n_simulations_raises(self):
        """Test that n_simulations <= 0 raises ValueError."""
        with pytest.raises(ValueError, match="n_simulations must be positive"):
            MonteCarloConfig(n_simulations=0)

    def test_invalid_n_simulations_negative_raises(self):
        """Test that negative n_simulations raises ValueError."""
        with pytest.raises(ValueError, match="n_simulations must be positive"):
            MonteCarloConfig(n_simulations=-10)

    def test_negative_std_raises(self):
        """Test that negative std raises ValueError."""
        with pytest.raises(
            ValueError, match="property_appreciation_std must be non-negative"
        ):
            MonteCarloConfig(property_appreciation_std=-1.0)

    def test_negative_equity_std_raises(self):
        """Test that negative equity_growth_std raises ValueError."""
        with pytest.raises(ValueError, match="equity_growth_std must be non-negative"):
            MonteCarloConfig(equity_growth_std=-2.0)

    def test_negative_rent_inflation_std_raises(self):
        """Test that negative rent_inflation_std raises ValueError."""
        with pytest.raises(ValueError, match="rent_inflation_std must be non-negative"):
            MonteCarloConfig(rent_inflation_std=-0.5)

    def test_correlation_out_of_bounds_raises(self):
        """Test that correlation outside [-1, 1] raises ValueError."""
        with pytest.raises(
            ValueError,
            match="appreciation_equity_correlation must be between -1 and 1",
        ):
            MonteCarloConfig(appreciation_equity_correlation=1.5)

    def test_correlation_negative_bound_raises(self):
        """Test that correlation below -1 raises ValueError."""
        with pytest.raises(
            ValueError,
            match="appreciation_equity_correlation must be between -1 and 1",
        ):
            MonteCarloConfig(appreciation_equity_correlation=-1.5)

    def test_correlation_at_bounds_accepted(self):
        """Test that correlation at exact bounds is accepted."""
        mc_pos = MonteCarloConfig(appreciation_equity_correlation=1.0)
        assert mc_pos.appreciation_equity_correlation == 1.0
        mc_neg = MonteCarloConfig(appreciation_equity_correlation=-1.0)
        assert mc_neg.appreciation_equity_correlation == -1.0


class TestMonteCarloResults:
    """Tests for MonteCarloResults dataclass."""

    def _make_results(self, n_sims: int = 10, n_months: int = 120):
        """Build a minimal MonteCarloResults for testing.

        Parameters
        ----------
        n_sims : int
            Number of simulations.
        n_months : int
            Number of months in the simulation.

        Returns
        -------
        MonteCarloResults
            A populated results object with random data.

        Examples
        --------
        .. code-block:: python

            results = self._make_results(n_sims=50, n_months=60)

        """
        rng = np.random.default_rng(42)
        n_points = n_months + 1
        all_net_buy = rng.normal(100000, 50000, (n_sims, n_points))
        all_net_rent = rng.normal(80000, 40000, (n_sims, n_points))
        all_diffs = all_net_buy - all_net_rent
        year_arr = np.arange(n_points) / 12

        percentile_levels = [5, 25, 50, 75, 95]
        diff_pctiles = np.percentile(all_diffs, percentile_levels, axis=0)

        final_diffs = all_diffs[:, -1]
        buy_wins_pct = float(np.mean(final_diffs > 0) * 100)

        from simulator.models import MonteCarloConfig, SimulationConfig

        base_config = SimulationConfig(
            duration_years=n_months // 12,
            property_price=500000,
            down_payment_pct=20,
            mortgage_rate_annual=4.5,
            property_appreciation_annual=3.0,
            equity_growth_annual=7.0,
            monthly_rent=2000,
        )

        return MonteCarloResults(
            final_net_buy=all_net_buy[:, -1],
            final_net_rent=all_net_rent[:, -1],
            final_differences=final_diffs,
            all_net_buy=all_net_buy,
            all_net_rent=all_net_rent,
            all_differences=all_diffs,
            year_arr=year_arr,
            percentile_levels=percentile_levels,
            difference_percentiles=diff_pctiles,
            buy_wins_pct=buy_wins_pct,
            median_difference=float(np.median(final_diffs)),
            p5_difference=float(np.percentile(final_diffs, 5)),
            p95_difference=float(np.percentile(final_diffs, 95)),
            sensitivity_params=[
                "Property Appreciation",
                "Equity Growth",
            ],
            sensitivity_low=np.array([-50000, -30000]),
            sensitivity_high=np.array([60000, 40000]),
            sensitivity_base=20000.0,
            base_config=base_config,
            mc_config=MonteCarloConfig(),
            n_simulations=n_sims,
        )

    def test_shapes(self):
        """Test that array shapes are consistent."""
        results = self._make_results(n_sims=10, n_months=120)
        assert results.final_net_buy.shape == (10,)
        assert results.final_net_rent.shape == (10,)
        assert results.final_differences.shape == (10,)
        assert results.all_net_buy.shape == (10, 121)
        assert results.all_net_rent.shape == (10, 121)
        assert results.all_differences.shape == (10, 121)
        assert results.year_arr.shape == (121,)
        assert results.difference_percentiles.shape == (5, 121)

    def test_summary_stats_types(self):
        """Test that summary statistics have correct types."""
        results = self._make_results()
        assert isinstance(results.buy_wins_pct, float)
        assert isinstance(results.median_difference, float)
        assert isinstance(results.p5_difference, float)
        assert isinstance(results.p95_difference, float)
        assert 0 <= results.buy_wins_pct <= 100

    def test_sensitivity_arrays_match(self):
        """Test that sensitivity arrays have consistent lengths."""
        results = self._make_results()
        n_params = len(results.sensitivity_params)
        assert results.sensitivity_low.shape == (n_params,)
        assert results.sensitivity_high.shape == (n_params,)
        assert isinstance(results.sensitivity_base, float)

    def test_n_simulations_matches_arrays(self):
        """Test that n_simulations matches first dimension of arrays."""
        results = self._make_results(n_sims=25, n_months=60)
        assert results.n_simulations == 25
        assert results.all_net_buy.shape[0] == 25
