"""Monte Carlo simulation engine for uncertainty analysis.

Feeds year-varying stochastic rates into the SAME ``_net_value_series``
core used by the deterministic engine, so MC can never drift from the
deterministic verdict (ADR-0001, ADR-0003).
"""

from __future__ import annotations

import math

import numpy as np

from .engine import _net_value_series
from .models import (
    MonteCarloConfig,
    MonteCarloResults,
    SimulationConfig,
)

# Smallest value a positive-only field may be perturbed to. A NUMERIC
# safety floor, unrelated to _UI_MAXIMUM below, which is a per-field UI
# policy -- the names are not an antonym pair. The proportional levy
# delta is checked against this same value so guard and clamp cannot
# drift apart.
_POSITIVE_FIELD_FLOOR = 0.001

# Relative swing applied to whichever field carries a region's property
# levy. Calibrated so the US ad-valorem base of 1.2 keeps its historical
# absolute delta of exactly 0.5.
_LEVY_RELATIVE_DELTA = 0.5 / 1.2

# Fraction of the verdict below which a tornado swing is float noise
# rather than signal. Well above IEEE-754 double precision (~1e-16
# relative) and far below any swing a user could read off the chart.
_NEGLIGIBLE_SWING_RATIO = 1e-6

# Fields whose tornado delta is an ANNUAL standard deviation.
#
# That sigma is what run_monte_carlo needs: it generates a fresh draw
# every year, so year-to-year dispersion is exactly the right scale. The
# tornado asks a different question. It shifts the deterministic engine's
# single long-run average and holds it for the whole horizon, so the
# relevant uncertainty is the uncertainty of that AVERAGE -- the standard
# error, sigma / sqrt(horizon).
#
# Using the raw annual sigma conflated the two. At 22 years it moved a 9%
# equity CAGR to 24% and held it there, compounding a 150k initial outlay
# into ~17M and producing a bar an order of magnitude wider than the rest
# of the chart combined. The standard error at that horizon is 3.2pp, not
# 15pp.
#
# The remaining perturbations are fixed absolute steps (a 100k price
# move, 5pp of down payment), not standard deviations, so sqrt(horizon)
# does not apply to them.
_STOCHASTIC_FIELDS = frozenset(
    {
        "property_appreciation_annual",
        "equity_growth_annual",
        "rent_inflation_rate",
    }
)

# Highest value the UI lets a user set for each perturbed field, in
# STORED units. With the standard-error delta above, a perturbation
# rarely reaches this -- it is the guard for a base that is already at or
# beyond the slider maximum, which the engine accepts (down payment is
# valid to 100, the slider stops at 50) and the API will hand over.
#
# The LOW side is deliberately NOT capped at the slider minimum. A crash
# is a real outcome the model must be able to represent even though the
# UI will not let you type a negative growth rate -- see
# test_tornado_low_uses_negative_growth_rate, which pins that.
#
# Mirrors fields.js. Kept honest by tests/test_tornado_bounds.py, which
# parses the slider maxima out of it rather than trusting this copy.
_UI_MAXIMUM = {
    "property_appreciation_annual": 10.0,
    "equity_growth_annual": 15.0,
    "rent_inflation_rate": 0.1,
    "property_price": 2_000_000.0,
    "down_payment_pct": 50.0,
    "monthly_rent": 10_000.0,
    "mortgage_rate_annual": 10.0,
    "property_tax_rate": 5.0,
    "annual_property_levy": 10_000.0,
}


def _is_negligible_against(swing: float, reference: float) -> bool:
    """Whether ``swing`` is rounding noise at the scale of ``reference``.

    Absolute tolerances cannot serve here: the verdict spans roughly
    1e3 to 1e11 across the slider ranges, so a fixed epsilon is either
    too tight at the top or meaningless at the bottom.

    Parameters
    ----------
    swing : float
        Difference between the high and low perturbation outcomes.
    reference : float
        Unperturbed verdict the swing is judged against.

    Returns
    -------
    bool
        True when ``swing`` is negligible at that scale.

    Examples
    --------
    .. code-block:: python

        from simulator.monte_carlo import _is_negligible_against

        _is_negligible_against(6.1e-05, 2.6e11)   # True
        _is_negligible_against(9048.0, 134799.0)  # False

    """
    return abs(swing) <= _NEGLIGIBLE_SWING_RATIO * max(1.0, abs(reference))


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
            horizon_years=10, property_price=500000,
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
    """Simulate one MC path by feeding stochastic monthly rates to the
    shared engine core — no duplicated financial math (ADR-0001).

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
        ``(net_buy, net_rent)`` liquidation-priced Net Value series,
        each of shape ``(n_months + 1,)``.

    Examples
    --------
    Simulate a single path with constant rates:

    .. code-block:: python

        import numpy as np
        from simulator.monte_carlo import _simulate_single_path
        from simulator.models import SimulationConfig

        config = SimulationConfig(
            horizon_years=10, property_price=500000,
            down_payment_pct=20, mortgage_rate_annual=4.5,
            property_appreciation_annual=3.0,
            equity_growth_annual=7.0, monthly_rent=2000,
        )
        prop = np.full(10, 3.0)
        eq = np.full(10, 7.0)
        rent = np.full(10, 3.0)
        net_buy, net_rent = _simulate_single_path(config, prop, eq, rent)

    """
    # Expand annual percentage draws to per-month decimal rates
    prop_m = np.repeat(annual_prop_rates / 100 / 12, 12)
    eq_m = np.repeat(annual_equity_rates / 100 / 12, 12)
    rent_m = np.repeat(annual_rent_rates / 100 / 12, 12)
    series = _net_value_series(config, prop_m, eq_m, rent_m)
    return series["net_buy"], series["net_rent"]


def _compute_sensitivity(  # noqa: C901
    base_config: SimulationConfig,
) -> tuple[list[str], np.ndarray, np.ndarray, float]:
    """Compute one-at-a-time sensitivity for tornado chart.

    Uses the EXISTING deterministic ``calculate_scenarios`` engine
    (not the MC path simulator). Perturbs 9 candidate parameters by
    +/- 1 standard deviation and measures the effect on the Verdict
    (``final_difference``, i.e. net_buy - net_rent).

    Fewer than 9 bars are returned in general. The two levy fields --
    ad-valorem ``property_tax_rate`` and flat ``annual_property_levy``
    -- take a RELATIVE swing rather than an absolute one, and each is
    skipped at a zero base, so a region gets whichever levy unit its
    bundle uses and never both. A flat levy that is occupier-borne
    cancels out of the Verdict entirely and is skipped too.

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
            horizon_years=10, property_price=500000,
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
        return res.final_difference

    # Base case
    base_value = _run_with_override()

    # Parameters to perturb: (display_name, config_field, delta)
    # Delta is +-1 "standard deviation" in the same units as the field.
    # The first three deltas mirror the fixed MC calibration so there is a
    # single source of truth (stds are in percentage points; rent_inflation_rate
    # is a decimal, hence /100).
    mc_defaults = MonteCarloConfig()
    perturbations = [
        (
            "Property Appreciation",
            "property_appreciation_annual",
            mc_defaults.property_appreciation_std,
        ),
        ("Equity Growth", "equity_growth_annual", mc_defaults.equity_growth_std),
        ("Rent Inflation", "rent_inflation_rate", mc_defaults.rent_inflation_std / 100),
        ("Property Price", "property_price", 100000),
        ("Down Payment %", "down_payment_pct", 5.0),
        ("Monthly Rent", "monthly_rent", 500),
        ("Property Tax Rate", "property_tax_rate", 0.5),
        # Both are skipped at a zero base, so a region gets whichever one
        # its bundle actually uses and never two levy bars at once.
        ("Property Levy (flat)", "annual_property_levy", 0.0),
        ("Mortgage Rate", "mortgage_rate_annual", 1.0),
    ]

    param_names: list[str] = []
    low_vals: list[float] = []
    high_vals: list[float] = []

    for display_name, field, delta in perturbations:
        base_val = getattr(base_config, field)

        # A levy delta must scale with its own base, and BOTH levy
        # representations take the same relative swing: they are one
        # economic quantity in different units -- ad-valorem for US/NL, a
        # flat cost-indexed amount for FR/DE/UK -- so a region's measured
        # sensitivity must not depend on which unit its bundle happens to
        # use. An absolute delta cannot do this: +-0.5pp on NL's
        # folded-EWF 0.2815 is a +-178% swing implying WOZ regimes it
        # does not have. _LEVY_RELATIVE_DELTA is calibrated so the US
        # base of 1.2 keeps its historical delta of exactly 0.5.
        # An annual sigma is the dispersion of ONE year. The tornado holds
        # its shift for the whole horizon, so the uncertainty that applies
        # is that of the long-run average: the standard error.
        if field in _STOCHASTIC_FIELDS:
            delta = delta / math.sqrt(base_config.horizon_years)

        if field in ("property_tax_rate", "annual_property_levy"):
            delta = base_val * _LEVY_RELATIVE_DELTA
            # Skip whenever the low side would hit the floor below. That
            # covers a region carrying its levy in the OTHER field (base
            # 0) and also the near-zero band: a floored low side
            # represents a HIGHER value than the base, and below
            # 0.000706 it exceeds the high side outright, rendering the
            # bar inverted. Reachable from the UI -- fields.js ships
            # propertyTaxRate with step 0.0005 from a min of 0.
            if base_val - delta < _POSITIVE_FIELD_FLOOR:
                continue

        # Low perturbation (subtract delta). Growth rates may legitimately
        # go negative; floor them just above -100% so the monthly compounding
        # factor stays positive. Positive-only fields keep the 0.001 floor.
        if field in ("property_appreciation_annual", "equity_growth_annual"):
            low_override = max(base_val - delta, -99.0)
        else:
            low_override = max(base_val - delta, _POSITIVE_FIELD_FLOOR)
        # Clamp down_payment_pct to [5, 100]
        if field == "down_payment_pct":
            low_override = max(low_override, 5.0)
        # Clamp rent_inflation_rate to [0, 1]
        if field == "rent_inflation_rate":
            low_override = max(low_override, 0.0)

        # High perturbation (add delta), never past what the UI can set.
        #
        # The outer max() is load-bearing, not defensive. The engine
        # accepts bases ABOVE the slider maximum (down_payment_pct is
        # valid to 100, the slider stops at 50) and a config can arrive
        # that way through the API. Clamping to the ceiling alone would
        # then put the "higher" bar BELOW the base -- and below the
        # "lower" bar -- so both bars land on the same side of the pivot
        # and the one labelled "higher" shows the outcome of a DECREASE.
        # It also let a proportional levy delta land low and high on the
        # ceiling together, collapsing the swing to zero so the
        # negligible-swing guard silently deleted a real bar.
        #
        # At base == ceiling this leaves the high half zero-width, which
        # is the honest reading: at the maximum the parameter can only
        # go down. The bar still renders at full width from the low side.
        high_override = base_val + delta
        ceiling = _UI_MAXIMUM.get(field)
        if ceiling is not None:
            high_override = max(base_val, min(high_override, ceiling))

        try:
            val_low = _run_with_override(**{field: low_override})
            val_high = _run_with_override(**{field: high_override})
            # An occupier-borne levy lands in BOTH arms and cancels out
            # of Buy - Rent, so perturbing it moves nothing (UK, DE). The
            # levy is the only tornado parameter that can be structurally
            # neutral by design, and a zero-width bar reads as a broken
            # chart rather than as "this does not matter". Drop it, but
            # only on measured equality: with the interest deduction on,
            # an occupier-borne levy DOES reach the verdict through the
            # deductible base, and then the bar is real and stays.
            #
            # The comparison must be RELATIVE. Cancellation is algebraic,
            # not bit-exact -- (a + levy) - (b + levy) carries rounding
            # that scales with the verdict, which reaches 1e11 at the
            # slider ceilings. An absolute 1e-9 leaked a zero-width bar
            # in 86 of 324 swept configs, residual up to 6.1e-05.
            if field == "annual_property_levy" and _is_negligible_against(
                val_high - val_low, base_value
            ):
                continue
            param_names.append(display_name)
            low_vals.append(val_low)
            high_vals.append(val_high)
        except ValueError:
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
            horizon_years=10, property_price=500000,
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
    n_years = base_config.horizon_years
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

    # Chart data uses the same liquidation-priced series as summary stats
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
