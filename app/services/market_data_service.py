"""
Market Data Service for fetching stock prices and technical indicators
"""

import asyncio
import httpx
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session

from ..config import settings
from ..models.price_history import PriceHistory
from ..models.technical_indicator import TechnicalIndicator
from ..database.redis_client import redis_client, get_price_cache_key, get_indicator_cache_key


class MarketDataService:
    """Market Data Service for fetching and processing market data"""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def get_stock_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get current stock price from Yahoo Finance"""
        try:
            # Check cache first
            cache_key = get_price_cache_key(symbol)
            cached_price = redis_client.get(cache_key)
            if cached_price:
                return cached_price
            
            # Fetch from Yahoo Finance
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            price_data = {
                "symbol": symbol,
                "price": info.get("regularMarketPrice", 0),
                "change": info.get("regularMarketChange", 0),
                "changePercent": info.get("regularMarketChangePercent", 0),
                "volume": info.get("regularMarketVolume", 0),
                "timestamp": datetime.now().isoformat()
            }
            
            # Cache the result
            redis_client.set(cache_key, price_data, ttl=settings.price_cache_ttl)
            
            return price_data
            
        except Exception as e:
            print(f"Error fetching price for {symbol}: {e}")
            return None
    
    async def get_multiple_prices(self, symbols: List[str]) -> Dict[str, Any]:
        """Get prices for multiple symbols concurrently"""
        tasks = [self.get_stock_price(symbol) for symbol in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        price_data = {}
        for symbol, result in zip(symbols, results):
            if isinstance(result, dict):
                price_data[symbol] = result
            else:
                print(f"Error getting price for {symbol}: {result}")
                price_data[symbol] = None
        
        return price_data
    
    async def get_historical_prices(self, symbol: str, period: str = "1y") -> pd.DataFrame:
        """Get historical price data"""
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period)
            return hist
        except Exception as e:
            print(f"Error fetching historical data for {symbol}: {e}")
            return pd.DataFrame()
    
    async def calculate_sma(self, symbol: str, period: int = 200) -> Optional[float]:
        """Calculate Simple Moving Average"""
        try:
            # Check cache first
            cache_key = get_indicator_cache_key(symbol, f"sma_{period}")
            cached_sma = redis_client.get(cache_key)
            if cached_sma:
                return cached_sma
            
            # Get historical data
            hist = await self.get_historical_prices(symbol, period="1y")
            if hist.empty:
                return None
            
            # Calculate SMA
            sma = hist['Close'].tail(period).mean()
            
            # Cache the result
            redis_client.set(cache_key, float(sma), ttl=settings.indicator_cache_ttl)
            
            return float(sma)
            
        except Exception as e:
            print(f"Error calculating SMA for {symbol}: {e}")
            return None
    
    async def get_vix_data(self) -> Optional[Dict[str, Any]]:
        """Get VIX data"""
        try:
            # Check cache first
            cache_key = get_price_cache_key("^VIX")
            cached_vix = redis_client.get(cache_key)
            if cached_vix:
                return cached_vix
            
            # Fetch VIX data
            vix_ticker = yf.Ticker("^VIX")
            vix_info = vix_ticker.info
            
            vix_data = {
                "symbol": "^VIX",
                "price": vix_info.get("regularMarketPrice", 0),
                "change": vix_info.get("regularMarketChange", 0),
                "changePercent": vix_info.get("regularMarketChangePercent", 0),
                "timestamp": datetime.now().isoformat()
            }
            
            # Cache the result
            redis_client.set(cache_key, vix_data, ttl=settings.price_cache_ttl)
            
            return vix_data
            
        except Exception as e:
            print(f"Error fetching VIX data: {e}")
            return None
    
    async def get_sp500_data(self) -> Optional[Dict[str, Any]]:
        """Get S&P 500 data"""
        try:
            # Get current price
            sp500_price = await self.get_stock_price("^GSPC")
            if not sp500_price:
                return None
            
            # Get 200-day SMA
            sma_200 = await self.calculate_sma("^GSPC", 200)
            
            return {
                "symbol": "^GSPC",
                "price": sp500_price["price"],
                "change": sp500_price["change"],
                "changePercent": sp500_price["changePercent"],
                "sma_200": sma_200,
                "below_sma": sp500_price["price"] < sma_200 if sma_200 else False,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"Error fetching S&P 500 data: {e}")
            return None
    
    async def get_spy_data(self) -> Optional[Dict[str, Any]]:
        """Get SPY data with technical indicators"""
        try:
            # Get current price
            spy_price = await self.get_stock_price("SPY")
            if not spy_price:
                return None
            
            # Get 200-day SMA
            sma_200 = await self.calculate_sma("SPY", 200)
            
            # Get 50-day EMA (simplified calculation)
            ema_50 = await self.calculate_sma("SPY", 50)  # Using SMA as approximation for now
            
            return {
                "symbol": "SPY",
                "price": spy_price["price"],
                "change": spy_price["change"],
                "changePercent": spy_price["changePercent"],
                "sma_200": sma_200,
                "ema_50": ema_50,
                "below_sma": spy_price["price"] < sma_200 if sma_200 else False,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"Error fetching SPY data: {e}")
            return None
    
    async def save_price_history(self, db: Session, symbol: str, price: float, volume: int = None):
        """Save price data to database"""
        try:
            price_record = PriceHistory(
                symbol=symbol,
                price=price,
                volume=volume,
                timestamp=datetime.now()
            )
            db.add(price_record)
            db.commit()
            
        except Exception as e:
            print(f"Error saving price history for {symbol}: {e}")
            db.rollback()
    
    async def save_technical_indicator(self, db: Session, symbol: str, indicator_type: str, value: float):
        """Save technical indicator to database"""
        try:
            indicator_record = TechnicalIndicator(
                symbol=symbol,
                indicator_type=indicator_type,
                value=value,
                timestamp=datetime.now()
            )
            db.add(indicator_record)
            db.commit()
            
        except Exception as e:
            print(f"Error saving technical indicator for {symbol}: {e}")
            db.rollback()
    
    async def get_exchange_rate(self, from_currency: str = "USD", to_currency: str = "CNY") -> Optional[float]:
        """Get current exchange rate from Yahoo Finance"""
        try:
            # Check cache first
            cache_key = get_price_cache_key(f"{from_currency}{to_currency}=X")
            cached_rate = redis_client.get(cache_key)
            if cached_rate:
                return cached_rate["price"]
            
            # Fetch from Yahoo Finance
            ticker = yf.Ticker(f"{from_currency}{to_currency}=X")
            info = ticker.info
            
            rate = info.get("regularMarketPrice", 0)
            
            # Cache the result
            redis_client.set(cache_key, {
                "symbol": f"{from_currency}{to_currency}=X",
                "price": rate,
                "timestamp": datetime.now().isoformat()
            }, ttl=settings.price_cache_ttl)
            
            return rate
            
        except Exception as e:
            print(f"Error fetching exchange rate {from_currency}/{to_currency}: {e}")
            return None
    
    async def update_all_monitored_symbols(self, db: Session):
        """Update all monitored symbols"""
        try:
            # Get all monitored symbols
            all_symbols = []
            for category in settings.monitored_symbols.values():
                all_symbols.extend(category)
            
            # Remove duplicates
            all_symbols = list(set(all_symbols))
            
            # Fetch prices for all symbols
            price_data = await self.get_multiple_prices(all_symbols)
            
            # Save to database
            for symbol, data in price_data.items():
                if data:
                    await self.save_price_history(
                        db, symbol, data["price"], data.get("volume")
                    )
            
            # Update technical indicators for S&P 500
            sp500_data = await self.get_sp500_data()
            if sp500_data and sp500_data["sma_200"]:
                await self.save_technical_indicator(
                    db, "^GSPC", "sma_200", sp500_data["sma_200"]
                )
            
            # Update VIX
            vix_data = await self.get_vix_data()
            if vix_data:
                await self.save_technical_indicator(
                    db, "^VIX", "vix", vix_data["price"]
                )
            
            print(f"Updated {len(all_symbols)} symbols")
            
        except Exception as e:
            print(f"Error updating monitored symbols: {e}")
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()


# Global market data service instance
market_data_service = MarketDataService() 