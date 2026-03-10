#!/usr/bin/env python3
"""
Screening Configuration

Defines filter criteria, presets, and configuration for company screening.

Presets include:
- 52_week_low_quality: Quality companies near 52-week lows
- deep_value: Extreme value opportunities
- li_lu_classic: Classic Li Lu methodology

Usage:
    from screening_config import ScreeningConfig, get_preset

    # Use a preset
    config = get_preset('52_week_low_quality')

    # Or create custom config
    config = ScreeningConfig(
        min_rodc=30.0,
        max_pe_operating=15.0,
        proximity_to_52w_low_max=0.20
    )
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any


@dataclass
class ScreeningConfig:
    """Configuration for company screening"""

    # Universe selection — letter spec: 'ALL', single letter 'A', or range 'A-C'
    universe: str = "ALL"

    # 52-week low filters
    proximity_to_52w_low_max: Optional[float] = None  # Max % above 52w low
    proximity_to_52w_low_min: Optional[float] = None  # Min proximity (optional)

    # Operating quality filters
    min_rodc: Optional[float] = None  # Minimum RODC percentage
    min_operating_margin: Optional[float] = None  # Minimum operating margin %

    # Valuation filters
    max_pe_operating: Optional[float] = None  # Maximum P/E on operating earnings
    max_pb_ratio: Optional[float] = None  # Maximum Price-to-Book ratio
    max_ev_to_operating_earnings: Optional[float] = None  # Max EV/Operating Earnings

    # Balance sheet filters
    positive_working_capital: bool = False  # Require positive working capital
    min_cash_pct_of_market_cap: Optional[float] = None  # Min cash % of market cap

    # Output settings
    top_n: int = 50  # Number of top candidates to output
    sort_by: str = "distance_from_52w_low_pct"  # Sort key
    sort_ascending: bool = True  # Sort order

    # Cache settings
    cache_ttl_days: int = 7  # Cache time-to-live in days
    force_refresh: bool = False  # Force refresh all data
    offline_mode: bool = False  # Use only cached data

    # API settings
    api_key: Optional[str] = None  # Massive.com API key
    rate_limit_delay: float = 0.15  # Delay between SEC requests (seconds)

    def __post_init__(self):
        """Validate configuration"""
        if self.proximity_to_52w_low_max is not None:
            if not 0 <= self.proximity_to_52w_low_max <= 1:
                raise ValueError("proximity_to_52w_low_max must be between 0 and 1")

        if self.sort_by not in ['proximity_to_52w_low', 'distance_from_52w_low_pct', 'rodc_pct', 'pe_operating', 'pb_ratio', 'operating_margin_pct', 'market_cap']:
            raise ValueError(f"Invalid sort_by: {self.sort_by}")

        # Validate universe spec via parse_letter_spec
        from company_universe import parse_letter_spec
        parse_letter_spec(self.universe)  # raises ValueError on bad input

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary"""
        return {
            'universe': self.universe,
            'proximity_to_52w_low_max': self.proximity_to_52w_low_max,
            'proximity_to_52w_low_min': self.proximity_to_52w_low_min,
            'min_rodc': self.min_rodc,
            'min_operating_margin': self.min_operating_margin,
            'max_pe_operating': self.max_pe_operating,
            'max_pb_ratio': self.max_pb_ratio,
            'max_ev_to_operating_earnings': self.max_ev_to_operating_earnings,
            'positive_working_capital': self.positive_working_capital,
            'min_cash_pct_of_market_cap': self.min_cash_pct_of_market_cap,
            'top_n': self.top_n,
            'sort_by': self.sort_by,
            'sort_ascending': self.sort_ascending,
            'cache_ttl_days': self.cache_ttl_days
        }

    def __str__(self) -> str:
        """Human-readable configuration summary"""
        filters = []

        if self.proximity_to_52w_low_max is not None:
            filters.append(f"52w Low: Within {self.proximity_to_52w_low_max*100:.0f}% of low")

        if self.min_rodc is not None:
            filters.append(f"RODC: >{self.min_rodc}%")

        if self.max_pe_operating is not None:
            filters.append(f"P/E: <{self.max_pe_operating}x")

        if self.max_pb_ratio is not None:
            filters.append(f"P/B: <{self.max_pb_ratio}x")

        if self.min_operating_margin is not None:
            filters.append(f"Operating Margin: >{self.min_operating_margin}%")

        return " | ".join(filters)


# Preset configurations
PRESETS = {
    "52_week_low_quality": ScreeningConfig(
        universe="ALL",
        proximity_to_52w_low_max=0.20,  # Within 20% of 52w low
        min_rodc=30.0,  # Strong businesses
        max_pe_operating=15.0,  # Reasonable valuation
        max_pb_ratio=2.0,
        min_operating_margin=10.0,
        top_n=50,  # Top 50 candidates
        sort_by="distance_from_52w_low_pct",  # Sort by % above 52w low
        sort_ascending=True  # Closest to 52w low first
    ),

    "deep_value": ScreeningConfig(
        universe="ALL",
        proximity_to_52w_low_max=0.15,  # Very close to 52w low
        max_pb_ratio=1.5,  # Trading near book value
        max_pe_operating=12.0,  # Very cheap valuation
        positive_working_capital=True,
        min_operating_margin=5.0,  # Lower bar for margin
        top_n=50,
        sort_by="distance_from_52w_low_pct",  # Sort by % above 52w low
        sort_ascending=True
    ),

    "li_lu_classic": ScreeningConfig(
        universe="ALL",
        min_rodc=50.0,  # Li Lu's "exceptional" businesses
        max_pe_operating=10.0,  # Very cheap on operating earnings
        max_pb_ratio=1.5,
        min_operating_margin=15.0,  # Strong margins
        proximity_to_52w_low_max=None,  # No 52w low requirement
        top_n=50,
        sort_by="rodc_pct",  # Sort by business quality
        sort_ascending=False  # Highest RODC first
    ),

    "quality_any_price": ScreeningConfig(
        universe="ALL",
        min_rodc=40.0,  # High-quality businesses
        min_operating_margin=20.0,  # Excellent margins
        max_pe_operating=None,  # No valuation filter
        max_pb_ratio=None,
        proximity_to_52w_low_max=None,
        top_n=50,
        sort_by="operating_margin_pct",  # Sort by standard metric (operating margin)
        sort_ascending=False  # Highest margin first
    ),

    "cash_fortress": ScreeningConfig(
        universe="ALL",
        min_cash_pct_of_market_cap=0.25,  # Cash > 25% of market cap
        positive_working_capital=True,
        max_pb_ratio=2.0,
        min_operating_margin=10.0,
        proximity_to_52w_low_max=0.30,
        top_n=30,
        sort_by="distance_from_52w_low_pct",
        sort_ascending=True
    )
}


# Preset descriptions for CLI help
PRESET_DESCRIPTIONS = {
    "52_week_low_quality": "Quality companies (RODC >30%) trading near 52-week lows (within 20%)",
    "deep_value": "Extreme value opportunities - very close to 52w low + P/B <1.5x",
    "li_lu_classic": "Classic Li Lu methodology - RODC >50%, P/E <10x, strong margins",
    "quality_any_price": "Find the highest quality businesses (RODC >40%, margins >20%) - sorted by operating margin",
    "cash_fortress": "Companies with strong cash positions (>25% of market cap) near 52w lows"
}


def get_preset(name: str) -> ScreeningConfig:
    """
    Get a preset configuration by name.

    Args:
        name: Preset name (e.g., '52_week_low_quality')

    Returns:
        ScreeningConfig instance

    Raises:
        KeyError if preset not found
    """
    if name not in PRESETS:
        available = ", ".join(PRESETS.keys())
        raise KeyError(f"Unknown preset '{name}'. Available presets: {available}")

    return PRESETS[name]


def list_presets() -> str:
    """
    Get formatted list of available presets.

    Returns:
        Formatted string describing all presets
    """
    lines = ["Available Screening Presets:", "="*70]

    for name, description in PRESET_DESCRIPTIONS.items():
        config = PRESETS[name]
        lines.append(f"\n{name}:")
        lines.append(f"  {description}")
        lines.append(f"  Filters: {config}")
        lines.append(f"  Output: Top {config.top_n}, sorted by {config.sort_by}")

    lines.append("\n" + "="*70)
    return "\n".join(lines)


def main():
    """Test screening configuration"""
    print("Testing Screening Configuration")
    print("="*70)

    # Test 1: List presets
    print("\n" + list_presets())

    # Test 2: Get specific preset
    print("\nTest 2: Loading preset '52_week_low_quality'...")
    config = get_preset('52_week_low_quality')
    print(f"✓ Loaded config:")
    print(f"  Universe: {config.universe}")
    print(f"  Filters: {config}")
    print(f"  Output: Top {config.top_n} by {config.sort_by}")

    # Test 3: Custom configuration
    print("\nTest 3: Creating custom configuration...")
    custom_config = ScreeningConfig(
        universe="ALL",
        min_rodc=25.0,
        max_pe_operating=12.0,
        proximity_to_52w_low_max=0.10,
        top_n=20
    )
    print(f"✓ Custom config created:")
    print(f"  {custom_config}")

    # Test 4: Configuration validation
    print("\nTest 4: Testing configuration validation...")
    try:
        invalid_config = ScreeningConfig(proximity_to_52w_low_max=1.5)
        print("✗ Validation failed - should have raised error")
    except ValueError as e:
        print(f"✓ Validation working: {e}")

    print("\n" + "="*70)
    print("All tests passed!")


if __name__ == "__main__":
    main()
