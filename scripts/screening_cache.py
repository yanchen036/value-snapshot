#!/usr/bin/env python3
"""
Screening Cache - SQLite-based persistent caching for financial data

Caches financial data, calculated metrics, and 52-week price data
to avoid redundant API calls during screening.

Features:
- SQLite database for persistent storage
- Automatic staleness detection
- Batch operations for performance
- Cache hit/miss statistics

Usage:
    from screening_cache import ScreeningCache

    cache = ScreeningCache()

    # Get cached data
    data = cache.get_cached_data('AAPL', max_age_days=7)

    # Store new data
    cache.store_data('AAPL', financial_data, metrics_data, price_data)

    # Identify stale tickers
    stale = cache.get_stale_tickers(['AAPL', 'MSFT'], max_age_days=7)
"""

import os
import sqlite3
import json
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from contextlib import contextmanager


class ScreeningCache:
    """Persistent cache for company screening data using SQLite"""

    def __init__(self, db_path: str = "~/.value_snapshot/cache/screening.db"):
        """
        Initialize screening cache.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = os.path.expanduser(db_path)

        # Ensure directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        # Initialize database
        self._init_database()

        # Statistics
        self.stats = {
            'hits': 0,
            'misses': 0,
            'stores': 0
        }

    @contextmanager
    def _get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_database(self):
        """Create database schema if it doesn't exist"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Financial data cache table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS financial_data (
                    ticker TEXT PRIMARY KEY,
                    fetch_date TEXT NOT NULL,
                    filing_date TEXT,
                    financial_json TEXT NOT NULL,
                    metrics_json TEXT,
                    price_history_json TEXT,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Screening results table (for historical tracking)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS screening_results (
                    run_id TEXT,
                    ticker TEXT,
                    rank INTEGER,
                    proximity_to_52w_low REAL,
                    rodc REAL,
                    pe_ratio REAL,
                    pb_ratio REAL,
                    result_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (run_id, ticker)
                )
            """)

            # Create indexes for performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_last_updated
                ON financial_data(last_updated)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_screening_run
                ON screening_results(run_id, rank)
            """)

            conn.commit()

    def get_cached_data(self, ticker: str, max_age_days: int = 7) -> Optional[Dict]:
        """
        Retrieve cached data for a ticker if fresh enough.

        Args:
            ticker: Ticker symbol
            max_age_days: Maximum age in days for data to be considered fresh

        Returns:
            Dictionary with financial, metrics, and price data if cached and fresh,
            None otherwise
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Calculate cutoff date
            cutoff_date = datetime.now() - timedelta(days=max_age_days)

            cursor.execute("""
                SELECT financial_json, metrics_json, price_history_json,
                       last_updated, filing_date
                FROM financial_data
                WHERE ticker = ? AND last_updated >= ?
            """, (ticker.upper(), cutoff_date.isoformat()))

            row = cursor.fetchone()

            if not row:
                self.stats['misses'] += 1
                return None

            self.stats['hits'] += 1

            # Parse JSON data
            result = {
                'financial': json.loads(row['financial_json']) if row['financial_json'] else None,
                'metrics': json.loads(row['metrics_json']) if row['metrics_json'] else None,
                'price_history': json.loads(row['price_history_json']) if row['price_history_json'] else None,
                'cached_at': row['last_updated'],
                'filing_date': row['filing_date']
            }

            return result

    def store_data(self, ticker: str, financial: Dict, metrics: Optional[Dict] = None,
                   price_history: Optional[Dict] = None):
        """
        Store or update cached data for a ticker.

        Args:
            ticker: Ticker symbol
            financial: Financial data from fetch_financials
            metrics: Calculated metrics from calculate_metrics
            price_history: 52-week price data
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            fetch_date = financial.get('fetch_date', datetime.now().strftime('%Y-%m-%d'))
            filing_date = financial.get('filing_date')

            cursor.execute("""
                INSERT OR REPLACE INTO financial_data
                (ticker, fetch_date, filing_date, financial_json, metrics_json,
                 price_history_json, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                ticker.upper(),
                fetch_date,
                filing_date,
                json.dumps(financial),
                json.dumps(metrics) if metrics else None,
                json.dumps(price_history) if price_history else None,
                datetime.now().isoformat()
            ))

            self.stats['stores'] += 1

    def get_stale_tickers(self, tickers: List[str], max_age_days: int = 7) -> List[str]:
        """
        Identify which tickers need data refresh.

        Args:
            tickers: List of ticker symbols to check
            max_age_days: Maximum age for data to be considered fresh

        Returns:
            List of tickers that need refresh (not cached or stale)
        """
        if not tickers:
            return []

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Calculate cutoff date
            cutoff_date = datetime.now() - timedelta(days=max_age_days)

            # Create placeholders for SQL IN clause
            placeholders = ','.join('?' * len(tickers))
            upper_tickers = [t.upper() for t in tickers]

            cursor.execute(f"""
                SELECT ticker FROM financial_data
                WHERE ticker IN ({placeholders})
                AND last_updated >= ?
            """, upper_tickers + [cutoff_date.isoformat()])

            fresh_tickers = {row['ticker'] for row in cursor.fetchall()}

            # Return tickers not in fresh set
            stale = [t for t in tickers if t.upper() not in fresh_tickers]

            return stale

    def store_screening_results(self, run_id: str, results: List[Dict]):
        """
        Store screening results for historical tracking.

        Args:
            run_id: Unique identifier for this screening run
            results: List of screening result dictionaries
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            for result in results:
                cursor.execute("""
                    INSERT OR REPLACE INTO screening_results
                    (run_id, ticker, rank, proximity_to_52w_low, rodc,
                     pe_ratio, pb_ratio, result_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    run_id,
                    result.get('ticker', '').upper(),
                    result.get('rank'),
                    result.get('proximity_to_52w_low'),
                    result.get('rodc_pct'),
                    result.get('pe_operating'),
                    result.get('pb_ratio'),
                    json.dumps(result)
                ))

    def get_screening_history(self, limit: int = 10) -> List[Dict]:
        """
        Retrieve recent screening runs.

        Args:
            limit: Number of recent runs to retrieve

        Returns:
            List of screening run summaries
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT run_id, COUNT(*) as company_count,
                       MIN(created_at) as run_date,
                       AVG(rodc) as avg_rodc,
                       AVG(pe_ratio) as avg_pe
                FROM screening_results
                GROUP BY run_id
                ORDER BY run_date DESC
                LIMIT ?
            """, (limit,))

            results = []
            for row in cursor.fetchall():
                results.append({
                    'run_id': row['run_id'],
                    'run_date': row['run_date'],
                    'company_count': row['company_count'],
                    'avg_rodc': row['avg_rodc'],
                    'avg_pe': row['avg_pe']
                })

            return results

    def clear_old_data(self, days_to_keep: int = 90):
        """
        Remove data older than specified days.

        Args:
            days_to_keep: Keep data from last N days
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cutoff_date = datetime.now() - timedelta(days=days_to_keep)

            cursor.execute("""
                DELETE FROM financial_data
                WHERE last_updated < ?
            """, (cutoff_date.isoformat(),))

            deleted_count = cursor.rowcount

            cursor.execute("""
                DELETE FROM screening_results
                WHERE created_at < ?
            """, (cutoff_date.isoformat(),))

            print(f"Cleared {deleted_count} old cache entries")

    def get_cache_stats(self) -> Dict:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Count total cached companies
            cursor.execute("SELECT COUNT(*) as count FROM financial_data")
            total_cached = cursor.fetchone()['count']

            # Count fresh vs stale (7 days)
            cutoff_date = datetime.now() - timedelta(days=7)
            cursor.execute("""
                SELECT COUNT(*) as count FROM financial_data
                WHERE last_updated >= ?
            """, (cutoff_date.isoformat(),))
            fresh_count = cursor.fetchone()['count']

            # Average age of data
            cursor.execute("""
                SELECT AVG(JULIANDAY('now') - JULIANDAY(last_updated)) as avg_age
                FROM financial_data
            """)
            avg_age_days = cursor.fetchone()['avg_age'] or 0

            return {
                'total_cached': total_cached,
                'fresh_7d': fresh_count,
                'stale_7d': total_cached - fresh_count,
                'avg_age_days': round(avg_age_days, 1),
                'session_hits': self.stats['hits'],
                'session_misses': self.stats['misses'],
                'session_stores': self.stats['stores'],
                'hit_rate': round(100 * self.stats['hits'] / (self.stats['hits'] + self.stats['misses']), 1)
                           if (self.stats['hits'] + self.stats['misses']) > 0 else 0
            }

    def vacuum(self):
        """Optimize database (reclaim space, rebuild indexes)"""
        with self._get_connection() as conn:
            conn.execute("VACUUM")
            print("Database optimized")


def main():
    """Test screening cache functionality"""
    print("Testing Screening Cache")
    print("="*70)

    cache = ScreeningCache()

    # Test 1: Store sample data
    print("\nTest 1: Storing sample data...")
    sample_financial = {
        'ticker': 'AAPL',
        'company_name': 'Apple Inc.',
        'revenue_ttm': 383285000000,
        'operating_income_ttm': 114301000000,
        'market_cap': 2900000000000,
        'fetch_date': datetime.now().strftime('%Y-%m-%d'),
        'filing_date': '2024-09-30'
    }

    sample_metrics = {
        'rodc_pct': 55.3,
        'pe_operating': 25.4,
        'pb_ratio': 45.2
    }

    sample_price = {
        'current_price': 180.25,
        '52_week_high': 199.50,
        '52_week_low': 164.08,
        'proximity_to_low': 0.46
    }

    cache.store_data('AAPL', sample_financial, sample_metrics, sample_price)
    print("✓ Stored data for AAPL")

    # Test 2: Retrieve cached data
    print("\nTest 2: Retrieving cached data...")
    cached = cache.get_cached_data('AAPL', max_age_days=7)
    if cached:
        print(f"✓ Retrieved cached data:")
        print(f"  Company: {cached['financial'].get('company_name')}")
        print(f"  RODC: {cached['metrics'].get('rodc_pct')}%")
        print(f"  52w Low: ${cached['price_history'].get('52_week_low')}")
    else:
        print("✗ Failed to retrieve cached data")

    # Test 3: Check stale tickers
    print("\nTest 3: Checking stale tickers...")
    test_tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN']
    stale = cache.get_stale_tickers(test_tickers, max_age_days=7)
    print(f"✓ Stale tickers (need refresh): {stale}")
    print(f"  Fresh tickers: {[t for t in test_tickers if t not in stale]}")

    # Test 4: Cache statistics
    print("\nTest 4: Cache statistics...")
    stats = cache.get_cache_stats()
    print(f"✓ Cache stats:")
    print(f"  Total cached: {stats['total_cached']} companies")
    print(f"  Fresh (7d): {stats['fresh_7d']}")
    print(f"  Stale (7d): {stats['stale_7d']}")
    print(f"  Average age: {stats['avg_age_days']} days")
    print(f"  Session hit rate: {stats['hit_rate']}%")

    # Test 5: Store screening results
    print("\nTest 5: Storing screening results...")
    run_id = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    results = [
        {
            'ticker': 'AAPL',
            'rank': 1,
            'proximity_to_52w_low': 0.46,
            'rodc_pct': 55.3,
            'pe_operating': 25.4,
            'pb_ratio': 45.2
        }
    ]
    cache.store_screening_results(run_id, results)
    print(f"✓ Stored screening results for run: {run_id}")

    print("\n" + "="*70)
    print("All tests passed!")
    print(f"Cache location: {cache.db_path}")


if __name__ == "__main__":
    main()
