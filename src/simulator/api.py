"""HTTP API serialization layer for the simulation engine.

Converts JSON-friendly camelCase dicts to engine dataclasses and engine
results back to JSON-friendly dicts. All wire-format decisions live in
this module; the engine is never aware of the HTTP layer.
"""

from __future__ import annotations

from dataclasses import fields
from typing import Any

from .engine import calculate_scenarios
from .models import MonteCarloConfig, SimulationConfig
from .monte_carlo import run_monte_carlo


def _camel(name: str) -> str:
    """Convert snake_case field name to lowerCamelCase."""
    head, *tail = name.split("_")
    return head + "".join(part.title() for part in tail)


_CAMEL_TO_SNAKE: dict[str, str] = {
    _camel(f.name): f.name for f in fields(SimulationConfig)
}


def config_from_dict(payload: dict[str, Any]) -> SimulationConfig:
    """Build a validated ``SimulationConfig`` from a camelCase payload.

    Parameters
    ----------
    payload : dict[str, Any]
        JSON-decoded request body with camelCase keys matching
        ``SimulationConfig`` field names (e.g. ``horizonYears``).

    Returns
    -------
    SimulationConfig
        The validated configuration.

    Raises
    ------
    ValueError
        If an unknown field is present or a value fails dataclass
        validation.
    TypeError
        If a required field is missing.

    Examples
    --------
    .. code-block:: python

        from simulator.api import config_from_dict

        config = config_from_dict(
            {
                "horizonYears": 10,
                "propertyPrice": 500000,
                "downPaymentPct": 20,
                "mortgageRateAnnual": 6.5,
                "propertyAppreciationAnnual": 3.0,
                "equityGrowthAnnual": 7.0,
                "monthlyRent": 2400,
            }
        )

    """
    unknown = sorted(set(payload) - set(_CAMEL_TO_SNAKE))
    if unknown:
        raise ValueError(f"Unknown config field(s): {', '.join(unknown)}")
    kwargs = {_CAMEL_TO_SNAKE[key]: value for key, value in payload.items()}
    return SimulationConfig(**kwargs)


def config_to_dict(config: SimulationConfig) -> dict[str, Any]:
    """Serialize a ``SimulationConfig`` to a camelCase dict.

    Examples
    --------
    .. code-block:: python

        from simulator.api import config_from_dict, config_to_dict
        from tests.test_models import make_config

        config = make_config()
        assert config_from_dict(config_to_dict(config)) == config

    """
    return {_camel(f.name): getattr(config, f.name) for f in fields(config)}


def simulate_payload(config: SimulationConfig) -> dict[str, Any]:
    """Run the deterministic engine and serialize results for the wire.

    Parameters
    ----------
    config : SimulationConfig
        Validated simulation configuration.

    Returns
    -------
    dict[str, Any]
        JSON-ready dict with ``verdict`` (winner, difference,
        horizonYears), ``breakevenYear``, year-1 monthly costs,
        ``totals`` (ownership-cost components), and ``series`` (the
        monthly time series, each ``horizon_years * 12 + 1`` long).

    Examples
    --------
    .. code-block:: python

        from simulator.api import simulate_payload
        from tests.test_models import make_config

        payload = simulate_payload(make_config())
        payload["verdict"]["winner"] in ("buy", "rent")  # True

    """
    results = calculate_scenarios(config)
    df = results.data
    breakeven = results.breakeven_year
    return {
        "verdict": {
            "winner": "buy" if results.final_difference > 0 else "rent",
            "difference": results.final_difference,
            "horizonYears": config.horizon_years,
        },
        "breakevenYear": float(breakeven) if breakeven is not None else None,
        "monthlyMortgagePayment": results.monthly_mortgage_payment,
        "monthlyCostBuyYear1": results.monthly_cost_buy_year1,
        "monthlyCostRentYear1": results.monthly_cost_rent_year1,
        "totals": {
            "closingCostsBuyer": results.total_closing_costs_buyer,
            "closingCostsSeller": results.total_closing_costs_seller,
            "propertyTaxPaid": results.total_property_tax_paid,
            "insurancePaid": results.total_insurance_paid,
            "maintenancePaid": results.total_maintenance_paid,
            "taxSavings": results.total_tax_savings,
        },
        "series": {
            "year": df["Year"].tolist(),
            "homeValue": df["Home_Value"].tolist(),
            "equityValue": df["Equity_Value"].tolist(),
            "buyPortfolioValue": df["Buy_Portfolio_Value"].tolist(),
            "mortgageBalance": df["Mortgage_Balance"].tolist(),
            "outflowBuy": df["Outflow_Buy"].tolist(),
            "outflowRent": df["Outflow_Rent"].tolist(),
            "cashCommitted": df["Cash_Committed"].tolist(),
            "netBuy": df["Net_Buy"].tolist(),
            "netRent": df["Net_Rent"].tolist(),
        },
    }


def monte_carlo_payload(
    config: SimulationConfig, mc_config: MonteCarloConfig | None = None
) -> dict[str, Any]:
    """Run Monte Carlo analysis and serialize results for the wire.

    Parameters
    ----------
    config : SimulationConfig
        Validated base configuration.
    mc_config : MonteCarloConfig | None, optional
        MC settings; defaults to ``MonteCarloConfig()`` (500 sims, fixed
        seed 42, auto-calibrated stds per ADR-0003). Exposed for tests —
        HTTP endpoints never pass this argument (knobless by design).

    Returns
    -------
    dict[str, Any]
        JSON-ready dict with summary stats, yearly fan percentiles of
        the Buy-Rent difference, tornado sensitivity data, and
        ``nSimulations``.

    Examples
    --------
    .. code-block:: python

        from simulator.api import monte_carlo_payload
        from simulator.models import MonteCarloConfig
        from tests.test_models import make_config

        payload = monte_carlo_payload(
            make_config(), MonteCarloConfig(n_simulations=30, seed=7)
        )
        0.0 <= payload["buyWinsPct"] <= 100.0  # True

    """
    results = run_monte_carlo(config, mc_config or MonteCarloConfig())
    return {
        "buyWinsPct": float(results.buy_wins_pct),
        "medianDifference": float(results.median_difference),
        "p5Difference": float(results.p5_difference),
        "p95Difference": float(results.p95_difference),
        "yearAxis": results.year_arr.tolist(),
        "percentileLevels": results.percentile_levels,
        "differencePercentiles": results.difference_percentiles.tolist(),
        "tornado": {
            "params": results.sensitivity_params,
            "low": results.sensitivity_low.tolist(),
            "high": results.sensitivity_high.tolist(),
            "base": float(results.sensitivity_base),
        },
        "nSimulations": results.n_simulations,
    }
