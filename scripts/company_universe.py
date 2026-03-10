#!/usr/bin/env python3
"""
Company Universe Management

Downloads and caches the full list of US common stock tickers from Massive.com.
Supports alphabetical filtering: 'A', 'A-C', 'ALL', etc.

Usage:
    # Build/refresh the ticker cache (run once before screening):
    python company_universe.py --build --api-key YOUR_KEY

    # As a module:
    from company_universe import get_universe, build_ticker_cache
    tickers = get_universe('A-C', api_key='...')
"""

import os
import json
import time
import requests
from collections import Counter
from datetime import datetime, timedelta
from typing import List, Optional

CACHE_DIR = os.path.expanduser('~/.value_snapshot/cache')
TICKER_CACHE_FILENAME = 'universe_tickers.json'
DEFAULT_CACHE_TTL_DAYS = 30


def _fetch_all_tickers_from_massive(api_key: str,
                                    cache_dir: str = CACHE_DIR) -> List[dict]:
    """
    Paginate through Massive.com to fetch all active US common stocks.
    Saves progress after each page so partial results survive rate-limit failures.
    Returns list of {ticker, name} dicts, sorted by ticker.
    """
    base_url = 'https://api.massive.com'
    headers = {'Authorization': f'Bearer {api_key}'}

    # Load partial progress if available
    partial_file = os.path.join(os.path.expanduser(cache_dir), '_universe_partial.json')
    all_tickers: List[dict] = []
    cursor = None

    if os.path.exists(partial_file):
        with open(partial_file) as f:
            partial = json.load(f)
        all_tickers = partial.get('tickers', [])
        cursor = partial.get('next_cursor')
        if all_tickers:
            print(f'  Resuming from partial save ({len(all_tickers):,} tickers, cursor={bool(cursor)})')

    page = 1

    while True:
        params = {
            'market': 'stocks',
            'locale': 'us',
            'active': 'true',
            'limit': 1000,
            'sort': 'ticker',
            'order': 'asc',
        }
        if cursor:
            params['cursor'] = cursor

        print(f'  Page {page}: fetched {len(all_tickers):,} tickers so far...', end='\r')

        # Fetch with retry on 429 — use increasing waits (30s, 60s, 90s, 120s)
        for attempt in range(4):
            response = requests.get(
                f'{base_url}/v3/reference/tickers',
                headers=headers,
                params=params,
                timeout=15,
            )
            if response.status_code == 429:
                wait = 30 * (attempt + 1)
                print(f'\n  Rate limited (attempt {attempt+1}/4), waiting {wait}s...')
                time.sleep(wait)
                continue
            response.raise_for_status()
            break
        else:
            # Save partial progress before giving up
            with open(partial_file, 'w') as f:
                json.dump({'tickers': all_tickers, 'next_cursor': cursor}, f)
            raise RuntimeError(
                f'Exceeded retry limit after {len(all_tickers):,} tickers. '
                f'Partial progress saved — re-run to resume.'
            )

        data = response.json()

        if data.get('status') not in ('OK', 'DELAYED'):
            raise RuntimeError(
                f"Massive.com error: {data.get('status')} — {data.get('message', '')}"
            )

        results = data.get('results', [])
        for r in results:
            ticker = r.get('ticker', '').strip()
            stock_type = r.get('type', '')
            # Keep CS (common stock) and ADRC (American Depositary Receipt — foreign companies
            # listed on US exchanges, e.g. BABA, PDD, BIDU). Skip ETFs, warrants, preferred, etc.
            if ticker and ticker[0].isalpha() and stock_type in ('CS', 'ADRC'):
                all_tickers.append({'ticker': ticker, 'name': r.get('name', '')})

        next_url = data.get('next_url', '')
        if not next_url or len(results) < 1000:
            cursor = None
            break

        # Extract cursor param from next_url
        cursor = next_url.split('cursor=')[1].split('&')[0] if 'cursor=' in next_url else None
        if not cursor:
            break

        # Save partial progress after each page
        with open(partial_file, 'w') as f:
            json.dump({'tickers': all_tickers, 'next_cursor': cursor}, f)

        page += 1
        time.sleep(2)  # conservative pacing between pages

    # Clean up partial file on success
    if os.path.exists(partial_file):
        os.remove(partial_file)

    print()  # clear the \r progress line
    return sorted(all_tickers, key=lambda t: t['ticker'])


def _print_letter_distribution(tickers: List[dict]) -> None:
    """Print a compact table showing how many tickers start with each letter."""
    counts = Counter(t['ticker'][0].upper() for t in tickers if t.get('ticker'))
    total = sum(counts.values())

    print(f'Ticker universe: {total:,} companies')

    letters = sorted(counts.keys())
    col_width = 6
    for i in range(0, len(letters), col_width):
        row = letters[i:i + col_width]
        print('  ' + '   '.join(f'{l}: {counts[l]:4d}' for l in row))
    print()


def build_ticker_cache(api_key: str,
                       cache_dir: str = CACHE_DIR,
                       force_refresh: bool = False,
                       cache_ttl_days: int = DEFAULT_CACHE_TTL_DAYS) -> List[dict]:
    """
    Download all US common stock tickers from Massive.com and cache them.
    Prints a letter distribution table after a fresh build.

    Returns list of {ticker, name} dicts.
    """
    cache_dir = os.path.expanduser(cache_dir)
    os.makedirs(cache_dir, exist_ok=True)
    cache_file = os.path.join(cache_dir, TICKER_CACHE_FILENAME)

    if not force_refresh and os.path.exists(cache_file):
        age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(cache_file))
        if age < timedelta(days=cache_ttl_days):
            with open(cache_file) as f:
                data = json.load(f)
            tickers = data['tickers']
            print(f'Using cached ticker universe ({len(tickers):,} companies, {age.days}d old)')
            return tickers

    print('Building ticker universe from Massive.com...')
    tickers = _fetch_all_tickers_from_massive(api_key, cache_dir=cache_dir)

    cache_data = {
        'built_at': datetime.now().isoformat(),
        'count': len(tickers),
        'tickers': tickers,
    }
    with open(cache_file, 'w') as f:
        json.dump(cache_data, f)

    print(f'✓ Cached {len(tickers):,} tickers → {cache_file}')
    _print_letter_distribution(tickers)

    return tickers


def parse_letter_spec(spec: str) -> Optional[List[str]]:
    """
    Parse a letter spec into a list of uppercase letters, or None for ALL.

    Examples:
        'ALL'  → None       (no filter — return everything)
        'A'    → ['A']
        'A-C'  → ['A', 'B', 'C']
        'K-M'  → ['K', 'L', 'M']

    Raises ValueError on invalid input.
    """
    spec = spec.strip().upper()

    if spec == 'ALL':
        return None

    if '-' in spec:
        parts = spec.split('-', 1)
        if len(parts[0]) != 1 or len(parts[1]) != 1:
            raise ValueError(f"Invalid range '{spec}': expected single letters, e.g. 'A-C'")
        start, end = parts[0], parts[1]
        if not start.isalpha() or not end.isalpha():
            raise ValueError(f"Invalid range '{spec}': must use letters only")
        if start > end:
            raise ValueError(f"Invalid range '{spec}': start letter must be ≤ end letter")
        return [chr(c) for c in range(ord(start), ord(end) + 1)]

    if len(spec) == 1 and spec.isalpha():
        return [spec]

    raise ValueError(f"Invalid universe spec '{spec}'. Use 'ALL', 'A', or 'A-C'")


def get_universe(spec: str,
                 api_key: str,
                 cache_dir: str = CACHE_DIR,
                 cache_ttl_days: int = DEFAULT_CACHE_TTL_DAYS) -> List[str]:
    """
    Return ticker symbols matching the letter spec.
    Auto-builds the ticker cache if missing or stale.

    Args:
        spec: 'ALL', single letter 'A', or range 'A-C'
        api_key: Massive.com API key
        cache_dir: Directory for the ticker cache file
        cache_ttl_days: Days before cache is considered stale

    Returns:
        Sorted list of ticker symbols
    """
    all_tickers = build_ticker_cache(api_key, cache_dir, cache_ttl_days=cache_ttl_days)
    letters = parse_letter_spec(spec)

    if letters is None:
        return [t['ticker'] for t in all_tickers]

    letter_set = set(letters)
    return [t['ticker'] for t in all_tickers if t['ticker'][0].upper() in letter_set]


# ---------------------------------------------------------------------------
# CLI — run directly to build/refresh the cache
# ---------------------------------------------------------------------------
def main():
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description='Build and inspect the US common stock ticker universe cache'
    )
    parser.add_argument('--build', action='store_true',
                        help='Download all tickers and build the cache')
    parser.add_argument('--force', action='store_true',
                        help='Force refresh even if cache is fresh')
    parser.add_argument('--api-key', default=None,
                        help='Massive.com API key (required only when cache is missing or --force)')
    parser.add_argument('--letters', default='ALL',
                        help="Preview tickers for a letter spec, e.g. 'A' or 'A-C'")
    args = parser.parse_args()

    # API key is required for build/force or when cache doesn't exist
    cache_file = os.path.join(os.path.expanduser(CACHE_DIR), TICKER_CACHE_FILENAME)
    needs_api = args.build or args.force or not os.path.exists(cache_file)
    if needs_api and not args.api_key:
        print('Error: --api-key is required to build or refresh the ticker cache')
        sys.exit(1)

    if args.build or args.force:
        build_ticker_cache(args.api_key, force_refresh=args.force)
    else:
        all_tickers = build_ticker_cache(args.api_key or '', cache_ttl_days=DEFAULT_CACHE_TTL_DAYS)

        if args.letters == 'ALL':
            _print_letter_distribution(all_tickers)
        else:
            letters = parse_letter_spec(args.letters)
            letter_set = set(letters)
            result = [t['ticker'] for t in all_tickers if t['ticker'][0].upper() in letter_set]
            print(f"Tickers matching '{args.letters}' ({len(result)} companies):")
            # Print all tickers, 10 per row
            for i in range(0, len(result), 10):
                print('  ' + '  '.join(result[i:i + 10]))

    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
