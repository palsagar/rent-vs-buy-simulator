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


def calculate_scenarios(config: SimulationConfig) -> SimulationResults:
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
            monthly_rent=2000,
            tax_bracket=24,
            enable_mortgage_deduction=True,
        )

        results = calculate_scenarios(config)
        print(f"Final difference: ${results.final_difference:,.0f}")
        print(f"Tax savings: ${results.total_tax_savings:,.0f}")

    """
    # Setup time vector (monthly granularity)
    n_months = config.duration_years * 12
    month_arr = np.arange(n_months + 1)
    year_arr = month_arr / 12

    # ========== SCENARIO A: BUY ==========

    # Calculate initial values
    down_payment = config.property_price * (config.down_payment_pct / 100)
    closing_costs = config.property_price * (config.closing_cost_buyer_pct / 100)
    initial_outflow = down_payment + closing_costs
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

    # Calculate monthly interest and principal payments
    monthly_interest = np.zeros(n_months + 1)
    monthly_principal = np.zeros(n_months + 1)

    for i in range(1, n_months + 1):
        if monthly_rate > 0 and not _is_close_to_zero(loan_amount):
            monthly_interest[i] = mortgage_balance[i - 1] * monthly_rate
            monthly_principal[i] = monthly_payment - monthly_interest[i]
        else:
            monthly_interest[i] = 0
            monthly_principal[i] = monthly_payment if i <= n_months else 0

    # Calculate annual interest paid (for tax deduction)
    annual_interest = np.zeros(n_months + 1)
    for i in range(1, n_months + 1):
        month_in_year = i % 12
        if month_in_year == 0:  # End of year
            year_start = max(0, i - 11)
            annual_interest[i] = np.sum(monthly_interest[year_start : i + 1])
        else:
            # Carry forward from previous December
            prev_december = ((i // 12) * 12)
            if prev_december > 0:
                annual_interest[i] = annual_interest[prev_december]

    # Calculate property tax (annual, based on current home value)
    monthly_property_tax_rate = (config.property_tax_rate / 100) / 12
    monthly_property_tax = home_value * monthly_property_tax_rate

    # Calculate annual property tax paid
    annual_property_tax = np.zeros(n_months + 1)
    for i in range(1, n_months + 1):
        month_in_year = i % 12
        if month_in_year == 0:  # End of year
            year_start = max(0, i - 11)
            annual_property_tax[i] = np.sum(monthly_property_tax[year_start : i + 1])
        else:
            # Carry forward from previous December
            prev_december = ((i // 12) * 12)
            if prev_december > 0:
                annual_property_tax[i] = annual_property_tax[prev_december]

    # Calculate tax savings from deductions
    # SALT cap limits property tax deduction
    # Mortgage interest + property tax (capped by SALT) are deductible
    tax_rate = config.tax_bracket / 100

    annual_tax_savings = np.zeros(n_months + 1)
    cumulative_tax_savings = np.zeros(n_months + 1)

    if config.enable_mortgage_deduction and not _is_close_to_zero(tax_rate):
        for i in range(1, n_months + 1):
            month_in_year = i % 12
            if month_in_year == 0:  # End of year - calculate tax savings
                year_start = max(0, i - 11)
                year_interest = np.sum(monthly_interest[year_start : i + 1])
                year_property_tax = np.sum(monthly_property_tax[year_start : i + 1])

                # Property tax deduction is capped by SALT cap
                deductible_property_tax = min(year_property_tax, config.salt_cap)

                # Total deductible amount
                total_deductions = year_interest + deductible_property_tax

                # Tax savings = deductions * tax rate
                annual_tax_savings[i] = total_deductions * tax_rate
            else:
                # Carry forward from previous December
                prev_december = ((i // 12) * 12)
                if prev_december > 0:
                    annual_tax_savings[i] = annual_tax_savings[prev_december]

        # Calculate cumulative tax savings (only at year-end)
        for i in range(12, n_months + 1, 12):  # Only process year-end months
            year_savings = annual_tax_savings[i]
            cumulative_tax_savings[i] = cumulative_tax_savings[i - 12] + year_savings

        # Fill in cumulative values for non-year-end months
        for i in range(1, n_months + 1):
            if i % 12 != 0:
                prev_december = ((i // 12) * 12)
                if prev_december > 0:
                    cumulative_tax_savings[i] = cumulative_tax_savings[prev_december]

    # Cumulative outflows for buying (include property tax and closing costs)
    cum_mortgage_outflow = initial_outflow + (monthly_payment * month_arr)
    cum_property_tax = np.cumsum(monthly_property_tax)
    cum_property_tax = np.concatenate([[0], cum_property_tax[:-1]])  # Adjust for t=0
    total_cum_outflow_buy = cum_mortgage_outflow + cum_property_tax

    # Net value for buying scenario (Asset - Cumulative Outflows)
    net_val_buy = home_value - total_cum_outflow_buy
    net_val_buy_tax_adjusted = net_val_buy + cumulative_tax_savings

    # Calculate equity in the property (Home_Value - Mortgage_Balance)
    property_equity = home_value - mortgage_balance

    # ========== SCENARIO B: RENT & INVEST ==========

    # Investment portfolio value over time
    # Initial investment equals the down payment from Scenario A
    # Formula: D * (1 + e/12)^month
    monthly_equity_rate = (config.equity_growth_annual / 100) / 12
    equity_value = down_payment * (1 + monthly_equity_rate) ** month_arr

    # Calculate cumulative rent outflows
    monthly_rent_inflation = (config.rent_inflation_rate * 100) / 12

    # Calculate rent at each month
    rent_at_month = config.monthly_rent * (1 + monthly_rent_inflation) ** month_arr

    # Cumulative rent is the sum of all rents up to each point
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

    # ========== CAPITAL GAINS TAX CALCULATION ==========
    # Calculate capital gains tax saved through primary residence exclusion
    capital_gains_tax_saved = 0.0

    if config.enable_capital_gains_exclusion:
        final_home_value = home_value[-1]
        # Capital gains = final value - purchase price
        capital_gains = max(0, final_home_value - config.property_price)

        # Apply exemption limit
        taxable_gains = max(0, capital_gains - config.capital_gains_exemption_limit)

        # Assuming long-term capital gains rate (15% for most brackets, 20% for high)
        # Using 15% as default, or 20% if tax bracket >= 35%
        lt_cap_gains_rate = 0.20 if config.tax_bracket >= 35 else 0.15

        # Tax saved = exempted gains * capital gains rate
        exempted_gains = capital_gains - taxable_gains
        capital_gains_tax_saved = exempted_gains * lt_cap_gains_rate

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
            "Savings_Portfolio_Value": savings_portfolio,
            "Net_Rent_Savings": net_val_rent_savings,
            "Annual_Interest": annual_interest,
            "Annual_Property_Tax": annual_property_tax,
            "Annual_Tax_Savings": annual_tax_savings,
            "Cumulative_Tax_Savings": cumulative_tax_savings,
            "Net_Buy_Tax_Adjusted": net_val_buy_tax_adjusted,
        }
    )

    # Calculate summary metrics
    final_net_buy = float(net_val_buy[-1])
    final_net_rent = float(net_val_rent[-1])
    final_difference = final_net_buy - final_net_rent

    # Find breakeven point (where net values cross)
    breakeven_year = _find_breakeven(year_arr, net_val_buy, net_val_rent)

    # Tax-adjusted metrics
    total_tax_savings = float(cumulative_tax_savings[-1])
    final_net_buy_tax_adjusted = float(net_val_buy_tax_adjusted[-1])
    tax_adjusted_difference = final_net_buy_tax_adjusted - final_net_rent

    # Calculate edge case metrics
    # Count months with negative equity (underwater mortgage)
    negative_equity_months = int(np.sum(property_equity < 0))

    # Minimum equity achieved during simulation
    min_equity_achieved = float(np.min(property_equity))

    # Final loan-to-value ratio
    final_home_value = float(home_value[-1])
    final_mortgage_balance = float(mortgage_balance[-1])
    final_ltv_ratio = (
        final_mortgage_balance / final_home_value
        if final_home_value > 0 and not _is_close_to_zero(final_home_value)
        else 0.0
    )

    # Maximum monthly payment (highest monthly obligation)
    # For buying: mortgage payment + avg property tax; for renting: max rent over time
    max_rent = float(np.max(rent_at_month))
    avg_monthly_property_tax = float(np.mean(monthly_property_tax))
    max_monthly_payment = max(monthly_payment + avg_monthly_property_tax, max_rent)

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
        total_tax_savings=total_tax_savings,
        capital_gains_tax_saved=capital_gains_tax_saved,
        final_net_buy_tax_adjusted=final_net_buy_tax_adjusted,
        tax_adjusted_difference=tax_adjusted_difference,
        negative_equity_months=negative_equity_months,
        min_equity_achieved=min_equity_achieved,
        final_ltv_ratio=final_ltv_ratio,
        max_monthly_payment=max_monthly_payment,
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
