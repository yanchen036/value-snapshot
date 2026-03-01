#!/usr/bin/env python3
"""
Fetch financial data for a company using SEC EDGAR (primary) and Massive.com API (market data).

Usage:
    python fetch_financials.py TICKER [API_KEY]

Example:
    python fetch_financials.py TSLA
    python fetch_financials.py PDD your_api_key_here

If API_KEY is not provided as argument, it will look for MASSIVE_API_KEY environment variable.
"""

import sys
import json
import os
import requests
from datetime import datetime
import time
import re


def get_cik_from_ticker(ticker):
    """Get CIK number from ticker using SEC company tickers JSON."""
    try:
        headers = {
            'User-Agent': 'ValueSnapshot/1.0 (contact@example.com)',
            'Accept-Encoding': 'gzip, deflate'
        }

        # SEC provides a JSON file mapping tickers to CIKs
        url = "https://www.sec.gov/files/company_tickers.json"
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        data = response.json()

        # Search for ticker (case insensitive)
        ticker_upper = ticker.upper()
        for item in data.values():
            if item.get('ticker', '').upper() == ticker_upper:
                # CIK is stored as integer, pad to 10 digits
                cik = str(item['cik_str']).zfill(10)
                return cik

        return None
    except Exception as e:
        print(f"Warning: Could not fetch CIK for {ticker}: {e}", file=sys.stderr)
        return None


def fetch_from_sec_edgar(ticker):
    """
    Fetch financial data from SEC EDGAR using Company Facts API.
    Returns financial data from most recent filings.
    """
    try:
        # Get CIK number
        cik = get_cik_from_ticker(ticker)
        if not cik:
            return None

        headers = {
            'User-Agent': 'ValueSnapshot/1.0 (contact@example.com)',
            'Accept-Encoding': 'gzip, deflate'
        }

        # SEC Company Facts API - provides XBRL tagged data
        url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"

        time.sleep(0.1)  # SEC rate limiting
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        data = response.json()

        # Extract facts from US-GAAP or IFRS
        facts = data.get('facts', {})
        us_gaap = facts.get('us-gaap', {})
        ifrs = facts.get('ifrs-full', {})

        # Use US-GAAP if available, else IFRS
        gaap_data = us_gaap if us_gaap else ifrs

        if not gaap_data:
            return None

        # Track most recent filing date
        most_recent_filing_date = None

        # Helper function to get most recent value
        def get_recent_value(fact_name, form_types=['10-K', '10-Q', '20-F', '6-K'], unit='USD'):
            nonlocal most_recent_filing_date

            if fact_name not in gaap_data:
                return None

            fact_data = gaap_data[fact_name]
            units_data = fact_data.get('units', {})

            # Try USD first, then other currency units
            unit_values = units_data.get(unit, [])
            if not unit_values and units_data:
                # Try first available unit
                unit_values = list(units_data.values())[0]

            if not unit_values:
                return None

            # Filter by form type and get most recent
            valid_filings = [
                f for f in unit_values
                if f.get('form') in form_types and f.get('val') is not None
            ]

            if not valid_filings:
                return None

            # Sort by filing date (most recent first)
            valid_filings.sort(key=lambda x: x.get('filed', ''), reverse=True)

            # Track the most recent filing date
            filing_date = valid_filings[0].get('filed')
            if filing_date and (not most_recent_filing_date or filing_date > most_recent_filing_date):
                most_recent_filing_date = filing_date

            return valid_filings[0].get('val')

        # Get most recent TTM/annual data
        # Revenue - try multiple field names
        revenue = (get_recent_value('Revenues') or
                  get_recent_value('RevenueFromContractWithCustomerExcludingAssessedTax') or
                  get_recent_value('SalesRevenueNet'))

        # Operating income
        operating_income = (get_recent_value('OperatingIncomeLoss') or
                          get_recent_value('IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest'))

        # Cost of revenue
        cost_of_revenue = get_recent_value('CostOfRevenue')

        # Balance sheet items
        cash = get_recent_value('CashAndCashEquivalentsAtCarryingValue')
        if not cash:
            cash = get_recent_value('Cash')

        current_assets = get_recent_value('AssetsCurrent')
        current_liabilities = get_recent_value('LiabilitiesCurrent')

        # PP&E
        net_ppe = (get_recent_value('PropertyPlantAndEquipmentNet') or
                  get_recent_value('PropertyPlantAndEquipmentAndFinanceLeaseRightOfUseAssetAfterAccumulatedDepreciationAndAmortization'))

        # Equity
        stockholder_equity = (get_recent_value('StockholdersEquity') or
                             get_recent_value('StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest'))

        # Goodwill and intangibles
        goodwill = get_recent_value('Goodwill') or 0
        intangible_assets = get_recent_value('IntangibleAssetsNetExcludingGoodwill') or 0

        # Short-term investments
        short_term_investments = get_recent_value('ShortTermInvestments') or 0

        total_cash = (cash or 0) + short_term_investments

        if not revenue or not operating_income:
            return None

        return {
            'revenue_ttm': revenue,
            'operating_income_ttm': operating_income,
            'cost_of_revenue': cost_of_revenue,
            'total_current_assets': current_assets,
            'total_current_liabilities': current_liabilities,
            'cash_and_short_term_investments': total_cash,
            'net_ppe': net_ppe or 0,
            'total_stockholder_equity': stockholder_equity,
            'currency': 'USD',
            'fiscal_period': 'Most Recent',
            'fiscal_year': '',
            'goodwill': goodwill,
            'intangible_assets': intangible_assets,
            'source': 'SEC EDGAR',
            'cik': cik,
            'filing_date': most_recent_filing_date  # Add filing date
        }

    except Exception as e:
        print(f"Warning: SEC EDGAR fetch failed: {e}", file=sys.stderr)
        return None


def fetch_from_massive_financials(ticker, api_key):
    """
    Fetch financial statements from Massive.com API.
    Used as fallback when SEC EDGAR doesn't have data.
    """
    base_url = "https://api.massive.com"
    headers = {"Authorization": f"Bearer {api_key}"}

    try:
        # Fetch financial statements (income, balance sheet, cash flow) - TTM data
        financials_url = f"{base_url}/vX/reference/financials"
        financials_params = {
            "ticker": ticker,
            "timeframe": "ttm",
            "limit": 1
        }
        financials_response = requests.get(financials_url, headers=headers, params=financials_params, timeout=10)
        financials_response.raise_for_status()
        financials_data = financials_response.json()

        if financials_data.get('status') != 'OK' or not financials_data.get('results'):
            return None

        # Extract financial data
        financial_report = financials_data['results'][0]
        financials = financial_report.get('financials', {})

        income_stmt = financials.get('income_statement', {})
        balance_sheet = financials.get('balance_sheet', {})

        # Extract data
        revenue_ttm = income_stmt.get('revenues', {}).get('value')
        operating_income_ttm = income_stmt.get('operating_income_loss', {}).get('value')
        cost_of_revenue = income_stmt.get('cost_of_revenue', {}).get('value')

        current_assets = balance_sheet.get('current_assets', {}).get('value')
        current_liabilities = balance_sheet.get('current_liabilities', {}).get('value')
        inventory = balance_sheet.get('inventory', {}).get('value', 0)

        # Estimate cash
        if current_assets and inventory is not None:
            total_cash = current_assets - inventory
        else:
            total_cash = balance_sheet.get('other_current_assets', {}).get('value', 0)

        net_ppe = balance_sheet.get('fixed_assets', {}).get('value', 0)
        stockholder_equity = balance_sheet.get('equity', {}).get('value') or \
                            balance_sheet.get('equity_attributable_to_parent', {}).get('value')

        currency = income_stmt.get('revenues', {}).get('unit', 'USD').upper()
        fiscal_period = financial_report.get('fiscal_period', 'TTM')
        fiscal_year = financial_report.get('fiscal_year', '')

        return {
            'revenue_ttm': revenue_ttm,
            'operating_income_ttm': operating_income_ttm,
            'cost_of_revenue': cost_of_revenue,
            'total_current_assets': current_assets,
            'total_current_liabilities': current_liabilities,
            'cash_and_short_term_investments': total_cash,
            'net_ppe': net_ppe,
            'total_stockholder_equity': stockholder_equity,
            'currency': currency,
            'fiscal_period': fiscal_period,
            'fiscal_year': fiscal_year,
            'goodwill': 0,
            'intangible_assets': 0,
            'source': 'Massive.com API'
        }

    except Exception as e:
        return None


def fetch_market_data_from_massive(ticker, api_key):
    """
    Fetch current market data (price, market cap) from Massive.com API.
    """
    base_url = "https://api.massive.com"
    headers = {"Authorization": f"Bearer {api_key}"}

    try:
        ticker_url = f"{base_url}/v3/reference/tickers/{ticker.upper()}"
        ticker_response = requests.get(ticker_url, headers=headers, timeout=10)
        ticker_response.raise_for_status()
        ticker_data = ticker_response.json()

        if ticker_data.get('status') != 'OK' or not ticker_data.get('results'):
            return None

        ticker_details = ticker_data['results']

        market_cap = ticker_details.get('market_cap')
        shares_outstanding = ticker_details.get('weighted_shares_outstanding')
        company_name = ticker_details.get('name', ticker.upper())

        # Calculate current price from market cap and shares
        current_price = None
        if market_cap and shares_outstanding and shares_outstanding > 0:
            current_price = market_cap / shares_outstanding

        return {
            'market_cap': market_cap,
            'shares_outstanding': shares_outstanding,
            'current_price': current_price,
            'company_name': company_name
        }

    except Exception as e:
        return None


def fetch_company_data(ticker, api_key=None):
    """
    Fetch TTM financial data for a given ticker.

    Strategy:
    1. PRIMARY: Try SEC EDGAR Company Facts API (works for ALL US-listed companies)
    2. ALWAYS: Get market data from Massive.com ticker API
    3. FALLBACK: Try Massive.com financials API if SEC EDGAR fails

    Returns a dictionary with all financial and market data.
    """
    if not api_key:
        api_key = os.environ.get('MASSIVE_API_KEY')

    if not api_key:
        return {"error": "API key required. Set MASSIVE_API_KEY environment variable or pass as argument."}

    print(f"Fetching data for {ticker}...", file=sys.stderr)
    print("Step 1: Trying SEC EDGAR (primary source)...", file=sys.stderr)

    # PRIMARY: Try to fetch financial data from SEC EDGAR
    financial_data = fetch_from_sec_edgar(ticker)

    if financial_data:
        print(f"✓ Successfully fetched from SEC EDGAR (CIK: {financial_data.get('cik')})", file=sys.stderr)
    else:
        print("✗ SEC EDGAR failed, trying Massive.com API (fallback)...", file=sys.stderr)
        # FALLBACK: Try Massive.com API
        financial_data = fetch_from_massive_financials(ticker, api_key)

        if financial_data:
            print("✓ Successfully fetched from Massive.com API", file=sys.stderr)

    # ALWAYS: Try to get market data from Massive.com
    print("Step 2: Fetching market data from Massive.com...", file=sys.stderr)
    market_data = fetch_market_data_from_massive(ticker, api_key)

    if not financial_data:
        if market_data:
            return {
                "error": f"No financial statement data available for {ticker}. "
                        f"The ticker exists (Market Cap: ${market_data['market_cap']/1e9:.2f}B) but financial statements could not be retrieved from SEC EDGAR or Massive.com API. "
                        f"Possible reasons: (1) Very recent IPO, (2) Delisted company, (3) Data not yet processed. "
                        f"Try checking SEC EDGAR directly at https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&ticker={ticker}",
                "ticker": ticker.upper(),
                "market_data_available": True,
                "market_cap": market_data.get('market_cap'),
                "company_name": market_data.get('company_name')
            }
        else:
            return {"error": f"No data available for {ticker}. Please verify the ticker symbol."}

    if not market_data:
        return {"error": f"Could not fetch market data for {ticker}"}

    print("✓ Successfully fetched market data", file=sys.stderr)

    # Calculate operating margin
    operating_margin = None
    if financial_data['revenue_ttm'] and financial_data['operating_income_ttm'] and financial_data['revenue_ttm'] != 0:
        operating_margin = (financial_data['operating_income_ttm'] / financial_data['revenue_ttm']) * 100

    # Combine all data
    result = {
        "ticker": ticker.upper(),
        "company_name": market_data['company_name'],
        "currency": financial_data.get('currency', 'USD'),
        "revenue_ttm": financial_data['revenue_ttm'],
        "operating_income_ttm": financial_data['operating_income_ttm'],
        "operating_margin_pct": operating_margin,
        "cash_and_short_term_investments": financial_data['cash_and_short_term_investments'],
        "total_current_assets": financial_data['total_current_assets'],
        "total_current_liabilities": financial_data['total_current_liabilities'],
        "net_ppe": financial_data['net_ppe'],
        "goodwill": financial_data['goodwill'],
        "intangible_assets": financial_data['intangible_assets'],
        "total_stockholder_equity": financial_data['total_stockholder_equity'],
        "market_cap": market_data['market_cap'],
        "shares_outstanding": market_data['shares_outstanding'],
        "current_price": market_data['current_price'],
        "fetch_date": datetime.now().strftime("%Y-%m-%d"),
        "fiscal_period": financial_data.get('fiscal_period'),
        "fiscal_year": financial_data.get('fiscal_year'),
        "cost_of_revenue": financial_data.get('cost_of_revenue'),
        "data_source": financial_data.get('source', 'Mixed sources'),
        "filing_date": financial_data.get('filing_date')  # Include filing date
    }

    return result


def main():
    if len(sys.argv) < 2:
        print("Usage: python fetch_financials.py TICKER [API_KEY]")
        print("Example: python fetch_financials.py TSLA")
        print("\nAPI Key can be provided as:")
        print("  1. Command line argument: python fetch_financials.py TSLA your_api_key")
        print("  2. Environment variable: export MASSIVE_API_KEY=your_api_key")
        sys.exit(1)

    ticker = sys.argv[1]
    api_key = sys.argv[2] if len(sys.argv) > 2 else None

    data = fetch_company_data(ticker, api_key)

    # Output as JSON for easy parsing
    print(json.dumps(data, indent=2, default=str))


if __name__ == "__main__":
    main()
