"""
Volume & Imbalance Analyzer
Analyzes volume anomalies (large trades, orderbook walls) to determine 
smart money flow direction (Accumulation or Distribution).
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
import time

from config import Config
from data.database import Database
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class VolumeSignal:
    """Result of volume anomaly analysis."""
    symbol: str
    net_flow: str         # ACCUMULATING, DISTRIBUTING, NEUTRAL
    intensity: str        # HIGH, MEDIUM, LOW
    imbalance_score: float # -1.0 to +1.0 (negative = sell bias, positive = buy bias)
    confidence: float     # 0.0 - 1.0

    def to_dict(self):
        return {
            "symbol": self.symbol,
            "net_flow": self.net_flow,
            "intensity": self.intensity,
            "imbalance_score": self.imbalance_score,
            "confidence": self.confidence,
        }


class VolumeAnalyzer:
    """
    Analyzes historical and real-time volume anomalies from the database
    to determine the direction of smart money flow.
    """

    def __init__(self, config: Config, db: Database):
        self.config = config
        self.db = db

    def analyze(self, symbol: str) -> VolumeSignal:
        """
        Analyze volume anomalies for a symbol to generate a direction signal.
        """
        # Look back 24 hours (86400000 ms)
        lookback_ms = int(time.time() * 1000) - (24 * 60 * 60 * 1000)
        anomalies = self.db.get_volume_anomalies(symbol, lookback_ms)
        
        if not anomalies:
            return VolumeSignal(symbol, "NEUTRAL", "LOW", 0.0, 0.0)

        # 1. Calculate Imbalance Score based on USD volume
        buy_usd = sum(e["amount_usd"] for e in anomalies if e["side"] == "buy")
        sell_usd = sum(e["amount_usd"] for e in anomalies if e["side"] == "sell")
        
        total_usd = buy_usd + sell_usd
        
        if total_usd == 0:
            return VolumeSignal(symbol, "NEUTRAL", "LOW", 0.0, 0.0)
            
        # Imbalance Score: -1.0 to 1.0
        # Positive = Buyers dominating (huge buy trades or massive support walls)
        # Negative = Sellers dominating (huge sell trades or massive resistance walls)
        imbalance_score = (buy_usd - sell_usd) / total_usd
        
        # 2. Determine Net Flow
        if imbalance_score > 0.3:
            net_flow = "ACCUMULATING"
        elif imbalance_score < -0.3:
            net_flow = "DISTRIBUTING"
        else:
            net_flow = "NEUTRAL"
            
        # 3. Determine Intensity based on total anomaly volume
        # We define a "high" intensity if total anomaly volume is very 
        # significant vs the minimum threshold
        min_usd = self.config.volume_anomaly.min_usd_value
        if total_usd > min_usd * 10:
            intensity = "HIGH"
        elif total_usd > min_usd * 3:
            intensity = "MEDIUM"
        else:
            intensity = "LOW"
            
        # 4. Confidence Score
        # High volume + strong one-sided imbalance = high confidence
        volume_factor = min(1.0, total_usd / (min_usd * 15))
        imbalance_factor = abs(imbalance_score)
        
        # Confidence is a blend of how much volume we saw and how one-sided it was
        confidence = (volume_factor * 0.4) + (imbalance_factor * 0.6)
        
        signal = VolumeSignal(
            symbol=symbol,
            net_flow=net_flow,
            intensity=intensity,
            imbalance_score=round(imbalance_score, 3),
            confidence=round(confidence, 2)
        )
        
        logger.info(
            f"📊 {symbol} Volume Anomaly → {net_flow} ({intensity}) | "
            f"Imbalance: {imbalance_score:+.2f} | Conf: {confidence:.0%}"
        )
        
        return signal
