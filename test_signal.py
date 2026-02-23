import asyncio
import logging
import sys

# Setup root logger to see DEBUG output from our app
logging.basicConfig(level=logging.DEBUG, stream=sys.stdout, format='%(levelname)s - %(message)s')
logger = logging.getLogger()

from config.settings import Config
from presentation.cli.main import TradingAgent

async def test():
    config = Config()
    config.trading.mode = "paper"
    agent = TradingAgent(config)
    print("Testing SOL/IDR signal generation...")
    # Forcefully trigger the analysis cycle directly
    await agent._analyze_pair("SOL/IDR")
    
    # Check what signal was saved
    if "SOL/IDR" in agent.last_signals:
        signal = agent.last_signals["SOL/IDR"]
        print(f"\nFINAL SIGNAL: {signal['combined_action']}")
        print(f"CONFIDENCE: {signal['combined_confidence']}")
        print(f"TECHNICAL: {signal['technical_trend']}")
        print(f"VOLUME: {signal['volume_flow']}")
        print(f"REASON: {signal.get('reason', 'N/A')}")
        
    # Trigger asinkron cleanup
    await agent._cleanup()

if __name__ == "__main__":
    asyncio.run(test())
