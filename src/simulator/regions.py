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
            ("fr", "France", "€"),
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
