#!/usr/bin/env python3
"""
Compare multiple companies using Li Lu's value investing methodology.

Usage:
    python compare_companies.py TICKER1 TICKER2 [TICKER3] [TICKER4] [API_KEY]

Example:
    python compare_companies.py GOOG MSFT
    python compare_companies.py PDD BABA AMZN your_api_key_here

Compares 2-4 companies side-by-side on key value investing metrics.
"""

import sys
import json
import subprocess
from pathlib import Path

def fetch_and_calculate(ticker, api_key):
    """Fetch financials and calculate metrics for a single company."""
    script_dir = Path(__file__).parent

    # Run fetch_financials.py
    fetch_cmd = [
        sys.executable,
        str(script_dir / 'fetch_financials.py'),
        ticker
    ]
    if api_key:
        fetch_cmd.append(api_key)

    try:
        fetch_result = subprocess.run(
            fetch_cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        if fetch_result.returncode != 0:
            return {"error": f"Failed to fetch data for {ticker}"}

        # Parse JSON from fetch_financials
        financial_data = json.loads(fetch_result.stdout)

        if "error" in financial_data:
            return financial_data

        # Run calculate_metrics.py
        calc_cmd = [
            sys.executable,
            str(script_dir / 'calculate_metrics.py'),
            '-'
        ]

        calc_result = subprocess.run(
            calc_cmd,
            input=json.dumps(financial_data),
            capture_output=True,
            text=True,
            timeout=30
        )

        if calc_result.returncode != 0:
            return {"error": f"Failed to calculate metrics for {ticker}"}

        # Parse output - extract JSON from the output
        output_lines = calc_result.stdout.split('\n')
        json_start = -1
        for i, line in enumerate(output_lines):
            if line.strip() == 'JSON Output:':
                json_start = i + 1
                break

        if json_start > 0:
            json_text = '\n'.join(output_lines[json_start:])
            metrics = json.loads(json_text)
            return metrics
        else:
            return {"error": f"Could not parse metrics for {ticker}"}

    except subprocess.TimeoutExpired:
        return {"error": f"Timeout fetching data for {ticker}"}
    except json.JSONDecodeError as e:
        return {"error": f"JSON parse error for {ticker}: {e}"}
    except Exception as e:
        return {"error": f"Error processing {ticker}: {e}"}


def format_number(value, is_currency=True, is_percentage=False):
    """Format numbers for display."""
    if value is None:
        return "N/A"

    if is_percentage:
        return f"{value:.1f}%"

    if is_currency:
        if abs(value) >= 1e9:
            return f"${value/1e9:.1f}B"
        elif abs(value) >= 1e6:
            return f"${value/1e6:.0f}M"
        else:
            return f"${value:,.0f}"

    return f"{value:.2f}"


def print_comparison_table(companies_data):
    """Print comparison table of companies."""

    if not companies_data:
        print("No data to compare")
        return

    # Filter out errors
    valid_companies = [c for c in companies_data if "error" not in c]

    if not valid_companies:
        print("No valid company data")
        for c in companies_data:
            if "error" in c:
                print(f"Error: {c['error']}")
        return

    tickers = [c['ticker'] for c in valid_companies]

    print("\n" + "="*100)
    print("COMPANY COMPARISON - Li Lu's Value Investing Framework")
    print("="*100)
    print()

    # Company names
    print("COMPANIES:")
    for c in valid_companies:
        company_name = c.get('company', 'Unknown')
        if len(company_name) > 60:
            company_name = company_name[:57] + "..."
        print(f"  {c['ticker']}: {company_name}")
    print()

    # Quick Check - Valuation
    print("🎯 VALUATION METRICS (Is it cheap?)")
    print("-" * 100)

    # Header
    header = f"{'Metric':<30}"
    for ticker in tickers:
        header += f" | {ticker:>12}"
    header += " | Li Lu Target"
    print(header)
    print("-" * 100)

    # Market Cap
    row = f"{'Market Cap':<30}"
    for c in valid_companies:
        row += f" | {format_number(c.get('market_cap')):>12}"
    row += " | N/A"
    print(row)

    # P/B Ratio
    row = f"{'P/B Ratio':<30}"
    for c in valid_companies:
        val = c.get('valuation_ratios', {}).get('pb_ratio')
        formatted = format_number(val, is_currency=False) if val else "N/A"
        row += f" | {formatted:>12}"
    row += " | < 1.5x"
    print(row)

    # P/E Operating
    row = f"{'P/E (Operating)':<30}"
    for c in valid_companies:
        val = c.get('valuation_ratios', {}).get('pe_operating')
        formatted = format_number(val, is_currency=False) if val else "N/A"
        row += f" | {formatted:>12}"
    row += " | < 10x"
    print(row)

    print()

    # Operating Quality
    print("📊 OPERATING QUALITY (Is the business good?)")
    print("-" * 100)

    header = f"{'Metric':<30}"
    for ticker in tickers:
        header += f" | {ticker:>12}"
    header += " | Li Lu Target"
    print(header)
    print("-" * 100)

    # Revenue
    row = f"{'Revenue (TTM)':<30}"
    for c in valid_companies:
        row += f" | {format_number(c.get('revenue_ttm')):>12}"
    row += " | N/A"
    print(row)

    # Operating Margin
    row = f"{'Operating Margin':<30}"
    for c in valid_companies:
        val = c.get('operating_margin_pct')
        formatted = format_number(val, is_currency=False, is_percentage=True) if val else "N/A"
        row += f" | {formatted:>12}"
    row += " | >20%"
    print(row)

    # Operating Earnings
    row = f"{'Operating Earnings':<30}"
    for c in valid_companies:
        row += f" | {format_number(c.get('operating_earnings_ttm')):>12}"
    row += " | N/A"
    print(row)

    # RODC - Most Important!
    row = f"{'RODC ⭐':<30}"
    for c in valid_companies:
        val = c.get('rodc_pct')
        formatted = format_number(val, is_currency=False, is_percentage=True) if val else "N/A"
        row += f" | {formatted:>12}"
    row += " | >50%"
    print(row)

    # Asset Profile
    row = f"{'Asset Profile':<30}"
    for c in valid_companies:
        profile = c.get('asset_profile', 'Unknown')
        if len(profile) > 12:
            profile = profile[:10] + ".."
        row += f" | {profile:>12}"
    row += " | Asset-light"
    print(row)

    print()

    # Capital Structure
    print("💰 CAPITAL STRUCTURE")
    print("-" * 100)

    header = f"{'Metric':<30}"
    for ticker in tickers:
        header += f" | {ticker:>12}"
    header += " | Best Practice"
    print(header)
    print("-" * 100)

    # Cash
    row = f"{'Cash & Liquid Assets':<30}"
    for c in valid_companies:
        cash = c.get('book_value_components', {}).get('liquid_assets')
        row += f" | {format_number(cash):>12}"
    row += " | Adequate"
    print(row)

    # Working Capital
    row = f"{'Working Capital':<30}"
    for c in valid_companies:
        wc = c.get('book_value_components', {}).get('working_capital')
        row += f" | {format_number(wc):>12}"
    row += " | Positive"
    print(row)

    # Deployed Capital
    row = f"{'Deployed Capital':<30}"
    for c in valid_companies:
        row += f" | {format_number(c.get('deployed_capital')):>12}"
    row += " | Efficient"
    print(row)

    # Goodwill
    row = f"{'Goodwill':<30}"
    for c in valid_companies:
        goodwill = c.get('book_value_components', {}).get('goodwill')
        row += f" | {format_number(goodwill):>12}"
    row += " | Low/None"
    print(row)

    # Tangible Book
    row = f"{'Tangible Book Value':<30}"
    for c in valid_companies:
        tbv = c.get('book_value_components', {}).get('tangible_book_value')
        row += f" | {format_number(tbv):>12}"
    row += " | High"
    print(row)

    print()
    print("="*100)
    print()


def analyze_comparison(companies_data):
    """Provide Li Lu's perspective on which company is best."""

    valid_companies = [c for c in companies_data if "error" not in c]

    if len(valid_companies) < 2:
        return

    print("💡 LI LU'S ANALYSIS")
    print("="*100)
    print()

    # Find best on each metric
    best_rodc = max(valid_companies, key=lambda c: c.get('rodc_pct', 0))
    best_pe = min([c for c in valid_companies if c.get('valuation_ratios', {}).get('pe_operating')],
                  key=lambda c: c.get('valuation_ratios', {}).get('pe_operating', 999))
    best_margin = max(valid_companies, key=lambda c: c.get('operating_margin_pct', 0))

    print("WINNERS BY METRIC:")
    print(f"  Best RODC (Capital Efficiency): {best_rodc['ticker']} at {best_rodc.get('rodc_pct', 0):.1f}%")
    print(f"  Cheapest (P/E):                 {best_pe['ticker']} at {best_pe.get('valuation_ratios', {}).get('pe_operating', 0):.1f}x")
    print(f"  Highest Operating Margin:       {best_margin['ticker']} at {best_margin.get('operating_margin_pct', 0):.1f}%")
    print()

    # Calculate scores
    print("OVERALL ASSESSMENT:")
    print()

    for c in valid_companies:
        ticker = c['ticker']
        rodc = c.get('rodc_pct', 0)
        pe = c.get('valuation_ratios', {}).get('pe_operating', 999)
        pb = c.get('valuation_ratios', {}).get('pb_ratio', 999)
        margin = c.get('operating_margin_pct', 0)

        print(f"{ticker}:")

        # Business Quality
        if rodc > 50:
            print(f"  ✓✓✓ EXCEPTIONAL business quality (RODC {rodc:.1f}%)")
        elif rodc > 30:
            print(f"  ✓✓ STRONG business quality (RODC {rodc:.1f}%)")
        elif rodc > 15:
            print(f"  ✓ GOOD business quality (RODC {rodc:.1f}%)")
        else:
            print(f"  ? MODEST business quality (RODC {rodc:.1f}%)")

        # Valuation
        if pe < 10 and pb < 1.5:
            print(f"  ✓✓ CHEAP (P/E {pe:.1f}x, P/B {pb:.1f}x)")
        elif pe < 15:
            print(f"  ✓ REASONABLE (P/E {pe:.1f}x)")
        else:
            print(f"  ✗ EXPENSIVE (P/E {pe:.1f}x)")

        # Overall verdict
        if rodc > 30 and pe < 10:
            print(f"  🎯 STRONG CANDIDATE - Good business at cheap price!")
        elif rodc > 50 and pe < 15:
            print(f"  🎯 QUALITY BUY - Exceptional business at reasonable price")
        elif rodc > 30:
            print(f"  ⚠️  WAIT FOR PULLBACK - Good business but too expensive")
        else:
            print(f"  ⏸  PASS - Doesn't meet Li Lu's standards")

        print()

    # Final recommendation
    print("-" * 100)
    print()
    print("LI LU'S LIKELY CHOICE:")
    print()

    # Score each company
    scores = []
    for c in valid_companies:
        rodc = c.get('rodc_pct', 0)
        pe = c.get('valuation_ratios', {}).get('pe_operating', 999)
        pb = c.get('valuation_ratios', {}).get('pb_ratio', 999)

        # Simple scoring: Quality (0-3) + Value (0-3)
        quality_score = 0
        if rodc > 50: quality_score = 3
        elif rodc > 30: quality_score = 2
        elif rodc > 15: quality_score = 1

        value_score = 0
        if pe < 10 and pb < 1.5: value_score = 3
        elif pe < 10 or pb < 1.5: value_score = 2
        elif pe < 15: value_score = 1

        total = quality_score + value_score
        scores.append((c['ticker'], total, quality_score, value_score, rodc, pe))

    scores.sort(key=lambda x: x[1], reverse=True)

    winner = scores[0]
    print(f"Best Overall: {winner[0]}")
    print(f"  Quality Score: {winner[2]}/3 (RODC {winner[4]:.1f}%)")
    print(f"  Value Score:   {winner[3]}/3 (P/E {winner[5]:.1f}x)")
    print(f"  Total Score:   {winner[1]}/6")
    print()

    if winner[1] >= 5:
        print("✓ Li Lu would likely INVEST at these levels")
    elif winner[1] >= 4:
        print("~ Li Lu might CONSIDER with deep due diligence")
    else:
        print("✗ Li Lu would likely PASS - Wait for better entry point")

    print()


def main():
    if len(sys.argv) < 3:
        print("Usage: python compare_companies.py TICKER1 TICKER2 [TICKER3] [TICKER4] [API_KEY]")
        print("Example: python compare_companies.py GOOG MSFT")
        print("Example: python compare_companies.py PDD BABA AMZN your_api_key")
        sys.exit(1)

    # Parse arguments
    tickers = []
    api_key = None

    for arg in sys.argv[1:]:
        if arg.startswith('-'):
            continue
        elif len(arg) > 10 and not arg.isupper():
            # Likely API key (longer than typical ticker)
            api_key = arg
        else:
            tickers.append(arg.upper())

    if len(tickers) < 2:
        print("Error: Please provide at least 2 tickers to compare")
        sys.exit(1)

    if len(tickers) > 4:
        print("Warning: Comparing more than 4 companies. Using first 4.")
        tickers = tickers[:4]

    # Check for API key
    if not api_key:
        import os
        api_key = os.environ.get('MASSIVE_API_KEY')

    if not api_key:
        print("Error: API key required. Set MASSIVE_API_KEY environment variable or pass as argument.")
        sys.exit(1)

    print("Fetching data for companies:", ", ".join(tickers))
    print()

    # Fetch data for all companies
    companies_data = []
    for ticker in tickers:
        print(f"Analyzing {ticker}...", file=sys.stderr)
        data = fetch_and_calculate(ticker, api_key)
        companies_data.append(data)

    # Print comparison
    print_comparison_table(companies_data)

    # Provide analysis
    analyze_comparison(companies_data)


if __name__ == "__main__":
    main()
