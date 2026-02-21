"""
Configuration Management - AI Trading Agent
Loads and validates all settings from .env file.
"""

import os
from dataclasses import dataclass, field
from typing import List
from dotenv import load_dotenv

load_dotenv()


@dataclass
class IndodaxConfig:
    api_key: str = ""
    secret: str = ""


@dataclass
class VolumeAnomalyConfig:
    multiplier: float = 3.0
    min_usd_value: int = 5_000
    poll_interval_minutes: int = 10


@dataclass
class RiskConfig:
    risk_per_trade: float = 0.02          # 2% max per position
    max_open_positions: int = 3
    daily_drawdown_limit: float = 0.05    # 5% daily max drawdown
    stop_loss_atr_multiplier: float = 1.5
    take_profit_rr_ratio: float = 2.0     # Risk:Reward = 1:2


@dataclass
class TradingConfig:
    mode: str = "paper"                   # "paper" or "live"
    pairs: List[str] = field(default_factory=lambda: ["BTC/IDR", "ETH/IDR", "SOL/IDR"])
    timeframe: str = "1h"
    analysis_interval_minutes: int = 60


@dataclass
class LogConfig:
    level: str = "INFO"
    directory: str = "logs"


class Config:
    """Central configuration loaded from environment variables."""

    def __init__(self):
        self.indodax = IndodaxConfig(
            api_key=os.getenv("INDODAX_API_KEY", ""),
            secret=os.getenv("INDODAX_SECRET", ""),
        )

        self.volume_anomaly = VolumeAnomalyConfig(
            multiplier=float(os.getenv("VOLUME_ANOMALY_MULTIPLIER", "3.0")),
            min_usd_value=int(os.getenv("VOLUME_ANOMALY_MIN_USD_VALUE", "5000")),
            poll_interval_minutes=int(os.getenv("VOLUME_POLL_INTERVAL_MINUTES", "10")),
        )

        self.risk = RiskConfig(
            risk_per_trade=float(os.getenv("RISK_PER_TRADE", "0.02")),
            max_open_positions=int(os.getenv("MAX_OPEN_POSITIONS", "3")),
            daily_drawdown_limit=float(os.getenv("DAILY_DRAWDOWN_LIMIT", "0.05")),
            stop_loss_atr_multiplier=float(os.getenv("STOP_LOSS_ATR_MULTIPLIER", "1.5")),
            take_profit_rr_ratio=float(os.getenv("TAKE_PROFIT_RR_RATIO", "2.0")),
        )

        pairs_str = os.getenv("TRADING_PAIRS", "BTC/IDR,ETH/IDR,SOL/IDR")
        self.trading = TradingConfig(
            mode=os.getenv("TRADING_MODE", "paper"),
            pairs=[p.strip() for p in pairs_str.split(",")],
            timeframe=os.getenv("TIMEFRAME", "1h"),
            analysis_interval_minutes=int(os.getenv("ANALYSIS_INTERVAL_MINUTES", "60")),
        )

        self.log = LogConfig(
            level=os.getenv("LOG_LEVEL", "INFO"),
            directory=os.getenv("LOG_DIR", "logs"),
        )

    def validate(self) -> List[str]:
        """Validate config and return list of warnings/errors."""
        issues = []

        if self.trading.mode == "live":
            if not self.indodax.api_key:
                issues.append("ERROR: INDODAX_API_KEY required for live trading")
            if not self.indodax.secret:
                issues.append("ERROR: INDODAX_SECRET required for live trading")



        if self.risk.risk_per_trade > 0.05:
            issues.append("WARNING: RISK_PER_TRADE > 5% — very aggressive risk level")

        if self.trading.timeframe not in ("1m", "5m", "15m", "30m", "1h", "4h", "1d"):
            issues.append(f"WARNING: Timeframe '{self.trading.timeframe}' may not be supported")

        return issues

    def __repr__(self) -> str:
        mode_emoji = "📝" if self.trading.mode == "paper" else "💰"
        return (
            f"Config({mode_emoji} mode={self.trading.mode}, "
            f"pairs={self.trading.pairs}, "
            f"tf={self.trading.timeframe}, "
            f"risk={self.risk.risk_per_trade*100:.0f}%)"
        )
