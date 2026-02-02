# Real Estate vs. Equity Simulation Engine

A financial simulation application that compares two capital allocation strategies over time:
- **Strategy A (Buy):** Purchase property with a mortgage
- **Strategy B (Rent):** Rent and invest the down payment in equities

## Features

- 🏠 **Comprehensive Financial Modeling:** Accurate mortgage calculations, property appreciation, and investment growth
- 📊 **Interactive Visualizations:** Beautiful Plotly charts with hover details and breakeven analysis
- ⚡ **High Performance:** Vectorized NumPy calculations for fast simulations
- 🎯 **Key Metrics:** Net value analysis, cumulative outflows, and asset growth comparisons
- 📱 **User-Friendly Interface:** Clean Streamlit UI with intuitive parameter controls

## Installation & Usage

Choose the method that best fits your needs:

| Method | Use Case | Requirements |
|--------|----------|--------------|
| **Local Docker** | Quick trial, no Python needed | Docker |
| **Python/uv** | Development, customization | Python 3.12+ |
| **Production Docker** | Cloud deployment | Docker |

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

1. Clone or navigate to the repository:
```bash
cd simulator
```

2. Install dependencies:
```bash
pip install -e .
```

Or if using `uv`:
```bash
uv pip install -e .
```

**Running the Web Application:**

Start the Streamlit application:

```bash
streamlit run app.py
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
```

## Project Structure

```
simulator/
├── app.py                  # Streamlit web application
├── pyproject.toml          # Project dependencies
├── README.md               # This file
├── specs.md                # Technical specifications
├── src/
│   └── simulator/
│       ├── __init__.py
│       ├── models.py       # Data models (SimulationConfig, SimulationResults)
│       ├── engine.py       # Core calculation engine
│       └── visualization.py # Plotly chart functions
└── tests/
    └── test_engine.py      # Unit tests
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

## Formulas & Methodology

For detailed mathematical formulas, derivations, and methodology used in the simulation engine, see the **[Mathematical Reference (FORMULAS.md)](FORMULAS.md)**.

**Key concepts:**
- Monthly mortgage payment using standard amortization formula
- Compound monthly appreciation for property values and equity portfolios
- Inflation-adjusted rent calculations with geometric series
- Net value comparison: Asset Value - Cumulative Outflows
- Breakeven analysis using linear interpolation

## Assumptions

The model makes several simplifying assumptions for comparison purposes:

- **Constant Growth Rates:** Property appreciation, equity returns, and rent inflation are constant
- **Monthly Granularity:** All calculations compound monthly for accuracy
- **Fixed Mortgage:** Standard amortization with fixed interest rate
- **No Transaction Costs:** Excludes closing costs, realtor fees, and moving expenses
- **No Property Costs:** Excludes property taxes, insurance, HOA fees, and maintenance
- **No Tax Effects:** Ignores mortgage interest deduction and capital gains taxes
- **Full Liquidity:** Assumes assets can be sold/liquidated at market value instantly

For a complete discussion of assumptions and limitations, see the [Mathematical Reference](FORMULAS.md).

## Visualization Outputs

The application generates three main charts:

1. **Asset Value Over Time:** Shows property value, equity portfolio value, and remaining mortgage balance
2. **Cumulative Outflows:** Compares total money spent in each scenario
3. **Net Value Analysis:** The "bottom line" showing asset value minus cumulative outflows

## Technical Stack

- **NumPy:** Vectorized calculations for performance
- **NumPy Financial:** Mortgage and financial formulas
- **Pandas:** Data manipulation and time-series handling
- **Plotly:** Interactive visualizations
- **Streamlit:** Web application framework
- **Pytest:** Testing framework

## Architecture

The application follows an MVC (Model-View-Controller) pattern:

- **Model** (`models.py`, `engine.py`): Pure calculation logic with NumPy
- **View** (`visualization.py`): Plotly chart generation
- **Controller** (`app.py`): Streamlit UI and user interaction

## Contributing

Feel free to open issues or submit pull requests for improvements.

## License

This project is provided as-is for educational and analytical purposes.
