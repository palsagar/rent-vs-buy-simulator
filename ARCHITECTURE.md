# Real Estate vs. Equity Simulator - Data Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                        USER INPUT (Streamlit)                       │
│  • Property Price, Down Payment %, Duration                         │
│  • Mortgage Rate, Property Appreciation                             │
│  • Monthly Rent, Equity Growth, Rent Inflation                      │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      SimulationConfig (dataclass)                   │
│  ✓ Type-safe parameter storage                                      │
│  ✓ Input validation                                                 │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   calculate_scenarios() [engine.py]                 │
│                                                                      │
│  Vectorized NumPy Calculations (Monthly Granularity):               │
│                                                                      │
│  SCENARIO A: BUY                      SCENARIO B: RENT              │
│  ─────────────────                    ───────────────────           │
│  • Down Payment = Price × %           • Initial Investment = D      │
│  • Loan = Price - Down                • Portfolio = D × (1+e)^t     │
│  • PMT = npf.pmt(r, n, Loan)          • Rent Outflow = Σ Rent_t    │
│  • Home Value = P × (1+c)^t           • Net = Portfolio - Rent     │
│  • Outflow = D + PMT × months                                       │
│  • Mortgage Balance = pv(r,n-t,PMT)                                 │
│  • Net = Home - Outflow                                             │
│                                                                      │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   SimulationResults (dataclass)                     │
│                                                                      │
│  • data: pd.DataFrame (time-series)                                 │
│    ├─ Month, Year                                                   │
│    ├─ Home_Value, Equity_Value                                      │
│    ├─ Mortgage_Balance                                              │
│    ├─ Outflow_Buy, Outflow_Rent                                     │
│    └─ Net_Buy, Net_Rent                                             │
│                                                                      │
│  • final_net_buy, final_net_rent                                    │
│  • final_difference                                                 │
│  • breakeven_year (if exists)                                       │
│                                                                      │
└───────────────┬──────────────────┬──────────────────┬───────────────┘
                │                  │                  │
                ▼                  ▼                  ▼
┌───────────────────┐  ┌──────────────────┐  ┌──────────────────────┐
│ Asset Growth      │  │ Cumulative       │  │ Net Value Analysis   │
│ Chart             │  │ Outflow Chart    │  │ Chart                │
│ [visualization.py]│  │ [visualization.py]│  │ [visualization.py]  │
│                   │  │                  │  │                      │
│ • Home Value      │  │ • Buy Outflow    │  │ • Net Buy            │
│ • Equity Value    │  │ • Rent Outflow   │  │ • Net Rent           │
│ • Mortgage Debt   │  │                  │  │ • Breakeven Point    │
└─────────┬─────────┘  └────────┬─────────┘  └──────────┬───────────┘
          │                     │                       │
          └─────────────────────┼───────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    STREAMLIT DISPLAY (app.py)                       │
│                                                                      │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │ Summary Metrics                                               │ │
│  │ • Final Net Buy    • Final Net Rent    • Difference           │ │
│  │ • Breakeven Point (if exists)                                 │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │ Tabbed Interface                                              │ │
│  │ [Asset Growth] [Cumulative Costs] [Net Value] [Data Table]   │ │
│  │                                                               │ │
│  │ Interactive Plotly Charts with:                               │ │
│  │ • Hover tooltips • Zoom/Pan • Export • Legend toggle          │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │ Data Export                                                   │ │
│  │ [Download CSV] - Full time-series data                        │ │
│  └───────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

## Key Design Principles

### 1. Separation of Concerns (MVC)
- **Model** (models.py, engine.py): Pure calculation logic, no UI
- **View** (visualization.py): Plotly charts, no business logic
- **Controller** (app.py): User input handling and orchestration

### 2. Performance
- All time-series calculations vectorized with NumPy
- No Python loops for array operations
- Instant calculation even for 40-year simulations

### 3. Data Flow
- Unidirectional: User Input → Config → Calculation → Results → Visualization
- No circular dependencies
- Clear interfaces between components

### 4. Type Safety
- Dataclasses with type hints
- Runtime validation
- Clear contracts between functions

### 5. Testability
- Pure functions (input → output)
- No global state
- Easy to mock and test

## Mathematical Foundation

### Mortgage Payment
```
PMT = P × [r(1+r)^n] / [(1+r)^n - 1]

Where:
  P = Loan amount (property_price - down_payment)
  r = Monthly interest rate (annual_rate / 12)
  n = Total months (duration_years × 12)
```

### Property Value Growth
```
V_p(t) = P_initial × (1 + c/12)^month

Where:
  P_initial = Initial property price
  c = Annual appreciation rate (as decimal)
  month = Time step (0 to duration_years × 12)
```

### Equity Portfolio Growth
```
V_e(t) = D × (1 + e/12)^month

Where:
  D = Initial investment (equals down payment)
  e = Annual equity growth rate (as decimal)
  month = Time step
```

### Net Value (The Decision Metric)
```
Net_Buy = Home_Value - (Down_Payment + Σ Mortgage_Payments)
Net_Rent = Portfolio_Value - Σ Rent_Payments

Winner = argmax(Net_Buy, Net_Rent)
```

## File Dependencies

```
app.py
  ├── imports: simulator.models (SimulationConfig)
  ├── imports: simulator.engine (calculate_scenarios)
  └── imports: simulator.visualization (all chart functions)

simulator/engine.py
  ├── imports: simulator.models (SimulationConfig, SimulationResults)
  ├── imports: numpy
  ├── imports: numpy_financial
  └── imports: pandas

simulator/visualization.py
  ├── imports: pandas
  └── imports: plotly.graph_objects

tests/test_engine.py
  ├── imports: simulator.models
  ├── imports: simulator.engine
  ├── imports: numpy
  └── imports: pytest
```

No circular dependencies! Clean architecture ✓
