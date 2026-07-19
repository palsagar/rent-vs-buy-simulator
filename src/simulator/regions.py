"""Region preset bundles (ADR-0007): trustworthy defaults per market.

Five bundles ship: US, France (Lyon), Germany (Köln), Netherlands and
the United Kingdom (England & NI). Countries are data, not code — no
per-country branch exists in the engine; each bundle expresses its
regime through the shared scalar primitives on ``SimulationConfig``.

Every value is source-verified, never guessed, and each one's
justification is pinned by a fixture in ``tests/test_regions.py`` with
its citation. Values that are derived rather than primary-sourced, and
every known divergence between a bundle and the real statute, carry a
caveat in that bundle's ``notes`` — rendered in the UI. See
``docs/multi-region-spec.md`` §8 for the full list of known gaps and
their bias directions.
"""

from __future__ import annotations

from typing import Any

REGIONS: list[dict[str, Any]] = [
    {
        "id": "us",
        "label": "United States",
        "available": True,
        "currencySymbol": "$",
        "typical": {
            "propertyPrice": 500000,
            "monthlyRent": 2400,
            "mortgageRateAnnual": 6.5,
            "mortgageTermYears": 30,
        },
        "taxPrimitives": {
            "closingCostBuyerPct": 3.0,
            "closingCostBuyerAmount": 0.0,
            "closingCostSellerPct": 6.0,
            "propertyTaxRate": 1.2,
            "annualPropertyLevy": 0.0,
            "levyPaidByOccupier": False,
            "annualHomeInsurance": 1200.0,
            "annualMaintenancePct": 1.0,
            "annualMaintenanceAmount": 0.0,
            "interestDeductionEnabled": True,
            "marginalTaxRatePct": 24.0,
            "levyDeductionCap": 10000.0,
            "saleCgRegime": "exempt_amount",
            "saleCgExemptAmount": 250000.0,
            "saleCgExemptAfterYears": 10,
            "saleCgRatePct": 15.0,
            "portfolioCgRatePct": 15.0,
            "portfolioDeemedReturnPct": 0.0,
            "portfolioDragRatePct": 0.0,
        },
        "firstTimeBuyerOverrides": {},
        "firstTimeBuyerMaxPrice": None,
        "notes": [
            "Portfolios are modelled as plain taxable brokerage accounts. "
            "401(k)/IRA sheltering is not modelled, which understates the "
            "renter's after-tax returns (ADR-0009).",
        ],
    },
    {
        "id": "fr",
        "label": "France (Lyon)",
        "available": True,
        "currencySymbol": "€",
        "typical": {
            "propertyPrice": 290000,  # M — Lyon existing apartment
            "monthlyRent": 812,  # M — OLL 2024, zone-3 median
            "mortgageRateAnnual": 3.45,  # M — aggregator-corroborated only
            "mortgageTermYears": 25,  # H — standard FR amortisation
        },
        "taxPrimitives": {
            # H — DMTO 6.318 + CSI 0.10 + emoluments ~1.05
            "closingCostBuyerPct": 7.468,
            "closingCostBuyerAmount": 1300.0,  # H — notaire débours, price-invariant
            "closingCostSellerPct": 6.0,  # M
            "propertyTaxRate": 0.0,
            # M — 0.42% x 290,000; Lyon combined TFPB 32.44%
            "annualPropertyLevy": 1220.0,
            # H — taxe d'habitation on main residences abolished 2023
            "levyPaidByOccupier": False,
            "annualHomeInsurance": 220.0,  # M — multirisque habitation
            "annualMaintenancePct": 0.0,
            "annualMaintenanceAmount": 1300.0,  # L — owner-only estimate; see notes
            "interestDeductionEnabled": False,  # H — abolished 2011
            "marginalTaxRatePct": 0.0,
            "levyDeductionCap": 0.0,
            # H — CGI art. 150 U II 1, no duration condition
            "saleCgRegime": "fully_exempt",
            "saleCgExemptAmount": 0.0,
            # inert; the PS taper period, recorded for documentation
            "saleCgExemptAfterYears": 30,
            "saleCgRatePct": 36.2,  # H — 19% IR + 17.2% PS
            "portfolioCgRatePct": 31.4,  # H — 12.8% PFU + 18.6% PS (LFSS 2026)
            "portfolioDeemedReturnPct": 0.0,
            "portfolioDragRatePct": 0.0,
        },
        # H — the primo-accédant carve-out from the departmental increase
        # is worth 0.51pp, not the 1.5pp in earlier research.
        "firstTimeBuyerOverrides": {"closingCostBuyerPct": 6.958},
        # The primo-accedant carve-out carries no price ceiling in the
        # sourced material, so none is modelled.
        "firstTimeBuyerMaxPrice": None,
        "notes": [
            "Maintenance (€1,300/yr) is an owner-only estimate. A large "
            "share of French copropriété charges are récupérables from the "
            "tenant; if the figure still includes any, it overstates the "
            "owner's cost and biases toward renting.",
            "The flat levy is indexed at your cost-inflation rate, not the "
            "statutory VLC coefficient (~+0.8%/yr), so it is over-indexed "
            "at the 2.5% default.",
            "Notaire emoluments are degressive across four bands; modelled "
            "flat, a ≤0.2pp error on a 7.9% cost.",
            "Rent regulation (encadrement) is not modelled; rent grows at "
            "the selected outlook rate.",
            "Portfolios are modelled as plain taxable accounts — no PEA (ADR-0009).",
        ],
    },
    {
        "id": "de",
        "label": "Germany (Köln)",
        "available": True,
        "currencySymbol": "€",
        "typical": {
            "propertyPrice": 339000,  # H — €4,239/m² x 80 m² = €339,120, rounded
            "monthlyRent": 992,  # H — €12.40/m² x 80 m², same matched pair
            "mortgageRateAnnual": 4.0,  # M — 15yr Zinsbindung; see notes
            # M — 2% anfängliche Tilgung => ~29yr full repayment
            "mortgageTermYears": 30,
        },
        "taxPrimitives": {
            # M — GrESt 6.5 (NRW) + Notar/Grundbuch 2.0 + Makler 3.57
            "closingCostBuyerPct": 12.07,
            "closingCostBuyerAmount": 0.0,
            "closingCostSellerPct": 4.0,  # M
            "propertyTaxRate": 0.0,
            # L — ~0.1% of market value; Köln Hebesatz 550% for 2026
            "annualPropertyLevy": 339.0,
            "levyPaidByOccupier": True,  # H — BetrKV §2 Nr.1, umlagefähig
            # H — condo: inside Hausgeld, umlagefähig (BetrKV §2 Nr.13)
            "annualHomeInsurance": 0.0,
            "annualMaintenancePct": 0.0,
            # M — §28 Abs.2 II.BV €9.00/m² x 80 + Verwalter + Sondereigentum
            "annualMaintenanceAmount": 1700.0,
            "interestDeductionEnabled": False,  # H — owner-occupied
            "marginalTaxRatePct": 0.0,
            "levyDeductionCap": 0.0,
            # H — §23 Abs.1 Nr.1 Satz 3 EStG, owner-occupier limb
            "saleCgRegime": "fully_exempt",
            "saleCgExemptAmount": 0.0,
            # inert; the §23 speculation period for non-owner-occupied
            "saleCgExemptAfterYears": 10,
            # inert; a taxable DE sale is taxed at the personal income rate
            "saleCgRatePct": 0.0,
            "portfolioCgRatePct": 26.375,  # H — 25% x 1.055 Soli
            # Vorabpauschale deliberately not modelled — creditable at exit
            "portfolioDeemedReturnPct": 0.0,
            "portfolioDragRatePct": 0.0,
        },
        "firstTimeBuyerOverrides": {},  # H — no FTB relief enacted
        "firstTimeBuyerMaxPrice": None,
        "notes": [
            "The Grundsteuer figure (€339/yr) is the weakest value in the "
            "set. The post-2025 reform runs eight state models and the "
            "effective rate is unsourceable at precision; ~0.1% of market "
            "value is likely understated at Köln's 550% Hebesatz.",
            "The Makler buyer-half (3.57% incl. USt) is conditional — a "
            "maklerfrei sale drops the total to 8.50%, a €12,102 swing at "
            "this price. Adjust the buyer-cost slider in Advanced.",
            "Grunderwerbsteuer varies 3.5–6.5% by Bundesland; 6.5% (NRW) "
            "is used nationally. The 3pp spread is ≈€10,170 on the shipped "
            "€339,000.",
            "The mortgage rate is held fixed for the full amortisation "
            "term; the 10/15/20yr Zinsbindung and Anschlussfinanzierung "
            "are not modelled, nor is the §489 BGB exit right after 10 yrs.",
            "Heating and water Nebenkosten are omitted from both arms — "
            "both parties pay them, so they are decision-neutral.",
            "Portfolios are modelled as plain taxable accounts — no "
            "Sparer-Pauschbetrag (ADR-0009).",
        ],
    },
    {
        "id": "nl",
        "label": "Netherlands",
        "available": True,
        "currencySymbol": "€",
        "typical": {
            "propertyPrice": 490000,  # H — CBS, verified 487,383
            "monthlyRent": 2300,  # L — derived, ±11% band; see notes
            "mortgageRateAnnual": 4.3,  # M — non-NHG (above the €470,000 NHG cap)
            # H — annuity; also the 30yr deduction period
            "mortgageTermYears": 30,
        },
        "taxPrimitives": {
            # H — overdrachtsbelasting 2% + ~1.2% other
            "closingCostBuyerPct": 3.2,
            "closingCostBuyerAmount": 0.0,
            "closingCostSellerPct": 1.4,  # M
            # H — 0.15% owner charges + 0.13146% EWF expressed as its exact
            # cash equivalent (0.35% of WOZ x 37.56% marginal rate).
            "propertyTaxRate": 0.2815,
            "annualPropertyLevy": 0.0,
            "levyPaidByOccupier": False,
            # M — opstalverzekering, €1.30/€1,000 herbouwwaarde
            "annualHomeInsurance": 550.0,
            "annualMaintenancePct": 1.0,  # M-H — Nibud "ruim 1%"/yr; VEH 1% of WOZ
            # deliberate: the sources are value-proportional
            "annualMaintenanceAmount": 0.0,
            "interestDeductionEnabled": True,  # H
            # H — 2026 tariefsaanpassing maximum, NOT the 49.5% top rate
            "marginalTaxRatePct": 37.56,
            "levyDeductionCap": 0.0,  # H — the NL levy is not deductible
            "saleCgRegime": "fully_exempt",  # H — eigen woning, box 1
            "saleCgExemptAmount": 0.0,
            "saleCgExemptAfterYears": 0,
            "saleCgRatePct": 0.0,  # H — no property CGT
            "portfolioCgRatePct": 0.0,  # H — the burden is box 3, not CGT
            # H — enacted 2026-01-01 (Wet IB 2001 art. 5.2 lid 2 / 5.5 / 2.13).
            # Two operands, not a product: art. 5.25 taxes min(deemed, actual).
            "portfolioDeemedReturnPct": 6.0,
            "portfolioDragRatePct": 36.0,
        },
        # H — startersvrijstelling: 0% vs 2% overdrachtsbelasting.
        "firstTimeBuyerOverrides": {"closingCostBuyerPct": 1.2},
        # H — the exemption is capped by property value; above it the
        # full 2% is due, so the relief must not apply there.
        "firstTimeBuyerMaxPrice": 555_000.0,
        "notes": [
            "The startersvrijstelling (0% instead of 2% "
            "overdrachtsbelasting) applies only to a home worth "
            "€555,000 or less, bought by someone aged 18–35 who will "
            "live in it. The first-time-buyer pill switches itself off "
            "above that price, but it cannot know your age — if you are "
            "36 or over, switch it off yourself.",
            "Box 3 is charged on the LESSER of a 6% deemed return and "
            "your actual return, floored at nil — so a bad year is taxed "
            "less, and a loss is not taxed at all.",
            "The heffingsvrij vermogen (€59,357 per person) is not "
            "modelled: under the tegenbewijs route the allowance is not "
            "available (Hoge Raad), which would make the comparison "
            "depend on your wealth and break the vectorised portfolio "
            "update. The headline verdict applies the full 2.16%/yr "
            "(6% × 36%) whenever your equity growth is 6% or above. "
            "With the allowance the effective drag would be 1.65% at "
            "€250k, 1.90% at €500k and 2.03% at €1M — a residual of "
            "0.13–0.51pp, biased toward buying. The Monte Carlo mean "
            "drag is lower (~1.30%), because the min binds in the "
            "years your return falls below 6%.",
            "The 6%/36% figures are enacted for 2026 ONLY. The 2027 "
            "deemed return is an identified funding lever, and the whole "
            "forfait-plus-tegenbewijs system is slated for replacement by "
            "the Wet werkelijk rendement box 3 from 1 January 2028. A 10-, "
            "25- or 30-year simulation should not be read as assuming "
            "this regime persists.",
            "Rent (€2,300/mo free-sector) is a derivation with a ±11% "
            "band; free-sector stock comparable to a large owner-occupied "
            "home barely exists. The blend overstates rent for a large "
            "home, so the true price/rent ratio is higher than shown.",
            "Hillen relief is inert at these defaults because deductible "
            "interest exceeds the eigenwoningforfait throughout. It would "
            "only bite above a ~91.9% down payment.",
            "Box 3 uses a 1 January peildatum; the model applies the drag "
            "monthly, which overstates it by ~3.36% of the terminal "
            "portfolio over 30 years, biased toward buying.",
            "Portfolios are modelled as plain taxable accounts (ADR-0009).",
        ],
    },
    {
        "id": "uk",
        "label": "United Kingdom (England & NI)",
        "available": True,
        "currencySymbol": "£",
        "typical": {
            # H — HM Land Registry UKHPI, England semi-detached, Apr 2026
            "propertyPrice": 289106,
            "monthlyRent": 1431,  # H — ONS PIPR, England semi-detached, May 2026
            "mortgageRateAnnual": 4.65,  # M — 5yr fix, 75% LTV
            "mortgageTermYears": 25,  # amortisation; the 5 is the fix
        },
        "taxPrimitives": {
            "closingCostBuyerPct": 5.0,  # H — SDLT marginal slice 250k-925k
            # H — SDLT nil-rate intercept (-10,000) + ~3,100 fixed fees
            "closingCostBuyerAmount": -6900.0,
            "closingCostSellerPct": 1.75,  # H — agent 1.42% VAT-INCLUSIVE + legal
            "propertyTaxRate": 0.0,
            # H — England avg Band D 2026/27 (2,343 excl. parish precepts)
            "annualPropertyLevy": 2392.0,
            "levyPaidByOccupier": True,  # H — LGFA 1992 s.6(2), resident liable
            "annualHomeInsurance": 310.0,  # M
            "annualMaintenancePct": 0.0,
            # M — ONS Family Spending FYE2025, LOWER bound
            "annualMaintenanceAmount": 900.0,
            "interestDeductionEnabled": False,  # H — MIRAS withdrawn 2000
            "marginalTaxRatePct": 0.0,
            "levyDeductionCap": 0.0,
            "saleCgRegime": "fully_exempt",  # H — Private Residence Relief
            "saleCgExemptAmount": 0.0,
            "saleCgExemptAfterYears": 0,
            "saleCgRatePct": 24.0,  # inert; the residential rate absent PRR
            "portfolioCgRatePct": 24.0,  # H — unwrapped higher rate (18% basic)
            "portfolioDeemedReturnPct": 0.0,
            "portfolioDragRatePct": 0.0,
        },
        "firstTimeBuyerOverrides": {
            "closingCostBuyerPct": 0.0,
            "closingCostBuyerAmount": 3100.0,
        },
        # H — gov.uk: "If the price is over £500,000, you cannot claim
        # the relief." Above this the relief does not exist, so applying
        # it inverts the verdict across roughly £610k-£710k.
        "firstTimeBuyerMaxPrice": 500_000.0,
        "notes": [
            "First-time-buyer relief is withdrawn entirely above £500,000 "
            '— gov.uk: "If the price is over £500,000, you cannot claim '
            'the relief." The first-time-buyer pill switches itself off '
            "above that price and full SDLT applies, so the verdict is "
            "not overstated there.",
            "First-time-buyer SDLT is also under-charged between £300,000 "
            "and £500,000, where relief is 5% rather than 0%: £5,000 low "
            "at £400k, £7,500 at £450k, £10,000 at £500k.",
            "Above £925,000 the SDLT marginal rate steps to 10% then 12%, "
            "but this model's line stays at 5% — £3,750 low at £1M, and "
            "£63,750 (41%) low at the £2M slider ceiling.",
            "SDLT applies to England & Northern Ireland only. Scotland "
            "uses LBTT and Wales uses LTT, with different bands and no "
            "first-time-buyer relief in Wales.",
            "Rents are modelled as exclusive of council tax. This premise "
            "is unverifiable — ONS never states it, and PIPR measures "
            "achieved rather than advertised rents. It shifts the displayed "
            "monthly costs but cannot change the verdict.",
            "Maintenance (£900/yr) is a lower bound: the ONS survey is "
            "recall-based and under-captures lumpy repairs.",
            "Buyer costs are under-charged across the whole £125,000–"
            "£250,000 band and clamp at zero below £138,000, where the "
            "true cost is £3,360.",
            "The additional-dwelling (+5pp) and non-resident (+2pp) SDLT "
            "surcharges are not modelled; this tool prices a single "
            "owner-occupied primary residence.",
            "The mortgage rate is held fixed for the full 25 years; "
            "reversion from the 5yr fix to SVR (currently ~195bp higher) "
            "is not modelled.",
            "Portfolios are modelled as plain taxable accounts — no ISA (ADR-0009).",
        ],
    },
]

_BY_ID: dict[str, dict[str, Any]] = {region["id"]: region for region in REGIONS}


def list_regions() -> list[dict[str, Any]]:
    """Return all region bundles, available or not.

    Examples
    --------
    .. code-block:: python

        from simulator.regions import list_regions

        ids = [r["id"] for r in list_regions()]
        assert "us" in ids

    """
    return REGIONS


def get_region(region_id: str) -> dict[str, Any]:
    """Return one region bundle by id.

    Raises
    ------
    KeyError
        If ``region_id`` is unknown.

    Examples
    --------
    .. code-block:: python

        from simulator.regions import get_region

        assert get_region("us")["currencySymbol"] == "$"

    """
    return _BY_ID[region_id]
