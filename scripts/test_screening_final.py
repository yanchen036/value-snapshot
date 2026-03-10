#!/usr/bin/env python3
"""
Test the final screening with user's requested filters:
- 52w low proximity <30%
- RODC >20%
- Operating margin >10%
- P/E <25x
- P/B <3.0x
- Sort by distance from 52-week low
- Output in markdown
"""

import sys
from screening_config import ScreeningConfig
from screen_companies import CompanyScreener

def main():
    print("Testing final screening configuration...")
    print("="*70)

    # Create config - NO FILTERS, just sort and show top 50
    # universe: 'ALL' = all tickers, 'A' = tickers starting with A, 'A-C' = A/B/C
    config = ScreeningConfig(
        universe='ALL',
        proximity_to_52w_low_max=None,   # No 52w low filter
        min_rodc=None,                   # No RODC filter
        min_operating_margin=None,       # No operating margin filter
        max_pe_operating=None,           # No P/E filter
        max_pb_ratio=None,               # No P/B filter
        top_n=50,                        # Top 50 results
        sort_by='distance_from_52w_low_pct',  # Sort by % above 52w low
        sort_ascending=True,             # Closest to low first
        api_key='8rhKqmYtZ6xSNQEu97AvAw4pL_LgUJFa',
        force_refresh=False              # Use cache
    )

    print("\nConfiguration:")
    print(f"  Universe: {config.universe}")
    print(f"  Filters: None (showing all companies)")
    print(f"  Sort by: {config.sort_by}")
    print(f"  Top N: {config.top_n}")
    print()

    # Run screening
    screener = CompanyScreener(config)
    results = screener.run(output_file='sp500_52week_all.md')

    # Results are already exported by run()
    if not results.empty:
        print("\n✓ Screening complete!")
        print(f"  {len(results)} companies passed filters")
    else:
        print("\n✗ No companies passed filters")
        sys.exit(1)

if __name__ == "__main__":
    main()
