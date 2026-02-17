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
    """Check if a value is effectively zero within tolerance."""
    return abs(value) < _FLOAT_TOLERANCE


def _is_close(a: float, b: float) -> bool:
    """Check if two values are close within tolerance."""
    return abs(a - b) < _FLOAT_TOLERANCE


def calculate_scenarios(config: SimulationConfig) -> SimulationResults:
    """Calculate time-series data for both buy and rent scenarios."""
    # Setup time vector (monthly granularity)
    n_months = config.duration_years * 12
    month_arr = np.arange(n_months + 1)
    year_arr = month_arr / 12

    # ========== SCENARIO A: BUY ==========
    down_payment = config.property_price * (config.down_payment_pct / 100)
    loan_amount = config.property_price - down_payment
    monthly_rate = (config.mortgage_rate_annual / 100) / 12

    # Calculate monthly mortgage payment
    if _is_close_to_zero(loan_amount):
        monthly_payment = 0.0
    elif _is_close_to_zero(monthly_rate):
        monthly_payment = loan_amount / n_months if n_months > 0 else 0.0
    else:
        monthly_payment = -npf.pmt(monthly_rate, n_months, loan_amount)

    # Property value over time
    monthly_appreciation_rate = (config.property_appreciation_annual / 100) / 12
    home_value = config.property_price * (1 + monthly_appreciation_rate) ** month_arr

    # Calculate remaining mortgage balance
    mortgage_balance = np.zeros(n_months + 1)
    if _is_close_to_zero(loan_amount):
        mortgage_balance = np.zeros(n_months + 1)
    else:
        for i in range(n_months + 1):
            remaining_months = n_months - i
            if remaining_months > 0 and not _is_close_to_zero(monthly_rate):
                mortgage_balance[i] = -npf.pv(monthly_rate, remaining_months, monthly_payment)
            elif remaining_months > 0 and _is_close_to_zero(monthly_rate):
                mortgage_balance[i] = loan_amount - (monthly_payment * i)
            else:
                mortgage_balance[i] = 0

    mortgage_balance = np.maximum(mortgage_balance, 0)

    # Cumulative outflows for buying
    cum_mortgage_outflow = down_payment + (monthly_payment * month_arr)
    net_val_buy = home_value - cum_mortgage_outflow
    property_equity = home_value - mortgage_balance

    # ========== SCENARIO B: RENT & INVEST ==========
    monthly_equity_rate = (config.equity_growth_annual / 100) / 12
    equity_value = down_payment * (1 + monthly_equity_rate) ** month_arr

    # Rent with inflation
    monthly_rent_inflation = config.rent_inflation_rate / 12
    rent_at_month = config.monthly_rent * (1 + monthly_rent_inflation) ** month_arr

    cum_rent_outflow = np.cumsum(rent_at_month)
    cum_rent_outflow = np.concatenate([[0], cum_rent_outflow[:-1]])
    net_val_rent = equity_value - cum_rent_outflow

    # ========== SCENARIO C: RENT & INVEST MONTHLY SAVINGS ==========
    scenario_c_enabled = monthly_payment > config.monthly_rent + _FLOAT_TOLERANCE
    monthly_savings = np.maximum(0, monthly_payment - rent_at_month)

    savings_portfolio = np.zeros(n_months + 1)
    for t in range(1, n_months + 1):
        savings_portfolio[t] = savings_portfolio[t - 1] * (1 + monthly_equity_rate)
        if t > 0:
            savings_portfolio[t] += monthly_savings[t - 1]

    asset_value_rent_savings = down_payment + savings_portfolio
    net_val_rent_savings = asset_value_rent_savings - cum_rent_outflow

    final_net_rent_savings = float(net_val_rent_savings[-1]) if scenario_c_enabled else None
    breakeven_year_vs_rent_savings = (
        _find_breakeven(year_arr, net_val_buy, net_val_rent_savings)
        if scenario_c_enabled else None
    )

    # ========== CONSTRUCT OUTPUT ==========
    df = pd.DataFrame({
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
    })

    final_net_buy = float(net_val_buy[-1])
    final_net_rent = float(net_val_rent[-1])
    final_difference = final_net_buy - final_net_rent
    breakeven_year = _find_breakeven(year_arr, net_val_buy, net_val_rent)

    # Edge case metrics
    negative_equity_months = int(np.sum(property_equity < 0))
    min_equity_achieved = float(np.min(property_equity))
    final_home_value = float(home_value[-1])
    final_mortgage_balance = float(mortgage_balance[-1])
    final_ltv_ratio = (
        final_mortgage_balance / final_home_value
        if final_home_value > 0 and not _is_close_to_zero(final_home_value)
        else 0.0
    )
    max_rent = float(np.max(rent_at_month))
    max_monthly_payment = max(monthly_payment, max_rent)

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
        negative_equity_months=negative_equity_months,
        min_equity_achieved=min_equity_achieved,
        final_ltv_ratio=final_ltv_ratio,
        max_monthly_payment=max_monthly_payment,
    )


def _find_breakeven(years: np.ndarray, net_buy: np.ndarray, net_rent: np.ndarray) -> float | None:
    """Find the year where net_buy crosses net_rent."""
    diff = net_buy - net_rent
    start_idx = 1 if _is_close_to_zero(diff[0]) else 0

    for i in range(start_idx, len(diff) - 1):
        if diff[i] * diff[i + 1] < -_FLOAT_TOLERANCE:
            x1, x2 = years[i], years[i + 1]
            y1, y2 = diff[i], diff[i + 1]
            if not _is_close(y1, y2):
                breakeven = x1 - y1 * (x2 - x1) / (y2 - y1)
                return float(breakeven)
            else:
                return float(x1)
        elif _is_close_to_zero(diff[i]) and i > 0:
            return float(years[i])

    return None
