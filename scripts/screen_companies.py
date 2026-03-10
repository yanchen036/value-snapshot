#!/usr/bin/env python3
"""
Company Screener - Main Orchestration

Scan public companies and identify investment opportunities using Li Lu's methodology.
Focus on companies near 52-week lows with strong fundamentals.

Usage:
    # Basic screen with defaults (S&P 500, preset: 52_week_low_quality)
    python screen_companies.py

    # Use a preset
    python screen_companies.py --preset deep_value

    # Custom filters
    python screen_companies.py --min-rodc 25 --max-pe 12 --max-proximity 0.15

    # Force refresh all data (ignore cache)
    python screen_companies.py --force-refresh

    # Offline mode (use cached data only)
    python screen_companies.py --offline

Example:
    python screen_companies.py --preset 52_week_low_quality --top 30
"""

import os
import sys
import argparse
import json
from datetime import datetime
from typing import List, Dict, Optional
import pandas as pd
from tqdm import tqdm

# Import local modules
from screening_cache import ScreeningCache
from screening_config import ScreeningConfig, get_preset, list_presets, PRESET_DESCRIPTIONS
from company_universe import get_universe as fetch_universe
from fetch_financials import fetch_company_data, fetch_52week_data
from calculate_metrics import calculate_value_metrics


class CompanyScreener:
    """Main screening orchestrator"""

    def __init__(self, config: ScreeningConfig):
        """
        Initialize screener with configuration.

        Args:
            config: ScreeningConfig instance
        """
        self.config = config
        self.cache = ScreeningCache()

        # Statistics
        self.stats = {
            'total_companies': 0,
            'fetched': 0,
            'cached': 0,
            'failed': 0,
            'passed_filters': 0,
            'start_time': datetime.now()
        }

    def get_universe(self) -> List[str]:
        """
        Get list of companies to screen based on universe letter spec.
        Auto-builds the ticker cache from Massive.com if missing or stale.
        """
        print("\n" + "="*70)
        print("STEP 1: Building Company Universe")
        print("="*70)

        spec = self.config.universe.upper()
        label = 'All tickers' if spec == 'ALL' else f'Tickers starting with {spec}'
        print(f'Universe: {label}')

        tickers = fetch_universe(
            spec,
            api_key=self.config.api_key,
            cache_ttl_days=self.config.cache_ttl_days,
        )

        self.stats['total_companies'] = len(tickers)
        print(f'✓ Universe built: {len(tickers):,} companies')

        return tickers

    def fetch_data_batch(self, tickers: List[str]) -> List[Dict]:
        """
        Fetch financial and price data for a batch of tickers.

        Uses cache when available, fetches fresh data for stale/missing tickers.

        Args:
            tickers: List of ticker symbols

        Returns:
            List of company data dictionaries
        """
        print("\n" + "="*70)
        print("STEP 2: Fetching Financial Data")
        print("="*70)

        # Check which tickers need refresh
        if self.config.offline_mode:
            print("Offline mode: Using cached data only")
            stale_tickers = []
        elif self.config.force_refresh:
            print("Force refresh: Fetching all companies")
            stale_tickers = tickers
        else:
            print(f"Checking cache (TTL: {self.config.cache_ttl_days} days)...")
            stale_tickers = self.cache.get_stale_tickers(tickers, self.config.cache_ttl_days)
            print(f"  Cached: {len(tickers) - len(stale_tickers)} companies")
            print(f"  Need refresh: {len(stale_tickers)} companies")

        results = []

        # Process cached data first
        if not self.config.force_refresh:
            for ticker in tickers:
                if ticker not in stale_tickers:
                    cached = self.cache.get_cached_data(ticker, self.config.cache_ttl_days)
                    if cached and cached.get('metrics'):
                        # Use metrics data (already includes everything we need)
                        # Pull extra balance sheet fields from financial that metrics omits
                        fin = cached.get('financial', {})
                        combined = {
                            **cached['metrics'],
                            '52_week_data': cached.get('price_history', {}),
                            'operating_income_ttm': fin.get('operating_income_ttm'),
                            'cash_and_short_term_investments': fin.get('cash_and_short_term_investments'),
                            'net_ppe': fin.get('net_ppe'),
                        }
                        results.append(combined)
                        self.stats['cached'] += 1

        # Fetch fresh data for stale tickers
        if stale_tickers:
            print(f"\nFetching fresh data for {len(stale_tickers)} companies...")

            with tqdm(total=len(stale_tickers), desc="Fetching", unit="company") as pbar:
                for ticker in stale_tickers:
                    try:
                        # Fetch financial data
                        financial_data = fetch_company_data(ticker, self.config.api_key)

                        if 'error' in financial_data:
                            self.stats['failed'] += 1
                            pbar.update(1)
                            continue

                        # Fetch 52-week price data (optional)
                        price_data = fetch_52week_data(ticker, self.config.api_key)

                        if not price_data:
                            # Continue without 52-week data (use None)
                            price_data = {
                                'current_price': None,
                                '52_week_high': None,
                                '52_week_low': None,
                                'proximity_to_low': None,
                                'proximity_to_high': None
                            }

                        # Calculate metrics
                        metrics = calculate_value_metrics(financial_data)

                        if 'error' in metrics:
                            self.stats['failed'] += 1
                            pbar.update(1)
                            continue

                        # Use metrics data (already includes everything we need)
                        # Pull extra balance sheet fields from financial that metrics omits
                        combined = {
                            **metrics,
                            '52_week_data': price_data,
                            'operating_income_ttm': financial_data.get('operating_income_ttm'),
                            'cash_and_short_term_investments': financial_data.get('cash_and_short_term_investments'),
                            'net_ppe': financial_data.get('net_ppe'),
                        }

                        results.append(combined)

                        # Store in cache
                        self.cache.store_data(ticker, financial_data, metrics, price_data)

                        self.stats['fetched'] += 1

                    except Exception as e:
                        # Log error and continue
                        print(f"\n  Error processing {ticker}: {e}")
                        self.stats['failed'] += 1

                    pbar.update(1)

        print(f"\n✓ Data collected:")
        print(f"  Total: {len(results)} companies")
        print(f"  Fetched: {self.stats['fetched']}")
        print(f"  Cached: {self.stats['cached']}")
        print(f"  Failed: {self.stats['failed']}")

        return results

    def apply_filters(self, data: List[Dict]) -> pd.DataFrame:
        """
        Apply screening filters to company data.

        Args:
            data: List of company data dictionaries

        Returns:
            Filtered DataFrame with passing companies
        """
        print("\n" + "="*70)
        print("STEP 3: Applying Filters")
        print("="*70)

        # Convert to DataFrame
        df = pd.DataFrame(data)

        initial_count = len(df)
        print(f"Starting with {initial_count} companies")
        print(f"\nApplying filters:")
        print(f"  {self.config}")

        # Extract 52-week data from nested dict
        if '52_week_data' in df.columns:
            df['proximity_to_52w_low'] = df['52_week_data'].apply(
                lambda x: x.get('proximity_to_low') if isinstance(x, dict) else None
            )
            df['52_week_high'] = df['52_week_data'].apply(
                lambda x: x.get('52_week_high') if isinstance(x, dict) else None
            )
            df['52_week_low'] = df['52_week_data'].apply(
                lambda x: x.get('52_week_low') if isinstance(x, dict) else None
            )
            df['current_price_52w'] = df['52_week_data'].apply(
                lambda x: x.get('current_price') if isinstance(x, dict) else None
            )

            # Calculate distance from 52-week low (% above/below)
            # Positive = above low (normal), Negative = below low (new low)
            df['distance_from_52w_low_pct'] = df.apply(
                lambda row: ((row['current_price_52w'] - row['52_week_low']) / row['52_week_low'] * 100)
                if pd.notna(row['current_price_52w']) and pd.notna(row['52_week_low']) and row['52_week_low'] > 0
                else None,
                axis=1
            )

        # Filter: 52-week low proximity
        if self.config.proximity_to_52w_low_max is not None:
            before = len(df)
            df = df[
                (df['proximity_to_52w_low'].notna()) &
                (df['proximity_to_52w_low'] >= 0) &  # Valid range
                (df['proximity_to_52w_low'] <= self.config.proximity_to_52w_low_max)
            ]
            print(f"  52w low proximity <{self.config.proximity_to_52w_low_max*100:.0f}%: {len(df)} pass ({before-len(df)} filtered)")
        else:
            # No 52-week filter - just count companies with data
            with_data = len(df[df['proximity_to_52w_low'].notna()])
            print(f"  52w low data available: {with_data}/{len(df)} companies")

        if self.config.proximity_to_52w_low_min is not None:
            before = len(df)
            df = df[df['proximity_to_52w_low'] >= self.config.proximity_to_52w_low_min]
            print(f"  52w low proximity >{self.config.proximity_to_52w_low_min*100:.0f}%: {len(df)} pass ({before-len(df)} filtered)")

        # Filter: RODC
        if self.config.min_rodc is not None:
            before = len(df)
            df = df[
                (df['rodc_pct'].notna()) &
                (df['rodc_pct'] >= self.config.min_rodc)
            ]
            print(f"  RODC >{self.config.min_rodc}%: {len(df)} pass ({before-len(df)} filtered)")

        # Filter: Operating margin
        if self.config.min_operating_margin is not None:
            before = len(df)
            df = df[
                (df['operating_margin_pct'].notna()) &
                (df['operating_margin_pct'] >= self.config.min_operating_margin)
            ]
            print(f"  Operating margin >{self.config.min_operating_margin}%: {len(df)} pass ({before-len(df)} filtered)")

        # Filter: P/E ratio
        if self.config.max_pe_operating is not None:
            before = len(df)
            # Extract P/E from nested valuation_ratios dict
            if 'valuation_ratios' in df.columns:
                df['pe_operating'] = df['valuation_ratios'].apply(
                    lambda x: x.get('pe_operating') if isinstance(x, dict) else None
                )
            df = df[
                (df['pe_operating'].notna()) &
                (df['pe_operating'] > 0) &
                (df['pe_operating'] <= self.config.max_pe_operating)
            ]
            print(f"  P/E <{self.config.max_pe_operating}x: {len(df)} pass ({before-len(df)} filtered)")

        # Filter: P/B ratio
        if self.config.max_pb_ratio is not None:
            before = len(df)
            # Extract P/B from nested valuation_ratios dict
            if 'valuation_ratios' in df.columns:
                df['pb_ratio'] = df['valuation_ratios'].apply(
                    lambda x: x.get('pb_ratio') if isinstance(x, dict) else None
                )
            df = df[
                (df['pb_ratio'].notna()) &
                (df['pb_ratio'] > 0) &
                (df['pb_ratio'] <= self.config.max_pb_ratio)
            ]
            print(f"  P/B <{self.config.max_pb_ratio}x: {len(df)} pass ({before-len(df)} filtered)")

        # Filter: Working capital
        if self.config.positive_working_capital:
            before = len(df)
            # Extract working capital from nested book_value_components
            if 'book_value_components' in df.columns:
                df['working_capital'] = df['book_value_components'].apply(
                    lambda x: x.get('working_capital') if isinstance(x, dict) else None
                )
            df = df[
                (df['working_capital'].notna()) &
                (df['working_capital'] > 0)
            ]
            print(f"  Positive working capital: {len(df)} pass ({before-len(df)} filtered)")

        # Filter: Cash percentage of market cap
        if self.config.min_cash_pct_of_market_cap is not None:
            before = len(df)
            # Calculate cash % of market cap
            df['cash_pct_market_cap'] = df.apply(
                lambda row: (row.get('book_value_components', {}).get('liquid_assets', 0) / row.get('market_cap', 1))
                if isinstance(row.get('book_value_components'), dict) and row.get('market_cap', 0) > 0
                else 0,
                axis=1
            )
            df = df[df['cash_pct_market_cap'] >= self.config.min_cash_pct_of_market_cap]
            print(f"  Cash >{self.config.min_cash_pct_of_market_cap*100:.0f}% of market cap: {len(df)} pass ({before-len(df)} filtered)")

        self.stats['passed_filters'] = len(df)

        print(f"\n✓ Filtering complete:")
        print(f"  Started with: {initial_count}")
        print(f"  Passed filters: {len(df)} ({len(df)/initial_count*100:.1f}%)")

        return df

    def sort_and_rank(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Sort filtered companies and assign ranks.

        Args:
            df: Filtered DataFrame

        Returns:
            Sorted DataFrame with rank column
        """
        if df.empty:
            return df

        print("\n" + "="*70)
        print("STEP 4: Sorting and Ranking")
        print("="*70)

        sort_by = self.config.sort_by
        ascending = self.config.sort_ascending

        print(f"Sorting by: {sort_by} ({'ascending' if ascending else 'descending'})")

        # Ensure sort column exists
        if sort_by not in df.columns:
            print(f"Warning: Sort column '{sort_by}' not found, using distance_from_52w_low_pct")
            sort_by = 'distance_from_52w_low_pct'

        # Sort
        df = df.sort_values(by=sort_by, ascending=ascending)

        # Add rank
        df['rank'] = range(1, len(df) + 1)

        print(f"✓ Ranked {len(df)} companies")

        return df

    def export_results(self, df: pd.DataFrame, output_file: str = "screening_results.md"):
        """
        Export screening results to markdown and generate summary report.

        Args:
            df: Results DataFrame
            output_file: Output filename (will use .md extension)
        """
        print("\n" + "="*70)
        print("STEP 5: Exporting Results")
        print("="*70)

        if df.empty:
            print("No companies passed filters - no results to export")
            return

        # Change extension to .md for markdown
        if not output_file.endswith('.md'):
            output_file += '.md'

        # Prepare export DataFrame
        export_df = pd.DataFrame({
            'rank': df['rank'],
            'ticker': df['ticker'],
            'company_name': df['company'],
            'distance_from_52w_low_pct': df['distance_from_52w_low_pct'] if 'distance_from_52w_low_pct' in df.columns else None,
            'current_price': df['current_price_52w'] if 'current_price_52w' in df.columns else df['52_week_data'].apply(lambda x: x.get('current_price') if isinstance(x, dict) else None),
            '52w_low': df['52_week_low'],
            'rodc_pct': df['rodc_pct'],
            'pe_operating': df['pe_operating'] if 'pe_operating' in df.columns else df['valuation_ratios'].apply(
                lambda x: x.get('pe_operating') if isinstance(x, dict) else None
            ),
            'pb_ratio': df['pb_ratio'] if 'pb_ratio' in df.columns else df['valuation_ratios'].apply(
                lambda x: x.get('pb_ratio') if isinstance(x, dict) else None
            ),
            'market_cap': df['market_cap'],
            'operating_margin_pct': df['operating_margin_pct'],
            'revenue_ttm': df['revenue_ttm'],
            'operating_income_ttm': df['operating_income_ttm'] if 'operating_income_ttm' in df.columns else None,
            'total_current_assets': df['total_current_assets'] if 'total_current_assets' in df.columns else None,
            'cash_and_short_term_investments': df['cash_and_short_term_investments'] if 'cash_and_short_term_investments' in df.columns else None,
            'total_current_liabilities': df['total_current_liabilities'] if 'total_current_liabilities' in df.columns else None,
            'net_ppe': df['net_ppe'] if 'net_ppe' in df.columns else None,
            'operating_earnings_ttm': df['operating_earnings_ttm'],
            'deployed_capital': df['deployed_capital'],
            'asset_profile': df['asset_profile']
        })

        # Export to Markdown
        self._export_markdown(export_df, output_file)
        print(f"✓ Results saved to: {output_file}")

        # Generate summary report (also in markdown)
        summary_file = output_file.replace('.md', '_summary.md')
        self._generate_summary_report(df, export_df, summary_file)
        print(f"✓ Summary saved to: {summary_file}")

        # Store in cache for historical tracking
        run_id = f"screen_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        results_list = df.to_dict('records')
        self.cache.store_screening_results(run_id, results_list)

        print(f"✓ Results cached with run ID: {run_id}")

    def _export_markdown(self, df: pd.DataFrame, output_file: str):
        """Export results as markdown table"""
        with open(output_file, 'w') as f:
            f.write("# Company Screening Results\n\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"**Total Companies:** {len(df)}\n\n")

            # Main results table
            f.write("## Screening Results\n\n")
            f.write("| Rank | Ticker | Company | 52w Low % | Price | 52w Low | Op Margin | RODC | P/E | P/B | Market Cap | Revenue | Op Income | Curr Assets | Cash | Curr Liab | PP&E |\n")
            f.write("|------|--------|---------|-----------|-------|---------|-----------|------|-----|-----|------------|---------|-----------|-------------|------|-----------|------|\n")

            def fmt_financial(val):
                if pd.isna(val) or val is None:
                    return "N/A"
                if abs(val) >= 1e9:
                    return f"${val/1e9:.1f}B"
                if abs(val) >= 1e6:
                    return f"${val/1e6:.0f}M"
                return f"${val:.0f}"

            for _, row in df.iterrows():
                # Format values
                rank = int(row['rank'])
                ticker = row['ticker']
                company = row['company_name'][:25]

                # Distance from 52w low
                dist_52w = f"+{row['distance_from_52w_low_pct']:.1f}%" if pd.notna(row['distance_from_52w_low_pct']) else "N/A"

                # Price
                price = f"${row['current_price']:.2f}" if pd.notna(row['current_price']) else "N/A"

                # 52w range
                low_52w = f"${row['52w_low']:.2f}" if pd.notna(row['52w_low']) else "N/A"

                # Operating margin
                op_margin = f"{row['operating_margin_pct']:.1f}%" if pd.notna(row['operating_margin_pct']) else "N/A"

                # RODC
                rodc = f"{row['rodc_pct']:.1f}%" if pd.notna(row['rodc_pct']) else "N/A"

                # P/E
                pe = f"{row['pe_operating']:.1f}x" if pd.notna(row['pe_operating']) else "N/A"

                # P/B
                pb = f"{row['pb_ratio']:.1f}x" if pd.notna(row['pb_ratio']) else "N/A"

                # Market cap
                mcap = row['market_cap']
                if pd.notna(mcap):
                    if mcap >= 1e9:
                        mcap_str = f"${mcap/1e9:.1f}B"
                    else:
                        mcap_str = f"${mcap/1e6:.0f}M"
                else:
                    mcap_str = "N/A"

                # Financial statement fields
                revenue     = fmt_financial(row.get('revenue_ttm'))
                op_income   = fmt_financial(row.get('operating_income_ttm'))
                curr_assets = fmt_financial(row.get('total_current_assets'))
                cash        = fmt_financial(row.get('cash_and_short_term_investments'))
                curr_liab   = fmt_financial(row.get('total_current_liabilities'))
                ppe         = fmt_financial(row.get('net_ppe'))

                f.write(f"| {rank} | {ticker} | {company} | {dist_52w} | {price} | {low_52w} | {op_margin} | {rodc} | {pe} | {pb} | {mcap_str} | {revenue} | {op_income} | {curr_assets} | {cash} | {curr_liab} | {ppe} |\n")

            f.write("\n")
            f.write("## Column Definitions\n\n")
            f.write("- **52w Low %**: Percentage above (+) or below (-) the 52-week low\n")
            f.write("- **Op Margin**: Operating margin percentage\n")
            f.write("- **RODC**: Return on Deployed Capital (Li Lu's metric)\n")
            f.write("- **P/E**: Price-to-Earnings ratio (operating earnings)\n")
            f.write("- **P/B**: Price-to-Book ratio\n")
            f.write("- **Revenue**: Trailing 12-month revenue\n")
            f.write("- **Op Income**: Trailing 12-month operating income\n")
            f.write("- **Curr Assets**: Total current assets\n")
            f.write("- **Cash**: Cash and short-term investments\n")
            f.write("- **Curr Liab**: Total current liabilities\n")
            f.write("- **PP&E**: Net property, plant & equipment\n")

    def _generate_summary_report(self, df: pd.DataFrame, export_df: pd.DataFrame, output_file: str):
        """Generate human-readable summary report"""

        elapsed_time = (datetime.now() - self.stats['start_time']).total_seconds() / 60

        with open(output_file, 'w') as f:
            f.write("="*80 + "\n")
            f.write("COMPANY SCREENING REPORT\n")
            f.write("Li Lu's Methodology - Companies Near 52-Week Lows\n")
            f.write("="*80 + "\n\n")

            f.write(f"Run Date:           {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Universe:           {self.config.universe.upper()}\n")
            f.write(f"Companies Screened: {self.stats['total_companies']}\n")
            f.write(f"Passed Filters:     {self.stats['passed_filters']} ")
            f.write(f"({self.stats['passed_filters']/self.stats['total_companies']*100:.1f}%)\n")
            f.write(f"Top Candidates:     {len(df)}\n")
            f.write(f"Run Time:           {elapsed_time:.1f} minutes\n\n")

            f.write("CRITERIA APPLIED\n")
            f.write("-"*80 + "\n")
            criteria_lines = str(self.config).split(" | ")
            for line in criteria_lines:
                f.write(f"{line}\n")
            f.write("\n")

            f.write(f"TOP {min(50, len(export_df))} OPPORTUNITIES (Sorted by {self.config.sort_by})\n")
            f.write("="*95 + "\n\n")

            # Markdown table header
            f.write("| Rank | Ticker | Company | 52w% | Mgn% | RODC | P/E | P/B | Price | Mkt Cap | Revenue | Op Income | Curr Assets | Cash | Curr Liab | PP&E |\n")
            f.write("|------|--------|---------|------|------|------|-----|-----|-------|---------|---------|-----------|-------------|------|-----------|------|\n")

            def fmt_fin(val):
                if pd.isna(val) or val is None:
                    return "N/A"
                if abs(val) >= 1e9:
                    return f"${val/1e9:.1f}B"
                if abs(val) >= 1e6:
                    return f"${val/1e6:.0f}M"
                return f"${val:.0f}"

            for _, row in export_df.head(50).iterrows():
                rank = int(row['rank'])
                ticker = row['ticker']
                company = row['company_name'][:24]

                dist_52w  = f"{row['distance_from_52w_low_pct']:.1f}%"  if pd.notna(row['distance_from_52w_low_pct']) else "N/A"
                op_margin = f"{row['operating_margin_pct']:.1f}%"        if pd.notna(row['operating_margin_pct'])       else "N/A"
                rodc      = f"{row['rodc_pct']:.1f}%"                    if pd.notna(row['rodc_pct'])                   else "N/A"
                pe        = f"{row['pe_operating']:.1f}x"                if pd.notna(row['pe_operating'])               else "N/A"
                pb        = f"{row['pb_ratio']:.1f}x"                    if pd.notna(row['pb_ratio'])                   else "N/A"
                price     = f"${row['current_price']:.2f}"               if pd.notna(row['current_price'])              else "N/A"

                mcap = row['market_cap']
                mcap_str = (f"${mcap/1e9:.1f}B" if mcap >= 1e9 else f"${mcap/1e6:.0f}M") if pd.notna(mcap) else "N/A"

                revenue     = fmt_fin(row.get('revenue_ttm'))
                op_income   = fmt_fin(row.get('operating_income_ttm'))
                curr_assets = fmt_fin(row.get('total_current_assets'))
                cash        = fmt_fin(row.get('cash_and_short_term_investments'))
                curr_liab   = fmt_fin(row.get('total_current_liabilities'))
                ppe         = fmt_fin(row.get('net_ppe'))

                f.write(f"| {rank} | {ticker} | {company} | {dist_52w} | {op_margin} | {rodc} | {pe} | {pb} | {price} | {mcap_str} | {revenue} | {op_income} | {curr_assets} | {cash} | {curr_liab} | {ppe} |\n")

            f.write("\n")

            f.write("\n")

            # Cache statistics
            cache_stats = self.cache.get_cache_stats()
            f.write("CACHE STATISTICS\n")
            f.write("-"*80 + "\n")
            f.write(f"Cache Hit Rate:     {cache_stats['hit_rate']}%\n")
            f.write(f"Fresh Data:         {self.stats['fetched']} companies fetched\n")
            f.write(f"Cached Data:        {self.stats['cached']} companies used\n")
            f.write(f"Failed:             {self.stats['failed']} companies\n\n")

            f.write("FILES SAVED\n")
            f.write("-"*80 + "\n")
            f.write(f"- {output_file.replace('_summary', '')} (full data)\n")
            f.write(f"- {output_file} (this report)\n")
            f.write(f"- {self.cache.db_path} (cached data)\n")
            f.write("="*80 + "\n")

        print(f"\nSummary preview:")
        print(f"  Total screened: {self.stats['total_companies']}")
        print(f"  Passed filters: {self.stats['passed_filters']} ({self.stats['passed_filters']/self.stats['total_companies']*100:.1f}%)")
        print(f"  Top candidates: {len(df)}")
        print(f"  Run time: {elapsed_time:.1f} minutes")

    def run(self, output_file: str = "screening_results.md") -> pd.DataFrame:
        """
        Run complete screening workflow.

        Args:
            output_file: Output CSV filename

        Returns:
            DataFrame with screening results
        """
        print("\n" + "="*80)
        print("COMPANY SCREENING SYSTEM")
        print("Li Lu's Methodology - Value Opportunities Near 52-Week Lows")
        print("="*80)

        # Step 1: Get universe
        tickers = self.get_universe()

        # Step 2: Fetch data
        data = self.fetch_data_batch(tickers)

        if not data:
            print("\nError: No data available to screen")
            return pd.DataFrame()

        # Step 3: Apply filters
        filtered_df = self.apply_filters(data)

        if filtered_df.empty:
            print("\nNo companies passed filters")
            return pd.DataFrame()

        # Step 4: Sort and rank
        ranked_df = self.sort_and_rank(filtered_df)

        # Step 5: Export results
        self.export_results(ranked_df, output_file)

        print("\n" + "="*80)
        print("SCREENING COMPLETE")
        print("="*80)

        return ranked_df


def main():
    """Command-line interface for company screener"""

    parser = argparse.ArgumentParser(
        description="Screen companies using Li Lu's methodology - find value near 52-week lows",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use default preset (52_week_low_quality)
  python screen_companies.py

  # Use a specific preset
  python screen_companies.py --preset deep_value

  # Custom filters
  python screen_companies.py --min-rodc 25 --max-pe 12 --max-proximity 0.15

  # List available presets
  python screen_companies.py --list-presets

  # Force refresh all data
  python screen_companies.py --force-refresh

  # Offline mode (cached data only)
  python screen_companies.py --offline
        """
    )

    # Preset selection
    parser.add_argument('--preset', type=str,
                        help=f"Use a preset configuration: {', '.join(PRESET_DESCRIPTIONS.keys())}")
    parser.add_argument('--list-presets', action='store_true',
                        help="List all available presets and exit")

    # Universe selection
    parser.add_argument('--universe', default='ALL',
                        help="Letter spec for universe: 'ALL', single letter 'A', or range 'A-C' (default: ALL)")

    # Filter options
    parser.add_argument('--min-rodc', type=float,
                        help="Minimum RODC percentage (e.g., 30)")
    parser.add_argument('--max-pe', type=float,
                        help="Maximum P/E ratio on operating earnings (e.g., 15)")
    parser.add_argument('--max-pb', type=float,
                        help="Maximum P/B ratio (e.g., 2.0)")
    parser.add_argument('--max-proximity', type=float,
                        help="Maximum proximity to 52w low, 0-1 (e.g., 0.20 = within 20%%)")
    parser.add_argument('--min-margin', type=float,
                        help="Minimum operating margin percentage (e.g., 10)")

    # Output options
    parser.add_argument('--top', type=int, default=50,
                        help="Number of top candidates to output (default: 50)")
    parser.add_argument('--output', type=str, default="screening_results.md",
                        help="Output CSV filename (default: screening_results.md)")

    # Cache options
    parser.add_argument('--force-refresh', action='store_true',
                        help="Force refresh all data (ignore cache)")
    parser.add_argument('--offline', action='store_true',
                        help="Offline mode - use cached data only")
    parser.add_argument('--cache-ttl', type=int, default=7,
                        help="Cache TTL in days (default: 7)")

    # API key
    parser.add_argument('--api-key', type=str,
                        help="Massive.com API key (or set MASSIVE_API_KEY env var)")

    args = parser.parse_args()

    # List presets and exit
    if args.list_presets:
        print(list_presets())
        sys.exit(0)

    # Get API key
    api_key = args.api_key or os.environ.get('MASSIVE_API_KEY')
    if not api_key and not args.offline:
        print("Error: API key required. Set MASSIVE_API_KEY environment variable or use --api-key")
        print("Example: export MASSIVE_API_KEY=your_api_key")
        sys.exit(1)

    # Build configuration
    if args.preset:
        # Start with preset
        config = get_preset(args.preset)
        print(f"Using preset: {args.preset}")
        print(f"  {PRESET_DESCRIPTIONS[args.preset]}")
    else:
        # No preset — use ScreeningConfig defaults (no filters)
        config = ScreeningConfig()

    # Override with command-line arguments
    if args.min_rodc is not None:
        config.min_rodc = args.min_rodc
    if args.max_pe is not None:
        config.max_pe_operating = args.max_pe
    if args.max_pb is not None:
        config.max_pb_ratio = args.max_pb
    if args.max_proximity is not None:
        config.proximity_to_52w_low_max = args.max_proximity
    if args.min_margin is not None:
        config.min_operating_margin = args.min_margin

    config.universe = args.universe
    config.top_n = args.top
    config.force_refresh = args.force_refresh
    config.offline_mode = args.offline
    config.cache_ttl_days = args.cache_ttl
    config.api_key = api_key

    # Run screening
    screener = CompanyScreener(config)
    results = screener.run(output_file=args.output)

    if not results.empty:
        print(f"\n✓ Screening complete! Results saved to: {args.output}")
        print(f"  Top {len(results)} candidates identified")
        print(f"\nTop 5 opportunities:")
        print(results[['rank', 'ticker', 'company', 'distance_from_52w_low_pct', 'rodc_pct']].head().to_string(index=False))
    else:
        print("\nNo companies passed the screening criteria")
        sys.exit(1)


if __name__ == "__main__":
    main()
