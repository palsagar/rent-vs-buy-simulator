"""Real Estate vs. Equity Simulation Engine."""

__version__ = "0.1.0"

from .engine import calculate_scenarios
from .models import SimulationConfig, SimulationResults

__all__ = ["SimulationConfig", "SimulationResults", "calculate_scenarios"]
