#!/usr/bin/env python3
"""
Calculate value investing metrics from financial data.

This script implements Li Lu's methodology:
- Operating Earnings (EBIT): Revenue × Operating Margin
- Deployed Capital: (Current Assets - Cash) - Current Liabilities + Net PP&E
- RODC (Return on Deployed Capital): Operating Earnings ÷ Deployed Capital

Usage:
    python calculate_metrics.py <financial_data.json>

Or use as a module:
    from calculate_metrics import calculate_value_metrics
"""

import sys
import json


def calculate_value_metrics(financial_data):
    """
    Calculate value investing metrics from financial data using Li Lu's methodology.

    Args:
        financial_data: Dictionary with financial data from fetch_financials.py

    Returns:
        Dictionary with calculated metrics and components
    """
    if "error" in financial_data:
        return financial_data

    # Extract data
    revenue = financial_data.get("revenue_ttm")
    operating_income = financial_data.get("operating_income_ttm")
    operating_margin = financial_data.get("operating_margin_pct")
    cash = financial_data.get("cash_and_short_term_investments", 0)
    current_assets = financial_data.get("total_current_assets", 0)
    current_liabilities = financial_data.get("total_current_liabilities", 0)
    net_ppe = financial_data.get("net_ppe", 0)
    goodwill = financial_data.get("goodwill", 0)
    intangible_assets = financial_data.get("intangible_assets", 0)
    stockholder_equity = financial_data.get("total_stockholder_equity")
    market_cap = financial_data.get("market_cap")

    # Calculate working capital (current assets - current liabilities)
    working_capital = current_assets - current_liabilities if current_assets and current_liabilities else None

    # Calculate tangible book value (exclude goodwill and intangibles)
    tangible_book_value = None
    if stockholder_equity:
        tangible_book_value = stockholder_equity - goodwill - intangible_assets

    # Calculate deployed capital - Li Lu's method
    # Li Lu: "Exclude ALL liquid assets from deployed capital"
    # Deployed Capital = Operating WC (ex-cash) + Fixed Assets
    # This is the capital ACTUALLY DEPLOYED in operations to generate earnings

    liquid_assets = cash  # All cash and short-term investments (NOT deployed)

    operating_working_capital = None
    if current_assets and current_liabilities and liquid_assets is not None:
        # Operating assets (deployed in business)
        operating_current_assets = current_assets - liquid_assets
        # Operating working capital = inventory + receivables - payables
        operating_working_capital = operating_current_assets - current_liabilities

    deployed_capital = None
    if operating_working_capital is not None and net_ppe is not None:
        # Deployed capital = Operating WC + Fixed Assets
        # This is what generates the operating earnings
        deployed_capital = operating_working_capital + net_ppe

        # For asset-light businesses with negative deployed capital (like Apple, PDD)
        # Use absolute value - shows capital deployed in operations (supplier financing)
        # This aligns with Li Lu's methodology: return on OPERATING capital deployed
        if deployed_capital < 0:
            deployed_capital = abs(deployed_capital)
        # If very small (near zero), use PP&E as minimum
        elif deployed_capital < (net_ppe * 0.1) and net_ppe > 0:
            deployed_capital = net_ppe
    elif net_ppe is not None:
        # Fallback: use fixed assets
        deployed_capital = net_ppe

    # Note: We treat ALL cash as excess (not deployed) per Li Lu's method
    # The business doesn't need cash sitting on balance sheet to generate operating earnings

    # Calculate RODC (Return on Deployed Capital) - Li Lu's signature metric
    rodc = None
    if operating_income and deployed_capital and deployed_capital > 0:
        rodc = (operating_income / deployed_capital) * 100

    # Calculate Enterprise Value (rough approximation)
    # EV = Market Cap - Net Cash
    enterprise_value = None
    if market_cap and cash:
        enterprise_value = market_cap - cash

    # Li Lu's Key Metrics
    # 1. Price-to-Book (P/B) - Li Lu looks for < 1.5x
    pb_ratio = None
    if market_cap and tangible_book_value and tangible_book_value > 0:
        pb_ratio = market_cap / tangible_book_value

    # 2. P/E on Operating Earnings (pre-tax, pre-interest) - Li Lu looks for 2-5x
    pe_operating = None
    if market_cap and operating_income and operating_income > 0:
        pe_operating = market_cap / operating_income

    # 3. Market Cap vs. Cash - Li Lu found companies trading BELOW cash!
    market_cap_vs_cash = None
    if market_cap and cash and cash > 0:
        market_cap_vs_cash = market_cap / cash

    # 4. Book Value Composition
    liquid_pct_of_book = None
    fixed_pct_of_book = None
    if tangible_book_value and tangible_book_value > 0:
        liquid_pct_of_book = (cash / tangible_book_value) * 100 if cash else 0
        fixed_pct_of_book = (net_ppe / tangible_book_value) * 100 if net_ppe else 0

    # 5. Asset Profile Classification
    asset_profile = "Unknown"
    if revenue and revenue > 0:
        ppe_to_revenue_ratio = (net_ppe / revenue) if net_ppe else 0
        if ppe_to_revenue_ratio < 0.10:
            asset_profile = "Asset-light platform (PP&E < 10% of revenue)"
        elif ppe_to_revenue_ratio < 0.30:
            asset_profile = "Moderate capital requirements"
        else:
            asset_profile = "Capital-intensive operations"

    # Prepare output
    result = {
        "company": financial_data.get("company_name"),
        "ticker": financial_data.get("ticker"),
        "currency": financial_data.get("currency", "USD"),
        "fetch_date": financial_data.get("fetch_date"),
        "filing_date": financial_data.get("filing_date"),  # Add filing date
        "data_source": financial_data.get("data_source", "Mixed sources"),

        # Top-line metrics
        "revenue_ttm": revenue,
        "operating_margin_pct": operating_margin,
        "operating_earnings_ttm": operating_income,

        # Li Lu's Quick Check Ratios
        "valuation_ratios": {
            "pb_ratio": pb_ratio,
            "pe_operating": pe_operating,
            "market_cap_vs_cash": market_cap_vs_cash,
            "market_cap_vs_book": pb_ratio  # Same as P/B
        },

        # Balance sheet breakdown
        "book_value_components": {
            "liquid_assets": cash,
            "liquid_pct_of_book": liquid_pct_of_book,
            "working_capital": working_capital,
            "operating_working_capital": operating_working_capital,
            "fixed_assets_net_ppe": net_ppe,
            "fixed_pct_of_book": fixed_pct_of_book,
            "goodwill": goodwill,
            "intangible_assets": intangible_assets,
            "tangible_book_value": tangible_book_value,
            "total_stockholder_equity": stockholder_equity
        },

        # Raw balance sheet items for transparency
        "total_current_assets": current_assets,
        "total_current_liabilities": current_liabilities,

        # Capital metrics
        "deployed_capital": deployed_capital,
        "asset_profile": asset_profile,

        # Valuation metrics
        "market_cap": market_cap,
        "enterprise_value_estimate": enterprise_value,
        "rodc_pct": rodc,  # Return on Deployed Capital (Li Lu's metric)

        # Additional context
        "current_price": financial_data.get("current_price"),
        "shares_outstanding": financial_data.get("shares_outstanding")
    }

    return result


def format_currency(value, currency="USD"):
    """Format a number as currency with appropriate suffix (M/B)"""
    if value is None:
        return "N/A"

    if abs(value) >= 1e9:
        return f"${value/1e9:.2f}B {currency}"
    elif abs(value) >= 1e6:
        return f"${value/1e6:.2f}M {currency}"
    else:
        return f"${value:,.0f} {currency}"


def print_value_snapshot(metrics):
    """Print formatted value snapshot in Li Lu's 5-minute analysis style"""
    if "error" in metrics:
        print(f"Error: {metrics['error']}")
        return

    currency = metrics.get("currency", "USD")
    valuation = metrics.get("valuation_ratios", {})
    bv = metrics['book_value_components']

    print("\n" + "="*75)
    print(f"VALUE SNAPSHOT: {metrics['company']} ({metrics['ticker']})")
    print(f"Analysis Date: {metrics['fetch_date']}                 Source: {metrics.get('data_source', 'Mixed')}")
    print("="*75)

    # Data timestamp information
    filing_date = metrics.get('filing_date')
    data_source = metrics.get('data_source', '')

    if filing_date:
        print(f"\n⏱  DATA TIMESTAMPS")
        print(f"  Financial Data: SEC filing as of {filing_date}")
        print(f"  Market Data:    Current price as of {metrics['fetch_date']} (${metrics.get('current_price', 'N/A')}/share)")

        # Add note about data currency for foreign filers
        if 'EDGAR' in data_source and filing_date:
            from datetime import datetime
            try:
                file_date = datetime.strptime(filing_date, '%Y-%m-%d')
                fetch_date = datetime.strptime(metrics['fetch_date'], '%Y-%m-%d')
                months_old = (fetch_date.year - file_date.year) * 12 + (fetch_date.month - file_date.month)

                if months_old > 6:
                    print(f"  Note:           Data is {months_old} months old - most recent complete filing")
                    print(f"                  (Foreign filers file annual 20-F; interim 6-K often lacks full data)")
            except:
                pass

    print()

    # Li Lu's Quick Check - "Is it cheap?"
    print("🎯 QUICK CHECK (Is it cheap?)")
    print(f"  Market Cap:         {format_currency(metrics['market_cap'], currency):<20} P/B:   {valuation['pb_ratio']:.2f}x" if valuation.get('pb_ratio') else f"  Market Cap:         {format_currency(metrics['market_cap'], currency):<20} P/B:   N/A")
    print(f"  Tangible Book:      {format_currency(bv['tangible_book_value'], currency):<20} P/E:   {valuation['pe_operating']:.2f}x (pre-tax)" if valuation.get('pe_operating') else f"  Tangible Book:      {format_currency(bv['tangible_book_value'], currency):<20} P/E:   N/A")
    print()

    # Trading multiples
    if valuation.get('pb_ratio'):
        if valuation['pb_ratio'] < 1.0:
            print(f"  ✓ Trading at {valuation['pb_ratio']:.1f}x book (BELOW tangible assets!)")
        elif valuation['pb_ratio'] < 1.5:
            print(f"  ✓ Trading at {valuation['pb_ratio']:.1f}x book (attractive)")
        else:
            print(f"    Trading at {valuation['pb_ratio']:.1f}x book")

    if valuation.get('market_cap_vs_cash'):
        if valuation['market_cap_vs_cash'] < 1.0:
            print(f"  ✓✓ TRADING BELOW CASH! (Market cap = {valuation['market_cap_vs_cash']:.2f}x cash)")
        elif valuation['market_cap_vs_cash'] < 2.0:
            print(f"  ✓ Strong cash position (Market cap = {valuation['market_cap_vs_cash']:.2f}x cash)")

    print()

    # Operating Quality - "Is the business good?"
    print("📊 OPERATING QUALITY (Is the business good?)")
    print(f"  Revenue (TTM):      {format_currency(metrics['revenue_ttm'], currency)}")
    print(f"  Operating Margin:   {metrics['operating_margin_pct']:.2f}%" if metrics['operating_margin_pct'] else "  Operating Margin:   N/A")
    print(f"  Operating Earnings: {format_currency(metrics['operating_earnings_ttm'], currency)} ⭐ (pre-tax, pre-interest)")
    print()

    rodc = metrics.get('rodc_pct')
    if rodc:
        print(f"  RODC:               {rodc:.2f}%  ", end="")
        if rodc > 50:
            print("[EXCEPTIONAL - Li Lu target!]")
        elif rodc > 30:
            print("[STRONG]")
        elif rodc > 15:
            print("[GOOD]")
        elif rodc > 0:
            print("[MODEST]")
        else:
            print("[NEGATIVE]")
    else:
        print("  RODC:               N/A")

    print(f"  Asset Profile:      {metrics.get('asset_profile', 'Unknown')}")
    print()

    # Capital Structure - "What are you buying?"
    print("💰 CAPITAL STRUCTURE (What are you buying?)")
    liquid_pct = bv.get('liquid_pct_of_book', 0)
    fixed_pct = bv.get('fixed_pct_of_book', 0)

    # Show balance sheet components
    current_assets = metrics.get('total_current_assets')
    current_liabilities = metrics.get('total_current_liabilities')

    if current_assets and current_liabilities:
        print(f"  Current Assets:     {format_currency(current_assets, currency)}")
        print(f"  Current Liabilities:{format_currency(current_liabilities, currency)}")
        print(f"  Working Capital:    {format_currency(bv['working_capital'], currency):<20} (net current assets)")
        print()

    print(f"  Liquid Assets:      {format_currency(bv['liquid_assets'], currency):<20} ({liquid_pct:.0f}% of book) - NOT deployed" if liquid_pct else f"  Liquid Assets:      {format_currency(bv['liquid_assets'], currency):<20} - NOT deployed")
    print(f"  Operating WC:       {format_currency(bv['operating_working_capital'], currency):<20} (non-cash working capital)")
    print(f"  Fixed Assets (PP&E):{format_currency(bv['fixed_assets_net_ppe'], currency):<20} ({fixed_pct:.0f}% of book) - deployed" if fixed_pct else f"  Fixed Assets (PP&E):{format_currency(bv['fixed_assets_net_ppe'], currency):<20} - deployed")
    print(f"  {'─'*50}")
    print(f"  Deployed Capital:   {format_currency(metrics['deployed_capital'], currency):<20} (generates earnings)")
    print()
    if bv.get('goodwill') and bv['goodwill'] > 0:
        goodwill_pct = (bv['goodwill'] / bv['tangible_book_value'] * 100) if bv.get('tangible_book_value') and bv['tangible_book_value'] > 0 else 0
        if goodwill_pct > 30:
            print(f"  ⚠ Goodwill:          {format_currency(bv['goodwill'], currency)} ({goodwill_pct:.0f}% of equity - HIGH)")
        else:
            print(f"  Goodwill:           {format_currency(bv['goodwill'], currency)} (exclude from analysis)")
        print()

    # Margin of Safety
    print("🔍 MARGIN OF SAFETY")
    print(f"  ✓ Tangible assets:  {format_currency(bv['tangible_book_value'], currency)}")
    print(f"  ✓ Liquid cushion:   {format_currency(bv['liquid_assets'], currency)} cash")

    # Asset-light check
    if metrics.get('asset_profile') and 'Asset-light' in metrics['asset_profile']:
        print(f"  ✓ Asset-light model: Minimal PP&E required")

    # Downside calculation
    if metrics.get('shares_outstanding') and bv.get('tangible_book_value'):
        downside_price = bv['tangible_book_value'] / metrics['shares_outstanding']
        print(f"  ✓ Downside at:      ${downside_price:.2f}/share (tangible book value)")
    print()

    # Investment Thesis Check
    print("📈 INVESTMENT THESIS CHECKLIST")

    # Cheap?
    cheap = False
    if valuation.get('pb_ratio') and valuation['pb_ratio'] < 1.5:
        cheap = True
        print(f"  [✓] Cheap? P/B = {valuation['pb_ratio']:.2f}x (< 1.5x ✓)")
    elif valuation.get('pe_operating') and valuation['pe_operating'] < 10:
        cheap = True
        print(f"  [✓] Cheap? P/E = {valuation['pe_operating']:.2f}x (< 10x ✓)")
    else:
        pb_str = f"{valuation.get('pb_ratio', 'N/A'):.2f}" if valuation.get('pb_ratio') else "N/A"
        pe_str = f"{valuation.get('pe_operating', 'N/A'):.2f}" if valuation.get('pe_operating') else "N/A"
        print(f"  [ ] Cheap? P/B = {pb_str}, P/E = {pe_str}")

    # Good business?
    good_business = False
    if rodc and rodc > 15:
        good_business = True
        print(f"  [✓] Good Business? RODC = {rodc:.1f}% (> 15% ✓)")
    elif rodc:
        print(f"  [ ] Good Business? RODC = {rodc:.1f}%")
    else:
        print(f"  [ ] Good Business? RODC = N/A")

    # Asset protection?
    asset_protection = False
    if bv.get('tangible_book_value') and metrics.get('market_cap'):
        if bv['tangible_book_value'] > metrics['market_cap'] * 0.5:
            asset_protection = True
            print(f"  [✓] Asset Protection? Book = {format_currency(bv['tangible_book_value'], currency)} ✓")
        else:
            print(f"  [ ] Asset Protection? Book = {format_currency(bv['tangible_book_value'], currency)}")

    print()

    # Li Lu's Final Comment
    if rodc and rodc > 50:
        print("💡 Li Lu's Take: \"RODC > 50% - That is not a bad business!\"")
        print("   Exceptional returns on deployed capital = competitive moat")
    elif rodc and rodc > 30:
        print("💡 Li Lu's Take: Strong capital efficiency with good returns")
    elif cheap and good_business:
        print("💡 Li Lu's Take: Cheap valuation + decent business = potential opportunity")
    elif valuation.get('market_cap_vs_cash') and valuation['market_cap_vs_cash'] < 1.0:
        print("💡 Li Lu's Take: Trading below cash - investigate why!")
        print("   (Hyundai H&S example: $60M market cap, $70M cash!)")

    print()


def main():
    if len(sys.argv) != 2:
        print("Usage: python calculate_metrics.py <financial_data.json>")
        print("Or pipe from fetch_financials.py:")
        print("  python fetch_financials.py TSLA | python calculate_metrics.py -")
        sys.exit(1)

    input_file = sys.argv[1]

    # Read financial data
    if input_file == "-":
        financial_data = json.load(sys.stdin)
    else:
        with open(input_file, 'r') as f:
            financial_data = json.load(f)

    # Calculate metrics
    metrics = calculate_value_metrics(financial_data)

    # Print formatted output
    print_value_snapshot(metrics)

    # Also output JSON for programmatic use
    print("\nJSON Output:")
    print(json.dumps(metrics, indent=2, default=str))


if __name__ == "__main__":
    main()
