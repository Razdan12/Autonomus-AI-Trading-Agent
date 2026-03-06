from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from presentation.api.database import (
    get_portfolio_summary,
    get_active_positions,
    get_recent_signals,
    get_volume_anomalies,
    get_equity_curve,
    get_latest_candles,
    get_trade_history,
    get_daily_target_status,
)
from presentation.api.models import (
    PortfolioSummaryResponse,
    PositionResponse,
    SignalResponse,
    VolumeAnomalyResponse,
    ChartDataPoint,
    CandleResponse,
    TradeHistoryResponse,
    DailyTargetResponse,
)
from typing import List

app = FastAPI(
    title="AI Trading Agent Dashboard API",
    description="Backend API for the AI Trading Web Dashboard",
    version="2.0.0"
)

# Enable CORS for React Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/portfolio", response_model=PortfolioSummaryResponse)
def api_portfolio_summary():
    """Get the latest portfolio summary."""
    return get_portfolio_summary()

@app.get("/api/positions", response_model=List[PositionResponse])
def api_active_positions():
    """Get all open trading positions."""
    return get_active_positions()

@app.get("/api/signals", response_model=List[SignalResponse])
def api_recent_signals(limit: int = 20):
    """Get the most recent AI generated signals."""
    return get_recent_signals(limit)

@app.get("/api/volume", response_model=List[VolumeAnomalyResponse])
def api_volume_anomalies(limit: int = 20):
    """Get the most recent detected volume anomalies."""
    return get_volume_anomalies(limit)

@app.get("/api/equity", response_model=List[ChartDataPoint])
def api_equity_curve(days: int = None):
    """Get the historical equity curve data for charting."""
    return get_equity_curve(days)

@app.get("/api/candles/{symbol}", response_model=List[CandleResponse])
def api_candles(symbol: str, timeframe: str = "1h", limit: int = 100):
    """Get historical OHLCV candles for charting."""
    symbol = symbol.replace('-', '/').upper()
    return get_latest_candles(symbol, timeframe, limit)

@app.get("/api/trades", response_model=List[TradeHistoryResponse])
def api_trade_history(limit: int = 50):
    """Get all trade history (open + closed), newest first."""
    return get_trade_history(limit)

@app.get("/api/daily-target", response_model=DailyTargetResponse)
def api_daily_target():
    """Get today's trading target status and progress."""
    return get_daily_target_status()
