"""Region bundle contract and source-cited value fixtures.

Every shipped value's justification lives here with its citation, so a
wrong number fails a build instead of decaying silently in prose. See
docs/multi-region-spec.md 7.1 for why: during research a summarizer
fabricated a plausible but entirely fictitious statute article.
"""

import re
import sys
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from simulator.api import config_from_dict
from simulator.regions import list_regions

_FIELDS_JS = Path(__file__).parent.parent / "src/simulator/static/js/fields.js"

# Every INPUT_DEFS entry that declares min/max. Update deliberately when
# a slider is added or removed -- see the canary test below.
_EXPECTED_BOUNDED_FIELDS = 25


def _field_steps() -> dict[str, tuple[Fraction, Fraction]]:
    """Parse ``(min, step)`` per key out of the fields.js INPUT_DEFS.

    Exact rationals, not floats: the whole point is a divisibility test,
    and ``0.1`` is not representable in binary so ``12.07 % 0.1`` is
    nonzero for reasons that have nothing to do with the slider.

    Examples
    --------
    .. code-block:: python

        grid = _field_steps()
        minimum, step = grid["closingCostBuyerPct"]
        assert (Fraction("12.07") - minimum) % step == 0

    """
    grid: dict[str, tuple[Fraction, Fraction]] = {}
    pattern = re.compile(
        r'key:\s*"(?P<key>\w+)".*?min:\s*(?P<min>-?[\d.]+)'
        r".*?step:\s*(?P<step>[\d.]+)"
    )
    for line in _FIELDS_JS.read_text(encoding="utf-8").splitlines():
        match = pattern.search(line)
        if match:
            scale_match = re.search(r"scale:\s*([\d.]+)", line)
            scale = Fraction(scale_match.group(1)) if scale_match else Fraction(1)
            grid[match.group("key")] = (
                Fraction(match.group("min")) / scale,
                Fraction(match.group("step")) / scale,
            )
    return grid


def _field_bounds() -> dict[str, tuple[float, float]]:
    """Parse min/max per key out of the fields.js INPUT_DEFS literal.

    There is no JS test harness in this repo (spec 8.4), so this regex
    parse is the only automated guard that a shipped region value is
    reachable from the UI and survives the share-URL validator.

    Examples
    --------
    .. code-block:: python

        bounds = _field_bounds()
        assert bounds["closingCostBuyerPct"][1] >= 12.07

    """
    bounds: dict[str, tuple[float, float]] = {}
    pattern = re.compile(
        r'key:\s*"(?P<key>\w+)".*?min:\s*(?P<min>-?[\d.]+)'
        r".*?max:\s*(?P<max>-?[\d.]+)"
    )
    for line in _FIELDS_JS.read_text(encoding="utf-8").splitlines():
        match = pattern.search(line)
        if match:
            scale_match = re.search(r"scale:\s*([\d.]+)", line)
            scale = float(scale_match.group(1)) if scale_match else 1.0
            bounds[match.group("key")] = (
                float(match.group("min")) / scale,
                float(match.group("max")) / scale,
            )
    return bounds


def _segmented_options(key: str) -> list[float]:
    """Allowed values for a segmented INPUT_DEFS entry.

    Examples
    --------
    .. code-block:: python

        assert 30 in _segmented_options("mortgageTermYears")

    """
    pattern = re.compile(rf'key:\s*"{key}".*?options:\s*\[(?P<opts>[^\]]*)\]')
    for line in _FIELDS_JS.read_text(encoding="utf-8").splitlines():
        match = pattern.search(line)
        if match:
            return [float(x) for x in match.group("opts").split(",")]
    raise AssertionError(f"no segmented options found for {key}")


# Fields a config needs that no region bundle supplies (the outlook trio
# plus the horizon), so a bundle can be constructed in isolation.
_NON_REGION_DEFAULTS = {
    "horizonYears": 10,
    "propertyAppreciationAnnual": 3.0,
    "equityGrowthAnnual": 7.0,
    "rentInflationRate": 0.03,
    "downPaymentPct": 20,
}

# The outlook presets own these; a region that also set them would fight
# the outlook pills non-deterministically (spec 4.0 rule 2).
_OUTLOOK_KEYS = {
    "propertyAppreciationAnnual",
    "equityGrowthAnnual",
    "rentInflationRate",
}


def _available():
    return [r for r in list_regions() if r["available"]]


def _config_for(region, first_time_buyer=False):
    payload = {
        **_NON_REGION_DEFAULTS,
        **region["typical"],
        **region["taxPrimitives"],
    }
    if first_time_buyer:
        payload.update(region["firstTimeBuyerOverrides"])
    return config_from_dict(payload)


class TestBundleContract:
    def test_every_available_bundle_has_the_same_tax_primitive_keys(self):
        # applyPreset is a bare Object.assign, so an omitted key LEAKS
        # from the previously selected region (spec 4.0 rule 1). This is
        # the highest-value structural test in the change.
        keysets = {r["id"]: frozenset(r["taxPrimitives"]) for r in _available()}
        reference = keysets["us"]
        for region_id, keys in keysets.items():
            assert keys == reference, (
                f"{region_id}: missing {sorted(reference - keys)}, "
                f"extra {sorted(keys - reference)}"
            )

    def test_every_available_bundle_has_the_same_typical_keys(self):
        keysets = {r["id"]: frozenset(r["typical"]) for r in _available()}
        reference = keysets["us"]
        for region_id, keys in keysets.items():
            assert keys == reference, f"{region_id}: {sorted(keys ^ reference)}"

    def test_no_bundle_sets_the_outlook_trio(self):
        for region in _available():
            for block in ("typical", "taxPrimitives"):
                assert not (_OUTLOOK_KEYS & set(region[block])), (
                    f"{region['id']}.{block} writes an outlook key"
                )

    def test_every_bundle_declares_the_amortisation_term(self):
        # Parsed, not hard-coded: a literal tuple here would silently
        # drift from fields.js's segmented options.
        allowed = _segmented_options("mortgageTermYears")
        for region in _available():
            assert region["typical"]["mortgageTermYears"] in allowed

    def test_every_bundle_is_constructible(self):
        for region in _available():
            assert _config_for(region) is not None
            assert _config_for(region, first_time_buyer=True) is not None

    def test_every_bundle_carries_ftb_overrides_and_notes(self):
        for region in _available():
            assert isinstance(region["firstTimeBuyerOverrides"], dict)
            assert isinstance(region["notes"], list)
            assert all(isinstance(note, str) for note in region["notes"])

    def test_every_bundle_declares_an_ftb_price_ceiling(self):
        # The relief defaults ON, so every bundle must state where it
        # stops applying -- None meaning "no ceiling in the sourced
        # material", never a missing key that reads as the same thing by
        # accident.
        for region in _available():
            assert "firstTimeBuyerMaxPrice" in region, region["id"]
            cap = region["firstTimeBuyerMaxPrice"]
            assert cap is None or cap > 0, f"{region['id']}: {cap}"

    def test_ftb_ceilings_match_the_statute(self):
        # gov.uk: "If the price is over GBP500,000, you cannot claim the
        # relief." The NL startersvrijstelling is capped at EUR555,000
        # (also age 18-35, own occupancy -- disclosed in notes since the
        # tool cannot know either).
        by_id = {r["id"]: r for r in _available()}
        assert by_id["uk"]["firstTimeBuyerMaxPrice"] == 500_000.0
        assert by_id["nl"]["firstTimeBuyerMaxPrice"] == 555_000.0
        # No relief enacted at all, so no ceiling to declare.
        assert by_id["us"]["firstTimeBuyerMaxPrice"] is None
        assert by_id["de"]["firstTimeBuyerMaxPrice"] is None

    def test_a_ceiling_is_declared_wherever_notes_describe_a_cliff(self):
        # The UK cliff was disclosed in notes but not enforced, and NL's
        # was enforced nowhere and disclosed nowhere. Any region whose
        # notes tell the user relief stops must also carry the ceiling
        # that makes the UI act on it.
        for region in _available():
            joined = " ".join(region["notes"]).lower()
            describes_cliff = "cannot claim the relief" in joined or (
                "startersvrijstelling" in joined and "or less" in joined
            )
            if describes_cliff:
                assert region["firstTimeBuyerMaxPrice"] is not None, (
                    f"{region['id']}: notes describe a relief cliff but no "
                    "firstTimeBuyerMaxPrice enforces it"
                )

    def test_nl_discloses_the_startersvrijstelling_conditions(self):
        # Verdict-relevant and previously absent: the value cap and the
        # age condition reached docs/multi-region-spec.md but never the
        # user, while the relief defaulted ON.
        nl = next(r for r in _available() if r["id"] == "nl")
        notes = " ".join(nl["notes"])
        assert "555,000" in notes or "555.000" in notes
        assert "18" in notes and "35" in notes

    def test_maintenance_path_is_exclusive(self):
        # Each region takes the path its own evidence unit dictates
        # (spec P3): UK/DE/FR absolute, NL/US percentage. Guards against a
        # future contributor "tidying" NL onto the absolute path and
        # freezing a value-proportional convention at one price.
        for region in _available():
            primitives = region["taxPrimitives"]
            pct = primitives["annualMaintenancePct"]
            amount = primitives["annualMaintenanceAmount"]
            assert (pct > 0) != (amount > 0), (
                f"{region['id']}: exactly one maintenance path must be live"
            )


class TestUnitedStates:
    def test_us_values_are_untouched_by_the_multi_region_work(self):
        primitives = next(r for r in list_regions() if r["id"] == "us")["taxPrimitives"]
        assert primitives["closingCostBuyerPct"] == 3.0
        assert primitives["propertyTaxRate"] == 1.2
        assert primitives["annualMaintenancePct"] == 1.0
        assert primitives["levyDeductionCap"] == 10000.0
        assert primitives["saleCgRegime"] == "exempt_amount"

    def test_us_new_primitives_are_all_inert(self):
        primitives = next(r for r in list_regions() if r["id"] == "us")["taxPrimitives"]
        assert primitives["closingCostBuyerAmount"] == 0.0
        assert primitives["annualPropertyLevy"] == 0.0
        assert primitives["levyPaidByOccupier"] is False
        assert primitives["annualMaintenanceAmount"] == 0.0
        assert primitives["portfolioDeemedReturnPct"] == 0.0
        assert primitives["portfolioDragRatePct"] == 0.0


class TestFrance:
    @staticmethod
    def _fr():
        return next(r for r in list_regions() if r["id"] == "fr")

    def test_non_primo_buyer_cost_matches_the_verified_band(self):
        # DMTO 6.318 + CSI 0.10 + emoluments ~1.05 = 7.468%, plus ~1,300
        # of price-invariant notaire debours.
        #   0.07468 * 290,000 + 1,300 = 22,957 = 7.916% of price,
        # inside the verified 7.90-8.00% band.
        primitives = self._fr()["taxPrimitives"]
        total = (
            290_000 * primitives["closingCostBuyerPct"] / 100
            + primitives["closingCostBuyerAmount"]
        )
        assert abs(total - 22_957.20) < 0.01
        assert abs(total / 290_000 * 100 - 7.9163) < 1e-3

    def test_primo_accedant_relief_is_051_pp(self):
        # The primo-accedant carve-out from the departmental increase is
        # worth 0.51pp -- NOT the 1.5pp claimed in earlier research.
        #   0.06958 * 290,000 + 1,300 = 21,478 = 7.406%
        region = self._fr()
        base = region["taxPrimitives"]["closingCostBuyerPct"]
        ftb = region["firstTimeBuyerOverrides"]["closingCostBuyerPct"]
        assert abs(base - ftb - 0.51) < 1e-9
        total = 290_000 * ftb / 100 + region["taxPrimitives"]["closingCostBuyerAmount"]
        assert abs(total - 21_478.20) < 0.01

    def test_sale_is_exempt_with_no_duration_condition(self):
        # CGI art. 150 U II 1 -- the primary-residence exemption carries no
        # holding-period condition.
        assert self._fr()["taxPrimitives"]["saleCgRegime"] == "fully_exempt"

    def test_portfolio_cg_rate_is_314_not_the_superseded_30(self):
        # 12.8% PFU + 18.6% PS. The PS rise came via LFSS 2026,
        # LOI 2025-1403 art. 12 (CSG 9.2 -> 10.6). ADR-0007's "30% PFU" is
        # superseded; see its 2026-07 amendment.
        assert self._fr()["taxPrimitives"]["portfolioCgRatePct"] == 31.4

    def test_home_sale_cg_rate_excludes_the_2026_social_levy_rise(self):
        # 19% IR + 17.2% PS. The rise does NOT apply to plus-values
        # immobilieres, which stay at 17.2%.
        assert self._fr()["taxPrimitives"]["saleCgRatePct"] == 36.2

    def test_levy_is_flat_and_owner_borne(self):
        # Taxe fonciere is assessed on valeur locative cadastrale (a
        # notional 1970 rent), so the base does not track market prices.
        # Taxe d'habitation on main residences was abolished in 2023, so
        # the renter bears nothing.
        primitives = self._fr()["taxPrimitives"]
        assert primitives["propertyTaxRate"] == 0.0
        assert primitives["annualPropertyLevy"] == 1220.0
        assert primitives["levyPaidByOccupier"] is False

    def test_rent_is_the_corrected_oll_figure(self):
        # 812 EUR/mo from Observatoires Locaux des Loyers 2024 microdata
        # (n = 9,362, zone-3 median 12.50 EUR/m2). The superseded 1,100 was
        # above the encadrement majored ceiling in EVERY Lyon zone.
        assert self._fr()["typical"]["monthlyRent"] == 812

    def test_low_confidence_maintenance_carries_its_caveat(self):
        notes = " ".join(self._fr()["notes"]).lower()
        assert "maintenance" in notes


class TestGermany:
    @staticmethod
    def _de():
        return next(r for r in list_regions() if r["id"] == "de")

    def test_buyer_cost_at_the_preset_price(self):
        # GrESt 6.5 (NRW, Landtag Drucksache 16/7147, effective 01.01.2015)
        # + Notar/Grundbuch 2.0 + Makler 3.57 (incl. USt) = 12.07%
        #   0.1207 * 339,000 = 40,917.30
        primitives = self._de()["taxPrimitives"]
        total = (
            339_000 * primitives["closingCostBuyerPct"] / 100
            + primitives["closingCostBuyerAmount"]
        )
        assert abs(total - 40_917.30) < 0.01

    def test_sale_is_exempt_at_any_holding_period(self):
        # 23 Abs.1 Nr.1 Satz 3 EStG, owner-occupier limb: exempt at ANY
        # holding period. The 10-year speculation period applies to
        # NON-owner-occupied property, which this tool does not model.
        # ADR-0007's "sale tax-free after a 10-year hold" is wrong for the
        # case modelled here; see its 2026-07 amendment.
        assert self._de()["taxPrimitives"]["saleCgRegime"] == "fully_exempt"

    def test_levy_and_insurance_are_umlagefaehig(self):
        # BetrKV 2 Nr.1 (Grundsteuer) and Nr.13 (Wohngebaeudeversicherung)
        # are umlagefaehig, so German Kaltmiete excludes them and the
        # tenant bears them.
        primitives = self._de()["taxPrimitives"]
        assert primitives["levyPaidByOccupier"] is True
        assert primitives["annualHomeInsurance"] == 0.0

    def test_maintenance_is_area_proportional_not_value_proportional(self):
        # 28 Abs.2 II. BV states the convention in EUR/m2/yr (9.00),
        # explicitly not value-linked: 9.00 x 80 m2 = 720 EUR
        # Instandhaltungsruecklage + Verwalter + Sondereigentum ~ 1,700.
        # Scoped to the NON-umlagefaehig components only.
        primitives = self._de()["taxPrimitives"]
        assert primitives["annualMaintenancePct"] == 0.0
        assert primitives["annualMaintenanceAmount"] == 1700.0

    def test_amortisation_term_is_30_not_the_zinsbindung(self):
        # A 4.0% rate with the conventional 2% anfaengliche Tilgung fully
        # repays in ~29 years. The 15 in the research is the Zinsbindung
        # (the fixing period), NOT the amortisation term. Shipping 15 would
        # inflate the monthly payment and badly bias DE toward renting.
        assert self._de()["typical"]["mortgageTermYears"] == 30

    def test_price_and_rent_reproduce_their_own_derivation(self):
        # Matched pair over the SAME 259 sold-and-rented condos:
        #   4,239 EUR/m2 x 80 m2 = 339,120 -> ships 339,000
        #   12.40 EUR/m2 x 80 m2 = 992
        # Superseded: 400,000, then 345,000 -- the latter did not
        # reproduce from its own 4,239 EUR/m2 and gave P/R 28.2.
        typical = self._de()["typical"]
        assert typical["propertyPrice"] == 339000
        assert typical["monthlyRent"] == 992  # Kaltmiete, same matched pair

    def test_price_to_rent_reproduces_the_research_headline_ratio(self):
        # 339,000 / (992 x 12) = 28.478 -> 28.48, reproducing the
        # research's own stated P/R of 28.5. The superseded 345,000/1,020
        # pair gave 28.2. A derivation that regenerates the source's
        # headline ratio is more trustworthy than a rounded price that
        # does not. Genuine, not a Kaltmiete artefact: on the most
        # conservative Warmmiete basis it is 36.6.
        typical = self._de()["typical"]
        ratio = typical["propertyPrice"] / (typical["monthlyRent"] * 12)
        assert abs(ratio - 28.48) < 0.005

    def test_vorabpauschale_is_deliberately_not_modelled(self):
        # ~0.41%/yr for 2026, but CREDITABLE against tax at exit -- a
        # timing drag, not a permanent tax. P5 models a permanent tax, so
        # applying it here would overstate the German cost by construction.
        primitives = self._de()["taxPrimitives"]
        assert primitives["portfolioDeemedReturnPct"] == 0.0
        assert primitives["portfolioDragRatePct"] == 0.0

    def test_no_ftb_relief_is_enacted(self):
        assert self._de()["firstTimeBuyerOverrides"] == {}

    def test_weakest_values_carry_their_caveats(self):
        notes = " ".join(self._de()["notes"]).lower()
        assert "grundsteuer" in notes  # the L-rated levy
        assert "makler" in notes  # the conditional 3.57pp


class TestNetherlands:
    @staticmethod
    def _nl():
        return next(r for r in list_regions() if r["id"] == "nl")

    def test_eigenwoningforfait_is_an_exact_algebraic_identity(self):
        # EWF adds 0.35% of WOZ to box-1 income, taxed at the marginal rate
        # and netted against deductible interest. In cash terms that is
        # identical to a levy of 0.35% x 37.56% = 0.13146% of WOZ. Total:
        #   0.15% (owner-specific public charges) + 0.13146% = 0.28146%
        # This is NOT a fudged effective rate -- it is an exact reduction,
        # asserted here as arithmetic rather than trusted as prose.
        rate = self._nl()["taxPrimitives"]["propertyTaxRate"]
        assert abs(rate - (0.15 + 0.35 * 0.3756)) < 1e-4
        assert rate == 0.2815

    def test_marginal_rate_is_the_tariefsaanpassing_maximum(self):
        # 37.56% is the 2026 tariefsaanpassing maximum -- NOT the 49.5%
        # top income rate. The identity above depends on the SAME rate
        # applying to the addback and the deduction, true by construction.
        assert self._nl()["taxPrimitives"]["marginalTaxRatePct"] == 37.56

    def test_levy_is_not_deductible_and_zero_means_exactly_that(self):
        # Requires the api.js sentinel fix: client 0 used to map to null,
        # and null means UNCAPPED. Left unfixed, NL would silently deduct
        # its own levy -- 0.2815% x 490,000 x 37.56% = 518 EUR/yr, ~5,200
        # over a 10-year horizon, credited to the WRONG arm.
        assert self._nl()["taxPrimitives"]["levyDeductionCap"] == 0.0

    def test_box_3_ships_two_separate_operands_not_a_product(self):
        # 6.00% deemed return and 36% rate, both definitive for 2026 and
        # enacted at 2026-01-01 (Wet IB 2001 art. 5.2 lid 2 / 5.5 / 2.13).
        # They ship SEPARATELY because Wet IB 2001 art. 5.25 assesses the
        # taxpayer on min(deemed, actual) floored at nil -- a test
        # asserting a pre-multiplied 2.16 would lock in the ~1.65x
        # overtax the split exists to remove. Do not "simplify" these.
        primitives = self._nl()["taxPrimitives"]
        assert primitives["portfolioDeemedReturnPct"] == 6.0
        assert primitives["portfolioDragRatePct"] == 36.0

    def test_superseded_introduction_figures_are_not_shipped(self):
        # 7.78% / EUR 51,396 were Belastingplan 2026 AS INTRODUCED and
        # were struck by adopted amendment nr. 47 -- real documents,
        # never law. Do not reintroduce them.
        primitives = self._nl()["taxPrimitives"]
        assert primitives["portfolioDeemedReturnPct"] != 7.78

    def test_box_1_dwelling_is_outside_box_3(self):
        # Wet IB 2001 art. 2.14 lid 2: the owner-occupied dwelling sits in
        # box 1 and is entirely outside box 3, and the box-1 mortgage does
        # not offset box-3 assets. The Netherlands taxes the renter's
        # wealth annually and exempts the buyer's completely -- the whole
        # NL story, and it emerges from portfolio SIZE, not a branch.
        assert self._nl()["taxPrimitives"]["saleCgRegime"] == "fully_exempt"

    def test_no_capital_gains_tax_on_either_the_home_or_the_portfolio(self):
        primitives = self._nl()["taxPrimitives"]
        assert primitives["saleCgRegime"] == "fully_exempt"  # eigen woning, box 1
        assert primitives["saleCgRatePct"] == 0.0
        assert primitives["portfolioCgRatePct"] == 0.0  # the burden is box 3

    def test_maintenance_stays_on_the_percentage_path_deliberately(self):
        # Nibud ("ruim 1%" per year) and Vereniging Eigen Huis (1% of WOZ)
        # both state this VALUE-PROPORTIONALLY. Converting 1.0% into
        # ~4,900 EUR at the default price would discard the rescaling
        # behaviour the sources actually assert and launder a value-
        # proportional convention into a frozen constant. DO NOT "tidy"
        # this onto the absolute path (spec P3).
        primitives = self._nl()["taxPrimitives"]
        assert primitives["annualMaintenancePct"] == 1.0
        assert primitives["annualMaintenanceAmount"] == 0.0

    def test_startersvrijstelling_is_a_2pp_relief(self):
        # 0% vs 2% overdrachtsbelasting (age 18-35, own occupancy,
        # value <= 555,000) -- a ~9,000 EUR swing.
        region = self._nl()
        base = region["taxPrimitives"]["closingCostBuyerPct"]
        ftb = region["firstTimeBuyerOverrides"]["closingCostBuyerPct"]
        assert abs(base - ftb - 2.0) < 1e-9

    def test_interest_deduction_is_on(self):
        assert self._nl()["taxPrimitives"]["interestDeductionEnabled"] is True

    def test_low_confidence_rent_and_forward_risk_carry_caveats(self):
        notes = " ".join(self._nl()["notes"]).lower()
        assert "rent" in notes
        assert "heffingsvrij" in notes  # the unmodelled box-3 exemption
        assert "2028" in notes  # the regime's known expiry date


class TestUnitedKingdom:
    @staticmethod
    def _uk():
        return next(r for r in list_regions() if r["id"] == "uk")

    def test_sdlt_linear_identity_is_exact_at_the_preset_price(self):
        # SDLT 2026/27 England & NI, standard single dwelling (gov.uk):
        #   0% to 125,000 | 2% to 250,000 | 5% to 925,000 | 10% to 1.5m
        # For P in (250,000, 925,000]:
        #   SDLT(P) = 0.02*125,000 + 0.05*(P - 250,000) = 0.05P - 10,000
        # Plus ~3,100 of price-invariant fees:  C(P) = 0.05P - 6,900
        # At the England semi-detached price of 289,106:
        #   0.05 * 289,106 - 6,900 = 7,555.30, of which SDLT = 4,455.30
        primitives = self._uk()["taxPrimitives"]
        total = (
            289_106 * primitives["closingCostBuyerPct"] / 100
            + primitives["closingCostBuyerAmount"]
        )
        assert abs(total - 7_555.30) < 1e-6
        assert abs(total - 3_100.0 - 4_455.30) < 1e-6  # SDLT alone

    def test_ftb_pays_fees_only(self):
        # First-time-buyer relief takes SDLT to zero at this price.
        region = self._uk()
        overrides = region["firstTimeBuyerOverrides"]
        total = (
            289_106 * overrides["closingCostBuyerPct"] / 100
            + overrides["closingCostBuyerAmount"]
        )
        assert abs(total - 3_100.0) < 1e-9

    def test_council_tax_is_flat_and_occupier_borne(self):
        # England average Band D 2026/27 = 2,392 (2,343 excl. parish
        # precepts). Bands are fixed on 1 April 1991 values and band
        # amounts are ninths of Band D (LGFA 1992 s.5). The resident is
        # liable (LGFA 1992 s.6(2)), so the renter bears it too.
        primitives = self._uk()["taxPrimitives"]
        assert primitives["propertyTaxRate"] == 0.0
        assert primitives["annualPropertyLevy"] == 2392.0
        assert primitives["levyPaidByOccupier"] is True

    def test_maintenance_is_observed_spend_not_a_percentage(self):
        # ONS Family Spending FYE2025 puts England maintenance-and-repair
        # at 634/yr across all households; scaled to ~65% owner-occupation,
        # ~900/yr. 1.0% of 289,106 would be 2,891 -- an overstatement of
        # 3.2x. This is a LOWER bound: the survey is recall-based and
        # under-captures lumpy repairs.
        primitives = self._uk()["taxPrimitives"]
        assert primitives["annualMaintenancePct"] == 0.0
        assert primitives["annualMaintenanceAmount"] == 900.0

    def test_seller_cost_is_already_vat_inclusive(self):
        # The 1.42% agent fee is VAT-INCLUSIVE; the Property Ombudsman has
        # required VAT-inclusive quoting since October 2016. Do NOT add 20%.
        assert self._uk()["taxPrimitives"]["closingCostSellerPct"] == 1.75

    def test_sale_is_exempt_via_private_residence_relief(self):
        assert self._uk()["taxPrimitives"]["saleCgRegime"] == "fully_exempt"

    def test_no_interest_deduction_since_miras_withdrawal(self):
        assert self._uk()["taxPrimitives"]["interestDeductionEnabled"] is False

    def test_amortisation_term_is_25_not_the_fix(self):
        # A 5yr fix on a 25-year amortisation. The 5 is the fix.
        assert self._uk()["typical"]["mortgageTermYears"] == 25

    def test_label_names_the_actual_jurisdiction(self):
        # SDLT is England & NI only; Scotland uses LBTT and Wales LTT,
        # with no FTB relief in Wales. A plain "United Kingdom" label would
        # silently misprice ~16% of the population.
        label = self._uk()["label"]
        assert "England" in label and "NI" in label

    def test_sdlt_divergences_above_the_linear_band_are_pinned(self):
        # The two-parameter form is EXACT over 250k-925k and diverges
        # outside it. These assert the MODEL's value and record the true
        # one, so the known gaps cannot silently drift. They document the
        # gap; they do not bless it.
        primitives = self._uk()["taxPrimitives"]

        def model(price):
            return max(
                price * primitives["closingCostBuyerPct"] / 100
                + primitives["closingCostBuyerAmount"],
                0.0,
            )

        # S18: above 925,000 the marginal rate steps to 10% then 12%,
        # but the model's line stays at 5%.
        assert abs(model(1_000_000) - 43_100.0) < 1e-6  # true 46,850 (-3,750)
        assert abs(model(2_000_000) - 93_100.0) < 1e-6  # true 156,850 (-63,750, 41%)
        # S6: under-charged across the whole 125k-250k band, clamped to
        # zero below 138,000. Worst point 138,000: true 3,360.
        assert model(138_000) == 0.0

    def test_ftb_divergences_are_pinned(self):
        # S19: FTB relief is 5% between 300,000 and 500,000, not 0%, and
        # is withdrawn ENTIRELY above 500,000.
        overrides = self._uk()["firstTimeBuyerOverrides"]

        def model(price):
            return max(
                price * overrides["closingCostBuyerPct"] / 100
                + overrides["closingCostBuyerAmount"],
                0.0,
            )

        assert abs(model(400_000) - 3_100.0) < 1e-6  # true 8,100  (-5,000)
        assert abs(model(450_000) - 3_100.0) < 1e-6  # true 10,600 (-7,500)
        assert abs(model(500_000) - 3_100.0) < 1e-6  # true 13,100 (-10,000)
        # S5, the sharpest bias in the change: above 500,000 an FTB owes
        # the FULL charge. At 501,000 that is 15,050 SDLT + 3,100 fees =
        # 18,150 against the model's 3,100 -- 15,050 understated.
        assert abs(model(501_000) - 3_100.0) < 1e-6

    def test_sharpest_known_biases_are_disclosed(self):
        notes = " ".join(self._uk()["notes"])
        assert "£500,000" in notes  # the FTB relief withdrawal cliff
        assert "£925,000" in notes  # the SDLT band divergence above the line
        assert "council tax" in notes.lower()  # the rent-exclusivity premise


class TestAllRegionsShip:
    def test_every_region_is_available(self):
        # Phase 2 delivers FOUR new regions, not three. This test is what
        # stops a bundle being quietly shipped disabled.
        unavailable = [r["id"] for r in list_regions() if not r["available"]]
        assert unavailable == [], f"not shipped: {unavailable}"

    def test_all_five_regions_are_present(self):
        assert {r["id"] for r in list_regions()} == {"us", "fr", "de", "nl", "uk"}

    def test_no_bundle_has_a_null_data_block(self):
        for region in list_regions():
            assert region["typical"] is not None
            assert region["taxPrimitives"] is not None


class TestBundleValuesAreReachableFromTheUi:
    def test_parser_canary_named_fields(self):
        bounds = _field_bounds()
        assert "closingCostBuyerPct" in bounds
        assert "propertyPrice" in bounds
        assert bounds["levyDeductionCap"][0] < 0  # the uncapped sentinel
        assert bounds["closingCostBuyerPct"][1] >= 12.07  # the DE blocker

    def test_parser_canary_count(self):
        # The parser is line-based: an INPUT_DEFS entry wrapped onto two
        # lines silently drops out while the named canary above still
        # passes, and the range check would then vacuously skip it. This
        # count is the guard. If you added or removed a slider, update
        # _EXPECTED_BOUNDED_FIELDS deliberately.
        assert len(_field_bounds()) == _EXPECTED_BOUNDED_FIELDS

    def test_every_numeric_bundle_value_is_inside_its_slider_range(self):
        # state.js NUMERIC_RANGES derives from these bounds and DROPS
        # out-of-range values on share-URL restore, falling back to
        # DEFAULT_CONFIG -- i.e. silently to the US value, with no visible
        # symptom. This is the test that would have caught DE's
        # closingCostBuyerPct 12.07 against max 10.
        bounds = _field_bounds()
        for region in _available():
            blocks = [
                region["typical"],
                region["taxPrimitives"],
                region["firstTimeBuyerOverrides"],
            ]
            for block in blocks:
                for key, value in block.items():
                    if key not in bounds or isinstance(value, bool):
                        continue
                    low, high = bounds[key]
                    assert low <= value <= high, (
                        f"{region['id']}.{key} = {value} is outside the "
                        f"fields.js range [{low}, {high}]"
                    )

    def test_statutory_values_sit_on_their_slider_step_grid(self):
        # A range input snaps its thumb to min + n*step while the readout
        # prints the unsnapped number, so an off-grid value makes the
        # widget disagree with the config and the first drag silently
        # rewrites a sourced figure.
        #
        # Enforced for taxPrimitives and the FTB overrides only. Those
        # are statute -- 12.07% vs 12.1% is a different tax. `typical`
        # is deliberately exempt: those are market medians carrying far
        # more uncertainty than the step (NL rent ships a +-11% band),
        # round stepping is the right interaction for them, and the
        # resulting thumb offset is a fraction of a pixel.
        grid = _field_steps()
        for region in _available():
            for block in ("taxPrimitives", "firstTimeBuyerOverrides"):
                for key, value in region[block].items():
                    if key not in grid or isinstance(value, bool):
                        continue
                    minimum, step = grid[key]
                    offset = Fraction(str(value)) - minimum
                    assert offset % step == 0, (
                        f"{region['id']}.{key} = {value} is off the "
                        f"fields.js grid (min {float(minimum)}, step "
                        f"{float(step)}); the thumb would snap to "
                        f"{float(minimum + round(offset / step) * step)}"
                    )
