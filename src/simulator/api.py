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
