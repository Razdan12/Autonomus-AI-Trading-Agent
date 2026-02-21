import pytest
import time
from unittest.mock import Mock, patch
from analysis.volume_analyzer import VolumeAnalyzer

@pytest.fixture
def mock_db():
    return Mock()

@pytest.fixture
def mock_config():
    config = Mock()
    config.volume_anomaly.min_usd_value = 5000
    return config

def test_volume_analyzer_neutral_no_data(mock_config, mock_db):
    mock_db.get_volume_anomalies.return_value = []
    
    analyzer = VolumeAnalyzer(mock_config, mock_db)
    signal = analyzer.analyze("BTC/IDR")
    
    assert signal.net_flow == "NEUTRAL"
    assert signal.intensity == "LOW"
    assert signal.imbalance_score == 0.0
    assert signal.confidence == 0.0

def test_volume_analyzer_accumulation(mock_config, mock_db):
    mock_db.get_volume_anomalies.return_value = [
        {"side": "buy", "amount_usd": 15000, "timestamp": int(time.time()*1000)},
        {"side": "buy", "amount_usd": 20000, "timestamp": int(time.time()*1000)},
        {"side": "sell", "amount_usd": 5000, "timestamp": int(time.time()*1000)},
    ]
    
    analyzer = VolumeAnalyzer(mock_config, mock_db)
    signal = analyzer.analyze("BTC/IDR")
    
    # Buy USD: 35k, Sell USD: 5k, Total: 40k. Imbalance: 30 / 40 = 0.75
    assert signal.net_flow == "ACCUMULATING"
    assert signal.intensity == "MEDIUM"  # 40k > 15k (min_usd * 3)
    assert signal.imbalance_score == 0.75
    assert signal.confidence > 0.0

def test_volume_analyzer_distribution_high_intensity(mock_config, mock_db):
    mock_db.get_volume_anomalies.return_value = [
        {"side": "sell", "amount_usd": 50000, "timestamp": int(time.time()*1000)},
        {"side": "sell", "amount_usd": 15000, "timestamp": int(time.time()*1000)},
    ]
    
    analyzer = VolumeAnalyzer(mock_config, mock_db)
    signal = analyzer.analyze("BTC/IDR")
    
    assert signal.net_flow == "DISTRIBUTING"
    assert signal.intensity == "HIGH"
    assert signal.imbalance_score == -1.0
