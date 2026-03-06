"""
Omni-Scanner - The Eyes of the Leviathan.
Scans all available Indodax markets concurrently to filter out illiquid assets.
Supports dynamic top N highly traded coins selection.
"""

import asyncio
from typing import List, Dict, Any

from config.settings import Config
from core.interfaces.market_data_port import IMarketData
from utils.logger import get_logger

logger = get_logger(__name__)


class OmniScanner:
    """
    Asynchronous market scanner.
    Filters out dead coins based on 24-hour USD volume, or picks the top active IDR pairs.
    """

    def __init__(self, config: Config, market_data: IMarketData):
        self.config = config
        self.market = market_data
        
        # We will use the config's min_usd_value or default to $50,000 equivalent in IDR
        # Assuming 1 USD = 16,000 IDR
        self.min_24h_vol_idr = 50_000 * 16_000
        
        # Commonly traded stablecoins or assets to ignore when finding volatile coins for profit
        self.blacklist_dynamic = {"USDT/IDR", "USDC/IDR", "BUSD/IDR", "FDUSD/IDR", "DAI/IDR"}

    async def get_liquid_pairs(self) -> List[str]:
        """
        Fetch pairs based on config.
        If dynamic pairs is active, fetch all tickers and get top N.
        Otherwise, validate explicit config pairs or fetch all IDR pairs above a liquidity threshold.
        """
        try:
            # 1. Check if user configured specific pairs manually
            if not self.config.trading.is_dynamic_pairs:
                configured_pairs = self.config.trading.pairs
                if configured_pairs and configured_pairs[0] != "ALL":
                    logger.info(f"🔍 Using {len(configured_pairs)} explicitly configured pairs.")
                    return await self.market.validate_pairs(configured_pairs)

            logger.info("🌊 Omni-Scanner diving into markets to find high volume assets...")
            
            # 2. Dynamic approach: Grab ALL tickers at once efficiently using CCXT fetch_tickers
            # Since MarketDataFetcher may not implement fetch_tickers if it wasn't added yet, use getattr fallback
            if hasattr(self.market, "fetch_tickers"):
                all_tickers = await self.market.fetch_tickers()
            else:
                logger.error("❌ MarketDataFetcher is missing fetch_tickers() method. Aborting dynamic scan.")
                return []
                
            # Filter to only IDR pairs, non-stablecoins, and valid volume
            valid_pairs = []
            
            for symbol, ticker in all_tickers.items():
                if not symbol.endswith("/IDR"):
                    continue
                if symbol in self.blacklist_dynamic:
                    continue
                    
                # In Indodax, quoteVolume is the base currency value (usually 24h IDR volume directly)
                # Some pairs might have None
                quote_vol = ticker.get("quoteVolume")
                if quote_vol is not None and quote_vol > 0:
                     valid_pairs.append({
                         "symbol": symbol,
                         "quoteVolume": float(quote_vol)
                     })

            # Sort descending by quote volume
            valid_pairs.sort(key=lambda x: x["quoteVolume"], reverse=True)
            
            if self.config.trading.is_dynamic_pairs:
                top_n = self.config.trading.dynamic_pair_count
                liquid_pairs = [p["symbol"] for p in valid_pairs[:top_n]]
                
                logger.info(f"🎯 Omni-Scanner dynamically selected TOP {len(liquid_pairs)} coins by Volume (24h IDR).")
                for idx, pair in enumerate(valid_pairs[:top_n], 1):
                    logger.info(f"   {idx}. {pair['symbol']} - Vol: Rp {pair['quoteVolume']:,.0f}")
                    
                return liquid_pairs
            else:
                # "ALL" fallback logic that just filters out dead coins
                liquid_pairs = [p["symbol"] for p in valid_pairs if p["quoteVolume"] >= self.min_24h_vol_idr]
                logger.info(f"🎯 Omni-Scanner filtered {len(all_tickers)} pairs down to {len(liquid_pairs)} highly liquid assets.")
                return liquid_pairs

        except Exception as e:
            logger.error(f"❌ Omni-Scanner critical failure: {e}")
            # Fallback to safe default if all else fails
            fallback = ["BTC/IDR", "ETH/IDR", "USDT/IDR"]
            logger.warning(f"⚠️ Falling back to safe defaults: {fallback}")
            return fallback

