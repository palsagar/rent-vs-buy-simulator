"""Data models for the simulation engine."""

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd

# Capital gains treatment on the sale of the home at the end of the horizon.
SaleCgRegime = Literal["exempt_amount", "exempt_after_years", "fully_exempt"]


@dataclass
class SimulationConfig:
    """Configuration parameters for the simulation.

    Parameters
    ----------
    horizon_years : int
        Number of years until you'd sell (simulation horizon).
    property_price : float
        Initial price of the property ($).
    down_payment_pct : float
        Down payment as percentage of property price (5-100).
    mortgage_rate_annual : float
        Annual mortgage interest rate (as percentage, e.g., 4.5 for 4.5%).
    property_appreciation_annual : float
        Annual property appreciation rate (as percentage).
    equity_growth_annual : float
        Annual equity portfolio growth rate (as percentage, CAGR).
    monthly_rent : float
        Monthly rent payment ($).
    mortgage_term_years : int, optional
        Length of the mortgage amortization schedule in years.
        Default is 30.
    rent_inflation_rate : float, optional
        Annual rent inflation rate (as a decimal). Default is 0.03 (3%).
    closing_cost_buyer_pct : float, optional
        Buyer closing costs as percentage of property price.
        Default is 3.0 (3%).
    closing_cost_seller_pct : float, optional
        Seller closing costs as percentage of sale price.
        Default is 6.0 (6%).
    property_tax_rate : float, optional
        Annual property tax levy as percentage of home value.
        Default is 1.2 (1.2%).
    annual_home_insurance : float, optional
        Annual home insurance cost ($). Default is 1200.
    annual_maintenance_pct : float, optional
        Annual maintenance cost as percentage of current home value.
        Default is 1.0 (1%).
    cost_inflation_rate : float, optional
        Annual inflation rate for ongoing costs (insurance only), as a
        decimal. Default is 0.025 (2.5%).
    annual_property_levy : float, optional
        Flat annual property levy in the region's currency, paid
        monthly and indexed by ``cost_inflation_rate``. Additive to the
        ad-valorem ``property_tax_rate``. Default is 0.0.
    levy_paid_by_occupier : bool, optional
        Whether the levy is charged to the renter as well as the buyer
        (UK council tax; DE umlagefaehige Grundsteuer). Default is
        False.
    annual_maintenance_amount : float, optional
        Flat annual maintenance cost in the region's currency,
        cost-indexed. Additive to ``annual_maintenance_pct``. Default
        is 0.0.
    closing_cost_buyer_amount : float, optional
        Fixed buyer transaction cost added to the percentage-of-price
        term. May be negative: a transfer tax with a zero-rate band has
        a negative intercept (UK SDLT). Default is 0.0.
    portfolio_deemed_return_pct : float, optional
        Assumed annual return an annual wealth tax is charged on, as a
        percentage. The tax is assessed on the lesser of this and the
        actual return, floored at nil (NL box 3, Wet IB 2001 art.
        5.25). Default is 0.0.
    portfolio_drag_rate_pct : float, optional
        Rate applied to that deemed return each year, on portfolio
        value rather than on realised gains, symmetrically to both
        strategies' portfolios, as a percentage. Default is 0.0.
    interest_deduction_enabled : bool, optional
        Whether mortgage interest is tax-deductible. Default is True.
    marginal_tax_rate_pct : float, optional
        Marginal income tax rate as a percentage. Default is 24.0.
    levy_deduction_cap : float | None, optional
        Cap on deductible property tax/levy ($). None means uncapped.
        Default is 10000.0.
    sale_cg_regime : SaleCgRegime, optional
        Capital gains treatment applied on sale of the home. One of
        "exempt_amount", "exempt_after_years", "fully_exempt".
        Default is "exempt_amount".
    sale_cg_exempt_amount : float, optional
        Capital gains exempt from tax when sale_cg_regime is
        "exempt_amount" ($). Default is 250000.0.
    sale_cg_exempt_after_years : int, optional
        Years of ownership after which gains become exempt when
        sale_cg_regime is "exempt_after_years". Default is 10.
    sale_cg_rate_pct : float, optional
        Tax rate applied to non-exempt capital gains on sale, as a
        percentage. Default is 15.0.
    portfolio_cg_rate_pct : float, optional
        Tax rate applied to capital gains on the equity portfolio, as a
        percentage. Default is 15.0.

    Raises
    ------
    ValueError
        If any parameter fails its validation check (see
        :meth:`__post_init__`).

    Examples
    --------
    Create a simulation configuration:

    .. code-block:: python

        from simulator.models import SimulationConfig

        config = SimulationConfig(
            horizon_years=10,
            property_price=500000,
            down_payment_pct=20,
            mortgage_rate_annual=4.5,
            property_appreciation_annual=3,
            equity_growth_annual=7,
            monthly_rent=2000
        )

    """

    horizon_years: int
    property_price: float
    down_payment_pct: float
    mortgage_rate_annual: float
    property_appreciation_annual: float
    equity_growth_annual: float
    monthly_rent: float
    mortgage_term_years: int = 30
    rent_inflation_rate: float = 0.03
    closing_cost_buyer_pct: float = 3.0
    closing_cost_seller_pct: float = 6.0
    property_tax_rate: float = 1.2
    annual_home_insurance: float = 1200.0
    annual_maintenance_pct: float = 1.0
    cost_inflation_rate: float = 0.025
    # Multi-region primitives (ADR-0007). All default to a value that
    # leaves the US preset bit-identical.
    annual_property_levy: float = 0.0
    levy_paid_by_occupier: bool = False
    annual_maintenance_amount: float = 0.0
    closing_cost_buyer_amount: float = 0.0
    portfolio_deemed_return_pct: float = 0.0
    portfolio_drag_rate_pct: float = 0.0
    # Tax benefit parameters
    interest_deduction_enabled: bool = True
    marginal_tax_rate_pct: float = 24.0
    levy_deduction_cap: float | None = 10000.0
    sale_cg_regime: SaleCgRegime = "exempt_amount"
    sale_cg_exempt_amount: float = 250000.0
    sale_cg_exempt_after_years: int = 10
    sale_cg_rate_pct: float = 15.0
    portfolio_cg_rate_pct: float = 15.0

    def __post_init__(self) -> None:  # noqa: C901
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
                horizon_years=10,
                property_price=500000,
                down_payment_pct=20,
                mortgage_rate_annual=4.5,
                property_appreciation_annual=3,
                equity_growth_annual=7,
                monthly_rent=2000
            )
            # Validation passed successfully

        """
        # Validate horizon_years (upper cap guards against OOM: every array
        # is sized horizon_years * 12 + 1, and Monte Carlo allocates
        # ~500 of them, so an unbounded client value can exhaust memory)
        if not (1 <= self.horizon_years <= 100):
            raise ValueError(
                f"horizon_years must be between 1 and 100 (got {self.horizon_years})."
            )

        # Validate mortgage_term_years (same OOM guard as horizon_years)
        if not (1 <= self.mortgage_term_years <= 100):
            raise ValueError(
                f"mortgage_term_years must be between 1 and 100 "
                f"(got {self.mortgage_term_years})."
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

        # Cap mortgage_rate_annual so it is not the one unbounded compounding
        # rate; no realistic rate exceeds 100%.
        if self.mortgage_rate_annual > 100:
            raise ValueError(
                "mortgage_rate_annual must be <= 100 "
                f"(got {self.mortgage_rate_annual})."
            )

        # Bound the annual growth rates (percentages). The upper cap of 100 keeps
        # the 1200-month cumprod far below float overflow (which needs a
        # several-hundred-percent rate); the -50 floor still permits a severe
        # single-year market crash.
        if not (-50 <= self.property_appreciation_annual <= 100):
            raise ValueError(
                "property_appreciation_annual must be between -50 and 100 "
                f"(got {self.property_appreciation_annual})."
            )
        if not (-50 <= self.equity_growth_annual <= 100):
            raise ValueError(
                "equity_growth_annual must be between -50 and 100 "
                f"(got {self.equity_growth_annual})."
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

        # Validate cost_inflation_rate (must be between 0 and 1, i.e., 0-100%)
        if not (0 <= self.cost_inflation_rate <= 1):
            raise ValueError(
                f"cost_inflation_rate must be 0-1 (got {self.cost_inflation_rate}). "
                "For 2.5% annual inflation, use 0.025. For no inflation, use 0."
            )

        # Multi-region primitives. Upper bounds are generous sanity caps,
        # not statutory limits.
        if not (0 <= self.annual_property_levy <= 100_000):
            raise ValueError(
                "annual_property_levy must be between 0 and 100000 "
                f"(got {self.annual_property_levy})."
            )

        if not (0 <= self.annual_maintenance_amount <= 100_000):
            raise ValueError(
                "annual_maintenance_amount must be between 0 and 100000 "
                f"(got {self.annual_maintenance_amount})."
            )

        # Negatives are legitimate: a transfer tax with a zero-rate band
        # has a negative intercept (UK SDLT ships -6,900). The engine
        # clamps the aggregate buyer cost at zero instead.
        if not (-100_000 <= self.closing_cost_buyer_amount <= 100_000):
            raise ValueError(
                "closing_cost_buyer_amount must be between -100000 and "
                f"100000 (got {self.closing_cost_buyer_amount})."
            )

        # Together the two 100 ceilings keep the monthly drag at or below
        # 1.0 * 1.0 / 12 = 0.0833, so (1 + monthly growth - monthly drag)
        # stays above -1 for every reachable growth rate.
        if not (0 <= self.portfolio_deemed_return_pct <= 100):
            raise ValueError(
                "portfolio_deemed_return_pct must be between 0 and 100 "
                f"(got {self.portfolio_deemed_return_pct})."
            )

        if not (0 <= self.portfolio_drag_rate_pct <= 100):
            raise ValueError(
                "portfolio_drag_rate_pct must be between 0 and 100 "
                f"(got {self.portfolio_drag_rate_pct})."
            )

        # Validate marginal_tax_rate_pct (must be between 0 and 100)
        if not (0 <= self.marginal_tax_rate_pct <= 100):
            raise ValueError(
                "marginal_tax_rate_pct must be between 0 and 100 "
                f"(got {self.marginal_tax_rate_pct}). "
                "For no tax benefits, use 0."
            )

        # Validate levy_deduction_cap (None means uncapped; else non-negative)
        if self.levy_deduction_cap is not None and self.levy_deduction_cap < 0:
            raise ValueError(
                "levy_deduction_cap cannot be negative "
                f"(got {self.levy_deduction_cap}). Use None for uncapped."
            )

        # Validate sale_cg_regime
        # NOTE: this tuple hand-duplicates the SaleCgRegime Literal declared
        # at the top of this module. Adding a fourth regime requires editing
        # both or the new value is silently rejected here.
        valid_regimes = ("exempt_amount", "exempt_after_years", "fully_exempt")
        if self.sale_cg_regime not in valid_regimes:
            raise ValueError(
                f"sale_cg_regime must be one of {valid_regimes} "
                f"(got {self.sale_cg_regime!r})."
            )

        # Validate sale_cg_exempt_amount (must be non-negative)
        if self.sale_cg_exempt_amount < 0:
            raise ValueError(
                "sale_cg_exempt_amount cannot be negative "
                f"(got {self.sale_cg_exempt_amount})."
            )

        # Validate sale_cg_exempt_after_years (must be non-negative)
        if self.sale_cg_exempt_after_years < 0:
            raise ValueError(
                "sale_cg_exempt_after_years cannot be negative "
                f"(got {self.sale_cg_exempt_after_years})."
            )

        # Validate sale_cg_rate_pct (must be between 0 and 100)
        if not (0 <= self.sale_cg_rate_pct <= 100):
            raise ValueError(
                "sale_cg_rate_pct must be between 0 and 100 "
                f"(got {self.sale_cg_rate_pct})."
            )

        # Validate portfolio_cg_rate_pct (must be between 0 and 100)
        if not (0 <= self.portfolio_cg_rate_pct <= 100):
            raise ValueError(
                "portfolio_cg_rate_pct must be between 0 and 100 "
                f"(got {self.portfolio_cg_rate_pct})."
            )


@dataclass
class SimulationResults:
    """Results from the simulation engine.

    Parameters
    ----------
    data : pd.DataFrame
        DataFrame containing the per-month time-series columns.
    final_net_buy : float
        Final net value for the buying scenario.
    final_net_rent : float
        Final net value for the rent-and-invest scenario.
    final_difference : float
        Difference between buying and renting (Buy - Rent); the Verdict.
    breakeven_year : float | None
        Year when net values cross (None if they never cross).
    monthly_mortgage_payment : float
        Monthly mortgage payment amount.
    monthly_cost_buy_year1 : float
        Mean month-1..12 buyer housing cost.
    monthly_cost_rent_year1 : float
        Mean month-1..12 renter housing cost.
    total_closing_costs_buyer : float
        Total closing costs paid by the buyer.
    total_closing_costs_seller : float
        Total closing costs paid by the seller on sale.
    total_property_tax_paid : float
        Total property tax paid over the horizon.
    total_insurance_paid : float
        Total home insurance paid over the horizon.
    total_maintenance_paid : float
        Total maintenance cost paid over the horizon.
    total_mortgage_interest_paid : float
        Total mortgage interest accrued over the horizon.
    total_tax_savings : float
        Total tax savings from mortgage interest / levy deductions.

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
            'Net_Buy': [400000, 397000, 394450],
            'Net_Rent': [100000, 83000, 66490],
        })

        results = SimulationResults(
            data=df,
            final_net_buy=394450,
            final_net_rent=66490,
            final_difference=327960,
            breakeven_year=None,
            monthly_mortgage_payment=2500,
            monthly_cost_buy_year1=3200,
            monthly_cost_rent_year1=2400,
            total_closing_costs_buyer=15000,
            total_closing_costs_seller=0,
            total_property_tax_paid=6000,
            total_insurance_paid=1200,
            total_maintenance_paid=5000,
            total_mortgage_interest_paid=140000,
            total_tax_savings=8000,
        )

    """

    data: pd.DataFrame
    final_net_buy: float
    final_net_rent: float
    final_difference: float
    breakeven_year: float | None
    monthly_mortgage_payment: float
    monthly_cost_buy_year1: float
    monthly_cost_rent_year1: float
    total_closing_costs_buyer: float
    total_closing_costs_seller: float
    total_property_tax_paid: float
    total_insurance_paid: float
    total_maintenance_paid: float
    total_mortgage_interest_paid: float
    total_tax_savings: float


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
        appreciation draws. Default is 8.0.
    randomize_equity_growth : bool
        Whether to randomize annual equity growth. Default True.
    equity_growth_std : float
        Standard deviation (in percentage points) for equity growth
        draws. Default is 15.0.
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
    property_appreciation_std: float = 8.0
    randomize_equity_growth: bool = True
    equity_growth_std: float = 15.0
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
            horizon_years=10, property_price=500000,
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
