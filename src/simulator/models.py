"""Data models for the simulation engine."""

from dataclasses import dataclass

import numpy as np
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
    closing_cost_buyer_pct : float, optional
        Buyer closing costs as percentage of property price.
        Default is 3.0 (3%).
    closing_cost_seller_pct : float, optional
        Seller closing costs as percentage of sale price.
        Default is 6.0 (6%).
    property_tax_rate : float, optional
        Annual property tax rate as percentage of property value.
        Default is 1.2 (1.2%).
    annual_home_insurance : float, optional
        Annual home insurance cost ($). Default is 1200.
    annual_maintenance_pct : float, optional
        Annual maintenance cost as percentage of property value.
        Default is 1.0 (1%).
    cost_inflation_rate : float, optional
        Annual inflation rate for ongoing costs (tax, insurance, maintenance).
        Default is 0.03 (3%).

    Raises
    ------
    ValueError
        If duration_years is not positive, property_price is not positive,
        down_payment_pct is not between 5 and 100, mortgage_rate_annual is
        not positive, monthly_rent is not positive, or rent_inflation_rate
        is not between 0 and 1 (0-100%).

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
    # Tax benefit parameters
    tax_bracket: float = 24.0
    enable_mortgage_deduction: bool = True
    enable_capital_gains_exclusion: bool = True
    capital_gains_exemption_limit: float = 250000.0
    salt_cap: float = 10000.0
    # Closing cost and ongoing expense parameters
    closing_cost_buyer_pct: float = 3.0
    closing_cost_seller_pct: float = 6.0
    property_tax_rate: float = 1.2
    annual_home_insurance: float = 1200.0
    annual_maintenance_pct: float = 1.0
    cost_inflation_rate: float = 0.03
    down_payment_investment_rate: float = 0.025

    def __post_init__(self):  # noqa: C901
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
        # Validate duration_years
        if self.duration_years <= 0:
            raise ValueError(
                f"duration_years must be positive (got {self.duration_years}). "
                "Please specify a duration greater than 0 years."
            )

        # Validate property_price
        if self.property_price <= 0:
            raise ValueError(
                f"property_price must be positive (got {self.property_price}). "
                "Please specify a property price greater than $0."
            )

        # Validate down_payment_pct (must be between 5% and 100%)
        if not (5 <= self.down_payment_pct <= 100):
            raise ValueError(
                f"down_payment_pct must be 5-100 (got {self.down_payment_pct}). "
                "Minimum down payment is typically 5% for most mortgages. "
                "Use 100% for an all-cash purchase."
            )

        # Validate mortgage_rate_annual (must be > 0 to avoid numerical issues)
        if self.mortgage_rate_annual <= 0:
            raise ValueError(
                f"mortgage_rate_annual must be > 0 (got {self.mortgage_rate_annual}). "
                "Please specify a rate greater than 0%. "
                "For very low rates, use a small positive value like 0.01%."
            )

        # Validate monthly_rent
        if self.monthly_rent <= 0:
            raise ValueError(
                f"monthly_rent must be positive (got {self.monthly_rent}). "
                "Please specify a monthly rent greater than $0."
            )

        # Validate rent_inflation_rate (must be between 0 and 1, i.e., 0-100%)
        if not (0 <= self.rent_inflation_rate <= 1):
            raise ValueError(
                f"rent_inflation_rate must be 0-1 (got {self.rent_inflation_rate}). "
                "For 3% annual inflation, use 0.03. For no inflation, use 0."
            )

        # Validate tax_bracket (must be between 0 and 100)
        if not (0 <= self.tax_bracket <= 100):
            raise ValueError(
                f"tax_bracket must be between 0 and 100 (got {self.tax_bracket}). "
                "For no tax benefits, use 0."
            )

        # Validate capital_gains_exemption_limit (must be non-negative)
        if self.capital_gains_exemption_limit < 0:
            raise ValueError(
                "capital_gains_exemption_limit cannot be negative "
                f"(got {self.capital_gains_exemption_limit})."
            )

        # Validate salt_cap (must be non-negative)
        if self.salt_cap < 0:
            raise ValueError(f"salt_cap cannot be negative (got {self.salt_cap}).")

        if not (0 <= self.down_payment_investment_rate <= 1):
            raise ValueError(
                f"down_payment_investment_rate must be 0–1 "
                f"(got {self.down_payment_investment_rate}). "
                "For 2.5% annual return use 0.025. For no return use 0."
            )


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
        - Savings_Portfolio_Value: Scenario C investment from monthly savings
        - Net_Rent_Savings: Scenario C net value (down payment + savings - rent)
    final_net_buy : float
        Final net value for buying scenario.
    final_net_rent : float
        Final net value for renting scenario.
    final_difference : float
        Difference between buying and renting (Buy - Rent).
    breakeven_year : float | None
        Year when net values cross (None if they never cross).
    monthly_mortgage_payment : float
        Monthly mortgage payment amount.
    scenario_c_enabled : bool
        Whether Scenario C is applicable (mortgage > initial rent).
    final_net_rent_savings : float | None
        Final net value for Scenario C (rent + invest savings).
    breakeven_year_vs_rent_savings : float | None
        Year when Buy crosses Rent+Savings (None if never crosses).

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
            'Net_Rent': [100000, 83000, 66490],
            'Savings_Portfolio_Value': [0, 5000, 10500],
            'Net_Rent_Savings': [100000, 81000, 62500]
        })

        results = SimulationResults(
            data=df,
            final_net_buy=394450,
            final_net_rent=66490,
            final_difference=327960,
            breakeven_year=None,
            monthly_mortgage_payment=2500,
            scenario_c_enabled=True,
            final_net_rent_savings=62500,
            breakeven_year_vs_rent_savings=None,
        )

    """

    data: pd.DataFrame
    final_net_buy: float
    final_net_rent: float
    final_difference: float
    breakeven_year: float | None
    monthly_mortgage_payment: float
    scenario_c_enabled: bool
    final_net_rent_savings: float | None
    breakeven_year_vs_rent_savings: float | None
    # Closing cost and ongoing expense totals
    total_closing_costs_buyer: float = 0.0
    total_closing_costs_seller: float = 0.0
    total_property_tax_paid: float = 0.0
    total_insurance_paid: float = 0.0
    total_maintenance_paid: float = 0.0
    final_down_payment_value: float | None = None
    # Tax benefit totals
    total_tax_savings: float = 0.0
    capital_gains_tax_saved: float = 0.0
    final_net_buy_tax_adjusted: float = 0.0
    tax_adjusted_difference: float = 0.0


@dataclass
class MonteCarloConfig:
    """Configuration for Monte Carlo uncertainty analysis.

    Controls the number of simulations, random seed, which parameters
    to randomize, their standard deviations (in percentage points),
    and the correlation between property appreciation and equity growth.

    Parameters
    ----------
    n_simulations : int
        Number of Monte Carlo paths to simulate. Default is 500.
    seed : int | None
        Random seed for reproducibility. None for non-deterministic.
        Default is 42.
    randomize_property_appreciation : bool
        Whether to randomize annual property appreciation. Default True.
    property_appreciation_std : float
        Standard deviation (in percentage points) for property
        appreciation draws. Default is 5.0.
    randomize_equity_growth : bool
        Whether to randomize annual equity growth. Default True.
    equity_growth_std : float
        Standard deviation (in percentage points) for equity growth
        draws. Default is 5.0.
    randomize_rent_inflation : bool
        Whether to randomize annual rent inflation. Default True.
    rent_inflation_std : float
        Standard deviation (in percentage points) for rent inflation
        draws. Default is 1.5.
    appreciation_equity_correlation : float
        Pearson correlation between property appreciation and equity
        growth annual draws. Default is 0.3.

    Raises
    ------
    ValueError
        If n_simulations is not positive, any std is negative, or
        correlation is outside [-1, 1].

    Examples
    --------
    Create a Monte Carlo configuration with defaults:

    .. code-block:: python

        from simulator.models import MonteCarloConfig

        mc_config = MonteCarloConfig()
        print(mc_config.n_simulations)  # 500

    """

    n_simulations: int = 500
    seed: int | None = 42
    randomize_property_appreciation: bool = True
    property_appreciation_std: float = 5.0
    randomize_equity_growth: bool = True
    equity_growth_std: float = 5.0
    randomize_rent_inflation: bool = True
    rent_inflation_std: float = 1.5
    appreciation_equity_correlation: float = 0.3

    def __post_init__(self) -> None:
        """Validate Monte Carlo configuration parameters.

        Raises
        ------
        ValueError
            If any parameter fails validation.

        Examples
        --------
        Validation runs automatically on creation:

        .. code-block:: python

            from simulator.models import MonteCarloConfig

            mc = MonteCarloConfig(n_simulations=1000)

        """
        if self.n_simulations <= 0:
            raise ValueError(
                f"n_simulations must be positive (got {self.n_simulations})."
            )
        if self.property_appreciation_std < 0:
            raise ValueError(
                "property_appreciation_std must be non-negative "
                f"(got {self.property_appreciation_std})."
            )
        if self.equity_growth_std < 0:
            raise ValueError(
                "equity_growth_std must be non-negative "
                f"(got {self.equity_growth_std})."
            )
        if self.rent_inflation_std < 0:
            raise ValueError(
                "rent_inflation_std must be non-negative "
                f"(got {self.rent_inflation_std})."
            )
        if not (-1 <= self.appreciation_equity_correlation <= 1):
            raise ValueError(
                "appreciation_equity_correlation must be "
                "between -1 and 1 "
                f"(got {self.appreciation_equity_correlation})."
            )


@dataclass
class MonteCarloResults:
    """Results from Monte Carlo uncertainty analysis.

    Contains per-simulation final values, full time-series paths for
    spaghetti charts, percentile bands, summary statistics, and
    sensitivity analysis data for tornado charts.

    Parameters
    ----------
    final_net_buy : np.ndarray
        Final net buy value per simulation. Shape: (n_simulations,).
    final_net_rent : np.ndarray
        Final net rent value per simulation. Shape: (n_simulations,).
    final_differences : np.ndarray
        Final (net_buy - net_rent) per simulation. Shape:
        (n_simulations,).
    all_net_buy : np.ndarray
        Full net buy paths. Shape: (n_simulations, n_months+1).
    all_net_rent : np.ndarray
        Full net rent paths. Shape: (n_simulations, n_months+1).
    all_differences : np.ndarray
        Full difference paths. Shape: (n_simulations, n_months+1).
    year_arr : np.ndarray
        Shared time axis in years. Shape: (n_months+1,).
    percentile_levels : list[int]
        Percentile levels computed (e.g. [5, 25, 50, 75, 95]).
    difference_percentiles : np.ndarray
        Percentiles of differences over time. Shape:
        (len(percentile_levels), n_months+1).
    buy_wins_pct : float
        Percentage of simulations where buying wins (0-100).
    median_difference : float
        Median final difference across simulations.
    p5_difference : float
        5th percentile of final differences.
    p95_difference : float
        95th percentile of final differences.
    sensitivity_params : list[str]
        Parameter names for tornado chart.
    sensitivity_low : np.ndarray
        Final difference when each param is set to mean - 1 std.
    sensitivity_high : np.ndarray
        Final difference when each param is set to mean + 1 std.
    sensitivity_base : float
        Base-case final difference (deterministic).
    base_config : SimulationConfig
        The base configuration used.
    mc_config : MonteCarloConfig
        The Monte Carlo configuration used.
    n_simulations : int
        Number of simulations that were run.

    Examples
    --------
    Access summary statistics from results:

    .. code-block:: python

        from simulator.monte_carlo import run_monte_carlo
        from simulator.models import SimulationConfig, MonteCarloConfig

        config = SimulationConfig(
            duration_years=10, property_price=500000,
            down_payment_pct=20, mortgage_rate_annual=4.5,
            property_appreciation_annual=3.0,
            equity_growth_annual=7.0, monthly_rent=2000,
        )
        mc_config = MonteCarloConfig(n_simulations=100)
        results = run_monte_carlo(config, mc_config)
        print(f"Buy wins {results.buy_wins_pct:.1f}% of the time")

    """

    final_net_buy: np.ndarray
    final_net_rent: np.ndarray
    final_differences: np.ndarray
    all_net_buy: np.ndarray
    all_net_rent: np.ndarray
    all_differences: np.ndarray
    year_arr: np.ndarray
    percentile_levels: list[int]
    difference_percentiles: np.ndarray
    buy_wins_pct: float
    median_difference: float
    p5_difference: float
    p95_difference: float
    sensitivity_params: list[str]
    sensitivity_low: np.ndarray
    sensitivity_high: np.ndarray
    sensitivity_base: float
    base_config: SimulationConfig
    mc_config: MonteCarloConfig
    n_simulations: int
