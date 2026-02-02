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

__version__ = "0.1.0"

from .engine import calculate_scenarios
from .models import SimulationConfig, SimulationResults

__all__ = ["SimulationConfig", "SimulationResults", "calculate_scenarios"]
