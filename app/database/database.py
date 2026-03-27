"""
Database connection and session management
"""

import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker

# Build async-compatible URL from env (convert postgresql:// → postgresql+asyncpg://)
_raw_url = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:password@localhost:5432/assetmgmt"
)
SQLALCHEMY_DATABASE_URL = _raw_url.replace(
    "postgresql://", "postgresql+asyncpg://", 1
)

# Create async engine
engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    echo=False,
)

# Create async session maker
async_session_maker = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Create base class for models
Base = declarative_base()

# Dependency for FastAPI routes to access DB session
async def get_db():
    """FastAPI dependency that yields an async DB session."""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close() 