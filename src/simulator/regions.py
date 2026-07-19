"""Region preset bundles (ADR-0007): trustworthy defaults per market.

v1 ships the US bundle, carried over from the app's long-standing
verified defaults. FR/DE/NL/UK are declared but unavailable until the
redesign spec §7 research completes — shipped values must be
source-verified, never guessed.
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
        "notes": [
            "Box 3 is charged on the LESSER of a 6% deemed return and "
            "your actual return, floored at nil — so a bad year is taxed "
            "less, and a loss is not taxed at all.",
            "The heffingsvrij vermogen (€59,357 per person) is not "
            "modelled: under the tegenbewijs route the allowance is not "
            "available (Hoge Raad), which would make the comparison "
            "depend on your wealth and break the vectorised portfolio "
            "update. Effective drags with the allowance are 0.99% at "
            "€250k, 1.12% at €500k and 1.19% at €1M, against this "
            "model's ~1.31% — a residual 0.12–0.32pp, biased toward "
            "buying.",
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
    *[
        {
            "id": region_id,
            "label": label,
            "available": False,
            "currencySymbol": symbol,
            "typical": None,
            "taxPrimitives": None,
            "firstTimeBuyerOverrides": {},
            "notes": [],
        }
        for region_id, label, symbol in [
            ("uk", "United Kingdom", "£"),
        ]
    ],
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
