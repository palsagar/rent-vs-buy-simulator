"""Core calculation engine for financial simulations.

This module provides vectorized NumPy calculations for comparing
two financial strategies: buying property vs. renting and investing.
"""

import numpy as np
import numpy_financial as npf
import pandas as pd

from .models import SimulationConfig, SimulationResults


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
    loan_amount = config.property_price - down_payment
    monthly_rate = (config.mortgage_rate_annual / 100) / 12

    # Calculate monthly mortgage payment using numpy-financial
    # Note: npf.pmt returns negative value (outflow), so we negate it
    if monthly_rate > 0 and loan_amount > 0:
        monthly_payment = -npf.pmt(monthly_rate, n_months, loan_amount)
    else:
        # If no interest or no loan, payment is just principal divided by months
        monthly_payment = loan_amount / n_months if n_months > 0 else 0

    # Property value over time (compound monthly appreciation)
    # Formula: P * (1 + r/12)^month
    monthly_appreciation_rate = (config.property_appreciation_annual / 100) / 12
    home_value = config.property_price * (1 + monthly_appreciation_rate) ** month_arr

    # Calculate remaining mortgage balance at each time step
    # This is the present value of remaining payments
    mortgage_balance = np.zeros(n_months + 1)
    for i in range(n_months + 1):
        remaining_months = n_months - i
        if remaining_months > 0 and monthly_rate > 0:
            # Calculate remaining balance using present value formula
            mortgage_balance[i] = -npf.pv(
                monthly_rate, remaining_months, monthly_payment
            )
        else:
            mortgage_balance[i] = 0

    # Cumulative outflows for buying
    # At t=0, outflow is just the down payment
    # After that, add cumulative mortgage payments
    cum_mortgage_outflow = down_payment + (monthly_payment * month_arr)

    # Net value for buying scenario (Asset - Cumulative Outflows)
    net_val_buy = home_value - cum_mortgage_outflow

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
    monthly_rent_inflation = (config.rent_inflation_rate / 100) / 12

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
    scenario_c_enabled = monthly_payment > config.monthly_rent

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
            "Outflow_Buy": cum_mortgage_outflow,
            "Outflow_Rent": cum_rent_outflow,
            "Net_Buy": net_val_buy,
            "Net_Rent": net_val_rent,
            "Savings_Portfolio_Value": savings_portfolio,
            "Net_Rent_Savings": net_val_rent_savings,
        }
    )

    # Calculate summary metrics
    final_net_buy = float(net_val_buy[-1])
    final_net_rent = float(net_val_rent[-1])
    final_difference = final_net_buy - final_net_rent

    # Find breakeven point (where net values cross)
    breakeven_year = _find_breakeven(year_arr, net_val_buy, net_val_rent)

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

    # Look for sign changes
    sign_changes = np.diff(np.sign(diff))

    # Find indices where sign changes (crossover points)
    crossover_indices = np.where(sign_changes != 0)[0]

    if len(crossover_indices) > 0:
        # Return the first crossover point
        # Linear interpolation for more accurate year
        idx = crossover_indices[0]
        # Interpolate between idx and idx+1
        x1, x2 = years[idx], years[idx + 1]
        y1, y2 = diff[idx], diff[idx + 1]

        # Linear interpolation to find exact zero crossing
        if y2 != y1:
            breakeven = x1 - y1 * (x2 - x1) / (y2 - y1)
            return float(breakeven)
        else:
            return float(x1)

    return None
