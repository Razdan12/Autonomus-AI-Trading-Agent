import sqlite3
import pandas as pd

conn = sqlite3.connect('trading_agent.db')
df = pd.read_sql_query("SELECT * FROM portfolio_snapshots ORDER BY id ASC", conn)
print("Columns in portfolio_snapshots:", df.columns.tolist())

if 'total_equity' in df.columns:
    df['equity_diff'] = df['total_equity'].diff()
    drops = df[df['equity_diff'] < -10000]
    if not drops.empty:
        print("\nSignificant Equity Drops (<-10,000 IDR):")
        print(drops[['snapshot_at', 'total_equity', 'equity_diff']])
        
        # Check trades around the biggest drop
        biggest_drop = df.loc[df['equity_diff'].idxmin()]
        drop_time = biggest_drop['snapshot_at']
        print(f"\nBiggest drop recorded at {drop_time}: {biggest_drop['equity_diff']} IDR")
        
        # Let's see some closed trades overall
        trades = pd.read_sql_query("SELECT id, symbol, side, status, pnl, opened_at, closed_at FROM trades WHERE status='closed' ORDER BY closed_at DESC LIMIT 10", conn)
        print("\nRecent 10 CLOSED trades:")
        print(trades)
    else:
        print("\nNo significant single-step equity drop found in snapshots. Maybe it bled slowly?")
conn.close()
