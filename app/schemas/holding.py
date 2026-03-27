from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class HoldingBase(BaseModel):
    symbol: str
    shares: float
    cost_basis: float
    broker_name: Optional[str] = None
    currency: Optional[str] = "USD"

class HoldingCreate(HoldingBase):
    user_id: int

class HoldingUpdate(BaseModel):
    symbol: Optional[str] = None
    shares: Optional[float] = None
    cost_basis: Optional[float] = None
    current_price: Optional[float] = None
    market_value: Optional[float] = None
    broker_name: Optional[str] = None
    currency: Optional[str] = None

class HoldingResponse(HoldingBase):
    id: int
    user_id: int
    current_price: Optional[float] = None
    market_value: Optional[float] = None
    unrealized_pnl: Optional[float] = None
    unrealized_pnl_percent: Optional[float] = None
    last_updated: Optional[datetime] = None

    class Config:
        from_attributes = True 