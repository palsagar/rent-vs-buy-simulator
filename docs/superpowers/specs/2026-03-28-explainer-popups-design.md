# Explainer Popups — Design Spec

Add a welcome modal and an inline guide panel to the rent-vs-buy simulator, making core concepts accessible to first-time users through colorful, scannable explainers.

## Goals

- Help first-time users understand what the app does and how to use it
- Explain four core concepts: the three scenarios, net value, breakeven point, and Scenario C availability
- Match the visual style of the FlowLab app (color-coded cards, bold key terms, clean typography)
- Keep implementation within Streamlit using `st.dialog`, `st.expander`, and `st.markdown(unsafe_allow_html=True)`

## Components

### 1. Welcome Modal

**Trigger:** Shown automatically on first page load. Uses `st.session_state.welcome_dismissed` (defaults to `False`). Once the user clicks "Start Exploring", the flag is set to `True` and the modal does not reappear for the rest of the session.

**Implementation:** `@st.dialog("Welcome")` decorated function.

**Content (top to bottom):**
1. Centered app icon and title
2. One-sentence tagline: "Compare capital allocation strategies over time"
3. One short paragraph explaining the core question (buy vs. rent + invest)
4. Three color-coded scenario cards:
   - **A (green, `#4ade80`):** Buy — property with mortgage, outflows are mortgage/taxes/insurance/maintenance
   - **B (blue, `#60a5fa`):** Rent + Invest — rent and invest full down payment in equities
   - **C (purple, `#c084fc`):** Rent + Invest Savings — rent, invest down payment conservatively, invest monthly savings in equities
5. Tip callout: points users to the sidebar for parameters and highlights Net Value as the key metric
6. "Start Exploring" button — closes the dialog

**Scenario card HTML structure:** Each card has a dark tinted background matching its color family, a colored left border, a letter badge, a bold colored title, and a one-sentence description in muted text.

### 2. Guide Panel

**Trigger:** A circular "?" button placed next to the app title using `st.columns`. Clicking it toggles `st.session_state.show_guide` (defaults to `False`).

**Implementation:** When `show_guide` is `True`, render a container below the title with four `st.expander` sections. Each expander contains custom HTML via `st.markdown(unsafe_allow_html=True)`.

**Topics:**

#### The Three Scenarios
- Color-coded A/B/C badges with one-sentence descriptions (same content as welcome modal cards, slightly more detail)

#### Net Value — The Key Metric
- Explains that asset growth alone is misleading because it ignores costs
- Shows the formula: `Net Value = Asset Value − Total Outflows`
- Notes that a scenario with higher asset growth can have lower net value if costs are steep

#### Breakeven Point
- The year when buying overtakes renting in net value
- Before breakeven: renter is wealthier; after: buyer pulls ahead
- "No breakeven" means one strategy dominates for the entire period
- If selling before breakeven, the dominant strategy may flip

#### When is Scenario C Available?
- Only available when monthly mortgage > monthly rent
- The difference (mortgage − rent) is the monthly savings invested in equities
- If rent >= mortgage, no savings to invest, so Scenario C is disabled
- Suggests: increase property price, lower down payment, or decrease rent to unlock it

### 3. Custom CSS

A single `<style>` block injected via `st.markdown` at the top of the page. Styles:
- `.explainer-card` — scenario cards with colored left borders and tinted backgrounds
- `.explainer-badge` — letter badges (A/B/C) with scenario colors
- `.explainer-formula` — centered code-style formula callout
- `.explainer-tip` — dark callout box for tips

Class names are prefixed with `explainer-` to avoid collisions with Streamlit internals.

### 4. Changes to `app.py`

- Import `show_welcome_modal`, `render_guide_panel`, `inject_explainer_css` from `src/simulator/explainers.py`
- Call `inject_explainer_css()` once at the top of `main()`, after `st.set_page_config`
- Call `show_welcome_modal()` after CSS injection, before any other content
- Replace the current title + description block with the title + "?" button row, followed by `render_guide_panel()`
- Remove the "About This Tool" expander at the bottom (its content is now in the guide panel)
- Keep the "Notes & Assumptions" section as-is (it covers different content — technical assumptions, not concepts)

## New File

**`src/simulator/explainers.py`** — all explainer logic and content:
- `inject_explainer_css()` — injects the `<style>` block
- `show_welcome_modal()` — renders the welcome dialog if not yet dismissed
- `render_guide_panel()` — renders the "?" button and expandable guide section

## Color Scheme

| Scenario | Accent     | Background tint | Badge |
|----------|------------|-----------------|-------|
| A (Buy)  | `#4ade80`  | `#1a2e1a`       | Green |
| B (Rent) | `#60a5fa`  | `#1a1a2e`       | Blue  |
| C (Save) | `#c084fc`  | `#2a1a2e`       | Purple|

These are brighter variants of the existing Plotly chart colors (`#2ecc71`, `#3498db`, `#9b59b6`) optimized for readability on dark card backgrounds.

## Session State Keys

| Key                  | Type | Default | Purpose                         |
|----------------------|------|---------|---------------------------------|
| `welcome_dismissed`  | bool | False   | Tracks if welcome modal was closed |
| `show_guide`         | bool | False   | Tracks if guide panel is expanded  |

## Out of Scope

- Persistent "don't show again" across sessions (would require cookies/query params)
- Explanations of advanced settings (closing costs, tax deductions, SALT cap)
- Chart reading guides
- Inline tooltips on individual input fields (Streamlit `help=` parameter already handles this)
