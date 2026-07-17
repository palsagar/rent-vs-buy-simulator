# Frontend Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Streamlit UI with a FastAPI + static JavaScript frontend matching the author's WebGPU apps (GitHub-dark aesthetic), implementing the redesign spec's narrative page.

**Architecture:** FastAPI server inside the Python package serves a hand-rolled `static/` frontend (ES modules, Plotly.js via CDN) and a JSON API wrapping the untouched NumPy engine. Spec: [docs/frontend-migration-design.md](frontend-migration-design.md).

**Tech Stack:** Python 3.12, FastAPI + uvicorn, existing engine (`engine.py`, `models.py`, `monte_carlo.py`), vanilla ES modules, Plotly.js 2.35.2 basic (CDN), pytest + FastAPI TestClient.

## Global Constraints

- **Engine untouched:** no task modifies `src/simulator/engine.py`, `src/simulator/models.py`, or `src/simulator/monte_carlo.py`.
- **Wire format:** camelCase keys; raw floats; units identical to `SimulationConfig` (`rentInflationRate`/`costInflationRate` are decimals, all `*Pct` fields are percents).
- **Python style:** type annotations on all signatures; NumPy-style docstrings with `.rst` examples on public functions; line length 88; `uv run ruff check src/ tests/` and `uv run ruff format src/ tests/` clean after every Python task.
- **Colors (exact):** Buy `#f0883e`, Rent `#58a6ff`, page `#0d1117`, surface `#161b22`, raised `#21262d`, border `#30363d`, text `#e6edf3`/`#b1bac4`/`#8b949e`, accent `#1f6feb`, slider values `#7ee787`, error `#da3633`. No red/green outcome semantics. No emoji in UI chrome (the footer privacy line keeps its 🔒 — it is verbatim content, not chrome).
- **Plotly:** pinned CDN `https://cdn.plot.ly/plotly-basic-2.35.2.min.js`; no other JS dependencies; no build step.
- **Monte Carlo stays knobless server-side:** endpoints always use `MonteCarloConfig()` defaults. The `mc_config` parameter on `monte_carlo_payload` exists for tests only.
- **Commits:** Conventional Commits (`feat:`/`fix:`/`chore:`/`docs:`), one commit per task minimum.

---

## Phase 1 — Server + API

### Task 1: Config codec in `api.py`

**Files:**
- Create: `src/simulator/api.py`
- Test: `tests/test_api.py`

**Interfaces:**
- Consumes: `simulator.models.SimulationConfig` (existing dataclass).
- Produces: `config_from_dict(payload: dict) -> SimulationConfig`, `config_to_dict(config: SimulationConfig) -> dict` — used by Tasks 2, 3, 5.

- [ ] **Step 1: Write the failing tests**

```python
"""Tests for the HTTP API layer and FastAPI server."""

import pytest

from simulator.api import config_from_dict, config_to_dict
from tests.test_models import make_config


def test_config_roundtrips_through_camel_case() -> None:
    config = make_config(monthly_rent=2100)
    assert config_from_dict(config_to_dict(config)) == config


def test_config_from_dict_applies_dataclass_defaults() -> None:
    config = config_from_dict(
        {
            "horizonYears": 8,
            "propertyPrice": 450000,
            "downPaymentPct": 25,
            "mortgageRateAnnual": 5.9,
            "propertyAppreciationAnnual": 2.5,
            "equityGrowthAnnual": 6.5,
            "monthlyRent": 1900,
        }
    )
    assert config.horizon_years == 8
    assert config.mortgage_term_years == 30  # dataclass default


def test_config_from_dict_rejects_unknown_field() -> None:
    with pytest.raises(ValueError, match="Unknown config field"):
        config_from_dict({"horizonYears": 8, "bogusField": 1})


def test_config_from_dict_propagates_validation() -> None:
    with pytest.raises(ValueError, match="down_payment_pct"):
        config_from_dict({**config_to_dict(make_config()), "downPaymentPct": 3})
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_api.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'simulator.api'`

- [ ] **Step 3: Implement `api.py`**

```python
"""HTTP API serialization layer for the simulation engine.

Converts JSON-friendly camelCase dicts to engine dataclasses and engine
results back to JSON-friendly dicts. All wire-format decisions live in
this module; the engine is never aware of the HTTP layer.
"""

from __future__ import annotations

from dataclasses import fields
from typing import Any

from .engine import calculate_scenarios
from .models import MonteCarloConfig, SimulationConfig
from .monte_carlo import run_monte_carlo


def _camel(name: str) -> str:
    """Convert snake_case field name to lowerCamelCase."""
    head, *tail = name.split("_")
    return head + "".join(part.title() for part in tail)


_CAMEL_TO_SNAKE: dict[str, str] = {
    _camel(f.name): f.name for f in fields(SimulationConfig)
}


def config_from_dict(payload: dict[str, Any]) -> SimulationConfig:
    """Build a validated ``SimulationConfig`` from a camelCase payload.

    Parameters
    ----------
    payload : dict[str, Any]
        JSON-decoded request body with camelCase keys matching
        ``SimulationConfig`` field names (e.g. ``horizonYears``).

    Returns
    -------
    SimulationConfig
        The validated configuration.

    Raises
    ------
    ValueError
        If an unknown field is present or a value fails dataclass
        validation.
    TypeError
        If a required field is missing.

    Examples
    --------
    .. code-block:: python

        from simulator.api import config_from_dict

        config = config_from_dict(
            {
                "horizonYears": 10,
                "propertyPrice": 500000,
                "downPaymentPct": 20,
                "mortgageRateAnnual": 6.5,
                "propertyAppreciationAnnual": 3.0,
                "equityGrowthAnnual": 7.0,
                "monthlyRent": 2400,
            }
        )

    """
    unknown = sorted(set(payload) - set(_CAMEL_TO_SNAKE))
    if unknown:
        raise ValueError(f"Unknown config field(s): {', '.join(unknown)}")
    kwargs = {_CAMEL_TO_SNAKE[key]: value for key, value in payload.items()}
    return SimulationConfig(**kwargs)


def config_to_dict(config: SimulationConfig) -> dict[str, Any]:
    """Serialize a ``SimulationConfig`` to a camelCase dict.

    Examples
    --------
    .. code-block:: python

        from simulator.api import config_from_dict, config_to_dict
        from tests.test_models import make_config

        config = make_config()
        assert config_from_dict(config_to_dict(config)) == config

    """
    return {_camel(f.name): getattr(config, f.name) for f in fields(config)}
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/test_api.py -v`
Expected: 4 passed

- [ ] **Step 5: Lint + commit**

Run: `uv run ruff check src/ tests/ && uv run ruff format src/ tests/`
Expected: clean

```bash
git add src/simulator/api.py tests/test_api.py
git commit -m "feat: add API config codec with camelCase wire format"
```

---

### Task 2: `simulate_payload` in `api.py`

**Files:**
- Modify: `src/simulator/api.py`
- Test: `tests/test_api.py`

**Interfaces:**
- Consumes: `calculate_scenarios(config) -> SimulationResults` (existing), `config_from_dict` (Task 1).
- Produces: `simulate_payload(config: SimulationConfig) -> dict[str, Any]` — response body of `POST /api/simulate` (Task 5) and of all frontend rendering. Series keys: `year`, `homeValue`, `equityValue`, `buyPortfolioValue`, `mortgageBalance`, `outflowBuy`, `outflowRent`, `cashCommitted`, `netBuy`, `netRent`.

- [ ] **Step 1: Write the failing tests**

```python
import json

from simulator.api import simulate_payload
from simulator.engine import calculate_scenarios


def test_simulate_payload_matches_engine_truth() -> None:
    config = make_config()
    payload = simulate_payload(config)
    results = calculate_scenarios(config)

    assert payload["verdict"]["difference"] == results.final_difference
    expected_winner = "buy" if results.final_difference > 0 else "rent"
    assert payload["verdict"]["winner"] == expected_winner
    assert payload["verdict"]["horizonYears"] == config.horizon_years
    assert payload["breakevenYear"] == results.breakeven_year
    assert payload["monthlyMortgagePayment"] == results.monthly_mortgage_payment
    assert payload["monthlyCostBuyYear1"] == results.monthly_cost_buy_year1
    assert payload["monthlyCostRentYear1"] == results.monthly_cost_rent_year1

    series = payload["series"]
    assert len(series["year"]) == config.horizon_years * 12 + 1
    assert series["netBuy"][-1] == results.final_net_buy
    assert series["netRent"][-1] == results.final_net_rent


def test_simulate_payload_outflows_monotonic() -> None:
    series = simulate_payload(make_config())["series"]
    for key in ("outflowBuy", "outflowRent"):
        values = series[key]
        assert all(b >= a for a, b in zip(values, values[1:], strict=False))


def test_simulate_payload_is_json_serializable() -> None:
    payload = simulate_payload(make_config())
    assert json.loads(json.dumps(payload)) == payload
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_api.py -v -k simulate`
Expected: FAIL — `ImportError: cannot import name 'simulate_payload'`

- [ ] **Step 3: Implement**

Append to `src/simulator/api.py`:

```python
def simulate_payload(config: SimulationConfig) -> dict[str, Any]:
    """Run the deterministic engine and serialize results for the wire.

    Parameters
    ----------
    config : SimulationConfig
        Validated simulation configuration.

    Returns
    -------
    dict[str, Any]
        JSON-ready dict with ``verdict`` (winner, difference,
        horizonYears), ``breakevenYear``, year-1 monthly costs,
        ``totals`` (ownership-cost components), and ``series`` (the
        monthly time series, each ``horizon_years * 12 + 1`` long).

    Examples
    --------
    .. code-block:: python

        from simulator.api import simulate_payload
        from tests.test_models import make_config

        payload = simulate_payload(make_config())
        payload["verdict"]["winner"] in ("buy", "rent")  # True

    """
    results = calculate_scenarios(config)
    df = results.data
    breakeven = results.breakeven_year
    return {
        "verdict": {
            "winner": "buy" if results.final_difference > 0 else "rent",
            "difference": results.final_difference,
            "horizonYears": config.horizon_years,
        },
        "breakevenYear": float(breakeven) if breakeven is not None else None,
        "monthlyMortgagePayment": results.monthly_mortgage_payment,
        "monthlyCostBuyYear1": results.monthly_cost_buy_year1,
        "monthlyCostRentYear1": results.monthly_cost_rent_year1,
        "totals": {
            "closingCostsBuyer": results.total_closing_costs_buyer,
            "closingCostsSeller": results.total_closing_costs_seller,
            "propertyTaxPaid": results.total_property_tax_paid,
            "insurancePaid": results.total_insurance_paid,
            "maintenancePaid": results.total_maintenance_paid,
            "taxSavings": results.total_tax_savings,
        },
        "series": {
            "year": df["Year"].tolist(),
            "homeValue": df["Home_Value"].tolist(),
            "equityValue": df["Equity_Value"].tolist(),
            "buyPortfolioValue": df["Buy_Portfolio_Value"].tolist(),
            "mortgageBalance": df["Mortgage_Balance"].tolist(),
            "outflowBuy": df["Outflow_Buy"].tolist(),
            "outflowRent": df["Outflow_Rent"].tolist(),
            "cashCommitted": df["Cash_Committed"].tolist(),
            "netBuy": df["Net_Buy"].tolist(),
            "netRent": df["Net_Rent"].tolist(),
        },
    }
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/test_api.py -v`
Expected: 7 passed

- [ ] **Step 5: Lint + commit**

```bash
uv run ruff check src/ tests/ && uv run ruff format src/ tests/
git add src/simulator/api.py tests/test_api.py
git commit -m "feat: add simulate payload serialization matching engine truth"
```

---

### Task 3: `monte_carlo_payload` in `api.py`

**Files:**
- Modify: `src/simulator/api.py`
- Test: `tests/test_api.py`

**Interfaces:**
- Consumes: `run_monte_carlo(base_config, mc_config) -> MonteCarloResults` (existing).
- Produces: `monte_carlo_payload(config: SimulationConfig, mc_config: MonteCarloConfig | None = None) -> dict[str, Any]` — response body of `POST /api/monte-carlo` (Task 5) and of the confidence/fan/tornado rendering. Keys: `buyWinsPct`, `medianDifference`, `p5Difference`, `p95Difference`, `yearAxis`, `percentileLevels`, `differencePercentiles`, `tornado` (`params`, `low`, `high`, `base`), `nSimulations`.

- [ ] **Step 1: Write the failing test**

```python
from simulator.api import monte_carlo_payload
from simulator.models import MonteCarloConfig


def test_monte_carlo_payload_shape_and_determinism() -> None:
    config = make_config()
    mc = MonteCarloConfig(n_simulations=30, seed=7)
    first = monte_carlo_payload(config, mc)
    second = monte_carlo_payload(config, mc)

    assert first == second  # fixed seed → identical payloads
    assert 0.0 <= first["buyWinsPct"] <= 100.0
    assert first["nSimulations"] == 30

    fan = first["differencePercentiles"]
    assert len(fan) == len(first["percentileLevels"])
    assert len(fan[0]) == len(first["yearAxis"]) == config.horizon_years * 12 + 1

    tornado = first["tornado"]
    assert len(tornado["params"]) == len(tornado["low"]) == len(tornado["high"])
    assert isinstance(tornado["base"], float)

    assert json.loads(json.dumps(first)) == first
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_api.py -v -k monte_carlo`
Expected: FAIL — `ImportError: cannot import name 'monte_carlo_payload'`

- [ ] **Step 3: Implement**

Append to `src/simulator/api.py`:

```python
def monte_carlo_payload(
    config: SimulationConfig, mc_config: MonteCarloConfig | None = None
) -> dict[str, Any]:
    """Run Monte Carlo analysis and serialize results for the wire.

    Parameters
    ----------
    config : SimulationConfig
        Validated base configuration.
    mc_config : MonteCarloConfig | None, optional
        MC settings; defaults to ``MonteCarloConfig()`` (500 sims, fixed
        seed 42, auto-calibrated stds per ADR-0003). Exposed for tests —
        HTTP endpoints never pass this argument (knobless by design).

    Returns
    -------
    dict[str, Any]
        JSON-ready dict with summary stats, yearly fan percentiles of
        the Buy−Rent difference, tornado sensitivity data, and
        ``nSimulations``.

    Examples
    --------
    .. code-block:: python

        from simulator.api import monte_carlo_payload
        from simulator.models import MonteCarloConfig
        from tests.test_models import make_config

        payload = monte_carlo_payload(
            make_config(), MonteCarloConfig(n_simulations=30, seed=7)
        )
        0.0 <= payload["buyWinsPct"] <= 100.0  # True

    """
    results = run_monte_carlo(config, mc_config or MonteCarloConfig())
    return {
        "buyWinsPct": float(results.buy_wins_pct),
        "medianDifference": float(results.median_difference),
        "p5Difference": float(results.p5_difference),
        "p95Difference": float(results.p95_difference),
        "yearAxis": results.year_arr.tolist(),
        "percentileLevels": results.percentile_levels,
        "differencePercentiles": results.difference_percentiles.tolist(),
        "tornado": {
            "params": results.sensitivity_params,
            "low": results.sensitivity_low.tolist(),
            "high": results.sensitivity_high.tolist(),
            "base": float(results.sensitivity_base),
        },
        "nSimulations": results.n_simulations,
    }
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/test_api.py -v`
Expected: 8 passed

- [ ] **Step 5: Lint + commit**

```bash
uv run ruff check src/ tests/ && uv run ruff format src/ tests/
git add src/simulator/api.py tests/test_api.py
git commit -m "feat: add knobless Monte Carlo payload serialization"
```

---

### Task 4: `regions.py`

**Files:**
- Create: `src/simulator/regions.py`
- Test: `tests/test_api.py` (append)

**Interfaces:**
- Consumes: nothing (pure data).
- Produces: `list_regions() -> list[dict]`, `get_region(region_id: str) -> dict` (raises `KeyError` for unknown id). Region dict keys: `id`, `label`, `available`, `currencySymbol`, `typical` (`propertyPrice`, `monthlyRent`, `mortgageRateAnnual`), `taxPrimitives` (camelCase config fields). `typical`/`taxPrimitives` are `None` when `available` is `False`.

- [ ] **Step 1: Write the failing tests**

```python
from simulator.regions import get_region, list_regions


def test_regions_us_available_others_disabled() -> None:
    regions = {r["id"]: r for r in list_regions()}
    assert set(regions) == {"us", "fr", "de", "nl", "uk"}

    us = regions["us"]
    assert us["available"] is True
    assert us["currencySymbol"] == "$"
    assert us["typical"]["propertyPrice"] == 500000
    assert us["typical"]["monthlyRent"] == 2400
    assert us["taxPrimitives"]["marginalTaxRatePct"] == 24.0
    assert us["taxPrimitives"]["saleCgRegime"] == "exempt_amount"

    for rid in ("fr", "de", "nl", "uk"):
        assert regions[rid]["available"] is False
        assert regions[rid]["typical"] is None
        assert regions[rid]["taxPrimitives"] is None


def test_get_region_unknown_raises_key_error() -> None:
    with pytest.raises(KeyError):
        get_region("xx")
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_api.py -v -k region`
Expected: FAIL — `ModuleNotFoundError: No module named 'simulator.regions'`

- [ ] **Step 3: Implement `regions.py`**

```python
"""Region preset bundles (ADR-0007): trustworthy defaults per market.

v1 ships the US bundle, carried over from the app's long-standing
verified defaults. FR/DE/NL/UK are declared but unavailable until the
redesign spec §7 research completes — shipped values must be
source-verified, never guessed.
"""

from __future__ import annotations

from typing import Any

REGIONS: list[dict[str, Any]] = [
    {
        "id": "us",
        "label": "United States",
        "available": True,
        "currencySymbol": "$",
        "typical": {
            "propertyPrice": 500000,
            "monthlyRent": 2400,
            "mortgageRateAnnual": 6.5,
        },
        "taxPrimitives": {
            "closingCostBuyerPct": 3.0,
            "closingCostSellerPct": 6.0,
            "propertyTaxRate": 1.2,
            "annualHomeInsurance": 1200.0,
            "annualMaintenancePct": 1.0,
            "interestDeductionEnabled": True,
            "marginalTaxRatePct": 24.0,
            "levyDeductionCap": 10000.0,
            "saleCgRegime": "exempt_amount",
            "saleCgExemptAmount": 250000.0,
            "saleCgExemptAfterYears": 10,
            "saleCgRatePct": 15.0,
            "portfolioCgRatePct": 15.0,
        },
    },
    *[
        {
            "id": region_id,
            "label": label,
            "available": False,
            "currencySymbol": symbol,
            "typical": None,
            "taxPrimitives": None,
        }
        for region_id, label, symbol in [
            ("fr", "France", "€"),
            ("de", "Germany", "€"),
            ("nl", "Netherlands", "€"),
            ("uk", "United Kingdom", "£"),
        ]
    ],
]

_BY_ID: dict[str, dict[str, Any]] = {region["id"]: region for region in REGIONS}


def list_regions() -> list[dict[str, Any]]:
    """Return all region bundles, available or not.

    Examples
    --------
    .. code-block:: python

        from simulator.regions import list_regions

        ids = [r["id"] for r in list_regions()]
        assert "us" in ids

    """
    return REGIONS


def get_region(region_id: str) -> dict[str, Any]:
    """Return one region bundle by id.

    Raises
    ------
    KeyError
        If ``region_id`` is unknown.

    Examples
    --------
    .. code-block:: python

        from simulator.regions import get_region

        assert get_region("us")["currencySymbol"] == "$"

    """
    return _BY_ID[region_id]
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/test_api.py -v`
Expected: 10 passed

- [ ] **Step 5: Lint + commit**

```bash
uv run ruff check src/ tests/ && uv run ruff format src/ tests/
git add src/simulator/regions.py tests/test_api.py
git commit -m "feat: add region preset bundles (US available, others declared)"
```

---

### Task 5: FastAPI server

**Files:**
- Create: `src/simulator/server.py`
- Test: `tests/test_api.py` (append)

**Interfaces:**
- Consumes: `config_from_dict`, `simulate_payload`, `monte_carlo_payload` (Tasks 1–3), `list_regions` (Task 4).
- Produces: `app` (FastAPI). `GET /api/health` → `{"status": "ok"}`; `GET /api/regions`; `POST /api/simulate` and `POST /api/monte-carlo` accepting the config dict and returning the Task 2/3 payloads; 422 `{"detail": str}` on invalid config.

- [ ] **Step 1: Write the failing tests**

```python
from fastapi.testclient import TestClient

from simulator.api import config_to_dict
from simulator.server import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_regions_endpoint() -> None:
    response = client.get("/api/regions")
    assert response.status_code == 200
    regions = response.json()
    assert len(regions) == 5
    assert regions[0]["id"] == "us"


def test_simulate_endpoint_happy_path() -> None:
    response = client.post("/api/simulate", json=config_to_dict(make_config()))
    assert response.status_code == 200
    body = response.json()
    assert body["verdict"]["winner"] in ("buy", "rent")
    assert len(body["series"]["netBuy"]) == 121


def test_simulate_endpoint_validation_error_is_422() -> None:
    payload = {**config_to_dict(make_config()), "downPaymentPct": 3}
    response = client.post("/api/simulate", json=payload)
    assert response.status_code == 422
    assert "down_payment_pct" in response.json()["detail"]


def test_simulate_endpoint_unknown_field_is_422() -> None:
    response = client.post("/api/simulate", json={"bogusField": 1})
    assert response.status_code == 422
    assert "Unknown config field" in response.json()["detail"]


def test_monte_carlo_endpoint_happy_path() -> None:
    response = client.post("/api/monte-carlo", json=config_to_dict(make_config()))
    assert response.status_code == 200
    body = response.json()
    assert 0.0 <= body["buyWinsPct"] <= 100.0
    assert body["nSimulations"] == 500
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_api.py -v -k "endpoint or health"`
Expected: FAIL — `ModuleNotFoundError: No module named 'simulator.server'` (or `No module named 'fastapi'` if Step 3's dependency install hasn't run yet — either failure confirms the red state)

- [ ] **Step 3: Add dependencies + implement `server.py`**

First add FastAPI/uvicorn and the test-time httpx:

```bash
uv add "fastapi>=0.115.0" "uvicorn[standard]>=0.30.0"
uv add --dev "httpx>=0.27.0"
```

Then create `src/simulator/server.py`:

```python
"""FastAPI server for the rent-vs-buy simulator.

Serves the static frontend and the JSON API wrapping the simulation
engine. Mirrors the structure of the author's other apps (health
endpoint, no-cache middleware for static assets during development).

Run with: uv run uvicorn simulator.server:app --reload
"""

from pathlib import Path
from typing import Any

from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from .api import config_from_dict, monte_carlo_payload, simulate_payload
from .regions import list_regions


class NoCacheMiddleware(BaseHTTPMiddleware):
    """Disable browser caching for JS/CSS/HTML during development."""

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        """Add no-cache headers to static asset responses."""
        response = await call_next(request)
        path = request.url.path
        if path.endswith((".js", ".css", ".html")) or path == "/":
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
        return response


app = FastAPI(title="Rent or Buy?")
app.add_middleware(NoCacheMiddleware)


@app.get("/api/health")
def health() -> JSONResponse:
    """Liveness probe used by Docker healthchecks and Coolify."""
    return JSONResponse({"status": "ok"})


@app.get("/api/regions")
def regions() -> list[dict[str, Any]]:
    """List region preset bundles (ADR-0007)."""
    return list_regions()


@app.post("/api/simulate")
def simulate(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    """Run the deterministic engine; 422 on invalid configuration."""
    try:
        config = config_from_dict(payload)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return simulate_payload(config)


@app.post("/api/monte-carlo")
def monte_carlo(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    """Run the knobless Monte Carlo analysis; 422 on invalid config."""
    try:
        config = config_from_dict(payload)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return monte_carlo_payload(config)


_STATIC_DIR = Path(__file__).parent / "static"
app.mount(
    "/",
    StaticFiles(directory=_STATIC_DIR, html=True, check_dir=False),
    name="static",
)
```

Note: `check_dir=False` keeps the app importable before `static/` exists (Phase 2 creates it).

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/test_api.py -v`
Expected: 16 passed

- [ ] **Step 5: Lint, type-check, smoke, commit**

```bash
uv run ruff check src/ tests/ && uv run ruff format src/ tests/
uv run ty check src/
```

Smoke (manual): `uv run uvicorn simulator.server:app --port 8010` in one shell, then:

```bash
curl -s http://localhost:8010/api/health
# expected: {"status":"ok"}
curl -s -X POST http://localhost:8010/api/simulate \
  -H 'Content-Type: application/json' \
  -d '{"horizonYears":10,"propertyPrice":500000,"downPaymentPct":20,"mortgageRateAnnual":6.5,"propertyAppreciationAnnual":3.0,"equityGrowthAnnual":7.0,"monthlyRent":2400}' | head -c 300
# expected: JSON starting with {"verdict":{"winner":...
```

Stop the server, then:

```bash
git add src/simulator/server.py tests/test_api.py pyproject.toml uv.lock
git commit -m "feat: add FastAPI server with simulate/monte-carlo/regions endpoints"
```

---

### Task 6: Phase 1 gate — full Python suite green

**Files:** none (verification only)

- [ ] **Step 1: Run the whole suite with coverage**

Run: `uv run pytest tests/ -v --cov --cov-report=term`
Expected: all pass; coverage ≥ 80% (new modules `api.py`, `regions.py`, `server.py` covered by `test_api.py`).

- [ ] **Step 2: Confirm Streamlit still runs (not yet cut over)**

Run: `uv run streamlit run src/simulator/app.py --server.port 8519` → loads without import errors. Stop it.

No commit (nothing changed).

---

## Phase 2 — Static shell + visual system

### Task 7: `index.html`

**Files:**
- Create: `src/simulator/static/index.html`

**Interfaces:**
- Produces: DOM ids consumed by JS (Tasks 9–13): `error-banner`, `welcome-overlay`, `welcome-start`, `guide-overlay`, `guide-btn`, `advanced-btn`, `advanced-panel`, `advanced-close`, `inputs-btn`, `input-panel`, `region-pills`, `outlook-pills`, `core-inputs`, `assumption-inputs`, `advanced-inputs`, `verdict-line`, `verdict-breakeven`, `verdict-confidence`, `stat-buy`, `stat-rent`, `stat-cost-buy`, `stat-cost-rent`, `decision-chart`, `fan-chart`, `tornado-chart`, `outflow-chart`, `breakdown-chart`, `data-table`, `csv-btn`, `results-spinner`.

- [ ] **Step 1: Port the guide/welcome prose**

Open `src/simulator/explainers.py`. Copy the inner markup of:
- `_WELCOME_MODAL_HTML` → into `#welcome-overlay .modal` (Step 2 marker `<!-- PORT: welcome -->`)
- `_GUIDE_SCENARIOS_HTML` → first `.guide-section-body`
- `_GUIDE_NET_VALUE_HTML` → second `.guide-section-body`
- `_GUIDE_BREAKEVEN_HTML` → third `.guide-section-body`
- `_GUIDE_MONTE_CARLO_HTML` → fourth `.guide-section-body`

Copy the prose verbatim (keep `<strong>`/`<em>`/`<ul>`); drop any Streamlit-specific wrapper markup. (`explainers.py` remains in the repo until Task 14 — do not delete it now.)

- [ ] **Step 2: Write `index.html`**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Rent or buy?</title>
  <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>🏠</text></svg>">
  <link rel="stylesheet" href="css/style.css">
  <script src="https://cdn.plot.ly/plotly-basic-2.35.2.min.js"></script>
</head>
<body>

<div id="error-banner"><span></span> <button onclick="location.reload()">Reload</button></div>

<div id="app">

  <div id="welcome-overlay" class="overlay">
    <div class="modal">
      <button class="modal-close" id="welcome-close" aria-label="Close">✕</button>
      <!-- PORT: welcome — inner markup of _WELCOME_MODAL_HTML from explainers.py -->
      <button id="welcome-start" class="btn-primary">Start exploring</button>
    </div>
  </div>

  <div id="guide-overlay" class="overlay hidden">
    <div class="modal">
      <button class="modal-close" aria-label="Close">✕</button>
      <h1>How this works</h1>
      <div class="guide-section">
        <div class="guide-section-header"><span class="guide-chevron">▸</span><span class="guide-section-title">The two strategies</span></div>
        <div class="guide-section-body"><!-- PORT: _GUIDE_SCENARIOS_HTML --></div>
      </div>
      <div class="guide-section">
        <div class="guide-section-header"><span class="guide-chevron">▸</span><span class="guide-section-title">Net Value</span></div>
        <div class="guide-section-body"><!-- PORT: _GUIDE_NET_VALUE_HTML --></div>
      </div>
      <div class="guide-section">
        <div class="guide-section-header"><span class="guide-chevron">▸</span><span class="guide-section-title">Breakeven</span></div>
        <div class="guide-section-body"><!-- PORT: _GUIDE_BREAKEVEN_HTML --></div>
      </div>
      <div class="guide-section">
        <div class="guide-section-header"><span class="guide-chevron">▸</span><span class="guide-section-title">Monte Carlo confidence</span></div>
        <div class="guide-section-body"><!-- PORT: _GUIDE_MONTE_CARLO_HTML --></div>
      </div>
    </div>
  </div>

  <div id="title-bar">
    <span id="app-name">🏠 Rent or buy?</span>
    <span class="badge">decision tool</span>
    <span class="title-spacer"></span>
    <a class="author-link" href="https://github.com/palsagar" target="_blank" rel="noopener">by palsagar</a>
    <a class="gh-pill" href="https://github.com/palsagar/rent-vs-buy-simulator" target="_blank" rel="noopener">★ GitHub</a>
  </div>

  <div id="preset-bar">
    <button id="inputs-btn" class="btn">Inputs</button>
    <span class="preset-label">Region</span>
    <span id="region-pills"></span>
    <span class="preset-label" style="margin-left:14px">Outlook</span>
    <span id="outlook-pills"></span>
    <span class="title-spacer"></span>
    <button id="advanced-btn" class="btn btn-advanced">⚙ Advanced</button>
    <button id="guide-btn" class="btn">? Guide</button>
  </div>

  <div id="main">
    <aside id="input-panel">
      <div class="section-title">Your situation</div>
      <div id="core-inputs"></div>
      <div class="section-title">Outlook assumptions</div>
      <div id="assumption-inputs"></div>
    </aside>

    <div id="results">
      <div id="results-spinner">updating…</div>

      <section id="verdict-hero">
        <p id="verdict-line"></p>
        <div id="verdict-subline"><span id="verdict-breakeven"></span><span id="verdict-confidence"></span></div>
        <div id="stat-row">
          <div class="stat-card buy"><div class="stat-label">Buy net value</div><div class="stat-value buy" id="stat-buy"></div></div>
          <div class="stat-card rent"><div class="stat-label">Rent net value</div><div class="stat-value rent" id="stat-rent"></div></div>
          <div class="stat-card"><div class="stat-label">Buy cost · yr 1</div><div class="stat-value" id="stat-cost-buy"></div></div>
          <div class="stat-card"><div class="stat-label">Rent cost · yr 1</div><div class="stat-value" id="stat-cost-rent"></div></div>
        </div>
      </section>

      <section class="card">
        <h2>Net value over time</h2>
        <div class="card-sub">What you'd walk away with, minus everything you put in — at every year.</div>
        <div id="decision-chart" class="chart"></div>
      </section>

      <section class="card">
        <h2>How sure is this?</h2>
        <div class="card-sub">500 simulated futures of the Buy − Rent difference. Bands: 50% and 90% of outcomes.</div>
        <div id="fan-chart" class="chart"></div>
        <h2 style="margin-top:18px">Which assumption to stress-test hardest</h2>
        <div class="card-sub">Wider bar = bigger swing in the outcome. Blue = assumption goes up, grey = goes down.</div>
        <div id="tornado-chart" class="chart"></div>
      </section>

      <section class="card">
        <h2>Where the money goes</h2>
        <div class="card-sub">Cumulative cash out of pocket on each side.</div>
        <div id="outflow-chart" class="chart"></div>
        <h2 style="margin-top:18px">Cost of ownership breakdown</h2>
        <div id="breakdown-chart" class="chart"></div>
      </section>

      <details id="numbers">
        <summary>The numbers</summary>
        <div id="data-table"></div>
        <button id="csv-btn" class="btn">Download CSV</button>
      </details>

      <footer>
        🔒 <strong>Privacy:</strong> This app does not track any user data, use cookies, or perform any analytics. Self-hosted on a tiny VPS via <a href="https://coolify.io/" target="_blank" rel="noopener">Coolify</a>.<br>
        Calculations use monthly granularity; Net Value prices a full exit at every year (selling costs and capital-gains tax on both sides). US tax defaults; more regions coming. Source: <a href="https://github.com/palsagar/rent-vs-buy-simulator" target="_blank" rel="noopener">GitHub</a>.
      </footer>
    </div>

    <aside id="advanced-panel">
      <div class="panel-header">Advanced <button id="advanced-close" aria-label="Close">✕</button></div>
      <div class="slider-hint" style="margin-bottom:12px">Defaults follow the selected region.</div>
      <div id="advanced-inputs"></div>
    </aside>
  </div>

</div>

<script type="module" src="js/main.js"></script>
</body>
</html>
```

- [ ] **Step 3: Serve and verify structure**

Run: `uv run uvicorn simulator.server:app --port 8010`, open `http://localhost:8010`.
Expected: title-bar, preset-bar (Advanced + Guide buttons), empty left panel, results skeleton, welcome modal shows; guide opens via `? Guide` with four accordions and ported prose. (Unstyled until Task 8 — verify DOM presence with View Source / DevTools.)

No commit yet — commit with Task 8.

---

### Task 8: `css/style.css`

**Files:**
- Create: `src/simulator/static/css/style.css`

**Interfaces:**
- Consumes: `index.html` structure (Task 7).

- [ ] **Step 1: Write the stylesheet**

```css
/* Rent or buy? — GitHub-dark design tokens ported verbatim from
   webgpu-fluid-solver / webgpu-gray-scott. Single dark theme. */

*, *::before, *::after {
  box-sizing: border-box;
}

:root {
  --bg: #0d1117;
  --surface: #161b22;
  --raised: #21262d;
  --border: #30363d;
  --text: #e6edf3;
  --text-2: #b1bac4;
  --muted: #8b949e;
  --faint: #484f58;
  --accent: #1f6feb;
  --accent-text: #58a6ff;
  --buy: #f0883e;
  --rent: #58a6ff;
  --green: #238636;
  --green-text: #7ee787;
  --error: #da3633;
  --mono: 'SF Mono', 'Cascadia Code', monospace;
}

body {
  background: var(--bg);
  color: var(--text-2);
  font-family: -apple-system, 'Segoe UI', sans-serif;
  margin: 0;
  overflow: hidden;
}

#app {
  display: flex;
  flex-direction: column;
  height: 100vh;
}

/* Error banner (device-lost pattern) */
#error-banner {
  display: none;
  background: var(--error);
  color: #fff;
  padding: 10px 16px;
  font-size: 13px;
  text-align: center;
  z-index: 100;
}
#error-banner.visible { display: block; }
#error-banner button {
  margin-left: 10px;
  background: none;
  border: 1px solid rgba(255, 255, 255, 0.6);
  border-radius: 4px;
  color: #fff;
  font-size: 12px;
  padding: 2px 10px;
  cursor: pointer;
}

/* Title bar (ported) */
#title-bar {
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  padding: 10px 16px;
  display: flex;
  align-items: center;
  gap: 12px;
}
#app-name { font-weight: 700; font-size: 16px; color: var(--text); }
.badge {
  display: inline-flex;
  padding: 3px 9px;
  border-radius: 8px;
  font-size: 10px;
  font-weight: 600;
  font-family: var(--mono);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  background: rgba(31, 111, 235, 0.2);
  color: var(--accent-text);
  border: 1px solid rgba(31, 111, 235, 0.3);
}
.title-spacer { flex: 1; }
.author-link { color: var(--text-2); text-decoration: none; font-size: 12px; }
.author-link:hover { color: #ffffff; }
.gh-pill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: #c9d1d9;
  text-decoration: none;
  font-size: 11px;
  padding: 3px 10px;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: var(--raised);
  transition: border-color 0.2s, color 0.2s;
}
.gh-pill:hover { border-color: var(--accent-text); color: #ffffff; }

/* Preset bar (ported) */
#preset-bar {
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  padding: 8px 16px;
  display: flex;
  align-items: center;
  gap: 8px;
  overflow-x: auto;
}
.preset-label {
  font-size: 11px;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  white-space: nowrap;
}
.preset-btn {
  padding: 4px 10px;
  background: var(--raised);
  border: 1px solid var(--border);
  border-radius: 4px;
  font-size: 12px;
  color: #c9d1d9;
  cursor: pointer;
  white-space: nowrap;
}
.preset-btn.active { background: var(--accent); border-color: var(--accent); color: #fff; }
.preset-btn.disabled { color: var(--faint); cursor: not-allowed; }
.btn {
  padding: 5px 14px;
  border: 1px solid var(--border);
  border-radius: 6px;
  font-size: 12px;
  cursor: pointer;
  background: var(--raised);
  color: #c9d1d9;
  white-space: nowrap;
}
.btn-advanced { background: var(--error); border-color: var(--error); color: #fff; }

/* Layout */
#main { flex: 1; display: flex; overflow: hidden; position: relative; }
#input-panel {
  width: 280px;
  min-width: 280px;
  background: var(--surface);
  border-right: 1px solid var(--border);
  padding: 16px;
  overflow-y: auto;
}
#results {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
#results-spinner {
  display: none;
  justify-content: center;
  font-family: var(--mono);
  font-size: 11px;
  color: var(--green-text);
}

/* Inputs (ported slider system) */
.section-title {
  font-size: 11px;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin: 14px 0 8px;
}
#input-panel .section-title:first-child { margin-top: 0; }
.slider-row { margin-bottom: 10px; }
.slider-header { display: flex; justify-content: space-between; margin-bottom: 3px; }
.slider-name { font-size: 12px; color: #c9d1d9; }
.slider-value { font-size: 12px; color: var(--green-text); font-family: var(--mono); }
input[type="range"] {
  -webkit-appearance: none;
  appearance: none;
  width: 100%;
  height: 4px;
  background: var(--raised);
  border-radius: 2px;
  outline: none;
}
input[type="range"]::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--accent);
  cursor: pointer;
}
input[type="range"]::-moz-range-thumb {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--accent);
  cursor: pointer;
  border: none;
}
.slider-hint { font-size: 10px; color: #6e7681; margin-top: 2px; }
.select-row select {
  width: 100%;
  background: var(--raised);
  border: 1px solid var(--border);
  border-radius: 6px;
  color: var(--text);
  font-size: 12px;
  padding: 5px 8px;
  margin-bottom: 10px;
}
.checkbox-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #c9d1d9;
  margin-bottom: 10px;
}
.checkbox-row input { accent-color: var(--accent); }
.seg-picker { display: flex; gap: 6px; margin-bottom: 10px; }
.seg-btn {
  flex: 1;
  padding: 4px 0;
  background: var(--raised);
  border: 1px solid var(--border);
  border-radius: 4px;
  font-size: 12px;
  font-family: var(--mono);
  color: #c9d1d9;
  cursor: pointer;
}
.seg-btn.active { background: var(--accent); border-color: var(--accent); color: #fff; }

/* Advanced drawer (ported) */
#advanced-panel {
  position: absolute;
  right: 0;
  top: 0;
  bottom: 0;
  width: 280px;
  background: var(--surface);
  border-left: 1px solid var(--border);
  padding: 16px;
  transform: translateX(100%);
  transition: transform 0.3s ease;
  z-index: 10;
  overflow-y: auto;
}
#advanced-panel.visible { transform: translateX(0); }
.panel-header {
  font-weight: 600;
  font-size: 14px;
  color: #f0f6fc;
  margin-bottom: 16px;
  display: flex;
  justify-content: space-between;
}
.panel-header button {
  background: none;
  border: none;
  color: var(--muted);
  cursor: pointer;
  font-size: 14px;
  padding: 0;
}

/* Verdict hero */
#verdict-hero {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 24px 26px;
}
#verdict-line {
  font-size: 26px;
  font-weight: 700;
  color: var(--text);
  letter-spacing: -0.5px;
  line-height: 1.3;
  margin: 0;
}
#verdict-line .amount-buy { color: var(--buy); }
#verdict-line .amount-rent { color: var(--rent); }
#verdict-subline { font-size: 13px; color: var(--muted); margin-top: 8px; }
#stat-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
  margin-top: 16px;
}
.stat-card {
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 10px 12px;
}
.stat-card.buy { border-left: 3px solid var(--buy); }
.stat-card.rent { border-left: 3px solid var(--rent); }
.stat-label {
  font-size: 10px;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.stat-value { font-family: var(--mono); font-size: 16px; color: var(--text); margin-top: 3px; }
.stat-value.buy { color: var(--buy); }
.stat-value.rent { color: var(--rent); }

/* Chart cards */
.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 16px 18px;
}
.card h2 { font-size: 15px; font-weight: 600; color: var(--text); margin: 0 0 4px; }
.card .card-sub { font-size: 12px; color: var(--muted); margin-bottom: 8px; }
.chart { width: 100%; height: 320px; }

/* Numbers table */
#numbers {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 12px 18px;
}
#numbers summary { cursor: pointer; font-size: 14px; font-weight: 600; color: var(--text); }
#data-table { margin-top: 10px; max-height: 400px; overflow: auto; }
#data-table table { border-collapse: collapse; width: 100%; font-family: var(--mono); font-size: 11px; }
#data-table th {
  position: sticky;
  top: 0;
  background: var(--surface);
  color: var(--muted);
  text-align: right;
  padding: 6px 10px;
  border-bottom: 1px solid var(--border);
}
#data-table td {
  text-align: right;
  padding: 4px 10px;
  border-bottom: 1px solid rgba(48, 54, 61, 0.4);
  color: var(--text-2);
}
#csv-btn { margin-top: 10px; }

/* Footer */
footer { font-size: 12px; color: var(--muted); line-height: 1.7; padding: 8px 4px 24px; }
footer a { color: var(--accent-text); text-decoration: none; }

/* Overlays: welcome modal + guide (ported) */
.overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 200;
  transition: opacity 0.3s ease;
}
.overlay.hidden { opacity: 0; pointer-events: none; }
.modal {
  position: relative;
  max-width: 600px;
  width: 90vw;
  max-height: 90vh;
  overflow-y: auto;
  background: rgba(13, 17, 23, 0.92);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid rgba(48, 54, 61, 0.8);
  border-radius: 12px;
  padding: 40px 40px 32px;
  box-shadow: 0 19px 38px rgba(0, 0, 0, 0.3), 0 15px 12px rgba(0, 0, 0, 0.22);
}
.modal h1 { font-size: 26px; font-weight: 700; color: var(--text); letter-spacing: -0.5px; margin: 0 0 14px; }
.modal p, .modal li { font-size: 14px; line-height: 1.65; color: var(--text-2); }
.modal strong { color: var(--text); }
.modal em { color: #a5d6ff; }
.modal-close {
  position: absolute;
  top: 14px;
  right: 16px;
  background: none;
  border: none;
  color: var(--muted);
  font-size: 16px;
  cursor: pointer;
}
.btn-primary {
  display: inline-flex;
  padding: 10px 28px;
  font-size: 15px;
  font-weight: 600;
  color: #fff;
  background: var(--green);
  border: 1px solid rgba(35, 134, 54, 0.6);
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s;
}
.btn-primary:hover { background: #2ea043; }
.guide-section { border-bottom: 1px solid rgba(48, 54, 61, 0.6); }
.guide-section:last-child { border-bottom: none; }
.guide-section-header { display: flex; align-items: center; gap: 8px; padding: 12px 0; cursor: pointer; }
.guide-section-title { font-size: 14px; font-weight: 600; color: var(--text-2); }
.guide-chevron { color: var(--faint); transition: transform 0.2s; }
.guide-section.open .guide-chevron { transform: rotate(90deg); }
.guide-section-body { max-height: 0; overflow: hidden; transition: max-height 0.3s ease; }
.guide-section.open .guide-section-body { max-height: 2000px; }

/* Mobile: left panel becomes a drawer */
#inputs-btn { display: none; }
@media (max-width: 900px) {
  #inputs-btn { display: inline-flex; }
  #input-panel {
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    z-index: 10;
    transform: translateX(-100%);
    transition: transform 0.3s ease;
  }
  #input-panel.visible { transform: translateX(0); box-shadow: 8px 0 16px rgba(0, 0, 0, 0.4); }
  #stat-row { grid-template-columns: repeat(2, 1fr); }
  #verdict-line { font-size: 20px; }
  #results { padding: 14px; }
}
```

- [ ] **Step 2: Visual verification**

Serve (`uv run uvicorn simulator.server:app --port 8010`) and check against the reference apps side by side: background `#0d1117`, panels `#161b22`, blue slider thumbs, green mono slider values, red Advanced button, welcome modal with blur backdrop, guide accordions animating, Advanced drawer sliding from the right. At ≤900px viewport the left panel hides behind the `Inputs` button.

- [ ] **Step 3: Commit**

```bash
git add src/simulator/static/index.html src/simulator/static/css/style.css
git commit -m "feat: static frontend shell with GitHub-dark visual system"
```

---

## Phase 3 — Results + charts + behavior

### Task 9: `js/format.js`, `js/api.js`, `js/state.js`

**Files:**
- Create: `src/simulator/static/js/format.js`
- Create: `src/simulator/static/js/api.js`
- Create: `src/simulator/static/js/state.js`

**Interfaces:**
- Produces:
  - `format.js`: `fmtMoney(v)`, `fmtCompact(v)`, `fmtPct(v, digits = 1)`
  - `api.js`: `serializeForWire(cfg)`, `postSimulate(cfg, signal)`, `postMonteCarlo(cfg, signal)`, `getRegions()`
  - `state.js`: `DEFAULT_CONFIG`, `getConfig()`, `setParam(key, value)`, `applyPreset(partial)`, `onConfigChange(fn)`, `readUrl()`, `configHash(cfg)`, `getCached(kind, hash)`, `setCached(kind, hash, value)`, `debounce(fn, ms)`

- [ ] **Step 1: Write `format.js`**

```js
// Number formatting shared by inputs and results.

export function fmtMoney(v) {
  const sign = v < 0 ? "-" : "";
  return `${sign}$${Math.round(Math.abs(v)).toLocaleString("en-US")}`;
}

export function fmtCompact(v) {
  const sign = v < 0 ? "-" : "";
  const abs = Math.abs(v);
  if (abs >= 1_000_000) return `${sign}$${(abs / 1_000_000).toFixed(1)}M`;
  if (abs >= 10_000) return `${sign}$${Math.round(abs / 1000)}k`;
  return fmtMoney(v);
}

export function fmtPct(v, digits = 1) {
  return `${v.toFixed(digits)}%`;
}
```

- [ ] **Step 2: Write `api.js`**

```js
// Fetch wrappers for the simulation API. `levyDeductionCap: 0` on the
// client means "uncapped" — the engine represents that as null.

export function serializeForWire(cfg) {
  return {
    ...cfg,
    levyDeductionCap: cfg.levyDeductionCap > 0 ? cfg.levyDeductionCap : null,
  };
}

async function postJson(path, body, signal) {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const data = await res.json();
      if (data.detail) {
        detail = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
      }
    } catch {
      // keep default message
    }
    throw new Error(detail);
  }
  return res.json();
}

export function postSimulate(cfg, signal) {
  return postJson("/api/simulate", serializeForWire(cfg), signal);
}

export function postMonteCarlo(cfg, signal) {
  return postJson("/api/monte-carlo", serializeForWire(cfg), signal);
}

export async function getRegions() {
  const res = await fetch("/api/regions");
  if (!res.ok) throw new Error(`Regions request failed (${res.status})`);
  return res.json();
}
```

- [ ] **Step 3: Write `state.js`**

```js
// Central config state, share-URL codec, debounce, and result cache.

export const DEFAULT_CONFIG = {
  horizonYears: 10,
  propertyPrice: 500000,
  downPaymentPct: 20,
  mortgageRateAnnual: 6.5,
  propertyAppreciationAnnual: 3.0,
  equityGrowthAnnual: 7.0,
  monthlyRent: 2400,
  mortgageTermYears: 30,
  rentInflationRate: 0.03,
  closingCostBuyerPct: 3.0,
  closingCostSellerPct: 6.0,
  propertyTaxRate: 1.2,
  annualHomeInsurance: 1200,
  annualMaintenancePct: 1.0,
  costInflationRate: 0.025,
  interestDeductionEnabled: true,
  marginalTaxRatePct: 24.0,
  levyDeductionCap: 10000,
  saleCgRegime: "exempt_amount",
  saleCgExemptAmount: 250000,
  saleCgExemptAfterYears: 10,
  saleCgRatePct: 15.0,
  portfolioCgRatePct: 15.0,
};

let config = { ...DEFAULT_CONFIG };
const listeners = [];

export function getConfig() {
  return { ...config };
}

export function onConfigChange(fn) {
  listeners.push(fn);
}

function emit() {
  writeUrl();
  for (const fn of listeners) fn(getConfig());
}

export function setParam(key, value) {
  config[key] = value;
  emit();
}

export function applyPreset(partial) {
  Object.assign(config, partial);
  emit();
}

// --- share URL codec: only non-default values are written ---

function writeUrl() {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(config)) {
    if (value !== DEFAULT_CONFIG[key]) params.set(key, value);
  }
  const qs = params.toString();
  history.replaceState(null, "", qs ? `?${qs}` : location.pathname);
}

export function readUrl() {
  const params = new URLSearchParams(location.search);
  const restored = {};
  for (const [key, def] of Object.entries(DEFAULT_CONFIG)) {
    if (!params.has(key)) continue;
    const raw = params.get(key);
    if (typeof def === "boolean") {
      restored[key] = raw === "true";
    } else if (typeof def === "number") {
      const n = Number(raw);
      if (!Number.isNaN(n)) restored[key] = n;
    } else {
      restored[key] = raw;
    }
  }
  if (Object.keys(restored).length > 0) {
    config = { ...DEFAULT_CONFIG, ...restored };
  }
}

// --- result cache, keyed by the serialized config ---

const cache = new Map();

export function configHash(cfg) {
  return JSON.stringify(cfg);
}

export function getCached(kind, hash) {
  return cache.get(hash)?.[kind];
}

export function setCached(kind, hash, value) {
  cache.set(hash, { ...cache.get(hash), [kind]: value });
}

export function debounce(fn, ms) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), ms);
  };
}
```

- [ ] **Step 4: Commit**

```bash
git add src/simulator/static/js/format.js src/simulator/static/js/api.js src/simulator/static/js/state.js
git commit -m "feat: frontend state, URL codec, and API client modules"
```

---

### Task 10: `js/inputs.js`

**Files:**
- Create: `src/simulator/static/js/inputs.js`

**Interfaces:**
- Consumes: `state.js` (`getConfig`, `setParam`, `applyPreset`), `format.js`.
- Produces: `initInputs(regions)`, `syncInputs()`. Called once by `main.js`; `syncInputs()` re-renders all input values after presets/URL restore.

- [ ] **Step 1: Write `inputs.js`**

```js
// Input rendering: left panel (core + assumptions), advanced drawer,
// region and outlook preset pills. Slider `scale` converts between the
// stored value and the displayed one (decimal rates display ×100).

import { fmtCompact, fmtMoney, fmtPct } from "./format.js";
import { applyPreset, getConfig, setParam } from "./state.js";

const INPUT_DEFS = [
  { key: "propertyPrice", label: "Home price", min: 50000, max: 2000000, step: 5000, fmt: fmtCompact, section: "core", hint: "Purchase price of the property" },
  { key: "downPaymentPct", label: "Down payment", min: 5, max: 50, step: 1, fmt: (v) => fmtPct(v, 0), section: "core" },
  { key: "mortgageRateAnnual", label: "Mortgage rate", min: 1, max: 10, step: 0.05, fmt: (v) => fmtPct(v, 2), section: "core" },
  { key: "mortgageTermYears", label: "Mortgage term", type: "segmented", options: [15, 20, 30], section: "core", hint: "Amortization period — independent of the horizon" },
  { key: "monthlyRent", label: "Monthly rent", min: 500, max: 10000, step: 50, fmt: fmtMoney, section: "core" },
  { key: "horizonYears", label: "Horizon", min: 2, max: 40, step: 1, fmt: (v) => `${v} yrs`, section: "core", hint: "Years until you'd sell — the chart x-axis ends here" },
  { key: "propertyAppreciationAnnual", label: "Property appreciation", min: 0, max: 10, step: 0.1, fmt: (v) => fmtPct(v), section: "assumptions" },
  { key: "equityGrowthAnnual", label: "Equity growth (CAGR)", min: 0, max: 15, step: 0.1, fmt: (v) => fmtPct(v), section: "assumptions" },
  { key: "rentInflationRate", label: "Rent inflation", min: 0, max: 10, step: 0.1, scale: 100, fmt: (v) => fmtPct(v), section: "assumptions" },
  { key: "closingCostBuyerPct", label: "Buyer closing costs", min: 0, max: 10, step: 0.1, fmt: (v) => fmtPct(v), section: "advanced" },
  { key: "closingCostSellerPct", label: "Seller closing costs", min: 0, max: 10, step: 0.1, fmt: (v) => fmtPct(v), section: "advanced" },
  { key: "propertyTaxRate", label: "Property levy", min: 0, max: 5, step: 0.05, fmt: (v) => fmtPct(v, 2), section: "advanced" },
  { key: "annualHomeInsurance", label: "Home insurance /yr", min: 0, max: 5000, step: 50, fmt: fmtMoney, section: "advanced" },
  { key: "annualMaintenancePct", label: "Maintenance", min: 0, max: 5, step: 0.1, fmt: (v) => fmtPct(v), section: "advanced" },
  { key: "costInflationRate", label: "Cost inflation", min: 0, max: 10, step: 0.1, scale: 100, fmt: (v) => fmtPct(v), section: "advanced" },
  { key: "interestDeductionEnabled", label: "Interest deductible", type: "checkbox", section: "advanced", hint: "Deduct mortgage interest (and capped levy) from taxable income" },
  { key: "marginalTaxRatePct", label: "Marginal tax rate", min: 0, max: 60, step: 1, fmt: (v) => fmtPct(v, 0), section: "advanced" },
  { key: "levyDeductionCap", label: "Levy deduction cap", min: 0, max: 50000, step: 1000, fmt: (v) => (v === 0 ? "uncapped" : fmtMoney(v)), section: "advanced", hint: "0 = uncapped (US SALT cap is $10k)" },
  { key: "saleCgRegime", label: "Home-sale CG rule", type: "select", options: [["exempt_amount", "Exempt up to a fixed amount"], ["exempt_after_years", "Exempt after N years"], ["fully_exempt", "Always exempt"]], section: "advanced" },
  { key: "saleCgExemptAmount", label: "Exempt gain amount", min: 0, max: 1000000, step: 10000, fmt: fmtCompact, section: "advanced" },
  { key: "saleCgExemptAfterYears", label: "Exempt after (years)", min: 0, max: 30, step: 1, fmt: (v) => `${v} yrs`, section: "advanced" },
  { key: "saleCgRatePct", label: "Home-sale CG rate", min: 0, max: 40, step: 0.5, fmt: (v) => fmtPct(v), section: "advanced" },
  { key: "portfolioCgRatePct", label: "Investment CG rate", min: 0, max: 40, step: 0.5, fmt: (v) => fmtPct(v), section: "advanced" },
];

const OUTLOOK_PRESETS = {
  conservative: { propertyAppreciationAnnual: 2.0, equityGrowthAnnual: 5.0, rentInflationRate: 0.02 },
  historical: { propertyAppreciationAnnual: 3.0, equityGrowthAnnual: 7.0, rentInflationRate: 0.03 },
  optimistic: { propertyAppreciationAnnual: 5.0, equityGrowthAnnual: 10.0, rentInflationRate: 0.025 },
};

const SECTION_CONTAINERS = {
  core: "core-inputs",
  assumptions: "assumption-inputs",
  advanced: "advanced-inputs",
};

const widgets = []; // { def, refresh() } — refresh re-reads state into the widget

function buildSlider(def, container) {
  const scale = def.scale ?? 1;
  const row = document.createElement("div");
  row.className = "slider-row";
  row.innerHTML = `
    <div class="slider-header">
      <span class="slider-name">${def.label}</span>
      <span class="slider-value"></span>
  </div>
    <input type="range" min="${def.min}" max="${def.max}" step="${def.step}">
    ${def.hint ? `<div class="slider-hint">${def.hint}</div>` : ""}
  `;
  const input = row.querySelector("input");
  const value = row.querySelector(".slider-value");
  const refresh = () => {
    const stored = getConfig()[def.key];
    input.value = stored * scale;
    value.textContent = def.fmt(stored * scale);
  };
  input.addEventListener("input", () => {
    const displayed = Number(input.value);
    value.textContent = def.fmt(displayed);
    setParam(def.key, displayed / scale);
  });
  container.appendChild(row);
  widgets.push({ refresh });
}

function buildSegmented(def, container) {
  const picker = document.createElement("div");
  picker.className = "seg-picker";
  const buttons = def.options.map((option) => {
    const btn = document.createElement("button");
    btn.className = "seg-btn";
    btn.textContent = option;
    btn.addEventListener("click", () => setParam(def.key, option));
    picker.appendChild(btn);
    return btn;
  });
  const refresh = () => {
    const stored = getConfig()[def.key];
    for (const [i, btn] of buttons.entries()) {
      btn.classList.toggle("active", def.options[i] === stored);
    }
  };
  container.appendChild(labeledRow(def, picker));
  widgets.push({ refresh });
}

function buildCheckbox(def, container) {
  const row = document.createElement("label");
  row.className = "checkbox-row";
  const input = document.createElement("input");
  input.type = "checkbox";
  row.appendChild(input);
  row.appendChild(document.createTextNode(def.label));
  const refresh = () => {
    input.checked = getConfig()[def.key];
  };
  input.addEventListener("change", () => setParam(def.key, input.checked));
  container.appendChild(row);
  if (def.hint) container.appendChild(hintEl(def.hint));
  widgets.push({ refresh });
}

function buildSelect(def, container) {
  const select = document.createElement("select");
  for (const [value, label] of def.options) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = label;
    select.appendChild(option);
  }
  const refresh = () => {
    select.value = getConfig()[def.key];
  };
  select.addEventListener("change", () => setParam(def.key, select.value));
  const row = document.createElement("div");
  row.className = "select-row";
  row.appendChild(select);
  container.appendChild(labeledRow(def, row));
  widgets.push({ refresh });
}

function labeledRow(def, el) {
  const wrap = document.createElement("div");
  const header = document.createElement("div");
  header.className = "slider-header";
  header.innerHTML = `<span class="slider-name">${def.label}</span>`;
  wrap.appendChild(header);
  wrap.appendChild(el);
  if (def.hint) wrap.appendChild(hintEl(def.hint));
  return wrap;
}

function hintEl(text) {
  const hint = document.createElement("div");
  hint.className = "slider-hint";
  hint.textContent = text;
  return hint;
}

function buildPresetPills(regions) {
  const regionPills = document.getElementById("region-pills");
  for (const region of regions) {
    const btn = document.createElement("button");
    btn.className = `preset-btn${region.available ? "" : " disabled"}`;
    btn.textContent = region.id.toUpperCase();
    if (!region.available) {
      btn.disabled = true;
      btn.title = "Coming in a follow-up — values pending research";
    } else {
      btn.addEventListener("click", () => {
        for (const el of regionPills.querySelectorAll(".preset-btn")) el.classList.remove("active");
        btn.classList.add("active");
        applyPreset({ ...region.typical, ...region.taxPrimitives });
        syncInputs();
      });
    }
    regionPills.appendChild(btn);
  }
  regionPills.querySelector(".preset-btn:not(.disabled)")?.classList.add("active");

  const outlookPills = document.getElementById("outlook-pills");
  for (const [name, preset] of Object.entries(OUTLOOK_PRESETS)) {
    const btn = document.createElement("button");
    btn.className = "preset-btn";
    btn.textContent = name[0].toUpperCase() + name.slice(1);
    btn.addEventListener("click", () => {
      for (const el of outlookPills.querySelectorAll(".preset-btn")) el.classList.remove("active");
      btn.classList.add("active");
      applyPreset(preset);
      syncInputs();
    });
    outlookPills.appendChild(btn);
  }
}

export function initInputs(regions) {
  for (const def of INPUT_DEFS) {
    const container = document.getElementById(SECTION_CONTAINERS[def.section]);
    if (def.type === "segmented") buildSegmented(def, container);
    else if (def.type === "checkbox") buildCheckbox(def, container);
    else if (def.type === "select") buildSelect(def, container);
    else buildSlider(def, container);
  }
  buildPresetPills(regions);
  syncInputs();
}

export function syncInputs() {
  for (const widget of widgets) widget.refresh();
}
```

- [ ] **Step 2: Verify in browser**

Serve and check: all 6 core sliders + term segmented control + 3 assumption sliders render with current values; dragging a slider updates its green value live; `⚙ Advanced` opens the drawer with all 15 advanced controls; Region pill US active, FR/DE/NL/UK greyed; Outlook pills set the trio.

- [ ] **Step 3: Commit**

```bash
git add src/simulator/static/js/inputs.js
git commit -m "feat: input system with presets and advanced drawer"
```

---

### Task 11: `js/charts.js`

**Files:**
- Create: `src/simulator/static/js/charts.js`

**Interfaces:**
- Consumes: Plotly.js global `Plotly` (CDN), Task 2/3 payload shapes.
- Produces: `renderDecisionChart(el, series, breakevenYear)`, `renderFanChart(el, mc)`, `renderTornadoChart(el, tornado)`, `renderOutflowChart(el, series)`, `renderBreakdownChart(el, payload, cfg)`.

- [ ] **Step 1: Write `charts.js`**

```js
// Plotly.js builders — one shared GitHub-dark theme. Buy #f0883e,
// Rent #58a6ff; bands/neutrals muted; direct line labels, no legends.

const BUY = "#f0883e";
const RENT = "#58a6ff";
const MUTED = "#8b949e";
const GRID = "rgba(48,54,61,0.6)";

const PLOT_CONFIG = { displayModeBar: false, responsive: true };

function baseLayout(xTitle) {
  return {
    paper_bgcolor: "#161b22",
    plot_bgcolor: "#161b22",
    font: { color: MUTED, family: "-apple-system, 'Segoe UI', sans-serif", size: 12 },
    margin: { t: 16, r: 64, b: 40, l: 56 },
    showlegend: false,
    hovermode: "x unified",
    xaxis: { title: { text: xTitle }, gridcolor: GRID, zerolinecolor: "#30363d" },
    yaxis: { gridcolor: GRID, zerolinecolor: "#30363d", tickformat: "$~s" },
  };
}

function strategyTraces(x, buyY, rentY) {
  return [
    { x, y: buyY, mode: "lines", line: { color: BUY, width: 2 }, name: "Buy", hovertemplate: "Buy %{y:$,.0f}<extra></extra>" },
    { x, y: rentY, mode: "lines", line: { color: RENT, width: 2 }, name: "Rent", hovertemplate: "Rent %{y:$,.0f}<extra></extra>" },
  ];
}

function endLabelAnnotations(x, buyY, rentY) {
  return [
    { x: x.at(-1), y: buyY.at(-1), text: "Buy", font: { color: BUY, size: 12 }, showarrow: false, xanchor: "left", xshift: 6 },
    { x: x.at(-1), y: rentY.at(-1), text: "Rent", font: { color: RENT, size: 12 }, showarrow: false, xanchor: "left", xshift: 6 },
  ];
}

export function renderDecisionChart(el, series, breakevenYear) {
  const x = series.year;
  const layout = baseLayout("Years");
  layout.annotations = endLabelAnnotations(x, series.netBuy, series.netRent);
  if (breakevenYear != null) {
    layout.shapes = [
      { type: "line", x0: breakevenYear, x1: breakevenYear, yref: "paper", y0: 0, y1: 1, line: { color: "#484f58", width: 1, dash: "dash" } },
    ];
    layout.annotations.push({
      x: breakevenYear, yref: "paper", y: 1, yanchor: "bottom", xanchor: "left", xshift: 4,
      text: `breakeven ${breakevenYear.toFixed(1)}y`, font: { color: MUTED, size: 11 }, showarrow: false,
    });
  }
  Plotly.react(el, strategyTraces(x, series.netBuy, series.netRent), layout, PLOT_CONFIG);
}

export function renderFanChart(el, mc) {
  const x = mc.yearAxis;
  const row = Object.fromEntries(mc.percentileLevels.map((level, i) => [level, mc.differencePercentiles[i]]));
  const traces = [
    { x, y: row[95], mode: "lines", line: { width: 0 }, hoverinfo: "skip", showlegend: false },
    { x, y: row[5], mode: "lines", line: { width: 0 }, fill: "tonexty", fillcolor: "rgba(139,148,158,0.14)", hoverinfo: "skip", showlegend: false },
    { x, y: row[75], mode: "lines", line: { width: 0 }, hoverinfo: "skip", showlegend: false },
    { x, y: row[25], mode: "lines", line: { width: 0 }, fill: "tonexty", fillcolor: "rgba(139,148,158,0.24)", hoverinfo: "skip", showlegend: false },
    { x, y: row[50], mode: "lines", line: { color: "#e6edf3", width: 1.5 }, name: "Median", hovertemplate: "Median %{y:$,.0f}<extra></extra>", showlegend: false },
  ];
  const layout = baseLayout("Years");
  layout.yaxis.title = { text: "Buy − Rent" };
  layout.shapes = [
    { type: "line", x0: 0, x1: x.at(-1), y0: 0, y1: 0, line: { color: "#484f58", width: 1, dash: "dash" } },
  ];
  Plotly.react(el, traces, layout, PLOT_CONFIG);
}

export function renderTornadoChart(el, tornado) {
  const params = [...tornado.params].reverse();
  const low = [...tornado.low].reverse();
  const high = [...tornado.high].reverse();
  const base = tornado.base;
  const traces = [
    { type: "bar", orientation: "h", y: params, x: low, base, marker: { color: MUTED }, hovertemplate: "%{y} lower: %{x:$,.0f}<extra></extra>" },
    { type: "bar", orientation: "h", y: params, x: high, base, marker: { color: RENT }, hovertemplate: "%{y} higher: %{x:$,.0f}<extra></extra>" },
  ];
  const layout = baseLayout("Impact on Buy − Rent difference");
  layout.barmode = "overlay";
  layout.shapes = [
    { type: "line", x0: base, x1: base, yref: "paper", y0: 0, y1: 1, line: { color: "#e6edf3", width: 1 } },
  ];
  Plotly.react(el, traces, layout, PLOT_CONFIG);
}

export function renderOutflowChart(el, series) {
  const x = series.year;
  const layout = baseLayout("Years");
  layout.annotations = endLabelAnnotations(x, series.outflowBuy, series.outflowRent);
  Plotly.react(el, strategyTraces(x, series.outflowBuy, series.outflowRent), layout, PLOT_CONFIG);
}

export function renderBreakdownChart(el, payload, cfg) {
  const nMonths = cfg.horizonYears * 12;
  const loan = cfg.propertyPrice * (1 - cfg.downPaymentPct / 100);
  const finalBalance = payload.series.mortgageBalance.at(-1);
  const interestPaid = payload.monthlyMortgagePayment * nMonths - (loan - finalBalance);
  const t = payload.totals;
  const items = [
    ["Mortgage interest", interestPaid],
    ["Property tax", t.propertyTaxPaid],
    ["Maintenance", t.maintenancePaid],
    ["Insurance", t.insurancePaid],
    ["Buyer closing", t.closingCostsBuyer],
    ["Seller closing", t.closingCostsSeller],
  ].sort((a, b) => b[1] - a[1]);
  const labels = [...items.map((i) => i[0]), "Tax savings (offset)"];
  const values = [...items.map((i) => i[1]), -t.taxSavings];
  const traces = [
    {
      type: "bar", orientation: "h",
      y: labels.reverse(), x: values.reverse(),
      marker: { color: values.map((v) => (v < 0 ? "#7ee787" : MUTED)).reverse() },
      hovertemplate: "%{y}: %{x:$,.0f}<extra></extra>",
    },
  ];
  const layout = baseLayout(`Total over ${cfg.horizonYears} years`);
  Plotly.react(el, traces, layout, PLOT_CONFIG);
}
```

- [ ] **Step 2: Commit**

```bash
git add src/simulator/static/js/charts.js
git commit -m "feat: Plotly.js chart builders with shared dark theme"
```

---

### Task 12: `js/results.js`

**Files:**
- Create: `src/simulator/static/js/results.js`

**Interfaces:**
- Consumes: `charts.js` (Task 11), `format.js` (Task 9), Task 2/3 payload shapes.
- Produces: `renderSimulate(data, cfg)`, `renderMonteCarlo(mc, winner)`, `downloadCsv(series)`.

- [ ] **Step 1: Write `results.js`**

```js
// Verdict hero, stat cards, numbers table, CSV export. The verdict,
// breakeven, and confidence all read from the same API payloads —
// never computed client-side (CONTEXT.md: "Verdict").

import {
  renderBreakdownChart,
  renderDecisionChart,
  renderFanChart,
  renderOutflowChart,
  renderTornadoChart,
} from "./charts.js";
import { fmtMoney } from "./format.js";

function renderVerdict(data) {
  const { winner, difference, horizonYears } = data.verdict;
  const name = winner === "buy" ? "Buying" : "Renting";
  document.getElementById("verdict-line").innerHTML =
    `${name} leaves you <span class="amount-${winner}">~${fmtMoney(Math.abs(difference))}</span> wealthier if you sell after ${horizonYears} years`;

  const breakevenEl = document.getElementById("verdict-breakeven");
  const b = data.breakevenYear;
  breakevenEl.textContent =
    b != null
      ? `${name} pulls ahead if you stay ≥ ${Math.ceil(b)} years`
      : `No breakeven within ${horizonYears} years`;
  document.getElementById("verdict-confidence").textContent = "";
}

function renderStats(data) {
  document.getElementById("stat-buy").textContent = fmtMoney(data.series.netBuy.at(-1));
  document.getElementById("stat-rent").textContent = fmtMoney(data.series.netRent.at(-1));
  document.getElementById("stat-cost-buy").textContent = `${fmtMoney(data.monthlyCostBuyYear1)}/mo`;
  document.getElementById("stat-cost-rent").textContent = `${fmtMoney(data.monthlyCostRentYear1)}/mo`;
}

const TABLE_COLUMNS = [
  ["Year", "year", (v) => v.toFixed(0)],
  ["Home value", "homeValue", fmtMoney],
  ["Portfolio (rent)", "equityValue", fmtMoney],
  ["Portfolio (buy)", "buyPortfolioValue", fmtMoney],
  ["Mortgage balance", "mortgageBalance", fmtMoney],
  ["Outflow (buy)", "outflowBuy", fmtMoney],
  ["Outflow (rent)", "outflowRent", fmtMoney],
  ["Net (buy)", "netBuy", fmtMoney],
  ["Net (rent)", "netRent", fmtMoney],
];

function renderTable(series) {
  // Yearly rows for readability; CSV export (below) keeps every month.
  const rows = series.year
    .map((year, i) => ({ year, i }))
    .filter(({ i }) => i % 12 === 0)
    .map(({ i }) => `<tr>${TABLE_COLUMNS.map(([, key, fmt]) => `<td>${fmt(series[key][i])}</td>`).join("")}</tr>`)
    .join("");
  document.getElementById("data-table").innerHTML =
    `<table><thead><tr>${TABLE_COLUMNS.map(([label]) => `<th>${label}</th>`).join("")}</tr></thead><tbody>${rows}</tbody></table>`;
}

export function downloadCsv(series) {
  const cols = [
    ["Year", series.year],
    ["Home_Value", series.homeValue],
    ["Equity_Value", series.equityValue],
    ["Buy_Portfolio_Value", series.buyPortfolioValue],
    ["Mortgage_Balance", series.mortgageBalance],
    ["Outflow_Buy", series.outflowBuy],
    ["Outflow_Rent", series.outflowRent],
    ["Cash_Committed", series.cashCommitted],
    ["Net_Buy", series.netBuy],
    ["Net_Rent", series.netRent],
  ];
  const lines = [
    cols.map(([name]) => name).join(","),
    ...series.year.map((_, i) => cols.map(([, arr]) => arr[i]).join(",")),
  ];
  const url = URL.createObjectURL(new Blob([lines.join("\n")], { type: "text/csv" }));
  const link = Object.assign(document.createElement("a"), { href: url, download: "simulation_results.csv" });
  link.click();
  URL.revokeObjectURL(url);
}

export function renderSimulate(data, cfg) {
  renderVerdict(data);
  renderStats(data);
  renderDecisionChart(document.getElementById("decision-chart"), data.series, data.breakevenYear);
  renderOutflowChart(document.getElementById("outflow-chart"), data.series);
  renderBreakdownChart(document.getElementById("breakdown-chart"), data, cfg);
  renderTable(data.series);
  document.getElementById("csv-btn").onclick = () => downloadCsv(data.series);
}

export function renderMonteCarlo(mc, winner) {
  const pct = winner === "buy" ? mc.buyWinsPct : 100 - mc.buyWinsPct;
  const name = winner === "buy" ? "Buying" : "Renting";
  document.getElementById("verdict-confidence").textContent =
    ` · ${name} wins in ${pct.toFixed(0)}% of simulated futures`;
  renderFanChart(document.getElementById("fan-chart"), mc);
  renderTornadoChart(document.getElementById("tornado-chart"), mc.tornado);
}
```

- [ ] **Step 2: Commit**

```bash
git add src/simulator/static/js/results.js
git commit -m "feat: verdict hero, stats, table, and CSV rendering"
```

---

### Task 13: `js/ui.js` + `js/main.js` + end-to-end smoke

**Files:**
- Create: `src/simulator/static/js/ui.js`
- Create: `src/simulator/static/js/main.js`

**Interfaces:**
- Consumes: all previous JS modules; DOM ids from Task 7.
- Produces: `initUi()`, `showError(msg)`, `hideError()`, `setLoading(on)`; `main.js` bootstrap (no exports).

- [ ] **Step 1: Write `ui.js`**

```js
// Chrome behavior: drawer, overlays, error banner, loading indicator.

export function initUi() {
  const panel = document.getElementById("advanced-panel");
  document.getElementById("advanced-btn").addEventListener("click", () => panel.classList.toggle("visible"));
  document.getElementById("advanced-close").addEventListener("click", () => panel.classList.remove("visible"));

  const guide = document.getElementById("guide-overlay");
  document.getElementById("guide-btn").addEventListener("click", () => guide.classList.remove("hidden"));
  guide.querySelector(".modal-close").addEventListener("click", () => guide.classList.add("hidden"));
  guide.addEventListener("click", (e) => {
    if (e.target === guide) guide.classList.add("hidden");
  });
  for (const header of guide.querySelectorAll(".guide-section-header")) {
    header.addEventListener("click", () => header.parentElement.classList.toggle("open"));
  }

  const welcome = document.getElementById("welcome-overlay");
  if (localStorage.getItem("rvb-welcomed")) welcome.classList.add("hidden");
  const dismiss = () => {
    localStorage.setItem("rvb-welcomed", "1");
    welcome.classList.add("hidden");
  };
  document.getElementById("welcome-start").addEventListener("click", dismiss);
  document.getElementById("welcome-close").addEventListener("click", dismiss);

  document.getElementById("inputs-btn").addEventListener("click", () => {
    document.getElementById("input-panel").classList.toggle("visible");
  });
}

export function showError(message) {
  const banner = document.getElementById("error-banner");
  banner.querySelector("span").textContent = message;
  banner.classList.add("visible");
}

export function hideError() {
  document.getElementById("error-banner").classList.remove("visible");
}

export function setLoading(on) {
  document.getElementById("results-spinner").style.display = on ? "flex" : "none";
}
```

- [ ] **Step 2: Write `main.js`**

```js
// Bootstrap and orchestration: config changes schedule a fast
// deterministic run and a slower Monte Carlo run, each debounced,
// aborted when superseded, and cached by config hash.

import { getRegions, postMonteCarlo, postSimulate } from "./api.js";
import { initInputs, syncInputs } from "./inputs.js";
import { renderMonteCarlo, renderSimulate } from "./results.js";
import {
  configHash,
  debounce,
  getCached,
  getConfig,
  onConfigChange,
  readUrl,
  setCached,
} from "./state.js";
import { hideError, initUi, setLoading, showError } from "./ui.js";

let simAbort = null;
let mcAbort = null;
let lastWinner = "rent";

async function runSimulate() {
  const cfg = getConfig();
  const hash = configHash(cfg);
  const cached = getCached("simulate", hash);
  if (cached) {
    lastWinner = cached.verdict.winner;
    renderSimulate(cached, cfg);
    return;
  }
  simAbort?.abort();
  simAbort = new AbortController();
  setLoading(true);
  try {
    const data = await postSimulate(cfg, simAbort.signal);
    setCached("simulate", hash, data);
    lastWinner = data.verdict.winner;
    renderSimulate(data, cfg);
    hideError();
  } catch (err) {
    if (err.name !== "AbortError") showError(`Simulation failed: ${err.message}`);
  } finally {
    setLoading(false);
  }
}

async function runMonteCarlo() {
  const cfg = getConfig();
  const hash = configHash(cfg);
  const cached = getCached("monteCarlo", hash);
  if (cached) {
    renderMonteCarlo(cached, lastWinner);
    return;
  }
  mcAbort?.abort();
  mcAbort = new AbortController();
  try {
    const data = await postMonteCarlo(cfg, mcAbort.signal);
    setCached("monteCarlo", hash, data);
    renderMonteCarlo(data, lastWinner);
  } catch (err) {
    if (err.name !== "AbortError") showError(`Monte Carlo failed: ${err.message}`);
  }
}

const scheduleSimulate = debounce(runSimulate, 300);
const scheduleMonteCarlo = debounce(runMonteCarlo, 600);

async function init() {
  readUrl();
  initUi();
  let regions;
  try {
    regions = await getRegions();
  } catch (err) {
    showError(`Could not load regions: ${err.message}`);
    regions = [{ id: "us", label: "United States", available: true, typical: {}, taxPrimitives: {} }];
  }
  initInputs(regions);
  syncInputs();
  onConfigChange(() => {
    scheduleSimulate();
    scheduleMonteCarlo();
  });
  await runSimulate();
  runMonteCarlo();
}

init();
```

- [ ] **Step 3: End-to-end smoke checklist**

Serve: `uv run uvicorn simulator.server:app --port 8010` → `http://localhost:8010`

- Initial load: welcome modal → dismiss → verdict hero filled, decision chart drawn with breakeven marker, stats populated; confidence subline + fan/tornado appear shortly after (MC is slower).
- Drag the mortgage-rate slider: URL updates live; charts re-render after ~300ms without page reload; no stale flash.
- Toggle to a previously used config: instant render (cache hit).
- Copy the URL into a new tab: identical config and verdict (share URLs).
- Click FR: disabled. Click Optimistic: assumptions trio updates.
- Open Advanced, change levy cap: results update; drawer slides.
- Open Guide: accordions expand with ported prose.
- Kill the server (Ctrl+C) and drag a slider: red error banner appears; restart + Reload recovers.
- Narrow the window <900px: `Inputs` button appears, panel slides from the left.
- `The numbers` expands a yearly table; Download CSV produces `simulation_results.csv` with monthly rows.

- [ ] **Step 4: Commit**

```bash
git add src/simulator/static/js/ui.js src/simulator/static/js/main.js
git commit -m "feat: frontend orchestration with debounced API runs"
```

---

## Phase 4 — Cutover

### Task 14: Delete Streamlit, rewire CLI and packaging

**Files:**
- Delete: `src/simulator/app.py`, `src/simulator/explainers.py`, `src/simulator/visualization.py`, `src/simulator/mc_visualization.py`, `tests/test_explainers.py`, `tests/test_mc_visualization.py`
- Modify: `src/simulator/cli.py`, `src/simulator/__init__.py`, `pyproject.toml`

**Interfaces:**
- Consumes: everything before it.
- Produces: `cli.main()` → uvicorn serving `simulator.server:app` on `$PORT` (default 8000).

- [ ] **Step 1: Delete the Streamlit surface**

```bash
git rm src/simulator/app.py src/simulator/explainers.py src/simulator/visualization.py src/simulator/mc_visualization.py tests/test_explainers.py tests/test_mc_visualization.py
```

- [ ] **Step 2: Rewrite `cli.py`**

```python
"""CLI entry point for the rent-vs-buy simulator.

Serves the web app locally via uvicorn.

Examples
--------
After installing the package:

.. code-block:: bash

    rent-vs-buy          # http://localhost:8000
    PORT=9000 rent-vs-buy
"""

import os


def main() -> None:
    """Launch the web app on ``$PORT`` (default 8000)."""
    import uvicorn

    uvicorn.run(
        "simulator.server:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "8000")),
    )
```

- [ ] **Step 3: Update `pyproject.toml`**

Dependencies become:

```toml
dependencies = [
    "numpy>=1.26.0",
    "numpy-financial>=1.0.0",
    "pandas>=2.1.0",
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",
]
```

Coverage omit list becomes (the deleted modules' entries removed; `cli.py` stays omitted as a thin launcher):

```toml
omit = [
    "*/cli.py",
]
```

Then: `uv sync`

- [ ] **Step 4: Update `src/simulator/__init__.py` docstring**

Replace `data models, calculation engine, and visualization tools.` with `data models, calculation engine, and a FastAPI web server.`

- [ ] **Step 5: Full verification**

```bash
uv run pytest tests/ -v --cov --cov-report=term   # all pass, ≥80%
uv run ruff check src/ tests/
uv run ruff format src/ tests/
uv run ty check src/
```

Expected: all clean; no import errors referencing deleted modules.

- [ ] **Step 6: Verify the wheel ships the static frontend**

```bash
uv build
unzip -l dist/rent_vs_buy_simulator-1.0.0-py3-none-any.whl | grep static/
```

Expected: `simulator/static/index.html`, `simulator/static/css/style.css`, and all seven `simulator/static/js/*.js` files listed.

- [ ] **Step 7: Smoke the installed CLI path**

```bash
uv run rent-vs-buy & sleep 3
curl -s http://localhost:8000/api/health   # {"status":"ok"}
kill %1
```

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "feat: cut over from Streamlit to FastAPI static frontend"
```

---

### Task 15: Docker + documentation + final checklist

**Files:**
- Modify: `Dockerfile`, `Dockerfile.local`, `docker-compose.yml`, `README.md`, `CLAUDE.md`, `docs/adr/0006-stay-on-streamlit-for-redesign.md`, `docs/redesign-spec.md`
- Create: `docs/adr/0008-fastapi-static-frontend.md`

- [ ] **Step 1: Rewrite `Dockerfile`**

```dockerfile
FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Copy dependency metadata first (for layer caching)
COPY pyproject.toml uv.lock README.md LICENSE ./

# Install dependencies only (cached until pyproject.toml or uv.lock change)
RUN uv sync --frozen --no-install-project --no-dev

# Copy source and install the local package
COPY src/ ./src/
RUN uv sync --frozen --no-dev

ENV PORT=8000
EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT}/api/health')" || exit 1

CMD /app/.venv/bin/uvicorn simulator.server:app --host 0.0.0.0 --port ${PORT}
```

(The chromium install for Kaleido is gone with the Streamlit stack.)

- [ ] **Step 2: Rewrite `Dockerfile.local`**

```dockerfile
FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Copy dependency metadata first (for layer caching)
COPY pyproject.toml uv.lock README.md LICENSE ./

# Install dependencies only (cached until pyproject.toml or uv.lock change)
RUN uv sync --frozen --no-install-project --no-dev

# Copy source and install the local package
COPY src/ ./src/
RUN uv sync --frozen --no-dev

ENV PORT=8000
EXPOSE 8000

CMD /app/.venv/bin/uvicorn simulator.server:app --host 0.0.0.0 --port ${PORT}
```

- [ ] **Step 3: Update `docker-compose.yml`**

```yaml
services:
  app:
    build:
      context: .
      dockerfile: Dockerfile.local
    ports:
      - "8000:8000"
    container_name: rent-vs-buy-simulator
```

- [ ] **Step 4: Update `README.md`**

- In Features: replace `Four interactive Plotly charts with breakeven analysis` with `Interactive Plotly.js charts in a dark GitHub-style UI — Net Value decision chart, uncertainty fan, sensitivity tornado, and cash-flow views`, and replace `Quick presets for common scenarios (High Interest, Bull Market, Conservative, First-Time Buyer)` with `Market-outlook presets and region-based tax defaults (US; more regions coming)`.
- In "From PyPI": after `rent-vs-buy` add `# Open http://localhost:8000`.
- In "From Source": replace `streamlit run src/simulator/app.py` with:

  ```bash
  uv run uvicorn simulator.server:app --reload
  # Open http://localhost:8000
  ```

- In Docker section: `# Open http://localhost:8501` → `# Open http://localhost:8000`; `docker run -p 8501:8501` → `docker run -p 8000:8000`.

- [ ] **Step 5: Update `CLAUDE.md`**

- "What This Is" paragraph → `A FastAPI + static JavaScript web app that compares buying property vs. renting and investing in equities. Users configure financial parameters in a dark GitHub-style UI (the same visual system as the author's WebGPU apps) and see Plotly.js charts comparing two strategies: Buy and Rent & Invest. The simulation engine is Python/NumPy behind a JSON API.`
- Run command → `uv run uvicorn simulator.server:app --reload` (app at `http://localhost:8000`). Add type check: `uv run ty check src/`.
- Data flow → `Browser (src/simulator/static/js) → FastAPI (src/simulator/server.py) → api.py → SimulationConfig (models.py) → calculate_scenarios (engine.py) / run_monte_carlo (monte_carlo.py) → JSON → Plotly.js`.
- File bullets: remove `app.py`/`visualization.py`/`scenario_manager.py`/`utils.py`; add `server.py` (FastAPI app + static mount), `api.py` (camelCase wire codec + payload serialization), `regions.py` (region preset bundles as data), `static/` (hand-rolled frontend: `index.html`, `css/style.css`, `js/` ES modules, Plotly.js via CDN).

- [ ] **Step 6: Supersede ADR-0006, write ADR-0008**

In `docs/adr/0006-stay-on-streamlit-for-redesign.md`, insert directly under the title:

```markdown
**Status:** Superseded by [ADR-0008](0008-fastapi-static-frontend.md) (2026-07-17) — the deferred client-side path arrived, in a different shape than predicted (Python engine behind an API, not a TS/Pyodide port).
```

Create `docs/adr/0008-fastapi-static-frontend.md`:

```markdown
# The frontend migrates from Streamlit to a FastAPI + static JavaScript stack

The Streamlit UI was the last pre-redesign surface: clunky rerun-everything interactions, no shareable URLs, and a look that diverged from the author's other public apps (webgpu-fluid-solver, webgpu-gray-scott), which share a hand-rolled GitHub-dark static stack. With the engine model stable after the Phase 1 rewrite (ADRs 0001–0005), the porting risk ADR-0006 cited is gone. The frontend is now a static ES-module app (Plotly.js via CDN) served by FastAPI, calling a JSON API that wraps the unchanged Python engine; Streamlit, Kaleido, and Python-Plotly leave the dependency tree. The page implements the redesign spec's narrative (verdict hero → decision chart → confidence → money flows → numbers) in the GitHub-dark token system with Buy #f0883e / Rent #58a6ff.

## Considered Options

- Port the engine to TypeScript (fully client-side): rejected — the tested NumPy engine would need re-implementation and re-validation, and the PyPI package would lose its purpose.
- Pyodide (Python engine in the browser): rejected — multi-MB WASM/NumPy first load and an exotic toolchain for zero correctness gain.
- Keep Streamlit and re-theme: rejected — the interaction ceiling (full-page reruns, widget model) was the motivating problem.

## Consequences

- ADR-0006 is superseded; the redesign spec §4 light-editorial theme is replaced by the dark token system, and §5's "recorded future path" is closed in a shape it did not predict (Python stays server-side).
- The `rent-vs-buy` CLI and Docker images serve uvicorn on port 8000 (was Streamlit on 8501); Coolify needs only the port change.
- The verdict, breakeven, and confidence are computed only server-side from the same Net Value series — the ADR-0001 invariant now extends across the wire by construction.
- Share URLs replace save/compare; the no-storage privacy stance is preserved.
```

- [ ] **Step 7: Amend `docs/redesign-spec.md`**

Under the `## 4. Visual system (light theme)` heading, insert:

```markdown
> **Superseded 2026-07-17** by [frontend-migration-design.md](frontend-migration-design.md) §4: the visual system ships as the GitHub-dark token set of the author's other apps (single dark theme, not light editorial), with Buy `#f0883e` / Rent `#58a6ff`.
```

Replace the body of `## 5. Stack (ADR-0006)` (the paragraph beginning "Ships on Streamlit") with:

```markdown
Ships as FastAPI + static ES-module frontend with Plotly.js (ADR-0008, which supersedes ADR-0006). The engine remains Python server-side; a TS/Pyodide client port is no longer the recorded path.
```

- [ ] **Step 8: Final verification + commit**

```bash
uv run pytest tests/ -v --cov --cov-report=term
uv run ruff check src/ tests/
uv run ty check src/
docker build -t rent-vs-buy-simulator . && docker run --rm -d -p 8012:8000 --name rvb-check rent-vs-buy-simulator
sleep 5 && curl -s http://localhost:8012/api/health   # {"status":"ok"}
docker stop rvb-check
```

Re-run the Task 13 Step 3 smoke checklist against `uv run uvicorn simulator.server:app --port 8010`. CI workflows (`test.yml`, `lint.yml`) need no changes — they run pytest and ruff generically. CONTEXT.md was reviewed and needs no edit: it describes product language only, with no stack references.

```bash
git add -A
git commit -m "chore: docker, docs, and ADR-0008 for the frontend migration"
```

---

## Done-when

- `uv run pytest tests/ --cov --cov-report=term` green at ≥80% with `test_api.py` covering the new server layer
- `uv run ruff check src/ tests/ && uv run ty check src/` clean
- App serves on `:8000` via uvicorn, CLI, and Docker; full smoke checklist passes
- No `streamlit`/`kaleido`/Python-`plotly` anywhere in the dependency tree; no references to deleted modules
- Spec satisfied: decisions 1–7 of [frontend-migration-design.md](frontend-migration-design.md) all observable in the running app
