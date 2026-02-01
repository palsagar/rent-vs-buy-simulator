"""Visualization module for creating interactive Plotly charts.

This module provides functions to create publication-quality interactive
charts for the financial simulation results.
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def create_asset_growth_chart(df: pd.DataFrame) -> go.Figure:
    """Create a line chart showing asset values over time.

    Shows the growth trajectories of both the property and equity portfolio,
    along with the remaining mortgage balance as a contextual reference.

    Args:
        df: DataFrame with columns: Year, Home_Value, Equity_Value, Mortgage_Balance

    Returns:
        Plotly Figure object
    """
    fig = go.Figure()

    # Home Value trace (green solid line)
    fig.add_trace(
        go.Scatter(
            x=df["Year"],
            y=df["Home_Value"],
            name="Home Value",
            line=dict(color="#2ecc71", width=3),
            mode="lines",
            hovertemplate="$%{y:,.0f}<extra></extra>",
        )
    )

    # Equity Portfolio trace (blue solid line)
    fig.add_trace(
        go.Scatter(
            x=df["Year"],
            y=df["Equity_Value"],
            name="Stock Portfolio",
            line=dict(color="#3498db", width=3),
            mode="lines",
            hovertemplate="$%{y:,.0f}<extra></extra>",
        )
    )

    # Mortgage Balance trace (red dashed line - contextual)
    fig.add_trace(
        go.Scatter(
            x=df["Year"],
            y=df["Mortgage_Balance"],
            name="Mortgage Balance",
            line=dict(color="#e74c3c", width=2, dash="dash"),
            mode="lines",
            hovertemplate="$%{y:,.0f}<extra></extra>",
        )
    )

    # Layout configuration
    fig.update_layout(
        title="Asset Value Over Time",
        xaxis_title="Years",
        yaxis_title="Value ($)",
        hovermode="x unified",
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=500,
    )

    # Format y-axis as currency
    fig.update_yaxes(tickformat="$,.0f")

    return fig


def create_outflow_chart(df: pd.DataFrame) -> go.Figure:
    """Create a chart showing cumulative outflows over time.

    Visualizes how much cash has physically left the user's pocket
    in both buying and renting scenarios.

    Args:
        df: DataFrame with columns: Year, Outflow_Buy, Outflow_Rent

    Returns:
        Plotly Figure object
    """
    fig = go.Figure()

    # Cumulative Mortgage Payments (red line)
    fig.add_trace(
        go.Scatter(
            x=df["Year"],
            y=df["Outflow_Buy"],
            name="Total Cost: Buy (Down Payment + Mortgage)",
            line=dict(color="#e74c3c", width=3),
            fill="tonexty",
            mode="lines",
            hovertemplate="$%{y:,.0f}<extra></extra>",
        )
    )

    # Cumulative Rent Payments (orange line)
    fig.add_trace(
        go.Scatter(
            x=df["Year"],
            y=df["Outflow_Rent"],
            name="Total Cost: Rent",
            line=dict(color="#f39c12", width=3),
            mode="lines",
            hovertemplate="$%{y:,.0f}<extra></extra>",
        )
    )

    # Layout configuration
    fig.update_layout(
        title="Cumulative Outflows: Cost of Lifestyle",
        xaxis_title="Years",
        yaxis_title="Cumulative Outflows ($)",
        hovermode="x unified",
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=500,
    )

    # Format y-axis as currency
    fig.update_yaxes(tickformat="$,.0f")

    return fig


def create_net_value_chart(
    df: pd.DataFrame, breakeven_year: float | None = None
) -> go.Figure:
    """Create a chart showing net value comparison.

    This is the "bottom line" chart showing Asset Value - Cumulative Outflows
    for both scenarios, with an optional breakeven annotation.

    Args:
        df: DataFrame with columns: Year, Net_Buy, Net_Rent
        breakeven_year: Year where the scenarios cross (optional)

    Returns:
        Plotly Figure object
    """
    fig = go.Figure()

    # Net Buy trace (green line)
    fig.add_trace(
        go.Scatter(
            x=df["Year"],
            y=df["Net_Buy"],
            name="Net Value: Buy (Asset - Outflows)",
            line=dict(color="#2ecc71", width=3, dash="dot"),
            mode="lines",
            hovertemplate="$%{y:,.0f}<extra></extra>",
        )
    )

    # Net Rent trace (blue line)
    fig.add_trace(
        go.Scatter(
            x=df["Year"],
            y=df["Net_Rent"],
            name="Net Value: Rent (Asset - Outflows)",
            line=dict(color="#3498db", width=3, dash="dot"),
            mode="lines",
            hovertemplate="$%{y:,.0f}<extra></extra>",
        )
    )

    # Add breakeven annotation if it exists
    if breakeven_year is not None and 0 < breakeven_year < df["Year"].max():
        # Interpolate net value at breakeven
        net_at_breakeven = df[df["Year"] <= breakeven_year]["Net_Buy"].iloc[-1]

        # Add vertical line at breakeven
        fig.add_vline(
            x=breakeven_year,
            line_dash="dash",
            line_color="gray",
            annotation_text=f"Breakeven: {breakeven_year:.1f} years",
            annotation_position="top",
        )

        # Add marker at breakeven point
        fig.add_trace(
            go.Scatter(
                x=[breakeven_year],
                y=[net_at_breakeven],
                mode="markers",
                marker=dict(size=10, color="red", symbol="star"),
                name="Breakeven Point",
                hovertemplate=f"Year: {breakeven_year:.1f}<br>Value: ${net_at_breakeven:,.0f}<extra></extra>",
            )
        )

    # Add zero line for reference
    fig.add_hline(
        y=0,
        line_dash="dash",
        line_color="gray",
        opacity=0.5,
    )

    # Layout configuration
    fig.update_layout(
        title="Net Value Analysis: The Bottom Line",
        xaxis_title="Years",
        yaxis_title="Net Value (Asset - Outflows) ($)",
        hovermode="x unified",
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=500,
    )

    # Format y-axis as currency
    fig.update_yaxes(tickformat="$,.0f")

    return fig


def create_combined_dashboard(
    df: pd.DataFrame, breakeven_year: float | None = None
) -> go.Figure:
    """Create a comprehensive dashboard with all three charts in subplots.

    Args:
        df: DataFrame with all simulation results
        breakeven_year: Year where net values cross (optional)

    Returns:
        Plotly Figure object with subplots
    """
    # Create subplots: 3 rows, 1 column
    fig = make_subplots(
        rows=3,
        cols=1,
        subplot_titles=(
            "Asset Value Over Time",
            "Cumulative Outflows: Cost of Lifestyle",
            "Net Value Analysis: The Bottom Line",
        ),
        vertical_spacing=0.12,
        specs=[[{"type": "scatter"}], [{"type": "scatter"}], [{"type": "scatter"}]],
    )

    # === SUBPLOT 1: Asset Growth ===
    fig.add_trace(
        go.Scatter(
            x=df["Year"],
            y=df["Home_Value"],
            name="Home Value",
            line=dict(color="#2ecc71", width=2),
            legendgroup="assets",
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=df["Year"],
            y=df["Equity_Value"],
            name="Stock Portfolio",
            line=dict(color="#3498db", width=2),
            legendgroup="assets",
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=df["Year"],
            y=df["Mortgage_Balance"],
            name="Mortgage Balance",
            line=dict(color="#e74c3c", width=2, dash="dash"),
            legendgroup="assets",
        ),
        row=1,
        col=1,
    )

    # === SUBPLOT 2: Outflows ===
    fig.add_trace(
        go.Scatter(
            x=df["Year"],
            y=df["Outflow_Buy"],
            name="Cost: Buy",
            line=dict(color="#e74c3c", width=2),
            legendgroup="outflows",
        ),
        row=2,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=df["Year"],
            y=df["Outflow_Rent"],
            name="Cost: Rent",
            line=dict(color="#f39c12", width=2),
            legendgroup="outflows",
        ),
        row=2,
        col=1,
    )

    # === SUBPLOT 3: Net Values ===
    fig.add_trace(
        go.Scatter(
            x=df["Year"],
            y=df["Net_Buy"],
            name="Net: Buy",
            line=dict(color="#2ecc71", width=2, dash="dot"),
            legendgroup="net",
        ),
        row=3,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=df["Year"],
            y=df["Net_Rent"],
            name="Net: Rent",
            line=dict(color="#3498db", width=2, dash="dot"),
            legendgroup="net",
        ),
        row=3,
        col=1,
    )

    # Update layout
    fig.update_layout(
        height=1400,
        hovermode="x unified",
        template="plotly_white",
        showlegend=True,
    )

    # Update all y-axes to currency format
    fig.update_yaxes(tickformat="$,.0f")
    fig.update_xaxes(title_text="Years", row=3, col=1)

    return fig
