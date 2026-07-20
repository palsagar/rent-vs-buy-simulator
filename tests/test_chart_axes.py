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

Every assertion here has been checked by mutating charts.js and
confirming the failure. A grep test that has never been seen to fail
proves nothing.
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
        # Pairing, not presence. `xaxis.tickformat = undefined` satisfies
        # a substring check while leaving the axis unlabelled.
        assert re.search(
            r"layout\.xaxis\.tickformat\s*=\s*layout\.yaxis\.tickformat\s*;",
            _helper_body(),
        ), "xaxis.tickformat is not assigned from yaxis.tickformat"

    def test_helper_clears_currency_from_the_category_axis(self):
        assert "delete layout.yaxis.tickformat" in _helper_body()

    def test_helper_refuses_to_run_twice(self):
        # The second call would read the already-deleted y-axis key and
        # assign undefined, wiping the currency it just installed.
        assert re.search(
            r"if\s*\(layout\.yaxis\.tickformat === undefined\)\s*return;",
            _helper_body(),
        ), "moveCurrencyToXAxis has no guard against a second call"

    def test_both_horizontal_bar_charts_use_the_helper(self):
        # Comments stripped first: a commented-out call is not a call.
        live = _strip_comments(_source())
        assert live.count("moveCurrencyToXAxis(layout);") == 2

    def test_base_layout_still_puts_money_on_the_y_axis(self):
        # The helper moves what baseLayout sets. If baseLayout stops
        # setting a tickformat, the helper silently propagates undefined.
        match = re.search(
            r"function baseLayout\(.*?\n\}", _strip_comments(_source()), re.S
        )
        assert match
        assert "tickformat: currencyTickformat()" in match.group(0)


class TestMinusSignPrecedesTheCurrencySymbol:
    """One convention for negative money on every axis: -EUR30M.

    Plotly's ``tickprefix`` renders before the sign, so a prefixed axis
    reads "EUR-30M" while the hand-formatted symlog axis reads
    "-EUR10k". The fix is to let d3-format place the symbol, which it
    does after the sign, and to match Plotly's own minus glyph in the
    hand-formatted labels.
    """

    def test_money_axes_use_the_d3_currency_type_not_a_prefix(self):
        # `tickprefix` anywhere on a money axis reintroduces "EUR-30M".
        live = _strip_comments(_source())
        assert "tickprefix" not in live, (
            "a tickprefix renders before the minus sign; use the "
            "d3-format currency type instead"
        )
        assert '"$~s"' in live, "no d3-format currency tickformat found"

    def test_the_currency_symbol_comes_from_a_registered_locale(self):
        # d3-format's "$" emits the LOCALE's currency, so the format
        # string alone is not enough -- without registration every axis
        # silently falls back to a dollar sign.
        live = _strip_comments(_source())
        assert re.search(
            r"format:\s*\{\s*currency:\s*\[\s*getCurrencySymbol\(\)",
            live,
        ), "the registered locale does not take the app's currency symbol"

    def test_the_registered_locale_is_the_one_plotly_is_told_to_use(self):
        # A name mismatch between the registration and the plot config
        # is the silent-fallback failure: every chart renders "$".
        live = _strip_comments(_source())
        assert re.search(r"name:\s*CURRENCY_LOCALE", live), (
            "the locale is not registered under CURRENCY_LOCALE"
        )
        assert re.search(r"locale:\s*CURRENCY_LOCALE", live), (
            "PLOT_CONFIG does not point Plotly at CURRENCY_LOCALE"
        )

    def test_hand_formatted_ticks_use_plotlys_minus_glyph(self):
        # Plotly emits U+2212; an ASCII hyphen here would render a
        # visibly different dash one chart across.
        match = re.search(
            r"function fmtTick\(v\)\s*\{(?P<body>.*?)\n\}",
            _strip_comments(_source()),
            re.S,
        )
        assert match, "fmtTick not found in charts.js"
        assert "-" not in match.group("body"), (
            "fmtTick builds its sign from an ASCII hyphen, not U+2212"
        )
        assert re.search(r'MINUS\s*=\s*"−"', _strip_comments(_source())), (
            "no U+2212 MINUS constant found"
        )
