import aiohttp
import json
from typing import Optional, Dict, Any
from utils.logger import get_logger

logger = get_logger(__name__)

class GeminiClient:
    """Client for Google Gemini API."""
    
    def __init__(self, api_key: str, model_name: str = "gemini-2.5-flash"):
        self.api_key = api_key
        self.model_name = model_name
        self.url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        
    async def generate_response(self, prompt: str) -> Optional[str]:
        """Send a prompt to Gemini and get completion."""
        if not self.api_key or "YOUR_GEMINI_API_KEY" in self.api_key:
            logger.warning("⚠️ Gemini API Key not set properly. Skipping LLM call.")
            return None
            
        payload = {
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "topK": 40,
                "topP": 0.95,
                "maxOutputTokens": 1024,
            }
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.url, json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"❌ Gemini API Error ({response.status}): {error_text}")
                        return None
                        
                    data = await response.json()
                    try:
                        return data["candidates"][0]["content"]["parts"][0]["text"]
                    except (KeyError, IndexError) as e:
                        logger.error(f"❌ Failed to parse Gemini response: {e}")
                        return None
        except Exception as e:
            logger.error(f"❌ Gemini Client Exception: {e}")
            return None
