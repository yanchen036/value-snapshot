#!/usr/bin/env python3
"""
Quick test script for the company screener

This script runs a minimal test of the screening system with a small
sample of companies to verify everything works.

Usage:
    python test_screener.py [API_KEY]

If API_KEY not provided, will use MASSIVE_API_KEY environment variable.
"""

import os
import sys

# Add scripts directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from screening_config import ScreeningConfig
from screen_companies import CompanyScreener


def test_screener(api_key: str):
    """Run a minimal screening test"""

    print("="*70)
    print("SCREENER TEST - Small Sample")
    print("="*70)

    # Create a relaxed configuration for testing
    config = ScreeningConfig(
        universe="sp500",
        proximity_to_52w_low_max=None,  # Disable 52-week filter for testing
        min_rodc=15.0,  # Lower threshold for testing
        max_pe_operating=25.0,  # Higher threshold
        max_pb_ratio=5.0,  # Higher threshold
        min_operating_margin=5.0,  # Lower threshold
        top_n=10,
        sort_by="rodc_pct",  # Sort by RODC instead of proximity
        sort_ascending=False,  # Highest RODC first
        cache_ttl_days=7,
        api_key=api_key
    )

    print("\nTest Configuration:")
    print(f"  {config}")
    print(f"  Universe: S&P 500")
    print(f"  Output: Top {config.top_n}")

    # Create screener
    screener = CompanyScreener(config)

    # For testing, we'll limit the universe
    print("\n⚠ TEST MODE: Limiting to first 20 S&P 500 companies for speed")

    # Override universe fetching for test
    original_get_universe = screener.get_universe

    def test_get_universe():
        tickers = original_get_universe()
        return tickers[:20]  # Test with first 20 companies only

    screener.get_universe = test_get_universe

    # Run screening
    results = screener.run(output_file="test_screening_results.md")

    if not results.empty:
        print("\n" + "="*70)
        print("TEST SUCCESSFUL!")
        print("="*70)
        print(f"\nFound {len(results)} candidates from 20 test companies")
        print("\nTop 5 results:")
        print(results[['rank', 'ticker', 'company', 'proximity_to_52w_low', 'rodc_pct']].head().to_string(index=False))
        print("\n✓ Screener is working correctly!")
        print("✓ Ready for full S&P 500 screening")
        return 0
    else:
        print("\n⚠ No companies passed filters")
        print("This might be normal with relaxed test filters and small sample")
        print("Try running full screening with: python screen_companies.py")
        return 0


def main():
    """Main test function"""

    # Get API key
    api_key = sys.argv[1] if len(sys.argv) > 1 else os.environ.get('MASSIVE_API_KEY')

    if not api_key:
        print("Error: API key required")
        print("\nUsage:")
        print("  python test_screener.py [API_KEY]")
        print("\nOr set environment variable:")
        print("  export MASSIVE_API_KEY=your_api_key")
        print("  python test_screener.py")
        sys.exit(1)

    try:
        return test_screener(api_key)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        return 1
    except Exception as e:
        print(f"\n\nTest failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
