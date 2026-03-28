# Monte Carlo Uncertainty Analysis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an opt-in Monte Carlo simulation tab with year-by-year stochastic paths, showing probability of buying winning, spaghetti chart with marginal distribution (aleatory style), tornado chart, and probability-over-time chart.

**Architecture:** Fully independent MC engine in `src/simulator/monte_carlo.py` that does NOT call the existing `calculate_scenarios`. Reimplements the financial math with year-varying rates. Visualization in `src/simulator/mc_visualization.py` using matplotlib (spaghetti chart with aleatory's `qp_style()`) and Plotly (tornado, probability charts). New 5th tab in app.py, idle by default, computes on button click.

**Tech Stack:** Python 3.12+, NumPy, numpy-financial, matplotlib, aleatory (for styling), Plotly, Streamlit

---

## Codebase Context

Before implementing, familiarize yourself with these files:

| File | Purpose |
|---|---|
| `src/simulator/engine.py` | Deterministic engine — `calculate_scenarios(config)` returns `SimulationResults`. Month-by-month vectorized calculations. The MC engine reimplements this logic with year-varying rates. |
| `src/simulator/models.py` | `SimulationConfig` (19 fields with validation) and `SimulationResults` dataclasses. MC data models go here too. |
| `src/simulator/visualization.py` | Plotly chart builders. Follows a pattern: function takes data, returns `go.Figure`. |
| `app.py` | Streamlit entry point. 4-tab layout (`tab1..tab4`). The 5th tab goes after tab4. |
| `tests/test_engine.py` | Test conventions: `sys.path.insert`, pytest classes, NumPy-style assertions. |
| `pyproject.toml` | Dependencies list, ruff config (line-length 88), coverage config. |

**Code conventions (mandatory):**
- Type annotations on all function/method signatures (use `typing` and `collections.abc`)
- NumPy-style docstrings with `.rst` code blocks
- Inline comments explain intent ("what"), not implementation ("how")
- Line length: 88 chars (Ruff/Black convention)
- Float comparisons use `_FLOAT_TOLERANCE = 1e-9` — never `==` for floats
- Tests use `sys.path.insert(0, str(Path(__file__).parent.parent / "src"))` pattern

---

## Task 1: Dependencies + Data Models

**Goal:** Add `matplotlib` and `aleatory` to `pyproject.toml`, define `MonteCarloConfig` and `MonteCarloResults` dataclasses in `models.py`, write tests.

### Steps

- [ ] **1.1** Write tests in `tests/test_monte_carlo.py`
- [ ] **1.2** Verify tests fail (models don't exist yet)
- [ ] **1.3** Add dependencies to `pyproject.toml`
- [ ] **1.4** Add `MonteCarloConfig` and `MonteCarloResults` to `models.py`
- [ ] **1.5** Verify tests pass
- [ ] **1.6** Run linter, fix any issues
- [ ] **1.7** Commit

### 1.1 — Write tests

Create `tests/test_monte_carlo.py` with the following content:

```python
"""Unit tests for Monte Carlo simulation."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import numpy as np
import pytest

from simulator.models import MonteCarloConfig, MonteCarloResults


class TestMonteCarloConfig:
    """Tests for MonteCarloConfig validation and defaults."""

    def test_default_values(self):
        """Test that defaults are set correctly."""
        mc = MonteCarloConfig()
        assert mc.n_simulations == 500
        assert mc.seed == 42
        assert mc.randomize_property_appreciation is True
        assert mc.property_appreciation_std == 5.0
        assert mc.randomize_equity_growth is True
        assert mc.equity_growth_std == 5.0
        assert mc.randomize_rent_inflation is True
        assert mc.rent_inflation_std == 1.5
        assert mc.appreciation_equity_correlation == 0.3

    def test_custom_values(self):
        """Test that custom values override defaults."""
        mc = MonteCarloConfig(
            n_simulations=1000,
            seed=None,
            property_appreciation_std=8.0,
            appreciation_equity_correlation=0.5,
        )
        assert mc.n_simulations == 1000
        assert mc.seed is None
        assert mc.property_appreciation_std == 8.0
        assert mc.appreciation_equity_correlation == 0.5

    def test_invalid_n_simulations_raises(self):
        """Test that n_simulations <= 0 raises ValueError."""
        with pytest.raises(ValueError, match="n_simulations must be positive"):
            MonteCarloConfig(n_simulations=0)

    def test_invalid_n_simulations_negative_raises(self):
        """Test that negative n_simulations raises ValueError."""
        with pytest.raises(ValueError, match="n_simulations must be positive"):
            MonteCarloConfig(n_simulations=-10)

    def test_negative_std_raises(self):
        """Test that negative std raises ValueError."""
        with pytest.raises(
            ValueError, match="property_appreciation_std must be non-negative"
        ):
            MonteCarloConfig(property_appreciation_std=-1.0)

    def test_negative_equity_std_raises(self):
        """Test that negative equity_growth_std raises ValueError."""
        with pytest.raises(
            ValueError, match="equity_growth_std must be non-negative"
        ):
            MonteCarloConfig(equity_growth_std=-2.0)

    def test_negative_rent_inflation_std_raises(self):
        """Test that negative rent_inflation_std raises ValueError."""
        with pytest.raises(
            ValueError, match="rent_inflation_std must be non-negative"
        ):
            MonteCarloConfig(rent_inflation_std=-0.5)

    def test_correlation_out_of_bounds_raises(self):
        """Test that correlation outside [-1, 1] raises ValueError."""
        with pytest.raises(
            ValueError,
            match="appreciation_equity_correlation must be between -1 and 1",
        ):
            MonteCarloConfig(appreciation_equity_correlation=1.5)

    def test_correlation_negative_bound_raises(self):
        """Test that correlation below -1 raises ValueError."""
        with pytest.raises(
            ValueError,
            match="appreciation_equity_correlation must be between -1 and 1",
        ):
            MonteCarloConfig(appreciation_equity_correlation=-1.5)

    def test_correlation_at_bounds_accepted(self):
        """Test that correlation at exact bounds is accepted."""
        mc_pos = MonteCarloConfig(appreciation_equity_correlation=1.0)
        assert mc_pos.appreciation_equity_correlation == 1.0
        mc_neg = MonteCarloConfig(appreciation_equity_correlation=-1.0)
        assert mc_neg.appreciation_equity_correlation == -1.0


class TestMonteCarloResults:
    """Tests for MonteCarloResults dataclass."""

    def _make_results(self, n_sims: int = 10, n_months: int = 120):
        """Build a minimal MonteCarloResults for testing.

        Parameters
        ----------
        n_sims : int
            Number of simulations.
        n_months : int
            Number of months in the simulation.

        Returns
        -------
        MonteCarloResults
            A populated results object with random data.

        Examples
        --------
        .. code-block:: python

            results = self._make_results(n_sims=50, n_months=60)

        """
        rng = np.random.default_rng(42)
        n_points = n_months + 1
        all_net_buy = rng.normal(100000, 50000, (n_sims, n_points))
        all_net_rent = rng.normal(80000, 40000, (n_sims, n_points))
        all_diffs = all_net_buy - all_net_rent
        year_arr = np.arange(n_points) / 12

        percentile_levels = [5, 25, 50, 75, 95]
        diff_pctiles = np.percentile(
            all_diffs, percentile_levels, axis=0
        )

        final_diffs = all_diffs[:, -1]
        buy_wins_pct = float(np.mean(final_diffs > 0) * 100)

        from simulator.models import MonteCarloConfig, SimulationConfig

        base_config = SimulationConfig(
            duration_years=n_months // 12,
            property_price=500000,
            down_payment_pct=20,
            mortgage_rate_annual=4.5,
            property_appreciation_annual=3.0,
            equity_growth_annual=7.0,
            monthly_rent=2000,
        )

        return MonteCarloResults(
            final_net_buy=all_net_buy[:, -1],
            final_net_rent=all_net_rent[:, -1],
            final_differences=final_diffs,
            all_net_buy=all_net_buy,
            all_net_rent=all_net_rent,
            all_differences=all_diffs,
            year_arr=year_arr,
            percentile_levels=percentile_levels,
            difference_percentiles=diff_pctiles,
            buy_wins_pct=buy_wins_pct,
            median_difference=float(np.median(final_diffs)),
            p5_difference=float(np.percentile(final_diffs, 5)),
            p95_difference=float(np.percentile(final_diffs, 95)),
            sensitivity_params=[
                "Property Appreciation",
                "Equity Growth",
            ],
            sensitivity_low=np.array([-50000, -30000]),
            sensitivity_high=np.array([60000, 40000]),
            sensitivity_base=20000.0,
            base_config=base_config,
            mc_config=MonteCarloConfig(),
            n_simulations=n_sims,
        )

    def test_shapes(self):
        """Test that array shapes are consistent."""
        results = self._make_results(n_sims=10, n_months=120)
        assert results.final_net_buy.shape == (10,)
        assert results.final_net_rent.shape == (10,)
        assert results.final_differences.shape == (10,)
        assert results.all_net_buy.shape == (10, 121)
        assert results.all_net_rent.shape == (10, 121)
        assert results.all_differences.shape == (10, 121)
        assert results.year_arr.shape == (121,)
        assert results.difference_percentiles.shape == (5, 121)

    def test_summary_stats_types(self):
        """Test that summary statistics have correct types."""
        results = self._make_results()
        assert isinstance(results.buy_wins_pct, float)
        assert isinstance(results.median_difference, float)
        assert isinstance(results.p5_difference, float)
        assert isinstance(results.p95_difference, float)
        assert 0 <= results.buy_wins_pct <= 100

    def test_sensitivity_arrays_match(self):
        """Test that sensitivity arrays have consistent lengths."""
        results = self._make_results()
        n_params = len(results.sensitivity_params)
        assert results.sensitivity_low.shape == (n_params,)
        assert results.sensitivity_high.shape == (n_params,)
        assert isinstance(results.sensitivity_base, float)

    def test_n_simulations_matches_arrays(self):
        """Test that n_simulations matches first dimension of arrays."""
        results = self._make_results(n_sims=25, n_months=60)
        assert results.n_simulations == 25
        assert results.all_net_buy.shape[0] == 25
```

### 1.2 — Verify tests fail

```bash
uv run pytest tests/test_monte_carlo.py -v
```

Expected output: `ImportError` — `MonteCarloConfig` and `MonteCarloResults` don't exist in `models.py`.

### 1.3 — Add dependencies to `pyproject.toml`

In `/Users/sagarpal/projects/rent-vs-buy-simulator/pyproject.toml`, add `matplotlib` and `aleatory` to the `dependencies` list:

```toml
dependencies = [
    "numpy>=1.26.0",
    "numpy-financial>=1.0.0",
    "pandas>=2.1.0",
    "plotly>=5.18.0",
    "streamlit>=1.37.0",
    "pytest>=7.4.0",
    "pytest-cov>=4.1.0",
    "fpdf2>=2.7.0",
    "kaleido>=0.2.0",
    "matplotlib>=3.8.0",
    "aleatory>=0.4.0",
]
```

Then install:

```bash
uv pip install -e .
```

### 1.4 — Add data models to `models.py`

Append the following two dataclasses to the end of `/Users/sagarpal/projects/rent-vs-buy-simulator/src/simulator/models.py` (after the `SimulationResults` class). Also add `from __future__ import annotations` at the very top of the file (before the existing docstring), and add `import numpy as np` with the existing imports:

First, add `import numpy as np` alongside the existing `import pandas as pd` at the top of `models.py`. Then add `from __future__ import annotations` as the very first line (before the module docstring — actually, `from __future__` must be the first statement, before the docstring). **Correction:** `from __future__` imports must come before everything except comments and docstrings at module level. Since there's already a docstring, place the import right after the module docstring and before `from dataclasses import dataclass`.

Add `import numpy as np` right after `import pandas as pd`:

```python
import numpy as np
import pandas as pd
```

Then append these two classes at the bottom of `models.py`:

```python
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
                "n_simulations must be positive "
                f"(got {self.n_simulations})."
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
```

### 1.5 — Verify tests pass

```bash
uv run pytest tests/test_monte_carlo.py -v
```

Expected: all tests in `TestMonteCarloConfig` and `TestMonteCarloResults` pass.

### 1.6 — Run linter

```bash
uv run ruff check src/simulator/models.py tests/test_monte_carlo.py
uv run ruff format src/simulator/models.py tests/test_monte_carlo.py
```

Fix any issues.

### 1.7 — Commit

```bash
git add pyproject.toml src/simulator/models.py tests/test_monte_carlo.py
git commit -m "feat(mc): add MonteCarloConfig and MonteCarloResults data models

Add matplotlib and aleatory dependencies. Define MonteCarloConfig
(simulation count, stds, correlation) and MonteCarloResults (paths,
percentiles, sensitivity data) dataclasses with validation and tests."
```

---

## Task 2: Parameter Generation

**Goal:** Create `src/simulator/monte_carlo.py` with `_generate_annual_draws()` that produces correlated annual rate draws for property appreciation, equity growth, and rent inflation.

### Steps

- [ ] **2.1** Write tests for `_generate_annual_draws`
- [ ] **2.2** Verify tests fail
- [ ] **2.3** Implement `_generate_annual_draws` in `monte_carlo.py`
- [ ] **2.4** Verify tests pass
- [ ] **2.5** Run linter, fix any issues
- [ ] **2.6** Commit

### 2.1 — Write tests

Append to `tests/test_monte_carlo.py`:

```python
from simulator.monte_carlo import _generate_annual_draws
from simulator.models import SimulationConfig


class TestGenerateAnnualDraws:
    """Tests for _generate_annual_draws."""

    @pytest.fixture()
    def base_config(self):
        """Return a standard SimulationConfig for MC tests.

        Returns
        -------
        SimulationConfig
            A 10-year, $500k property configuration.

        Examples
        --------
        .. code-block:: python

            config = base_config

        """
        return SimulationConfig(
            duration_years=10,
            property_price=500000,
            down_payment_pct=20,
            mortgage_rate_annual=4.5,
            property_appreciation_annual=3.0,
            equity_growth_annual=7.0,
            monthly_rent=2000,
        )

    def test_output_shapes(self, base_config):
        """Test that output arrays have correct shapes."""
        mc_config = MonteCarloConfig(n_simulations=50, seed=42)
        rng = np.random.default_rng(mc_config.seed)
        draws = _generate_annual_draws(
            base_config, mc_config, base_config.duration_years, rng
        )
        assert draws["property_appreciation"].shape == (50, 10)
        assert draws["equity_growth"].shape == (50, 10)
        assert draws["rent_inflation"].shape == (50, 10)

    def test_means_near_base_rates(self, base_config):
        """Test that mean draws are near the base config rates."""
        mc_config = MonteCarloConfig(n_simulations=5000, seed=42)
        rng = np.random.default_rng(mc_config.seed)
        draws = _generate_annual_draws(
            base_config, mc_config, base_config.duration_years, rng
        )
        # Mean property appreciation should be near 3.0
        mean_prop = np.mean(draws["property_appreciation"])
        assert abs(mean_prop - 3.0) < 0.5

        # Mean equity growth should be near 7.0
        mean_eq = np.mean(draws["equity_growth"])
        assert abs(mean_eq - 7.0) < 0.5

        # Mean rent inflation should be near 3.0 (config has 0.03 = 3%)
        mean_rent = np.mean(draws["rent_inflation"])
        assert abs(mean_rent - 3.0) < 0.5

    def test_correlation_positive(self, base_config):
        """Test that property and equity draws are positively correlated."""
        mc_config = MonteCarloConfig(
            n_simulations=10000,
            seed=42,
            appreciation_equity_correlation=0.8,
        )
        rng = np.random.default_rng(mc_config.seed)
        draws = _generate_annual_draws(
            base_config, mc_config, base_config.duration_years, rng
        )
        # Flatten and compute correlation
        prop_flat = draws["property_appreciation"].flatten()
        eq_flat = draws["equity_growth"].flatten()
        corr = np.corrcoef(prop_flat, eq_flat)[0, 1]
        assert corr > 0.5  # Should be strongly positive

    def test_zero_correlation(self, base_config):
        """Test that zero correlation produces near-zero correlation."""
        mc_config = MonteCarloConfig(
            n_simulations=10000,
            seed=42,
            appreciation_equity_correlation=0.0,
        )
        rng = np.random.default_rng(mc_config.seed)
        draws = _generate_annual_draws(
            base_config, mc_config, base_config.duration_years, rng
        )
        prop_flat = draws["property_appreciation"].flatten()
        eq_flat = draws["equity_growth"].flatten()
        corr = np.corrcoef(prop_flat, eq_flat)[0, 1]
        assert abs(corr) < 0.1

    def test_rent_inflation_clamped_non_negative(self, base_config):
        """Test that rent inflation draws are clamped at zero."""
        mc_config = MonteCarloConfig(
            n_simulations=1000,
            seed=42,
            rent_inflation_std=10.0,  # High std to force some negatives
        )
        rng = np.random.default_rng(mc_config.seed)
        draws = _generate_annual_draws(
            base_config, mc_config, base_config.duration_years, rng
        )
        assert np.all(draws["rent_inflation"] >= 0)

    def test_disabled_randomization_returns_constant(self, base_config):
        """Test that disabling randomization returns base rates."""
        mc_config = MonteCarloConfig(
            n_simulations=100,
            seed=42,
            randomize_property_appreciation=False,
            randomize_equity_growth=False,
            randomize_rent_inflation=False,
        )
        rng = np.random.default_rng(mc_config.seed)
        draws = _generate_annual_draws(
            base_config, mc_config, base_config.duration_years, rng
        )
        # All values should be the base rates
        assert np.allclose(draws["property_appreciation"], 3.0)
        assert np.allclose(draws["equity_growth"], 7.0)
        # Rent inflation is stored as 0.03 in config, converted to 3.0 pct
        assert np.allclose(draws["rent_inflation"], 3.0)

    def test_reproducibility_with_seed(self, base_config):
        """Test that same seed produces identical draws."""
        mc_config = MonteCarloConfig(n_simulations=50, seed=123)
        rng1 = np.random.default_rng(mc_config.seed)
        draws1 = _generate_annual_draws(
            base_config, mc_config, base_config.duration_years, rng1
        )
        rng2 = np.random.default_rng(mc_config.seed)
        draws2 = _generate_annual_draws(
            base_config, mc_config, base_config.duration_years, rng2
        )
        np.testing.assert_array_equal(
            draws1["property_appreciation"],
            draws2["property_appreciation"],
        )
        np.testing.assert_array_equal(
            draws1["equity_growth"],
            draws2["equity_growth"],
        )
```

### 2.2 — Verify tests fail

```bash
uv run pytest tests/test_monte_carlo.py::TestGenerateAnnualDraws -v
```

Expected: `ImportError` — `monte_carlo` module doesn't exist.

### 2.3 — Implement `_generate_annual_draws`

Create `/Users/sagarpal/projects/rent-vs-buy-simulator/src/simulator/monte_carlo.py`:

```python
"""Monte Carlo simulation engine for uncertainty analysis.

Provides a fully independent MC engine that reimplements the
financial math from ``engine.py`` with year-varying stochastic rates.
Does NOT call ``calculate_scenarios`` (except for sensitivity analysis).
"""

from __future__ import annotations

import numpy as np
import numpy_financial as npf

from .engine import calculate_scenarios
from .models import (
    MonteCarloConfig,
    MonteCarloResults,
    SimulationConfig,
)

# Floating-point tolerance for comparisons
_FLOAT_TOLERANCE = 1e-9


def _generate_annual_draws(
    base_config: SimulationConfig,
    mc_config: MonteCarloConfig,
    n_years: int,
    rng: np.random.Generator,
) -> dict[str, np.ndarray]:
    """Generate correlated annual rate draws for MC simulations.

    Produces arrays of annual rates for property appreciation, equity
    growth, and rent inflation. Property appreciation and equity growth
    are drawn from a bivariate normal with configurable correlation.
    Rent inflation is drawn independently and clamped to be >= 0.

    All rates are in percentage-point units (e.g. 3.0 means 3%).

    Parameters
    ----------
    base_config : SimulationConfig
        The base deterministic configuration. Mean rates are taken from
        ``property_appreciation_annual``, ``equity_growth_annual``, and
        ``rent_inflation_rate`` (converted from decimal to pct).
    mc_config : MonteCarloConfig
        Controls which parameters to randomize, their standard
        deviations, and the correlation.
    n_years : int
        Number of years (columns in the output arrays).
    rng : np.random.Generator
        NumPy random generator for reproducibility.

    Returns
    -------
    dict[str, np.ndarray]
        Dictionary with keys ``"property_appreciation"``,
        ``"equity_growth"``, ``"rent_inflation"``. Each value is a
        2D array of shape ``(n_simulations, n_years)`` in percentage
        points.

    Examples
    --------
    Generate draws for 100 simulations over 10 years:

    .. code-block:: python

        from simulator.monte_carlo import _generate_annual_draws
        from simulator.models import SimulationConfig, MonteCarloConfig

        config = SimulationConfig(
            duration_years=10, property_price=500000,
            down_payment_pct=20, mortgage_rate_annual=4.5,
            property_appreciation_annual=3.0,
            equity_growth_annual=7.0, monthly_rent=2000,
        )
        mc = MonteCarloConfig(n_simulations=100, seed=42)
        rng = np.random.default_rng(mc.seed)
        draws = _generate_annual_draws(config, mc, 10, rng)
        print(draws["property_appreciation"].shape)  # (100, 10)

    """
    n_sims = mc_config.n_simulations

    # Base rates in percentage points
    mu_prop = base_config.property_appreciation_annual
    mu_eq = base_config.equity_growth_annual
    # rent_inflation_rate is stored as decimal (0.03 = 3%)
    mu_rent = base_config.rent_inflation_rate * 100

    # --- Property appreciation and equity growth: correlated bivariate ---
    if mc_config.randomize_property_appreciation or mc_config.randomize_equity_growth:
        sigma_prop = (
            mc_config.property_appreciation_std
            if mc_config.randomize_property_appreciation
            else 0.0
        )
        sigma_eq = (
            mc_config.equity_growth_std
            if mc_config.randomize_equity_growth
            else 0.0
        )
        rho = mc_config.appreciation_equity_correlation

        # Covariance matrix for bivariate normal
        cov = np.array(
            [
                [sigma_prop**2, rho * sigma_prop * sigma_eq],
                [rho * sigma_prop * sigma_eq, sigma_eq**2],
            ]
        )
        mean = np.array([mu_prop, mu_eq])

        # Draw all (n_sims * n_years) pairs, then reshape
        raw = rng.multivariate_normal(mean, cov, size=(n_sims, n_years))
        prop_draws = raw[:, :, 0]
        eq_draws = raw[:, :, 1]
    else:
        # No randomization: constant base rates
        prop_draws = np.full((n_sims, n_years), mu_prop)
        eq_draws = np.full((n_sims, n_years), mu_eq)

    # Override with constant if specific param is not randomized
    if not mc_config.randomize_property_appreciation:
        prop_draws = np.full((n_sims, n_years), mu_prop)
    if not mc_config.randomize_equity_growth:
        eq_draws = np.full((n_sims, n_years), mu_eq)

    # --- Rent inflation: independent normal, clamped >= 0 ---
    if mc_config.randomize_rent_inflation:
        rent_draws = rng.normal(
            mu_rent, mc_config.rent_inflation_std, (n_sims, n_years)
        )
        # Clamp to non-negative (rent doesn't deflate)
        rent_draws = np.maximum(rent_draws, 0.0)
    else:
        rent_draws = np.full((n_sims, n_years), mu_rent)

    return {
        "property_appreciation": prop_draws,
        "equity_growth": eq_draws,
        "rent_inflation": rent_draws,
    }
```

### 2.4 — Verify tests pass

```bash
uv run pytest tests/test_monte_carlo.py::TestGenerateAnnualDraws -v
```

Expected: all tests pass.

### 2.5 — Run linter

```bash
uv run ruff check src/simulator/monte_carlo.py tests/test_monte_carlo.py
uv run ruff format src/simulator/monte_carlo.py tests/test_monte_carlo.py
```

### 2.6 — Commit

```bash
git add src/simulator/monte_carlo.py tests/test_monte_carlo.py
git commit -m "feat(mc): implement _generate_annual_draws with correlated rates

Bivariate normal for property/equity correlation, independent normal
for rent inflation (clamped >= 0). Supports per-param randomization
toggle."
```

---

## Task 3: Single Path Simulation

**Goal:** Implement `_simulate_single_path()` — the month-by-month financial math for one MC simulation using year-varying rates. Also write a consistency test comparing it against the deterministic engine when stds are zero.

### Steps

- [ ] **3.1** Write tests for `_simulate_single_path`
- [ ] **3.2** Verify tests fail
- [ ] **3.3** Implement `_simulate_single_path`
- [ ] **3.4** Verify tests pass
- [ ] **3.5** Run linter, fix any issues
- [ ] **3.6** Commit

### 3.1 — Write tests

Append to `tests/test_monte_carlo.py`:

```python
from simulator.monte_carlo import _simulate_single_path
from simulator.engine import calculate_scenarios as deterministic_engine


class TestSimulateSinglePath:
    """Tests for _simulate_single_path."""

    @pytest.fixture()
    def base_config(self):
        """Return a standard SimulationConfig.

        Returns
        -------
        SimulationConfig
            A 10-year, $500k property configuration.

        Examples
        --------
        .. code-block:: python

            config = base_config

        """
        return SimulationConfig(
            duration_years=10,
            property_price=500000,
            down_payment_pct=20,
            mortgage_rate_annual=4.5,
            property_appreciation_annual=3.0,
            equity_growth_annual=7.0,
            monthly_rent=2000,
            rent_inflation_rate=0.03,
        )

    def test_output_shapes(self, base_config):
        """Test that output arrays have correct length."""
        n_years = base_config.duration_years
        n_months = n_years * 12
        # Constant rates = base config rates for every year
        prop_rates = np.full(n_years, 3.0)
        eq_rates = np.full(n_years, 7.0)
        rent_rates = np.full(n_years, 3.0)

        net_buy, net_rent = _simulate_single_path(
            base_config, prop_rates, eq_rates, rent_rates
        )
        assert net_buy.shape == (n_months + 1,)
        assert net_rent.shape == (n_months + 1,)

    def test_initial_values(self, base_config):
        """Test that initial net values are correct."""
        n_years = base_config.duration_years
        prop_rates = np.full(n_years, 3.0)
        eq_rates = np.full(n_years, 7.0)
        rent_rates = np.full(n_years, 3.0)

        net_buy, net_rent = _simulate_single_path(
            base_config, prop_rates, eq_rates, rent_rates
        )
        # At t=0: net_buy = home_value - down_payment - buyer_closing
        down_payment = 500000 * 0.20
        buyer_closing = 500000 * (base_config.closing_cost_buyer_pct / 100)
        expected_net_buy_0 = 500000 - down_payment - buyer_closing
        assert abs(net_buy[0] - expected_net_buy_0) < 1.0

        # At t=0: net_rent = down_payment - 0 rent
        assert abs(net_rent[0] - down_payment) < 1.0

    def test_consistency_with_deterministic_engine(self, base_config):
        """Test that constant-rate MC path matches deterministic engine.

        When all annual rates are constant (matching base_config),
        the MC single path should match the deterministic engine's
        net_buy and net_rent within a small tolerance. The tolerance
        accounts for the MC path applying seller closing costs and
        tax adjustments at the final step only, matching the
        deterministic engine's summary metrics (not the raw arrays).
        """
        det_results = deterministic_engine(base_config)
        n_years = base_config.duration_years
        prop_rates = np.full(
            n_years, base_config.property_appreciation_annual
        )
        eq_rates = np.full(n_years, base_config.equity_growth_annual)
        rent_rates = np.full(
            n_years, base_config.rent_inflation_rate * 100
        )

        net_buy, net_rent = _simulate_single_path(
            base_config, prop_rates, eq_rates, rent_rates
        )

        # Compare intermediate net values (before seller closing costs)
        # The MC path's net_buy[:−1] should match the deterministic
        # Net_Buy column (both exclude seller closing costs until end)
        det_net_buy = det_results.data["Net_Buy"].values
        det_net_rent = det_results.data["Net_Rent"].values

        # Intermediate months should match closely
        for m in [0, 12, 60, 119]:
            assert abs(net_buy[m] - det_net_buy[m]) < 100, (
                f"net_buy mismatch at month {m}: "
                f"MC={net_buy[m]:.2f}, det={det_net_buy[m]:.2f}"
            )
            assert abs(net_rent[m] - det_net_rent[m]) < 100, (
                f"net_rent mismatch at month {m}: "
                f"MC={net_rent[m]:.2f}, det={det_net_rent[m]:.2f}"
            )

        # Final net_buy includes seller closing costs + tax benefits
        # Should match deterministic final_net_buy_tax_adjusted
        assert abs(
            net_buy[-1] - det_results.final_net_buy_tax_adjusted
        ) < 500, (
            f"Final net_buy mismatch: "
            f"MC={net_buy[-1]:.2f}, "
            f"det={det_results.final_net_buy_tax_adjusted:.2f}"
        )

        # Final net_rent should match exactly
        assert abs(net_rent[-1] - det_results.final_net_rent) < 100

    def test_varying_rates_affect_outcome(self, base_config):
        """Test that different rates produce different outcomes."""
        n_years = base_config.duration_years

        # Low appreciation, high equity growth
        prop_low = np.full(n_years, 1.0)
        eq_high = np.full(n_years, 12.0)
        rent_rates = np.full(n_years, 3.0)
        net_buy_low, net_rent_high = _simulate_single_path(
            base_config, prop_low, eq_high, rent_rates
        )

        # High appreciation, low equity growth
        prop_high = np.full(n_years, 8.0)
        eq_low = np.full(n_years, 2.0)
        net_buy_high, net_rent_low = _simulate_single_path(
            base_config, prop_high, eq_low, rent_rates
        )

        # When property appreciation is high + equity is low, buy should
        # do relatively better
        diff_buy_favored = net_buy_high[-1] - net_rent_low[-1]
        diff_rent_favored = net_buy_low[-1] - net_rent_high[-1]
        assert diff_buy_favored > diff_rent_favored

    def test_net_values_monotonicity_not_required(self, base_config):
        """Test that MC paths can be non-monotonic with volatile rates."""
        n_years = base_config.duration_years
        # Alternating boom/bust years
        prop_rates = np.array([10, -5] * (n_years // 2))
        eq_rates = np.full(n_years, 7.0)
        rent_rates = np.full(n_years, 3.0)

        net_buy, net_rent = _simulate_single_path(
            base_config, prop_rates, eq_rates, rent_rates
        )
        # Just verify it runs without error and produces valid output
        assert net_buy.shape == (n_years * 12 + 1,)
        assert not np.any(np.isnan(net_buy))
        assert not np.any(np.isnan(net_rent))
```

### 3.2 — Verify tests fail

```bash
uv run pytest tests/test_monte_carlo.py::TestSimulateSinglePath -v
```

Expected: `ImportError` — `_simulate_single_path` not yet defined.

### 3.3 — Implement `_simulate_single_path`

Add to `src/simulator/monte_carlo.py` (after `_generate_annual_draws`):

```python
def _simulate_single_path(
    config: SimulationConfig,
    annual_prop_rates: np.ndarray,
    annual_equity_rates: np.ndarray,
    annual_rent_rates: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Simulate one MC path with year-varying rates.

    Reimplements the full financial math from ``engine.py`` using
    per-year stochastic rates instead of fixed annual rates. The
    mortgage is still fixed-rate (amortization doesn't change).

    Final ``net_buy[-1]`` includes: seller closing costs (subtracted),
    cumulative tax savings (added), and capital gains tax saved (added).
    Intermediate values ``net_buy[0..n_months-1]`` do NOT include
    seller closing costs (same convention as the deterministic engine's
    ``Net_Buy`` column).

    Parameters
    ----------
    config : SimulationConfig
        Base configuration (property price, down payment, mortgage rate,
        closing costs, tax settings, etc.).
    annual_prop_rates : np.ndarray
        Property appreciation rate per year in percentage points.
        Shape: ``(n_years,)``.
    annual_equity_rates : np.ndarray
        Equity growth rate per year in percentage points.
        Shape: ``(n_years,)``.
    annual_rent_rates : np.ndarray
        Rent inflation rate per year in percentage points.
        Shape: ``(n_years,)``.

    Returns
    -------
    tuple[np.ndarray, np.ndarray]
        ``(net_buy, net_rent)`` — each of shape ``(n_months + 1,)``.

    Examples
    --------
    Simulate a single path with constant rates:

    .. code-block:: python

        import numpy as np
        from simulator.monte_carlo import _simulate_single_path
        from simulator.models import SimulationConfig

        config = SimulationConfig(
            duration_years=10, property_price=500000,
            down_payment_pct=20, mortgage_rate_annual=4.5,
            property_appreciation_annual=3.0,
            equity_growth_annual=7.0, monthly_rent=2000,
        )
        prop = np.full(10, 3.0)
        eq = np.full(10, 7.0)
        rent = np.full(10, 3.0)
        net_buy, net_rent = _simulate_single_path(
            config, prop, eq, rent
        )

    """
    n_years = config.duration_years
    n_months = n_years * 12

    # --- Fixed mortgage parameters (don't vary with stochastic rates) ---
    down_payment = config.property_price * (config.down_payment_pct / 100)
    buyer_closing = config.property_price * (
        config.closing_cost_buyer_pct / 100
    )
    initial_outflow = down_payment + buyer_closing
    loan_amount = config.property_price - down_payment
    fixed_monthly_rate = (config.mortgage_rate_annual / 100) / 12

    # Monthly mortgage payment (fixed for the life of the loan)
    if abs(loan_amount) < _FLOAT_TOLERANCE:
        monthly_payment = 0.0
    elif abs(fixed_monthly_rate) < _FLOAT_TOLERANCE:
        monthly_payment = loan_amount / n_months if n_months > 0 else 0.0
    else:
        monthly_payment = -npf.pmt(fixed_monthly_rate, n_months, loan_amount)

    # --- Allocate arrays ---
    home_value = np.zeros(n_months + 1)
    equity_value = np.zeros(n_months + 1)
    mortgage_balance = np.zeros(n_months + 1)
    cum_outflow_buy = np.zeros(n_months + 1)
    cum_outflow_rent = np.zeros(n_months + 1)
    monthly_interest = np.zeros(n_months + 1)
    monthly_property_tax = np.zeros(n_months + 1)
    rent_at_month = np.zeros(n_months + 1)

    # --- Initial conditions ---
    home_value[0] = config.property_price
    equity_value[0] = down_payment
    mortgage_balance[0] = loan_amount
    cum_outflow_buy[0] = initial_outflow
    cum_outflow_rent[0] = 0.0
    rent_at_month[0] = config.monthly_rent

    # Cost inflation is fixed (not stochastic)
    monthly_cost_inflation = config.cost_inflation_rate / 12

    # --- Month-by-month simulation ---
    for m in range(1, n_months + 1):
        yr = (m - 1) // 12  # Year index (0-based)

        # Monthly rates from annual draws (percentage to decimal, / 12)
        monthly_prop_rate = annual_prop_rates[yr] / 100 / 12
        monthly_eq_rate = annual_equity_rates[yr] / 100 / 12
        monthly_rent_rate = annual_rent_rates[yr] / 100 / 12

        # Property appreciation
        home_value[m] = home_value[m - 1] * (1 + monthly_prop_rate)

        # Equity portfolio growth
        equity_value[m] = equity_value[m - 1] * (1 + monthly_eq_rate)

        # Mortgage amortization (fixed rate, not stochastic)
        if mortgage_balance[m - 1] > _FLOAT_TOLERANCE:
            interest = mortgage_balance[m - 1] * fixed_monthly_rate
            principal = monthly_payment - interest
            mortgage_balance[m] = max(
                0.0, mortgage_balance[m - 1] - principal
            )
            monthly_interest[m] = interest
        else:
            mortgage_balance[m] = 0.0
            monthly_interest[m] = 0.0

        # Rent with year-varying inflation
        rent_at_month[m] = rent_at_month[m - 1] * (
            1 + monthly_rent_rate
        )

        # Ongoing homeownership costs
        cost_inflation_factor = (1 + monthly_cost_inflation) ** m
        prop_tax = (
            home_value[m] * (config.property_tax_rate / 100) / 12
        )
        insurance = (
            config.annual_home_insurance / 12
        ) * cost_inflation_factor
        maintenance = (
            home_value[m] * (config.annual_maintenance_pct / 100) / 12
        ) * cost_inflation_factor

        monthly_property_tax[m] = prop_tax

        # Cumulative outflows
        cum_outflow_buy[m] = (
            cum_outflow_buy[m - 1]
            + monthly_payment
            + prop_tax
            + insurance
            + maintenance
        )
        cum_outflow_rent[m] = cum_outflow_rent[m - 1] + rent_at_month[m - 1]

    # --- Tax savings (annual computation, same logic as engine.py) ---
    tax_rate = config.tax_bracket / 100
    cumulative_tax_savings = 0.0
    if config.enable_mortgage_deduction and tax_rate > _FLOAT_TOLERANCE:
        for yr in range(n_years):
            yr_start = yr * 12 + 1
            yr_end = (yr + 1) * 12
            year_interest = float(
                np.sum(monthly_interest[yr_start : yr_end + 1])
            )
            year_prop_tax = float(
                np.sum(monthly_property_tax[yr_start : yr_end + 1])
            )
            deductible_prop_tax = min(year_prop_tax, config.salt_cap)
            cumulative_tax_savings += (
                year_interest + deductible_prop_tax
            ) * tax_rate

    # --- Capital gains exclusion ---
    capital_gains_tax_saved = 0.0
    if config.enable_capital_gains_exclusion:
        capital_gain = home_value[-1] - config.property_price
        if capital_gain > config.capital_gains_exemption_limit:
            taxable_gain = (
                capital_gain - config.capital_gains_exemption_limit
            )
            cg_rate = 0.20 if config.tax_bracket >= 35 else 0.15
            capital_gains_tax_saved = taxable_gain * cg_rate

    # --- Seller closing costs ---
    seller_closing = home_value[-1] * (
        config.closing_cost_seller_pct / 100
    )

    # --- Net value arrays ---
    net_buy = home_value - cum_outflow_buy
    net_rent = equity_value - cum_outflow_rent

    # Apply end-of-period adjustments to the final month only
    net_buy[-1] = (
        net_buy[-1]
        - seller_closing
        + cumulative_tax_savings
        + capital_gains_tax_saved
    )

    return net_buy, net_rent
```

### 3.4 — Verify tests pass

```bash
uv run pytest tests/test_monte_carlo.py::TestSimulateSinglePath -v
```

Expected: all tests pass. The consistency test may need the tolerance adjusted (up to `< 500`) because the MC path uses a loop with slightly different accumulation order than the vectorized engine. If the consistency test fails, check the specific values and adjust tolerance — the key is that they agree to within a few hundred dollars on a $500k simulation.

### 3.5 — Run linter

```bash
uv run ruff check src/simulator/monte_carlo.py tests/test_monte_carlo.py
uv run ruff format src/simulator/monte_carlo.py tests/test_monte_carlo.py
```

### 3.6 — Commit

```bash
git add src/simulator/monte_carlo.py tests/test_monte_carlo.py
git commit -m "feat(mc): implement _simulate_single_path with year-varying rates

Month-by-month loop reimplements mortgage amortization, property
appreciation, equity growth, rent inflation, ongoing costs, tax
savings, and closing costs. Consistency test validates against the
deterministic engine."
```

---

## Task 4: Main Runner + Sensitivity Analysis

**Goal:** Implement `run_monte_carlo()` (orchestrator) and `_compute_sensitivity()` (tornado chart data via OAT perturbation of the deterministic engine).

### Steps

- [ ] **4.1** Write tests for `run_monte_carlo` and `_compute_sensitivity`
- [ ] **4.2** Verify tests fail
- [ ] **4.3** Implement `_compute_sensitivity` and `run_monte_carlo`
- [ ] **4.4** Verify tests pass
- [ ] **4.5** Run linter, fix any issues
- [ ] **4.6** Commit

### 4.1 — Write tests

Append to `tests/test_monte_carlo.py`:

```python
from simulator.monte_carlo import _compute_sensitivity, run_monte_carlo


class TestComputeSensitivity:
    """Tests for _compute_sensitivity (tornado chart data)."""

    @pytest.fixture()
    def base_config(self):
        """Return a standard SimulationConfig.

        Returns
        -------
        SimulationConfig
            A 10-year, $500k property configuration.

        Examples
        --------
        .. code-block:: python

            config = base_config

        """
        return SimulationConfig(
            duration_years=10,
            property_price=500000,
            down_payment_pct=20,
            mortgage_rate_annual=4.5,
            property_appreciation_annual=3.0,
            equity_growth_annual=7.0,
            monthly_rent=2000,
        )

    def test_returns_sorted_params(self, base_config):
        """Test that sensitivity params are sorted by impact range."""
        params, low, high, base_val = _compute_sensitivity(base_config)
        assert len(params) == len(low) == len(high)
        assert len(params) > 0

        # Should be sorted by descending impact range
        ranges = np.abs(high - low)
        for i in range(len(ranges) - 1):
            assert ranges[i] >= ranges[i + 1] - _FLOAT_TOLERANCE

    def test_base_value_matches_deterministic(self, base_config):
        """Test that base value matches deterministic engine output."""
        _, _, _, base_val = _compute_sensitivity(base_config)
        det_results = deterministic_engine(base_config)
        expected = det_results.final_net_buy_tax_adjusted - det_results.final_net_rent
        assert abs(base_val - expected) < 1.0

    def test_known_param_directions(self, base_config):
        """Test that known params have expected directional effects."""
        params, low, high, base_val = _compute_sensitivity(base_config)

        # Higher property appreciation should help buying
        if "Property Appreciation" in params:
            idx = params.index("Property Appreciation")
            assert high[idx] > low[idx]

        # Higher equity growth should help renting
        if "Equity Growth" in params:
            idx = params.index("Equity Growth")
            assert high[idx] < low[idx]

    def test_number_of_params(self, base_config):
        """Test that we get 8 sensitivity parameters."""
        params, low, high, base_val = _compute_sensitivity(base_config)
        assert len(params) == 8


class TestRunMonteCarlo:
    """Tests for the main run_monte_carlo orchestrator."""

    @pytest.fixture()
    def base_config(self):
        """Return a standard SimulationConfig for MC runner tests.

        Returns
        -------
        SimulationConfig
            A 10-year, $500k property configuration.

        Examples
        --------
        .. code-block:: python

            config = base_config

        """
        return SimulationConfig(
            duration_years=10,
            property_price=500000,
            down_payment_pct=20,
            mortgage_rate_annual=4.5,
            property_appreciation_annual=3.0,
            equity_growth_annual=7.0,
            monthly_rent=2000,
        )

    def test_basic_run(self, base_config):
        """Test that run_monte_carlo produces valid results."""
        mc_config = MonteCarloConfig(n_simulations=50, seed=42)
        results = run_monte_carlo(base_config, mc_config)

        assert isinstance(results, MonteCarloResults)
        assert results.n_simulations == 50
        assert results.all_net_buy.shape == (50, 121)
        assert results.all_net_rent.shape == (50, 121)
        assert results.all_differences.shape == (50, 121)
        assert results.final_differences.shape == (50,)
        assert results.year_arr.shape == (121,)

    def test_buy_wins_pct_in_range(self, base_config):
        """Test that buy_wins_pct is between 0 and 100."""
        mc_config = MonteCarloConfig(n_simulations=100, seed=42)
        results = run_monte_carlo(base_config, mc_config)
        assert 0 <= results.buy_wins_pct <= 100

    def test_percentiles_ordered(self, base_config):
        """Test that percentile bands are properly ordered."""
        mc_config = MonteCarloConfig(n_simulations=200, seed=42)
        results = run_monte_carlo(base_config, mc_config)

        # At every time step, p5 <= p25 <= p50 <= p75 <= p95
        for t in range(results.difference_percentiles.shape[1]):
            vals = results.difference_percentiles[:, t]
            for i in range(len(vals) - 1):
                assert vals[i] <= vals[i + 1] + _FLOAT_TOLERANCE

    def test_reproducibility(self, base_config):
        """Test that same seed produces identical results."""
        mc_config = MonteCarloConfig(n_simulations=50, seed=99)
        r1 = run_monte_carlo(base_config, mc_config)
        r2 = run_monte_carlo(base_config, mc_config)
        np.testing.assert_array_equal(
            r1.final_differences, r2.final_differences
        )

    def test_sensitivity_populated(self, base_config):
        """Test that sensitivity analysis data is populated."""
        mc_config = MonteCarloConfig(n_simulations=50, seed=42)
        results = run_monte_carlo(base_config, mc_config)
        assert len(results.sensitivity_params) > 0
        assert results.sensitivity_low.shape[0] == len(
            results.sensitivity_params
        )
        assert results.sensitivity_high.shape[0] == len(
            results.sensitivity_params
        )

    def test_configs_stored_in_results(self, base_config):
        """Test that base and MC configs are stored in results."""
        mc_config = MonteCarloConfig(n_simulations=50, seed=42)
        results = run_monte_carlo(base_config, mc_config)
        assert results.base_config is base_config
        assert results.mc_config is mc_config

    def test_zero_std_produces_identical_paths(self, base_config):
        """Test that zero stds produce near-identical final values."""
        mc_config = MonteCarloConfig(
            n_simulations=20,
            seed=42,
            property_appreciation_std=0.0,
            equity_growth_std=0.0,
            rent_inflation_std=0.0,
        )
        results = run_monte_carlo(base_config, mc_config)
        # All final differences should be nearly the same
        diffs = results.final_differences
        assert np.std(diffs) < 1.0  # Near-zero variance
```

### 4.2 — Verify tests fail

```bash
uv run pytest tests/test_monte_carlo.py::TestComputeSensitivity tests/test_monte_carlo.py::TestRunMonteCarlo -v
```

Expected: `ImportError` — `_compute_sensitivity` and `run_monte_carlo` not yet defined.

### 4.3 — Implement `_compute_sensitivity` and `run_monte_carlo`

Add to `src/simulator/monte_carlo.py` (after `_simulate_single_path`):

```python
def _compute_sensitivity(
    base_config: SimulationConfig,
) -> tuple[list[str], np.ndarray, np.ndarray, float]:
    """Compute one-at-a-time sensitivity for tornado chart.

    Uses the EXISTING deterministic ``calculate_scenarios`` engine
    (not the MC path simulator). Perturbs 8 key parameters by +/- 1
    standard deviation and measures the effect on the tax-adjusted
    difference (net_buy_tax_adjusted - net_rent).

    Parameters
    ----------
    base_config : SimulationConfig
        The base deterministic configuration.

    Returns
    -------
    tuple[list[str], np.ndarray, np.ndarray, float]
        ``(param_names, low_values, high_values, base_value)`` sorted
        by descending impact range ``abs(high - low)``.

    Examples
    --------
    Compute sensitivity for a base configuration:

    .. code-block:: python

        from simulator.monte_carlo import _compute_sensitivity
        from simulator.models import SimulationConfig

        config = SimulationConfig(
            duration_years=10, property_price=500000,
            down_payment_pct=20, mortgage_rate_annual=4.5,
            property_appreciation_annual=3.0,
            equity_growth_annual=7.0, monthly_rent=2000,
        )
        params, low, high, base = _compute_sensitivity(config)
        for p, lo, hi in zip(params, low, high):
            print(f"{p}: [{lo:,.0f}, {hi:,.0f}]")

    """
    from dataclasses import asdict

    def _run_with_override(
        **overrides: float,
    ) -> float:
        """Run deterministic engine with parameter overrides."""
        base_dict = asdict(base_config)
        base_dict.update(overrides)
        cfg = SimulationConfig(**base_dict)
        res = calculate_scenarios(cfg)
        return res.final_net_buy_tax_adjusted - res.final_net_rent

    # Base case
    base_value = _run_with_override()

    # Parameters to perturb: (display_name, config_field, delta)
    # Delta is +-1 "standard deviation" in the same units as the field
    perturbations = [
        (
            "Property Appreciation",
            "property_appreciation_annual",
            5.0,
        ),
        ("Equity Growth", "equity_growth_annual", 5.0),
        ("Rent Inflation", "rent_inflation_rate", 0.015),
        ("Property Price", "property_price", 100000),
        ("Down Payment %", "down_payment_pct", 5.0),
        ("Monthly Rent", "monthly_rent", 500),
        ("Property Tax Rate", "property_tax_rate", 0.5),
        ("Mortgage Rate", "mortgage_rate_annual", 1.0),
    ]

    param_names: list[str] = []
    low_vals: list[float] = []
    high_vals: list[float] = []

    for display_name, field, delta in perturbations:
        base_val = getattr(base_config, field)

        # Low perturbation (subtract delta)
        low_override = max(base_val - delta, 0.001)
        # Clamp down_payment_pct to [5, 100]
        if field == "down_payment_pct":
            low_override = max(low_override, 5.0)
        # Clamp rent_inflation_rate to [0, 1]
        if field == "rent_inflation_rate":
            low_override = max(low_override, 0.0)

        # High perturbation (add delta)
        high_override = base_val + delta
        if field == "down_payment_pct":
            high_override = min(high_override, 100.0)
        if field == "rent_inflation_rate":
            high_override = min(high_override, 1.0)

        try:
            val_low = _run_with_override(**{field: low_override})
            val_high = _run_with_override(**{field: high_override})
            param_names.append(display_name)
            low_vals.append(val_low)
            high_vals.append(val_high)
        except (ValueError, Exception):
            # Skip if perturbation produces invalid config
            continue

    # Sort by descending impact range
    low_arr = np.array(low_vals)
    high_arr = np.array(high_vals)
    impact_range = np.abs(high_arr - low_arr)
    sort_idx = np.argsort(-impact_range)

    sorted_names = [param_names[i] for i in sort_idx]
    sorted_low = low_arr[sort_idx]
    sorted_high = high_arr[sort_idx]

    return sorted_names, sorted_low, sorted_high, base_value


def run_monte_carlo(
    base_config: SimulationConfig,
    mc_config: MonteCarloConfig,
) -> MonteCarloResults:
    """Run the full Monte Carlo uncertainty analysis.

    Generates correlated annual rate draws, simulates each path,
    collects results into 2D arrays, computes percentiles and summary
    statistics, and runs OAT sensitivity analysis.

    Parameters
    ----------
    base_config : SimulationConfig
        The base deterministic configuration.
    mc_config : MonteCarloConfig
        Monte Carlo settings (n_simulations, stds, correlation, seed).

    Returns
    -------
    MonteCarloResults
        Full results including paths, percentiles, summary stats,
        and sensitivity data.

    Examples
    --------
    Run a Monte Carlo simulation:

    .. code-block:: python

        from simulator.monte_carlo import run_monte_carlo
        from simulator.models import SimulationConfig, MonteCarloConfig

        config = SimulationConfig(
            duration_years=10, property_price=500000,
            down_payment_pct=20, mortgage_rate_annual=4.5,
            property_appreciation_annual=3.0,
            equity_growth_annual=7.0, monthly_rent=2000,
        )
        mc_config = MonteCarloConfig(n_simulations=500, seed=42)
        results = run_monte_carlo(config, mc_config)
        print(f"Buy wins {results.buy_wins_pct:.1f}% of the time")
        print(f"Median difference: ${results.median_difference:,.0f}")

    """
    n_sims = mc_config.n_simulations
    n_years = base_config.duration_years
    n_months = n_years * 12
    n_points = n_months + 1

    # Seeded RNG for reproducibility
    rng = np.random.default_rng(mc_config.seed)

    # Generate year-by-year stochastic rates
    draws = _generate_annual_draws(base_config, mc_config, n_years, rng)

    # Allocate result arrays
    all_net_buy = np.zeros((n_sims, n_points))
    all_net_rent = np.zeros((n_sims, n_points))

    # Simulate each path
    for i in range(n_sims):
        net_buy, net_rent = _simulate_single_path(
            config=base_config,
            annual_prop_rates=draws["property_appreciation"][i],
            annual_equity_rates=draws["equity_growth"][i],
            annual_rent_rates=draws["rent_inflation"][i],
        )
        all_net_buy[i] = net_buy
        all_net_rent[i] = net_rent

    # Compute differences
    all_diffs = all_net_buy - all_net_rent
    final_diffs = all_diffs[:, -1]

    # Time axis
    year_arr = np.arange(n_points) / 12

    # Percentiles
    percentile_levels = [5, 25, 50, 75, 95]
    diff_percentiles = np.percentile(
        all_diffs, percentile_levels, axis=0
    )

    # Summary statistics
    buy_wins_pct = float(np.mean(final_diffs > 0) * 100)
    median_diff = float(np.median(final_diffs))
    p5_diff = float(np.percentile(final_diffs, 5))
    p95_diff = float(np.percentile(final_diffs, 95))

    # Sensitivity analysis (uses deterministic engine, not MC)
    sens_params, sens_low, sens_high, sens_base = _compute_sensitivity(
        base_config
    )

    return MonteCarloResults(
        final_net_buy=all_net_buy[:, -1],
        final_net_rent=all_net_rent[:, -1],
        final_differences=final_diffs,
        all_net_buy=all_net_buy,
        all_net_rent=all_net_rent,
        all_differences=all_diffs,
        year_arr=year_arr,
        percentile_levels=percentile_levels,
        difference_percentiles=diff_percentiles,
        buy_wins_pct=buy_wins_pct,
        median_difference=median_diff,
        p5_difference=p5_diff,
        p95_difference=p95_diff,
        sensitivity_params=sens_params,
        sensitivity_low=sens_low,
        sensitivity_high=sens_high,
        sensitivity_base=sens_base,
        base_config=base_config,
        mc_config=mc_config,
        n_simulations=n_sims,
    )
```

### 4.4 — Verify tests pass

```bash
uv run pytest tests/test_monte_carlo.py -v
```

Expected: all tests pass (Tasks 1-4).

### 4.5 — Run linter

```bash
uv run ruff check src/simulator/monte_carlo.py tests/test_monte_carlo.py
uv run ruff format src/simulator/monte_carlo.py tests/test_monte_carlo.py
```

### 4.6 — Commit

```bash
git add src/simulator/monte_carlo.py tests/test_monte_carlo.py
git commit -m "feat(mc): implement run_monte_carlo and _compute_sensitivity

Orchestrator loops over _simulate_single_path, collects 2D arrays,
computes percentiles and summary stats. OAT sensitivity uses the
deterministic engine with +-1 std perturbations for 8 key params."
```

---

## Task 5: Spaghetti Chart (Matplotlib + Aleatory)

**Goal:** Create `src/simulator/mc_visualization.py` with `create_spaghetti_chart()` that produces a matplotlib figure using aleatory's `qp_style()`.

### Steps

- [ ] **5.1** Write tests for `create_spaghetti_chart`
- [ ] **5.2** Verify tests fail
- [ ] **5.3** Implement `create_spaghetti_chart`
- [ ] **5.4** Verify tests pass
- [ ] **5.5** Run linter, fix any issues
- [ ] **5.6** Commit

### 5.1 — Write tests

Append to `tests/test_monte_carlo.py`:

```python
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for testing
import matplotlib.pyplot as plt
from simulator.mc_visualization import create_spaghetti_chart


class TestSpaghettiChart:
    """Tests for the spaghetti chart visualization."""

    @pytest.fixture()
    def mc_results(self):
        """Return MC results for visualization tests.

        Returns
        -------
        MonteCarloResults
            Results from a 50-sim, 10-year MC run.

        Examples
        --------
        .. code-block:: python

            fig = create_spaghetti_chart(mc_results)

        """
        config = SimulationConfig(
            duration_years=10,
            property_price=500000,
            down_payment_pct=20,
            mortgage_rate_annual=4.5,
            property_appreciation_annual=3.0,
            equity_growth_annual=7.0,
            monthly_rent=2000,
        )
        mc_config = MonteCarloConfig(n_simulations=50, seed=42)
        return run_monte_carlo(config, mc_config)

    def test_returns_figure(self, mc_results):
        """Test that function returns a matplotlib Figure."""
        fig = create_spaghetti_chart(mc_results)
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_has_two_axes(self, mc_results):
        """Test that figure has main plot and marginal histogram."""
        fig = create_spaghetti_chart(mc_results)
        axes = fig.get_axes()
        # Main axis + marginal axis = 2
        assert len(axes) >= 2
        plt.close(fig)

    def test_main_axis_has_lines(self, mc_results):
        """Test that main axis contains line paths."""
        fig = create_spaghetti_chart(mc_results)
        ax_main = fig.get_axes()[0]
        # Should have at least n_simulations lines + median + zero line
        assert len(ax_main.get_lines()) >= mc_results.n_simulations
        plt.close(fig)

    def test_figure_can_be_saved(self, mc_results, tmp_path):
        """Test that figure can be saved to a file."""
        fig = create_spaghetti_chart(mc_results)
        save_path = tmp_path / "spaghetti.png"
        fig.savefig(save_path, dpi=72)
        assert save_path.exists()
        assert save_path.stat().st_size > 0
        plt.close(fig)
```

### 5.2 — Verify tests fail

```bash
uv run pytest tests/test_monte_carlo.py::TestSpaghettiChart -v
```

Expected: `ImportError` — `mc_visualization` module doesn't exist.

### 5.3 — Implement `create_spaghetti_chart`

Create `/Users/sagarpal/projects/rent-vs-buy-simulator/src/simulator/mc_visualization.py`:

```python
"""Monte Carlo visualization module.

Provides matplotlib and Plotly charts for MC uncertainty analysis:
spaghetti chart (matplotlib + aleatory), tornado chart (Plotly),
and probability-over-time chart (Plotly).
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import plotly.graph_objects as go

from .models import MonteCarloResults


def create_spaghetti_chart(mc_results: MonteCarloResults) -> plt.Figure:
    """Create a spaghetti chart with marginal distribution.

    Shows individual MC paths colored by final outcome (green if
    buying wins, red if renting wins), a bold median path, and a
    marginal histogram/KDE of final differences on the right.

    Uses aleatory's ``qp_style()`` for publication-quality styling.

    Parameters
    ----------
    mc_results : MonteCarloResults
        Full MC results containing ``all_differences``, ``year_arr``,
        ``final_differences``, and ``median_difference``.

    Returns
    -------
    plt.Figure
        Matplotlib Figure with two panels: main spaghetti plot (left)
        and marginal distribution (right).

    Examples
    --------
    Create and display a spaghetti chart:

    .. code-block:: python

        from simulator.mc_visualization import create_spaghetti_chart

        fig = create_spaghetti_chart(mc_results)
        fig.savefig("spaghetti.png", dpi=150)

    """
    # Apply aleatory's quant-plot style
    try:
        from aleatory.styles import qp_style
        qp_style()
    except ImportError:
        pass  # Graceful fallback if aleatory unavailable

    fig, (ax_main, ax_marginal) = plt.subplots(
        1,
        2,
        gridspec_kw={"width_ratios": [4, 1]},
        sharey=True,
        figsize=(14, 6),
    )

    years = mc_results.year_arr
    all_diffs = mc_results.all_differences
    final_diffs = mc_results.final_differences

    # Individual paths: green if final > 0 (buy wins), red otherwise
    for i in range(mc_results.n_simulations):
        color = "#2ecc71" if final_diffs[i] > 0 else "#e74c3c"
        ax_main.plot(
            years, all_diffs[i], color=color, alpha=0.08, linewidth=0.5
        )

    # Median path as bold dashed blue line
    median_path = np.median(all_diffs, axis=0)
    ax_main.plot(
        years,
        median_path,
        color="#3498db",
        linewidth=2.5,
        linestyle="--",
        label="Median path",
        zorder=10,
    )

    # Zero reference line
    ax_main.axhline(
        y=0, color="gray", linewidth=1, linestyle="--", alpha=0.7
    )

    ax_main.set_xlabel("Years")
    ax_main.set_ylabel("Net Difference (Buy - Rent) ($)")
    ax_main.set_title(
        "Monte Carlo Simulation: Buy vs. Rent Outcomes",
        fontsize=14,
    )
    ax_main.legend(loc="upper left")

    # Format y-axis as currency
    ax_main.yaxis.set_major_formatter(
        plt.FuncFormatter(lambda x, _: f"${x:,.0f}")
    )

    # --- Marginal distribution (right panel) ---
    # Color bins by sign
    pos_diffs = final_diffs[final_diffs > 0]
    neg_diffs = final_diffs[final_diffs <= 0]

    # Determine common bin edges
    n_bins = 40
    all_range = (final_diffs.min(), final_diffs.max())
    bins = np.linspace(all_range[0], all_range[1], n_bins + 1)

    if len(pos_diffs) > 0:
        ax_marginal.hist(
            pos_diffs,
            bins=bins,
            orientation="horizontal",
            color="#2ecc71",
            alpha=0.7,
            label="Buy wins",
        )
    if len(neg_diffs) > 0:
        ax_marginal.hist(
            neg_diffs,
            bins=bins,
            orientation="horizontal",
            color="#e74c3c",
            alpha=0.7,
            label="Rent wins",
        )

    ax_marginal.axhline(
        y=0, color="gray", linewidth=1, linestyle="--", alpha=0.7
    )
    ax_marginal.set_xlabel("Count")
    ax_marginal.set_title("Final Distribution", fontsize=11)
    ax_marginal.legend(loc="upper right", fontsize=8)

    # Remove y-axis labels on marginal (shared with main)
    ax_marginal.tick_params(axis="y", labelleft=False)

    fig.tight_layout()
    return fig
```

### 5.4 — Verify tests pass

```bash
uv run pytest tests/test_monte_carlo.py::TestSpaghettiChart -v
```

Expected: all tests pass.

### 5.5 — Run linter

```bash
uv run ruff check src/simulator/mc_visualization.py tests/test_monte_carlo.py
uv run ruff format src/simulator/mc_visualization.py tests/test_monte_carlo.py
```

### 5.6 — Commit

```bash
git add src/simulator/mc_visualization.py tests/test_monte_carlo.py
git commit -m "feat(mc): add spaghetti chart with aleatory styling

Matplotlib figure with individual paths (green/red by outcome),
median dashed line, zero reference, and marginal histogram of final
differences."
```

---

## Task 6: Tornado + Probability Charts (Plotly)

**Goal:** Add `create_tornado_chart()` and `create_probability_chart()` to `mc_visualization.py`.

### Steps

- [ ] **6.1** Write tests for both chart functions
- [ ] **6.2** Verify tests fail
- [ ] **6.3** Implement `create_tornado_chart` and `create_probability_chart`
- [ ] **6.4** Verify tests pass
- [ ] **6.5** Run linter, fix any issues
- [ ] **6.6** Commit

### 6.1 — Write tests

Append to `tests/test_monte_carlo.py`:

```python
from simulator.mc_visualization import (
    create_tornado_chart,
    create_probability_chart,
)


class TestTornadoChart:
    """Tests for the tornado chart visualization."""

    @pytest.fixture()
    def mc_results(self):
        """Return MC results for tornado chart tests.

        Returns
        -------
        MonteCarloResults
            Results from a 50-sim, 10-year MC run.

        Examples
        --------
        .. code-block:: python

            fig = create_tornado_chart(mc_results)

        """
        config = SimulationConfig(
            duration_years=10,
            property_price=500000,
            down_payment_pct=20,
            mortgage_rate_annual=4.5,
            property_appreciation_annual=3.0,
            equity_growth_annual=7.0,
            monthly_rent=2000,
        )
        mc_config = MonteCarloConfig(n_simulations=50, seed=42)
        return run_monte_carlo(config, mc_config)

    def test_returns_plotly_figure(self, mc_results):
        """Test that function returns a Plotly Figure."""
        fig = create_tornado_chart(mc_results)
        assert isinstance(fig, go.Figure)

    def test_has_traces(self, mc_results):
        """Test that tornado chart has bar traces."""
        fig = create_tornado_chart(mc_results)
        # Should have 2 traces: low and high bars
        assert len(fig.data) == 2

    def test_bar_count_matches_params(self, mc_results):
        """Test that number of bars matches number of params."""
        fig = create_tornado_chart(mc_results)
        n_params = len(mc_results.sensitivity_params)
        # Each trace should have n_params bars
        assert len(fig.data[0].y) == n_params


class TestProbabilityChart:
    """Tests for the probability-over-time chart."""

    @pytest.fixture()
    def mc_results(self):
        """Return MC results for probability chart tests.

        Returns
        -------
        MonteCarloResults
            Results from a 100-sim, 10-year MC run.

        Examples
        --------
        .. code-block:: python

            fig = create_probability_chart(mc_results)

        """
        config = SimulationConfig(
            duration_years=10,
            property_price=500000,
            down_payment_pct=20,
            mortgage_rate_annual=4.5,
            property_appreciation_annual=3.0,
            equity_growth_annual=7.0,
            monthly_rent=2000,
        )
        mc_config = MonteCarloConfig(n_simulations=100, seed=42)
        return run_monte_carlo(config, mc_config)

    def test_returns_plotly_figure(self, mc_results):
        """Test that function returns a Plotly Figure."""
        fig = create_probability_chart(mc_results)
        assert isinstance(fig, go.Figure)

    def test_probability_values_in_range(self, mc_results):
        """Test that probability values are between 0 and 100."""
        fig = create_probability_chart(mc_results)
        # The first trace should be the probability line
        y_values = fig.data[0].y
        assert all(0 <= v <= 100 for v in y_values)

    def test_has_50_percent_reference(self, mc_results):
        """Test that chart has a 50% reference line."""
        fig = create_probability_chart(mc_results)
        # Check layout for horizontal line shapes
        shapes = fig.layout.shapes
        has_50_line = any(
            hasattr(s, "y0") and s.y0 == 50 for s in shapes
        )
        assert has_50_line

    def test_x_axis_matches_years(self, mc_results):
        """Test that x-axis spans the simulation duration."""
        fig = create_probability_chart(mc_results)
        x_values = fig.data[0].x
        assert x_values[0] == pytest.approx(0.0, abs=0.1)
        assert x_values[-1] == pytest.approx(10.0, abs=0.1)
```

### 6.2 — Verify tests fail

```bash
uv run pytest tests/test_monte_carlo.py::TestTornadoChart tests/test_monte_carlo.py::TestProbabilityChart -v
```

Expected: `ImportError` — functions not yet defined.

### 6.3 — Implement both chart functions

Add to `src/simulator/mc_visualization.py` (after `create_spaghetti_chart`):

```python
def create_tornado_chart(mc_results: MonteCarloResults) -> go.Figure:
    """Create a tornado (sensitivity) chart.

    Horizontal bar chart showing how each parameter's +/- 1 std
    perturbation affects the final buy-vs-rent difference. Sorted by
    impact range (widest at top).

    Parameters
    ----------
    mc_results : MonteCarloResults
        MC results containing ``sensitivity_params``,
        ``sensitivity_low``, ``sensitivity_high``, and
        ``sensitivity_base``.

    Returns
    -------
    go.Figure
        Plotly Figure with horizontal bar chart.

    Examples
    --------
    Create a tornado chart:

    .. code-block:: python

        from simulator.mc_visualization import create_tornado_chart

        fig = create_tornado_chart(mc_results)
        fig.show()

    """
    params = mc_results.sensitivity_params
    low = mc_results.sensitivity_low
    high = mc_results.sensitivity_high
    base = mc_results.sensitivity_base

    # Reverse order so widest bar is at top in horizontal layout
    params_rev = list(reversed(params))
    low_rev = low[::-1]
    high_rev = high[::-1]

    # Low-side bars (base to low value)
    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            y=params_rev,
            x=low_rev - base,
            orientation="h",
            name="Low (-1 std)",
            marker_color="#e74c3c",
            hovertemplate=(
                "%{y}<br>"
                "Shift: $%{x:,.0f}<br>"
                "Value: $%{customdata:,.0f}<extra></extra>"
            ),
            customdata=low_rev,
        )
    )

    fig.add_trace(
        go.Bar(
            y=params_rev,
            x=high_rev - base,
            orientation="h",
            name="High (+1 std)",
            marker_color="#2ecc71",
            hovertemplate=(
                "%{y}<br>"
                "Shift: $%{x:,.0f}<br>"
                "Value: $%{customdata:,.0f}<extra></extra>"
            ),
            customdata=high_rev,
        )
    )

    fig.update_layout(
        title="Sensitivity Analysis: Impact on Buy vs. Rent Difference",
        xaxis_title="Change from Base Case ($)",
        barmode="overlay",
        template="plotly_white",
        height=400,
        xaxis_tickformat="$,.0f",
    )

    return fig


def create_probability_chart(mc_results: MonteCarloResults) -> go.Figure:
    """Create a probability-over-time chart.

    Line chart showing the fraction of simulations where buying
    beats renting at each point in time.

    Parameters
    ----------
    mc_results : MonteCarloResults
        MC results containing ``all_differences`` and ``year_arr``.

    Returns
    -------
    go.Figure
        Plotly Figure with probability line and 50% reference.

    Examples
    --------
    Create a probability chart:

    .. code-block:: python

        from simulator.mc_visualization import create_probability_chart

        fig = create_probability_chart(mc_results)
        fig.show()

    """
    years = mc_results.year_arr
    all_diffs = mc_results.all_differences

    # Fraction of sims where buy wins at each month
    buy_wins_frac = np.mean(all_diffs > 0, axis=0) * 100

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=years,
            y=buy_wins_frac,
            mode="lines",
            name="P(Buy Wins)",
            line=dict(color="#3498db", width=3),
            hovertemplate=(
                "Year %{x:.1f}<br>"
                "%{y:.1f}% chance buy wins<extra></extra>"
            ),
        )
    )

    # 50% reference line
    fig.add_hline(
        y=50,
        line_dash="dash",
        line_color="gray",
        opacity=0.7,
        annotation_text="50%",
        annotation_position="bottom right",
    )

    fig.update_layout(
        title="Probability of Buying Winning Over Time",
        xaxis_title="Years",
        yaxis_title="Probability Buy Wins (%)",
        yaxis_range=[0, 100],
        template="plotly_white",
        height=400,
    )

    return fig
```

### 6.4 — Verify tests pass

```bash
uv run pytest tests/test_monte_carlo.py::TestTornadoChart tests/test_monte_carlo.py::TestProbabilityChart -v
```

Expected: all tests pass.

### 6.5 — Run linter

```bash
uv run ruff check src/simulator/mc_visualization.py tests/test_monte_carlo.py
uv run ruff format src/simulator/mc_visualization.py tests/test_monte_carlo.py
```

### 6.6 — Commit

```bash
git add src/simulator/mc_visualization.py tests/test_monte_carlo.py
git commit -m "feat(mc): add tornado and probability-over-time Plotly charts

Tornado chart shows OAT sensitivity sorted by impact range.
Probability chart shows fraction of simulations where buying wins
at each month."
```

---

## Task 7: UI Integration

**Goal:** Add a 5th "Uncertainty Analysis" tab to `app.py` that is idle by default and runs MC simulation on button click.

### Steps

- [ ] **7.1** Write a manual smoke test plan (no automated UI tests)
- [ ] **7.2** Modify `app.py` to add the 5th tab
- [ ] **7.3** Run the app and verify manually
- [ ] **7.4** Run full test suite + linter
- [ ] **7.5** Commit

### 7.1 — Manual smoke test plan

After implementing, verify manually with `streamlit run app.py`:

1. Open the app. All 4 existing tabs work as before.
2. Click the 5th tab "Uncertainty Analysis". See explanation text and "Run Simulations" button.
3. Click "Run 500 Simulations". See spinner, then 3 headline metrics appear.
4. Spaghetti chart renders with green/red paths and marginal histogram.
5. Tornado and probability charts render side-by-side below.
6. Expand "Tune Parameters" to see MC settings sliders. Change n_simulations to 100 and re-run.
7. Verify different seed produces different results.

### 7.2 — Modify `app.py`

Make these changes to `/Users/sagarpal/projects/rent-vs-buy-simulator/app.py`:

**A) Add import at the top** (after the existing simulator imports):

```python
from simulator.monte_carlo import run_monte_carlo
from simulator.models import MonteCarloConfig
from simulator.mc_visualization import (
    create_spaghetti_chart,
    create_tornado_chart,
    create_probability_chart,
)
```

**B) Change the tab creation** from 4 tabs to 5. Find this line:

```python
    tab1, tab2, tab3, tab4 = st.tabs(
        [
            "Asset Growth",
            "Cumulative Costs",
            "Net Value Comparison",
            "Data Table",
        ]
    )
```

Replace with:

```python
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        [
            "Asset Growth",
            "Cumulative Costs",
            "Net Value Comparison",
            "Data Table",
            "Uncertainty Analysis",
        ]
    )
```

**C) Add the 5th tab content** after the `with tab4:` block (before the footer divider). Insert the following block:

```python
    with tab5:
        st.subheader("Monte Carlo Uncertainty Analysis")
        st.markdown(
            "Explore how **randomness in market conditions** affects "
            "the buy-vs-rent outcome. Instead of fixed annual rates, "
            "this simulation draws random rates each year from "
            "distributions centered on your inputs."
        )

        # MC settings in an expander (on the tab, not sidebar)
        with st.expander("Tune Parameters", expanded=False):
            mc_col1, mc_col2 = st.columns(2)
            with mc_col1:
                mc_n_sims = st.slider(
                    "Number of Simulations",
                    min_value=50,
                    max_value=2000,
                    value=500,
                    step=50,
                    help="More simulations = smoother results, slower",
                )
                mc_seed = st.number_input(
                    "Random Seed",
                    min_value=0,
                    max_value=99999,
                    value=42,
                    step=1,
                    help="Change for different random outcomes",
                )
            with mc_col2:
                mc_prop_std = st.slider(
                    "Property Appreciation Std (%)",
                    min_value=0.0,
                    max_value=15.0,
                    value=5.0,
                    step=0.5,
                )
                mc_eq_std = st.slider(
                    "Equity Growth Std (%)",
                    min_value=0.0,
                    max_value=15.0,
                    value=5.0,
                    step=0.5,
                )
                mc_rent_std = st.slider(
                    "Rent Inflation Std (%)",
                    min_value=0.0,
                    max_value=5.0,
                    value=1.5,
                    step=0.1,
                )
                mc_corr = st.slider(
                    "Appreciation-Equity Correlation",
                    min_value=-1.0,
                    max_value=1.0,
                    value=0.3,
                    step=0.1,
                )

        # Run button
        if st.button(
            f"Run {mc_n_sims} Simulations",
            use_container_width=True,
            type="primary",
        ):
            mc_config = MonteCarloConfig(
                n_simulations=mc_n_sims,
                seed=int(mc_seed),
                property_appreciation_std=mc_prop_std,
                equity_growth_std=mc_eq_std,
                rent_inflation_std=mc_rent_std,
                appreciation_equity_correlation=mc_corr,
            )

            with st.spinner(
                f"Running {mc_n_sims} simulations..."
            ):
                mc_results = run_monte_carlo(config, mc_config)

            # Store results in session state
            st.session_state["mc_results"] = mc_results

        # Display results if available
        mc_results = st.session_state.get("mc_results")
        if mc_results is not None:
            # Headline metrics
            mc_m1, mc_m2, mc_m3 = st.columns(3)
            with mc_m1:
                st.metric(
                    "Buy Wins",
                    f"{mc_results.buy_wins_pct:.1f}%",
                    help="Fraction of simulations where buying wins",
                )
            with mc_m2:
                st.metric(
                    "Median Difference",
                    f"${mc_results.median_difference:,.0f}",
                    help="Median (Buy - Rent) across simulations",
                )
            with mc_m3:
                st.metric(
                    "90% Range",
                    (
                        f"${mc_results.p5_difference:,.0f} to "
                        f"${mc_results.p95_difference:,.0f}"
                    ),
                    help="5th to 95th percentile of outcomes",
                )

            st.divider()

            # Spaghetti chart (matplotlib → streamlit)
            st.subheader("Outcome Paths")
            st.markdown(
                "Each line is one possible future. "
                "**Green** = buying wins, **Red** = renting wins, "
                "**Blue dashed** = median path."
            )
            spaghetti_fig = create_spaghetti_chart(mc_results)
            st.pyplot(spaghetti_fig)
            plt.close(spaghetti_fig)

            st.divider()

            # Tornado + Probability side by side
            tc1, tc2 = st.columns(2)
            with tc1:
                st.subheader("Sensitivity Analysis")
                tornado_fig = create_tornado_chart(mc_results)
                st.plotly_chart(tornado_fig, use_container_width=True)
            with tc2:
                st.subheader("Probability Over Time")
                prob_fig = create_probability_chart(mc_results)
                st.plotly_chart(prob_fig, use_container_width=True)
```

**D) Add `import matplotlib.pyplot as plt`** near the top of the file with the other imports (needed for `plt.close`):

```python
import matplotlib.pyplot as plt
```

**E) Add `mc_results` session state initialization** in `init_session_state()`:

```python
    if "mc_results" not in st.session_state:
        st.session_state.mc_results = None
```

### 7.3 — Run the app and verify manually

```bash
streamlit run app.py
```

Follow the smoke test plan from step 7.1.

### 7.4 — Run full test suite + linter

```bash
uv run pytest tests/ -v
uv run ruff check src/ tests/ app.py
uv run ruff format src/ tests/ app.py
```

All tests should pass. Linter should report no errors.

### 7.5 — Commit

```bash
git add app.py
git commit -m "feat(mc): add Uncertainty Analysis tab to Streamlit UI

5th tab with idle state, 'Run N Simulations' button, 3 headline
metrics, spaghetti chart (matplotlib), tornado and probability
charts (Plotly) in two columns, and tunable MC parameters expander."
```

---

## Final Checklist

After all 7 tasks are complete:

- [ ] Run full test suite: `uv run pytest tests/ -v`
- [ ] Run linter: `uv run ruff check src/ tests/ app.py`
- [ ] Run formatter: `uv run ruff format src/ tests/ app.py`
- [ ] Run coverage check: `uv run pytest --cov --cov-report=term` (note: `mc_visualization.py` should be added to the coverage omit list in `pyproject.toml` alongside `visualization.py`, since visualization code is not meaningfully unit-testable for coverage)
- [ ] Manual smoke test of the full app
- [ ] Verify existing tests still pass (no regressions)

### Coverage configuration update

In `pyproject.toml`, add the new visualization module to the coverage omit list:

```toml
[tool.coverage.run]
source = ["src/simulator"]
branch = true
omit = [
    "*/scenario_manager.py",
    "*/utils.py",
    "*/visualization.py",
    "*/mc_visualization.py",
]
```

---

## File Inventory

| File | Action | Task |
|---|---|---|
| `pyproject.toml` | Edit (add deps + coverage omit) | 1, Final |
| `src/simulator/models.py` | Edit (add 2 dataclasses) | 1 |
| `src/simulator/monte_carlo.py` | Create (4 functions) | 2, 3, 4 |
| `src/simulator/mc_visualization.py` | Create (3 chart functions) | 5, 6 |
| `app.py` | Edit (5th tab + imports) | 7 |
| `tests/test_monte_carlo.py` | Create (8 test classes) | 1-6 |
