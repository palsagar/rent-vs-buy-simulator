"""Streamlit application for Real Estate vs. Equity Simulation.

This is the main entry point for the interactive web application.
Run with: streamlit run app.py
"""

import sys
from pathlib import Path

import streamlit as st

# Add src to path to import our modules
sys.path.insert(0, str(Path(__file__).parent / "src"))

from simulator.engine import calculate_scenarios
from simulator.models import SimulationConfig
from simulator.visualization import (
    create_asset_growth_chart,
    create_net_value_chart,
    create_outflow_chart,
)


def main():
    """Main application entry point."""

    # Page configuration
    st.set_page_config(
        layout="wide",
        page_title="Financial Simulator: Buy vs. Rent",
        page_icon="🏠",
    )

    # Title and description
    st.title("🏠 Financial Simulator: Buy vs. Rent")
    st.markdown("""
    Compare two capital allocation strategies over time:
    - **Strategy A (Buy):** Purchase property with a mortgage
    - **Strategy B (Rent):** Rent and invest the down payment in equities
    """)

    # Sidebar for inputs
    st.sidebar.header("📊 Simulation Parameters")

    # Common parameters
    st.sidebar.subheader("Common Settings")
    years = st.sidebar.slider(
        "Duration (Years)",
        min_value=10,
        max_value=40,
        value=30,
        step=1,
        help="How many years to simulate",
    )

    # Scenario A: Buy
    st.sidebar.subheader("🏡 Scenario A: Buy")
    prop_price = st.sidebar.number_input(
        "Property Price ($)",
        min_value=50000,
        max_value=5000000,
        value=500000,
        step=10000,
        help="Initial purchase price of the property",
    )

    down_pmt_pct = st.sidebar.slider(
        "Down Payment (%)",
        min_value=5,
        max_value=50,
        value=20,
        step=1,
        help="Down payment as percentage of property price",
    )

    mortgage_rate = st.sidebar.slider(
        "Mortgage Rate (% Annual)",
        min_value=1.0,
        max_value=10.0,
        value=4.5,
        step=0.1,
        help="Annual interest rate on the mortgage",
    )

    prop_appreciation = st.sidebar.slider(
        "Property Appreciation (% Annual)",
        min_value=0.0,
        max_value=10.0,
        value=3.0,
        step=0.1,
        help="Expected annual property value appreciation",
    )

    # Scenario B: Rent
    st.sidebar.subheader("🏢 Scenario B: Rent & Invest")
    monthly_rent = st.sidebar.number_input(
        "Monthly Rent ($)",
        min_value=500,
        max_value=20000,
        value=2000,
        step=100,
        help="Monthly rent payment",
    )

    equity_growth = st.sidebar.slider(
        "Equity Growth (CAGR % Annual)",
        min_value=0.0,
        max_value=15.0,
        value=7.0,
        step=0.1,
        help="Expected annual return on equity investments",
    )

    rent_inflation = st.sidebar.slider(
        "Rent Inflation (% Annual)",
        min_value=0.0,
        max_value=10.0,
        value=3.0,
        step=0.1,
        help="Expected annual rent increase",
    )

    # Create configuration
    config = SimulationConfig(
        duration_years=years,
        property_price=prop_price,
        down_payment_pct=down_pmt_pct,
        mortgage_rate_annual=mortgage_rate,
        property_appreciation_annual=prop_appreciation,
        equity_growth_annual=equity_growth,
        monthly_rent=monthly_rent,
        rent_inflation_rate=rent_inflation / 100,
    )

    # Run simulation
    with st.spinner("Running simulation..."):
        try:
            results = calculate_scenarios(config)
        except Exception as e:
            st.error(f"Error running simulation: {e}")
            st.stop()

    # Display key metrics at the top
    st.header("📈 Summary Metrics")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            label="Final Net Value: Buy",
            value=f"${results.final_net_buy:,.0f}",
            help="Home value minus total payments",
        )

    with col2:
        st.metric(
            label="Final Net Value: Rent",
            value=f"${results.final_net_rent:,.0f}",
            help="Portfolio value minus total rent payments",
        )

    with col3:
        delta_color = "normal" if results.final_difference > 0 else "inverse"
        winner = "Buy" if results.final_difference > 0 else "Rent"
        st.metric(
            label="Difference (Buy - Rent)",
            value=f"${results.final_difference:,.0f}",
            delta=f"{winner} wins",
            delta_color=delta_color,
            help="Positive means buying is better, negative means renting is better",
        )

    # Breakeven information
    if results.breakeven_year is not None:
        st.info(
            f"🎯 **Breakeven Point:** {results.breakeven_year:.1f} years - "
            f"This is when the net values cross over."
        )
    else:
        st.info(
            "🎯 **No breakeven point** - One strategy dominates for the entire period."
        )

    st.divider()

    # Visualization section
    st.header("📊 Detailed Analysis")

    # Create tabs for different views
    tab1, tab2, tab3, tab4 = st.tabs(
        ["Asset Growth", "Cumulative Costs", "Net Value Comparison", "Data Table"]
    )

    with tab1:
        st.subheader("Asset Value Over Time")
        st.markdown("""
        This chart shows how your assets grow over time:
        - **Green line:** Property value
        - **Blue line:** Investment portfolio value
        - **Red dashed line:** Remaining mortgage balance (contextual)
        """)
        fig_assets = create_asset_growth_chart(results.data)
        st.plotly_chart(fig_assets, use_container_width=True)

    with tab2:
        st.subheader("Cumulative Outflows: Cost of Lifestyle")
        st.markdown("""
        This chart shows how much cash has physically left your pocket:
        - **Red line:** Down payment + cumulative mortgage payments
        - **Orange line:** Cumulative rent payments
        """)
        fig_outflows = create_outflow_chart(results.data)
        st.plotly_chart(fig_outflows, use_container_width=True)

    with tab3:
        st.subheader("Net Value Analysis: The Bottom Line")
        st.markdown("""
        This chart shows the **Net Value** (Asset Value - Cumulative Outflows):
        - **Green dotted line:** Net value of buying
        - **Blue dotted line:** Net value of renting
        - **Star marker:** Breakeven point (if exists)
        """)
        fig_net = create_net_value_chart(results.data, results.breakeven_year)
        st.plotly_chart(fig_net, use_container_width=True)

    with tab4:
        st.subheader("Raw Data")
        st.markdown("View and download the underlying simulation data.")

        # Format the dataframe for display
        display_df = results.data.copy()

        # Round Year to 1 decimal
        display_df["Year"] = display_df["Year"].round(1)

        # Format currency columns
        currency_cols = [
            "Home_Value",
            "Equity_Value",
            "Mortgage_Balance",
            "Outflow_Buy",
            "Outflow_Rent",
            "Net_Buy",
            "Net_Rent",
        ]

        st.dataframe(
            display_df[["Year"] + currency_cols],
            use_container_width=True,
            hide_index=True,
        )

        # Download button
        csv = results.data.to_csv(index=False)
        st.download_button(
            label="📥 Download Data as CSV",
            data=csv,
            file_name="simulation_results.csv",
            mime="text/csv",
        )

    # Footer with additional information
    st.divider()
    st.markdown("""
    ### 📝 Notes & Assumptions
    - Calculations use **monthly granularity** for accuracy
    - Mortgage payments are fixed (standard amortization)
    - Property appreciation and equity growth compound monthly
    - Rent increases with inflation annually
    - No transaction costs, property taxes, or maintenance costs included
    - No taxes on investment gains considered
    """)

    with st.expander("ℹ️ About This Tool"):
        st.markdown("""
        This simulation engine helps compare two common financial strategies:

        **Strategy A (Buy):** You purchase a property with a mortgage. Your outflows
        are the down payment and monthly mortgage payments. Your asset is the property value.

        **Strategy B (Rent):** You rent a similar property and invest the equivalent
        down payment into a diversified equity portfolio. Your outflows are rent payments.
        Your asset is the investment portfolio.

        The **Net Value** metric (Asset - Outflows) represents the actual wealth accumulation
        after accounting for money spent. This is the key decision metric.

        **Developed using:** Python, NumPy, Pandas, Plotly, and Streamlit
        """)


if __name__ == "__main__":
    main()
