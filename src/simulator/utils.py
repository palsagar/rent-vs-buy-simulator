"""Utility functions for PDF report generation.

This module contains helper functions for generating PDF reports with charts.
"""

import io
from datetime import datetime

import plotly.graph_objects as go
from fpdf import FPDF

from simulator.models import SimulationConfig, SimulationResults


def generate_pdf_report(  # noqa: C901
    config: SimulationConfig,
    results: SimulationResults,
    show_scenario_c: bool,
    fig_assets: go.Figure | None = None,
    fig_outflows: go.Figure | None = None,
    fig_net: go.Figure | None = None,
) -> bytes:
    """Generate a multi-page PDF summary of the simulation with charts.

    Parameters
    ----------
    config : SimulationConfig
        The simulation configuration parameters.
    results : SimulationResults
        The simulation results.
    show_scenario_c : bool
        Whether Scenario C is enabled and should be included.
    fig_assets : go.Figure | None, optional
        Asset growth chart figure. Default is None.
    fig_outflows : go.Figure | None, optional
        Cumulative outflows chart figure. Default is None.
    fig_net : go.Figure | None, optional
        Net value comparison chart figure. Default is None.

    Returns
    -------
    bytes
        The PDF file content as bytes.

    Examples
    --------
    Generate a PDF report with charts:

    .. code-block:: python

        from simulator.models import SimulationConfig
        from simulator.engine import calculate_scenarios
        from simulator.visualization import (
            create_asset_growth_chart,
            create_outflow_chart,
            create_net_value_chart
        )

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
        fig_assets = create_asset_growth_chart(results.data)
        fig_outflows = create_outflow_chart(results.data)
        fig_net = create_net_value_chart(results.data)
        pdf_bytes = generate_pdf_report(
            config, results, show_scenario_c=True,
            fig_assets=fig_assets, fig_outflows=fig_outflows, fig_net=fig_net
        )

    """
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=False)

    # Header
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Buy vs. Rent Simulation Report", ln=True, align="C")
    pdf.set_font("Arial", "", 9)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    pdf.cell(0, 5, f"Generated: {timestamp}", ln=True, align="C")
    pdf.ln(5)

    # Calculate derived values
    down_payment = config.property_price * (config.down_payment_pct / 100)
    loan_amount = config.property_price - down_payment

    # Input Parameters Section
    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 6, "Input Parameters", ln=True)
    pdf.set_font("Arial", "", 9)

    # Two-column layout for parameters
    line_height = 5

    params = [
        ("Duration", f"{config.duration_years} years"),
        ("Property Price", f"${config.property_price:,.0f}"),
        ("Down Payment", f"{config.down_payment_pct}% (${down_payment:,.0f})"),
        ("Loan Amount", f"${loan_amount:,.0f}"),
        ("Mortgage Rate", f"{config.mortgage_rate_annual}% annual"),
        ("Monthly Mortgage Payment", f"${results.monthly_mortgage_payment:,.0f}"),
        ("Property Appreciation", f"{config.property_appreciation_annual}% annual"),
        ("Monthly Rent", f"${config.monthly_rent:,.0f}"),
        ("Equity Growth (CAGR)", f"{config.equity_growth_annual}% annual"),
        ("Rent Inflation", f"{config.rent_inflation_rate * 100}% annual"),
    ]

    for i in range(0, len(params), 2):
        # Left column
        pdf.set_font("Arial", "B", 9)
        pdf.cell(45, line_height, params[i][0] + ":", 0, 0)
        pdf.set_font("Arial", "", 9)
        pdf.cell(50, line_height, params[i][1], 0, 0)

        # Right column (if exists)
        if i + 1 < len(params):
            pdf.set_font("Arial", "B", 9)
            pdf.cell(45, line_height, params[i + 1][0] + ":", 0, 0)
            pdf.set_font("Arial", "", 9)
            pdf.cell(50, line_height, params[i + 1][1], 0, 1)
        else:
            pdf.ln()

    pdf.ln(3)

    # Results Summary Section
    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 6, "Results Summary", ln=True)
    pdf.set_font("Arial", "", 9)

    # Final net values
    pdf.set_font("Arial", "B", 9)
    pdf.cell(60, line_height, "Final Net Value - Buy (A):", 0, 0)
    pdf.set_font("Arial", "", 9)
    pdf.cell(0, line_height, f"${results.final_net_buy:,.0f}", ln=True)

    pdf.set_font("Arial", "B", 9)
    pdf.cell(60, line_height, "Final Net Value - Rent + Invest (B):", 0, 0)
    pdf.set_font("Arial", "", 9)
    pdf.cell(0, line_height, f"${results.final_net_rent:,.0f}", ln=True)

    if show_scenario_c and results.final_net_rent_savings is not None:
        pdf.set_font("Arial", "B", 9)
        pdf.cell(60, line_height, "Final Net Value - Rent + Savings (C):", 0, 0)
        pdf.set_font("Arial", "", 9)
        pdf.cell(0, line_height, f"${results.final_net_rent_savings:,.0f}", ln=True)

    pdf.ln(2)

    # Winner determination
    pdf.set_font("Arial", "B", 9)
    pdf.cell(60, line_height, "Winner (A vs B):", 0, 0)
    pdf.set_font("Arial", "", 9)
    winner = "Buy (A)" if results.final_difference > 0 else "Rent + Invest (B)"
    pdf.cell(
        0,
        line_height,
        f"{winner} by ${abs(results.final_difference):,.0f}",
        ln=True,
    )

    if show_scenario_c and results.final_net_rent_savings is not None:
        diff_a_vs_c = results.final_net_buy - results.final_net_rent_savings
        winner_c = "Buy (A)" if diff_a_vs_c > 0 else "Rent + Savings (C)"
        pdf.set_font("Arial", "B", 9)
        pdf.cell(60, line_height, "Winner (A vs C):", 0, 0)
        pdf.set_font("Arial", "", 9)
        pdf.cell(0, line_height, f"{winner_c} by ${abs(diff_a_vs_c):,.0f}", ln=True)

    pdf.ln(2)

    # Breakeven points
    pdf.set_font("Arial", "B", 9)
    pdf.cell(60, line_height, "Breakeven Point (A vs B):", 0, 0)
    pdf.set_font("Arial", "", 9)
    if results.breakeven_year is not None:
        pdf.cell(0, line_height, f"{results.breakeven_year:.1f} years", ln=True)
    else:
        pdf.cell(0, line_height, "No breakeven - one strategy dominates", ln=True)

    if show_scenario_c and results.breakeven_year_vs_rent_savings is not None:
        pdf.set_font("Arial", "B", 9)
        pdf.cell(60, line_height, "Breakeven Point (A vs C):", 0, 0)
        pdf.set_font("Arial", "", 9)
        pdf.cell(
            0,
            line_height,
            f"{results.breakeven_year_vs_rent_savings:.1f} years",
            ln=True,
        )

    pdf.ln(3)

    # Modeling Assumptions Section
    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 6, "Key Modeling Assumptions", ln=True)
    pdf.set_font("Arial", "", 8)

    assumptions = [
        "Monthly compounding for all growth rates",
        "Fixed mortgage payments (standard amortization)",
        "Scenario B: Down payment invested at t=0",
        "Scenario C: Down payment as cash (0%), savings invested",
        "No transaction costs, property taxes, or maintenance",
        "No taxes on investment gains",
    ]

    for assumption in assumptions:
        pdf.cell(0, 4, f"  - {assumption}", ln=True)

    # Add visualization charts if provided
    if fig_assets or fig_outflows or fig_net:
        # Add a new page for charts
        pdf.add_page()
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "Visualization Charts", ln=True, align="C")
        pdf.ln(5)

        # Chart dimensions (width fits page margins)
        chart_width = 180  # mm

        # Asset Growth Chart
        if fig_assets:
            pdf.set_font("Arial", "B", 11)
            pdf.cell(0, 6, "1. Asset Growth Over Time", ln=True)
            pdf.ln(2)

            # Export chart as PNG image
            img_bytes = fig_assets.to_image(
                format="png", width=1200, height=700, scale=2
            )
            img_stream = io.BytesIO(img_bytes)

            # Add image to PDF
            pdf.image(img_stream, x=15, w=chart_width)
            pdf.ln(5)

        # Cumulative Outflows Chart
        if fig_outflows:
            # Check if we need a new page
            if pdf.get_y() > 200:
                pdf.add_page()

            pdf.set_font("Arial", "B", 11)
            pdf.cell(0, 6, "2. Cumulative Outflows", ln=True)
            pdf.ln(2)

            # Export chart as PNG image
            img_bytes = fig_outflows.to_image(
                format="png", width=1200, height=700, scale=2
            )
            img_stream = io.BytesIO(img_bytes)

            # Add image to PDF
            pdf.image(img_stream, x=15, w=chart_width)
            pdf.ln(5)

        # Net Value Comparison Chart
        if fig_net:
            # Check if we need a new page
            if pdf.get_y() > 200:
                pdf.add_page()

            pdf.set_font("Arial", "B", 11)
            pdf.cell(0, 6, "3. Net Value Comparison", ln=True)
            pdf.ln(2)

            # Export chart as PNG image
            img_bytes = fig_net.to_image(format="png", width=1200, height=700, scale=2)
            img_stream = io.BytesIO(img_bytes)

            # Add image to PDF
            pdf.image(img_stream, x=15, w=chart_width)

    # Convert PDF to bytes
    return bytes(pdf.output())
