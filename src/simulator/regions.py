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
            ("de", "Germany", "€"),
            ("nl", "Netherlands", "€"),
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
