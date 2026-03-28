# Explainer Popups Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a welcome modal and inline guide panel with colorful, scannable explainers for core concepts.

**Architecture:** New `src/simulator/explainers.py` module containing HTML content constants, CSS, and Streamlit rendering functions. Integrated into `app.py` with minimal changes (3 imports, ~20 lines changed). Content tested via string assertions on the HTML constants.

**Tech Stack:** Streamlit (`st.dialog`, `st.expander`, `st.markdown` with `unsafe_allow_html=True`), custom CSS

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `src/simulator/explainers.py` | Create | CSS, HTML content constants, 3 public Streamlit functions |
| `tests/test_explainers.py` | Create | Content assertions on HTML constants |
| `app.py` | Modify | Wire up imports + calls, remove redundant About section |
| `pyproject.toml` | Modify | Bump Streamlit minimum to `>=1.37.0` (for `@st.dialog`) |

---

### Task 1: CSS injection — test and implement

**Files:**
- Create: `tests/test_explainers.py`
- Create: `src/simulator/explainers.py`

- [ ] **Step 1: Write failing tests for CSS content**

Create `tests/test_explainers.py`:

```python
"""Unit tests for the explainer UI components."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from simulator.explainers import _EXPLAINER_CSS


class TestExplainerCSS:
    """Tests for the injected CSS content."""

    def test_contains_card_classes(self) -> None:
        """CSS includes all scenario card variants."""
        assert ".explainer-card--a" in _EXPLAINER_CSS
        assert ".explainer-card--b" in _EXPLAINER_CSS
        assert ".explainer-card--c" in _EXPLAINER_CSS

    def test_contains_badge_classes(self) -> None:
        """CSS includes all badge color variants."""
        assert ".explainer-badge--a" in _EXPLAINER_CSS
        assert ".explainer-badge--b" in _EXPLAINER_CSS
        assert ".explainer-badge--c" in _EXPLAINER_CSS

    def test_contains_utility_classes(self) -> None:
        """CSS includes formula and tip classes."""
        assert ".explainer-formula" in _EXPLAINER_CSS
        assert ".explainer-tip" in _EXPLAINER_CSS

    def test_contains_scenario_colors(self) -> None:
        """CSS uses the correct accent colors for each scenario."""
        assert "#4ade80" in _EXPLAINER_CSS
        assert "#60a5fa" in _EXPLAINER_CSS
        assert "#c084fc" in _EXPLAINER_CSS
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_explainers.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'simulator.explainers'`

- [ ] **Step 3: Create explainers.py with CSS constant and inject function**

Create `src/simulator/explainers.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_explainers.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/simulator/explainers.py tests/test_explainers.py
git commit -m "feat: add explainer CSS injection"
```

---

### Task 2: Welcome modal — test and implement

**Files:**
- Modify: `src/simulator/explainers.py`
- Modify: `tests/test_explainers.py`

- [ ] **Step 1: Write failing tests for welcome modal HTML**

Append to `tests/test_explainers.py`:

```python
from simulator.explainers import _EXPLAINER_CSS, _WELCOME_MODAL_HTML


class TestWelcomeModal:
    """Tests for the welcome modal HTML content."""

    def test_contains_all_scenario_names(self) -> None:
        """Welcome modal describes all three strategies."""
        assert "Buy" in _WELCOME_MODAL_HTML
        assert "Rent + Invest<" in _WELCOME_MODAL_HTML
        assert "Rent + Invest Savings" in _WELCOME_MODAL_HTML

    def test_contains_scenario_badges(self) -> None:
        """Welcome modal has A, B, C letter badges."""
        assert 'explainer-badge--a">A<' in _WELCOME_MODAL_HTML
        assert 'explainer-badge--b">B<' in _WELCOME_MODAL_HTML
        assert 'explainer-badge--c">C<' in _WELCOME_MODAL_HTML

    def test_contains_tip_callout(self) -> None:
        """Welcome modal includes the tip about Net Value."""
        assert "Net Value" in _WELCOME_MODAL_HTML
        assert "explainer-tip" in _WELCOME_MODAL_HTML

    def test_contains_tagline(self) -> None:
        """Welcome modal has the one-sentence tagline."""
        assert "Compare capital allocation strategies" in _WELCOME_MODAL_HTML
```

Update the import at the top of the file to include `_WELCOME_MODAL_HTML`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_explainers.py::TestWelcomeModal -v`
Expected: FAIL — `ImportError: cannot import name '_WELCOME_MODAL_HTML'`

- [ ] **Step 3: Add welcome modal HTML constant and dialog function**

Append to `src/simulator/explainers.py` (after the CSS section):

```python
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
    if st.button(
        "Start Exploring", use_container_width=True, type="primary"
    ):
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
    if not st.session_state.get("welcome_dismissed", False):
        _welcome_dialog()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_explainers.py -v`
Expected: 8 passed

- [ ] **Step 5: Commit**

```bash
git add src/simulator/explainers.py tests/test_explainers.py
git commit -m "feat: add welcome modal with scenario cards"
```

---

### Task 3: Guide panel — test and implement

**Files:**
- Modify: `src/simulator/explainers.py`
- Modify: `tests/test_explainers.py`

- [ ] **Step 1: Write failing tests for guide panel HTML**

Append to `tests/test_explainers.py`:

```python
from simulator.explainers import (
    _EXPLAINER_CSS,
    _GUIDE_BREAKEVEN_HTML,
    _GUIDE_NET_VALUE_HTML,
    _GUIDE_SCENARIO_C_HTML,
    _GUIDE_SCENARIOS_HTML,
    _WELCOME_MODAL_HTML,
)


class TestGuidePanel:
    """Tests for the guide panel HTML content."""

    def test_scenarios_contains_all_strategies(self) -> None:
        """Guide scenarios topic describes all three strategies."""
        assert "Buy" in _GUIDE_SCENARIOS_HTML
        assert "Rent + Invest<" in _GUIDE_SCENARIOS_HTML
        assert "Rent + Invest Savings" in _GUIDE_SCENARIOS_HTML

    def test_scenarios_has_badges(self) -> None:
        """Guide scenarios has A, B, C badges."""
        assert 'explainer-badge--a">A<' in _GUIDE_SCENARIOS_HTML
        assert 'explainer-badge--b">B<' in _GUIDE_SCENARIOS_HTML
        assert 'explainer-badge--c">C<' in _GUIDE_SCENARIOS_HTML

    def test_net_value_contains_formula(self) -> None:
        """Guide net value topic shows the formula."""
        assert "Net Value = Asset Value" in _GUIDE_NET_VALUE_HTML
        assert "Total Outflows" in _GUIDE_NET_VALUE_HTML

    def test_net_value_explains_misleading_growth(self) -> None:
        """Guide explains why asset growth alone is misleading."""
        assert "lower" in _GUIDE_NET_VALUE_HTML.lower()
        assert "costs" in _GUIDE_NET_VALUE_HTML.lower()

    def test_breakeven_explains_concept(self) -> None:
        """Guide breakeven topic explains what it means."""
        assert "buying" in _GUIDE_BREAKEVEN_HTML.lower()
        assert "renting" in _GUIDE_BREAKEVEN_HTML.lower()
        assert "No breakeven" in _GUIDE_BREAKEVEN_HTML

    def test_scenario_c_explains_availability(self) -> None:
        """Guide Scenario C topic explains the mortgage > rent rule."""
        assert "mortgage" in _GUIDE_SCENARIO_C_HTML.lower()
        assert "rent" in _GUIDE_SCENARIO_C_HTML.lower()
        assert "disabled" in _GUIDE_SCENARIO_C_HTML.lower()
```

Update the import at the top of the file to include all four guide HTML constants.

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_explainers.py::TestGuidePanel -v`
Expected: FAIL — `ImportError: cannot import name '_GUIDE_SCENARIOS_HTML'`

- [ ] **Step 3: Add guide panel HTML constants and render function**

Append to `src/simulator/explainers.py` (after the welcome modal section):

```python
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
            st.markdown(
                _GUIDE_SCENARIOS_HTML, unsafe_allow_html=True
            )
        with st.expander("📊 Net Value — The Key Metric"):
            st.markdown(
                _GUIDE_NET_VALUE_HTML, unsafe_allow_html=True
            )
        with st.expander("🎯 Breakeven Point"):
            st.markdown(
                _GUIDE_BREAKEVEN_HTML, unsafe_allow_html=True
            )
        with st.expander("🔒 When is Scenario C Available?"):
            st.markdown(
                _GUIDE_SCENARIO_C_HTML, unsafe_allow_html=True
            )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_explainers.py -v`
Expected: 14 passed

- [ ] **Step 5: Commit**

```bash
git add src/simulator/explainers.py tests/test_explainers.py
git commit -m "feat: add guide panel with 4 explainer topics"
```

---

### Task 4: Integrate into app.py and bump Streamlit version

**Files:**
- Modify: `app.py:7-30` (imports)
- Modify: `app.py:322-352` (page config → title → description block)
- Modify: `app.py:961-987` (remove About expander)
- Modify: `pyproject.toml:8` (Streamlit version)

- [ ] **Step 1: Bump Streamlit minimum version**

In `pyproject.toml`, change:

```
"streamlit>=1.29.0",
```

to:

```
"streamlit>=1.37.0",
```

This is required for `@st.dialog` (stable API, added in 1.37.0).

- [ ] **Step 2: Add imports to app.py**

Add this import block after the existing `from simulator.visualization import ...` block (around line 30):

```python
from simulator.explainers import (
    inject_explainer_css,
    render_guide_panel,
    show_welcome_modal,
)
```

- [ ] **Step 3: Wire up CSS injection and welcome modal**

In `app.py`, after the `st.set_page_config(...)` call (line 322-326), add:

```python
    # Inject custom CSS for explainer components
    inject_explainer_css()

    # Show welcome modal on first visit
    show_welcome_modal()
```

- [ ] **Step 4: Replace title + description with title + guide toggle**

Replace the current title and description block (lines 328-352):

```python
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
    - **Strategy C (Rent + Invest Savings):** Rent, invest down payment at a
      configurable rate, invest monthly savings
    """)
```

with:

```python
    # Title with guide toggle button
    title_col, btn_col = st.columns([20, 1])
    with title_col:
        st.title("🏠 Financial Simulator: Buy vs. Rent")
    with btn_col:
        st.write("")  # vertical spacer to align with title
        if st.button("?", help="Learn how this simulator works"):
            st.session_state.show_guide = not st.session_state.get(
                "show_guide", False
            )

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
```

- [ ] **Step 5: Remove the "About This Tool" expander**

Delete lines 961-987 (the `with st.expander("ℹ️ About This Tool"):` block). Its content is now covered by the guide panel. Keep the "Notes & Assumptions" section and the privacy caption that follow it.

- [ ] **Step 6: Run full test suite**

Run: `uv run pytest tests/ -v`
Expected: all tests pass

- [ ] **Step 7: Run linter**

Run: `uv run ruff check src/ tests/ app.py && uv run ruff format --check src/ tests/ app.py`
Expected: no errors

- [ ] **Step 8: Smoke test the app**

Run: `streamlit run app.py`

Verify:
1. Welcome modal appears on load with 3 colored scenario cards
2. Clicking "Start Exploring" closes it and it doesn't reappear
3. "?" button is visible next to the title
4. Clicking "?" reveals the guide panel with 4 expanders
5. Each expander shows styled HTML content
6. Clicking "?" again hides the guide panel
7. The "About This Tool" expander at the bottom is gone
8. Everything else in the app still works

- [ ] **Step 9: Commit**

```bash
git add app.py pyproject.toml
git commit -m "feat: integrate explainer popups into app"
```
