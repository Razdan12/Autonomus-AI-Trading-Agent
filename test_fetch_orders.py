import asyncio
from config.settings import Config
from infrastructure.exchange.indodax_client import MarketDataFetcher

async def main():
    config = Config()
    client = MarketDataFetcher(config)
    try:
        # Panggil fetch_open_orders jika tersedia
        print("\n=== FETCH OPEN ORDERS ===")
        if hasattr(client.exchange, "fetch_open_orders"):
            orders = await client.exchange.fetch_open_orders()
            print(f"Found {len(orders)} open orders.")
            for o in orders:
                print(f"ID: {o['id']}, Symbol: {o['symbol']}, Side: {o['side']}, Status: {o['status']}")
        else:
            print("fetch_open_orders not supported by this ccxt version for Indodax.")

        # Ambil trade history untuk ETH/IDR
        print("\n=== FETCH MY TRADES (ETH/IDR) ===")
        if hasattr(client.exchange, "fetch_my_trades"):
            trades = await client.exchange.fetch_my_trades("ETH/IDR", limit=5)
            print(f"Found {len(trades)} recent trades.")
            for t in trades:
                print(f"ID: {t['id']}, Symbol: {t['symbol']}, Side: {t['side']}, Amount: {t['amount']}, Price: {t['price']}")
                
    except Exception as e:
        print("Error:", e)
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())
