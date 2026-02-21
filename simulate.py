import sqlite3
import os
from datetime import datetime, timedelta
import random
from datetime import timezone

DB_PATH = os.path.join(os.path.dirname(__file__), "trading_agent.db")

def simulate():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    now = datetime.now(timezone.utc)
    
    # 1. Simulate Portfolio Equity Curve over the last 24 hours
    c.execute("DELETE FROM portfolio_snapshots")
    base_equity = 10000000 # 10 Juta IDR
    equity = base_equity
    for i in range(24, -1, -1):
        snap_time = now - timedelta(hours=i)
        
        # Add some random walk to equity
        change = random.uniform(-0.01, 0.02) * equity
        equity += change
        
        drawdown = 0.0
        if equity < base_equity:
            drawdown = ((base_equity - equity) / base_equity) * 100
            
        c.execute("""
            INSERT INTO portfolio_snapshots 
            (total_equity, available_balance, unrealized_pnl, realized_pnl_today, open_positions, snapshot_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            equity, 
            equity * 0.5, # Fake available balance
            random.uniform(-50000, 150000), 
            random.uniform(10000, 300000),
            2,
            snap_time.isoformat()
        ))
        
    # 2. Add some fake Open Trades
    # Clear existing trades for a clean demo
    # c.execute("DELETE FROM trades") 
    
    demo_trades = [
        {
            "symbol": "BTC/IDR",
            "side": "buy",
            "order_type": "market",
            "price": 950000000,
            "amount": 0.01,
            "cost": 9500000,
            "stop_loss": 900000000,
            "take_profit": 1100000000,
            "status": "open",
            "mode": "paper",
            "opened_at": (now - timedelta(hours=2)).isoformat(),
        },
        {
            "symbol": "SOL/IDR",
            "side": "buy",
            "order_type": "market",
            "price": 1500000,
            "amount": 5.0,
            "cost": 7500000,
            "stop_loss": 1400000,
            "take_profit": 1800000,
            "status": "open",
            "mode": "paper",
            "opened_at": (now - timedelta(minutes=45)).isoformat(),
        }
    ]
    
    for t in demo_trades:
        c.execute("""
            INSERT INTO trades
            (symbol, side, order_type, price, amount, cost, stop_loss, take_profit, status, mode, opened_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            t["symbol"], t["side"], t["order_type"], t["price"], t["amount"], t["cost"],
            t["stop_loss"], t["take_profit"], t["status"], t["mode"], t["opened_at"]
        ))
        
    trade_ids = [c.lastrowid if hasattr(c, 'lastrowid') else 1, 2] # rough fix
    
    # We also need to update position unrealized PnL in the API, 
    # but the API computes unrealized PnL assuming `current_price` updates. 
    # Since our DB doesn't store current live price, we will just fake the response in the API temporary 
    # or let the API return 0 PnL for positions if there's no live fetch.
    
    conn.commit()
    conn.close()
    print("Simulation data injected successfully into SQLite!")

if __name__ == "__main__":
    simulate()
