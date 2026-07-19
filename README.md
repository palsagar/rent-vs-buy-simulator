# Rent vs. Buy Simulator

[![Tests](https://github.com/palsagar/rent-vs-buy-simulator/actions/workflows/test.yml/badge.svg)](https://github.com/palsagar/rent-vs-buy-simulator/actions/workflows/test.yml)
[![Coverage](https://img.shields.io/codecov/c/github/palsagar/rent-vs-buy-simulator)](https://codecov.io/gh/palsagar/rent-vs-buy-simulator)
[![Linting](https://github.com/palsagar/rent-vs-buy-simulator/actions/workflows/lint.yml/badge.svg)](https://github.com/palsagar/rent-vs-buy-simulator/actions/workflows/lint.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

**[Try the Live App](https://rent-or-buy-sim.com/)**

A financial simulation tool that compares two capital allocation strategies over time:

- **Buy** — Purchase property with a mortgage
- **Rent & Invest** — Rent and invest the down payment (and any monthly surplus) in equities

## Features

- Mortgage amortization, property appreciation, equity growth, closing costs, property tax, insurance, and maintenance
- Tax primitives: mortgage-interest and property-levy deductibility (with a configurable levy cap), a selectable home-sale capital-gains regime, a flat cost-indexed levy and maintenance amount, a fixed buyer-cost component (negative where a transfer tax has a zero-rate band), an occupier-borne-levy flag, and an annual portfolio drag on the lesser of a deemed and actual return
- Interactive Plotly.js charts in a dark GitHub-style UI — Net Value decision chart, uncertainty fan, sensitivity tornado, and cash-flow views
- Market-outlook presets and region-based tax defaults — US, France (Lyon), Germany (Köln), Netherlands and the UK (England & NI), each rendered in its own currency, with a first-time-buyer toggle that withdraws itself above each region's statutory price cap
- Liquidation-based Net Value — a single wealth series, at every year, that drives every chart, the verdict, and Monte Carlo alike (see [FORMULAS.md](FORMULAS.md))
- Cash-flow matching — whichever side is cheaper each month invests the difference in equities
- Independent horizon (when you'd sell) and mortgage term, instead of one combined duration
- Auto-calibrated Monte Carlo uncertainty analysis — no manual parameter tuning required
- Vectorized NumPy engine — no Python loops

## Installation

### From PyPI

```bash
# As a CLI tool (recommended)
uv tool install rent-vs-buy-simulator
rent-vs-buy
# Open http://localhost:8501

# Or as a library
uv pip install rent-vs-buy-simulator
```

### From Source

```bash
git clone https://github.com/palsagar/rent-vs-buy-simulator.git
cd rent-vs-buy-simulator
uv sync
uv run uvicorn simulator.server:app --reload --port 8501
# Open http://localhost:8501
```

### Docker

```bash
# Local development
docker compose up --build
# Open http://localhost:8501

# Production
docker build -t rent-vs-buy-simulator .
docker run -p 8501:8501 rent-vs-buy-simulator
```

The app listens on port **8501** everywhere — matching the prior Streamlit deployment, so an existing Coolify/Traefik route serves the new image without reconfiguration.

In production, run the app behind a reverse proxy (e.g. Coolify/Traefik) that enforces per-IP rate limiting; the app's built-in limits (request body-size cap, bounded Monte Carlo concurrency) are only a dependency-free backstop.

## Library Usage

```python
from simulator import SimulationConfig, calculate_scenarios

config = SimulationConfig(
    horizon_years=10,
    mortgage_term_years=30,
    property_price=500000,
    down_payment_pct=20,
    mortgage_rate_annual=4.5,
    property_appreciation_annual=3.0,
    equity_growth_annual=7.0,
    monthly_rent=2000,
    rent_inflation_rate=0.03,
)

results = calculate_scenarios(config)
print(f"Buy: ${results.final_net_buy:,.0f}")
print(f"Rent & Invest: ${results.final_net_rent:,.0f}")
print(f"Difference: ${results.final_difference:,.0f}")
```

## Contributing

Contributions welcome! Fork the repo, create a feature branch, and open a PR against `main`.

```bash
uv sync
uv run pytest tests/ --cov --cov-report=term   # 80% coverage minimum
uv run ruff check src/ tests/
```

See [FORMULAS.md](FORMULAS.md) for the mathematical reference.

## License

MIT License. See [LICENSE](LICENSE) for details.
