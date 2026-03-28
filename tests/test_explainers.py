"""Unit tests for the explainer UI components."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from simulator.explainers import (
    _EXPLAINER_CSS,
    _GUIDE_BREAKEVEN_HTML,
    _GUIDE_NET_VALUE_HTML,
    _GUIDE_SCENARIO_C_HTML,
    _GUIDE_SCENARIOS_HTML,
    _WELCOME_MODAL_HTML,
)


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
