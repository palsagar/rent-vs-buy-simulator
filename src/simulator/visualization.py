"""Visualization module for creating interactive Plotly charts.

This module provides functions to create publication-quality interactive
charts for the financial simulation results.
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def create_asset_growth_chart(
    df: pd.DataFrame, show_scenario_c: bool = False, down_payment: float = 0
) -> go.Figure:
    """Create a line chart showing asset values over time.

    Shows the growth trajectories of both the property and equity portfolio,
    along with the remaining mortgage balance as a contextual reference.
    Optionally shows Scenario C assets (down payment cash + savings portfolio).

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with columns: Year, Home_Value, Equity_Value, Mortgage_Balance,
        and optionally Savings_Portfolio_Value for Scenario C.
    show_scenario_c : bool, optional
        Whether to show Scenario C trace. Default is False.
    down_payment : float, optional
        Down payment amount for Scenario C asset calculation. Default is 0.

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
            'Equity_Value': [100000, 107000, 114490, 122504],
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

    # Scenario C: Down Payment (cash) + Savings Portfolio (purple solid line)
    if show_scenario_c and "Savings_Portfolio_Value" in df.columns:
        scenario_c_asset = down_payment + df["Savings_Portfolio_Value"]
        fig.add_trace(
            go.Scatter(
                x=df["Year"],
                y=scenario_c_asset,
                name="Cash + Savings Portfolio (Scenario C)",
                line=dict(color="#9b59b6", width=3),
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
            'Outflow_Buy': [100000, 118000, 136000, 154000],
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
    df: pd.DataFrame,
    breakeven_year: float | None = None,
    show_scenario_c: bool = False,
    breakeven_year_vs_rent_savings: float | None = None,
) -> go.Figure:
    """Create a chart showing net value comparison.

    This is the "bottom line" chart showing Asset Value - Cumulative Outflows
    for both scenarios, with an optional breakeven annotation.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with columns: Year, Net_Buy, Net_Rent, and optionally
        Net_Rent_Savings for Scenario C.
    breakeven_year : float | None, optional
        Year where Buy and Rent scenarios cross. Default is None.
    show_scenario_c : bool, optional
        Whether to show Scenario C trace. Default is False.
    breakeven_year_vs_rent_savings : float | None, optional
        Year where Buy and Rent+Savings scenarios cross. Default is None.

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

    # Scenario C: Net Rent + Invest Savings (purple line)
    if show_scenario_c and "Net_Rent_Savings" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df["Year"],
                y=df["Net_Rent_Savings"],
                name="Net Value: Rent + Invest Savings (Scenario C)",
                line=dict(color="#9b59b6", width=3, dash="dot"),
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

    # Add breakeven annotation for Buy vs Rent+Savings (Scenario A vs C)
    if (
        show_scenario_c
        and breakeven_year_vs_rent_savings is not None
        and 0 < breakeven_year_vs_rent_savings < df["Year"].max()
    ):
        net_at_breakeven_c = df[df["Year"] <= breakeven_year_vs_rent_savings][
            "Net_Buy"
        ].iloc[-1]  # pyright: ignore[reportAttributeAccessIssue]

        # Add vertical line at breakeven (different style to distinguish)
        fig.add_vline(
            x=breakeven_year_vs_rent_savings,
            line_dash="dot",
            line_color="#9b59b6",
            annotation_text=f"A vs C: {breakeven_year_vs_rent_savings:.1f}y",
            annotation_position="bottom",
        )

        # Add marker at breakeven point
        fig.add_trace(
            go.Scatter(
                x=[breakeven_year_vs_rent_savings],
                y=[net_at_breakeven_c],
                mode="markers",
                marker=dict(size=10, color="#9b59b6", symbol="diamond"),
                name="Breakeven (A vs C)",
                hovertemplate=(
                    f"Year: {breakeven_year_vs_rent_savings:.1f}<br>"
                    f"Value: ${net_at_breakeven_c:,.0f}<extra></extra>"
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


def create_combined_dashboard(
    df: pd.DataFrame, breakeven_year: float | None = None
) -> go.Figure:
    """Create a comprehensive dashboard with all three charts in subplots.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with all simulation results including Year, Home_Value,
        Equity_Value, Mortgage_Balance, Outflow_Buy, Outflow_Rent,
        Net_Buy, and Net_Rent columns.
    breakeven_year : float | None, optional
        Year where net values cross. Default is None.

    Returns
    -------
    go.Figure
        Plotly Figure object with three subplots showing asset growth,
        cumulative outflows, and net value comparison.

    Examples
    --------
    Create a comprehensive dashboard:

    .. code-block:: python

        import pandas as pd
        from simulator.visualization import create_combined_dashboard

        df = pd.DataFrame({
            'Year': [0, 1, 2],
            'Home_Value': [500000, 515000, 530450],
            'Equity_Value': [100000, 107000, 114490],
            'Mortgage_Balance': [400000, 390000, 380000],
            'Outflow_Buy': [100000, 118000, 136000],
            'Outflow_Rent': [0, 24000, 48000],
            'Net_Buy': [400000, 397000, 394450],
            'Net_Rent': [100000, 83000, 66490]
        })

        fig = create_combined_dashboard(df)
        fig.show()

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
