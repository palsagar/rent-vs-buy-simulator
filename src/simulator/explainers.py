"""Educational explainer components for the simulation UI.

Provides a welcome modal and inline guide panel that explain core
concepts (scenarios, net value, breakeven, Scenario C availability)
using colorful, scannable cards and accordions.
"""

import streamlit as st

# -- CSS -------------------------------------------------------------------

_EXPLAINER_CSS = """\
<style>
.explainer-card {
    padding: 14px 16px;
    border-radius: 6px;
    margin-bottom: 10px;
    display: flex;
    align-items: flex-start;
    gap: 12px;
}
.explainer-card--a { background: #1a2e1a; border-left: 4px solid #4ade80; }
.explainer-card--b { background: #1a1a2e; border-left: 4px solid #60a5fa; }
.explainer-card--c { background: #2a1a2e; border-left: 4px solid #c084fc; }
.explainer-badge {
    font-size: 0.75rem;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 4px;
    color: #000;
    flex-shrink: 0;
    margin-top: 2px;
}
.explainer-badge--a { background: #4ade80; }
.explainer-badge--b { background: #60a5fa; }
.explainer-badge--c { background: #c084fc; }
.explainer-formula {
    background: #1c2128;
    border-radius: 6px;
    padding: 14px;
    text-align: center;
    margin: 12px 0;
}
.explainer-formula code {
    color: #7dd3fc;
    font-size: 0.95rem;
}
.explainer-tip {
    background: #1e293b;
    border-radius: 6px;
    padding: 12px 16px;
    margin-top: 16px;
}
.explainer-tip p {
    color: #94a3b8;
    font-size: 0.85rem;
    margin: 0;
}
.explainer-card p {
    color: #aaa;
    font-size: 0.88rem;
    margin: 4px 0 0;
    line-height: 1.5;
}
</style>
"""


def inject_explainer_css() -> None:
    """Inject custom CSS for explainer components.

    Call once at the top of the main page, after ``st.set_page_config``.

    Examples
    --------
    .. code-block:: python

        from simulator.explainers import inject_explainer_css

        inject_explainer_css()
    """
    st.markdown(_EXPLAINER_CSS, unsafe_allow_html=True)


# -- Welcome modal ---------------------------------------------------------

_WELCOME_MODAL_HTML = """\
<div style="text-align: center; margin-bottom: 16px;">
    <p style="color: #888; font-size: 0.95rem; margin: 0;">
        Compare capital allocation strategies over time
    </p>
</div>
<p style="color: #ccc; font-size: 0.95rem; line-height: 1.6; margin-bottom: 20px;">
    Should you buy a home or rent and invest the difference? This simulator
    models <strong style="color: #fff;">three financial strategies</strong>
    side-by-side so you can compare outcomes with your own numbers.
</p>
<div class="explainer-card explainer-card--a">
    <span class="explainer-badge explainer-badge--a">A</span>
    <div>
        <strong style="color: #4ade80;">Buy</strong>
        <p>Purchase property with a mortgage. Your asset is the home value;
        outflows include mortgage payments, taxes, insurance, and
        maintenance.</p>
    </div>
</div>
<div class="explainer-card explainer-card--b">
    <span class="explainer-badge explainer-badge--b">B</span>
    <div>
        <strong style="color: #60a5fa;">Rent + Invest</strong>
        <p>Rent and invest the full down payment in equities. Your asset is
        the investment portfolio; outflows are rent payments.</p>
    </div>
</div>
<div class="explainer-card explainer-card--c">
    <span class="explainer-badge explainer-badge--c">C</span>
    <div>
        <strong style="color: #c084fc;">Rent + Invest Savings</strong>
        <p>Rent, invest the down payment conservatively, and invest monthly
        savings (mortgage &minus; rent) in equities. Available when
        mortgage &gt; rent.</p>
    </div>
</div>
<div class="explainer-tip">
    <p><strong style="color: #e2e8f0;">Tip:</strong> Adjust parameters in
    the sidebar and watch the charts update. The <strong
    style="color: #e2e8f0;">Net Value</strong> chart is the key decision
    metric.</p>
</div>
"""


@st.dialog("Welcome")
def _welcome_dialog() -> None:
    """Render the welcome modal content inside a Streamlit dialog."""
    st.markdown(_WELCOME_MODAL_HTML, unsafe_allow_html=True)
    if st.button("Start Exploring", use_container_width=True, type="primary"):
        st.session_state.welcome_dismissed = True
        st.rerun()


def show_welcome_modal() -> None:
    """Show the welcome modal on first visit.

    Displays a dialog explaining the three scenarios and how to use
    the simulator. Dismissed by clicking "Start Exploring", after
    which it does not reappear for the rest of the session.

    Examples
    --------
    .. code-block:: python

        from simulator.explainers import show_welcome_modal

        show_welcome_modal()
    """
    # Only show on first visit; session_state persists across reruns
    if not st.session_state.get("welcome_dismissed", False):
        _welcome_dialog()


# -- Guide panel -----------------------------------------------------------

_GUIDE_SCENARIOS_HTML = """\
<div class="explainer-card explainer-card--a">
    <span class="explainer-badge explainer-badge--a">A</span>
    <div>
        <strong style="color: #4ade80;">Buy</strong>
        <p>You purchase property with a mortgage. Your asset is the home
        value. Outflows include the down payment, closing costs, monthly
        mortgage payments, property tax, insurance, and maintenance.</p>
    </div>
</div>
<div class="explainer-card explainer-card--b">
    <span class="explainer-badge explainer-badge--b">B</span>
    <div>
        <strong style="color: #60a5fa;">Rent + Invest</strong>
        <p>You rent and invest the full down payment into a diversified
        equity portfolio. Your asset is the investment portfolio. Outflows
        are rent payments.</p>
    </div>
</div>
<div class="explainer-card explainer-card--c">
    <span class="explainer-badge explainer-badge--c">C</span>
    <div>
        <strong style="color: #c084fc;">Rent + Invest Savings</strong>
        <p>You rent and invest the down payment at a conservative rate
        (e.g. money market fund). Monthly savings (mortgage &minus; rent)
        are invested in equities at the same growth rate as Strategy B.
        Available when mortgage &gt; rent.</p>
    </div>
</div>
"""

_GUIDE_NET_VALUE_HTML = """\
<p style="color: #ccc; font-size: 0.9rem; line-height: 1.6;">
    A home appreciating in value looks great — but you're also paying
    mortgage interest, property tax, insurance, and maintenance.
    <strong style="color: #e2e8f0;">Net Value</strong> captures the full
    picture:
</p>
<div class="explainer-formula">
    <code>Net Value = Asset Value − Total Outflows</code>
</div>
<p style="color: #ccc; font-size: 0.9rem; line-height: 1.6;">
    This tells you which strategy actually leaves you wealthier. A scenario
    can have higher asset growth but <em>lower</em> net value if the costs
    are steep enough.
</p>
"""

_GUIDE_BREAKEVEN_HTML = """\
<p style="color: #ccc; font-size: 0.9rem; line-height: 1.6;">
    The breakeven point is the year when
    <strong style="color: #4ade80;">buying</strong> overtakes
    <strong style="color: #60a5fa;">renting + investing</strong> in net
    value. Before this point, the renter is wealthier. After it, the buyer
    pulls ahead.
</p>
<p style="color: #ccc; font-size: 0.9rem; line-height: 1.6;">
    <strong style="color: #e2e8f0;">No breakeven?</strong> That means one
    strategy dominates for the entire simulation period. If you're planning
    to sell before the breakeven year, the dominant strategy may flip.
</p>
"""

_GUIDE_SCENARIO_C_HTML = """\
<p style="color: #ccc; font-size: 0.9rem; line-height: 1.6;">
    Scenario C only appears when your <strong style="color: #e2e8f0;">
    monthly mortgage payment is higher than rent</strong>. The difference
    (mortgage &minus; rent) is the "savings" you invest each month in
    equities.
</p>
<p style="color: #ccc; font-size: 0.9rem; line-height: 1.6;">
    If rent &ge; mortgage, there are no monthly savings to invest, so
    Scenario C is disabled. Try increasing the property price, lowering
    the down payment, or decreasing rent to unlock it.
</p>
"""


def render_guide_panel() -> None:
    """Render the guide accordion when the user has toggled it open.

    Checks ``st.session_state.show_guide`` and, when ``True``, renders
    a bordered container with four expandable topic sections. Does
    nothing when the guide is hidden.

    Examples
    --------
    .. code-block:: python

        from simulator.explainers import render_guide_panel

        render_guide_panel()
    """
    if not st.session_state.get("show_guide", False):
        return

    with st.container(border=True):
        st.markdown("#### 📖 How It Works")
        with st.expander("🏠 The Three Scenarios"):
            st.markdown(_GUIDE_SCENARIOS_HTML, unsafe_allow_html=True)
        with st.expander("📊 Net Value — The Key Metric"):
            st.markdown(_GUIDE_NET_VALUE_HTML, unsafe_allow_html=True)
        with st.expander("🎯 Breakeven Point"):
            st.markdown(_GUIDE_BREAKEVEN_HTML, unsafe_allow_html=True)
        with st.expander("🔒 When is Scenario C Available?"):
            st.markdown(_GUIDE_SCENARIO_C_HTML, unsafe_allow_html=True)
