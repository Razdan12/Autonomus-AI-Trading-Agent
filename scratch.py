import sqlite3
import pandas as pd

conn = sqlite3.connect('trading_agent.db')
df = pd.read_sql_query("SELECT id, symbol, side, status, pnl, pnl_percent, close_reason FROM trades WHERE status='closed'", conn)

total_trades = len(df)
winning_trades = len(df[df['pnl'] > 0])
losing_trades = len(df[df['pnl'] <= 0])
win_rate = winning_trades / total_trades * 100 if total_trades > 0 else 0
total_pnl = df['pnl'].sum()

print(f"Total Trades: {total_trades}")
print(f"Win Rate: {win_rate:.2f}% ({winning_trades}W / {losing_trades}L)")
print(f"Total PnL: {total_pnl:.2f} IDR")
print("\nTop Close Reasons:")
print(df['close_reason'].value_counts().head(5))
conn.close()
