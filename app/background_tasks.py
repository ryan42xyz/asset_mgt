import asyncio
from datetime import datetime, time
import pytz
from sqlalchemy.orm import Session

from .config import settings
from .database.database import SessionLocal
from .models.user import User
from .services.market_data_service import market_data_service
from .services.strategy_service import strategy_service


def is_trading_hours(now_est):
    """Return True if current EST time is within U.S. regular trading hours."""
    start = time(settings.trading_start_hour, settings.trading_start_minute)
    end = time(settings.trading_end_hour, settings.trading_end_minute)
    return start <= now_est.time() <= end


async def market_update_loop():
    """Background loop that periodically pulls market data and updates holdings."""
    est = pytz.timezone("US/Eastern")
    price_freq = settings.price_update_frequency
    while True:
        now_est = datetime.now(est)
        try:
            with SessionLocal() as db:
                if is_trading_hours(now_est):
                    # Update monitored symbols (indices & ETFs)
                    await market_data_service.update_all_monitored_symbols(db)
                    # Update each user's holdings (only symbols they hold)
                    user_ids = [uid for (uid,) in db.query(User.id).all()]
                    for uid in user_ids:
                        await strategy_service.update_holdings_market_value(db, uid)
                else:
                    # Outside trading hours we can sleep longer or still update less frequently
                    pass
        except Exception as e:
            print(f"[BackgroundTask] Error in market update loop: {e}")
        await asyncio.sleep(price_freq) 