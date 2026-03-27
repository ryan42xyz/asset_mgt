"""
Market Data API endpoints
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from ..database.database import get_db
from ..services.market_data_service import market_data_service
from ..config import settings, get_all_symbols

router = APIRouter()


@router.get("/prices")
async def get_all_prices():
    """Get prices for all monitored symbols"""
    try:
        # Get all monitored symbols
        all_symbols = []
        for category in settings.monitored_symbols.values():
            all_symbols.extend(category)
        
        # Remove duplicates
        all_symbols = list(set(all_symbols))
        
        # Fetch prices
        price_data = await market_data_service.get_multiple_prices(all_symbols)
        
        return {
            "status": "success",
            "data": price_data,
            "symbols_count": len(all_symbols)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching prices: {str(e)}")


@router.get("/prices/{symbol}")
async def get_stock_price(symbol: str) -> Dict[str, Any]:
    """Get current stock price"""
    price_data = await market_data_service.get_stock_price(symbol)
    if not price_data:
        raise HTTPException(status_code=404, detail=f"Price data not found for {symbol}")
    return {"data": price_data}


@router.get("/indicators/sp500")
async def get_sp500_indicators():
    """Get S&P 500 indicators including 200-day SMA"""
    try:
        sp500_data = await market_data_service.get_sp500_data()
        
        if not sp500_data:
            raise HTTPException(status_code=500, detail="Unable to fetch S&P 500 data")
        
        return {
            "status": "success",
            "data": sp500_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching S&P 500 indicators: {str(e)}")


@router.get("/indicators/spy")
async def get_spy_indicators():
    """Get SPY indicators including 200-day SMA and 50-day EMA"""
    try:
        spy_data = await market_data_service.get_spy_data()
        
        if not spy_data:
            raise HTTPException(status_code=500, detail="Unable to fetch SPY data")
        
        return {
            "status": "success",
            "data": spy_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching SPY indicators: {str(e)}")


@router.get("/indicators/vix")
async def get_vix_data():
    """Get VIX (Fear Index) data"""
    try:
        vix_data = await market_data_service.get_vix_data()
        
        if not vix_data:
            raise HTTPException(status_code=500, detail="Unable to fetch VIX data")
        
        return {
            "status": "success",
            "data": vix_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching VIX data: {str(e)}")


@router.get("/indicators/{symbol}/sma/{period}")
async def get_sma(symbol: str, period: int):
    """Get Simple Moving Average for a symbol"""
    try:
        if period not in [20, 50, 100, 200]:
            raise HTTPException(status_code=400, detail="Period must be 20, 50, 100, or 200")
        
        sma_value = await market_data_service.calculate_sma(symbol, period)
        
        if sma_value is None:
            raise HTTPException(status_code=404, detail=f"SMA data not available for {symbol}")
        
        return {
            "status": "success",
            "data": {
                "symbol": symbol,
                "period": period,
                "sma": sma_value,
                "indicator_type": f"sma_{period}"
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating SMA: {str(e)}")


@router.get("/exchange-rate/{from_currency}/{to_currency}")
async def get_exchange_rate(from_currency: str, to_currency: str) -> Dict[str, Any]:
    """Get current exchange rate"""
    rate = await market_data_service.get_exchange_rate(from_currency, to_currency)
    if not rate:
        raise HTTPException(status_code=404, detail=f"Exchange rate not found for {from_currency}/{to_currency}")
    return {"rate": rate}


@router.get("/categories")
async def get_symbol_categories():
    """Get all symbol categories and their target allocations"""
    try:
        return {
            "status": "success",
            "data": {
                "target_allocation": settings.target_allocation,
                "monitored_symbols": settings.monitored_symbols
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching categories: {str(e)}")


@router.post("/update")
async def update_market_data(db: Session = Depends(get_db)):
    """Manually trigger market data update"""
    try:
        await market_data_service.update_all_monitored_symbols(db)
        
        return {
            "status": "success",
            "message": "Market data updated successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating market data: {str(e)}")


@router.get("/historical/{symbol}")
async def get_historical_data(symbol: str, period: str = "1y"):
    """Get historical price data for a symbol"""
    try:
        if period not in ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"]:
            raise HTTPException(status_code=400, detail="Invalid period")
        
        hist_data = await market_data_service.get_historical_prices(symbol, period)
        
        if hist_data.empty:
            raise HTTPException(status_code=404, detail=f"Historical data not found for {symbol}")
        
        # Convert DataFrame to list of dictionaries
        data = []
        for index, row in hist_data.iterrows():
            data.append({
                "date": index.isoformat(),
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"]),
                "volume": int(row["Volume"])
            })
        
        return {
            "status": "success",
            "data": {
                "symbol": symbol,
                "period": period,
                "data": data
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching historical data: {str(e)}") 