"""Monte Carlo visualization module.

Provides Plotly charts for MC uncertainty analysis: a percentile fan
chart and a tornado (sensitivity) chart.
"""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go

from .models import MonteCarloResults


def create_fan_chart(mc_results: MonteCarloResults) -> go.Figure:
    """Percentile fan of the Buy - Rent Net Value difference over time.

    Median line with 50% and 90% bands; where the bands sit relative
    to the zero line is the visual answer to "how sure is this?".

    Parameters
    ----------
    mc_results : MonteCarloResults
        MC results containing ``year_arr``, ``difference_percentiles``,
        and ``percentile_levels`` (must include 5, 25, 50, 75, 95).

    Returns
    -------
    go.Figure
        Plotly Figure with a 90% band, a 50% band, a median line, and
        a zero reference line.

    Examples
    --------
    Create a fan chart:

    .. code-block:: python

        from simulator.mc_visualization import create_fan_chart

        fig = create_fan_chart(mc_results)
        fig.show()

    """
    years = mc_results.year_arr
    p = {
        level: mc_results.difference_percentiles[i]
        for i, level in enumerate(mc_results.percentile_levels)
    }
    fig = go.Figure()
    # 90% band (p5-p95), drawn first so the 50% band sits on top
    fig.add_trace(go.Scatter(x=years, y=p[95], line={"width": 0}, showlegend=False))
    fig.add_trace(
        go.Scatter(
            x=years,
            y=p[5],
            fill="tonexty",
            line={"width": 0},
            fillcolor="rgba(99, 110, 250, 0.15)",
            name="90% of futures",
        )
    )
    fig.add_trace(go.Scatter(x=years, y=p[75], line={"width": 0}, showlegend=False))
    fig.add_trace(
        go.Scatter(
            x=years,
            y=p[25],
            fill="tonexty",
            line={"width": 0},
            fillcolor="rgba(99, 110, 250, 0.35)",
            name="50% of futures",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=years,
            y=p[50],
            name="Median",
            line={"color": "#636efa", "width": 2},
        )
    )
    fig.add_hline(y=0, line_dash="dash", line_color="gray")
    fig.update_layout(
        title="Buy vs. Rent advantage across simulated futures",
        xaxis_title="Years",
        yaxis_title="Buy advantage ($)",
        hovermode="x unified",
    )
    return fig


def create_tornado_chart(mc_results: MonteCarloResults) -> go.Figure:
    """Create a tornado (sensitivity) chart.

    Horizontal bar chart showing how each parameter's +/- 1 std
    perturbation affects the final buy-vs-rent difference. Sorted by
    impact range (widest at top).

    Parameters
    ----------
    mc_results : MonteCarloResults
        MC results containing ``sensitivity_params``,
        ``sensitivity_low``, ``sensitivity_high``, and
        ``sensitivity_base``.

    Returns
    -------
    go.Figure
        Plotly Figure with horizontal bar chart.

    Examples
    --------
    Create a tornado chart:

    .. code-block:: python

        from simulator.mc_visualization import create_tornado_chart

        fig = create_tornado_chart(mc_results)
        fig.show()

    """
    params = mc_results.sensitivity_params
    low = mc_results.sensitivity_low
    high = mc_results.sensitivity_high
    base = mc_results.sensitivity_base

    # Reverse order so widest bar is at top in horizontal layout
    params_rev = list(reversed(params))
    low_shift = low[::-1] - base
    high_shift = high[::-1] - base

    # Compute total range per parameter for annotation
    total_range = np.abs(high[::-1] - low[::-1])

    fig = go.Figure()

    # "Parameter decreases" bars
    fig.add_trace(
        go.Bar(
            y=params_rev,
            x=low_shift,
            orientation="h",
            name="↓ Parameter decreases",
            marker_color="rgba(231, 76, 60, 0.7)",
            hovertemplate=(
                "<b>%{y}</b> decreases<br>"
                "Buy advantage shifts by <b>$%{x:,.0f}</b>"
                "<extra></extra>"
            ),
        )
    )

    # "Parameter increases" bars
    fig.add_trace(
        go.Bar(
            y=params_rev,
            x=high_shift,
            orientation="h",
            name="↑ Parameter increases",
            marker_color="rgba(46, 204, 113, 0.7)",
            hovertemplate=(
                "<b>%{y}</b> increases<br>"
                "Buy advantage shifts by <b>$%{x:,.0f}</b>"
                "<extra></extra>"
            ),
        )
    )

    # Add total impact range as text annotations on the right
    for i, rng in enumerate(total_range):
        fig.add_annotation(
            y=params_rev[i],
            x=max(high_shift[i], low_shift[i]),
            text=f"  ±${rng / 2:,.0f}",
            showarrow=False,
            xanchor="left",
            font=dict(size=11, color="#888"),
        )

    fig.update_layout(
        title="Which Parameters Move the Needle?",
        xaxis_title="Impact on Buy Advantage ($)",
        barmode="overlay",
        template="plotly_white",
        height=400,
        xaxis_tickformat="$,.0f",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )

    return fig
