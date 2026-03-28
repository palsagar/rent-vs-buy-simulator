"""Unit tests for Monte Carlo simulation."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import numpy as np
import pytest

from simulator.engine import calculate_scenarios as deterministic_engine
from simulator.models import MonteCarloConfig, MonteCarloResults, SimulationConfig
from simulator.monte_carlo import _generate_annual_draws, _simulate_single_path


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


class TestGenerateAnnualDraws:
    """Tests for _generate_annual_draws."""

    @pytest.fixture()
    def base_config(self):
        """Return a standard SimulationConfig for MC tests.

        Returns
        -------
        SimulationConfig
            A 10-year, $500k property configuration.

        Examples
        --------
        .. code-block:: python

            config = base_config

        """
        return SimulationConfig(
            duration_years=10,
            property_price=500000,
            down_payment_pct=20,
            mortgage_rate_annual=4.5,
            property_appreciation_annual=3.0,
            equity_growth_annual=7.0,
            monthly_rent=2000,
        )

    def test_output_shapes(self, base_config):
        """Test that output arrays have correct shapes."""
        mc_config = MonteCarloConfig(n_simulations=50, seed=42)
        rng = np.random.default_rng(mc_config.seed)
        draws = _generate_annual_draws(
            base_config, mc_config, base_config.duration_years, rng
        )
        assert draws["property_appreciation"].shape == (50, 10)
        assert draws["equity_growth"].shape == (50, 10)
        assert draws["rent_inflation"].shape == (50, 10)

    def test_means_near_base_rates(self, base_config):
        """Test that mean draws are near the base config rates."""
        mc_config = MonteCarloConfig(n_simulations=5000, seed=42)
        rng = np.random.default_rng(mc_config.seed)
        draws = _generate_annual_draws(
            base_config, mc_config, base_config.duration_years, rng
        )
        # Mean property appreciation should be near 3.0
        mean_prop = np.mean(draws["property_appreciation"])
        assert abs(mean_prop - 3.0) < 0.5

        # Mean equity growth should be near 7.0
        mean_eq = np.mean(draws["equity_growth"])
        assert abs(mean_eq - 7.0) < 0.5

        # Mean rent inflation should be near 3.0 (config has 0.03 = 3%)
        mean_rent = np.mean(draws["rent_inflation"])
        assert abs(mean_rent - 3.0) < 0.5

    def test_correlation_positive(self, base_config):
        """Test that property and equity draws are positively correlated."""
        mc_config = MonteCarloConfig(
            n_simulations=10000,
            seed=42,
            appreciation_equity_correlation=0.8,
        )
        rng = np.random.default_rng(mc_config.seed)
        draws = _generate_annual_draws(
            base_config, mc_config, base_config.duration_years, rng
        )
        # Flatten and compute correlation
        prop_flat = draws["property_appreciation"].flatten()
        eq_flat = draws["equity_growth"].flatten()
        corr = np.corrcoef(prop_flat, eq_flat)[0, 1]
        assert corr > 0.5  # Should be strongly positive

    def test_zero_correlation(self, base_config):
        """Test that zero correlation produces near-zero correlation."""
        mc_config = MonteCarloConfig(
            n_simulations=10000,
            seed=42,
            appreciation_equity_correlation=0.0,
        )
        rng = np.random.default_rng(mc_config.seed)
        draws = _generate_annual_draws(
            base_config, mc_config, base_config.duration_years, rng
        )
        prop_flat = draws["property_appreciation"].flatten()
        eq_flat = draws["equity_growth"].flatten()
        corr = np.corrcoef(prop_flat, eq_flat)[0, 1]
        assert abs(corr) < 0.1

    def test_rent_inflation_clamped_non_negative(self, base_config):
        """Test that rent inflation draws are clamped at zero."""
        mc_config = MonteCarloConfig(
            n_simulations=1000,
            seed=42,
            rent_inflation_std=10.0,  # High std to force some negatives
        )
        rng = np.random.default_rng(mc_config.seed)
        draws = _generate_annual_draws(
            base_config, mc_config, base_config.duration_years, rng
        )
        assert np.all(draws["rent_inflation"] >= 0)

    def test_disabled_randomization_returns_constant(self, base_config):
        """Test that disabling randomization returns base rates."""
        mc_config = MonteCarloConfig(
            n_simulations=100,
            seed=42,
            randomize_property_appreciation=False,
            randomize_equity_growth=False,
            randomize_rent_inflation=False,
        )
        rng = np.random.default_rng(mc_config.seed)
        draws = _generate_annual_draws(
            base_config, mc_config, base_config.duration_years, rng
        )
        # All values should be the base rates
        assert np.allclose(draws["property_appreciation"], 3.0)
        assert np.allclose(draws["equity_growth"], 7.0)
        # Rent inflation is stored as 0.03 in config, converted to 3.0 pct
        assert np.allclose(draws["rent_inflation"], 3.0)

    def test_reproducibility_with_seed(self, base_config):
        """Test that same seed produces identical draws."""
        mc_config = MonteCarloConfig(n_simulations=50, seed=123)
        rng1 = np.random.default_rng(mc_config.seed)
        draws1 = _generate_annual_draws(
            base_config, mc_config, base_config.duration_years, rng1
        )
        rng2 = np.random.default_rng(mc_config.seed)
        draws2 = _generate_annual_draws(
            base_config, mc_config, base_config.duration_years, rng2
        )
        np.testing.assert_array_equal(
            draws1["property_appreciation"],
            draws2["property_appreciation"],
        )
        np.testing.assert_array_equal(
            draws1["equity_growth"],
            draws2["equity_growth"],
        )


class TestSimulateSinglePath:
    """Tests for _simulate_single_path."""

    @pytest.fixture()
    def base_config(self):
        """Return a standard SimulationConfig.

        Returns
        -------
        SimulationConfig
            A 10-year, $500k property configuration.

        Examples
        --------
        .. code-block:: python

            config = base_config

        """
        return SimulationConfig(
            duration_years=10,
            property_price=500000,
            down_payment_pct=20,
            mortgage_rate_annual=4.5,
            property_appreciation_annual=3.0,
            equity_growth_annual=7.0,
            monthly_rent=2000,
            rent_inflation_rate=0.03,
        )

    def test_output_shapes(self, base_config):
        """Test that output arrays have correct length."""
        n_years = base_config.duration_years
        n_months = n_years * 12
        # Constant rates = base config rates for every year
        prop_rates = np.full(n_years, 3.0)
        eq_rates = np.full(n_years, 7.0)
        rent_rates = np.full(n_years, 3.0)

        net_buy, net_rent = _simulate_single_path(
            base_config, prop_rates, eq_rates, rent_rates
        )
        assert net_buy.shape == (n_months + 1,)
        assert net_rent.shape == (n_months + 1,)

    def test_initial_values(self, base_config):
        """Test that initial net values are correct."""
        n_years = base_config.duration_years
        prop_rates = np.full(n_years, 3.0)
        eq_rates = np.full(n_years, 7.0)
        rent_rates = np.full(n_years, 3.0)

        net_buy, net_rent = _simulate_single_path(
            base_config, prop_rates, eq_rates, rent_rates
        )
        # At t=0: net_buy = home_value - down_payment - buyer_closing
        down_payment = 500000 * 0.20
        buyer_closing = 500000 * (base_config.closing_cost_buyer_pct / 100)
        expected_net_buy_0 = 500000 - down_payment - buyer_closing
        assert abs(net_buy[0] - expected_net_buy_0) < 1.0

        # At t=0: net_rent = down_payment - 0 rent
        assert abs(net_rent[0] - down_payment) < 1.0

    def test_consistency_with_deterministic_engine(self, base_config):
        """Test that constant-rate MC path matches deterministic engine.

        When all annual rates are constant (matching base_config),
        the MC single path should match the deterministic engine's
        net_buy and net_rent within a small tolerance. The tolerance
        accounts for the MC path applying seller closing costs and
        tax adjustments at the final step only, matching the
        deterministic engine's summary metrics (not the raw arrays).
        """
        det_results = deterministic_engine(base_config)
        n_years = base_config.duration_years
        prop_rates = np.full(n_years, base_config.property_appreciation_annual)
        eq_rates = np.full(n_years, base_config.equity_growth_annual)
        rent_rates = np.full(n_years, base_config.rent_inflation_rate * 100)

        net_buy, net_rent = _simulate_single_path(
            base_config, prop_rates, eq_rates, rent_rates
        )

        # Compare intermediate net values (before seller closing costs)
        # The MC path's net_buy[:-1] should match the deterministic
        # Net_Buy column (both exclude seller closing costs until end)
        det_net_buy = det_results.data["Net_Buy"].values
        det_net_rent = det_results.data["Net_Rent"].values

        # Intermediate months should match closely
        for m in [0, 12, 60, 119]:
            assert abs(net_buy[m] - det_net_buy[m]) < 100, (
                f"net_buy mismatch at month {m}: "
                f"MC={net_buy[m]:.2f}, det={det_net_buy[m]:.2f}"
            )
            assert abs(net_rent[m] - det_net_rent[m]) < 100, (
                f"net_rent mismatch at month {m}: "
                f"MC={net_rent[m]:.2f}, det={det_net_rent[m]:.2f}"
            )

        # Final net_buy includes seller closing costs + tax benefits
        # Should match deterministic final_net_buy_tax_adjusted
        assert abs(net_buy[-1] - det_results.final_net_buy_tax_adjusted) < 500, (
            f"Final net_buy mismatch: "
            f"MC={net_buy[-1]:.2f}, "
            f"det={det_results.final_net_buy_tax_adjusted:.2f}"
        )

        # Final net_rent should match exactly
        assert abs(net_rent[-1] - det_results.final_net_rent) < 100

    def test_varying_rates_affect_outcome(self, base_config):
        """Test that different rates produce different outcomes."""
        n_years = base_config.duration_years

        # Low appreciation, high equity growth
        prop_low = np.full(n_years, 1.0)
        eq_high = np.full(n_years, 12.0)
        rent_rates = np.full(n_years, 3.0)
        net_buy_low, net_rent_high = _simulate_single_path(
            base_config, prop_low, eq_high, rent_rates
        )

        # High appreciation, low equity growth
        prop_high = np.full(n_years, 8.0)
        eq_low = np.full(n_years, 2.0)
        net_buy_high, net_rent_low = _simulate_single_path(
            base_config, prop_high, eq_low, rent_rates
        )

        # When property appreciation is high + equity is low, buy should
        # do relatively better
        diff_buy_favored = net_buy_high[-1] - net_rent_low[-1]
        diff_rent_favored = net_buy_low[-1] - net_rent_high[-1]
        assert diff_buy_favored > diff_rent_favored

    def test_net_values_monotonicity_not_required(self, base_config):
        """Test that MC paths can be non-monotonic with volatile rates."""
        n_years = base_config.duration_years
        # Alternating boom/bust years
        prop_rates = np.array([10, -5] * (n_years // 2))
        eq_rates = np.full(n_years, 7.0)
        rent_rates = np.full(n_years, 3.0)

        net_buy, net_rent = _simulate_single_path(
            base_config, prop_rates, eq_rates, rent_rates
        )
        # Just verify it runs without error and produces valid output
        assert net_buy.shape == (n_years * 12 + 1,)
        assert not np.any(np.isnan(net_buy))
        assert not np.any(np.isnan(net_rent))
