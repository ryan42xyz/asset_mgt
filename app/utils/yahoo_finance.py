import aiohttp
import pandas as pd
import yfinance as yf
from typing import Dict, List, Optional

class YahooFinanceAPI:
    """Yahoo Finance API wrapper for fetching market data"""
    
    def __init__(self):
        self.session = None
    
    async def _ensure_session(self):
        """Ensure aiohttp session exists"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
    
    async def get_quotes(self, symbols: List[str]) -> Dict[str, float]:
        """Get latest quotes for multiple symbols"""
        try:
            # Use yfinance for batch quotes
            tickers = yf.Tickers(" ".join(symbols))
            prices = {}
            
            for symbol in symbols:
                try:
                    if symbol in tickers.tickers:
                        ticker = tickers.tickers[symbol]
                        # Get last price
                        hist = ticker.history(period="1d")
                        if not hist.empty:
                            prices[symbol] = float(hist['Close'].iloc[-1])
                except Exception as e:
                    print(f"Error getting price for {symbol}: {e}")
                    continue
            
            return prices
            
        except Exception as e:
            print(f"Error fetching quotes: {e}")
            return {}
    
    async def get_historical(self, symbol: str, period: str = "1y") -> Optional[pd.DataFrame]:
        """Get historical data for a symbol"""
        try:
            ticker = yf.Ticker(symbol)
            return ticker.history(period=period)
        except Exception as e:
            print(f"Error fetching historical data for {symbol}: {e}")
            return None
    
    async def get_sma(self, symbol: str, window: int = 200) -> Optional[float]:
        """Calculate Simple Moving Average"""
        try:
            # Get enough data for SMA calculation
            df = await self.get_historical(symbol, period="1y")
            if df is not None and not df.empty:
                sma = df['Close'].rolling(window=window).mean().iloc[-1]
                return float(sma)
        except Exception as e:
            print(f"Error calculating SMA for {symbol}: {e}")
        return None
    
    async def close(self):
        """Close the session"""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None 