"""
CryptoPanic Client - Fetches live cryptocurrency news headlines asynchronously.
"""

import aiohttp
import asyncio
from typing import List

from config.settings import Config
from core.interfaces.news_port import INewsData
from utils.logger import get_logger

logger = get_logger(__name__)


class CryptoPanicClient(INewsData):
    """Implementation of INewsData using the free CryptoPanic API."""

    def __init__(self, config: Config):
        self.config = config
        self.api_key = config.news.cryptopanic_api_key
        self.base_url = "https://cryptopanic.com/api/developer/v2/posts/"
        self.session = None

        # Caching and Rate Limiting
        self._cache = {}  # {symbol: {"headlines": List[str], "timestamp": float}}
        self._cache_ttl = 600  # 10 minutes cache
        self._last_429_time = 0
        self._cooldown_period = 60  # 60 seconds cooldown after 429

    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def fetch_recent_headlines(self, symbol: str, limit: int = 20) -> List[str]:
        """Fetch recent headlines for a symbol using aiohttp."""
        
        # Fast exit if sentiment is disabled or no API key is set
        if not self.config.risk.enable_sentiment_veto or not self.api_key:
            return []
            
        # Parse symbol (e.g., 'BTC/IDR' -> 'BTC')
        coin = symbol.split('/')[0].upper()
        
        import time
        now = time.time()

        # 1. 429 Cooldown check
        if now - self._last_429_time < self._cooldown_period:
            cached = self._cache.get(coin)
            if cached:
                logger.debug(f"🧊 CryptoPanic in 429 cooldown. Serving (potentially expired) cache for {coin}.")
                return cached["headlines"]
            return []

        # 2. Cache Hit check (within TTL)
        cached = self._cache.get(coin)
        if cached and (now - cached["timestamp"]) < self._cache_ttl:
            logger.debug(f"📦 CryptoPanic cache hit for {coin}.")
            return cached["headlines"]
        
        headlines = []
        try:
            params = {
                "auth_token": self.api_key,
                "currencies": coin,
                "kind": "news",
                "filter": "important", # Pre-filter for high-impact news if possible
            }
            
            session = await self._get_session()
            async with session.get(self.base_url, params=params, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    results = data.get("results", [])
                    for item in results:
                        title = item.get("title")
                        if title:
                            headlines.append(title)
                            if len(headlines) >= limit:
                                break
                    
                    # Update cache on success
                    self._cache[coin] = {
                        "headlines": headlines,
                        "timestamp": now
                    }
                elif response.status == 429:
                    self._last_429_time = now
                    logger.warning(f"⚠️ CryptoPanic API Rate Limited (429) for {coin}. Cooling down for {self._cooldown_period}s.")
                    # Serve expired cache if available
                    if cached:
                        return cached["headlines"]
                else:
                    logger.warning(f"⚠️ CryptoPanic API returned status {response.status} for {coin}")
                        
            return headlines
            
        except asyncio.TimeoutError:
            logger.warning(f"⏳ CryptoPanic API timeout for {symbol}")
            return []
        except Exception as e:
            logger.error(f"❌ CryptoPanic client error for {symbol}: {e}")
            return []

    async def close(self):
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()
            logger.info("🔌 CryptoPanic API session closed.")
