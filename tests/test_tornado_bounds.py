"""The tornado's high perturbations must stay inside the UI's own range.

``_PERTURBATION_CEILING`` hand-mirrors the slider maxima in fields.js
because the engine cannot read JavaScript. This module parses those
maxima and asserts the copy is honest -- the same approach
``tests/test_regions.py`` uses for bundle values.

Without the cap the tornado measured configurations the app cannot
produce: equity growth swung to +1 sigma = 22-24% against a slider that
stops at 15%, which over a long horizon compounds into a bar an order of
magnitude wider than every other one combined.
"""

import dataclasses
import re
import sys
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from simulator.engine import calculate_scenarios
from simulator.models import MonteCarloConfig, SimulationConfig
from simulator.monte_carlo import _PERTURBATION_CEILING, _compute_sensitivity

_FIELDS_JS = Path(__file__).parent.parent / "src/simulator/static/js/fields.js"

# Wire (camelCase) name for each engine field that carries a ceiling.
_WIRE_NAME = {
    "property_appreciation_annual": "propertyAppreciationAnnual",
    "equity_growth_annual": "equityGrowthAnnual",
    "rent_inflation_rate": "rentInflationRate",
    "property_price": "propertyPrice",
    "down_payment_pct": "downPaymentPct",
    "monthly_rent": "monthlyRent",
    "mortgage_rate_annual": "mortgageRateAnnual",
    "property_tax_rate": "propertyTaxRate",
    "annual_property_levy": "annualPropertyLevy",
}


def _slider_maxima() -> dict[str, Fraction]:
    """Slider maxima from fields.js, converted to STORED units.

    Examples
    --------
    .. code-block:: python

        assert _slider_maxima()["equityGrowthAnnual"] == 15

    """
    maxima: dict[str, Fraction] = {}
    pattern = re.compile(r'key:\s*"(?P<key>\w+)".*?max:\s*(?P<max>-?[\d.]+)')
    for line in _FIELDS_JS.read_text(encoding="utf-8").splitlines():
        match = pattern.search(line)
        if match:
            scale_match = re.search(r"scale:\s*([\d.]+)", line)
            scale = Fraction(scale_match.group(1)) if scale_match else Fraction(1)
            maxima[match.group("key")] = Fraction(match.group("max")) / scale
    return maxima


class TestCeilingsMatchTheUi:
    def test_every_ceiling_equals_its_slider_maximum(self):
        maxima = _slider_maxima()
        for field, ceiling in _PERTURBATION_CEILING.items():
            wire = _WIRE_NAME[field]
            assert Fraction(str(ceiling)) == maxima[wire], (
                f"{field}: ceiling {ceiling} != fields.js max "
                f"{float(maxima[wire])} for {wire}"
            )

    def test_every_perturbed_field_declares_a_ceiling(self):
        # A perturbation with no ceiling silently reverts to the old
        # unbounded behaviour for that field.
        source = (
            Path(__file__).parent.parent / "src/simulator/monte_carlo.py"
        ).read_text()
        block = re.search(r"perturbations = \[(?P<body>.*?)\n    \]", source, re.S)
        assert block
        fields = re.findall(r'"[^"]+",\s*"(\w+)"', block.group("body"))
        assert fields, "could not parse the perturbation list"
        missing = [f for f in fields if f not in _PERTURBATION_CEILING]
        assert not missing, f"perturbed without a ceiling: {missing}"


class TestHighSideIsBounded:
    def test_equity_growth_stops_at_the_slider_maximum(self):
        # The reported case: a long horizon turned the unbounded +1 sigma
        # into a bar that dwarfed the whole chart.
        config = SimulationConfig(
            horizon_years=22,
            property_price=750_000,
            down_payment_pct=20,
            mortgage_rate_annual=3.45,
            property_appreciation_annual=3.0,
            equity_growth_annual=9.0,
            monthly_rent=2200,
        )
        names, low, high, _ = _compute_sensitivity(config)
        spans = {n: abs(high[i] - low[i]) for i, n in enumerate(names)}
        widest = max(spans.values())
        # Unbounded, equity spanned ~33.7M against a ~0.5M median bar.
        assert widest < 10_000_000, f"widest bar {widest:,.0f} is still runaway"
        # And the chart stays readable: no bar is a rounding error next to
        # the widest one.
        assert min(spans.values()) / widest > 0.005

    def test_low_side_still_reaches_genuinely_negative_growth(self):
        # The cap is deliberately ASYMMETRIC. A crash is a real outcome
        # the model must represent even though the slider floor is 0, so
        # capping the low side too would be a behaviour regression.
        base = 7.0
        std = MonteCarloConfig().equity_growth_std
        config = SimulationConfig(
            horizon_years=10,
            property_price=500_000,
            down_payment_pct=20,
            mortgage_rate_annual=6.5,
            property_appreciation_annual=3.0,
            equity_growth_annual=base,
            monthly_rent=2400,
        )
        assert base - std < 0, "test presumes the low perturbation goes negative"
        names, low, _high, _ = _compute_sensitivity(config)
        expected = calculate_scenarios(
            dataclasses.replace(config, equity_growth_annual=base - std)
        ).final_difference
        # The low bar must still be the outcome at -8%, NOT at the slider
        # floor of 0. If a future change caps the low side too, this is
        # the assertion that catches it.
        assert low[names.index("Equity Growth")] == expected
