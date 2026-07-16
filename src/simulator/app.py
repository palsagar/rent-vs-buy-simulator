"""Streamlit application for Real Estate vs. Equity Simulation.

This is the main entry point for the interactive web application.
Run with: rent-vs-buy (after pip install) or streamlit run src/simulator/app.py
"""

import streamlit as st

from simulator.engine import calculate_scenarios
from simulator.explainers import (
    inject_explainer_css,
    render_guide_panel,
    show_welcome_modal,
)
from simulator.mc_visualization import create_fan_chart, create_tornado_chart
from simulator.models import MonteCarloConfig, SimulationConfig
from simulator.monte_carlo import run_monte_carlo
from simulator.visualization import (
    create_asset_growth_chart,
    create_cost_breakdown_chart,
    create_net_value_chart,
    create_outflow_chart,
)


def init_session_state() -> None:
    """Initialize Streamlit session state variables on first load.

    Sets a default value for ``mc_results`` if not already present in
    ``st.session_state``. Safe to call on every rerun.

    Examples
    --------
    Call once at the top of the main entry point:

    .. code-block:: python

        import streamlit as st
        from app import init_session_state

        init_session_state()
        assert "mc_results" in st.session_state

    """
    if "mc_results" not in st.session_state:
        st.session_state.mc_results = None


def main() -> None:
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

    # Preset overrides hardcoded defaults
    p = preset_values.get(preset, {})

    # Common parameters
    st.sidebar.subheader("Common Settings")

    default_price = 500000
    default_down_pct = p.get("down_pmt_pct", 20)
    default_mortgage_rate = p.get("mortgage_rate", 6.5)
    default_appreciation = p.get("prop_appreciation", 3.0)
    default_equity_growth = p.get("equity_growth", 7.0)
    default_rent = 2400
    default_rent_inflation = p.get("rent_inflation", 3.0)

    horizon = st.sidebar.slider(
        "Horizon (Years until you'd sell)",
        min_value=2,
        max_value=40,
        value=10,
        step=1,
        help="How long you expect to stay before selling / moving out",
    )
    mortgage_term = st.sidebar.selectbox(
        "Mortgage Term (Years)",
        options=[15, 20, 30],
        index=2,
        help="Loan amortization period — independent of the horizon",
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
        interest_deduction = st.checkbox(
            "Mortgage Interest Deductible",
            value=True,
            help="Deduct mortgage interest (and capped property levy) "
            "from taxable income",
        )
        marginal_rate = st.slider(
            "Marginal Income Tax Rate (%)",
            0.0,
            60.0,
            24.0,
            1.0,
            help="Your top income tax rate, used for the deduction",
        )
        levy_cap_value = st.number_input(
            "Levy Deduction Cap ($, 0 = uncapped)",
            0,
            50_000,
            10_000,
            1_000,
            help="Cap on deductible property levy (US: SALT cap)",
        )
        sale_regime = st.selectbox(
            "Home-Sale Capital Gains Rule",
            options=["exempt_amount", "exempt_after_years", "fully_exempt"],
            format_func=lambda r: {
                "exempt_amount": "Exempt up to a fixed amount (US §121)",
                "exempt_after_years": "Exempt after N years of holding",
                "fully_exempt": "Always exempt (primary residence)",
            }[r],
            help="How your jurisdiction taxes the gain when you sell",
        )
        sale_exempt_amount = st.number_input(
            "Exempt Gain Amount ($)",
            0,
            1_000_000,
            250_000,
            50_000,
        )
        sale_exempt_years = st.number_input(
            "Exempt After (Years)",
            0,
            30,
            10,
            1,
        )
        sale_cg_rate = st.slider("Home-Sale CG Rate (%)", 0.0, 40.0, 15.0, 0.5)
        portfolio_cg_rate = st.slider(
            "Investment CG Rate (%)",
            0.0,
            40.0,
            15.0,
            0.5,
            help="Capital-gains rate on the investment portfolio at exit",
        )

    # Create configuration
    config = SimulationConfig(
        horizon_years=horizon,
        mortgage_term_years=int(mortgage_term),
        property_price=prop_price,
        down_payment_pct=down_pmt_pct,
        mortgage_rate_annual=mortgage_rate,
        property_appreciation_annual=prop_appreciation,
        equity_growth_annual=equity_growth,
        monthly_rent=monthly_rent,
        rent_inflation_rate=rent_inflation / 100,
        closing_cost_buyer_pct=closing_cost_buyer_pct,
        closing_cost_seller_pct=closing_cost_seller_pct,
        property_tax_rate=property_tax_rate,
        annual_home_insurance=float(annual_home_insurance),
        annual_maintenance_pct=annual_maintenance_pct,
        cost_inflation_rate=cost_inflation_rate / 100,
        interest_deduction_enabled=interest_deduction,
        marginal_tax_rate_pct=float(marginal_rate),
        levy_deduction_cap=float(levy_cap_value) if levy_cap_value > 0 else None,
        sale_cg_regime=sale_regime,
        sale_cg_exempt_amount=float(sale_exempt_amount),
        sale_cg_exempt_after_years=int(sale_exempt_years),
        sale_cg_rate_pct=float(sale_cg_rate),
        portfolio_cg_rate_pct=float(portfolio_cg_rate),
    )

    # Invalidate MC results when base config changes
    if st.session_state.get("mc_base_config") != config:
        st.session_state.pop("mc_results", None)
        st.session_state["mc_base_config"] = config

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

    st.caption(
        f"Year-1 monthly cost — Buy: ${results.monthly_cost_buy_year1:,.0f} "
        f"vs Rent: ${results.monthly_cost_rent_year1:,.0f}"
    )

    # Breakeven information
    if results.breakeven_year is not None:
        st.info(f"🎯 **Breakeven Point:** {results.breakeven_year:.1f} years")
    else:
        st.info(
            "🎯 **No breakeven point** - One strategy dominates for the entire period."
        )

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
            "- **Red dashed line:** Remaining mortgage balance"
        )
        st.markdown(asset_description)
        fig_assets = create_asset_growth_chart(results.data)
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
            "- **Markers:** Breakeven points (if they exist)"
        )
        st.markdown(net_description)
        fig_net = create_net_value_chart(
            results.data,
            breakeven_year=results.breakeven_year,
        )
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
            "Buy_Portfolio_Value",
            "Mortgage_Balance",
            "Outflow_Buy",
            "Outflow_Rent",
            "Net_Buy",
            "Net_Rent",
        ]

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

        # Run button
        if st.button(
            "Run Uncertainty Analysis", use_container_width=True, type="primary"
        ):
            with st.spinner("Simulating 500 futures..."):
                st.session_state["mc_results"] = run_monte_carlo(
                    config, MonteCarloConfig()
                )

        # Display results if available
        mc_results = st.session_state.get("mc_results")
        if mc_results is not None:
            # Headline metrics
            def _fmt_dollar(val: float) -> str:
                return f"-${abs(val):,.0f}" if val < 0 else f"${val:,.0f}"

            _mc_label = "font-size:0.875rem;color:#808495;margin-bottom:-0.25rem;"
            _mc_value = "font-size:2.25rem;font-weight:700;margin-top:0;"

            mc_m1, mc_m2, mc_m3 = st.columns(3)
            with mc_m1:
                st.markdown(
                    f"<p style='{_mc_label}'>Buy Wins</p>"
                    f"<p style='{_mc_value}'>"
                    f"{mc_results.buy_wins_pct:.1f}%</p>",
                    unsafe_allow_html=True,
                )
            with mc_m2:
                st.markdown(
                    f"<p style='{_mc_label}'>Median Difference</p>"
                    f"<p style='{_mc_value}'>"
                    f"${mc_results.median_difference:,.0f}</p>",
                    unsafe_allow_html=True,
                )
            with mc_m3:
                st.markdown(
                    f"<p style='{_mc_label}'>90% Range</p>"
                    f"<p style='{_mc_value}'>"
                    f"{_fmt_dollar(mc_results.p5_difference)} to "
                    f"{_fmt_dollar(mc_results.p95_difference)}</p>",
                    unsafe_allow_html=True,
                )

            st.divider()

            # Fan chart of the buy-vs-rent advantage across simulated futures
            st.subheader("Outcome Paths")
            st.markdown(
                "The shaded bands show where most simulated futures land. "
                "**Median** = the middle-of-the-road outcome."
            )
            st.plotly_chart(create_fan_chart(mc_results), use_container_width=True)

            st.divider()

            # Tornado (sensitivity) chart
            tc1, _ = st.columns(2)
            with tc1:
                st.subheader("What Matters Most?")
                st.caption(
                    "Wider bar = bigger impact on the outcome. "
                    "Green = parameter goes up, Red = goes down."
                )
                tornado_fig = create_tornado_chart(mc_results)
                st.plotly_chart(tornado_fig, use_container_width=True)

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
    - **Tax benefits:** Mortgage-interest and property-levy deductions
      (with a configurable levy cap), plus a configurable home-sale
      capital-gains regime
    - **Exit pricing:** Net value at every year includes selling costs and
      capital-gains tax on both the home and the portfolio
    - **Cash-flow matching:** whichever side pays less each month invests
      the difference in equities
    """)

    # Privacy and hosting notice
    st.caption(
        "🔒 **Privacy:** This app does not track any user data, use cookies, "
        "or perform any analytics. Self-hosted on a tiny VPS via "
        "[Coolify](https://coolify.io/)."
    )


if __name__ == "__main__":
    main()
