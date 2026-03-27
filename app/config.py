"""
Application configuration settings
"""

import os
from typing import Optional
from pydantic import BaseModel
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    app_name: str = "Asset Management Platform"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # Database (SQLite by default; override with DATABASE_URL env var)
    database_url: str = "sqlite+aiosqlite:///./app.db"
    
    # Security
    secret_key: str = "your-secret-key-here"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # API Keys
    alpha_vantage_api_key: Optional[str] = None
    iex_cloud_api_key: Optional[str] = None
    
    # External APIs
    yahoo_finance_url: str = "https://query1.finance.yahoo.com/v8/finance/chart"
    alpha_vantage_url: str = "https://www.alphavantage.co/query"
    iex_cloud_url: str = "https://cloud.iexapis.com/stable/stock"
    exchange_rate_url: str = "https://api.exchangerate-api.com/v4/latest/USD"
    
    # Investment Strategy
    target_allocation: dict = {
        "cash_short_debt": {"symbols": ["DUSB", "SGOV"], "target": 0.25},
        "sp_equal_weight": {"symbols": ["RSP", "SPYV"], "target": 0.20},
        "sp_market_cap": {"symbols": ["SPY", "VOO"], "target": 0.15},
        "high_beta": {"symbols": ["NVDA", "QQQ"], "target": 0.15},
        "global_ex_us": {"symbols": ["DFAW"], "target": 0.10},
        "defensive": {"symbols": ["BRK.B", "GLD"], "target": 0.10}
    }
    
    # Monitored Symbols
    monitored_symbols: dict = {
        "indices": ["^GSPC", "^VIX"],  # S&P 500, VIX
        "stocks": ["SPY", "VOO", "RSP", "SPYV", "NVDA", "QQQ", "DFAW", "BRK.B", "GLD", "DUSB", "SGOV", "FUND"],  # All stock ETFs
        "insurance": ["BOC_HK_INSURANCE"],  # Insurance assets
        "cash": ["WEBANK_RMB"]  # Cash assets
    }
    
    # Trading Hours (EST)
    trading_start_hour: int = 9
    trading_start_minute: int = 30
    trading_end_hour: int = 16
    trading_end_minute: int = 0
    
    # Update Frequencies (seconds)
    price_update_frequency: int = 60  # 1 minute
    indicator_update_frequency: int = 300  # 5 minutes
    risk_gate_check_frequency: int = 60  # 1 minute
    weight_analysis_frequency: int = 600  # 10 minutes
    
    # Cache TTL (seconds)
    price_cache_ttl: int = 60
    indicator_cache_ttl: int = 300
    risk_gate_cache_ttl: int = 60
    
    # Risk Gate Settings
    risk_gate_sma_period: int = 200
    risk_gate_vix_threshold: float = 30.0
    risk_gate_consecutive_days: int = 10
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Ignore extra environment variables


# Create global settings instance
settings = Settings()

# Target allocation utility
def get_all_symbols():
    """Get all symbols from target allocation"""
    symbols = []
    for category in settings.target_allocation.values():
        symbols.extend(category["symbols"])
    return list(set(symbols))

def get_symbol_category(symbol: str) -> Optional[str]:
    """Get the category for a given symbol"""
    for category_name, category_info in settings.target_allocation.items():
        if symbol in category_info["symbols"]:
            return category_name
    return None 