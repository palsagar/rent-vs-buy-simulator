# Mathematical Formulas Reference

This document provides detailed mathematical formulas and methodology used in the rent vs. buy simulation engine.

## Time Vector

All calculations use monthly granularity for accuracy:

```
t ∈ {0, 1, 2, ..., n_months} where n_months = duration_years × 12

year = t / 12
```

## Scenario A: Buy Property with Mortgage

### 1. Initial Values

**Down Payment:**

```
D = P_property × (down_payment_% / 100)
```

**Loan Amount:**

```
L = P_property - D
```

**Monthly Interest Rate:**

```
r = rate_annual / (100 × 12)
```

### 2. Monthly Mortgage Payment

Using the standard amortization formula:

```
PMT = L × [r(1 + r)^n] / [(1 + r)^n - 1]
```

Where:
- `PMT` = Monthly payment (principal + interest)
- `L` = Loan amount
- `r` = Monthly interest rate
- `n` = Total number of months

**Special Cases:**
- If `r = 0`: `PMT = L / n` (no interest, just principal)
- If `L = 0`: `PMT = 0` (100% down payment)

### 3. Property Value Over Time

Property appreciates with monthly compounding:

```
V_p(t) = P_property × (1 + a/12)^t
```

Where:
- `V_p(t)` = Property value at month t
- `P_property` = Initial property price
- `a` = Annual appreciation rate (as decimal)
- `t` = Month number

### 4. Remaining Mortgage Balance

The outstanding principal at any time t is the present value of remaining payments:

```
B(t) = PMT × [(1 + r)^(n-t) - 1] / [r(1 + r)^(n-t)]
```

Where:
- `B(t)` = Remaining balance at month t
- `n - t` = Remaining months
- At `t = n` (end): `B(n) = 0` (mortgage paid off)

This can also be expressed using the present value formula:

```
B(t) = -PV(r, n-t, PMT)
```

### 5. Cumulative Outflows

Total cash spent by month t:

```
O_buy(t) = D + (PMT × t)
```

**Components:**
- `D`: One-time down payment at t = 0
- `PMT × t`: Cumulative mortgage payments

### 6. Net Value for Buying

```
N_buy(t) = V_p(t) - O_buy(t)

         = P_property × (1 + a/12)^t - [D + (PMT × t)]
```

This represents: **Asset Value - Money Spent**

## Scenario B: Rent and Invest

### 1. Initial Investment

The same down payment is invested in equities:

```
I_0 = D  (from Scenario A)
```

### 2. Investment Portfolio Value

Portfolio grows with monthly compounding:

```
V_e(t) = I_0 × (1 + e/12)^t
```

Where:
- `V_e(t)` = Portfolio value at month t
- `I_0` = Initial investment
- `e` = Annual equity growth rate (as decimal)
- `t` = Month number

### 3. Rent Payments with Inflation

Rent increases with monthly compounding inflation:

```
Rent(t) = Rent_0 × (1 + i/12)^t
```

Where:
- `Rent(t)` = Rent at month t
- `Rent_0` = Initial monthly rent
- `i` = Annual rent inflation rate (as decimal)

### 4. Cumulative Rent Outflows

Total rent paid by month t is calculated as the cumulative sum:

```
O_rent(t) = Σ(k=0 to t-1) Rent(k) = Σ(k=0 to t-1) [Rent_0 × (1 + i/12)^k]
```

This is a geometric series. The closed-form solution is:

**If** `i = 0` (no inflation):

```
O_rent(t) = Rent_0 × t
```

**If** `i > 0`:

```
O_rent(t) = Rent_0 × [(1 + i/12)^t - 1] / (i/12)
```

**Implementation Note:** The engine uses cumulative sum (`np.cumsum`) for numerical accuracy rather than the closed-form geometric series formula.

### 5. Net Value for Renting

```
N_rent(t) = V_e(t) - O_rent(t)

          = I_0 × (1 + e/12)^t - Σ(k=0 to t-1) Rent(k)
```

This represents: **Portfolio Value - Money Spent on Rent**

## Decision Metric: Net Value Comparison

### The Bottom Line

The fundamental comparison metric:

```
Δ(t) = N_buy(t) - N_rent(t)
```

**Decision Rule:**
- If `Δ(t) > 0`: Buying is better at time t
- If `Δ(t) < 0`: Renting is better at time t
- If `Δ(t) = 0`: Break-even point

### Breakeven Point

The breakeven time t* is when net values are equal:

```
N_buy(t*) = N_rent(t*)  ⟺  Δ(t*) = 0
```

Since we calculate discrete monthly values, we find the breakeven using **linear interpolation**:

Given indices i and i+1 where Δ changes sign:

```
t* = t_i - Δ_i × [(t_(i+1) - t_i) / (Δ_(i+1) - Δ_i)]
```

Where:
- `t_i`, `t_(i+1)` = Time values at indices i and i+1
- `Δ_i`, `Δ_(i+1)` = Difference values at those indices
- This gives the approximate zero-crossing point

## Key Relationships

### Leverage Effect (Buying)

With a mortgage, you control an asset worth more than your initial investment:

```
Leverage Ratio = P_property / D
```

**Example:** $500k property with 20% down

```
Leverage = $500,000 / $100,000 = 5×
```

This amplifies both:
- **Gains:** If property appreciates, you gain on the full value
- **Costs:** Interest payments on leveraged amount

### Opportunity Cost (Renting)

By not buying, you keep capital liquid and invest it. The trade-off:

**Opportunity Benefit:**

```
Benefit = (e - a) × I_0  (when equity growth exceeds property appreciation)
```

**Opportunity Cost:**

```
Cost = O_rent(t)  (money gone forever, no asset accumulation)
```

## Example Calculation

Let's work through a concrete example:

**Given:**
- Property Price: $500,000
- Down Payment: 20% = $100,000
- Mortgage Rate: 4.5% annual
- Property Appreciation: 3% annual
- Duration: 30 years
- Monthly Rent: $2,000
- Equity Growth: 7% annual
- Rent Inflation: 3% annual

**Step 1: Calculate Monthly Values**

```
L = $500,000 - $100,000 = $400,000

r = 4.5% / 12 = 0.375% = 0.00375

n = 30 × 12 = 360 months
```

**Step 2: Monthly Mortgage Payment**

```
PMT = $400,000 × [0.00375(1.00375)^360] / [(1.00375)^360 - 1] ≈ $2,027
```

**Step 3: After 30 Years**

**Scenario A (Buy):**

```
V_p(360) = $500,000 × (1.0025)^360 ≈ $1,214,000

O_buy(360) = $100,000 + ($2,027 × 360) ≈ $829,720

N_buy(360) = $1,214,000 - $829,720 = $384,280
```

**Scenario B (Rent):**

```
V_e(360) = $100,000 × (1.00583)^360 ≈ $761,226

O_rent(360) ≈ $972,000  (geometric series sum)

N_rent(360) = $761,226 - $972,000 = -$210,774
```

**Result:**

```
Δ(360) = $384,280 - (-$210,774) = $595,054
```

**Buying wins by $595,054 in this scenario!**

## Assumptions & Limitations

### 1. Constant Rates
All growth rates are assumed constant over time. In reality:
- Property appreciation varies with market cycles
- Equity returns fluctuate with market conditions
- Interest rates may change (for adjustable-rate mortgages)

### 2. No Transaction Costs
The model excludes:
- Closing costs on purchase (typically 2-5% of property price)
- Realtor fees on sale (typically 5-6%)
- Home inspection, appraisal, title insurance fees
- Moving costs

### 3. No Property Ownership Costs
Not included in the model:
- Property taxes (typically 0.5-2% annually)
- Homeowners insurance
- HOA fees
- Maintenance and repairs (rule of thumb: 1% of home value annually)
- Utilities (may differ between renting and owning)

### 4. No Tax Effects
Tax implications ignored:
- Mortgage interest deduction (can reduce effective cost of buying)
- Property tax deduction
- Capital gains tax on investment returns (Scenario B)
- Capital gains exclusion on primary residence sale (up to $250k/$500k)

### 5. No Down Payment Assistance
Both scenarios start with identical capital (D). In reality:
- Some buyers receive gift funds
- FHA/VA loans allow lower down payments
- Some may have more/less liquid capital available

### 6. Perfect Markets
The model assumes:
- No market crashes or bubbles
- Property can be sold instantly at market value
- Investments can be liquidated without penalty
- No forced sales during downturns

### 7. Full Reinvestment (Scenario B)
The model assumes:
- The down payment is invested as a lump sum at t=0
- No additional monthly investments from rent savings
- In reality, if mortgage payment > rent, the difference could be invested

### 8. Monthly Compounding
Both property appreciation and investment growth compound monthly rather than annually or continuously. This is a standard approximation that:
- Provides more granular tracking
- Is computationally efficient
- Slightly overestimates compound growth vs. annual compounding

## How to Interpret Results

### If Buying Wins (Δ > 0)
Factors contributing to this outcome:
- Property appreciation is strong relative to equity returns
- Mortgage rates are favorable (low interest)
- Leverage is working in your favor
- Long time horizon allows appreciation to compound
- Rent is high relative to mortgage payment

### If Renting Wins (Δ < 0)
Factors contributing to this outcome:
- Equity returns significantly exceed property appreciation
- Rent is low relative to property price (high price-to-rent ratio)
- Flexibility value is high (ability to relocate, no maintenance burden)
- Avoiding leverage risk and transaction costs pays off
- Short to medium time horizon

### The Breakeven Point (t*)

The breakeven year provides critical insights:

| Breakeven Time | Interpretation |
|----------------|----------------|
| t* < 10 years | Buying is clearly advantageous for long-term holders |
| 10 ≤ t* ≤ 20 years | Strategies are competitive; personal factors matter |
| t* > 20 years | Renting may be preferable unless very long holding period |
| No breakeven | One strategy dominates entirely across all time horizons |

### Sensitivity Analysis

Key variables to test:
1. **Property Appreciation Rate (a):** Most uncertain input
2. **Equity Growth Rate (e):** Historical average is ~7-10% for stocks
3. **Rent Inflation (i):** Varies greatly by market
4. **Down Payment (D):** Affects leverage ratio
5. **Duration (n):** Longer periods favor appreciation/compounding

## Implementation Notes

All formulas are implemented using vectorized NumPy operations for performance:

```python
# Property value calculation (vectorized)
home_value = property_price * (1 + monthly_appreciation_rate) ** month_arr

# Equity value calculation (vectorized)
equity_value = down_payment * (1 + monthly_equity_rate) ** month_arr

# Rent with inflation (vectorized)
rent_at_month = monthly_rent * (1 + monthly_rent_inflation) ** month_arr

# No Python loops needed - NumPy broadcasts over the entire time series
```

**Benefits of vectorization:**
- 10-100× faster than Python loops
- More numerically accurate (no accumulation errors from iterative updates)
- More readable and concise
- Industry standard in quantitative finance

### Numerical Precision

The engine uses:
- `numpy_financial.pmt()` for mortgage payment calculation
- `numpy_financial.pv()` for remaining mortgage balance
- Double-precision floating point (64-bit) throughout
- Cumulative sum rather than closed-form geometric series for rent (better numerical stability)

## Related Documentation

- See `engine.py` for the complete implementation
- See `models.py` for data structures (`SimulationConfig`, `SimulationResults`)
- See `visualization.py` for chart generation
- See `README.md` for usage instructions and examples
