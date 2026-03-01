# Value Snapshot - Li Lu's Investment Methodology

Quick value investing analysis for public companies using Li Lu's methodology from his 2006 Columbia Business School masterclass.

## Features

### 1. Single Company Analysis

Generate 5-minute financial snapshots showing:
- **Operating earnings power** (EBIT - pre-tax, pre-interest)
- **Capital efficiency** (RODC - Return on Deployed Capital)
- **Valuation metrics** (P/B, P/E, Market Cap vs. Cash)
- **Book value breakdown** (Liquid assets, working capital, fixed assets)
- **Investment thesis checklist** (Is it cheap? Good business? Asset protection?)

### 2. Company Comparisons **NEW!**

Compare 2-4 companies side-by-side:
- Side-by-side metrics table
- Winner on each dimension
- Li Lu's analysis of which is best
- Quality + Value scoring system

Following Li Lu's philosophy: Focus on operating earnings and deployed capital (excluding ALL cash).

## Installation

### Prerequisites

```bash
# Activate your Python environment
conda activate cc_financial  # or your preferred environment

# Install required packages
pip install requests pyyaml
```

### API Key Setup

This skill requires a Massive.com API key for real-time market data (free tier available at https://massive.com/).

**IMPORTANT: Never commit your API key to version control or share it publicly.**

Set your API key as an environment variable:

```bash
# Add to your ~/.bashrc or ~/.zshrc for persistence
export MASSIVE_API_KEY='your_api_key_here'
```

Or pass it directly as a command-line argument (see Usage below).

## Usage

### Single Company Analysis

```bash
# Navigate to the skill directory
cd /Users/chenyan12/workspace/value-snapshot

# Analyze a company (using environment variable for API key)
python scripts/fetch_financials.py TSLA | python scripts/calculate_metrics.py -

# Or pass API key directly
python scripts/fetch_financials.py PDD your_api_key_here | python scripts/calculate_metrics.py -
```

### Company Comparison **NEW!**

```bash
# Compare 2 companies
python scripts/compare_companies.py GOOG MSFT

# Compare 3-4 companies
python scripts/compare_companies.py PDD BABA AMZN

# Pass API key if not in environment
python scripts/compare_companies.py GOOG MSFT your_api_key_here
```

### Create a Convenient Alias

Add to your `~/.bashrc` or `~/.zshrc`:

```bash
alias value-snapshot='python /Users/chenyan12/workspace/value-snapshot/scripts/fetch_financials.py "$1" | python /Users/chenyan12/workspace/value-snapshot/scripts/calculate_metrics.py -'
alias compare-stocks='python /Users/chenyan12/workspace/value-snapshot/scripts/compare_companies.py'
```

Then simply:

```bash
value-snapshot TSLA
compare-stocks GOOG MSFT
```

## Example Output

### Single Company (PDD)

```
VALUE SNAPSHOT: PDD Holdings Inc (PDD)

⏱  DATA TIMESTAMPS
  Financial Data: SEC filing as of 2025-04-28
  Market Data:    Current price as of 2026-02-28 ($105.39/share)
  Note:           Data is 10 months old - most recent complete filing

🎯 QUICK CHECK (Is it cheap?)
  Market Cap:         $149.62B USD        P/B:   3.49x
  Tangible Book:      $42.92B USD         P/E:   10.07x (pre-tax)

📊 OPERATING QUALITY (Is the business good?)
  Revenue (TTM):      $53.96B USD
  Operating Margin:   27.53%
  Operating Earnings: $12.84B USD ⭐

  RODC:               104.80%  [EXCEPTIONAL - Li Lu target!]
  Asset Profile:      Asset-light platform (PP&E < 10% of revenue)

💰 CAPITAL STRUCTURE
  Current Assets:     $56.94B USD
  Current Liabilities:$25.81B USD
  Working Capital:    $31.13B USD

  Liquid Assets:      $45.42B USD (NOT deployed)
  Operating WC:       $-14.29B USD (supplier financing)
  Fixed Assets (PP&E):$120.47M USD
  Deployed Capital:   $14.17B USD (generates earnings)

📈 INVESTMENT THESIS CHECKLIST
  [ ] Cheap? P/E = 10.07x (< 10x ~)
  [✓✓✓] Good Business? RODC = 104.8% (>50% ✓, EXCEPTIONAL!)
  [ ] Asset Protection? Book = 29% of market cap

💡 Li Lu's Take: "RODC > 50% - That is not a bad business!"
   Exceptional returns on deployed capital = competitive moat
```

### Company Comparison (GOOG vs MSFT)

```
COMPANY COMPARISON - Li Lu's Value Investing Framework

🎯 VALUATION METRICS
Metric                         |         GOOG |         MSFT | Li Lu Target
Market Cap                     |     $3715.6B |     $2983.0B | N/A
P/B Ratio                      |        16.52 |        16.44 | < 1.5x
P/E (Operating)                |        44.08 |        47.95 | < 10x

📊 OPERATING QUALITY
Metric                         |         GOOG |         MSFT | Li Lu Target
Revenue (TTM)                  |      $307.4B |       $31.9B | N/A
Operating Margin               |        27.4% |       194.7% | >20%
RODC ⭐                         |        37.9% |        38.8% | >50%

💡 LI LU'S ANALYSIS
Best Overall: GOOG
  Quality Score: 2/3 (RODC 37.9%)
  Value Score:   0/3 (P/E 44.1x)
  Total Score:   2/6

✗ Li Lu would likely PASS on both - Wait for better entry point
```

## Data Sources

1. **Primary:** SEC EDGAR Company Facts API (official audited data from 10-K, 10-Q, 20-F filings)
2. **Market Data:** Massive.com API (real-time price, market cap, shares outstanding)
3. **Fallback:** Massive.com financials API (if SEC EDGAR data unavailable)

Works for **all US-listed companies** including foreign ADRs (PDD, BABA, etc.).

## Li Lu's Investment Framework

### The 5-Minute Analysis

1. **Quick Check (30 seconds):** P/B ratio (<1.5x target), P/E (<10x target), Market cap vs. cash
2. **Operating Quality (1 minute):** Revenue, margin, operating earnings, RODC (>50% = exceptional)
3. **Capital Structure (2 minutes):** Separate liquid vs. deployed assets, calculate deployed capital
4. **Margin of Safety (1 minute):** Tangible book value, downside protection

### Key Metrics

- **Operating Earnings (EBIT):** Pre-tax, pre-interest, unlevered earnings
- **Deployed Capital:** Operating working capital + PP&E - excludes ALL cash
- **RODC:** Operating Earnings ÷ Deployed Capital
  - **>50%** = Exceptional (Li Lu's target: "That is not a bad business!")
  - **>30%** = Strong
  - **>15%** = Good
  - **<15%** = Weak
- **P/B Ratio:** Market Cap ÷ Tangible Book Value (target <1.5x)
- **P/E Ratio:** Market Cap ÷ Operating Earnings (target 2-10x)

### Investment Checklist

1. **Is it cheap?** (P/B, P/E, market cap vs. cash)
2. **Is the business good?** (RODC >15%, ideally >50%)
3. **Is management trustworthy?** (Requires deep due diligence)
4. **What am I missing?** (Risks, catalysts, blind spots)
5. **Why does this opportunity exist?** (No coverage, crisis, complexity)

### Comparison Scoring System

For multi-company comparisons, each company gets:

**Quality Score (0-3):**
- 3 points: RODC >50% (Exceptional)
- 2 points: RODC 30-50% (Strong)
- 1 point: RODC 15-30% (Good)
- 0 points: RODC <15% (Weak)

**Value Score (0-3):**
- 3 points: P/E <10 AND P/B <1.5 (Cheap)
- 2 points: P/E <10 OR P/B <1.5 (Reasonable)
- 1 point: P/E <15 (Acceptable)
- 0 points: P/E >15 (Expensive)

**Total Score (0-6):**
- 5-6: Li Lu would likely INVEST
- 4: Li Lu might CONSIDER with deep due diligence
- <4: Li Lu would likely PASS

## Reference Materials

- **`references/li_lu_framework.md`** - Complete investment framework with Timberland and Hyundai H&S case studies
- **`references/methodology.md`** - Detailed calculation methodology
- **`references/interpretation.md`** - Guide to interpreting metrics and benchmarks

## Limitations

- **Public companies only:** Requires SEC filings or public financial data
- **US-listed companies:** Works best for companies listed on US exchanges (NYSE, NASDAQ)
  - SEC EDGAR covers all US-listed companies including foreign ADRs
  - Non-US companies not trading in US may need alternative sources
- **Data freshness:** SEC EDGAR data updated after quarterly/annual filings (10-K, 10-Q, 20-F)
  - Most recent data typically 1-3 months old (US companies) or up to 12 months (foreign 20-F filers)
  - Market data (price, market cap) is real-time from Massive.com
- **Simplified deployed capital:** Uses heuristic for asset-light businesses with negative working capital
- **No debt analysis:** Focuses on operating metrics, not capital structure details
- **Requires API key:** Massive.com API key needed for real-time market data

## Examples

```bash
# Asset-light platform
value-snapshot PDD    # E-commerce platform with 104.8% RODC

# Capital-intensive manufacturing
value-snapshot TSLA   # Manufacturing with 31.1% RODC

# Tech giants comparison
compare-stocks GOOG MSFT   # Which tech giant is better value?

# Chinese ADRs
compare-stocks PDD BABA    # Compare e-commerce platforms

# Three-way comparison
compare-stocks PDD BABA AMZN   # Best e-commerce platform?
```

## Philosophy

> "What you want to pay attention to is the pre-tax and pre-interest without leveraged capital to see how profitable it really is." - Li Lu

This tool implements Li Lu's disciplined approach:
- Train mental math and pattern recognition
- Focus on operating earnings and capital efficiency
- Look for competitive moats (high RODC)
- Demand margin of safety
- Think like a business owner, not a paper shuffler
- Compare companies to find the best opportunity

## Security Note

⚠️ **Never commit your API key to version control or share it publicly.** Always use environment variables or command-line arguments, and add `.env` files to `.gitignore` if using them.
