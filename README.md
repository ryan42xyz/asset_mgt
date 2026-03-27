# Asset Management Platform

A personal investment dashboard for US stock investors. Tracks holdings against a target allocation strategy, monitors risk gates (S&P 500 vs 200-day SMA + VIX), and surfaces rebalancing suggestions.

## Features

- **Portfolio dashboard** — real-time holdings with P&L, current vs. target allocation chart
- **Risk gate monitor** — alerts when S&P 500 drops below 200-day SMA and VIX > 30
- **Rebalancing suggestions** — which positions to buy/sell to return to target weights
- **SPY dashboard** — S&P 500 price + technical indicators
- **FIRE calculator** — retirement number calculator

## Quick Start

**Prerequisites:** Docker, Python 3.11+

```bash
# 1. Clone and enter the directory
cd toys/asset_mgt

# 2. Create Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Copy env template (edit if needed)
cp .env.example .env

# 4. Start everything
./start.sh
```

Open **http://localhost:8000** in your browser.

The demo user (id=1) is created automatically on first startup.

## Pages

| URL | Description |
|---|---|
| `/` | Main portfolio dashboard |
| `/spy-dashboard` | SPY / S&P 500 monitor |
| `/fire-calc` | FIRE retirement calculator |
| `/docs` | API documentation (Swagger UI) |
| `/health` | Health check |

## Architecture

```
FastAPI (port 8000)
├── /api/v1/auth        — demo user management
├── /api/v1/portfolio   — holdings CRUD + price refresh
├── /api/v1/strategy    — allocation analysis, risk gate, rebalancing
├── /api/v1/market      — live prices, indicators, exchange rates
└── /api/v1/fire-calc   — FIRE number calculations

PostgreSQL (port 5432)  — holdings, price history, risk gate state
Redis (port 6379)       — price + indicator cache
```

Market data is sourced from Yahoo Finance (free, ~15-min delay) with optional Alpha Vantage / IEX Cloud fallback.

## Target Allocation

| Category | Symbols | Weight |
|---|---|---|
| Cash / Short-term debt | DUSB, SGOV | 25% |
| S&P Equal Weight | RSP, SPYV | 20% |
| S&P Market Cap | SPY, VOO | 15% |
| High Beta | NVDA, QQQ | 15% |
| Global ex-US | DFAW | 10% |
| Defensive | BRK.B, GLD | 10% |

## Risk Gate

Triggers when **both** conditions are met:
- S&P 500 < 200-day moving average
- VIX > 30

Clears after S&P 500 closes above 200-day SMA for 10 consecutive days.

## Development

```bash
# Run tests
venv/bin/python3 test_system.py

# API docs
open http://localhost:8000/docs
```
