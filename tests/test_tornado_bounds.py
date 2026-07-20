"""The tornado's high perturbations must stay inside the UI's own range.

``_UI_MAXIMUM`` hand-mirrors the slider maxima in fields.js
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

from simulator.api import _camel
from simulator.engine import calculate_scenarios
from simulator.models import MonteCarloConfig, SimulationConfig
from simulator.monte_carlo import (
    _UI_MAXIMUM,
    _UI_MINIMUM,
    _compute_sensitivity,
)

_FIELDS_JS = Path(__file__).parent.parent / "src/simulator/static/js/fields.js"

# Floor for the line-oriented INPUT_DEFS parse below. A canary, not a
# count: it only has to be high enough that a reformat that silently
# drops entries trips it. Raise it deliberately, never to make a
# failure pass.
_EXPECTED_FORMATTED_FIELDS = 25


def _slider_bounds(bound: str) -> dict[str, Fraction]:
    """Slider ``min`` or ``max`` from fields.js, in STORED units.

    Parameters
    ----------
    bound : str
        Either ``"min"`` or ``"max"``.

    Examples
    --------
    .. code-block:: python

        assert _slider_bounds("max")["equityGrowthAnnual"] == 15
        assert _slider_bounds("min")["monthlyRent"] == 500

    """
    bounds: dict[str, Fraction] = {}
    pattern = re.compile(
        r'key:\s*"(?P<key>\w+)".*?\b' + bound + r":\s*(?P<val>-?[\d.]+)"
    )
    for line in _FIELDS_JS.read_text(encoding="utf-8").splitlines():
        match = pattern.search(line)
        if match:
            scale_match = re.search(r"scale:\s*([\d.]+)", line)
            scale = Fraction(scale_match.group(1)) if scale_match else Fraction(1)
            bounds[match.group("key")] = Fraction(match.group("val")) / scale
    return bounds


def _slider_maxima() -> dict[str, Fraction]:
    """Slider maxima from fields.js, converted to STORED units.

    Examples
    --------
    .. code-block:: python

        assert _slider_maxima()["equityGrowthAnnual"] == 15

    """
    return _slider_bounds("max")


class TestCeilingsMatchTheUi:
    def test_every_ceiling_equals_its_slider_maximum(self):
        maxima = _slider_maxima()
        for field, ceiling in _UI_MAXIMUM.items():
            wire = _camel(field)
            # A Prettier run that wraps a fields.js entry across lines
            # drops it from this line-oriented parse. Say so, rather
            # than raising a KeyError that reads as a broken ceiling.
            assert wire in maxima, (
                f"{wire} was not parsed out of fields.js -- is its "
                "INPUT_DEFS entry wrapped across multiple lines?"
            )
            assert Fraction(str(ceiling)) == maxima[wire], (
                f"{field}: ceiling {ceiling} != fields.js max "
                f"{float(maxima[wire])} for {wire}"
            )

    def test_every_floor_equals_its_slider_minimum(self):
        # The mirror of the ceiling check. A hand-copied floor that
        # drifts below its slider lets the tornado measure a
        # configuration the app cannot be set to -- which is exactly the
        # "$50k -> $0" home price this table was added to stop.
        minima = _slider_bounds("min")
        for field, floor in _UI_MINIMUM.items():
            wire = _camel(field)
            assert wire in minima, (
                f"{wire} was not parsed out of fields.js -- is its "
                "INPUT_DEFS entry wrapped across multiple lines?"
            )
            assert Fraction(str(floor)) == minima[wire], (
                f"{field}: floor {floor} != fields.js min "
                f"{float(minima[wire])} for {wire}"
            )

    def test_growth_rates_are_deliberately_absent_from_the_floors(self):
        # A crash is a real outcome the model must represent. Adding
        # either growth rate here would floor its low side at 0 and
        # silently delete the negative-growth case that
        # test_tornado_low_uses_negative_growth_rate pins.
        assert "property_appreciation_annual" not in _UI_MINIMUM
        assert "equity_growth_annual" not in _UI_MINIMUM

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
        missing = [f for f in fields if f not in _UI_MAXIMUM]
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
        sens = _compute_sensitivity(config)
        names = sens.params
        low = sens.low
        high = sens.high
        spans = {n: abs(high[i] - low[i]) for i, n in enumerate(names)}
        widest = max(spans.values())
        # Unbounded, equity spanned ~33.7M against a ~0.5M median bar.
        assert widest < 10_000_000, f"widest bar {widest:,.0f} is still runaway"
        # And the chart stays readable: no bar is a rounding error next to
        # the widest one.
        assert min(spans.values()) / widest > 0.005

    def test_a_base_above_its_ceiling_never_inverts_the_bar(self):
        # The engine accepts bases above the slider maximum -- down
        # payment is valid to 100, the slider stops at 50 -- and a config
        # can arrive that way through the API. Clamping to the ceiling
        # alone put the "higher" bar BELOW the base and below the "lower"
        # bar, so both landed on the same side of the pivot and the one
        # labelled "higher" showed the outcome of a DECREASE.
        for field, value in (
            ("down_payment_pct", 90.0),
            ("equity_growth_annual", 20.0),
            ("property_tax_rate", 40.0),
        ):
            kwargs = {
                "horizon_years": 10,
                "property_price": 500_000,
                "down_payment_pct": 20,
                "mortgage_rate_annual": 6.5,
                "property_appreciation_annual": 3.0,
                "equity_growth_annual": 7.0,
                "monthly_rent": 2400,
                field: value,
            }
            sens = _compute_sensitivity(SimulationConfig(**kwargs))
            names = sens.params
            low = sens.low
            high = sens.high
            base = sens.base
            label = {
                "down_payment_pct": "Down Payment %",
                "equity_growth_annual": "Equity Growth",
                "property_tax_rate": "Property Levy (% of value)",
            }[field]
            if label not in names:
                continue
            i = names.index(label)
            assert (low[i] > base) != (high[i] > base) or high[i] == base, (
                f"{field}={value}: low {low[i]:,.0f} and high {high[i]:,.0f} "
                f"are on the same side of base {base:,.0f}"
            )

    def test_ceiling_never_collapses_a_real_levy_bar(self):
        # The levy delta is proportional, so there is an exact base where
        # the low side lands ON the ceiling while the high side is
        # clamped TO it. The swing became exactly zero and the
        # negligible-swing guard -- meant for structural cancellation --
        # deleted a large, real cost from the chart.
        for levy in (10_000.0, 10_000 / 0.5833333333333334, 20_000.0):
            config = SimulationConfig(
                horizon_years=10,
                property_price=500_000,
                down_payment_pct=20,
                mortgage_rate_annual=6.5,
                property_appreciation_annual=3.0,
                equity_growth_annual=7.0,
                monthly_rent=2400,
                property_tax_rate=0.0,
                annual_property_levy=levy,
            )
            sens = _compute_sensitivity(config)
            names = sens.params
            assert "Property Levy (flat)" in names, (
                f"levy {levy:,.2f}: a real, owner-borne cost lost its bar"
            )

    def test_low_side_is_never_floored_at_the_slider_minimum(self):
        # The cap is deliberately ASYMMETRIC: only the high side is
        # bounded by the UI. The low side must remain the true perturbed
        # value even when that is below the slider floor of 0, because a
        # crash is a real outcome the model has to represent.
        #
        # At a 1-year horizon the standard error is the full std of 15,
        # so the low target is 7 - 15 = -8%.
        base = 7.0
        std = MonteCarloConfig().equity_growth_std
        config = SimulationConfig(
            horizon_years=1,
            property_price=500_000,
            down_payment_pct=20,
            mortgage_rate_annual=6.5,
            property_appreciation_annual=3.0,
            equity_growth_annual=base,
            monthly_rent=2400,
        )
        assert base - std < 0, "test presumes the low perturbation goes negative"
        sens = _compute_sensitivity(config)
        names = sens.params
        low = sens.low
        expected = calculate_scenarios(
            dataclasses.replace(config, equity_growth_annual=base - std)
        ).final_difference
        # Same code path and same inputs on both sides, so these are
        # bit-identical by construction and exact equality is the
        # assertion -- approx would hide a floor being applied.
        assert low[names.index("Equity Growth")] == expected


def _formatted_field_keys() -> set[str]:
    """INPUT_DEFS keys that declare a formatter.

    Examples
    --------
    .. code-block:: python

        assert "equityGrowthAnnual" in _formatted_field_keys()

    """
    keys: set[str] = set()
    pattern = re.compile(r'key:\s*"(?P<key>\w+)".*?fmt:')
    for line in _FIELDS_JS.read_text(encoding="utf-8").splitlines():
        match = pattern.search(line)
        if match:
            keys.add(match.group("key"))
    # Same fragility as _slider_bounds: this parse is line-oriented, so a
    # Prettier run that wraps an INPUT_DEFS entry drops it silently and
    # the caller reports a field as having no formatter when it has one.
    assert len(keys) >= _EXPECTED_FORMATTED_FIELDS, (
        f"only {len(keys)} INPUT_DEFS entries parsed out of fields.js "
        f"(expected at least {_EXPECTED_FORMATTED_FIELDS}) -- are some "
        "wrapped across multiple lines?"
    )
    return keys


class TestEveryBarCanBeFormatted:
    """The tornado reports each bar's perturbed range on hover.

    charts.js looks the value's format up in INPUT_DEFS by the config
    field the payload ships. A perturbed field with no INPUT_DEFS entry
    has no formatter to borrow, and ``fmtFieldValue`` returns an empty
    string -- the hover then reads a bare arrow with no numbers, on the
    one bar a user was trying to understand. Nothing else fails.
    """

    def test_every_perturbed_field_has_a_formatter_in_fields_js(self):
        formatted = _formatted_field_keys()
        # Drive this off the perturbation table itself, so a bar added
        # without a matching slider is caught here rather than in the UI.
        config = SimulationConfig(
            horizon_years=10,
            property_price=500_000,
            down_payment_pct=20,
            mortgage_rate_annual=6.5,
            property_appreciation_annual=3.0,
            equity_growth_annual=7.0,
            monthly_rent=2400,
            property_tax_rate=1.2,
        )
        perturbed = {_camel(f) for f in _compute_sensitivity(config).fields}
        assert perturbed, "no bars produced; the check would be vacuous"
        missing = perturbed - formatted
        assert not missing, (
            f"perturbed but absent from INPUT_DEFS (or missing fmt): {missing}"
        )

    def test_the_flat_levy_bar_is_covered_too(self):
        # It never coexists with the ad-valorem bar, so the config above
        # cannot reach it -- it needs a region that carries the levy flat
        # and does not pass it to the occupier.
        config = SimulationConfig(
            horizon_years=10,
            property_price=500_000,
            down_payment_pct=20,
            mortgage_rate_annual=6.5,
            property_appreciation_annual=3.0,
            equity_growth_annual=7.0,
            monthly_rent=2400,
            property_tax_rate=0.0,
            annual_property_levy=1220.0,
        )
        sens = _compute_sensitivity(config)
        assert "Property Levy (flat)" in sens.params
        assert {_camel(f) for f in sens.fields} <= _formatted_field_keys()
