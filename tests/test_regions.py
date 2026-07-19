"""Region bundle contract and source-cited value fixtures.

Every shipped value's justification lives here with its citation, so a
wrong number fails a build instead of decaying silently in prose. See
docs/multi-region-spec.md 7.1 for why: during research a summarizer
fabricated a plausible but entirely fictitious statute article.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from simulator.api import config_from_dict
from simulator.regions import list_regions

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
        for region in _available():
            assert region["typical"]["mortgageTermYears"] in (15, 20, 25, 30)

    def test_every_bundle_is_constructible(self):
        for region in _available():
            assert _config_for(region) is not None
            assert _config_for(region, first_time_buyer=True) is not None

    def test_every_bundle_carries_ftb_overrides_and_notes(self):
        for region in _available():
            assert isinstance(region["firstTimeBuyerOverrides"], dict)
            assert isinstance(region["notes"], list)
            assert all(isinstance(note, str) for note in region["notes"])

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
