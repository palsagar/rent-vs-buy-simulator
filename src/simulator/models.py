"""Data models for the simulation engine."""

from dataclasses import dataclass

import pandas as pd


@dataclass
class SimulationConfig:
    """Configuration parameters for the simulation.

    Attributes:
        duration_years: Number of years to simulate
        property_price: Initial price of the property ($)
        down_payment_pct: Down payment as percentage of property price
        mortgage_rate_annual: Annual mortgage interest rate (as percentage, e.g., 4.5 for 4.5%)
        property_appreciation_annual: Annual property appreciation rate (as percentage)
        equity_growth_annual: Annual equity portfolio growth rate (as percentage)
        monthly_rent: Monthly rent payment ($)
        rent_inflation_rate: Annual rent inflation rate (as percentage, default 3%)
    """

    duration_years: int
    property_price: float
    down_payment_pct: float
    mortgage_rate_annual: float
    property_appreciation_annual: float
    equity_growth_annual: float
    monthly_rent: float
    rent_inflation_rate: float = 0.03

    def __post_init__(self):
        """Validate input parameters."""
        if self.duration_years <= 0:
            raise ValueError("duration_years must be positive")
        if self.property_price <= 0:
            raise ValueError("property_price must be positive")
        if not (0 <= self.down_payment_pct <= 100):
            raise ValueError("down_payment_pct must be between 0 and 100")
        if self.mortgage_rate_annual < 0:
            raise ValueError("mortgage_rate_annual cannot be negative")
        if self.monthly_rent <= 0:
            raise ValueError("monthly_rent must be positive")


@dataclass
class SimulationResults:
    """Results from the simulation engine.

    Attributes:
        data: DataFrame containing time-series data with columns:
            - Month: Month number (0 to duration_years * 12)
            - Year: Year number (0 to duration_years)
            - Home_Value: Property value over time
            - Equity_Value: Investment portfolio value over time
            - Mortgage_Balance: Remaining mortgage principal
            - Outflow_Buy: Cumulative outflows for buying scenario
            - Outflow_Rent: Cumulative outflows for renting scenario
            - Net_Buy: Net value for buying (Home_Value - Outflow_Buy)
            - Net_Rent: Net value for renting (Equity_Value - Outflow_Rent)
        final_net_buy: Final net value for buying scenario
        final_net_rent: Final net value for renting scenario
        final_difference: Difference between buying and renting (Buy - Rent)
        breakeven_year: Year when net values cross (None if they never cross)
    """

    data: pd.DataFrame
    final_net_buy: float
    final_net_rent: float
    final_difference: float
    breakeven_year: float | None
