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

    """
    return abs(a - b) < _FLOAT_TOLERANCE


def calculate_scenarios(config: SimulationConfig) -> SimulationResults:  # noqa: C901
    """Calculate time-series data for both buy and rent scenarios.

    This function performs vectorized calculations using NumPy for performance.
    All calculations are done at monthly granularity for accuracy.

    Parameters
    ----------
    config : SimulationConfig
        Configuration object with all input parameters for the simulation.

    Returns
    -------
    SimulationResults
        Results object containing DataFrame with time-series data and summary
        metrics including final net values and breakeven year.

    Examples
    --------
    Run a simulation:

    .. code-block:: python

        from simulator.models import SimulationConfig
        from simulator.engine import calculate_scenarios

        config = SimulationConfig(
            duration_years=5,
            property_price=500000,
            down_payment_pct=20,
            mortgage_rate_annual=4.5,
            property_appreciation_annual=3,
            equity_growth_annual=7,
            monthly_rent=2000
        )

        results = calculate_scenarios(config)
        print(f"Final difference: ${results.final_difference:,.0f}")

    """
    # Setup time vector (monthly granularity)
    n_months = config.duration_years * 12
    month_arr = np.arange(n_months + 1)
    year_arr = month_arr / 12

    # ========== SCENARIO A: BUY ==========

    # Calculate initial values
    down_payment = config.property_price * (config.down_payment_pct / 100)
    # Buyer closing costs are a one-time upfront outflow at purchase
    buyer_closing_costs = config.property_price * (config.closing_cost_buyer_pct / 100)
    initial_outflow = down_payment + buyer_closing_costs
    loan_amount = config.property_price - down_payment
    monthly_rate = (config.mortgage_rate_annual / 100) / 12

    # Calculate monthly mortgage payment using numpy-financial
    # Note: npf.pmt returns negative value (outflow), so we negate it
    # Handle edge case: 100% down payment (no loan)
    if _is_close_to_zero(loan_amount):
        # No loan = no monthly payment
        monthly_payment = 0.0
    elif _is_close_to_zero(monthly_rate):
        # 0% interest rate edge case: simple principal division
        monthly_payment = loan_amount / n_months if n_months > 0 else 0.0
    else:
        # Normal case: calculate amortized payment
        monthly_payment = -npf.pmt(monthly_rate, n_months, loan_amount)

    # Property value over time (compound monthly appreciation)
    # Formula: P * (1 + r/12)^month
    monthly_appreciation_rate = (config.property_appreciation_annual / 100) / 12
    home_value = config.property_price * (1 + monthly_appreciation_rate) ** month_arr

    # Calculate remaining mortgage balance at each time step
    # This is the present value of remaining payments
    mortgage_balance = np.zeros(n_months + 1)

    # Handle edge case: 100% down payment (no mortgage)
    if _is_close_to_zero(loan_amount):
        # No mortgage, balance is always zero
        mortgage_balance = np.zeros(n_months + 1)
    else:
        for i in range(n_months + 1):
            remaining_months = n_months - i
            if remaining_months > 0 and not _is_close_to_zero(monthly_rate):
                # Calculate remaining balance using present value formula
                mortgage_balance[i] = -npf.pv(
                    monthly_rate, remaining_months, monthly_payment
                )
            elif remaining_months > 0 and _is_close_to_zero(monthly_rate):
                # With 0% interest, balance decreases linearly
                mortgage_balance[i] = loan_amount - (monthly_payment * i)
            else:
                mortgage_balance[i] = 0

    # Ensure balance doesn't go below zero (handle floating-point errors)
    mortgage_balance = np.maximum(mortgage_balance, 0)

    # Monthly interest paid at each time step (for tax deduction calculations)
    monthly_interest = np.zeros(n_months + 1)
    if not _is_close_to_zero(loan_amount) and not _is_close_to_zero(monthly_rate):
        for i in range(1, n_months + 1):
            monthly_interest[i] = mortgage_balance[i - 1] * monthly_rate

    # Ongoing homeownership costs: property tax, insurance, maintenance
    # Property tax is a % of current home value each month
    monthly_property_tax_rate = (config.property_tax_rate / 100) / 12
    monthly_property_tax = home_value * monthly_property_tax_rate

    # Insurance and maintenance inflate with cost_inflation_rate
    monthly_cost_inflation_rate = config.cost_inflation_rate / 12
    cost_inflation_factor = (1 + monthly_cost_inflation_rate) ** month_arr
    monthly_insurance = (config.annual_home_insurance / 12) * cost_inflation_factor
    monthly_maintenance = (
        home_value * (config.annual_maintenance_pct / 100) / 12
    ) * cost_inflation_factor

    # Cumulate ongoing costs using the same convention as cum_rent_outflow:
    # value at t = total paid through end of month t-1 (so t=0 is zero).
    cum_property_tax = np.concatenate([[0], np.cumsum(monthly_property_tax[:-1])])
    cum_insurance = np.concatenate([[0], np.cumsum(monthly_insurance[:-1])])
    cum_maintenance = np.concatenate([[0], np.cumsum(monthly_maintenance[:-1])])

    # Total buy outflow: initial (down payment + closing) + mortgage + ongoing costs
    cum_mortgage_outflow = initial_outflow + (monthly_payment * month_arr)
    total_cum_outflow_buy = (
        cum_mortgage_outflow + cum_property_tax + cum_insurance + cum_maintenance
    )

    # Tax deduction savings (mortgage interest + property tax, subject to SALT cap)
    tax_rate = config.tax_bracket / 100
    annual_interest = np.zeros(n_months + 1)
    annual_property_tax = np.zeros(n_months + 1)
    annual_tax_savings = np.zeros(n_months + 1)
    cumulative_tax_savings = np.zeros(n_months + 1)
    for yr in range(1, config.duration_years + 1):
        yr_end = yr * 12
        yr_start = yr_end - 11

        year_interest = float(np.sum(monthly_interest[yr_start : yr_end + 1]))
        year_property_tax = float(np.sum(monthly_property_tax[yr_start : yr_end + 1]))

        annual_interest[yr_start : yr_end + 1] = year_interest
        annual_property_tax[yr_start : yr_end + 1] = year_property_tax

        yr_savings = 0.0
        if config.enable_mortgage_deduction and not _is_close_to_zero(tax_rate):
            deductible_prop_tax = min(year_property_tax, config.salt_cap)
            yr_savings = (year_interest + deductible_prop_tax) * tax_rate

        annual_tax_savings[yr_start : yr_end + 1] = yr_savings
        prior = cumulative_tax_savings[yr_start - 1] if yr_start > 1 else 0.0
        cumulative_tax_savings[yr_start : yr_end + 1] = prior + yr_savings

    # Capital gains exclusion on sale (primary residence benefit)
    capital_gains_tax_saved = 0.0
    if config.enable_capital_gains_exclusion:
        final_home_val = float(home_value[-1])
        capital_gain = final_home_val - config.property_price
        if capital_gain > config.capital_gains_exemption_limit:
            taxable_gain = capital_gain - config.capital_gains_exemption_limit
            cg_rate = 0.20 if config.tax_bracket >= 35 else 0.15
            capital_gains_tax_saved = taxable_gain * cg_rate

    # Seller closing costs reduce final net value at sale
    seller_closing_costs = float(home_value[-1]) * (
        config.closing_cost_seller_pct / 100
    )

    # Net value for buying scenario (Asset - Cumulative Outflows)
    # Seller closing costs are only realised at the end, so only applied to final value
    net_val_buy = home_value - total_cum_outflow_buy
    net_val_buy_tax_adjusted = net_val_buy + cumulative_tax_savings

    # ========== SCENARIO B: RENT & INVEST ==========

    # Investment portfolio value over time
    # Initial investment equals the down payment from Scenario A
    # Formula: D * (1 + e/12)^month
    monthly_equity_rate = (config.equity_growth_annual / 100) / 12
    equity_value = down_payment * (1 + monthly_equity_rate) ** month_arr

    # Calculate cumulative rent outflows
    # Option 1: Constant rent (simpler)
    # cum_rent_outflow = config.monthly_rent * month_arr

    # Option 2: Rent with inflation (more realistic)
    # We need to calculate cumulative sum of inflating rent
    monthly_rent_inflation = config.rent_inflation_rate / 12

    # Calculate rent at each month
    rent_at_month = config.monthly_rent * (1 + monthly_rent_inflation) ** month_arr

    # Cumulative rent is the sum of all rents up to each point
    # We use cumulative sum (trapezoid rule for integration)
    cum_rent_outflow = np.cumsum(rent_at_month)
    # Adjust: first month should be 0 (no rent paid yet at t=0)
    cum_rent_outflow = np.concatenate([[0], cum_rent_outflow[:-1]])

    # Net value for renting scenario (Asset - Cumulative Outflows)
    net_val_rent = equity_value - cum_rent_outflow

    # ========== SCENARIO C: RENT & INVEST MONTHLY SAVINGS ==========
    # Only applicable when initial mortgage payment > initial rent
    # Handle edge case: rent equals mortgage exactly
    scenario_c_enabled = monthly_payment > config.monthly_rent + _FLOAT_TOLERANCE

    # Calculate monthly savings (mortgage payment - rent), capped at 0 when
    # rent exceeds mortgage. The savings are invested each month at the same
    # CAGR as Scenario B
    monthly_savings = np.maximum(0, monthly_payment - rent_at_month)

    # Calculate compounded value of monthly contributions
    # Each month's contribution compounds for the remaining months
    # savings_portfolio[t] = sum over i from 0 to t-1 of: savings[i] * (1 + r)^(t-i)
    savings_portfolio = np.zeros(n_months + 1)
    for t in range(1, n_months + 1):
        # Previous portfolio value grows by one month
        savings_portfolio[t] = savings_portfolio[t - 1] * (1 + monthly_equity_rate)
        # Add this month's savings contribution (invested at end of month t-1)
        if t > 0:
            savings_portfolio[t] += monthly_savings[t - 1]

    # Scenario C asset value: uninvested down payment (cash) + savings portfolio
    asset_value_rent_savings = down_payment + savings_portfolio

    # Scenario C net value: asset value - cumulative rent outflows
    net_val_rent_savings = asset_value_rent_savings - cum_rent_outflow

    # Calculate Scenario C final values and breakeven
    final_net_rent_savings = (
        float(net_val_rent_savings[-1]) if scenario_c_enabled else None
    )
    breakeven_year_vs_rent_savings = (
        _find_breakeven(year_arr, net_val_buy, net_val_rent_savings)
        if scenario_c_enabled
        else None
    )

    # ========== CONSTRUCT OUTPUT ==========

    # Create DataFrame with all time-series data
    df = pd.DataFrame(
        {
            "Month": month_arr,
            "Year": year_arr,
            "Home_Value": home_value,
            "Equity_Value": equity_value,
            "Mortgage_Balance": mortgage_balance,
            "Outflow_Buy": total_cum_outflow_buy,
            "Outflow_Rent": cum_rent_outflow,
            "Net_Buy": net_val_buy,
            "Net_Rent": net_val_rent,
            "Annual_Interest": annual_interest,
            "Annual_Property_Tax": annual_property_tax,
            "Annual_Tax_Savings": annual_tax_savings,
            "Cumulative_Tax_Savings": cumulative_tax_savings,
            "Net_Buy_Tax_Adjusted": net_val_buy_tax_adjusted,
            "Savings_Portfolio_Value": savings_portfolio,
            "Net_Rent_Savings": net_val_rent_savings,
            "Property_Tax_Paid": cum_property_tax,
            "Insurance_Paid": cum_insurance,
            "Maintenance_Paid": cum_maintenance,
            # Scalar closing costs broadcast to all rows for easy access
            "Closing_Costs_Buyer": np.full(n_months + 1, buyer_closing_costs),
            "Closing_Costs_Seller": np.full(n_months + 1, seller_closing_costs),
        }
    )

    # Summary metrics: seller closing costs applied at sale only
    final_net_buy = float(net_val_buy[-1]) - seller_closing_costs
    final_net_rent = float(net_val_rent[-1])
    final_difference = final_net_buy - final_net_rent

    # Find breakeven point (where net values cross)
    breakeven_year = _find_breakeven(year_arr, net_val_buy, net_val_rent)

    # Tax-adjusted final values
    total_tax_savings = float(cumulative_tax_savings[-1])
    final_net_buy_tax_adjusted = (
        float(net_val_buy_tax_adjusted[-1])
        - seller_closing_costs
        + capital_gains_tax_saved
    )
    tax_adjusted_difference = final_net_buy_tax_adjusted - final_net_rent

    # Totals match the last DataFrame row (consistent with shift convention)
    total_closing_costs_buyer = buyer_closing_costs
    total_property_tax_paid = float(cum_property_tax[-1])
    total_insurance_paid = float(cum_insurance[-1])
    total_maintenance_paid = float(cum_maintenance[-1])

    return SimulationResults(
        data=df,
        final_net_buy=final_net_buy,
        final_net_rent=final_net_rent,
        final_difference=final_difference,
        breakeven_year=breakeven_year,
        monthly_mortgage_payment=monthly_payment,
        scenario_c_enabled=scenario_c_enabled,
        final_net_rent_savings=final_net_rent_savings,
        breakeven_year_vs_rent_savings=breakeven_year_vs_rent_savings,
        total_closing_costs_buyer=total_closing_costs_buyer,
        total_closing_costs_seller=seller_closing_costs,
        total_property_tax_paid=total_property_tax_paid,
        total_insurance_paid=total_insurance_paid,
        total_maintenance_paid=total_maintenance_paid,
        total_tax_savings=total_tax_savings,
        capital_gains_tax_saved=capital_gains_tax_saved,
        final_net_buy_tax_adjusted=final_net_buy_tax_adjusted,
        tax_adjusted_difference=tax_adjusted_difference,
    )


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
