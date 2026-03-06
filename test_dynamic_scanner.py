import asyncio
from config.settings import Config
from infrastructure.exchange.indodax_client import MarketDataFetcher
from use_cases.analysis.omni_scanner import OmniScanner

async def test_dynamic():
    print("Testing DYNAMIC:5 Configuration")
    import os
    os.environ["TRADING_PAIRS"] = "DYNAMIC:5"
    
    config = Config()
    print(config)
    
    market_data = MarketDataFetcher(config)
    scanner = OmniScanner(config, market_data)
    
    pairs = await scanner.get_liquid_pairs()
    print(f"\nFinal Selected Pairs ({len(pairs)}):")
    for pair in pairs:
        print(f" - {pair}")
        
    await market_data.close()

if __name__ == "__main__":
    asyncio.run(test_dynamic())
