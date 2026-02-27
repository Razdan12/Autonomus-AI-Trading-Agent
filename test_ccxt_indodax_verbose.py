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
        "verbose": True
    })
    
    await exchange.load_markets()
    
    try:
        print("\n\n--- Testing limit buy order ---")
        order = await exchange.create_order(
            symbol='ETH/IDR',
            type='limit',
            side='buy',
            amount=0.0001,
            price=1000000,
            params={'pair': 'eth_idr'}  # Override the incorrect 'ethidr' pair
        )
        print("Success:", order)
    except Exception as e:
        print("Error:", type(e).__name__, str(e))
        
    await exchange.close()

if __name__ == "__main__":
    asyncio.run(main())
