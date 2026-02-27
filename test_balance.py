import asyncio
from config.settings import Config
from infrastructure.exchange.indodax_client import MarketDataFetcher

async def main():
    config = Config()
    client = MarketDataFetcher(config)
    try:
        balance = await client.fetch_balance()
        print("\n=== RAW BALANCE RESPONSE ===")
        print(balance.get("total", {}))
        print(balance.get("free", {}))
        print("============================\n")
    except Exception as e:
        print("Error:", e)
    await client.close()

if __name__ == "__main__":
    asyncio.run(main())
