# Rent vs. Buy Simulator

[![Tests](https://github.com/palsagar/rent-vs-buy-simulator/actions/workflows/test.yml/badge.svg)](https://github.com/palsagar/rent-vs-buy-simulator/actions/workflows/test.yml)
[![Coverage](https://img.shields.io/codecov/c/github/palsagar/rent-vs-buy-simulator)](https://codecov.io/gh/palsagar/rent-vs-buy-simulator)
[![Linting](https://github.com/palsagar/rent-vs-buy-simulator/actions/workflows/lint.yml/badge.svg)](https://github.com/palsagar/rent-vs-buy-simulator/actions/workflows/lint.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

**[Try the Live App](https://rent-or-buy-sim.com/)**

A financial simulation tool that compares three capital allocation strategies over time:

- **Buy** — Purchase property with a mortgage
- **Rent & Invest** — Rent and invest the down payment in equities
- **Rent & Invest Savings** — Rent and invest monthly savings (when mortgage > rent)

## Features

- Mortgage amortization, property appreciation, equity growth, closing costs, property tax, insurance, and maintenance
- Tax benefit modeling: mortgage interest deduction, capital gains exclusion (Section 121), SALT cap
- Four interactive Plotly charts with breakeven analysis
- Quick presets for common scenarios (High Interest, Bull Market, Conservative, First-Time Buyer)
- Save, compare, and export up to 5 scenarios side-by-side
- PDF report export with charts and configuration summary
- Monte Carlo uncertainty analysis with stochastic simulation
- Vectorized NumPy engine — no Python loops

## Installation

### From PyPI

```bash
# As a CLI tool (recommended)
uv tool install rent-vs-buy-simulator
rent-vs-buy

# Or as a library
uv pip install rent-vs-buy-simulator
```

### From Source

```bash
git clone https://github.com/palsagar/rent-vs-buy-simulator.git
cd rent-vs-buy-simulator
uv sync
streamlit run src/simulator/app.py
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

## Library Usage

```python
from simulator import SimulationConfig, calculate_scenarios

config = SimulationConfig(
    duration_years=30,
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
