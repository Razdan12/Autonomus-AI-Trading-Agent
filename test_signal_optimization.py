import asyncio
from unittest.mock import MagicMock
from core.entities.technical_signal import TechnicalSignal
from core.entities.volume_signal import VolumeSignal
from use_cases.analysis.signal_generator import SignalGenerator

def test_whipsaw_choppy_market_rejection():
    generator = SignalGenerator()
    
    # 1. Technical signal (BULLISH trend)
    tech = TechnicalSignal(
        symbol="BTC/IDR",
        trend="BULLISH",
        momentum="WEAK",
        volatility="NORMAL",
        confidence=0.6,
        timeframe="1h",
        rsi=60,
        macd_value=0.5
    )
    
    # 2. Volume signal (Weak Whale)
    vol_weak = VolumeSignal(
        symbol="BTC/IDR",
        net_flow="ACCUMULATING",
        intensity="LOW",
        imbalance_score=0.4,
        confidence=0.5,
        whale_score=6, # Below 8
        whale_reason="Small spike"
    )
    
    # Generate signal in CHOPPY market
    res_weak = generator.generate_multi_timeframe(
        tech_signals={"1h": tech},
        volume_signal=vol_weak,
        market_regime="CHOPPY"
    )
    
    print("\n[TEST 1] Choppy Market + Weak Whale (Score 6) -> Should be VETOED (HOLD)")
    print(f"Action: {res_weak.action}")
    print(f"Reason: {res_weak.reason}")
    assert res_weak.action == "HOLD", "Gagal: Sinyal tidak difilter di pasar Choppy"
    assert "VETO CHOPPY AVOIDANCE" in res_weak.reason
    
    # 3. Volume signal (Strong Whale)
    vol_strong = VolumeSignal(
        symbol="BTC/IDR",
        net_flow="ACCUMULATING",
        intensity="HIGH",
        imbalance_score=0.9,
        confidence=0.9,
        whale_score=9, # Above 8
        whale_reason="Massive spike"
    )
    
    # Generate signal again in CHOPPY market but with high whale score
    res_strong = generator.generate_multi_timeframe(
        tech_signals={"1h": tech},
        volume_signal=vol_strong,
        market_regime="CHOPPY"
    )
    
    print("\n[TEST 2] Choppy Market + Strong Whale (Score 9) -> Should NOT be Vetoed (BUY/STRONG_BUY)")
    print(f"Action: {res_strong.action}")
    print(f"Reason: {res_strong.reason}")
    assert res_strong.action in ("BUY", "STRONG_BUY"), "Gagal: Sinyal terlalu ketat, melewatkan Whale nyata"
    assert "tapi Whale Score sangat tinggi" in res_strong.reason
    print("\n✅ Veto Whipsaw bekerja dengan baik!")

if __name__ == "__main__":
    test_whipsaw_choppy_market_rejection()
