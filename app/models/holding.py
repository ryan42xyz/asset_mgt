"""
Holding model
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, select, delete, update, func
from sqlalchemy.orm import relationship
from typing import List, Optional, Dict
from ..database.database import Base, engine, async_session_maker

class Holding(Base):
    """Holding model for storing portfolio holdings"""
    __tablename__ = "holdings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    symbol = Column(String, nullable=False)
    shares = Column(Float, nullable=False)
    cost_basis = Column(Float, nullable=False)
    current_price = Column(Float)
    market_value = Column(Float)
    broker_name = Column(String)
    currency = Column(String, default="USD")  # 添加币种字段，默认为 USD
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="holdings")

    @property
    def avg_cost_price(self) -> Optional[float]:
        """Calculate average cost price per share"""
        if self.shares > 0:
            return self.cost_basis / self.shares
        return None

    @property
    def unrealized_pnl(self) -> Optional[float]:
        """Calculate unrealized P&L"""
        if self.market_value is not None and self.cost_basis is not None:
            return self.market_value - self.cost_basis
        return None

    @property
    def unrealized_pnl_percent(self) -> Optional[float]:
        """Calculate unrealized P&L percentage"""
        if self.unrealized_pnl is not None and self.cost_basis > 0:
            return (self.unrealized_pnl / self.cost_basis) * 100
        return None

    @classmethod
    async def get_by_user(cls, user_id: int) -> List["Holding"]:
        """Get all holdings for a user"""
        async with async_session_maker() as session:
            stmt = select(cls).where(cls.user_id == user_id)
            result = await session.execute(stmt)
            return result.scalars().all()

    @classmethod
    async def create(cls, **kwargs) -> "Holding":
        """Create a new holding"""
        async with async_session_maker() as session:
            holding = cls(**kwargs)
            # If current_price not provided, calculate from cost_basis
            if holding.current_price is None:
                if holding.shares > 0:
                    holding.current_price = holding.cost_basis / holding.shares
                else:
                    holding.current_price = 0
            holding.market_value = holding.shares * holding.current_price
            session.add(holding)
            await session.commit()
            await session.refresh(holding)
            return holding

    @classmethod
    async def delete(cls, holding_id: int, user_id: int) -> None:
        """Delete a holding"""
        async with async_session_maker() as session:
            stmt = delete(cls).where(cls.id == holding_id, cls.user_id == user_id)
            await session.execute(stmt)
            await session.commit()

    @classmethod
    async def get_unique_symbols(cls) -> List[str]:
        """Get list of unique symbols"""
        async with async_session_maker() as session:
            stmt = select(cls.symbol).distinct()
            result = await session.execute(stmt)
            return [row[0] for row in result.all()]

    @classmethod
    async def update_prices(cls, symbol: str, price: float) -> int:
        """Update current price and market value for a symbol"""
        async with async_session_maker() as session:
            stmt = (
                update(cls)
                .where(cls.symbol == symbol)
                .values(
                    current_price=price,
                    market_value=cls.shares * price,
                    last_updated=func.current_timestamp()
                )
            )
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount 