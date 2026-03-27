"""
User model
"""

from sqlalchemy import Column, Integer, String, DateTime, select, func
from sqlalchemy.orm import relationship
from ..database.database import Base, engine, async_session_maker

class User(Base):
    """User model"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    holdings = relationship("Holding", back_populates="user", cascade="all, delete-orphan")

    @classmethod
    async def create(cls, username: str) -> "User":
        """Create a new user"""
        async with async_session_maker() as session:
            user = cls(username=username)
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return user

    @classmethod
    async def get_by_id(cls, user_id: int) -> "User":
        """Get user by ID"""
        async with async_session_maker() as session:
            stmt = select(cls).where(cls.id == user_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none() 