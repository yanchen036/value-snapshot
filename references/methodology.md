# Value Snapshot Methodology

This document explains the calculation methodology for value investing metrics used in this skill.

## Core Philosophy

> "The things you want to pay attention to is the pre-tax and pre-interest without leveraged capital to see how profitable it really is."

Focus on **operating earnings power** and **capital efficiency** rather than accounting profits or market sentiment.

## Key Metrics

### 1. Revenue (Top-Line Scale)
**What:** Total sales or revenue for the trailing twelve months (TTM)

**Why:** Shows the scale of operations. Larger revenue provides more room for margin expansion and economies of scale.

**Source:** Income statement - Total Revenue (TTM)

---

### 2. Operating Margin
**What:** Operating income divided by revenue, expressed as a percentage

**Formula:** `Operating Income ÷ Revenue × 100`

**Why:** Reveals the profitability of core operations before financing costs and taxes. More reliable than net margin which can be distorted by tax strategies and capital structure.

**Source:** Income statement - Operating Income ÷ Total Revenue

---

### 3. Operating Earnings (EBIT)
**What:** Earnings Before Interest and Taxes - the **single most important number**

**Formula:** `Revenue × Operating Margin`

**Why:** This is pre-tax, pre-interest, unlevered earnings. It shows the true earning power of the business independent of how it's financed. This is what you're really buying.

**Alternative calculation:** Can be read directly from the income statement as Operating Income

**Importance:** ⭐⭐⭐⭐⭐ (Most critical metric)

---

### 4. Book Value Breakdown
**Components to examine:**

**a. Cash & Liquid Assets**
- Cash and cash equivalents
- Short-term investments (marketable securities)
- **Why examine:** Shows financial flexibility and potential excess capital

**b. Working Capital**
- Current Assets minus Current Liabilities
- Includes cash, inventory, receivables minus payables and short-term debt
- **Why examine:** Indicates capital needed to run day-to-day operations

**c. Fixed Assets (Net PP&E)**
- Property, Plant & Equipment (net of depreciation)
- Real estate, factories, equipment
- **Why examine:** Shows tangible assets that generate earnings

**d. Goodwill (EXCLUDE)**
- Intangible assets from acquisitions
- **Why exclude:** Not a real asset; represents overpayment for acquisitions

**Source:** Balance sheet

---

### 5. Market Cap
**What:** Current market value of all outstanding shares

**Formula:** `Share Price × Shares Outstanding`

**Why:** Shows what the market currently values the entire company at. Compare to earnings power to assess valuation.

**Source:** Market data

---

### 6. Deployed Capital
**What:** Capital actually employed in the business to generate operating earnings

**Formula (simplified):** `Working Capital + Fixed Assets - Excess Cash`

**Components:**
- Start with working capital (current assets - current liabilities)
- Add fixed assets (Net PP&E) needed for operations
- Subtract excess cash not needed for operations

**Why:** Shows the actual capital needed to generate the operating earnings. This is the denominator for ROIC.

**Note:** "Excess cash" is cash beyond what's needed to run operations. A rough heuristic is ~10% of revenue as minimum operating cash.

---

### 7. ROIC (Return on Invested Capital)
**What:** Operating earnings divided by deployed capital, expressed as a percentage

**Formula:** `Operating Earnings ÷ Deployed Capital × 100`

**Why:** Shows how efficiently the business converts capital into earnings. High ROIC (>20-30%) indicates a strong competitive position and efficient operations.

**Interpretation:**
- **>30%:** Excellent - strong moat, high efficiency
- **15-30%:** Good - solid business
- **<15%:** Modest - competitive or capital-intensive industry
- **Negative:** Destroying value

---

## Historical Examples

### Case 1: Timberland (1998, Asian Financial Crisis)

**Context:** 1998 Asian financial crisis created market panic

**Metrics:**
- Revenue: ~$850M
- Operating Margin: 13%
- Operating Earnings: ~$110M (850M × 13%)
- Book Value: ~$300M (mostly liquid working capital + real estate)
- Market Cap: Very low (crisis valuation)

**ROIC Calculation:**
```
ROIC = $110M ÷ $300M = ~37%
```

**Actually achieved:** ~50% ROIC on deployed capital

**Interpretation:** During crisis, market valued company at fire-sale prices despite strong operating earnings and minimal capital needs. High ROIC indicated strong business quality being obscured by temporary market fear.

---

### Case 2: PDD Holdings (PDD) - February 2026

**Context:** Leading Chinese e-commerce platform (Pinduoduo)

**Metrics:**
- Revenue (TTM): $58.07B USD
- Operating Margin: 22.11%
- Operating Income: $12.84B USD

**Book Value Components:**
- Cash & Short-term Investments: ~$58.5B USD (massive excess cash)
- Working Capital: Strongly positive, cash-dominated
  - Current Assets >> Current Liabilities
- Net PP&E (Tangible Fixed Assets): <$0.15B (negligible - asset-light)
- Tangible Book Value: ~$54B USD (intangibles are minimal)

**Valuation:**
- Market Cap: $151.76B USD
- Enterprise Value: $93.77B USD (subtracts huge net cash position)

**ROIC Calculation:**
```
Deployed Capital = Working Capital + Net PP&E - Excess Cash
                 ≈ Positive WC + $0.15B - (Most of $58.5B cash)
                 ≈ ~$18.9B (rough estimate of actual operating capital)

ROIC = $12.84B ÷ $18.9B = 67.86%
```

**Interpretation:**
- **Asset-light model:** Virtually no PP&E needed (platform business)
- **Massive cash generation:** $58.5B cash shows extraordinary cash generation
- **High ROIC:** 67.86% indicates very efficient capital use
- **Strong business quality:** High margins + low capital needs = excellent economics
- **Note:** Large cash hoard creates question about capital allocation

---

## Calculation Workflow

1. **Fetch financial data** (TTM income statement, latest balance sheet)
2. **Extract revenue** → Income statement
3. **Calculate operating margin** → Operating Income ÷ Revenue
4. **Confirm operating earnings** → Read directly or calculate (Revenue × Margin)
5. **Analyze book value components:**
   - Cash & liquid assets
   - Working capital
   - Fixed assets (PP&E)
   - Exclude goodwill/intangibles
6. **Get market cap** → Current price × shares outstanding
7. **Calculate deployed capital** → WC + PP&E - Excess Cash
8. **Calculate ROIC** → Operating Earnings ÷ Deployed Capital
9. **Interpret results** → Compare ROIC to industry norms and historical examples

---

## Key Insights

**Asset-Light vs Capital-Intensive:**
- **Asset-light** (software, platforms): Low PP&E, high ROIC potential (PDD example)
- **Capital-intensive** (manufacturing, retail): High PP&E, lower ROIC typically (Timberland example)

**Excess Cash:**
- Large cash hoards can signal strong cash generation (good)
- But also raises questions about capital allocation opportunities (consideration)
- Should be excluded from deployed capital since it's not needed for operations

**Operating Earnings = The Truth:**
- Net income can be manipulated through tax strategies, interest deductions, one-time charges
- Operating earnings shows the real earning power before financial engineering
- This is what you're buying when you invest

**ROIC = Quality Signal:**
- High sustained ROIC (>20%) typically indicates competitive advantages (moat)
- Low ROIC (<10%) may signal commodity business or weak competitive position
- ROIC trends matter: Improving vs. declining
