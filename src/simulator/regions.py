"""Region preset bundles (ADR-0007): trustworthy defaults per market.

Five bundles ship: US, France (Lyon), Germany (Köln), Netherlands and
the United Kingdom (England & NI). Countries are data, not code — no
per-country branch exists in the engine; each bundle expresses its
regime through the shared scalar primitives on ``SimulationConfig``.

Every value is source-verified, never guessed, and each one's
justification is pinned by a fixture in ``tests/test_regions.py`` with
its citation. Values that are derived rather than primary-sourced, and
every known divergence between a bundle and the real statute, carry a
caveat in that bundle's ``notes`` — rendered in the UI, under the verdict.
Notes are written for the person using the calculator: plain words, one
idea per sentence, led by what the caveat means for the answer, and
ordered by how much it can move the verdict. Sources and internal
references go in the comment above each list, not in the notes. See
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
            # M — Freddie Mac: $30-$70/month per $100,000 borrowed
            # (0.36-0.84%/yr); charged below 20% down, ends at 78%
            "mortgageInsuranceRatePct": 0.5,
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
        # Sources and internal references for these notes: ADR-0009 (plain
        # taxable portfolios), ADR-0013 (refunds invested), CFPB and
        # 12 U.S.C. 4901(18)(A) (mortgage insurance ends at 78%).
        "notes": [
            "Renting may come out better than shown if you invest through a"
            " 401(k) or an IRA. The model treats all investments as an "
            "ordinary taxable account, so it leaves out the tax those "
            "accounts save the renter.",
            "The tax you save by deducting mortgage interest and the "
            "property levy comes back as a refund each year, and the model "
            "assumes you invest it. It grows with your other investments, "
            "and its gains are taxed when you cash them in. If you would "
            "spend it instead, buying comes out worse than shown.",
            "If you put down less than 20%, buying costs more: lenders "
            "charge mortgage insurance. The model sets it at 0.5% of the "
            "amount you borrow each year. It stops once you owe 78% of the "
            "purchase price or less, because the law ends it there. If your"
            " quote differs, change it in Advanced under Yearly costs of "
            "owning.",
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
            # H — no yearly premium; the loan guarantee (caution or
            # hypothèque) is paid when the loan is taken out
            "mortgageInsuranceRatePct": 0.0,
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
        # Sources and internal references: copropriété charges
        # récupérables (owner-only maintenance), the VLC revaluation
        # coefficient (~+0.8%/yr), the degressive notaire emolument bands,
        # encadrement des loyers, and ADR-0009 (no PEA).
        "notes": [
            "Maintenance is set at €1,300 a year, meant to cover only what "
            "an owner pays. In a French apartment building, a tenant pays a"
            " large share of the shared building charges. If your figure "
            "still includes some of those, it overstates what owning costs,"
            " and the answer leans toward renting.",
            "Buying looks a little more expensive than it is, because the "
            "yearly property tax (taxe foncière) grows with your cost "
            "inflation, 2.5% by default. The official value it is charged "
            "on rises by only about 0.8% a year.",
            "Mortgage insurance is set to 0. French lenders ask for a "
            "guarantee on almost every home loan: a guarantee company "
            "vouches for you, or the lender registers a charge on the home."
            " You pay it once when you take out the loan, not every year, "
            "and the model does not include it separately.",
            "Rent grows at the outlook rate you pick. Rent controls in "
            "French cities are not modelled.",
            "If you invest through a PEA, a French account with lower tax "
            "on investment gains, your investments are taxed less than "
            "shown. The model treats them as an ordinary taxable account.",
            "Notary fees fall in four steps as the price rises. The model "
            "uses one flat rate instead, which is off by at most 0.2 "
            "percentage points of the 7.9% total buying costs.",
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
            # H — no premium; a small deposit is priced into the rate
            "mortgageInsuranceRatePct": 0.0,
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
        # Sources and internal references: Makler buyer half 3.57% incl.
        # USt; Grunderwerbsteuer 3.5-6.5% by Bundesland, NRW 6.5%;
        # Grundsteuer reform (eight state models) and Köln Hebesatz 550%;
        # Zinsbindung, Anschlussfinanzierung and § 489 BGB (exit after
        # 10 years); ADR-0009 (no Sparer-Pauschbetrag). Heating and water
        # (Nebenkosten) are left out of both sides, so they cannot change
        # the verdict and carry no note.
        "notes": [
            "Buying costs include 3.57% (with VAT) for the buyer's half of "
            "the estate agent's fee (Makler). If you buy without an agent, "
            "total buying costs fall to 8.50%, about €12,102 less at the "
            "default price of €339,000. Change Buying costs in Advanced to "
            "match.",
            "The property transfer tax (Grunderwerbsteuer) is set at 6.5%, "
            "the rate in North Rhine-Westphalia. Other states charge "
            "between 3.5% and 6.5%. In a cheaper state, buying costs up to "
            "about €10,170 less at €339,000.",
            "Buying may cost more than shown, because the yearly property "
            "tax (Grundsteuer) of €339 is probably too low. It is the least"
            " certain number here: the 2025 reform created eight different "
            "state models, so the real rate cannot be pinned down. About "
            "0.1% of the home's value is likely too little at Köln's local "
            "rate.",
            "The mortgage rate stays fixed for the whole loan. In Germany a"
            " rate is usually fixed for 10, 15 or 20 years and then "
            "renegotiated, which the model does not include. It also leaves"
            " out your legal right to repay a fixed-rate loan early after "
            "10 years.",
            "Mortgage insurance is set to 0. German lenders charge a higher"
            " interest rate when your deposit is small, not a separate "
            "premium. If your quote reflects that, raise the mortgage rate.",
            "Your investments are taxed a little more than they would be, "
            "because the model leaves out the yearly tax-free allowance on "
            "investment income (Sparer-Pauschbetrag).",
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
            # H — no yearly premium; NHG is a one-off fee, and this loan
            # is above the NHG limit
            "mortgageInsuranceRatePct": 0.0,
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
        # Sources and internal references: startersvrijstelling (0%
        # instead of 2% overdrachtsbelasting, value cap, age 18-35, owner
        # occupation); box 3 forfait 6% x 36% enacted for 2026 only, the
        # 2027 deemed return an identified funding lever, Wet werkelijk
        # rendement box 3 from 1 Jan 2028; heffingsvrij vermogen
        # unavailable under the tegenbewijs route (Hoge Raad); 1 January
        # peildatum; NHG limit; free-sector rent derivation (+/-11% band).
        # Hillen relief carries no note: it only applies above a ~91.9%
        # down payment, beyond the slider's 50% maximum. ADR-0009,
        # ADR-0013.
        "notes": [
            "The first-time-buyer relief (startersvrijstelling: 0% transfer"
            " tax instead of 2%) applies only to a home worth €555,000 or "
            "less, bought by someone aged 18 to 35 who will live in it. The"
            " First-time buyer pill switches itself off above that price, "
            "but it cannot know your age. If you are 36 or over, switch it "
            "off yourself.",
            "The tax on investments (box 3) follows rules set for 2026 "
            "only: tax on an assumed 6% return, at 36%. The government may "
            "change the assumed return for 2027, and the whole system is "
            "due to be replaced on 1 January 2028 by a tax on actual "
            "returns. A 10-, 25- or 30-year simulation does not mean these "
            "rules will last.",
            "Leaving out the box 3 tax-free allowance (heffingsvrij "
            "vermogen, €59,357 per person) makes investing look worse than "
            "it is, so the answer leans toward buying. If you are taxed on "
            "your actual return, the Dutch Supreme Court has ruled that the"
            " allowance does not apply. The model charges the full 2.16% a "
            "year (6% × 36%) whenever your equity growth is 6% or more. "
            "With the allowance, the charge would be 1.65% on €250k, 1.90% "
            "on €500k and 2.03% on €1M, a gap of 0.13 to 0.51 percentage "
            "points. In the simulated futures the average charge is lower, "
            "about 1.30%, because years with a return under 6% are taxed on"
            " that lower return.",
            "Box 3 tax is charged on the lower of the assumed 6% return and"
            " your actual return, and never on a loss. So a bad year is "
            "taxed less, and a year with a loss is not taxed at all.",
            "The tax you save by deducting mortgage interest comes back as "
            "a refund each year, and the model assumes you invest it. It "
            "grows with your other investments and pays the box 3 tax like "
            "them. If you would spend it instead, buying comes out worse "
            "than shown.",
            "Renting may cost less than shown. The rent of €2,300 a month "
            "is an estimate, with a margin of about 11% either way, and few"
            " homes this size are rented on the open market. The estimate "
            "likely overstates the rent for a large home.",
            "Box 3 tax is worked out on what you own on 1 January. The "
            "model charges it every month instead, which overstates it by "
            "about 3.37% of the final portfolio over 30 years, so the "
            "answer leans slightly toward buying.",
            "Mortgage insurance is set to 0. There is no yearly premium in "
            "the Netherlands. A loan under the national mortgage guarantee "
            "limit (NHG) can carry a one-off guarantee fee instead. The "
            "figures here are for a loan above that limit.",
            "The model treats investments as an ordinary taxable account.",
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
            # H — no premium; a small deposit is priced into the rate
            "mortgageInsuranceRatePct": 0.0,
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
        # Sources and internal references: gov.uk ("If the price is over
        # £500,000, you cannot claim the relief"); SDLT bands; LBTT
        # (Scotland) and LTT (Wales); ONS Family Spending (maintenance,
        # recall-based); 5-year fix reverting to SVR (~195bp higher);
        # SDLT surcharges; ADR-0009 (no ISA). The council-tax note (rents
        # assumed exclusive of it, unverifiable from ONS PIPR) is left out:
        # it shifts the monthly costs shown but cannot change the verdict.
        "notes": [
            "First-time buyers lose the stamp duty relief entirely on a "
            "home over £500,000. The First-time buyer pill switches itself "
            "off above that price and the full stamp duty applies, so the "
            "answer is not too kind to buying there.",
            "Between £300,000 and £500,000, first-time buyers pay 5% stamp "
            "duty on the part of the price above £300,000, but the model "
            "charges none. So buying costs too little by £5,000 at £400k, "
            "£7,500 at £450k and £10,000 at £500k.",
            "Above £925,000, stamp duty rises in steps to 10% and then 12%,"
            " but the model keeps charging 5%. So buying costs too little "
            "by £3,750 at £1M, and by £63,750 (41% of the real cost) at £2M,"
            " the top of the price slider.",
            "Below £250,000 the model charges too little in buying costs. "
            "Below £138,000 it charges nothing; the real cost at £138,000 "
            "is £3,360.",
            "The mortgage rate stays fixed for the full 25 years. A 5-year "
            "fixed rate usually moves to the lender's standard variable "
            "rate afterwards, now about 1.95 percentage points higher, "
            "which the model does not include.",
            "If you invest through an ISA, a UK account with no tax on "
            "investment gains, your investments are taxed less than shown. "
            "The model treats them as an ordinary taxable account.",
            "Buying may cost more than shown, because maintenance of £900 a"
            " year is a minimum. It comes from a national survey in which "
            "people recall their spending, which misses large one-off "
            "repairs.",
            "The extra stamp duty on a second home (5 percentage points) or"
            " for a buyer who does not live in the UK (2 percentage points)"
            " is not modelled. The figures are for a single home you live "
            "in.",
            "Mortgage insurance is set to 0. UK lenders charge a higher "
            "interest rate when your deposit is small, not a separate "
            "premium. If your quote reflects that, raise the mortgage rate.",
            "The stamp duty here is the one for England and Northern "
            "Ireland. Scotland and Wales have their own taxes, with "
            "different bands, and Wales has no first-time-buyer relief.",
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
