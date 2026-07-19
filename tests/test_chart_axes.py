"""Chart axis contract, parsed out of charts.js.

There is no JS test harness in this repo, so this regex parse is the
only automated guard on the money axis -- the same approach
``tests/test_regions.py`` already uses for ``fields.js``.

It exists because of a real regression: the currency moved from
``tickformat: "$~s"`` to a separate ``tickprefix`` when multi-currency
shipped, and the horizontal-bar helper still only DELETED the y-axis
formatting. Money on those charts is on X, which was left with no
currency and no SI compaction -- the tornado read "-0.5M" where every
other chart read "-EUR500k".
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

_CHARTS_JS = Path(__file__).parent.parent / "src/simulator/static/js/charts.js"


def _source() -> str:
    return _CHARTS_JS.read_text(encoding="utf-8")


def _helper_body() -> str:
    """The body of the horizontal-bar axis helper.

    Examples
    --------
    .. code-block:: python

        assert "xaxis.tickprefix" in _helper_body()

    """
    match = re.search(
        r"function moveCurrencyToXAxis\(layout\)\s*\{(?P<body>.*?)\n\}",
        _source(),
        re.S,
    )
    assert match, "moveCurrencyToXAxis not found in charts.js"
    return match.group("body")


class TestHorizontalBarMoneyAxis:
    """Tornado and breakdown put money on X, categories on Y."""

    def test_helper_assigns_currency_to_the_x_axis(self):
        # The regression was a helper that only deleted. Assigning to X is
        # the whole fix, so assert the assignment rather than its absence
        # from Y.
        body = _helper_body()
        assert "xaxis.tickprefix" in body
        assert "xaxis.tickformat" in body

    def test_helper_clears_currency_from_the_category_axis(self):
        # Plotly ignores a tickformat on a category axis but honours a
        # tickprefix, so a prefix left on Y renders every parameter name
        # as "<symbol>Rent Inflation".
        body = _helper_body()
        assert "delete layout.yaxis.tickprefix" in body
        assert "delete layout.yaxis.tickformat" in body

    def test_both_horizontal_bar_charts_use_the_helper(self):
        # Tornado and breakdown are the only two; if a third horizontal
        # bar chart is added it must opt in or ship an unlabelled axis.
        source = _source()
        assert source.count("moveCurrencyToXAxis(layout);") == 2

    def test_base_layout_still_puts_money_on_the_y_axis(self):
        # The helper moves what baseLayout sets. If baseLayout stops
        # setting a tickprefix, the helper silently propagates undefined.
        match = re.search(r"function baseLayout\(.*?\n\}", _source(), re.S)
        assert match
        assert "tickprefix: getCurrencySymbol()" in match.group(0)
