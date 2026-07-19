"""Core calculation engine for financial simulations.

This module provides vectorized NumPy calculations for comparing
two financial strategies: buying property vs. renting and investing.
"""

import numpy as np
import numpy_financial as npf
import pandas as pd

from .models import SimulationConfig, SimulationResults

# Floating-point tolerance for comparisons
_FLOAT_TOLERANCE = 1e-9


def _is_close_to_zero(value: float) -> bool:
    """Check if a value is effectively zero within tolerance.

    Parameters
    ----------
    value : float
        The value to check.

    Returns
    -------
    bool
        True if value is close to zero, False otherwise.

    Examples
    --------
    Check whether a floating-point value rounds to zero:

    .. code-block:: python

        from simulator.engine import _is_close_to_zero

        _is_close_to_zero(0.0)       # True
        _is_close_to_zero(1e-10)     # True
        _is_close_to_zero(0.001)     # False

    """
    return abs(value) < _FLOAT_TOLERANCE


def _is_close(a: float, b: float) -> bool:
    """Check if two values are close within tolerance.

    Parameters
    ----------
    a : float
        First value.
    b : float
        Second value.

    Returns
    -------
    bool
        True if values are close, False otherwise.

    Examples
    --------
    Compare two floating-point values within the default tolerance:

    .. code-block:: python

        from simulator.engine import _is_close

        _is_close(1.0, 1.0 + 1e-10)   # True
        _is_close(1.0, 1.01)           # False

    """
    return abs(a - b) < _FLOAT_TOLERANCE


def _net_value_series(
    config: SimulationConfig,
    prop_rate_monthly: np.ndarray,
    eq_rate_monthly: np.ndarray,
    rent_growth_monthly: np.ndarray,
) -> dict[str, np.ndarray]:
    """Compute all Net Value time series from per-month rate arrays.

    Single source of truth for both the deterministic engine and Monte
    Carlo (ADR-0001). Net Value at month t is the wealth you would walk
    away with if you exited the strategy at t, minus all cash committed
    through t (CONTEXT.md: "Net Value"). Both strategies commit the same
    cash each month; the cheaper side invests the difference in equities
    (CONTEXT.md: "Cash-flow matching"). Capital-gains and deduction tax
    primitives are applied inline (ADR-0007).

    Parameters
    ----------
    config : SimulationConfig
        Configuration object with all input parameters for the
        simulation, including the Horizon (``horizon_years``).
    prop_rate_monthly : np.ndarray
        Monthly property appreciation rate per month, decimal, shape
        ``(H,)`` for months 1..H.
    eq_rate_monthly : np.ndarray
        Monthly equity portfolio growth rate per month, decimal, shape
        ``(H,)``.
    rent_growth_monthly : np.ndarray
        Monthly rent growth rate per month, decimal, shape ``(H,)``.

    Returns
    -------
    dict[str, np.ndarray]
        Time series keyed by name, each of shape ``(H+1,)`` where
        ``H = config.horizon_years * 12``: ``home_value``,
        ``mortgage_balance``, ``rent_portfolio``, ``buy_portfolio``,
        ``housing_cost_buy``, ``housing_cost_rent``, ``outflow_buy``,
        ``outflow_rent``, ``cash_committed``, ``cum_tax_savings``,
        ``net_buy``, ``net_rent``, plus underscore-prefixed internals
        (``_interest``, ``_levy``, ``_insurance``, ``_maintenance``,
        ``_basis_rent``, ``_basis_buy``, ``_monthly_payment``,
        ``_buyer_closing``) consumed by the tax layer.

    Examples
    --------
    Run the core with constant (deterministic) monthly rates:

    .. code-block:: python

        import numpy as np
        from simulator.models import SimulationConfig
        from simulator.engine import _net_value_series

        config = SimulationConfig(
            horizon_years=10,
            property_price=500000,
            down_payment_pct=20,
            mortgage_rate_annual=4.5,
            property_appreciation_annual=3,
            equity_growth_annual=7,
            monthly_rent=2000,
        )
        h = config.horizon_years * 12
        series = _net_value_series(
            config,
            np.full(h, 0.03 / 12),
            np.full(h, 0.07 / 12),
            np.full(h, config.rent_inflation_rate / 12),
        )
        print(f"Net Value (buy): ${series['net_buy'][-1]:,.0f}")

    """
    h = config.horizon_years * 12
    t_arr = np.arange(h + 1)

    down_payment = config.property_price * (config.down_payment_pct / 100)
    # A transfer tax with a zero-rate band has a negative intercept (UK
    # SDLT ships -6,900), so the amount may be negative. Clamp the
    # aggregate, not the term: the UK pair goes negative below a price of
    # 138,000 and the slider floor is 50,000.
    buyer_closing = max(
        config.property_price * (config.closing_cost_buyer_pct / 100)
        + config.closing_cost_buyer_amount,
        0.0,
    )
    initial_outlay = down_payment + buyer_closing
    loan = config.property_price - down_payment
    r = (config.mortgage_rate_annual / 100) / 12
    n_term = config.mortgage_term_years * 12

    # --- Home value: compounds with the (possibly stochastic) monthly rate
    home_growth = np.concatenate([[1.0], np.cumprod(1 + prop_rate_monthly)])
    home_value = config.property_price * home_growth

    # --- Fixed-rate mortgage: payment over the term, not the horizon
    if _is_close_to_zero(loan):
        pmt = 0.0
        balance = np.zeros(h + 1)
    elif _is_close_to_zero(r):
        pmt = loan / n_term
        balance = np.maximum(loan - pmt * t_arr, 0.0)
    else:
        pmt = -npf.pmt(r, n_term, loan)
        growth = (1 + r) ** np.minimum(t_arr, n_term)
        balance = np.maximum(loan * growth - pmt * (growth - 1) / r, 0.0)

    # Payment made during month m (1..min(term, horizon)); zero after payoff
    payment = np.where((t_arr >= 1) & (t_arr <= n_term), pmt, 0.0)
    # Interest accrued during month m on the prior balance
    interest = np.zeros(h + 1)
    interest[1:] = balance[:-1] * r

    # --- Ongoing ownership costs paid during month m (prior-month value base)
    # Hoisted: three cost lines are now absolute amounts sharing one index.
    cost_index = (1 + config.cost_inflation_rate / 12) ** (t_arr[1:] - 1)

    # No new region's levy base tracks market prices (FR valeur locative
    # cadastrale, DE Grundsteuerwert, UK 1991 bands), so the flat component
    # is cost-indexed rather than tied to the appreciating home value.
    levy = np.zeros(h + 1)
    levy[1:] = (
        home_value[:-1] * (config.property_tax_rate / 100) / 12
        + (config.annual_property_levy / 12) * cost_index
    )
    insurance = np.zeros(h + 1)
    insurance[1:] = (config.annual_home_insurance / 12) * cost_index
    maintenance = np.zeros(h + 1)
    maintenance[1:] = (
        home_value[:-1] * (config.annual_maintenance_pct / 100) / 12
        + (config.annual_maintenance_amount / 12) * cost_index
    )

    housing_cost_buy = payment + levy + insurance + maintenance

    # --- Rent paid during month m (rent set at end of prior month)
    rent_level = config.monthly_rent * np.concatenate(
        [[1.0], np.cumprod(1 + rent_growth_monthly)]
    )
    housing_cost_rent = np.zeros(h + 1)
    housing_cost_rent[1:] = rent_level[:-1]

    # Occupier-borne levies (UK council tax; DE umlagefaehige Grundsteuer)
    # are owed by whoever lives there, so the renter bears them too.
    # Charging the levy to BOTH arms leaves the Verdict unchanged against
    # charging it to neither: it shifts both by the same amount and
    # cancels in the difference. (It is NOT invariant to toggling this
    # flag at a fixed levy -- that moves the cost from one arm to two.)
    # The headline monthly costs and the outflow chart do move.
    if config.levy_paid_by_occupier:
        housing_cost_rent = housing_cost_rent + levy

    # --- Cash-flow matching: cheaper side invests the difference
    surplus = housing_cost_buy - housing_cost_rent
    contrib_rent = np.maximum(surplus, 0.0)
    contrib_buy = np.maximum(-surplus, 0.0)

    # Portfolio value with varying growth: V[t] = G[t]*(V0 + sum c[m]/G[m])
    # NL box 3 (Wet IB 2001 art. 5.25): taxed on min(deemed, actual)
    # return, floored at nil. Both operands are proportional to wealth,
    # so the min reduces to a rate comparison and the closed form
    # survives. Summed, not compounded: engine.py:402 and
    # monte_carlo.py:187 both feed arithmetic annual/100/12, so twelve
    # of them sum back to the annual draw exactly.
    annual_return = eq_rate_monthly.reshape(config.horizon_years, 12).sum(axis=1)
    deemed = config.portfolio_deemed_return_pct / 100
    taxable = np.clip(np.minimum(deemed, annual_return), 0.0, None)
    drag_monthly = np.repeat(taxable * (config.portfolio_drag_rate_pct / 100) / 12, 12)
    eq_growth = np.concatenate([[1.0], np.cumprod(1 + eq_rate_monthly - drag_monthly)])
    rent_portfolio = eq_growth * (initial_outlay + np.cumsum(contrib_rent / eq_growth))
    buy_portfolio = eq_growth * np.cumsum(contrib_buy / eq_growth)
    basis_rent = initial_outlay + np.cumsum(contrib_rent)
    basis_buy = np.cumsum(contrib_buy)

    # --- Cash committed: identical for both strategies by construction
    cash_committed = initial_outlay + np.cumsum(
        np.maximum(housing_cost_buy, housing_cost_rent)
    )
    outflow_buy = initial_outlay + np.cumsum(housing_cost_buy)
    outflow_rent = np.cumsum(housing_cost_rent)

    # --- Deduction savings: (interest + capped levy) * marginal rate,
    # credited at the end of each completed year
    cum_tax_savings = np.zeros(h + 1)
    if (
        config.interest_deduction_enabled
        and config.marginal_tax_rate_pct > _FLOAT_TOLERANCE
    ):
        yearly_interest = interest[1:].reshape(config.horizon_years, 12).sum(axis=1)
        yearly_levy = levy[1:].reshape(config.horizon_years, 12).sum(axis=1)
        if config.levy_deduction_cap is not None:
            yearly_levy = np.minimum(yearly_levy, config.levy_deduction_cap)
        yearly_savings = (yearly_interest + yearly_levy) * (
            config.marginal_tax_rate_pct / 100
        )
        cum_by_year = np.concatenate([[0.0], np.cumsum(yearly_savings)])
        cum_tax_savings = cum_by_year[t_arr // 12]

    # --- Sale capital gains: regime-dependent taxable gain (ADR-0007)
    home_gain = np.maximum(home_value - config.property_price, 0.0)
    if config.sale_cg_regime == "fully_exempt":
        taxable_gain = np.zeros(h + 1)
    elif config.sale_cg_regime == "exempt_amount":
        taxable_gain = np.maximum(home_gain - config.sale_cg_exempt_amount, 0.0)
    else:  # exempt_after_years: taxed only if sold before the holding period
        held_long_enough = t_arr >= config.sale_cg_exempt_after_years * 12
        taxable_gain = np.where(held_long_enough, 0.0, home_gain)
    sale_cg_tax = taxable_gain * (config.sale_cg_rate_pct / 100)

    # --- Portfolio capital gains: symmetric on both strategies' exits
    portfolio_rate = config.portfolio_cg_rate_pct / 100
    portfolio_tax_rent = np.maximum(rent_portfolio - basis_rent, 0.0) * portfolio_rate
    portfolio_tax_buy = np.maximum(buy_portfolio - basis_buy, 0.0) * portfolio_rate

    # --- Liquidation-priced Net Value at every t (ADR-0001)
    seller_cost = home_value * (config.closing_cost_seller_pct / 100)
    net_buy = (
        home_value
        - balance
        - seller_cost
        - sale_cg_tax
        + buy_portfolio
        - portfolio_tax_buy
        + cum_tax_savings
        - cash_committed
    )
    net_rent = rent_portfolio - portfolio_tax_rent - cash_committed

    return {
        "home_value": home_value,
        "mortgage_balance": balance,
        "rent_portfolio": rent_portfolio,
        "buy_portfolio": buy_portfolio,
        "housing_cost_buy": housing_cost_buy,
        "housing_cost_rent": housing_cost_rent,
        "outflow_buy": outflow_buy,
        "outflow_rent": outflow_rent,
        "cash_committed": cash_committed,
        "cum_tax_savings": cum_tax_savings,
        "net_buy": net_buy,
        "net_rent": net_rent,
        # internal series (underscore keys) consumed by callers; not exported to the df
        "_interest": interest,
        "_levy": levy,
        "_insurance": insurance,
        "_maintenance": maintenance,
        "_basis_rent": basis_rent,
        "_basis_buy": basis_buy,
        "_monthly_payment": np.array([pmt]),
        "_buyer_closing": np.array([buyer_closing]),
    }


def _find_breakeven(
    years: np.ndarray, net_buy: np.ndarray, net_rent: np.ndarray
) -> float | None:
    """Find the year where net_buy crosses net_rent.

    Parameters
    ----------
    years : np.ndarray
        Array of year values.
    net_buy : np.ndarray
        Net value array for buying scenario.
    net_rent : np.ndarray
        Net value array for renting scenario.

    Returns
    -------
    float | None
        Year of breakeven point, or None if no crossover occurs.

    Examples
    --------
    Find breakeven between two scenarios:

    .. code-block:: python

        import numpy as np
        from simulator.engine import _find_breakeven

        years = np.array([0, 1, 2, 3, 4, 5])
        net_buy = np.array([100000, 110000, 120000, 130000, 140000,
                            150000])
        net_rent = np.array([100000, 105000, 115000, 125000, 135000,
                             145000])

        breakeven = _find_breakeven(years, net_buy, net_rent)

    """
    # Calculate the difference (positive when buy is winning)
    diff = net_buy - net_rent

    # Find where diff crosses zero (changes sign)
    # Skip the first point if it's effectively zero, to handle initial equality
    start_idx = 1 if _is_close_to_zero(diff[0]) else 0

    # Look for sign changes in the difference
    for i in range(start_idx, len(diff) - 1):
        # Check if diff crosses zero between i and i+1 using tolerance
        if diff[i] * diff[i + 1] < -_FLOAT_TOLERANCE:
            # Found a crossover: interpolate to find exact zero crossing
            x1, x2 = years[i], years[i + 1]
            y1, y2 = diff[i], diff[i + 1]

            if not _is_close(y1, y2):
                breakeven = x1 - y1 * (x2 - x1) / (y2 - y1)
                return float(breakeven)
            else:
                # Both are zero (shouldn't happen with < 0 check, but handle it)
                return float(x1)
        elif _is_close_to_zero(diff[i]) and i > 0:
            # Exact match at this point (within tolerance)
            return float(years[i])

    return None


def calculate_scenarios(config: SimulationConfig) -> SimulationResults:
    """Run the deterministic simulation on the shared Net Value core.

    Feeds constant monthly rates (derived from the config's annual
    rates) into :func:`_net_value_series` and assembles the results
    DataFrame and summary fields. The Verdict (``final_difference``),
    the charted series (``results.data``), and the Breakeven all read
    the same ``net_buy``/``net_rent`` arrays, so they can never
    disagree (CONTEXT.md: "Net Value", "Verdict", "Breakeven").

    Parameters
    ----------
    config : SimulationConfig
        Configuration object with all input parameters for the
        simulation, including the Horizon (``horizon_years``).

    Returns
    -------
    SimulationResults
        Assembled time series and summary statistics for both
        strategies.

    Examples
    --------
    Run the deterministic simulation and read the Verdict:

    .. code-block:: python

        from simulator.models import SimulationConfig
        from simulator.engine import calculate_scenarios

        config = SimulationConfig(
            horizon_years=10,
            property_price=500000,
            down_payment_pct=20,
            mortgage_rate_annual=4.5,
            property_appreciation_annual=3,
            equity_growth_annual=7,
            monthly_rent=2000,
        )
        results = calculate_scenarios(config)
        print(f"Final difference: ${results.final_difference:,.0f}")

    """
    h = config.horizon_years * 12
    series = _net_value_series(
        config,
        np.full(h, (config.property_appreciation_annual / 100) / 12),
        np.full(h, (config.equity_growth_annual / 100) / 12),
        np.full(h, config.rent_inflation_rate / 12),
    )

    t_arr = np.arange(h + 1)
    year_arr = t_arr / 12
    df = pd.DataFrame(
        {
            "Month": t_arr,
            "Year": year_arr,
            "Home_Value": series["home_value"],
            "Equity_Value": series["rent_portfolio"],
            "Buy_Portfolio_Value": series["buy_portfolio"],
            "Mortgage_Balance": series["mortgage_balance"],
            "Outflow_Buy": series["outflow_buy"],
            "Outflow_Rent": series["outflow_rent"],
            "Cash_Committed": series["cash_committed"],
            "Net_Buy": series["net_buy"],
            "Net_Rent": series["net_rent"],
        }
    )

    net_buy, net_rent = series["net_buy"], series["net_rent"]
    return SimulationResults(
        data=df,
        final_net_buy=float(net_buy[-1]),
        final_net_rent=float(net_rent[-1]),
        final_difference=float(net_buy[-1] - net_rent[-1]),
        breakeven_year=_find_breakeven(year_arr, net_buy, net_rent),
        monthly_mortgage_payment=float(series["_monthly_payment"][0]),
        monthly_cost_buy_year1=float(np.mean(series["housing_cost_buy"][1:13])),
        monthly_cost_rent_year1=float(np.mean(series["housing_cost_rent"][1:13])),
        total_closing_costs_buyer=float(series["_buyer_closing"][0]),
        total_closing_costs_seller=float(
            series["home_value"][-1] * (config.closing_cost_seller_pct / 100)
        ),
        total_property_tax_paid=float(np.sum(series["_levy"])),
        total_insurance_paid=float(np.sum(series["_insurance"])),
        total_maintenance_paid=float(np.sum(series["_maintenance"])),
        total_mortgage_interest_paid=float(np.sum(series["_interest"])),
        total_tax_savings=float(series["cum_tax_savings"][-1]),
    )
