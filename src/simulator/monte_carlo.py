"""Monte Carlo simulation engine for uncertainty analysis.

Provides a fully independent MC engine that reimplements the
financial math from ``engine.py`` with year-varying stochastic rates.
Does NOT call ``calculate_scenarios`` (except for sensitivity analysis).
"""

from __future__ import annotations

import numpy as np
import numpy_financial as npf

from .models import (
    MonteCarloConfig,
    MonteCarloResults,
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


def _simulate_single_path(
    config: SimulationConfig,
    annual_prop_rates: np.ndarray,
    annual_equity_rates: np.ndarray,
    annual_rent_rates: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Simulate one MC path with year-varying rates.

    Reimplements the full financial math from ``engine.py`` using
    per-year stochastic rates instead of fixed annual rates. The
    mortgage is still fixed-rate (amortization doesn't change).

    Final ``net_buy[-1]`` includes: seller closing costs (subtracted),
    cumulative tax savings (added), and capital gains tax saved (added).
    Intermediate values ``net_buy[0..n_months-1]`` do NOT include
    seller closing costs (same convention as the deterministic engine's
    ``Net_Buy`` column).

    Parameters
    ----------
    config : SimulationConfig
        Base configuration (property price, down payment, mortgage rate,
        closing costs, tax settings, etc.).
    annual_prop_rates : np.ndarray
        Property appreciation rate per year in percentage points.
        Shape: ``(n_years,)``.
    annual_equity_rates : np.ndarray
        Equity growth rate per year in percentage points.
        Shape: ``(n_years,)``.
    annual_rent_rates : np.ndarray
        Rent inflation rate per year in percentage points.
        Shape: ``(n_years,)``.

    Returns
    -------
    tuple[np.ndarray, np.ndarray]
        ``(net_buy, net_rent)`` — each of shape ``(n_months + 1,)``.

    Examples
    --------
    Simulate a single path with constant rates:

    .. code-block:: python

        import numpy as np
        from simulator.monte_carlo import _simulate_single_path
        from simulator.models import SimulationConfig

        config = SimulationConfig(
            duration_years=10, property_price=500000,
            down_payment_pct=20, mortgage_rate_annual=4.5,
            property_appreciation_annual=3.0,
            equity_growth_annual=7.0, monthly_rent=2000,
        )
        prop = np.full(10, 3.0)
        eq = np.full(10, 7.0)
        rent = np.full(10, 3.0)
        net_buy, net_rent = _simulate_single_path(
            config, prop, eq, rent
        )

    """
    n_years = config.duration_years
    n_months = n_years * 12

    # --- Fixed mortgage parameters (don't vary with stochastic rates) ---
    down_payment = config.property_price * (config.down_payment_pct / 100)
    buyer_closing = config.property_price * (config.closing_cost_buyer_pct / 100)
    initial_outflow = down_payment + buyer_closing
    loan_amount = config.property_price - down_payment
    fixed_monthly_rate = (config.mortgage_rate_annual / 100) / 12

    # Monthly mortgage payment (fixed for the life of the loan)
    if abs(loan_amount) < _FLOAT_TOLERANCE:
        monthly_payment = 0.0
    elif abs(fixed_monthly_rate) < _FLOAT_TOLERANCE:
        monthly_payment = loan_amount / n_months if n_months > 0 else 0.0
    else:
        monthly_payment = -npf.pmt(fixed_monthly_rate, n_months, loan_amount)

    # --- Allocate arrays ---
    home_value = np.zeros(n_months + 1)
    equity_value = np.zeros(n_months + 1)
    mortgage_balance = np.zeros(n_months + 1)
    cum_outflow_buy = np.zeros(n_months + 1)
    cum_outflow_rent = np.zeros(n_months + 1)
    monthly_interest = np.zeros(n_months + 1)
    monthly_property_tax = np.zeros(n_months + 1)
    rent_at_month = np.zeros(n_months + 1)

    # --- Initial conditions ---
    home_value[0] = config.property_price
    equity_value[0] = down_payment
    mortgage_balance[0] = loan_amount
    cum_outflow_buy[0] = initial_outflow
    cum_outflow_rent[0] = 0.0
    rent_at_month[0] = config.monthly_rent

    # Cost inflation is fixed (not stochastic)
    monthly_cost_inflation = config.cost_inflation_rate / 12

    # Precompute ongoing cost rates
    monthly_prop_tax_rate = (config.property_tax_rate / 100) / 12
    monthly_maint_rate = (config.annual_maintenance_pct / 100) / 12

    # --- Month-by-month simulation ---
    for m in range(1, n_months + 1):
        yr = (m - 1) // 12  # Year index (0-based)

        # Monthly rates from annual draws (percentage to decimal, / 12)
        monthly_prop_rate = annual_prop_rates[yr] / 100 / 12
        monthly_eq_rate = annual_equity_rates[yr] / 100 / 12
        monthly_rent_rate = annual_rent_rates[yr] / 100 / 12

        # Property appreciation
        home_value[m] = home_value[m - 1] * (1 + monthly_prop_rate)

        # Equity portfolio growth
        equity_value[m] = equity_value[m - 1] * (1 + monthly_eq_rate)

        # Mortgage amortization (fixed rate, not stochastic)
        if mortgage_balance[m - 1] > _FLOAT_TOLERANCE:
            interest = mortgage_balance[m - 1] * fixed_monthly_rate
            principal = monthly_payment - interest
            mortgage_balance[m] = max(0.0, mortgage_balance[m - 1] - principal)
            monthly_interest[m] = interest
        else:
            mortgage_balance[m] = 0.0
            monthly_interest[m] = 0.0

        # Rent with year-varying inflation
        rent_at_month[m] = rent_at_month[m - 1] * (1 + monthly_rent_rate)

        # Ongoing homeownership costs use previous-month values
        # (shifted convention matching engine.py: outflow at t includes
        # costs through end of month t-1)
        cost_factor_prev = (1 + monthly_cost_inflation) ** (m - 1)
        prop_tax = home_value[m - 1] * monthly_prop_tax_rate
        insurance = (config.annual_home_insurance / 12) * cost_factor_prev
        maintenance = (home_value[m - 1] * monthly_maint_rate) * cost_factor_prev

        monthly_property_tax[m - 1] = prop_tax

        # Cumulative outflows
        cum_outflow_buy[m] = (
            cum_outflow_buy[m - 1]
            + monthly_payment
            + prop_tax
            + insurance
            + maintenance
        )
        # Rent outflow: pay rent_at_month[m-1] during month m-1
        cum_outflow_rent[m] = cum_outflow_rent[m - 1] + rent_at_month[m - 1]

    # Record final month's property tax for the tax savings loop
    monthly_property_tax[n_months] = home_value[n_months] * monthly_prop_tax_rate

    # --- Tax savings (annual computation, same logic as engine.py) ---
    tax_rate = config.tax_bracket / 100
    cumulative_tax_savings = 0.0
    if config.enable_mortgage_deduction and tax_rate > _FLOAT_TOLERANCE:
        for yr in range(n_years):
            # engine.py uses 1-based years: yr_start = yr*12 - 11,
            # yr_end = yr*12.  Translating to 0-based: year k covers
            # months k*12+1 .. (k+1)*12.
            yr_start = yr * 12 + 1
            yr_end = (yr + 1) * 12
            year_interest = float(np.sum(monthly_interest[yr_start : yr_end + 1]))
            year_prop_tax = float(np.sum(monthly_property_tax[yr_start : yr_end + 1]))
            deductible_prop_tax = min(year_prop_tax, config.salt_cap)
            cumulative_tax_savings += (year_interest + deductible_prop_tax) * tax_rate

    # --- Capital gains exclusion ---
    capital_gains_tax_saved = 0.0
    if config.enable_capital_gains_exclusion:
        capital_gain = home_value[-1] - config.property_price
        if capital_gain > config.capital_gains_exemption_limit:
            taxable_gain = capital_gain - config.capital_gains_exemption_limit
            cg_rate = 0.20 if config.tax_bracket >= 35 else 0.15
            capital_gains_tax_saved = taxable_gain * cg_rate

    # --- Seller closing costs ---
    seller_closing = home_value[-1] * (config.closing_cost_seller_pct / 100)

    # --- Net value arrays ---
    net_buy = home_value - cum_outflow_buy
    net_rent = equity_value - cum_outflow_rent

    # Apply end-of-period adjustments to the final month only
    net_buy[-1] = (
        net_buy[-1] - seller_closing + cumulative_tax_savings + capital_gains_tax_saved
    )

    return net_buy, net_rent


def _compute_sensitivity(
    base_config: SimulationConfig,
) -> tuple[list[str], np.ndarray, np.ndarray, float]:
    """Compute one-at-a-time sensitivity for tornado chart.

    Uses the EXISTING deterministic ``calculate_scenarios`` engine
    (not the MC path simulator). Perturbs 8 key parameters by +/- 1
    standard deviation and measures the effect on the tax-adjusted
    difference (net_buy_tax_adjusted - net_rent).

    Parameters
    ----------
    base_config : SimulationConfig
        The base deterministic configuration.

    Returns
    -------
    tuple[list[str], np.ndarray, np.ndarray, float]
        ``(param_names, low_values, high_values, base_value)`` sorted
        by descending impact range ``abs(high - low)``.

    Examples
    --------
    Compute sensitivity for a base configuration:

    .. code-block:: python

        from simulator.monte_carlo import _compute_sensitivity
        from simulator.models import SimulationConfig

        config = SimulationConfig(
            duration_years=10, property_price=500000,
            down_payment_pct=20, mortgage_rate_annual=4.5,
            property_appreciation_annual=3.0,
            equity_growth_annual=7.0, monthly_rent=2000,
        )
        params, low, high, base = _compute_sensitivity(config)
        for p, lo, hi in zip(params, low, high):
            print(f"{p}: [{lo:,.0f}, {hi:,.0f}]")

    """
    from dataclasses import asdict

    from .engine import calculate_scenarios

    def _run_with_override(
        **overrides: float,
    ) -> float:
        """Run deterministic engine with parameter overrides."""
        base_dict = asdict(base_config)
        base_dict.update(overrides)
        cfg = SimulationConfig(**base_dict)
        res = calculate_scenarios(cfg)
        return res.final_net_buy_tax_adjusted - res.final_net_rent

    # Base case
    base_value = _run_with_override()

    # Parameters to perturb: (display_name, config_field, delta)
    # Delta is +-1 "standard deviation" in the same units as the field
    perturbations = [
        (
            "Property Appreciation",
            "property_appreciation_annual",
            5.0,
        ),
        ("Equity Growth", "equity_growth_annual", 5.0),
        ("Rent Inflation", "rent_inflation_rate", 0.015),
        ("Property Price", "property_price", 100000),
        ("Down Payment %", "down_payment_pct", 5.0),
        ("Monthly Rent", "monthly_rent", 500),
        ("Property Tax Rate", "property_tax_rate", 0.5),
        ("Mortgage Rate", "mortgage_rate_annual", 1.0),
    ]

    param_names: list[str] = []
    low_vals: list[float] = []
    high_vals: list[float] = []

    for display_name, field, delta in perturbations:
        base_val = getattr(base_config, field)

        # Low perturbation (subtract delta)
        low_override = max(base_val - delta, 0.001)
        # Clamp down_payment_pct to [5, 100]
        if field == "down_payment_pct":
            low_override = max(low_override, 5.0)
        # Clamp rent_inflation_rate to [0, 1]
        if field == "rent_inflation_rate":
            low_override = max(low_override, 0.0)

        # High perturbation (add delta)
        high_override = base_val + delta
        if field == "down_payment_pct":
            high_override = min(high_override, 100.0)
        if field == "rent_inflation_rate":
            high_override = min(high_override, 1.0)

        try:
            val_low = _run_with_override(**{field: low_override})
            val_high = _run_with_override(**{field: high_override})
            param_names.append(display_name)
            low_vals.append(val_low)
            high_vals.append(val_high)
        except (ValueError, Exception):
            # Skip if perturbation produces invalid config
            continue

    # Sort by descending impact range
    low_arr = np.array(low_vals)
    high_arr = np.array(high_vals)
    impact_range = np.abs(high_arr - low_arr)
    sort_idx = np.argsort(-impact_range)

    sorted_names = [param_names[i] for i in sort_idx]
    sorted_low = low_arr[sort_idx]
    sorted_high = high_arr[sort_idx]

    return sorted_names, sorted_low, sorted_high, base_value


def run_monte_carlo(
    base_config: SimulationConfig,
    mc_config: MonteCarloConfig,
) -> MonteCarloResults:
    """Run the full Monte Carlo uncertainty analysis.

    Generates correlated annual rate draws, simulates each path,
    collects results into 2D arrays, computes percentiles and summary
    statistics, and runs OAT sensitivity analysis.

    Parameters
    ----------
    base_config : SimulationConfig
        The base deterministic configuration.
    mc_config : MonteCarloConfig
        Monte Carlo settings (n_simulations, stds, correlation, seed).

    Returns
    -------
    MonteCarloResults
        Full results including paths, percentiles, summary stats,
        and sensitivity data.

    Examples
    --------
    Run a Monte Carlo simulation:

    .. code-block:: python

        from simulator.monte_carlo import run_monte_carlo
        from simulator.models import SimulationConfig, MonteCarloConfig

        config = SimulationConfig(
            duration_years=10, property_price=500000,
            down_payment_pct=20, mortgage_rate_annual=4.5,
            property_appreciation_annual=3.0,
            equity_growth_annual=7.0, monthly_rent=2000,
        )
        mc_config = MonteCarloConfig(n_simulations=500, seed=42)
        results = run_monte_carlo(config, mc_config)
        print(f"Buy wins {results.buy_wins_pct:.1f}% of the time")
        print(f"Median difference: ${results.median_difference:,.0f}")

    """
    n_sims = mc_config.n_simulations
    n_years = base_config.duration_years
    n_months = n_years * 12
    n_points = n_months + 1

    # Seeded RNG for reproducibility
    rng = np.random.default_rng(mc_config.seed)

    # Generate year-by-year stochastic rates
    draws = _generate_annual_draws(base_config, mc_config, n_years, rng)

    # Allocate result arrays
    all_net_buy = np.zeros((n_sims, n_points))
    all_net_rent = np.zeros((n_sims, n_points))

    # Simulate each path
    for i in range(n_sims):
        net_buy, net_rent = _simulate_single_path(
            config=base_config,
            annual_prop_rates=draws["property_appreciation"][i],
            annual_equity_rates=draws["equity_growth"][i],
            annual_rent_rates=draws["rent_inflation"][i],
        )
        all_net_buy[i] = net_buy
        all_net_rent[i] = net_rent

    # Compute differences
    all_diffs = all_net_buy - all_net_rent
    final_diffs = all_diffs[:, -1]

    # Time axis
    year_arr = np.arange(n_points) / 12

    # Percentiles
    percentile_levels = [5, 25, 50, 75, 95]
    diff_percentiles = np.percentile(all_diffs, percentile_levels, axis=0)

    # Summary statistics
    buy_wins_pct = float(np.mean(final_diffs > 0) * 100)
    median_diff = float(np.median(final_diffs))
    p5_diff = float(np.percentile(final_diffs, 5))
    p95_diff = float(np.percentile(final_diffs, 95))

    # Sensitivity analysis (uses deterministic engine, not MC)
    sens_params, sens_low, sens_high, sens_base = _compute_sensitivity(base_config)

    return MonteCarloResults(
        final_net_buy=all_net_buy[:, -1],
        final_net_rent=all_net_rent[:, -1],
        final_differences=final_diffs,
        all_net_buy=all_net_buy,
        all_net_rent=all_net_rent,
        all_differences=all_diffs,
        year_arr=year_arr,
        percentile_levels=percentile_levels,
        difference_percentiles=diff_percentiles,
        buy_wins_pct=buy_wins_pct,
        median_difference=median_diff,
        p5_difference=p5_diff,
        p95_difference=p95_diff,
        sensitivity_params=sens_params,
        sensitivity_low=sens_low,
        sensitivity_high=sens_high,
        sensitivity_base=sens_base,
        base_config=base_config,
        mc_config=mc_config,
        n_simulations=n_sims,
    )
