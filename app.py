"""Streamlit application for Real Estate vs. Equity Simulation.

This is the main entry point for the interactive web application.
Run with: streamlit run app.py
"""

import sys
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import streamlit as st

# Add src to path to import our modules
sys.path.insert(0, str(Path(__file__).parent / "src"))

from simulator.engine import calculate_scenarios
from simulator.explainers import (
    inject_explainer_css,
    render_guide_panel,
    show_welcome_modal,
)
from simulator.mc_visualization import (
    create_probability_chart,
    create_spaghetti_chart,
    create_tornado_chart,
)
from simulator.models import MonteCarloConfig, SimulationConfig, SimulationResults
from simulator.monte_carlo import run_monte_carlo
from simulator.scenario_manager import (
    ScenarioManager,
    create_comparison_chart,
    create_comparison_table,
    export_comparison_csv,
)
from simulator.utils import generate_pdf_report
from simulator.visualization import (
    create_asset_growth_chart,
    create_cost_breakdown_chart,
    create_net_value_chart,
    create_outflow_chart,
)

# Constants
MAX_SAVED_SCENARIOS = 5


def init_session_state() -> None:
    """Initialize Streamlit session state variables on first load.

    Sets default values for ``saved_scenarios``, ``pdf_data``, and
    ``scenario_manager`` if they are not already present in
    ``st.session_state``. Safe to call on every rerun.

    Examples
    --------
    Call once at the top of the main entry point:

    .. code-block:: python

        import streamlit as st
        from app import init_session_state

        init_session_state()
        assert "saved_scenarios" in st.session_state

    """
    if "saved_scenarios" not in st.session_state:
        st.session_state.saved_scenarios = []
    if "pdf_data" not in st.session_state:
        st.session_state.pdf_data = None
    if "mc_results" not in st.session_state:
        st.session_state.mc_results = None
    if "scenario_manager" not in st.session_state:
        st.session_state.scenario_manager = ScenarioManager(
            max_scenarios=MAX_SAVED_SCENARIOS
        )


def render_scenario_saver(config: SimulationConfig, results: SimulationResults) -> None:
    """Render the scenario saving UI in the sidebar.

    Displays a text input for naming the scenario and a save button.
    Shows a warning when the maximum number of saved scenarios is reached.

    Parameters
    ----------
    config : SimulationConfig
        The current simulation configuration to save.
    results : SimulationResults
        The current simulation results to save alongside the config.

    Examples
    --------
    Typical call after running the simulation:

    .. code-block:: python

        from app import render_scenario_saver

        render_scenario_saver(config, results)

    """
    st.sidebar.divider()
    st.sidebar.subheader("💾 Save Scenario")

    manager = st.session_state.scenario_manager

    if manager.is_full():
        st.sidebar.warning(
            f"⚠️ Maximum {MAX_SAVED_SCENARIOS} scenarios saved. Delete one to save more."
        )
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


def render_saved_scenarios_sidebar() -> None:
    """Render saved scenarios management in the sidebar.

    Lists all saved scenarios with per-scenario delete buttons and a
    bulk "Clear All" button. Does nothing when no scenarios are saved.

    Examples
    --------
    Call after saving at least one scenario:

    .. code-block:: python

        from app import render_saved_scenarios_sidebar

        render_saved_scenarios_sidebar()

    """
    manager = st.session_state.scenario_manager

    if not manager.scenarios:
        return

    st.sidebar.divider()
    st.sidebar.subheader("📁 Saved Scenarios")
    st.sidebar.caption(
        f"{len(manager.scenarios)}/{MAX_SAVED_SCENARIOS} scenarios saved"
    )

    for scenario in manager.scenarios:
        col1, col2 = st.sidebar.columns([3, 1])
        with col1:
            st.caption(f"📊 {scenario.name}")
        with col2:
            if st.button(
                "🗑️", key=f"delete_{scenario.name}", help=f"Delete {scenario.name}"
            ):
                manager.remove_scenario(scenario.name)
                st.session_state.saved_scenarios = manager.to_dict_list()
                st.rerun()

    if st.sidebar.button("🗑️ Clear All Scenarios", use_container_width=True):
        manager.clear_all()
        st.session_state.saved_scenarios = []
        st.rerun()


def render_scenario_comparison() -> None:
    """Render the scenario comparison section.

    Displays a collapsible expander containing a comparison table,
    CSV export button, visual comparison chart, and quick-load buttons
    for each saved scenario. Does nothing when no scenarios are saved.

    Examples
    --------
    Call after the main simulation output to append the comparison UI:

    .. code-block:: python

        from app import render_scenario_comparison

        render_scenario_comparison()

    """
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
        col1, _ = st.columns([1, 4])
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

        fig_comparison = create_comparison_chart(
            manager.scenarios, metric=chart_type[0]
        )
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

                    if st.button(
                        "📂 Load", key=f"load_{scenario.name}", use_container_width=True
                    ):
                        # Store selected scenario parameters in session state
                        cfg = scenario.config
                        st.session_state["load_scenario"] = {
                            "duration_years": cfg.duration_years,
                            "property_price": cfg.property_price,
                            "down_payment_pct": cfg.down_payment_pct,
                            "mortgage_rate_annual": cfg.mortgage_rate_annual,
                            "property_appreciation_annual": (
                                cfg.property_appreciation_annual
                            ),
                            "equity_growth_annual": cfg.equity_growth_annual,
                            "monthly_rent": cfg.monthly_rent,
                            "rent_inflation_rate": cfg.rent_inflation_rate,
                            "down_payment_investment_rate": (
                                cfg.down_payment_investment_rate
                            ),
                        }
                        st.rerun()


def main() -> None:  # noqa: C901
    """Run the Streamlit application.

    Orchestrates the full UI lifecycle: initialises session state,
    renders sidebar inputs, runs the simulation via
    ``calculate_scenarios``, and displays summary metrics, charts,
    data table, and scenario comparison.

    Examples
    --------
    Invoke directly when running the app via Streamlit:

    .. code-block:: python

        # From the command line:
        # streamlit run app.py

        # Or programmatically in tests / notebooks:
        from app import main

        main()

    """

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

    # Inject custom CSS for explainer components
    inject_explainer_css()

    # Show welcome modal on first visit
    show_welcome_modal()

    # Title with guide toggle button
    title_col, btn_col = st.columns([20, 1])
    with title_col:
        st.title("🏠 Financial Simulator: Buy vs. Rent")
    with btn_col:
        st.write("")  # vertical spacer to align with title
        if st.button("?", help="Learn how this simulator works"):
            st.session_state.show_guide = not st.session_state.get("show_guide", False)

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

    # Expandable guide panel (shown when "?" is toggled)
    render_guide_panel()

    # Check for scenario to load
    load_params = st.session_state.get("load_scenario", None)

    # Sidebar for inputs
    st.sidebar.header("📊 Simulation Parameters")

    # Preset scenarios — provide quick-start configurations
    st.sidebar.subheader("⚡ Quick Presets")
    preset = st.sidebar.selectbox(
        "Load a preset scenario",
        options=[
            "Custom",
            "High Interest Rate (2024-2025)",
            "Bull Market Optimistic",
            "Conservative Planning",
            "First-Time Buyer",
        ],
        help="Select a preset to quickly configure realistic scenarios",
    )

    preset_values = {
        "Custom": {},
        "High Interest Rate (2024-2025)": {
            "mortgage_rate": 7.0,
            "prop_appreciation": 2.5,
            "equity_growth": 6.0,
            "rent_inflation": 3.5,
        },
        "Bull Market Optimistic": {
            "mortgage_rate": 4.0,
            "prop_appreciation": 5.0,
            "equity_growth": 10.0,
            "rent_inflation": 2.5,
        },
        "Conservative Planning": {
            "mortgage_rate": 5.5,
            "prop_appreciation": 2.0,
            "equity_growth": 5.0,
            "rent_inflation": 2.0,
        },
        "First-Time Buyer": {
            "down_pmt_pct": 10,
            "mortgage_rate": 6.5,
            "prop_appreciation": 3.0,
            "equity_growth": 7.0,
            "rent_inflation": 3.0,
        },
    }

    # Loaded scenario takes priority over preset; preset overrides hardcoded defaults
    p = preset_values.get(preset, {})

    # Common parameters
    st.sidebar.subheader("Common Settings")

    # Use loaded values if available
    default_years = load_params["duration_years"] if load_params else 30
    default_price = load_params["property_price"] if load_params else 500000
    default_down_pct = (
        load_params["down_payment_pct"] if load_params else p.get("down_pmt_pct", 20)
    )
    default_mortgage_rate = (
        load_params["mortgage_rate_annual"]
        if load_params
        else p.get("mortgage_rate", 4.5)
    )
    default_appreciation = (
        load_params["property_appreciation_annual"]
        if load_params
        else p.get("prop_appreciation", 3.0)
    )
    default_equity_growth = (
        load_params["equity_growth_annual"]
        if load_params
        else p.get("equity_growth", 7.0)
    )
    default_rent = load_params["monthly_rent"] if load_params else 2000
    default_rent_inflation = (
        load_params["rent_inflation_rate"] * 100
        if load_params
        else p.get("rent_inflation", 3.0)
    )

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

    # Advanced Settings: closing costs, ongoing expenses, and tax benefits
    with st.sidebar.expander("⚙️ Advanced Settings", expanded=False):
        st.caption("Closing costs, ongoing expenses, and tax benefits")
        closing_cost_buyer_pct = st.slider(
            "Buyer's Closing Costs (%)",
            min_value=0.0,
            max_value=10.0,
            value=3.0,
            step=0.5,
            help="Upfront closing costs when buying (loan fees, inspection, title)",
        )
        closing_cost_seller_pct = st.slider(
            "Seller's Closing Costs (%)",
            min_value=0.0,
            max_value=10.0,
            value=6.0,
            step=0.5,
            help="Closing costs when selling (agent commissions, transfer taxes, etc.)",
        )
        property_tax_rate = st.slider(
            "Property Tax Rate (% Annual)",
            min_value=0.0,
            max_value=5.0,
            value=1.2,
            step=0.1,
            help="Annual property tax as % of current property value",
        )
        annual_home_insurance = st.number_input(
            "Annual Home Insurance ($)",
            min_value=0,
            max_value=10000,
            value=1200,
            step=100,
            help="Annual homeowners insurance premium",
        )
        annual_maintenance_pct = st.slider(
            "Maintenance (% Annual)",
            min_value=0.0,
            max_value=5.0,
            value=1.0,
            step=0.1,
            help="Annual maintenance costs as % of property value",
        )
        cost_inflation_rate = st.slider(
            "Cost Inflation (% Annual)",
            min_value=0.0,
            max_value=10.0,
            value=2.5,
            step=0.1,
            help="Annual inflation rate for insurance and maintenance costs",
        )
        st.divider()
        tax_bracket = st.selectbox(
            "Federal Tax Bracket (%)",
            options=[0, 12, 22, 24, 32, 35, 37],
            index=3,
            help="Marginal federal income tax rate for deduction calculations",
        )
        enable_mortgage_deduction = st.checkbox(
            "Enable Mortgage Interest Deduction",
            value=True,
            help="Deduct mortgage interest from taxable income",
        )
        enable_capital_gains_exclusion = st.checkbox(
            "Enable Capital Gains Exclusion",
            value=True,
            help="Exclude capital gains on primary residence sale (Section 121)",
        )
        capital_gains_exemption_limit = st.selectbox(
            "Capital Gains Exemption Limit",
            options=[250000, 500000],
            format_func=lambda x: (
                f"${x:,.0f} ({'Single' if x == 250000 else 'Married'})"
            ),
            index=0,
            help="Maximum capital gains exclusion amount",
        )
        salt_cap = st.number_input(
            "SALT Deduction Cap ($)",
            min_value=0,
            max_value=50000,
            value=10000,
            step=1000,
            help="State and Local Tax deduction cap (set to $0 for pre-2018 behavior)",
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
    default_down_pmt_investment_rate = (
        load_params["down_payment_investment_rate"] * 100
        if load_params and "down_payment_investment_rate" in load_params
        else 2.5
    )
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
                "same CAGR. Down payment invested at the configured rate."
            ),
        )
        down_pmt_investment_rate = st.sidebar.slider(
            "Down Pmt Investment Rate (% Annual)",
            min_value=0.0,
            max_value=10.0,
            value=float(default_down_pmt_investment_rate),
            step=0.1,
            help=(
                "Annual return on the idle down payment (e.g. money market fund "
                "or short-term government bonds). Applies to Scenario C only."
            ),
        )
    else:
        st.sidebar.caption(
            f"⚠️ Not available: Monthly rent (\\${monthly_rent:,.0f}) ≥ "
            f"Monthly mortgage (\\${preliminary_monthly_payment:,.0f})"
        )
        show_scenario_c = False
        down_pmt_investment_rate = 2.5

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
        closing_cost_buyer_pct=closing_cost_buyer_pct,
        closing_cost_seller_pct=closing_cost_seller_pct,
        annual_home_insurance=float(annual_home_insurance),
        annual_maintenance_pct=annual_maintenance_pct,
        cost_inflation_rate=cost_inflation_rate / 100,
        tax_bracket=float(tax_bracket),
        enable_mortgage_deduction=enable_mortgage_deduction,
        enable_capital_gains_exclusion=enable_capital_gains_exclusion,
        capital_gains_exemption_limit=float(capital_gains_exemption_limit),
        property_tax_rate=property_tax_rate,
        salt_cap=float(salt_cap),
        down_payment_investment_rate=down_pmt_investment_rate / 100,
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
        col1, col2, col3, col4, col5 = st.columns(5)
    else:
        col1, col2, col3 = st.columns(3)
        col4 = col5 = None

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
                help="Invested down payment + savings portfolio - rent payments",
            )

    if col5 is not None and results.final_down_payment_value is not None:
        with col5:
            dp_initial = prop_price * (down_pmt_pct / 100)
            dp_gain = results.final_down_payment_value - dp_initial
            st.metric(
                label="Down Pmt Final Value (C)",
                value=f"${results.final_down_payment_value:,.0f}",
                delta=f"+${dp_gain:,.0f} earned",
                help="Final value of the invested down payment (Scenario C)",
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
            )
            fig_outflows_pdf = create_outflow_chart(results.data)
            fig_net_pdf = create_net_value_chart(
                results.data,
                breakeven_year=results.breakeven_year,
                show_scenario_c=show_c,
                breakeven_year_vs_rent_savings=results.breakeven_year_vs_rent_savings,
            )

            # Generate PDF with charts
            pdf_bytes = generate_pdf_report(
                config,
                results,
                show_c,
                fig_assets=fig_assets_pdf,
                fig_outflows=fig_outflows_pdf,
                fig_net=fig_net_pdf,
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
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        [
            "Asset Growth",
            "Cumulative Costs",
            "Net Value Comparison",
            "Data Table",
            "Uncertainty Analysis",
        ]
    )

    with tab1:
        st.subheader("Asset Value Over Time")
        asset_description = (
            "This chart shows how your assets grow over time:\n"
            "- **Green line:** Property value (Scenario A)\n"
            "- **Blue line:** Investment portfolio value (Scenario B)\n"
        )
        if show_scenario_c and results.scenario_c_enabled:
            asset_description += (
                "- **Purple line:** Invested down payment + "
                "Savings portfolio (Scenario C)\n"
            )
        asset_description += "- **Red dashed line:** Remaining mortgage balance"
        st.markdown(asset_description)
        fig_assets = create_asset_growth_chart(
            results.data,
            show_scenario_c=show_scenario_c and results.scenario_c_enabled,
        )
        st.plotly_chart(fig_assets, use_container_width=True)

    with tab2:
        st.subheader("Cumulative Outflows: Cost of Lifestyle")
        st.markdown(
            "This chart shows how much cash has physically left your pocket:\n"
            "- **Red line:** Down payment + cumulative mortgage payments\n"
            "- **Orange line:** Cumulative rent payments"
        )
        fig_outflows = create_outflow_chart(results.data)
        st.plotly_chart(fig_outflows, use_container_width=True)

        st.divider()
        st.subheader("Cost of Homeownership — Breakdown")
        fig_cost_breakdown = create_cost_breakdown_chart(results)
        st.plotly_chart(fig_cost_breakdown, use_container_width=True)

    with tab3:
        st.subheader("Net Value Analysis: The Bottom Line")
        net_description = (
            "This chart shows the **Net Value** (Asset Value - Cumulative Outflows):\n"
            "- **Green dotted line:** Net value of buying (Scenario A)\n"
            "- **Blue dotted line:** Net value of renting + investing (Scenario B)\n"
        )
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
            currency_cols.extend(
                ["Down_Payment_Value", "Savings_Portfolio_Value", "Net_Rent_Savings"]
            )

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

    with tab5:
        st.subheader("Monte Carlo Uncertainty Analysis")
        st.markdown(
            "Explore how **randomness in market conditions** affects "
            "the buy-vs-rent outcome. Instead of fixed annual rates, "
            "this simulation draws random rates each year from "
            "distributions centered on your inputs."
        )

        # MC settings in an expander (on the tab, not sidebar)
        with st.expander("Tune Parameters", expanded=False):
            mc_col1, mc_col2 = st.columns(2)
            with mc_col1:
                mc_n_sims = st.slider(
                    "Number of Simulations",
                    min_value=50,
                    max_value=2000,
                    value=500,
                    step=50,
                    help="More simulations = smoother results, slower",
                )
                mc_seed = st.number_input(
                    "Random Seed",
                    min_value=0,
                    max_value=99999,
                    value=42,
                    step=1,
                    help="Change for different random outcomes",
                )
            with mc_col2:
                mc_prop_std = st.slider(
                    "Property Appreciation Std (%)",
                    min_value=0.0,
                    max_value=15.0,
                    value=5.0,
                    step=0.5,
                )
                mc_eq_std = st.slider(
                    "Equity Growth Std (%)",
                    min_value=0.0,
                    max_value=15.0,
                    value=5.0,
                    step=0.5,
                )
                mc_rent_std = st.slider(
                    "Rent Inflation Std (%)",
                    min_value=0.0,
                    max_value=5.0,
                    value=1.5,
                    step=0.1,
                )
                mc_corr = st.slider(
                    "Appreciation-Equity Correlation",
                    min_value=-1.0,
                    max_value=1.0,
                    value=0.3,
                    step=0.1,
                )

        # Run button
        if st.button(
            f"Run {mc_n_sims} Simulations",
            use_container_width=True,
            type="primary",
        ):
            mc_config = MonteCarloConfig(
                n_simulations=mc_n_sims,
                seed=int(mc_seed),
                property_appreciation_std=mc_prop_std,
                equity_growth_std=mc_eq_std,
                rent_inflation_std=mc_rent_std,
                appreciation_equity_correlation=mc_corr,
            )

            with st.spinner(f"Running {mc_n_sims} simulations..."):
                mc_results = run_monte_carlo(config, mc_config)

            # Store results in session state
            st.session_state["mc_results"] = mc_results

        # Display results if available
        mc_results = st.session_state.get("mc_results")
        if mc_results is not None:
            # Headline metrics
            mc_m1, mc_m2, mc_m3 = st.columns(3)
            with mc_m1:
                st.metric(
                    "Buy Wins",
                    f"{mc_results.buy_wins_pct:.1f}%",
                    help="Fraction of simulations where buying wins",
                )
            with mc_m2:
                st.metric(
                    "Median Difference",
                    f"${mc_results.median_difference:,.0f}",
                    help="Median (Buy - Rent) across simulations",
                )
            with mc_m3:
                st.metric(
                    "90% Range",
                    (
                        f"${mc_results.p5_difference:,.0f} to "
                        f"${mc_results.p95_difference:,.0f}"
                    ),
                    help="5th to 95th percentile of outcomes",
                )

            st.divider()

            # Spaghetti chart (matplotlib)
            st.subheader("Outcome Paths")
            st.markdown(
                "Each line is one possible future. "
                "**Green** = buying wins, **Red** = renting wins, "
                "**Blue dashed** = median path."
            )
            spaghetti_fig = create_spaghetti_chart(mc_results)
            st.pyplot(spaghetti_fig)
            plt.close(spaghetti_fig)

            st.divider()

            # Tornado + Probability side by side
            tc1, tc2 = st.columns(2)
            with tc1:
                st.subheader("Sensitivity Analysis")
                tornado_fig = create_tornado_chart(mc_results)
                st.plotly_chart(tornado_fig, use_container_width=True)
            with tc2:
                st.subheader("Probability Over Time")
                prob_fig = create_probability_chart(mc_results)
                st.plotly_chart(prob_fig, use_container_width=True)

    # Footer with additional information
    st.divider()
    st.markdown("""
    ### 📝 Notes & Assumptions
    - Calculations use **monthly granularity** for accuracy
    - Mortgage payments are fixed (standard amortization)
    - Property appreciation and equity growth compound monthly
    - Rent increases with inflation annually
    - **Closing costs:** Buyer and seller costs modeled (configurable %)
    - **Ongoing costs:** Property tax, insurance, maintenance (inflation-adjusted)
    - **Tax benefits:** Mortgage interest deduction, capital gains exclusion
      (Section 121), SALT cap for property tax deduction
    - **Scenario C** available when mortgage payment > rent
    - No taxes on investment gains for the rent scenario
    """)

    # Privacy and hosting notice
    st.caption(
        "🔒 **Privacy:** This app does not track any user data, use cookies, "
        "or perform any analytics. Self-hosted on a tiny VPS via "
        "[Coolify](https://coolify.io/)."
    )


if __name__ == "__main__":
    main()
