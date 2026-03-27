"""
Risk Gate Status model
"""

from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from .base import Base


class RiskGateStatus(Base):
    """Risk Gate Status model"""
    
    __tablename__ = "risk_gate_status"
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_triggered = Column(Boolean, default=False)
    sp500_below_sma = Column(Boolean, default=False)
    vix_above_30 = Column(Boolean, default=False)
    consecutive_days_above_sma = Column(Integer, default=0)
    trigger_date = Column(DateTime)
    resolution_date = Column(DateTime)
    
    # Relationships
    user = relationship("User", back_populates="risk_gate_status")
    
    def __repr__(self):
        return f"<RiskGateStatus(user_id={self.user_id}, is_triggered={self.is_triggered})>"
    
    @property
    def is_ready_to_trigger(self):
        """Check if risk gate is ready to trigger"""
        return self.sp500_below_sma and self.vix_above_30
    
    @property
    def is_ready_to_resolve(self):
        """Check if risk gate is ready to resolve"""
        return self.consecutive_days_above_sma >= 10 