"""
Price History model
"""

from sqlalchemy import Column, String, Numeric, BigInteger, DateTime, Index, desc
from .base import Base


class PriceHistory(Base):
    """Price History model"""
    
    __tablename__ = "price_history"
    
    symbol = Column(String(10), nullable=False)
    price = Column(Numeric(18, 2), nullable=False)
    volume = Column(BigInteger)
    timestamp = Column(DateTime, nullable=False)
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_symbol_timestamp', 'symbol', 'timestamp'),
        Index('idx_symbol_timestamp_desc', 'symbol', desc('timestamp')),
    )
    
    def __repr__(self):
        return f"<PriceHistory(symbol='{self.symbol}', price={self.price}, timestamp={self.timestamp})>" 