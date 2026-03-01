---
name: value-snapshot
description: Quick value investing analysis for public companies using Li Lu's methodology. Generates 5-minute financial snapshots showing operating earnings power and capital efficiency (RODC). Calculates P/B, P/E, deployed capital, and RODC following Li Lu's framework from his Columbia masterclass. Use when user requests financial analysis, value investing metrics, company snapshots, or company comparisons. Triggered by requests like "analyze [TICKER]", "value snapshot for [company]", "compare GOOG and MSFT", "which is better PDD or BABA", or "Li Lu analysis of [ticker]".
---

# Value Snapshot - Li Lu's Methodology

Generate 5-minute value investing snapshots for public companies using Li Lu's analytical framework.

## Overview

This skill implements Li Lu's investment methodology from his 2006 Columbia Business School masterclass, focusing on:

1. **Operating earnings (EBIT)** - Pre-tax, pre-interest, unlevered earnings
2. **Deployed capital** - Capital actually used in operations (excludes ALL cash)
3. **RODC** (Return on Deployed Capital) - Li Lu's signature metric
4. **P/B and P/E ratios** - Quick valuation checks
5. **Margin of safety** - Tangible assets, cash cushion, downside protection

**Li Lu's Philosophy:**
> "What you want to pay attention to is the pre-tax and pre-interest without leveraged capital to see how profitable it really is."

**The 5-Minute Analysis:** Each company analysis should take less than 5 minutes for the numbers. Train mental math. No calculators.

## Workflow

### Step 1: Get Company Ticker

If the user provides a company name instead of ticker, identify the correct ticker symbol first.

**Examples:**
- "Tesla" → TSLA
- "Alphabet" or "Google" → GOOG or GOOGL
- "PDD Holdings" or "Pinduoduo" → PDD

### Step 2: Fetch Financial Data

Use `scripts/fetch_financials.py` to retrieve TTM financial data:

```bash
python scripts/fetch_financials.py TICKER [API_KEY]
```

**Data Strategy:**
1. **Primary:** SEC EDGAR Company Facts API (official source, works for ALL US-listed companies including ADRs)
2. **Always:** Massive.com API for real-time market data (price, market cap)
3. **Fallback:** Massive.com financials API if SEC EDGAR fails

The script fetches:
- Income statement (TTM): Revenue, Operating Income, Operating Margin
- Balance sheet (latest): Cash, Current Assets/Liabilities, PP&E, Goodwill
- Market data: Market cap, shares outstanding, current price

**Output:** JSON with all required financial data

**Troubleshooting:**

The script now uses SEC EDGAR as primary source and provides clear progress messages:
- "✓ Successfully fetched from SEC EDGAR (CIK: XXXXXXXXXX)"
- "✗ SEC EDGAR failed, trying Massive.com API (fallback)..."
- "✓ Successfully fetched from Massive.com API"

**Common issues:**
- If ticker not found: Verify ticker symbol is correct
- If both SEC and API fail: Company may be very recently listed or delisted
- Data quality: SEC EDGAR provides official audited data from 10-K, 10-Q, 20-F filings
- The script automatically handles Chinese ADRs (PDD, BABA, etc.) via SEC EDGAR

### Step 3: Calculate Value Metrics

Use `scripts/calculate_metrics.py` to compute key metrics:

```bash
python scripts/fetch_financials.py TICKER | python scripts/calculate_metrics.py -
```

Or in two steps:
```bash
python scripts/fetch_financials.py TICKER > data.json
python scripts/calculate_metrics.py data.json
```

**The script calculates:**

1. **Operating Earnings** - Confirmed from income statement
2. **Deployed Capital** - Working capital + PP&E - Excess cash
3. **ROIC** - Operating Earnings ÷ Deployed Capital
4. **Book Value Breakdown** - Cash, working capital, fixed assets, tangible book value
5. **Valuation Context** - Market cap, enterprise value estimate

**Output:** Formatted snapshot + JSON with all calculated metrics

### Step 4: Present Results

Format the output clearly with context:

**Template:**

```
VALUE SNAPSHOT: [Company Name] ([TICKER])
Date: [YYYY-MM-DD]

📊 OPERATING METRICS (TTM)
  Revenue:              $XX.XXB USD
  Operating Margin:     XX.XX%
  Operating Earnings:   $X.XXB USD ⭐ [Most important number]

💰 BOOK VALUE BREAKDOWN
  Cash & Liquid Assets: $XX.XXB
  Working Capital:      $XX.XXB
  Fixed Assets (PP&E):  $X.XXB
  Goodwill:             $X.XXB [excluded]
  Tangible Book Value:  $XX.XXB

🎯 VALUATION & CAPITAL EFFICIENCY
  Market Cap:           $XXX.XXB
  Enterprise Value:     $XX.XXB
  Deployed Capital:     $XX.XXB
  ROIC:                 XX.XX%

💡 INTERPRETATION
[1-2 sentences on business quality based on ROIC and asset profile]
[1 sentence on valuation context]
```

### Step 5: Add Interpretation

Provide brief context using the interpretation guide:

**ROIC interpretation:**
- **>30%** → "Outstanding capital efficiency - indicates strong competitive moat"
- **20-30%** → "Strong returns - solid business quality"
- **10-20%** → "Adequate returns - reasonably efficient"
- **<10%** → "Modest returns - capital-intensive or competitive industry"
- **Negative** → "Currently destroying value"

**Asset profile:**
- **Low PP&E (<20% of revenue)** → "Asset-light business model"
- **Moderate PP&E (20-50%)** → "Balanced capital requirements"
- **High PP&E (>50%)** → "Capital-intensive operations"

**Cash position:**
- **High cash (>30% of market cap)** → "Fortress balance sheet - note capital allocation question"
- **Adequate cash** → "Healthy liquidity"
- **Low cash + negative WC** → "⚠️ Liquidity concerns"

**See `references/interpretation.md` for detailed benchmarks and decision frameworks.**

## Comparing Multiple Companies

When the user wants to compare companies (e.g., "compare GOOG and MSFT", "which is better PDD or BABA"):

### Use `scripts/compare_companies.py`

```bash
python scripts/compare_companies.py TICKER1 TICKER2 [TICKER3] [TICKER4] [API_KEY]
```

**Examples:**
```bash
python scripts/compare_companies.py GOOG MSFT
python scripts/compare_companies.py PDD BABA AMZN
```

**What it does:**
1. Fetches data and calculates metrics for 2-4 companies
2. Displays side-by-side comparison table
3. Highlights winner on each metric
4. Provides Li Lu's analysis of which is best investment

**Output includes:**
- **Valuation Metrics:** Market cap, P/B, P/E with Li Lu targets
- **Operating Quality:** Revenue, margin, RODC, asset profile
- **Capital Structure:** Cash, working capital, deployed capital, goodwill
- **Winners by Metric:** Best RODC, cheapest P/E, highest margin
- **Overall Assessment:** Quality score + Value score for each company
- **Li Lu's Verdict:** Which company he'd likely choose and why

**Scoring System:**
- Quality Score (0-3): Based on RODC thresholds
  - 3 points: RODC >50% (Exceptional)
  - 2 points: RODC 30-50% (Strong)
  - 1 point: RODC 15-30% (Good)
- Value Score (0-3): Based on P/E and P/B
  - 3 points: P/E <10 AND P/B <1.5 (Cheap)
  - 2 points: P/E <10 OR P/B <1.5 (Reasonable)
  - 1 point: P/E <15 (Acceptable)
- Total Score: 5-6 = Invest, 4 = Consider, <4 = Pass

**See `references/interpretation.md` for detailed benchmarks and decision frameworks.**

## Resources

### Scripts

**`fetch_financials.py`**
- **Primary:** Fetches financial data from SEC EDGAR Company Facts API (official, audited data)
- **Fallback:** Massive.com API (Polygon.io) if SEC fails
- **Market data:** Always from Massive.com for real-time price/market cap
- Requires: `requests` library and Massive.com API key
- Returns: JSON with financial statements and market data
- **Works for ALL US-listed companies** including foreign ADRs (PDD, BABA, etc.)

**`calculate_metrics.py`**
- Calculates value investing metrics from financial data
- Can be piped from fetch_financials.py or run standalone
- Returns: Formatted snapshot + JSON output

**`compare_companies.py`**
- Compares 2-4 companies side-by-side using Li Lu's framework
- Fetches data and calculates metrics for each company
- Displays comparison table with winners on each metric
- Provides Li Lu's analysis and overall recommendation
- Scoring system: Quality (0-3) + Value (0-3) = Total score

### References

**`li_lu_framework.md`** - Li Lu's complete investment framework:
- The 5-Minute Analysis process
- Investment checklist (5 key questions)
- Position sizing philosophy
- **Timberland case study** (1998): 7x return, 55% RODC
- **Hyundai H&S case study** (2004): Trading below cash, 6x return
- Key principles and mental models
- Research sources and due diligence methods

**`methodology.md`** - Detailed calculation methodology:
- RODC calculation (Li Lu's signature metric)
- Deployed capital (excludes ALL cash)
- Operating earnings (pre-tax, pre-interest)
- Book value breakdown and asset classification
- Formula explanations with examples

**`interpretation.md`** - Comprehensive guide to interpreting metrics:
- RODC benchmarks (>50% = exceptional, >30% = strong)
- P/B and P/E thresholds
- Asset profile analysis (asset-light vs capital-intensive)
- Red flags and green flags
- Quick decision heuristics

**Load these references when:**
- User asks about Li Lu's methodology → li_lu_framework.md
- User asks how metrics are calculated → methodology.md
- User asks what numbers mean or thresholds → interpretation.md
- Want to show case studies → li_lu_framework.md

## Examples

### Example 1: Asset-Light Platform (PDD Holdings)

**User request:** "Run value snapshot for PDD"

**Output:**
```
VALUE SNAPSHOT: PDD Holdings Inc (PDD)

📊 OPERATING METRICS (TTM)
  Revenue:              $58.07B USD
  Operating Margin:     22.11%
  Operating Earnings:   $12.84B USD ⭐

💰 BOOK VALUE BREAKDOWN
  Cash & Liquid Assets: $58.50B (massive cash hoard)
  Fixed Assets (PP&E):  $0.15B (negligible)
  Tangible Book Value:  $54.00B

🎯 VALUATION & CAPITAL EFFICIENCY
  Market Cap:           $151.76B
  Enterprise Value:     $93.77B
  Deployed Capital:     ~$18.9B
  ROIC:                 67.86%

💡 INTERPRETATION
Outstanding capital efficiency (ROIC 67.86%) with asset-light platform model.
Massive cash generation ($58.5B cash) raises capital allocation questions.
```

### Example 2: Traditional Retail (Historical Reference)

**User request:** "Show me an example of a strong ROIC retail business"

**Timberland (1998, during Asian financial crisis):**
- Revenue: $850M, Operating Margin: 13% → Operating Earnings: $110M
- Book Value: ~$300M (liquid working capital + real estate)
- ROIC: ~50% on deployed capital
- Context: Market panic created opportunity in quality business with strong returns

### Example 3: Basic Usage

**User:** "Value snapshot for TSLA"

**Process:**
1. Fetch data: `python scripts/fetch_financials.py TSLA`
2. Calculate: Pipe to `calculate_metrics.py`
3. Present formatted snapshot with ROIC interpretation
4. Note asset profile (capital-intensive manufacturing vs software)

## Tips - Li Lu's Approach

- **Most important metric:** Operating Earnings (EBIT) - unlevered earning power
- **Quality signal:** RODC >50% = "That is not a bad business!" (Li Lu)
- **Deployed capital:** Excludes ALL cash - only capital generating operating earnings
- **Asset profile matters:** Asset-light businesses can have higher RODC potential
- **P/B < 1.5x, P/E < 10x:** Li Lu's initial screens for cheapness
- **Trading below cash:** Rare but exists (Hyundai H&S: $60M market cap, $70M cash)
- **5-minute analysis:** Train speed - should take < 5 minutes for the numbers
- **Deep research:** 2-3 weeks of intense work when opportunity identified
- **Position sizing:** High conviction = large positions (30-50%+)
- **Compare to peers:** RODC varies by industry
- **Trends matter:** Improving margins and RODC > absolute levels

**Li Lu's Checklist:**
1. Is it cheap? (P/B, P/E, market cap vs. cash)
2. Is the business good? (RODC > 15%, ideally > 50%)
3. Is management trustworthy? (Requires deep due diligence)
4. What am I missing? (Risks, catalysts, blind spots)
5. Why does this opportunity exist? (No coverage, crisis, complexity)

## Limitations

- **Public companies only:** Requires SEC filings or public financial data
- **US-listed companies:** Works best for companies listed on US exchanges (NYSE, NASDAQ)
  - SEC EDGAR covers all US-listed companies including foreign ADRs
  - Non-US companies not trading in US may need alternative sources
- **Data freshness:** SEC EDGAR data updated after quarterly/annual filings (10-K, 10-Q, 20-F)
  - Most recent data typically 1-3 months old
  - Market data (price, market cap) is real-time from Massive.com
- **Simplified deployed capital:** Uses heuristic for excess cash (5% of revenue)
- **No debt analysis:** Focuses on operating metrics, not capital structure details
- **Requires API key:** Massive.com API key needed for real-time market data

For detailed methodology and interpretation, load the reference files as needed.
