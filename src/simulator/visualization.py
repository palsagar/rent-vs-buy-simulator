"""Visualization module for creating interactive Plotly charts.

This module provides functions to create publication-quality interactive
charts for the financial simulation results.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from simulator.models import SimulationResults


def create_asset_growth_chart(df: pd.DataFrame) -> go.Figure:
    """Create a line chart showing asset values over time.

    Shows the growth trajectories of both the property and equity portfolio,
    along with the remaining mortgage balance as a contextual reference.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with columns: Year, Home_Value, Equity_Value, Mortgage_Balance.

    Returns
    -------
    go.Figure
        Plotly Figure object with asset growth visualization.

    Examples
    --------
    Create an asset growth chart:

    .. code-block:: python

        import pandas as pd
        from simulator.visualization import create_asset_growth_chart

        df = pd.DataFrame({
            'Year': [0, 1, 2, 3],
            'Home_Value': [500000, 515000, 530450, 546364],
            'Equity_Value': [100000, 107000, 122504, 131080],
            'Mortgage_Balance': [400000, 390000, 380000, 370000]
        })

        fig = create_asset_growth_chart(df)
        fig.show()

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
            name="Stock Portfolio (Scenario B)",
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

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with columns: Year, Outflow_Buy, Outflow_Rent.

    Returns
    -------
    go.Figure
        Plotly Figure object with cumulative outflows visualization.

    Examples
    --------
    Create a cumulative outflow chart:

    .. code-block:: python

        import pandas as pd
        from simulator.visualization import create_outflow_chart

        df = pd.DataFrame({
            'Year': [0, 1, 2, 3],
            'Outflow_Buy': [100000, 124000, 148000, 172000],
            'Outflow_Rent': [0, 24000, 48000, 72000]
        })

        fig = create_outflow_chart(df)
        fig.show()

    """
    fig = go.Figure()

    # Cumulative Mortgage Payments (red line)
    fig.add_trace(
        go.Scatter(
            x=df["Year"],
            y=df["Outflow_Buy"],
            name="Total Cost: Buy (Down Payment + Mortgage + Property Tax)",
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
    df: pd.DataFrame,
    breakeven_year: float | None = None,
) -> go.Figure:
    """Create a chart showing net value comparison.

    This is the "bottom line" chart showing Asset Value - Cumulative Outflows
    for both scenarios, with an optional breakeven annotation.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with columns: Year, Net_Buy, Net_Rent.
    breakeven_year : float | None, optional
        Year where Buy and Rent scenarios cross. Default is None.

    Returns
    -------
    go.Figure
        Plotly Figure object with net value comparison visualization.

    Examples
    --------
    Create a net value comparison chart:

    .. code-block:: python

        import pandas as pd
        from simulator.visualization import create_net_value_chart

        df = pd.DataFrame({
            'Year': [0, 1, 2, 3],
            'Net_Buy': [400000, 397000, 394450, 392364],
            'Net_Rent': [100000, 83000, 66490, 50504]
        })

        fig = create_net_value_chart(df, breakeven_year=2.5)
        fig.show()

    """
    fig = go.Figure()

    # Net Buy trace (green line)
    fig.add_trace(
        go.Scatter(
            x=df["Year"],
            y=df["Net_Buy"],
            name="Net Value: Buy (Scenario A)",
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
            name="Net Value: Rent + Invest (Scenario B)",
            line=dict(color="#3498db", width=3, dash="dot"),
            mode="lines",
            hovertemplate="$%{y:,.0f}<extra></extra>",
        )
    )

    # Add breakeven annotation for Buy vs Rent (Scenario A vs B)
    if breakeven_year is not None and 0 < breakeven_year < df["Year"].max():
        # Interpolate net value at breakeven
        net_at_breakeven = df[df["Year"] <= breakeven_year]["Net_Buy"].iloc[-1]  # pyright: ignore[reportAttributeAccessIssue]

        # Add vertical line at breakeven
        fig.add_vline(
            x=breakeven_year,
            line_dash="dash",
            line_color="gray",
            annotation_text=f"A vs B: {breakeven_year:.1f}y",
            annotation_position="top",
        )

        # Add marker at breakeven point
        fig.add_trace(
            go.Scatter(
                x=[breakeven_year],
                y=[net_at_breakeven],
                mode="markers",
                marker=dict(size=10, color="red", symbol="star"),
                name="Breakeven (A vs B)",
                hovertemplate=(
                    f"Year: {breakeven_year:.1f}<br>"
                    f"Value: ${net_at_breakeven:,.0f}<extra></extra>"
                ),
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


def create_cost_breakdown_chart(results: SimulationResults) -> go.Figure:
    """Create a bar chart breaking down the total cost of homeownership.

    Shows the cumulative cost components for the buy scenario: mortgage
    payments, closing costs, property taxes, insurance, and maintenance.

    Parameters
    ----------
    results : SimulationResults
        Simulation results containing cost totals.

    Returns
    -------
    go.Figure
        Plotly figure with stacked bar chart of cost components.

    Examples
    --------
    Create a cost breakdown bar chart from simulation results:

    .. code-block:: python

        from simulator.visualization import create_cost_breakdown_chart
        fig = create_cost_breakdown_chart(results)
        fig.show()

    """
    categories = [
        "Buyer Closing Costs",
        "Seller Closing Costs",
        "Property Tax",
        "Insurance",
        "Maintenance",
        "Mortgage Payments",
    ]

    # Mortgage total = total outflow minus all other components
    total_outflow = float(results.data["Outflow_Buy"].iloc[-1])
    mortgage_total = (
        total_outflow
        - results.total_closing_costs_buyer
        - results.total_property_tax_paid
        - results.total_insurance_paid
        - results.total_maintenance_paid
    )

    values = [
        results.total_closing_costs_buyer,
        results.total_closing_costs_seller,
        results.total_property_tax_paid,
        results.total_insurance_paid,
        results.total_maintenance_paid,
        mortgage_total,
    ]

    fig = go.Figure(
        go.Bar(
            x=categories,
            y=values,
            marker_color="#8a8f98",
            text=[f"${v:,.0f}" for v in values],
            textposition="outside",
        )
    )

    fig.update_layout(
        title="Total Cost of Homeownership — Component Breakdown",
        yaxis_title="Total Cost ($)",
        yaxis_tickformat="$,.0f",
        template="plotly_white",
        showlegend=False,
    )

    return fig
