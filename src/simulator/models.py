"""Data models for the simulation engine."""

from dataclasses import dataclass

import pandas as pd


@dataclass
class SimulationConfig:
    """Configuration parameters for the simulation.

    Parameters
    ----------
    duration_years : int
        Number of years to simulate.
    property_price : float
        Initial price of the property ($).
    down_payment_pct : float
        Down payment as percentage of property price.
    mortgage_rate_annual : float
        Annual mortgage interest rate (as percentage, e.g., 4.5 for 4.5%).
    property_appreciation_annual : float
        Annual property appreciation rate (as percentage).
    equity_growth_annual : float
        Annual equity portfolio growth rate (as percentage).
    monthly_rent : float
        Monthly rent payment ($).
    rent_inflation_rate : float, optional
        Annual rent inflation rate (as percentage). Default is 0.03 (3%).

    Attributes
    ----------
    duration_years : int
        Number of years to simulate.
    property_price : float
        Initial price of the property ($).
    down_payment_pct : float
        Down payment as percentage of property price.
    mortgage_rate_annual : float
        Annual mortgage interest rate (as percentage).
    property_appreciation_annual : float
        Annual property appreciation rate (as percentage).
    equity_growth_annual : float
        Annual equity portfolio growth rate (as percentage).
    monthly_rent : float
        Monthly rent payment ($).
    rent_inflation_rate : float
        Annual rent inflation rate (as percentage).

    Raises
    ------
    ValueError
        If duration_years is not positive, property_price is not positive,
        down_payment_pct is not between 0 and 100, mortgage_rate_annual is
        negative, or monthly_rent is not positive.

    Examples
    --------
    Create a simulation configuration:

    .. code-block:: python

        from simulator.models import SimulationConfig
        
        config = SimulationConfig(
            duration_years=30,
            property_price=500000,
            down_payment_pct=20,
            mortgage_rate_annual=4.5,
            property_appreciation_annual=3,
            equity_growth_annual=7,
            monthly_rent=2000
        )

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
        """Validate input parameters.

        Raises
        ------
        ValueError
            If any parameter fails validation checks.

        Examples
        --------
        Validation happens automatically on instantiation:

        .. code-block:: python

            from simulator.models import SimulationConfig
            
            config = SimulationConfig(
                duration_years=30,
                property_price=500000,
                down_payment_pct=20,
                mortgage_rate_annual=4.5,
                property_appreciation_annual=3,
                equity_growth_annual=7,
                monthly_rent=2000
            )
            # Validation passed successfully

        """
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

    Parameters
    ----------
    data : pd.DataFrame
        DataFrame containing time-series data with columns:
        - Month: Month number (0 to duration_years * 12)
        - Year: Year number (0 to duration_years)
        - Home_Value: Property value over time
        - Equity_Value: Investment portfolio value over time
        - Mortgage_Balance: Remaining mortgage principal
        - Outflow_Buy: Cumulative outflows for buying scenario
        - Outflow_Rent: Cumulative outflows for renting scenario
        - Net_Buy: Net value for buying (Home_Value - Outflow_Buy)
        - Net_Rent: Net value for renting (Equity_Value - Outflow_Rent)
    final_net_buy : float
        Final net value for buying scenario.
    final_net_rent : float
        Final net value for renting scenario.
    final_difference : float
        Difference between buying and renting (Buy - Rent).
    breakeven_year : float | None
        Year when net values cross (None if they never cross).

    Attributes
    ----------
    data : pd.DataFrame
        DataFrame containing time-series simulation data.
    final_net_buy : float
        Final net value for buying scenario.
    final_net_rent : float
        Final net value for renting scenario.
    final_difference : float
        Difference between buying and renting (Buy - Rent).
    breakeven_year : float | None
        Year when net values cross (None if they never cross).

    Examples
    --------
    Create simulation results:

    .. code-block:: python

        from simulator.models import SimulationResults
        import pandas as pd
        
        df = pd.DataFrame({
            'Month': [0, 12, 24],
            'Year': [0, 1, 2],
            'Home_Value': [500000, 515000, 530450],
            'Equity_Value': [100000, 107000, 114490],
            'Mortgage_Balance': [400000, 390000, 380000],
            'Outflow_Buy': [100000, 118000, 136000],
            'Outflow_Rent': [0, 24000, 48000],
            'Net_Buy': [400000, 397000, 394450],
            'Net_Rent': [100000, 83000, 66490]
        })
        
        results = SimulationResults(
            data=df,
            final_net_buy=394450,
            final_net_rent=66490,
            final_difference=327960,
            breakeven_year=None
        )

    """

    data: pd.DataFrame
    final_net_buy: float
    final_net_rent: float
    final_difference: float
    breakeven_year: float | None
