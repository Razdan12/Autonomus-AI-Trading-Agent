from dataclasses import dataclass
from typing import Dict, Any, Optional

from core.entities.technical_signal import TechnicalSignal
from core.entities.volume_signal import VolumeSignal


@dataclass
class TradingSignal:
    """Final combined trading signal based on multi-factor analysis."""
    symbol: str
    action: str              # STRONG_BUY, BUY, HOLD, SELL, STRONG_SELL
    confidence: float        # 0.0 - 1.0
    reason: str              # Human-readable explanation

    # Component signals
    technical: Optional[TechnicalSignal] = None
    volume: Optional[VolumeSignal] = None

    # Multi-timeframe confirmation
    timeframes_aligned: int = 0
    total_timeframes: int = 1

    # AI (LLM) Audit results
    ai_decision: Optional[str] = None    # APPROVE, REJECT, WAIT
    ai_reasoning: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        res = {
            "symbol": self.symbol,
            "action": self.action,
            "confidence": self.confidence,
            "reason": self.reason,
            "technical_trend": None,
            "technical_momentum": None,
            "technical_confidence": None,
            "volume_flow": None,
            "volume_intensity": None,
            "volume_confidence": None,
            "combined_action": self.action,
            "combined_confidence": self.confidence,
            "timeframes_aligned": self.timeframes_aligned,
        }
        
        tech = self.technical
        if tech:
            res["technical_trend"] = tech.trend
            res["technical_momentum"] = tech.momentum
            res["technical_confidence"] = tech.confidence
            
        vol = self.volume
        if vol:
            res["volume_flow"] = vol.net_flow
            res["volume_intensity"] = vol.intensity
            res["volume_confidence"] = vol.confidence
            
        return res
