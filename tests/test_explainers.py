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
