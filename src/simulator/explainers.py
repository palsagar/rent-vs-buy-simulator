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
