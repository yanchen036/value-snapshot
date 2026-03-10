# Company Screening System

Automated company screening system using Li Lu's value investing methodology. Identifies investment opportunities by finding quality companies trading near their 52-week lows.

## Features

- **52-Week Low Detection**: Find companies near their 52-week lows (potential value opportunities)
- **Li Lu's Methodology**: Screen for RODC (Return on Deployed Capital), operating margins, and valuation ratios
- **Smart Caching**: SQLite-based cache reduces API calls and speeds up subsequent runs
- **Multiple Presets**: Pre-configured screening strategies (deep value, quality, cash fortress, etc.)
- **Flexible Filtering**: Customize all screening criteria via command-line or presets
- **S&P 500 Focus**: MVP targets S&P 500 (~500 companies), expandable to small/mid-caps

## Quick Start

### 1. Setup Environment

```bash
# Activate conda environment
conda activate cc_financial

# Ensure dependencies are installed
pip install pandas tqdm requests

# Set API key
export MASSIVE_API_KEY=your_api_key_here
```

### 2. Run Your First Screen

```bash
cd scripts

# Default screen: Quality companies near 52-week lows
python screen_companies.py

# Use a specific preset
python screen_companies.py --preset deep_value

# List all available presets
python screen_companies.py --list-presets
```

### 3. View Results

Results are saved to:
- `screening_results.md` - Full data for all passing companies
- `screening_results_summary.md` - Human-readable summary report

## Available Presets

### 1. **52_week_low_quality** (Default)
Quality companies trading near 52-week lows
- 52w Low: Within 20% of low
- RODC: >30%
- P/E: <15x
- P/B: <2.0x
- Operating Margin: >10%

### 2. **deep_value**
Extreme value opportunities
- 52w Low: Within 15% of low (very close)
- P/E: <12x
- P/B: <1.5x
- Positive working capital required

### 3. **li_lu_classic**
Classic Li Lu methodology - exceptional businesses
- RODC: >50% (Li Lu's "not a bad business" threshold)
- P/E: <10x
- P/B: <1.5x
- Operating Margin: >15%

### 4. **cash_fortress**
Strong cash positions near 52-week lows
- Cash: >25% of market cap
- 52w Low: Within 30% of low
- Positive working capital

### 5. **quality_any_price**
Find the highest quality businesses regardless of price
- RODC: >40%
- Operating Margin: >20%
- No valuation filters

## Usage Examples

### Basic Usage

```bash
# Default preset (52_week_low_quality)
python screen_companies.py

# Specify output file
python screen_companies.py --output my_screen.md

# Get top 30 candidates instead of 50
python screen_companies.py --top 30
```

### Custom Filters

```bash
# Custom RODC and P/E thresholds
python screen_companies.py --min-rodc 25 --max-pe 12

# Companies within 10% of 52-week low
python screen_companies.py --max-proximity 0.10

# Combine multiple filters
python screen_companies.py --min-rodc 30 --max-pe 15 --max-proximity 0.15 --min-margin 10
```

### Cache Management

```bash
# Force refresh all data (ignore cache)
python screen_companies.py --force-refresh

# Use cached data only (no API calls)
python screen_companies.py --offline

# Change cache TTL to 3 days
python screen_companies.py --cache-ttl 3
```

### Using Different Presets

```bash
# Deep value screen
python screen_companies.py --preset deep_value --top 20

# Li Lu classic methodology
python screen_companies.py --preset li_lu_classic

# Quality at any price
python screen_companies.py --preset quality_any_price
```

## Command-Line Options

```
Screening Options:
  --preset PRESET       Use preset configuration (52_week_low_quality, deep_value, etc.)
  --list-presets        List all available presets
  --universe {sp500,small_mid_cap,all}
                        Company universe to screen

Filter Options:
  --min-rodc FLOAT      Minimum RODC percentage (e.g., 30)
  --max-pe FLOAT        Maximum P/E ratio (e.g., 15)
  --max-pb FLOAT        Maximum P/B ratio (e.g., 2.0)
  --max-proximity FLOAT Maximum proximity to 52w low, 0-1 (e.g., 0.20 = within 20%)
  --min-margin FLOAT    Minimum operating margin percentage

Output Options:
  --top N               Number of top candidates to output (default: 50)
  --output FILE         Output CSV filename

Cache Options:
  --force-refresh       Force refresh all data (ignore cache)
  --offline             Use cached data only (no API calls)
  --cache-ttl DAYS      Cache TTL in days (default: 7)

API Options:
  --api-key KEY         Massive.com API key (or set MASSIVE_API_KEY env var)
```

## Understanding the Output

### CSV Columns

- **rank**: Ranking (1 = best opportunity)
- **ticker**: Stock ticker symbol
- **company_name**: Company name
- **proximity_to_52w_low**: 0.00 = at 52w low, 1.00 = at 52w high (lower is better)
- **current_price**: Current stock price
- **52w_low / 52w_high**: 52-week price range
- **rodc_pct**: Return on Deployed Capital (Li Lu's key metric)
- **pe_operating**: P/E ratio on operating earnings (pre-tax, pre-interest)
- **pb_ratio**: Price-to-Book ratio
- **market_cap**: Market capitalization
- **operating_margin_pct**: Operating margin percentage
- **revenue_ttm**: Trailing twelve-month revenue
- **operating_earnings_ttm**: Operating earnings (EBIT)
- **deployed_capital**: Capital deployed in operations
- **asset_profile**: Business asset intensity classification

### Interpreting Results

**Strong Candidates:**
- Proximity to 52w low: <0.10 (within 10% of low)
- RODC: >30% (strong business)
- P/E: <15x (reasonable valuation)
- Operating margin: >10% (profitable operations)

**Li Lu's Targets:**
- RODC >50%: "That is not a bad business!"
- Trading near book value (P/B <1.5x)
- P/E on operating earnings <10x

## Performance

### First Run (No Cache)
- S&P 500 (~500 companies): 15-20 minutes
- Small/Mid-Cap (~2,000 companies): 40-60 minutes

### Subsequent Runs (With Cache)
- S&P 500: 5-8 minutes (70% cache hit rate)
- Small/Mid-Cap: 12-27 minutes

### Cache Statistics

Cache is stored at: `~/.value_snapshot/cache/screening.db`

View cache statistics in the summary report after each run.

## Testing

Run a quick test with a small sample:

```bash
# Test with first 20 S&P 500 companies
python test_screener.py

# Or provide API key directly
python test_screener.py your_api_key_here
```

## Module Architecture

```
scripts/
├── screen_companies.py      # Main screener orchestrator
├── company_universe.py      # S&P 500 / SEC company list fetching
├── screening_cache.py       # SQLite caching layer
├── screening_config.py      # Configuration and presets
├── fetch_financials.py      # Financial data fetching (+ 52-week data)
├── calculate_metrics.py     # Metric calculations (RODC, ratios)
└── test_screener.py         # Test script
```

## Data Sources

1. **SEC EDGAR**: Financial statements (primary source)
2. **Massive.com API**: Market data, 52-week price history
3. **Wikipedia**: S&P 500 constituent list (with SEC EDGAR fallback)

## Troubleshooting

### API Key Issues
```bash
# Verify API key is set
echo $MASSIVE_API_KEY

# Set it if missing
export MASSIVE_API_KEY=your_key_here
```

### Module Import Errors
```bash
# Ensure you're in the correct conda environment
conda activate cc_financial

# Verify Python is finding modules
cd scripts
python -c "import pandas; import tqdm; print('OK')"
```

### Cache Issues
```bash
# Clear cache if needed
rm -rf ~/.value_snapshot/cache/screening.db

# Run with force refresh
python screen_companies.py --force-refresh
```

### No Results
If screening returns no results:
1. Try relaxing filters (e.g., increase --max-proximity, --max-pe)
2. Check if cached data is stale (use --force-refresh)
3. Verify API key is working
4. Run test script to check system health

## Next Steps

### Phase 2: Small/Mid-Cap Expansion
```bash
# Screen small/mid-cap companies ($100M-$10B)
python screen_companies.py --universe small_mid_cap
```

### Phase 3: Advanced Features
- Scheduled screening (cron jobs)
- Email alerts for new opportunities
- Historical trending analysis
- Sector-relative scoring

## References

See `references/` directory for Li Lu's methodology:
- `li_lu_framework.md` - Core framework
- `interpretation.md` - Metric interpretation guide
- `methodology.md` - Detailed methodology

## License

Part of the value-snapshot project.
