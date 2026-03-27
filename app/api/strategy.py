"""
Strategy API endpoints
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from ..models.holding import Holding
from ..utils.yahoo_finance import YahooFinanceAPI
from ..config import settings, get_symbol_category
from ..services.market_data_service import market_data_service

router = APIRouter()

@router.get("/dashboard/{user_id}")
async def get_dashboard(user_id: int) -> Dict[str, Any]:
    """Get dashboard data for a user"""
    try:
        # Initialize Yahoo Finance API
        yf_api = YahooFinanceAPI()
        
        # Get user holdings
        holdings = await Holding.get_by_user(user_id)
        
        # Get USD/CNY exchange rate for currency conversion
        usd_cny_rate = await market_data_service.get_exchange_rate("USD", "CNY")
        if usd_cny_rate is None:
            usd_cny_rate = 7.18  # fallback rate
        
        # Calculate total portfolio value (in USD)
        total_value = 0.0
        holdings_data = []
        
        for holding in holdings:
            holding_dict = {
                "symbol": holding.symbol,
                "shares": holding.shares,
                "cost_basis": holding.cost_basis,
                "current_price": holding.current_price,
                "market_value": holding.market_value,
                "unrealized_pnl": holding.unrealized_pnl,
                "unrealized_pnl_percent": holding.unrealized_pnl_percent,
                "broker_name": holding.broker_name,
                "currency": holding.currency,
                "last_updated": holding.last_updated.isoformat() if holding.last_updated else None
            }
            holdings_data.append(holding_dict)
            
            if holding.market_value is not None:
                # Convert to USD if needed
                if holding.currency == "CNY":
                    total_value += holding.market_value / usd_cny_rate
                else:
                    total_value += holding.market_value

        # ----- Allocation calculation (stocks only) -----
        # Calculate total stock value for allocation percentage
        total_stock_value = 0.0
        stock_holdings = []
        
        for h in holdings:
            if h.market_value is not None and h.symbol in settings.monitored_symbols.get("stocks", []):
                usd_value = h.market_value / usd_cny_rate if h.currency == "CNY" else h.market_value
                total_stock_value += usd_value
                stock_holdings.append(h)
        
        allocation = {}
        for cat_name, cat_info in settings.target_allocation.items():
            cat_value = 0.0
            cat_holdings = []
            
            # Aggregate holdings by symbol first 
            symbol_aggregates = {}
            for h in stock_holdings:  # Only use stock holdings
                if h.symbol in cat_info["symbols"]:
                    # Convert to USD value
                    usd_value = h.market_value / usd_cny_rate if h.currency == "CNY" else h.market_value
                    
                    if h.symbol in symbol_aggregates:
                        symbol_aggregates[h.symbol] += usd_value
                    else:
                        symbol_aggregates[h.symbol] = usd_value
            
            # Add aggregated symbols to category
            for symbol, value in symbol_aggregates.items():
                cat_value += value
                if symbol not in cat_holdings:
                    cat_holdings.append(symbol)
                    
            current_weight = (cat_value / total_stock_value) if total_stock_value > 0 else 0
            
            # Create detailed holdings information
            holdings_detail = []
            for symbol, value in symbol_aggregates.items():
                # Calculate total shares for this symbol
                total_shares = sum(h.shares for h in stock_holdings if h.symbol == symbol)
                holdings_detail.append({
                    "symbol": symbol,
                    "shares": total_shares,
                    "market_value": value,
                    "weight": value / total_stock_value if total_stock_value > 0 else 0
                })
            
            allocation[cat_name] = {
                "target_weight": cat_info["target"],
                "current_weight": current_weight,
                "current_value": cat_value,
                "symbols": cat_holdings,
                "holdings": holdings_detail,
                "deviation": current_weight - cat_info["target"]
            }
        
        # Calculate asset class distribution for pie chart
        asset_distribution = {
            "stocks": 0.0,
            "insurance": 0.0,
            "cash": 0.0
        }
        
        for h in holdings:
            if h.market_value is not None:
                usd_value = h.market_value / usd_cny_rate if h.currency == "CNY" else h.market_value
                
                if h.symbol in settings.monitored_symbols.get("stocks", []):
                    asset_distribution["stocks"] += usd_value
                elif h.symbol in settings.monitored_symbols.get("insurance", []):
                    asset_distribution["insurance"] += usd_value
                elif h.symbol in settings.monitored_symbols.get("cash", []):
                    asset_distribution["cash"] += usd_value
        
        return {
            "total_value": total_value,
            "holdings": holdings_data,
            "allocation": {
                "total_value": total_value,
                "allocation": allocation
            },
            "asset_distribution": asset_distribution,
            "risk_gate": await compute_risk_gate(),
            "rebalance_suggestions": compute_rebalance_suggestions(allocation, total_stock_value)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 

# ------ helper functions ------

async def compute_risk_gate():
    """Compute risk gate status based on S&P 500 SMA and VIX."""
    sp500 = await market_data_service.get_sp500_data()
    vix = await market_data_service.get_vix_data()
    if not sp500 or not vix:
        return None
    is_triggered = sp500["below_sma"] and vix["price"] > 30
    return {
        "is_triggered": is_triggered,
        "sp500_price": sp500["price"],
        "sp500_sma_200": sp500["sma_200"],
        "vix_price": vix["price"],
        "timestamp": sp500["timestamp"]
    }


def compute_rebalance_suggestions(allocation_dict: dict, total_value: float):
    """Generate rebalance suggestions if deviation >5%."""
    suggestions = []
    for cat, info in allocation_dict.items():
        deviation = info["deviation"]
        if abs(deviation) > 0.05 and total_value > 0:
            action = "increase" if deviation < 0 else "decrease"
            amount = abs(deviation) * total_value
            suggestions.append({
                "category": cat,
                "action": action,
                "current_weight": info["current_weight"],
                "target_weight": info["target_weight"],
                "deviation": deviation,
                "suggested_amount": amount,
                "symbols": settings.target_allocation[cat]["symbols"]
            })
    return suggestions 