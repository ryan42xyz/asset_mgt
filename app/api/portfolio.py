"""
Portfolio Management API endpoints
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from sqlalchemy import or_

from ..database.database import get_db
from ..models.holding import Holding
from ..schemas.holding import HoldingCreate, HoldingUpdate, HoldingResponse
from ..services.market_data_service import market_data_service
from sqlalchemy import update as sql_update, select
from ..database.database import async_session_maker

router = APIRouter()


@router.get("/{user_id}/holdings", response_model=List[HoldingResponse])
async def get_holdings(user_id: int):
    """Get all holdings for a user"""
    try:
        holdings = await Holding.get_by_user(user_id)
        return holdings
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{user_id}/holdings", response_model=HoldingResponse)
async def create_holding(user_id: int, holding: HoldingCreate):
    """Create a new holding for a user"""
    try:
        # Add user_id to the holding data
        holding_dict = holding.model_dump()
        holding_dict["user_id"] = user_id
        
        # Create the holding
        new_holding = await Holding.create(**holding_dict)
        return new_holding
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{user_id}/holdings/{holding_id}")
async def delete_holding(user_id: int, holding_id: int):
    """Delete a holding"""
    try:
        await Holding.delete(holding_id, user_id)
        return {"message": "Holding deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 

@router.post("/{user_id}/refresh-prices", response_model=List[HoldingResponse])
async def refresh_prices(user_id: int):
    """Fetch latest market prices for user's holdings and update DB."""
    try:
        # Get current holdings
        holdings = await Holding.get_by_user(user_id)
        if not holdings:
            return []

        symbols = [h.symbol for h in holdings]
        price_map = await market_data_service.get_multiple_prices(symbols)

        # Update each holding price
        for sym, data in price_map.items():
            if data and "price" in data:
                price_val = data["price"]
                if price_val and price_val > 0:
                    await Holding.update_prices(sym, price_val)
                else:
                    # fallback to average cost price
                    for h in holdings:
                        if h.symbol == sym and h.shares > 0:
                            avg_cost = h.cost_basis / h.shares
                            await Holding.update_prices(sym, avg_cost)

        # Return updated holdings
        updated = await Holding.get_by_user(user_id)
        return updated
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 

@router.put("/{user_id}/holdings/{holding_id}", response_model=HoldingResponse)
async def update_holding(user_id: int, holding_id: int, payload: dict):
    """Update an existing holding. payload can include cost_basis, shares, broker_name, current_price."""
    try:
        async with async_session_maker() as session:
            # First get the current holding to preserve current_price if not provided
            current_holding = await session.execute(
                select(Holding).where(Holding.id == holding_id, Holding.user_id == user_id)
            )
            current_holding = current_holding.scalar_one_or_none()
            
            if not current_holding:
                raise HTTPException(status_code=404, detail="Holding not found")
            
            # Update the holding
            stmt = sql_update(Holding).where(Holding.id == holding_id, Holding.user_id == user_id).values(**payload)
            await session.execute(stmt)
            
            # Recalculate market_value if shares or current_price changed
            if 'shares' in payload or 'current_price' in payload:
                new_shares = payload.get('shares', current_holding.shares)
                new_current_price = payload.get('current_price', current_holding.current_price)
                new_market_value = new_shares * new_current_price
                
                # Update market_value
                await session.execute(
                    sql_update(Holding)
                    .where(Holding.id == holding_id)
                    .values(market_value=new_market_value)
                )
            
            await session.commit()
            
            # Get updated holding
            updated = await Holding.get_by_user(user_id)
            for h in updated:
                if h.id == holding_id:
                    return h
            raise HTTPException(status_code=404, detail="Holding not found after update")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{user_id}/update-price/{symbol}")
async def update_symbol_price(user_id: int, symbol: str, new_price: float):
    """Manually update price for all holdings of a specific symbol"""
    try:
        updated_count = await Holding.update_prices(symbol, new_price)
        if updated_count == 0:
            raise HTTPException(status_code=404, detail=f"No holdings found for symbol {symbol}")
        
        return {"message": f"Updated {updated_count} holdings for {symbol} with price ${new_price}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 

@router.put("/{user_id}/holdings/bulk-update")
async def bulk_update_holdings(
    user_id: int,
    updates: List[Dict[str, Any]],
    db: Session = Depends(get_db)
):
    """Bulk update holdings"""
    try:
        for update in updates:
            query = db.query(Holding).filter(Holding.user_id == user_id)
            
            # 可以通过 ID 或 symbol 更新
            if "id" in update:
                query = query.filter(Holding.id == update["id"])
            elif "symbol" in update:
                query = query.filter(Holding.symbol == update["symbol"])
            else:
                continue
                
            holding = query.first()
            if holding:
                for key, value in update.items():
                    if key not in ["id", "user_id"]:
                        setattr(holding, key, value)
        
        db.commit()
        return {"message": "Holdings updated successfully"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e)) 