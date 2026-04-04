"""Real Estate vs. Equity Simulation Engine.

This package provides tools for comparing two financial strategies:
buying property vs. renting and investing in equities. It includes
data models, calculation engine, and visualization tools.

Examples
--------
Basic usage:

.. code-block:: python

    from simulator import SimulationConfig, calculate_scenarios

    config = SimulationConfig(
        duration_years=30,
        property_price=500000,
        down_payment_pct=20,
        mortgage_rate_annual=4.5,
        property_appreciation_annual=3,
        equity_growth_annual=7,
        monthly_rent=2000
    )

    results = calculate_scenarios(config)
    print(f"Final difference: ${results.final_difference:,.0f}")

"""

from importlib.metadata import version as _get_version

__version__ = _get_version("rent-vs-buy-simulator")

from .engine import _find_breakeven, _is_close, _is_close_to_zero, calculate_scenarios
from .models import SimulationConfig, SimulationResults

__all__ = [
    "SimulationConfig",
    "SimulationResults",
    "_find_breakeven",
    "_is_close",
    "_is_close_to_zero",
    "calculate_scenarios",
]
