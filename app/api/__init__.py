"""API modules for the application"""

from .auth import router as auth_router
from .portfolio import router as portfolio_router
from .strategy import router as strategy_router

auth = auth_router
portfolio = portfolio_router
strategy = strategy_router

__all__ = ["auth", "portfolio", "strategy"] 