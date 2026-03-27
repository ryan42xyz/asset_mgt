"""
Technical Indicator model
"""

from sqlalchemy import Column, String, Numeric, DateTime, Index, desc
from .base import Base


class TechnicalIndicator(Base):
    """Technical Indicator model"""
    
    __tablename__ = "technical_indicators"
    
    symbol = Column(String(10), nullable=False)
    indicator_type = Column(String(20), nullable=False)  # sma_200, vix
    value = Column(Numeric(18, 4), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_symbol_indicator_timestamp', 'symbol', 'indicator_type', 'timestamp'),
        Index('idx_symbol_indicator_timestamp_desc', 'symbol', 'indicator_type', desc('timestamp')),
    )
    
    def __repr__(self):
        return f"<TechnicalIndicator(symbol='{self.symbol}', type='{self.indicator_type}', value={self.value})>" 