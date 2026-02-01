# Mathematical Formulas Reference

This document provides detailed mathematical formulas used in the simulation engine.

## Time Vector

All calculations use monthly granularity for accuracy:

```
t = [0, 1, 2, ..., n_months]  where n_months = duration_years × 12
year = t / 12
```

## Scenario A: Buy Property with Mortgage

### 1. Initial Values

```
Down Payment (D):
  D = Property_Price × (Down_Payment_% / 100)

Loan Amount (L):
  L = Property_Price - D

Monthly Interest Rate (r):
  r = Annual_Rate / 100 / 12
```

### 2. Monthly Mortgage Payment

Using the standard amortization formula:

```
PMT = L × [r(1 + r)^n] / [(1 + r)^n - 1]

Where:
  PMT = Monthly payment (principal + interest)
  L   = Loan amount
  r   = Monthly interest rate
  n   = Total number of months

Special Cases:
  - If r = 0: PMT = L / n  (no interest, just principal)
  - If L = 0: PMT = 0      (100% down payment)
```

### 3. Property Value Over Time

Property appreciates with monthly compounding:

```
V_p(t) = P × (1 + a/12)^t

Where:
  V_p(t) = Property value at month t
  P      = Initial property price
  a      = Annual appreciation rate (as decimal)
  t      = Month number
```

### 4. Remaining Mortgage Balance

The outstanding principal at any time t:

```
B(t) = Present Value of remaining payments

B(t) = PMT × [(1 + r)^(n-t) - 1] / [r(1 + r)^(n-t)]

Where:
  B(t) = Remaining balance at month t
  n-t  = Remaining months

At t=n (end): B(n) = 0 (mortgage paid off)
```

### 5. Cumulative Outflows

Total cash spent by month t:

```
O_buy(t) = D + (PMT × t)

Components:
  - D: One-time down payment at t=0
  - PMT × t: Cumulative mortgage payments
```

### 6. Net Value for Buying

```
N_buy(t) = V_p(t) - O_buy(t)
         = P × (1 + a/12)^t - [D + (PMT × t)]

This represents: Asset Value - Money Spent
```

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

Where:
  V_e(t) = Portfolio value at month t
  I_0    = Initial investment
  e      = Annual equity growth rate (as decimal)
  t      = Month number
```

### 3. Rent Payments with Inflation

Rent increases annually at inflation rate:

```
Rent(t) = Rent_0 × (1 + i/12)^t

Where:
  Rent(t) = Rent at month t
  Rent_0  = Initial monthly rent
  i       = Annual rent inflation rate (as decimal)
```

### 4. Cumulative Rent Outflows

Total rent paid by month t:

```
O_rent(t) = Σ(k=0 to t-1) Rent(k)
          = Σ(k=0 to t-1) [Rent_0 × (1 + i/12)^k]

This is a geometric series sum.

If i = 0 (no inflation):
  O_rent(t) = Rent_0 × t

If i > 0:
  O_rent(t) = Rent_0 × [(1 + i/12)^t - 1] / (i/12)
```

### 5. Net Value for Renting

```
N_rent(t) = V_e(t) - O_rent(t)
          = I_0 × (1 + e/12)^t - Σ Rent(k)

This represents: Portfolio Value - Money Spent on Rent
```

## Decision Metric: Net Value Comparison

### The Bottom Line

```
Difference(t) = N_buy(t) - N_rent(t)

Decision Rule:
  - If Difference > 0: Buying is better
  - If Difference < 0: Renting is better
  - If Difference = 0: Break-even point
```

### Breakeven Point

The time when net values are equal:

```
N_buy(t*) = N_rent(t*)

Solving for t* requires numerical methods (we use linear interpolation
between data points where the sign of Difference changes).
```

## Key Relationships

### Leverage Effect (Buying)

With a mortgage, you control an asset worth more than your initial investment:

```
Leverage Ratio = Property_Price / Down_Payment

Example: $500k property with 20% down
  Leverage = $500k / $100k = 5x

This amplifies both gains (if property appreciates) 
and the effective cost (interest payments).
```

### Opportunity Cost (Renting)

By not buying, you keep capital liquid and invest it:

```
Opportunity Benefit = (Equity_Growth - Property_Appreciation) × Initial_Investment

But you also pay rent, which has no asset accumulation:
Opportunity Cost = Cumulative_Rent (money gone forever)
```

## Example Calculation

Let's work through a simple example:

```
Given:
  Property Price: $500,000
  Down Payment: 20% = $100,000
  Mortgage Rate: 4.5% annual
  Property Appreciation: 3% annual
  Duration: 30 years
  Monthly Rent: $2,000
  Equity Growth: 7% annual
  Rent Inflation: 3% annual

Step 1: Calculate Monthly Values
  Loan Amount: $500,000 - $100,000 = $400,000
  Monthly Rate: 4.5% / 12 = 0.375%
  Months: 30 × 12 = 360

Step 2: Monthly Mortgage Payment
  PMT = $400,000 × [0.00375(1.00375)^360] / [(1.00375)^360 - 1]
      ≈ $2,027

Step 3: After 30 Years

Scenario A (Buy):
  Property Value: $500,000 × (1.0025)^360 ≈ $1,214,000
  Total Payments: $100,000 + ($2,027 × 360) ≈ $829,720
  Net Value: $1,214,000 - $829,720 = $384,280

Scenario B (Rent):
  Portfolio Value: $100,000 × (1.00583)^360 ≈ $761,226
  Total Rent: Σ(geometric series) ≈ $972,000
  Net Value: $761,226 - $972,000 = -$210,774

Result: Buying wins by $595,054 in this scenario!
```

## Assumptions & Limitations

1. **Constant Rates:** All growth rates are assumed constant (unrealistic but useful for comparison)

2. **No Transaction Costs:** 
   - No closing costs on purchase
   - No realtor fees on sale
   - No maintenance/repair costs

3. **No Taxes:**
   - No property taxes
   - No income taxes on investment gains
   - No mortgage interest deduction

4. **No Down Payment Assistance:** Both scenarios start with same capital

5. **Perfect Markets:** No market crashes or bubbles modeled

6. **Full Reinvestment:** In reality, monthly rent savings might not all be invested

## How to Interpret Results

### If Buying Wins
- Property appreciation is strong
- Mortgage rates are favorable
- Leverage is working in your favor
- Long time horizon allows appreciation to compound

### If Renting Wins
- Equity returns significantly exceed property appreciation
- Rent is low relative to property price
- Flexibility value is high
- Avoiding leverage risk pays off

### The Breakeven Point
- Shows when the strategies cross over
- Earlier breakeven (< 10 years) suggests buying is clearly better
- Later breakeven (> 20 years) suggests strategies are comparable
- No breakeven suggests one dominates entirely

## Implementation Notes

All formulas are implemented using vectorized NumPy operations:

```python
# Property value calculation (vectorized)
home_value = property_price * (1 + monthly_appreciation_rate) ** month_arr

# Equity value calculation (vectorized)  
equity_value = down_payment * (1 + monthly_equity_rate) ** month_arr

# No Python loops needed - NumPy handles the entire time series at once
```

This approach is:
- 10-100× faster than loops
- More accurate (no accumulation errors)
- More readable
- Standard in quantitative finance
