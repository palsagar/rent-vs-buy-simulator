"""Monte Carlo simulation engine for uncertainty analysis.

Provides a fully independent MC engine that reimplements the
financial math from ``engine.py`` with year-varying stochastic rates.
Does NOT call ``calculate_scenarios`` (except for sensitivity analysis).
"""

from __future__ import annotations

import numpy as np

from .models import (
    MonteCarloConfig,
    SimulationConfig,
)

# Floating-point tolerance for comparisons
_FLOAT_TOLERANCE = 1e-9


def _generate_annual_draws(
    base_config: SimulationConfig,
    mc_config: MonteCarloConfig,
    n_years: int,
    rng: np.random.Generator,
) -> dict[str, np.ndarray]:
    """Generate correlated annual rate draws for MC simulations.

    Produces arrays of annual rates for property appreciation, equity
    growth, and rent inflation. Property appreciation and equity growth
    are drawn from a bivariate normal with configurable correlation.
    Rent inflation is drawn independently and clamped to be >= 0.

    All rates are in percentage-point units (e.g. 3.0 means 3%).

    Parameters
    ----------
    base_config : SimulationConfig
        The base deterministic configuration. Mean rates are taken from
        ``property_appreciation_annual``, ``equity_growth_annual``, and
        ``rent_inflation_rate`` (converted from decimal to pct).
    mc_config : MonteCarloConfig
        Controls which parameters to randomize, their standard
        deviations, and the correlation.
    n_years : int
        Number of years (columns in the output arrays).
    rng : np.random.Generator
        NumPy random generator for reproducibility.

    Returns
    -------
    dict[str, np.ndarray]
        Dictionary with keys ``"property_appreciation"``,
        ``"equity_growth"``, ``"rent_inflation"``. Each value is a
        2D array of shape ``(n_simulations, n_years)`` in percentage
        points.

    Examples
    --------
    Generate draws for 100 simulations over 10 years:

    .. code-block:: python

        from simulator.monte_carlo import _generate_annual_draws
        from simulator.models import SimulationConfig, MonteCarloConfig

        config = SimulationConfig(
            duration_years=10, property_price=500000,
            down_payment_pct=20, mortgage_rate_annual=4.5,
            property_appreciation_annual=3.0,
            equity_growth_annual=7.0, monthly_rent=2000,
        )
        mc = MonteCarloConfig(n_simulations=100, seed=42)
        rng = np.random.default_rng(mc.seed)
        draws = _generate_annual_draws(config, mc, 10, rng)
        print(draws["property_appreciation"].shape)  # (100, 10)

    """
    n_sims = mc_config.n_simulations

    # Base rates in percentage points
    mu_prop = base_config.property_appreciation_annual
    mu_eq = base_config.equity_growth_annual
    # rent_inflation_rate is stored as decimal (0.03 = 3%)
    mu_rent = base_config.rent_inflation_rate * 100

    # --- Property appreciation and equity growth: correlated bivariate ---
    if mc_config.randomize_property_appreciation or mc_config.randomize_equity_growth:
        sigma_prop = (
            mc_config.property_appreciation_std
            if mc_config.randomize_property_appreciation
            else 0.0
        )
        sigma_eq = (
            mc_config.equity_growth_std if mc_config.randomize_equity_growth else 0.0
        )
        rho = mc_config.appreciation_equity_correlation

        # Covariance matrix for bivariate normal
        cov = np.array(
            [
                [sigma_prop**2, rho * sigma_prop * sigma_eq],
                [rho * sigma_prop * sigma_eq, sigma_eq**2],
            ]
        )
        mean = np.array([mu_prop, mu_eq])

        # Draw all (n_sims * n_years) pairs, then reshape
        raw = rng.multivariate_normal(mean, cov, size=(n_sims, n_years))
        prop_draws = raw[:, :, 0]
        eq_draws = raw[:, :, 1]
    else:
        # No randomization: constant base rates
        prop_draws = np.full((n_sims, n_years), mu_prop)
        eq_draws = np.full((n_sims, n_years), mu_eq)

    # Override with constant if specific param is not randomized
    if not mc_config.randomize_property_appreciation:
        prop_draws = np.full((n_sims, n_years), mu_prop)
    if not mc_config.randomize_equity_growth:
        eq_draws = np.full((n_sims, n_years), mu_eq)

    # --- Rent inflation: independent normal, clamped >= 0 ---
    if mc_config.randomize_rent_inflation:
        rent_draws = rng.normal(
            mu_rent, mc_config.rent_inflation_std, (n_sims, n_years)
        )
        # Clamp to non-negative (rent doesn't deflate)
        rent_draws = np.maximum(rent_draws, 0.0)
    else:
        rent_draws = np.full((n_sims, n_years), mu_rent)

    return {
        "property_appreciation": prop_draws,
        "equity_growth": eq_draws,
        "rent_inflation": rent_draws,
    }
