"""Streamlit application for Real Estate vs. Equity Simulation.

This is the main entry point for the interactive web application.
Run with: streamlit run app.py
"""

import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

# Add src to path to import our modules
sys.path.insert(0, str(Path(__file__).parent / "src"))

from simulator.engine import calculate_scenarios
from simulator.models import SimulationConfig
from simulator.scenario_manager import (
    ScenarioManager,
    SavedScenario,
    create_comparison_chart,
    create_comparison_table,
    export_comparison_csv,
)
from simulator.utils import generate_pdf_report
from simulator.visualization import (
    create_asset_growth_chart,
    create_net_value_chart,
    create_outflow_chart,
)

# Constants
MAX_SAVED_SCENARIOS = 5


def init_session_state():
    """Initialize session state variables."""
    if "saved_scenarios" not in st.session_state:
        st.session_state.saved_scenarios = []
    if "pdf_data" not in st.session_state:
        st.session_state.pdf_data = None
    if "scenario_manager" not in st.session_state:
        st.session_state.scenario_manager = ScenarioManager(max_scenarios=MAX_SAVED_SCENARIOS)


def render_scenario_saver(config: SimulationConfig, results):
    """Render the scenario saving UI in the sidebar."""
    st.sidebar.divider()
    st.sidebar.subheader("💾 Save Scenario")
    
    manager = st.session_state.scenario_manager
    
    if manager.is_full():
        st.sidebar.warning(f"⚠️ Maximum {MAX_SAVED_SCENARIOS} scenarios saved. Delete one to save more.")
    else:
        scenario_name = st.sidebar.text_input(
            "Scenario Name",
            value=f"Scenario {len(manager.scenarios) + 1}",
            max_chars=30,
            help="Give your scenario a descriptive name",
        )
        
        if st.sidebar.button("💾 Save Current Scenario", use_container_width=True):
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M")
            success = manager.add_scenario(scenario_name, config, results, created_at)
            if success:
                st.session_state.saved_scenarios = manager.to_dict_list()
                st.sidebar.success(f"✅ Saved '{scenario_name}'")
                st.rerun()
            else:
                st.sidebar.error("❌ Failed to save scenario")


def render_saved_scenarios_sidebar():
    """Render saved scenarios management in the sidebar."""
    manager = st.session_state.scenario_manager
    
    if not manager.scenarios:
        return
    
    st.sidebar.divider()
    st.sidebar.subheader("📁 Saved Scenarios")
    st.sidebar.caption(f"{len(manager.scenarios)}/{MAX_SAVED_SCENARIOS} scenarios saved")
    
    for scenario in manager.scenarios:
        col1, col2 = st.sidebar.columns([3, 1])
        with col1:
            st.caption(f"📊 {scenario.name}")
        with col2:
            if st.button("🗑️", key=f"delete_{scenario.name}", help=f"Delete {scenario.name}"):
                manager.remove_scenario(scenario.name)
                st.session_state.saved_scenarios = manager.to_dict_list()
                st.rerun()
    
    if st.sidebar.button("🗑️ Clear All Scenarios", use_container_width=True):
        manager.clear_all()
        st.session_state.saved_scenarios = []
        st.rerun()


def render_scenario_comparison():
    """Render the scenario comparison section."""
    manager = st.session_state.scenario_manager
    
    if not manager.scenarios:
        return
    
    st.divider()
    
    with st.expander("📊 Compare Scenarios", expanded=False):
        st.header("📊 Scenario Comparison")
        st.caption("Compare saved scenarios side-by-side")
        
        # Comparison table
        st.subheader("Comparison Table")
        comparison_df = create_comparison_table(manager.scenarios)
        
        # Format the dataframe for display
        st.dataframe(
            comparison_df,
            use_container_width=True,
            hide_index=True,
        )
        
        # Export comparison CSV
        csv_data = export_comparison_csv(manager.scenarios)
        col1, col2 = st.columns([1, 4])
        with col1:
            st.download_button(
                label="📥 Export Comparison CSV",
                data=csv_data,
                file_name=f"scenario_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True,
            )
        
        st.divider()
        
        # Comparison charts
        st.subheader("Visual Comparison")
        
        chart_type = st.selectbox(
            "Select Comparison View",
            options=[
                ("final_values", "Final Net Values"),
                ("net_value", "Net Value Trajectories"),
                ("breakeven", "Breakeven Points"),
            ],
            format_func=lambda x: x[1],
        )
        
        fig_comparison = create_comparison_chart(manager.scenarios, metric=chart_type[0])
        st.plotly_chart(fig_comparison, use_container_width=True)
        
        # Quick load section
        st.divider()
        st.subheader("🔄 Quick Load Saved Scenario")
        st.caption("Click a scenario to load its parameters")
        
        cols = st.columns(min(len(manager.scenarios), 3))
        for idx, scenario in enumerate(manager.scenarios):
            with cols[idx % 3]:
                with st.container(border=True):
                    st.caption(f"**{scenario.name}**")
                    st.caption(f"Property: ${scenario.config.property_price:,.0f}")
                    st.caption(f"Duration: {scenario.config.duration_years} years")
                    
                    # Show winner
                    if scenario.results.final_difference > 0:
                        winner = "🏆 Buy"
                        winner_color = "green"
                    else:
                        winner = "🏆 Rent"
                        winner_color = "blue"
                    
                    st.caption(f":{winner_color}[{winner} wins]")
                    
                    if st.button("📂 Load", key=f"load_{scenario.name}", use_container_width=True):
                        # Store selected scenario parameters in session state
                        st.session_state["load_scenario"] = {
                            "duration_years": scenario.config.duration_years,
                            "property_price": scenario.config.property_price,
                            "down_payment_pct": scenario.config.down_payment_pct,
                            "mortgage_rate_annual": scenario.config.mortgage_rate_annual,
                            "property_appreciation_annual": scenario.config.property_appreciation_annual,
                            "equity_growth_annual": scenario.config.equity_growth_annual,
                            "monthly_rent": scenario.config.monthly_rent,
                            "rent_inflation_rate": scenario.config.rent_inflation_rate,
                        }
                        st.rerun()


def render_comparison_in_pdf(config, results, show_c):
    """Generate comparison charts for PDF report."""
    manager = st.session_state.scenario_manager
    
    if not manager.scenarios or len(manager.scenarios) < 2:
        return None, None, None
    
    # Create comparison charts for PDF
    fig_final = create_comparison_chart(manager.scenarios, metric="final_values")
    fig_breakeven = create_comparison_chart(manager.scenarios, metric="breakeven")
    fig_trajectory = create_comparison_chart(manager.scenarios, metric="net_value")
    
    return fig_final, fig_breakeven, fig_trajectory


def main():  # noqa: C901
    """Main application entry point."""
    
    # Initialize session state
    init_session_state()
    
    # Restore scenarios from session state if needed
    manager = st.session_state.scenario_manager
    if not manager.scenarios and st.session_state.saved_scenarios:
        try:
            restored_manager = ScenarioManager.from_dict_list(
                st.session_state.saved_scenarios, max_scenarios=MAX_SAVED_SCENARIOS
            )
            st.session_state.scenario_manager = restored_manager
            manager = restored_manager
        except Exception:
            pass
    
    # Page configuration
    st.set_page_config(
        layout="wide",
        page_title="Financial Simulator: Buy vs. Rent",
        page_icon="🏠",
    )

    # Title and description
    st.title("🏠 Financial Simulator: Buy vs. Rent")

    # GitHub star link
    st.markdown(
        """
        <a href="https://github.com/palsagar/rent-vs-buy-simulator" target="_blank"
           style="text-decoration: none;">
            <img src="https://img.shields.io/github/stars/palsagar/rent-vs-buy-simulator?style=social"
                 alt="GitHub stars">
        </a>
        <span style="color: #666; font-size: 0.9em; margin-left: 8px;">
            Found this useful? Give it a ⭐ on GitHub!
        </span>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("""
    Compare capital allocation strategies over time:
    - **Strategy A (Buy):** Purchase property with a mortgage
    - **Strategy B (Rent + Invest):** Rent and invest the down payment in equities
    - **Strategy C (Rent + Invest Savings):** Rent, keep down payment as cash,
      invest monthly savings
    """)

    # Check for scenario to load
    load_params = st.session_state.get("load_scenario", None)

    # Sidebar for inputs
    st.sidebar.header("📊 Simulation Parameters")

    # Common parameters
    st.sidebar.subheader("Common Settings")
    
    # Use loaded values if available
    default_years = load_params["duration_years"] if load_params else 30
    default_price = load_params["property_price"] if load_params else 500000
    default_down_pct = load_params["down_payment_pct"] if load_params else 20
    default_mortgage_rate = load_params["mortgage_rate_annual"] if load_params else 4.5
    default_appreciation = load_params["property_appreciation_annual"] if load_params else 3.0
    default_equity_growth = load_params["equity_growth_annual"] if load_params else 7.0
    default_rent = load_params["monthly_rent"] if load_params else 2000
    default_rent_inflation = load_params["rent_inflation_rate"] * 100 if load_params else 3.0
    
    years = st.sidebar.slider(
        "Duration (Years)",
        min_value=10,
        max_value=40,
        value=int(default_years),
        step=1,
        help="How many years to simulate",
    )

    # Scenario A: Buy
    st.sidebar.subheader("🏡 Scenario A: Buy")
    prop_price = st.sidebar.number_input(
        "Property Price ($)",
        min_value=50000,
        max_value=5000000,
        value=int(default_price),
        step=10000,
        help="Initial purchase price of the property",
    )

    down_pmt_pct = st.sidebar.slider(
        "Down Payment (%)",
        min_value=5,
        max_value=50,
        value=int(default_down_pct),
        step=1,
        help="Down payment as percentage of property price",
    )

    mortgage_rate = st.sidebar.slider(
        "Mortgage Rate (% Annual)",
        min_value=1.0,
        max_value=10.0,
        value=float(default_mortgage_rate),
        step=0.1,
        help="Annual interest rate on the mortgage",
    )

    prop_appreciation = st.sidebar.slider(
        "Property Appreciation (% Annual)",
        min_value=0.0,
        max_value=10.0,
        value=float(default_appreciation),
        step=0.1,
        help="Expected annual property value appreciation",
    )

    # Scenario B: Rent
    st.sidebar.subheader("🏢 Scenario B: Rent & Invest")
    monthly_rent = st.sidebar.number_input(
        "Monthly Rent ($)",
        min_value=500,
        max_value=20000,
        value=int(default_rent),
        step=100,
        help="Monthly rent payment",
    )

    equity_growth = st.sidebar.slider(
        "Equity Growth (CAGR % Annual)",
        min_value=0.0,
        max_value=15.0,
        value=float(default_equity_growth),
        step=0.1,
        help="Expected annual return on equity investments",
    )

    rent_inflation = st.sidebar.slider(
        "Rent Inflation (% Annual)",
        min_value=0.0,
        max_value=10.0,
        value=float(default_rent_inflation),
        step=0.1,
        help="Expected annual rent increase",
    )

    # Clear load_params after using it
    if load_params:
        del st.session_state["load_scenario"]

    # Calculate preliminary values to determine if Scenario C is available
    down_payment = prop_price * (down_pmt_pct / 100)
    loan_amount = prop_price - down_payment
    monthly_rate = (mortgage_rate / 100) / 12
    n_months = years * 12

    # Calculate monthly mortgage payment
    if monthly_rate > 0 and loan_amount > 0:
        import numpy_financial as npf

        preliminary_monthly_payment = -npf.pmt(monthly_rate, n_months, loan_amount)
    else:
        preliminary_monthly_payment = loan_amount / n_months if n_months > 0 else 0

    # Scenario C toggle (only available when mortgage > rent)
    scenario_c_available = preliminary_monthly_payment > monthly_rent

    st.sidebar.subheader("📈 Scenario C: Rent + Invest Savings")
    if scenario_c_available:
        monthly_savings = preliminary_monthly_payment - monthly_rent
        st.sidebar.caption(
            f"Monthly mortgage (\\${preliminary_monthly_payment:,.0f}) > "
            f"Monthly rent (\\${monthly_rent:,.0f})"
        )
        st.sidebar.caption(f"💰 Monthly savings: \\${monthly_savings:,.0f}")
        show_scenario_c = st.sidebar.checkbox(
            "Show Scenario C",
            value=True,
            help=(
                "Rent and invest the monthly savings (mortgage - rent) at the "
                "same CAGR. Down payment kept as cash (0% return)."
            ),
        )
    else:
        st.sidebar.caption(
            f"⚠️ Not available: Monthly rent (\\${monthly_rent:,.0f}) ≥ "
            f"Monthly mortgage (\\${preliminary_monthly_payment:,.0f})"
        )
        show_scenario_c = False

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

    # Render scenario saver in sidebar
    render_scenario_saver(config, results)
    render_saved_scenarios_sidebar()

    # Display key metrics at the top
    st.header("📈 Summary Metrics")

    # Determine number of columns based on whether Scenario C is shown
    if show_scenario_c and results.scenario_c_enabled:
        col1, col2, col3, col4 = st.columns(4)
    else:
        col1, col2, col3 = st.columns(3)
        col4 = None

    with col1:
        st.metric(
            label="Final Net Value: Buy (A)",
            value=f"${results.final_net_buy:,.0f}",
            help="Home value minus total payments",
        )

    with col2:
        st.metric(
            label="Final Net Value: Rent + Invest (B)",
            value=f"${results.final_net_rent:,.0f}",
            help="Portfolio value minus total rent payments",
        )

    with col3:
        delta_color = "normal" if results.final_difference > 0 else "inverse"
        winner = "Buy (A)" if results.final_difference > 0 else "Rent (B)"
        st.metric(
            label="Difference (A - B)",
            value=f"${results.final_difference:,.0f}",
            delta=f"{winner} wins",
            delta_color=delta_color,
            help="Positive means buying is better, negative means renting is better",
        )

    if col4 is not None and results.final_net_rent_savings is not None:
        with col4:
            diff_a_vs_c = results.final_net_buy - results.final_net_rent_savings
            delta_color_c = "normal" if diff_a_vs_c > 0 else "inverse"
            winner_c = "Buy (A)" if diff_a_vs_c > 0 else "Rent+Savings (C)"
            st.metric(
                label="Final Net Value: Rent + Savings (C)",
                value=f"${results.final_net_rent_savings:,.0f}",
                delta=f"{winner_c} wins",
                delta_color=delta_color_c,
                help="Down payment (cash) + invested savings - rent payments",
            )

    # Breakeven information
    breakeven_messages = []
    if results.breakeven_year is not None:
        breakeven_messages.append(f"**A vs B:** {results.breakeven_year:.1f} years")
    if (
        show_scenario_c
        and results.scenario_c_enabled
        and results.breakeven_year_vs_rent_savings is not None
    ):
        breakeven_messages.append(
            f"**A vs C:** {results.breakeven_year_vs_rent_savings:.1f} years"
        )

    if breakeven_messages:
        st.info("🎯 **Breakeven Points:** " + " | ".join(breakeven_messages))
    else:
        st.info(
            "🎯 **No breakeven point** - One strategy dominates for the entire period."
        )

    # PDF Report Generation Section
    st.markdown("")  # Small spacing
    show_c = show_scenario_c and results.scenario_c_enabled

    # Initialize session state for PDF if not exists
    if "pdf_data" not in st.session_state:
        st.session_state.pdf_data = None

    # Button to trigger PDF generation
    if st.button(
        "📄 Generate PDF Report",
        help="Click to generate a comprehensive PDF report with charts",
    ):
        with st.spinner(
            "Generating PDF report with charts... This may take a few seconds."
        ):
            # Generate charts for PDF only when button is clicked
            fig_assets_pdf = create_asset_growth_chart(
                results.data,
                show_scenario_c=show_c,
                down_payment=down_payment,
            )
            fig_outflows_pdf = create_outflow_chart(results.data)
            fig_net_pdf = create_net_value_chart(
                results.data,
                breakeven_year=results.breakeven_year,
                show_scenario_c=show_c,
                breakeven_year_vs_rent_savings=results.breakeven_year_vs_rent_savings,
            )

            # Generate comparison charts if we have saved scenarios
            comparison_charts = None
            if len(manager.scenarios) >= 2:
                comparison_charts = render_comparison_in_pdf(config, results, show_c)

            # Generate PDF with charts
            pdf_bytes = generate_pdf_report(
                config,
                results,
                show_c,
                fig_assets=fig_assets_pdf,
                fig_outflows=fig_outflows_pdf,
                fig_net=fig_net_pdf,
                comparison_charts=comparison_charts,
                saved_scenarios=manager.scenarios,
            )

            # Store in session state
            st.session_state.pdf_data = pdf_bytes
            st.success("✅ PDF report generated successfully!")

    # Show download button if PDF has been generated
    if st.session_state.pdf_data is not None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        st.download_button(
            label="⬇️ Download PDF Report",
            data=st.session_state.pdf_data,
            file_name=f"simulation_report_{timestamp}.pdf",
            mime="application/pdf",
            help="Download the generated PDF report",
        )

    # Render scenario comparison section
    render_scenario_comparison()

    st.divider()

    # Visualization section
    st.header("📊 Detailed Analysis")

    # Create tabs for different views
    tab1, tab2, tab3, tab4 = st.tabs(
        ["Asset Growth", "Cumulative Costs", "Net Value Comparison", "Data Table"]
    )

    with tab1:
        st.subheader("Asset Value Over Time")
        asset_description = """
        This chart shows how your assets grow over time:
        - **Green line:** Property value (Scenario A)
        - **Blue line:** Investment portfolio value (Scenario B)
        """
        if show_scenario_c and results.scenario_c_enabled:
            asset_description += (
                "- **Purple line:** Cash + Savings portfolio (Scenario C)\n"
            )
        asset_description += "- **Red dashed line:** Remaining mortgage balance"
        st.markdown(asset_description)
        fig_assets = create_asset_growth_chart(
            results.data,
            show_scenario_c=show_scenario_c and results.scenario_c_enabled,
            down_payment=down_payment,
        )
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
        net_description = """
        This chart shows the **Net Value** (Asset Value - Cumulative Outflows):
        - **Green dotted line:** Net value of buying (Scenario A)
        - **Blue dotted line:** Net value of renting + investing (Scenario B)
        """
        if show_scenario_c and results.scenario_c_enabled:
            net_description += (
                "- **Purple dotted line:** Net value of renting + savings "
                "(Scenario C)\n"
            )
        net_description += "- **Markers:** Breakeven points (if they exist)"
        st.markdown(net_description)
        fig_net = create_net_value_chart(
            results.data,
            breakeven_year=results.breakeven_year,
            show_scenario_c=show_scenario_c and results.scenario_c_enabled,
            breakeven_year_vs_rent_savings=results.breakeven_year_vs_rent_savings,
        )
        st.plotly_chart(fig_net, use_container_width=True)

    with tab4:
        st.subheader("Raw Data")
        st.markdown("View and download the underlying simulation data.")

        # Format the dataframe for display
        display_df = results.data.copy()

        # Round Year to 1 decimal
        display_df["Year"] = display_df["Year"].round(1)

        # Format currency columns (include Scenario C columns when applicable)
        currency_cols = [
            "Home_Value",
            "Equity_Value",
            "Mortgage_Balance",
            "Outflow_Buy",
            "Outflow_Rent",
            "Net_Buy",
            "Net_Rent",
        ]

        if show_scenario_c and results.scenario_c_enabled:
            currency_cols.extend(["Savings_Portfolio_Value", "Net_Rent_Savings"])

        st.dataframe(
            display_df[["Year", *currency_cols]],
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
        This simulation engine helps compare three financial strategies:

        **Strategy A (Buy):** You purchase a property with a mortgage. Your
        outflows are the down payment and monthly mortgage payments. Your asset
        is the property value.

        **Strategy B (Rent + Invest):** You rent and invest the equivalent down payment
        into a diversified equity portfolio. Your outflows are rent payments.
        Your asset is the investment portfolio.

        **Strategy C (Rent + Invest Savings):** Available when mortgage payment > rent.
        You rent and keep the down payment as cash (0% return). The monthly savings
        (mortgage payment - rent) are invested at the same CAGR as Strategy B.
        Your asset is cash + savings portfolio. Outflows are rent payments.

        The **Net Value** metric (Asset - Outflows) represents the actual
        wealth accumulation after accounting for money spent. This is the key
        decision metric.

        **Developed using:** Python, NumPy, Pandas, Plotly, and Streamlit
        """)

    # Privacy and hosting notice
    st.caption(
        "🔒 **Privacy:** This app does not track any user data, use cookies, "
        "or perform any analytics. Self-hosted on a tiny VPS via "
        "[Coolify](https://coolify.io/)."
    )


if __name__ == "__main__":
    main()
