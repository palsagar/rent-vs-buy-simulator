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
    """The symbol follows the sign everywhere: -EUR30M, not EUR-30M.

    Plotly's ``tickprefix`` renders before the sign, so a prefixed axis
    read "EUR-30M" while the hand-formatted symlog axis read "-EUR10k".
    The fix is to let d3-format place the symbol, which it does after
    the sign, and to match Plotly's own minus glyph in the
    hand-formatted labels.

    ORDERING is what is unified here, not the glyph. Ticks carry U+2212
    and hovers an ASCII hyphen, because Plotly rewrites the sign only on
    the tick path; see the MONEY_HOVER comment in charts.js.
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

    def test_hover_money_uses_the_same_currency_type_as_the_axes(self):
        # Hovers are the other money surface, and a hand-built
        # `${getCurrencySymbol()}%{x:,.0f}` prefix reproduces the exact
        # defect there: the tornado read "EUR-3,986,681" while its own
        # axis read "-EUR150k". d3 honours the locale in hovertemplates
        # too, so both surfaces can share one convention.
        live = _strip_comments(_source())
        for match in re.finditer(r"hovertemplate:\s*`(?P<tpl>[^`]*)`", live):
            tpl = match.group("tpl")
            assert "getCurrencySymbol()" not in tpl, (
                f"hovertemplate hand-prefixes the currency: {tpl}"
            )
            assert "${cur}" not in tpl, (
                f"hovertemplate hand-prefixes the currency: {tpl}"
            )
        assert re.search(r'MONEY_HOVER\s*=\s*"\$,\.0f"', live), (
            "no d3 currency hover format found"
        )

    def test_no_hovertemplate_formats_money_without_the_currency(self):
        # Guards the constant being defined but only half-adopted,
        # WITHOUT hardcoding a template count: a future non-money hover
        # (a percentage, a year) must not be forced to adopt MONEY_HOVER
        # just to keep a tally happy. What is banned is the bare
        # thousands format, which is money stripped of its currency.
        live = _strip_comments(_source())
        for match in re.finditer(r"hovertemplate:\s*`(?P<tpl>[^`]*)`", live):
            tpl = match.group("tpl")
            assert not re.search(r"%\{[^}]*:,\.\d f?\}|%\{[^}]*:,\.\df\}", tpl), (
                f"hovertemplate formats money without a currency: {tpl}"
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


def _tornado_body() -> str:
    """Body of renderTornadoChart, comments stripped.

    Examples
    --------
    .. code-block:: python

        assert "customdata" in _tornado_body()

    """
    match = re.search(
        r"export function renderTornadoChart\(el, tornado\)\s*\{(?P<body>.*?)\n\}",
        _strip_comments(_source()),
        re.S,
    )
    assert match, "renderTornadoChart not found in charts.js"
    return match.group("body")


class TestTornadoRangeHover:
    """Each bar's hover states the assumption's own before and after.

    The payload arrives sorted by descending impact and is drawn
    bottom-up, so every array is reversed. A single missed reverse
    attaches one bar's range to another bar's outcome -- both still
    render, and nothing else fails.
    """

    def test_every_payload_array_is_reversed_together(self):
        # params, fields, baseInput, lowInput, highInput and the two
        # outcome arrays all index the same bar. Reversing some and not
        # others silently mislabels every hover.
        body = _tornado_body()
        for key in (
            "params",
            "fields",
            "baseInput",
            "lowInput",
            "highInput",
            "low",
            "high",
        ):
            assert re.search(rf"\[\.\.\.tornado\.{key}\]\.reverse\(\)", body), (
                f"tornado.{key} is not reversed with the others"
            )

    def test_the_lower_bar_gets_the_low_range_and_the_higher_the_high(self):
        # Swapping these renders a "lower" bar whose stated range is an
        # increase -- the hover contradicting its own label.
        body = _tornado_body()
        assert re.search(
            r"x:\s*low,.*?customdata:\s*hoverData\(lowIn,\s*low\).*?tpl\(\"lower\"\)",
            body,
            re.S,
        ), "the lower bar is not paired with the low range and low impact"
        assert re.search(
            r"x:\s*high,.*?customdata:\s*hoverData\(highIn,\s*high\).*?tpl\(\"higher\"\)",
            body,
            re.S,
        ), "the higher bar is not paired with the high range and high impact"

    def test_the_hover_reports_impact_not_the_absolute_verdict(self):
        # On a trace with `base`, %{x} resolves to base + size -- the
        # absolute verdict, not the impact the axis is titled for.
        body = _tornado_body()
        assert "%{customdata[1]:" in body, (
            "the money line does not read the impact out of customdata"
        )
        assert not re.search(r"%\{x:", body), (
            "%{x} on a based bar is the absolute verdict, not the impact"
        )

    def test_the_range_is_rendered_in_display_units(self):
        # INPUT_DEFS min/max are display units and `scale` converts
        # stored -> display, so the stored value is MULTIPLIED. Dividing
        # renders rent inflation (stored 0.03, scale 100) as "0.0%".
        match = re.search(
            r"function fmtFieldValue\(fieldKey, storedValue\)\s*\{(?P<body>.*?)\n\}",
            _strip_comments(_source()),
            re.S,
        )
        assert match, "fmtFieldValue not found in charts.js"
        assert re.search(
            r"storedValue\s*\*\s*\(def\.scale\s*\?\?\s*1\)", match.group("body")
        ), "fmtFieldValue does not scale stored -> display by multiplying"


class TestSymlogTickSign:
    def test_the_minus_is_applied_to_negative_values(self):
        # `v > 0 ? MINUS : ""` still contains no ASCII hyphen and still
        # references the constant, so the glyph tests above pass while
        # every positive tick gains a minus sign.
        match = re.search(
            r"function fmtTick\(v\)\s*\{(?P<body>.*?)\n\}",
            _strip_comments(_source()),
            re.S,
        )
        assert match, "fmtTick not found in charts.js"
        assert re.search(r"v\s*<\s*0\s*\?\s*MINUS", match.group("body")), (
            "fmtTick does not sign strictly-negative values"
        )


class TestHorizontalBarHoversReadTheMoneyAxis:
    """A horizontal bar's money is on X; Y holds the category label.

    ``%{y}: %{y:$,.0f}`` is well-formed, uses the currency format and
    passes every check above -- it just formats a category name as
    money. The pairing has to be asserted per chart, because on the line
    charts money genuinely IS on Y.
    """

    def test_breakdown_labels_from_y_and_formats_money_from_x(self):
        match = re.search(
            r"export function renderBreakdownChart\(.*?\n\}",
            _strip_comments(_source()),
            re.S,
        )
        assert match, "renderBreakdownChart not found in charts.js"
        body = match.group(0)
        assert re.search(r"hovertemplate:\s*`%\{y\}:\s*%\{x:", body), (
            "the breakdown hover does not label from y and read money from x"
        )
