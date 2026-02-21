"""
Volume Anomaly Tracker - Replaces Whale Alert.
Analyzes Indodax orderbook imbalances and massive single trades.
"""

import time
from typing import Dict, List, Optional
from datetime import datetime, timedelta

from config import Config
from data.market_data import MarketDataFetcher
from data.database import Database
from utils.logger import get_logger

logger = get_logger(__name__)


class VolumeTracker:
    """
    On-chain alternative to Whale Alert using exchange orderbooks and trades.
    Identifies high-volume spikes and massive orderbook walls.
    """
    def __init__(self, config: Config, market_data: MarketDataFetcher, db: Database):
        self.config = config
        self.market = market_data
        self.db = db
    
    def scan_anomalies(self, symbol: str):
        """Scan active market for volume spikes or extreme orderbook walls."""
        self._check_large_trades(symbol)
        self._check_orderbook_walls(symbol)

    def _check_large_trades(self, symbol: str):
        """Fetch recent trades and flag massive market buys/sells."""
        try:
            trades = self.market.fetch_trades(symbol, limit=100)
            if not trades:
                return

            # Indodax IDR threshold
            min_usd = self.config.volume_anomaly.min_usd_value
            min_idr = min_usd * 16000  # Approx FX rate for hardcap scaling

            # Limit logs to avoid spamming
            logged_spikes = 0
            for t in trades:
                cost = t.get("cost", 0)
                if cost >= min_idr:
                    event = {
                        "symbol": symbol,
                        "anomaly_type": "trade_spike",
                        "side": t.get("side", "unknown"),
                        "amount": t.get("amount", 0),
                        "price": t.get("price", 0),
                        "amount_usd": cost / 16000,
                        "timestamp": t.get("timestamp", int(time.time() * 1000))
                    }
                    self.db.save_volume_anomaly(event)
                    if logged_spikes < 3:
                        logger.info(f"🚨 LARGE TRADE: {symbol} {event['side']} {event['amount_usd']:,.0f} USD")
                        logged_spikes += 1

        except Exception as e:
            logger.error(f"Failed to scan large trades for {symbol}: {e}")

    def _check_orderbook_walls(self, symbol: str):
        """Analyze orderbook depth to find massive bid/ask walls."""
        try:
            # fetch top 50 levels
            ob = self.market.fetch_order_book(symbol, limit=50)
            bids = ob.get("bids", [])
            asks = ob.get("asks", [])
            
            if not bids or not asks:
                return
                
            current_price = bids[0][0]
            
            # Find the largest bid (Buy Wall)
            max_bid = max(bids, key=lambda x: x[1]*x[0]) if bids else [0, 0]
            bid_vol_idr = max_bid[0] * max_bid[1]
            
            # Find the largest ask (Sell Wall)
            max_ask = max(asks, key=lambda x: x[1]*x[0]) if asks else [0, 0]
            ask_vol_idr = max_ask[0] * max_ask[1]
            
            min_idr = self.config.volume_anomaly.min_usd_value * 16000
            
            if bid_vol_idr >= min_idr:
                event = {
                    "symbol": symbol,
                    "anomaly_type": "orderbook_wall",
                    "side": "buy", # Bid wall acts as support / fake accumulation
                    "amount": max_bid[1],
                    "price": max_bid[0],
                    "amount_usd": bid_vol_idr / 16000,
                    "timestamp": int(time.time() * 1000)
                }
                self.db.save_volume_anomaly(event)
                logger.debug(f"🧱 BUY WALL: {symbol} {event['amount_usd']:,.0f} USD at {max_bid[0]:,.0f}")
                
            if ask_vol_idr >= min_idr * 1.5:  # Sell walls need to be thicker to trigger anomaly
                event = {
                    "symbol": symbol,
                    "anomaly_type": "orderbook_wall",
                    "side": "sell",
                    "amount": max_ask[1],
                    "price": max_ask[0],
                    "amount_usd": ask_vol_idr / 16000,
                    "timestamp": int(time.time() * 1000)
                }
                self.db.save_volume_anomaly(event)
                logger.debug(f"🧱 SELL WALL: {symbol} {event['amount_usd']:,.0f} USD at {max_ask[0]:,.0f}")
                
        except Exception as e:
            logger.error(f"Failed to scan orderbook walls for {symbol}: {e}")
