"""Monte Carlo visualization module.

Provides matplotlib and Plotly charts for MC uncertainty analysis:
spaghetti chart (matplotlib + aleatory), tornado chart (Plotly),
and probability-over-time chart (Plotly).
"""

from __future__ import annotations

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import plotly.graph_objects as go

from .models import MonteCarloResults

# Non-interactive backend for Streamlit compatibility
matplotlib.use("Agg")


def create_spaghetti_chart(mc_results: MonteCarloResults) -> plt.Figure:
    """Create a spaghetti chart with marginal distribution.

    Shows individual MC paths colored by final outcome (green if
    buying wins, red if renting wins), a bold median path, and a
    marginal histogram/KDE of final differences on the right.

    Uses aleatory's ``qp_style()`` for publication-quality styling.

    Parameters
    ----------
    mc_results : MonteCarloResults
        Full MC results containing ``all_differences``, ``year_arr``,
        ``final_differences``, and ``median_difference``.

    Returns
    -------
    plt.Figure
        Matplotlib Figure with two panels: main spaghetti plot (left)
        and marginal distribution (right).

    Examples
    --------
    Create and display a spaghetti chart:

    .. code-block:: python

        from simulator.mc_visualization import create_spaghetti_chart

        fig = create_spaghetti_chart(mc_results)
        fig.savefig("spaghetti.png", dpi=150)

    """
    # Apply aleatory's quant-plot style (colors, layout)
    try:
        from aleatory.styles import qp_style

        qp_style()
    except ImportError:
        pass  # Graceful fallback if aleatory unavailable

    # Disable LaTeX rendering — qp_style enables it but a full
    # LaTeX installation may not be available in all environments
    plt.rcParams["text.usetex"] = False

    fig, (ax_main, ax_marginal) = plt.subplots(
        1,
        2,
        gridspec_kw={"width_ratios": [4, 1]},
        sharey=True,
        figsize=(14, 6),
    )

    years = mc_results.year_arr
    all_diffs = mc_results.all_differences
    final_diffs = mc_results.final_differences

    # Individual paths: green if final > 0 (buy wins), red otherwise
    for i in range(mc_results.n_simulations):
        color = "#2ecc71" if final_diffs[i] > 0 else "#e74c3c"
        ax_main.plot(years, all_diffs[i], color=color, alpha=0.08, linewidth=0.5)

    # Median path as bold dashed blue line
    median_path = np.median(all_diffs, axis=0)
    ax_main.plot(
        years,
        median_path,
        color="#3498db",
        linewidth=2.5,
        linestyle="--",
        label="Median path",
        zorder=10,
    )

    # Zero reference line
    ax_main.axhline(y=0, color="gray", linewidth=1, linestyle="--", alpha=0.7)

    ax_main.set_xlabel("Years")
    ax_main.set_ylabel("Net Difference (Buy - Rent) ($)")
    ax_main.set_title(
        "Monte Carlo Simulation: Buy vs. Rent Outcomes",
        fontsize=14,
    )
    ax_main.legend(loc="upper left")

    # Format y-axis as currency
    ax_main.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"${x:,.0f}"))

    # --- Marginal distribution (right panel) ---
    # Color bins by sign
    pos_diffs = final_diffs[final_diffs > 0]
    neg_diffs = final_diffs[final_diffs <= 0]

    # Determine common bin edges
    n_bins = 40
    all_range = (final_diffs.min(), final_diffs.max())
    bins = np.linspace(all_range[0], all_range[1], n_bins + 1)

    if len(pos_diffs) > 0:
        ax_marginal.hist(
            pos_diffs,
            bins=bins,
            orientation="horizontal",
            color="#2ecc71",
            alpha=0.7,
            label="Buy wins",
        )
    if len(neg_diffs) > 0:
        ax_marginal.hist(
            neg_diffs,
            bins=bins,
            orientation="horizontal",
            color="#e74c3c",
            alpha=0.7,
            label="Rent wins",
        )

    ax_marginal.axhline(y=0, color="gray", linewidth=1, linestyle="--", alpha=0.7)
    ax_marginal.set_xlabel("Count")
    ax_marginal.set_title("Final Distribution", fontsize=11)
    ax_marginal.legend(loc="upper right", fontsize=8)

    # Shared y-axis: suppress labels on marginal
    ax_marginal.tick_params(axis="y", labelleft=False)

    fig.tight_layout()
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


def create_probability_chart(
    mc_results: MonteCarloResults,
) -> go.Figure:
    """Create a probability-over-time chart.

    Line chart showing the fraction of simulations where buying
    beats renting at each point in time.

    Parameters
    ----------
    mc_results : MonteCarloResults
        MC results containing ``all_differences`` and ``year_arr``.

    Returns
    -------
    go.Figure
        Plotly Figure with probability line and 50% reference.

    Examples
    --------
    Create a probability chart:

    .. code-block:: python

        from simulator.mc_visualization import create_probability_chart

        fig = create_probability_chart(mc_results)
        fig.show()

    """
    years = mc_results.year_arr
    all_diffs = mc_results.all_differences

    # Fraction of sims where buy wins at each month
    buy_wins_frac = np.mean(all_diffs > 0, axis=0) * 100

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=years,
            y=buy_wins_frac,
            mode="lines",
            name="P(Buy Wins)",
            line=dict(color="#3498db", width=3),
            hovertemplate=("Year %{x:.1f}<br>%{y:.1f}% chance buy wins<extra></extra>"),
        )
    )

    # 50% reference line
    fig.add_hline(
        y=50,
        line_dash="dash",
        line_color="gray",
        opacity=0.7,
        annotation_text="50%",
        annotation_position="bottom right",
    )

    fig.update_layout(
        title="Probability of Buying Winning Over Time",
        xaxis_title="Years",
        yaxis_title="Probability Buy Wins (%)",
        yaxis_range=[0, 100],
        template="plotly_white",
        height=400,
    )

    return fig
