# Real Estate vs. Equity Simulation Engine

[![Tests](https://github.com/palsagar/rent-vs-buy-simulator/actions/workflows/test.yml/badge.svg)](https://github.com/palsagar/rent-vs-buy-simulator/actions/workflows/test.yml)
[![Coverage](https://img.shields.io/codecov/c/github/palsagar/rent-vs-buy-simulator)](https://codecov.io/gh/palsagar/rent-vs-buy-simulator)
[![Linting](https://github.com/palsagar/rent-vs-buy-simulator/actions/workflows/lint.yml/badge.svg)](https://github.com/palsagar/rent-vs-buy-simulator/actions/workflows/lint.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

**[Try the Live App](https://rent-or-buy-sim.com/)**

A financial simulation application that compares three capital allocation strategies over time:

- **Strategy A (Buy):** Purchase property with a mortgage
- **Strategy B (Rent & Invest):** Rent and invest the down payment in equities
- **Strategy C (Rent & Invest Savings):** Rent, keep down payment as cash, and invest monthly savings

## Features

- **Comprehensive Financial Modeling:** Mortgage amortization, property appreciation, equity growth, closing costs, property tax, insurance, and maintenance
- **Tax Benefit Modeling:** Mortgage interest deduction, capital gains exclusion (Section 121), SALT cap, configurable tax bracket
- **Interactive Visualizations:** Four Plotly charts — asset growth, cumulative outflows, net value analysis, and cost breakdown
- **Quick Presets:** 4 built-in scenarios (High Interest Rate, Bull Market, Conservative, First-Time Buyer) for fast configuration
- **Scenario Management:** Save, load, compare, and export up to 5 scenarios side-by-side
- **PDF Report Export:** Downloadable PDF with charts, metrics, and configuration summary
- **Data Table & CSV Export:** Raw simulation data with CSV download for further analysis
- **Three-Way Comparison:** Includes Scenario C for investing monthly savings when mortgage exceeds rent
- **High Performance:** Vectorized NumPy calculations — no Python loops in the engine

## Installation & Usage

Choose the method that best fits your needs:

| Method                | Use Case                      | Requirements |
| --------------------- | ----------------------------- | ------------ |
| **Local Docker**      | Quick trial, no Python needed | Docker       |
| **Python/uv**         | Development, customization    | Python 3.12+ |
| **Production Docker** | Cloud deployment              | Docker       |

### Option 1: Local Docker (Recommended for Quick Start)

The easiest way to run the application locally without installing Python:

1. Make sure Docker is installed and running on your system

2. Run the application:

```bash
docker compose up --build
```

3. Open your browser and navigate to `http://localhost:8501`

4. To stop the application, press `Ctrl+C` and run:

```bash
docker compose down
```

### Option 2: Python/uv (For Development)

Best for developers who want to modify the code or use the simulator as a library.

**Prerequisites:**

- Python 3.12 or higher
- pip or uv package manager

**Setup:**

1. Install `uv` if you haven't already:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. Clone or navigate to the repository:

```bash
cd simulator
```

3. Create virtual environment and install dependencies:

```bash
uv sync
```

This will create a `.venv` directory, install all dependencies, and install the package in editable mode, as shown below :

```bash
uv pip install -e .
```

**Running the Web Application:**

Start the Streamlit application:

```bash
streamlit run src/simulator/app.py
```

The application will open in your browser at `http://localhost:8501`.

### Option 3: Production Docker (For Cloud Deployment)

For deploying to cloud platforms (AWS, GCP, Azure, etc.):

```bash
docker build -t rent-vs-buy-simulator .
docker run -p 8501:8501 rent-vs-buy-simulator
```

The production `Dockerfile` includes additional security flags for public-facing deployments.

### Using as a Library

You can also use the simulation engine programmatically:

```python
from simulator import SimulationConfig, calculate_scenarios

# Configure the simulation
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

# Run the simulation
results = calculate_scenarios(config)

# Access results
print(f"Final net value (Buy): ${results.final_net_buy:,.0f}")
print(f"Final net value (Rent): ${results.final_net_rent:,.0f}")
print(f"Difference: ${results.final_difference:,.0f}")

if results.breakeven_year:
    print(f"Breakeven at: {results.breakeven_year:.1f} years")

# Access Scenario C results (if applicable)
if results.scenario_c_enabled:
    print(f"\nScenario C (Rent + Invest Savings):")
    print(f"Final net value: ${results.final_net_rent_savings:,.0f}")
    if results.breakeven_year_vs_rent_savings:
        print(f"Breakeven vs Buy: {results.breakeven_year_vs_rent_savings:.1f} years")
```

## Project Structure

```
simulator/
├── pyproject.toml                  # Project dependencies
├── README.md                       # This file
├── FORMULAS.md                     # Mathematical reference
├── Dockerfile                      # Production Docker image
├── Dockerfile.local                # Local development Docker image
├── docker-compose.yml              # Docker Compose for local dev
├── src/
│   └── simulator/
│       ├── __init__.py
│       ├── models.py               # Data models (SimulationConfig, SimulationResults)
│       ├── engine.py               # Core calculation engine
│       ├── visualization.py        # Plotly chart functions
│       ├── scenario_manager.py     # Save/load/compare scenarios
│       └── utils.py                # PDF report generation
└── tests/
    ├── test_engine.py              # Engine unit tests
    └── test_closing_costs.py       # Closing cost tests
```

## Running Tests

Execute the test suite using pytest:

```bash
pytest tests/ -v
```

For coverage report:

```bash
pytest tests/ --cov=src/simulator --cov-report=html
```

## Key Parameters

### Common Settings

- **Duration (Years):** Simulation time horizon (10-40 years)

### Scenario A: Buy

- **Property Price:** Initial purchase price
- **Down Payment %:** Down payment as percentage (5-50%)
- **Mortgage Rate:** Annual interest rate (1-10%)
- **Property Appreciation:** Expected annual value increase (0-10%)

### Scenario B: Rent & Invest

- **Monthly Rent:** Rent payment amount
- **Equity Growth (CAGR):** Expected annual investment returns (0-15%)
- **Rent Inflation:** Annual rent increase rate (0-10%)

### Scenario C: Rent & Invest Savings

- **Availability:** Only when mortgage payment > initial rent
- **Strategy:** Keep down payment as cash (0% return) and invest monthly savings (mortgage - rent) at equity CAGR
- **Use Case:** Conservative approach that maintains liquidity while capturing upside from monthly savings

### Advanced Settings

- **Buyer's Closing Costs:** Upfront costs when buying (default 3%)
- **Seller's Closing Costs:** Costs when selling (default 6%)
- **Property Tax Rate:** Annual property tax (default 1.2%)
- **Home Insurance:** Annual insurance premium (default $1,200/yr)
- **Maintenance:** Annual upkeep as % of property value (default 1%)
- **Cost Inflation:** Annual inflation for ongoing costs (default 2.5%)

### Tax Settings

- **Federal Tax Bracket:** Marginal rate for deduction calculations (0-37%)
- **Mortgage Interest Deduction:** Toggle mortgage interest tax deduction
- **Capital Gains Exclusion:** Toggle Section 121 primary residence exclusion
- **Exemption Limit:** $250K (single) or $500K (married filing jointly)
- **SALT Cap:** State and local tax deduction cap (default $10,000)

## Formulas & Methodology

For detailed mathematical formulas, derivations, and methodology used in the simulation engine, see the **[Mathematical Reference (FORMULAS.md)](FORMULAS.md)**.

**Key concepts:**

- Monthly mortgage payment using standard amortization formula
- Compound monthly appreciation for property values and equity portfolios
- Inflation-adjusted rent calculations with geometric series
- Net value comparison: Asset Value - Cumulative Outflows
- Breakeven analysis using linear interpolation
- Scenario C: Monthly savings investment with compounding (see FORMULAS.md for details)

## Assumptions

The model makes several simplifying assumptions for comparison purposes:

- **Constant Growth Rates:** Property appreciation, equity returns, and rent inflation are constant over the simulation period
- **Monthly Granularity:** All calculations compound monthly for accuracy
- **Fixed Mortgage:** Standard amortization with fixed interest rate
- **No Investment Taxes:** Equity portfolio growth in Scenarios B and C is not reduced by capital gains or dividend taxes
- **Full Liquidity:** Assumes assets can be sold/liquidated at market value instantly
- **No Rental Income:** Property is owner-occupied; no rental income is modeled

For a complete discussion of assumptions and limitations, see the [Mathematical Reference](FORMULAS.md).

## Visualization Outputs

The application generates four main charts plus scenario comparison views:

1. **Asset Value Over Time:** Property value, equity portfolio value, remaining mortgage balance, and (when applicable) Scenario C assets
2. **Cumulative Outflows:** Total money spent in each scenario over time
3. **Net Value Analysis:** Asset value minus cumulative outflows for all applicable scenarios, with breakeven markers
4. **Cost Breakdown:** Stacked bar chart showing the composition of buying costs (mortgage, property tax, insurance, maintenance, closing costs)

### Scenario Comparison

When multiple scenarios are saved, additional comparison views are available:

- **Final Net Values:** Bar chart comparing end-of-period outcomes across saved scenarios
- **Net Value Trajectories:** Overlaid line charts showing how scenarios evolve over time
- **Breakeven Points:** Visual comparison of when buying overtakes renting in each scenario
- **Comparison Table:** Side-by-side metrics with CSV export

## Technical Stack

- **NumPy:** Vectorized calculations for performance
- **NumPy Financial:** Mortgage and financial formulas
- **Pandas:** Data manipulation and time-series handling
- **Plotly:** Interactive visualizations
- **Streamlit:** Web application framework
- **fpdf2:** PDF report generation
- **kaleido:** Static chart export for PDF reports
- **Pytest:** Testing framework

## Architecture

The application follows an MVC (Model-View-Controller) pattern:

- **Model** (`models.py`, `engine.py`): Pure calculation logic with NumPy
- **View** (`visualization.py`): Plotly chart generation
- **Controller** (`src/simulator/app.py`): Streamlit UI and user interaction

## Contributing

Contributions are welcome! Here's how to get started:

1. **Fork the repository** and clone your fork locally
2. **Set up the dev environment:**
   ```bash
   uv sync
   ```
3. **Create a feature branch:**
   ```bash
   git checkout -b feat/your-feature
   ```
4. **Make your changes** — follow existing code conventions (type annotations, NumPy-style docstrings, 88-char line length)
5. **Run tests and linting before submitting:**
   ```bash
   uv run pytest tests/ --cov --cov-report=term   # 80% coverage minimum
   uv run ruff check src/ tests/            # lint
   uv run ruff format src/ tests/           # format
   ```
6. **Open a pull request** against `main` with a clear description of your changes

Bug reports, feature requests, and documentation improvements are all appreciated — feel free to open an issue to start a discussion.

## License

This project is provided as-is for educational and analytical purposes.
