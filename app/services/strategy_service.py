"""
Investment Strategy Service for portfolio management and risk control
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc

from ..config import settings, get_symbol_category
from ..models.user import User
from ..models.holding import Holding
from ..models.risk_gate_status import RiskGateStatus
from ..models.strategy_action import StrategyAction
from ..models.technical_indicator import TechnicalIndicator
from ..services.market_data_service import market_data_service
from ..database.redis_client import redis_client, get_risk_gate_cache_key, get_portfolio_cache_key


class StrategyService:
    """Investment Strategy Service"""
    
    def __init__(self):
        pass
    
    async def get_portfolio_allocation(self, db: Session, user_id: int) -> Dict[str, Any]:
        """Get current portfolio allocation"""
        try:
            # Check cache first
            cache_key = get_portfolio_cache_key(user_id)
            cached_allocation = redis_client.get(cache_key)
            if cached_allocation:
                return cached_allocation
            
            # Get user holdings
            holdings = db.query(Holding).filter(Holding.user_id == user_id).all()
            
            # Get USD/CNY exchange rate for currency conversion
            usd_cny_rate = await market_data_service.get_exchange_rate("USD", "CNY")
            if usd_cny_rate is None:
                usd_cny_rate = 7.18  # fallback rate
            
            # Calculate total portfolio value (in USD)
            total_value = 0
            for holding in holdings:
                if holding.market_value:
                    if holding.currency == "CNY":
                        total_value += float(holding.market_value) / usd_cny_rate
                    else:
                        total_value += float(holding.market_value)
            
            # Calculate allocation by category
            allocation = {}
            for category_name, category_info in settings.target_allocation.items():
                category_value = 0
                category_holdings = []
                
                # Aggregate holdings by symbol first
                symbol_aggregates = {}
                for holding in holdings:
                    if holding.symbol in category_info["symbols"]:
                        symbol = holding.symbol
                        # Convert to USD if needed
                        market_value = float(holding.market_value or 0)
                        if holding.currency == "CNY":
                            market_value = market_value / usd_cny_rate
                        shares = float(holding.shares)
                        
                        if symbol in symbol_aggregates:
                            symbol_aggregates[symbol]["market_value"] += market_value
                            symbol_aggregates[symbol]["shares"] += shares
                        else:
                            symbol_aggregates[symbol] = {
                                "market_value": market_value,
                                "shares": shares
                            }
                
                # Add aggregated symbols to category
                for symbol, aggregate in symbol_aggregates.items():
                    category_value += aggregate["market_value"]
                    category_holdings.append({
                        "symbol": symbol,
                        "shares": aggregate["shares"],
                        "market_value": aggregate["market_value"],
                        "weight": aggregate["market_value"] / total_value if total_value > 0 else 0
                    })
                
                allocation[category_name] = {
                    "target_weight": category_info["target"],
                    "current_weight": category_value / total_value if total_value > 0 else 0,
                    "current_value": category_value,
                    "deviation": (category_value / total_value - category_info["target"]) if total_value > 0 else -category_info["target"],
                    "holdings": category_holdings
                }
            
            result = {
                "total_value": total_value,
                "allocation": allocation,
                "timestamp": datetime.now().isoformat()
            }
            
            # Cache the result
            redis_client.set(cache_key, result, ttl=600)  # 10 minutes
            
            return result
            
        except Exception as e:
            print(f"Error getting portfolio allocation: {e}")
            return {"total_value": 0, "allocation": {}, "timestamp": datetime.now().isoformat()}
    
    async def check_risk_gate_status(self, db: Session, user_id: int) -> Dict[str, Any]:
        """Check risk gate status"""
        try:
            # Check cache first
            cache_key = get_risk_gate_cache_key(user_id)
            cached_status = redis_client.get(cache_key)
            if cached_status:
                return cached_status
            
            # Get current S&P 500 and VIX data
            sp500_data = await market_data_service.get_sp500_data()
            vix_data = await market_data_service.get_vix_data()
            
            if not sp500_data or not vix_data:
                return {"error": "Unable to fetch market data"}
            
            # Get current risk gate status from database
            risk_gate = db.query(RiskGateStatus).filter(
                RiskGateStatus.user_id == user_id
            ).first()
            
            if not risk_gate:
                # Create new risk gate status
                risk_gate = RiskGateStatus(user_id=user_id)
                db.add(risk_gate)
            
            # Check conditions
            sp500_below_sma = sp500_data["below_sma"]
            vix_above_30 = vix_data["price"] > settings.risk_gate_vix_threshold
            
            # Update risk gate status
            risk_gate.sp500_below_sma = sp500_below_sma
            risk_gate.vix_above_30 = vix_above_30
            
            # Check if risk gate should be triggered
            if not risk_gate.is_triggered and risk_gate.is_ready_to_trigger:
                risk_gate.is_triggered = True
                risk_gate.trigger_date = datetime.now()
                risk_gate.consecutive_days_above_sma = 0
                
                # Log strategy action
                await self.log_strategy_action(
                    db, user_id, "risk_gate_trigger", 
                    details={"sp500_price": sp500_data["price"], "vix": vix_data["price"]}
                )
            
            # Check if risk gate should be resolved
            elif risk_gate.is_triggered:
                if not sp500_below_sma:
                    risk_gate.consecutive_days_above_sma += 1
                else:
                    risk_gate.consecutive_days_above_sma = 0
                
                # Get user investment stage
                user = db.query(User).filter(User.id == user_id).first()
                user_stage = user.investment_stage if user else "early"
                
                # Check resolution conditions based on user stage
                if user_stage == "late":
                    # Late stage: need both S&P above SMA and VIX < 25
                    if risk_gate.is_ready_to_resolve and vix_data["price"] < 25:
                        risk_gate.is_triggered = False
                        risk_gate.resolution_date = datetime.now()
                        
                        # Log strategy action
                        await self.log_strategy_action(
                            db, user_id, "risk_gate_resolve",
                            details={"sp500_price": sp500_data["price"], "vix": vix_data["price"]}
                        )
                else:
                    # Early/Middle stage: only need S&P above SMA for 10 days
                    if risk_gate.is_ready_to_resolve:
                        risk_gate.is_triggered = False
                        risk_gate.resolution_date = datetime.now()
                        
                        # Log strategy action
                        await self.log_strategy_action(
                            db, user_id, "risk_gate_resolve",
                            details={"sp500_price": sp500_data["price"], "vix": vix_data["price"]}
                        )
            
            db.commit()
            
            result = {
                "is_triggered": risk_gate.is_triggered,
                "sp500_below_sma": sp500_below_sma,
                "vix_above_30": vix_above_30,
                "consecutive_days_above_sma": risk_gate.consecutive_days_above_sma,
                "sp500_price": sp500_data["price"],
                "sp500_sma_200": sp500_data["sma_200"],
                "vix_price": vix_data["price"],
                "trigger_date": risk_gate.trigger_date.isoformat() if risk_gate.trigger_date else None,
                "resolution_date": risk_gate.resolution_date.isoformat() if risk_gate.resolution_date else None,
                "user_stage": user.investment_stage if user else "early",
                "timestamp": datetime.now().isoformat()
            }
            
            # Cache the result
            redis_client.set(cache_key, result, ttl=settings.risk_gate_cache_ttl)
            
            return result
            
        except Exception as e:
            print(f"Error checking risk gate status: {e}")
            return {"error": str(e)}
    
    async def generate_rebalance_suggestions(self, db: Session, user_id: int) -> List[Dict[str, Any]]:
        """Generate portfolio rebalance suggestions"""
        try:
            # Get current allocation
            allocation = await self.get_portfolio_allocation(db, user_id)
            
            suggestions = []
            
            for category_name, category_data in allocation["allocation"].items():
                deviation = category_data["deviation"]
                
                # Suggest rebalancing if deviation > 5%
                if abs(deviation) > 0.05:
                    action = "increase" if deviation < 0 else "decrease"
                    amount = abs(deviation) * allocation["total_value"]
                    
                    suggestion = {
                        "category": category_name,
                        "action": action,
                        "current_weight": category_data["current_weight"],
                        "target_weight": category_data["target_weight"],
                        "deviation": deviation,
                        "suggested_amount": amount,
                        "symbols": [symbol for symbol in settings.target_allocation[category_name]["symbols"]]
                    }
                    
                    suggestions.append(suggestion)
            
            return suggestions
            
        except Exception as e:
            print(f"Error generating rebalance suggestions: {e}")
            return []
    
    async def get_strategy_actions(self, db: Session, user_id: int) -> List[Dict[str, Any]]:
        """Get strategy execution actions based on current state"""
        try:
            # Get risk gate status
            risk_gate_status = await self.check_risk_gate_status(db, user_id)
            
            # Get user
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return []
            
            # Get rebalance suggestions
            rebalance_suggestions = await self.generate_rebalance_suggestions(db, user_id)
            
            actions = []
            
            # Add rebalance actions
            for suggestion in rebalance_suggestions:
                actions.append({
                    "type": "rebalance",
                    "priority": "high" if abs(suggestion["deviation"]) > 0.1 else "medium",
                    "category": suggestion["category"],
                    "action": suggestion["action"],
                    "description": f"{suggestion['action'].capitalize()} {suggestion['category']} position by {suggestion['suggested_amount']:.2f}",
                    "details": suggestion
                })
            
            # Add risk gate actions
            if risk_gate_status.get("is_triggered"):
                if user.investment_stage == "early":
                    actions.append({
                        "type": "risk_gate",
                        "priority": "info",
                        "description": "Risk gate triggered - Continue regular investment plan (Early stage)",
                        "details": risk_gate_status
                    })
                elif user.investment_stage == "middle":
                    actions.append({
                        "type": "risk_gate",
                        "priority": "high",
                        "description": "Risk gate triggered - Consider reducing satellite positions",
                        "details": risk_gate_status
                    })
                else:  # late stage
                    actions.append({
                        "type": "risk_gate",
                        "priority": "high",
                        "description": "Risk gate triggered - Consider reducing overall positions",
                        "details": risk_gate_status
                    })
            
            return actions
            
        except Exception as e:
            print(f"Error getting strategy actions: {e}")
            return []
    
    async def log_strategy_action(self, db: Session, user_id: int, action_type: str, 
                                 symbol: str = None, details: Dict = None):
        """Log strategy action"""
        try:
            strategy_action = StrategyAction(
                user_id=user_id,
                action_type=action_type,
                symbol=symbol,
                action_details=details or {},
                executed_at=datetime.now(),
                status="completed"
            )
            
            db.add(strategy_action)
            db.commit()
            
        except Exception as e:
            print(f"Error logging strategy action: {e}")
            db.rollback()
    
    async def get_performance_metrics(self, db: Session, user_id: int) -> Dict[str, Any]:
        """Calculate portfolio performance metrics"""
        try:
            # Get user holdings
            holdings = db.query(Holding).filter(Holding.user_id == user_id).all()
            
            total_cost = sum(holding.total_cost for holding in holdings)
            total_value = sum(float(holding.market_value or 0) for holding in holdings)
            
            # Calculate basic metrics
            total_return = total_value - total_cost
            total_return_pct = (total_return / total_cost * 100) if total_cost > 0 else 0
            
            # Get historical performance (simplified)
            # In a real implementation, you'd calculate more sophisticated metrics
            
            performance = {
                "total_cost": total_cost,
                "total_value": total_value,
                "total_return": total_return,
                "total_return_percent": total_return_pct,
                "positions": len(holdings),
                "timestamp": datetime.now().isoformat()
            }
            
            return performance
            
        except Exception as e:
            print(f"Error calculating performance metrics: {e}")
            return {}
    
    async def update_holdings_market_value(self, db: Session, user_id: int):
        """Update market values for all holdings"""
        try:
            # Get user holdings
            holdings = db.query(Holding).filter(Holding.user_id == user_id).all()
            
            # Get symbols
            symbols = [holding.symbol for holding in holdings]
            
            # Fetch current prices
            price_data = await market_data_service.get_multiple_prices(symbols)
            
            # Update market values
            for holding in holdings:
                if holding.symbol in price_data and price_data[holding.symbol]:
                    current_price = price_data[holding.symbol]["price"]
                    holding.current_price = current_price
                    holding.market_value = float(holding.shares) * current_price
                    holding.last_updated = datetime.now()
            
            db.commit()
            
            # Clear portfolio cache
            cache_key = get_portfolio_cache_key(user_id)
            redis_client.delete(cache_key)
            
        except Exception as e:
            print(f"Error updating holdings market value: {e}")
            db.rollback()


# Global strategy service instance
strategy_service = StrategyService() 