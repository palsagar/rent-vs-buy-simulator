"""HTTP API serialization layer for the simulation engine.

Converts JSON-friendly camelCase dicts to engine dataclasses and engine
results back to JSON-friendly dicts. All wire-format decisions live in
this module; the engine is never aware of the HTTP layer.
"""

from __future__ import annotations

import math
from dataclasses import fields
from types import UnionType
from typing import Any, Literal, Union, get_args, get_origin, get_type_hints

from .engine import calculate_scenarios
from .models import MonteCarloConfig, SimulationConfig
from .monte_carlo import run_monte_carlo

_UNION_ORIGINS = frozenset({Union, UnionType})


def _camel(name: str) -> str:
    """Convert snake_case field name to lowerCamelCase."""
    head, *tail = name.split("_")
    return head + "".join(part.title() for part in tail)


_CAMEL_TO_SNAKE: dict[str, str] = {
    _camel(f.name): f.name for f in fields(SimulationConfig)
}

_TYPE_HINTS: dict[str, Any] = get_type_hints(SimulationConfig)


def _validate_value(name: str, value: Any, annotation: Any) -> Any:  # noqa: C901
    """Validate and coerce a JSON value against a field annotation.

    Parameters
    ----------
    name : str
        snake_case field name used in error messages.
    value : Any
        JSON-decoded value from the request payload.
    annotation : Any
        Type annotation from ``SimulationConfig``.

    Returns
    -------
    Any
        The coerced value (e.g. ``10.0`` becomes ``10`` for ``int``).

    Raises
    ------
    ValueError
        If the value does not match the annotated type.
    TypeError
        If the annotation is not a supported scalar type.

    Examples
    --------
    .. code-block:: python

        from simulator.api import _validate_value

        assert _validate_value("horizon_years", 10.0, int) == 10
        _validate_value("horizon_years", 10.5, int)  # raises ValueError

    """
    origin = get_origin(annotation)
    args = get_args(annotation)

    # ``float | None`` is the only nullable field.
    if origin in _UNION_ORIGINS and type(None) in args:
        if value is None:
            return None
        non_none = [a for a in args if a is not type(None)]
        return _validate_value(name, value, non_none[0])

    if annotation is bool:
        if not isinstance(value, bool):
            raise ValueError(f"{name} must be a boolean")
        return value

    if annotation in (int, float):
        label = "an integer" if annotation is int else "a number"
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{name} must be {label}")
        # Reject NaN/±Infinity: json.loads accepts these bareword tokens and
        # they would silently poison the engine's arithmetic.
        if not math.isfinite(value):
            raise ValueError(f"{name} must be a finite number")
        if annotation is int and value != int(value):
            raise ValueError(f"{name} must be an integer")
        return annotation(value)

    if annotation is str or origin is Literal:
        if not isinstance(value, str):
            raise ValueError(f"{name} must be a string")
        return value

    # Every SimulationConfig field is scalar by design
    # (docs/multi-region-spec.md 3 rejects list-shaped primitives). A
    # non-scalar field would otherwise be returned unvalidated.
    raise TypeError(f"{name}: unsupported field annotation {annotation!r}")


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
        If an unknown field is present, a value has the wrong JSON
        type for its field annotation, or a value fails dataclass
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
    kwargs: dict[str, Any] = {}
    for key, value in payload.items():
        snake = _CAMEL_TO_SNAKE[key]
        kwargs[snake] = _validate_value(snake, value, _TYPE_HINTS[snake])
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
            "interestPaid": results.total_mortgage_interest_paid,
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
