"""Tests for the Plotly fan chart."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import plotly.graph_objects as go

from simulator.mc_visualization import create_fan_chart
from simulator.models import MonteCarloConfig
from simulator.monte_carlo import run_monte_carlo
from tests.test_models import make_config


def test_fan_chart_structure():
    res = run_monte_carlo(
        make_config(horizon_years=5), MonteCarloConfig(n_simulations=30)
    )
    fig = create_fan_chart(res)
    assert isinstance(fig, go.Figure)
    # 2 band fills (90% and 50%) + median line + zero reference = >= 4 traces
    assert len(fig.data) >= 4


def test_matplotlib_functions_are_gone():
    import simulator.mc_visualization as mcv

    assert not hasattr(mcv, "create_spaghetti_chart")
    assert not hasattr(mcv, "create_probability_chart")
