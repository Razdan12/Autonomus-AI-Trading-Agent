import asyncio
import ccxt.async_support as ccxt
import os
from dotenv import load_dotenv

load_dotenv()

async def main():
    api_key = os.getenv("INDODAX_API_KEY")
    secret = os.getenv("INDODAX_SECRET")
    
    exchange = ccxt.indodax({
        "apiKey": api_key,
        "secret": secret,
        "enableRateLimit": True,
    })
    
    await exchange.load_markets()
    
    try:
        print("Testing limit buy order without postOnly...")
        order = await exchange.create_order(
            symbol='ETH/IDR',
            type='limit',
            side='buy',
            amount=0.0001,  # very small amount, maybe this causes invalid pair? Wait, indodax min trade is 10000 IDR!
            price=1000000,
        )
        print("Success without postOnly:", order)
    except Exception as e:
        print("Error no postOnly:", type(e).__name__, str(e))

    try:
        print("Testing market buy order...")
        order = await exchange.create_order(
            symbol='ETH/IDR',
            type='market',
            side='buy',
            amount=10000,  # 10k IDR min trade amount for market buy? In indodax market buy specifies cost, ccxt amount handles it?
            price=None,
        )
        print("Success market buy:", order)
    except Exception as e:
        print("Error market buy:", type(e).__name__, str(e))
        
    await exchange.close()

if __name__ == "__main__":
    asyncio.run(main())
