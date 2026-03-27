import asyncio
import datetime
import pytz
from fastapi import BackgroundTasks
from ..models.holding import Holding
from ..utils.yahoo_finance import YahooFinanceAPI

class MarketDataService:
    def __init__(self):
        self.yf_api = YahooFinanceAPI()
        self.is_running = False
        self.update_interval = 60  # seconds
        
    def is_market_hours(self) -> bool:
        """Check if US market is open"""
        now = datetime.datetime.now(pytz.timezone('America/New_York'))
        # Market hours 9:30 AM - 4:00 PM ET, Monday to Friday
        if now.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return False
        market_open = now.replace(hour=9, minute=30, second=0)
        market_close = now.replace(hour=16, minute=0, second=0)
        return market_open <= now <= market_close
    
    async def update_market_data(self):
        """Update market data for all holdings"""
        try:
            # Get unique symbols
            symbols = await Holding.get_unique_symbols()
            if not symbols:
                return
            
            # Get quotes
            quotes = await self.yf_api.get_quotes(symbols)
            
            # Update prices
            for symbol, price in quotes.items():
                await Holding.update_prices(symbol, price)
                
        except Exception as e:
            print(f"Error updating market data: {e}")
    
    async def run_updates(self):
        """Run market data updates"""
        while self.is_running:
            if self.is_market_hours():
                await self.update_market_data()
            await asyncio.sleep(self.update_interval)
    
    def start(self, background_tasks: BackgroundTasks):
        """Start market data service"""
        if not self.is_running:
            self.is_running = True
            background_tasks.add_task(self.run_updates)
    
    def stop(self):
        """Stop market data service"""
        self.is_running = False 