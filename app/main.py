"""
Main FastAPI application for Asset Management Platform
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from .api.auth import router as auth_router
from .api.portfolio import router as portfolio_router
from .api.strategy import router as strategy_router
from .api.market import router as market_router
from .api.fire_calc import router as fire_calc_router
from .services.market_data import MarketDataService
from .database.database import Base, engine
import asyncio

app = FastAPI(title="Asset Management Platform")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include routers
app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(portfolio_router, prefix="/api/v1/portfolio", tags=["portfolio"])
app.include_router(strategy_router, prefix="/api/v1/strategy", tags=["strategy"])
app.include_router(market_router, prefix="/api/v1/market", tags=["market"])
app.include_router(fire_calc_router)

# Initialize market data service
market_service = MarketDataService()

# holder for background task created at startup
market_data_task = None

@app.on_event("startup")
async def startup_event():
    """Start background services"""
    print("Starting Asset Management Platform...")

    # Create database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables created successfully")

    # Seed demo user (id=1) if not present
    from .models.user import User
    from .database.database import async_session_maker
    from sqlalchemy import select
    async with async_session_maker() as session:
        result = await session.execute(select(User).where(User.username == "demo"))
        if result.scalar_one_or_none() is None:
            session.add(User(username="demo"))
            await session.commit()
            print("Demo user created (username=demo)")

    # Start market data service in its own asyncio.Task so that startup doesn't block
    global market_data_task
    if not market_service.is_running:
        market_service.is_running = True  # ensure flag set before loop starts
    market_data_task = asyncio.create_task(market_service.run_updates())

@app.on_event("shutdown")
async def shutdown_event():
    """Stop background services"""
    market_service.stop()
    # Cancel background task if running
    global market_data_task
    if market_data_task:
        market_data_task.cancel()
        try:
            await market_data_task
        except asyncio.CancelledError:
            pass

@app.get("/")
async def root():
    """Serve the main page"""
    from fastapi.responses import FileResponse
    return FileResponse("app/static/index.html")

@app.get("/spy-dashboard")
async def spy_dashboard():
    """Serve the SPY dashboard page"""
    from fastapi.responses import FileResponse
    return FileResponse("app/static/spy_dashboard.html")

@app.get("/fire-calc")
async def fire_calc():
    """Serve the FIRE calculator page"""
    from fastapi.responses import FileResponse
    return FileResponse("app/static/fire_calc.html")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "market_service": market_service.is_running,
        "market_hours": market_service.is_market_hours()
    } 