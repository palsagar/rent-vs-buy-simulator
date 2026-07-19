"""Chart axis contract, parsed out of charts.js.

There is no JS test harness in this repo, so this parse is the only
automated guard on the money axis -- the same approach
``tests/test_regions.py`` uses for ``fields.js``.

**What this does and does not buy.** It is a STRUCTURAL guard: it checks
that the helper moves the money formatting to the axis that carries
money, and that both horizontal-bar charts call it. It does NOT render
anything, so it cannot prove Plotly draws the result correctly -- that
rests on the manual browser pass recorded in the PR.

An earlier version of this file asserted only that the substrings
``"xaxis.tickprefix"`` and ``"xaxis.tickformat"`` appeared somewhere in
the helper. Three mutations passed it, including
``layout.xaxis.tickprefix = undefined``, which is exactly the regression
the helper exists to prevent, and commenting out both call sites, which a
raw ``count()`` scored as present. The assertions below check the
assignment PAIRING and strip comments before counting.
"""

import re
from pathlib import Path

_CHARTS_JS = Path(__file__).parent.parent / "src/simulator/static/js/charts.js"


def _source() -> str:
    return _CHARTS_JS.read_text(encoding="utf-8")


def _strip_comments(source: str) -> str:
    """Source with ``//`` and ``/* */`` comments removed.

    Counting call sites in raw text scores a commented-out call as live.

    Examples
    --------
    .. code-block:: python

        assert _strip_comments("a(); // b();").strip() == "a();"

    """
    source = re.sub(r"/\*.*?\*/", "", source, flags=re.S)
    return re.sub(r"//[^\n]*", "", source)


def _helper_body() -> str:
    """Body of the horizontal-bar axis helper, comments stripped.

    Examples
    --------
    .. code-block:: python

        assert "xaxis" in _helper_body()

    """
    match = re.search(
        r"function moveCurrencyToXAxis\(layout\)\s*\{(?P<body>.*?)\n\}",
        _strip_comments(_source()),
        re.S,
    )
    assert match, "moveCurrencyToXAxis not found in charts.js"
    return match.group("body")


class TestHorizontalBarMoneyAxis:
    """Tornado and breakdown put money on X, categories on Y."""

    def test_x_axis_takes_its_value_from_the_matching_y_axis_key(self):
        # Pairing, not presence. `xaxis.tickprefix = undefined` and
        # `xaxis.tickprefix = yaxis.tickformat` both satisfy a substring
        # check while leaving the axis unlabelled or mislabelled.
        body = _helper_body()
        for key in ("tickprefix", "tickformat"):
            assert re.search(
                rf"layout\.xaxis\.{key}\s*=\s*layout\.yaxis\.{key}\s*;", body
            ), f"xaxis.{key} is not assigned from yaxis.{key}"

    def test_helper_clears_currency_from_the_category_axis(self):
        # Plotly ignores a tickformat on a category axis but honours a
        # tickprefix, so a prefix left on Y renders every parameter name
        # as "<symbol>Rent Inflation".
        body = _helper_body()
        assert "delete layout.yaxis.tickprefix" in body
        assert "delete layout.yaxis.tickformat" in body

    def test_helper_refuses_to_run_twice(self):
        # The second call would read the already-deleted y-axis keys and
        # assign undefined, wiping the currency it just installed.
        assert re.search(
            r"if\s*\(layout\.yaxis\.tickprefix === undefined\)\s*return;",
            _helper_body(),
        ), "moveCurrencyToXAxis has no guard against a second call"

    def test_both_horizontal_bar_charts_use_the_helper(self):
        # Comments stripped first: a commented-out call is not a call.
        live = _strip_comments(_source())
        assert live.count("moveCurrencyToXAxis(layout);") == 2

    def test_base_layout_still_puts_money_on_the_y_axis(self):
        # The helper moves what baseLayout sets. If baseLayout stops
        # setting a tickprefix, the helper silently propagates undefined.
        match = re.search(
            r"function baseLayout\(.*?\n\}", _strip_comments(_source()), re.S
        )
        assert match
        assert "tickprefix: getCurrencySymbol()" in match.group(0)
