"""
Strategy Action model
"""

from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from .base import Base


class StrategyAction(Base):
    """Strategy Action model"""
    
    __tablename__ = "strategy_actions"
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action_type = Column(String(50), nullable=False)  # rebalance, risk_gate_trigger, etc.
    symbol = Column(String(10))
    action_details = Column(JSON)
    executed_at = Column(DateTime)
    status = Column(String(20), default="pending")  # pending, completed, failed
    
    # Relationships
    user = relationship("User", back_populates="strategy_actions")
    
    def __repr__(self):
        return f"<StrategyAction(user_id={self.user_id}, action_type='{self.action_type}', status='{self.status}')>" 