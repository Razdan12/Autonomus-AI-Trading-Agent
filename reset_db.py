import sqlite3
import os

from infrastructure.storage.sqlite_repository import SqliteRepository

def reset_database():
    db_path = "trading_agent.db"
    
    # Force delete the file to start fresh if needed
    if os.path.exists(db_path):
        os.remove(db_path)
    
    if os.path.exists(db_path + "-shm"):
        os.remove(db_path + "-shm")
        
    if os.path.exists(db_path + "-wal"):
        os.remove(db_path + "-wal")

    print(f"🔄 Memulai proses reset database '{db_path}' dari awal...")
    
    try:
        # Recreate tables from scratch using the existing repository logic
        db = SqliteRepository("trading_agent.db")
        
        # Inject an initial zero snapshot so the dashboard doesn't crash before the first cycle
        db.save_portfolio_snapshot({
            "total_equity": 0.0,
            "available_balance": 0.0,
            "unrealized_pnl": 0.0,
            "realized_pnl_today": 0.0,
            "open_positions": 0
        })
        
        print("✅ Berhasil! Database telah di-rebuild ulang beserta seluruh skema tabelnya.")
        print("💡 Silakan jalankan ulang bot Anda (misal: pm2 restart ai-trading-bot)")
        
    except Exception as e:
        print(f"❌ Terjadi kesalahan saat mereset database: {e}")

if __name__ == "__main__":
    confirm = input("⚠️ PERINGATAN: Ini akan menghapus seluruh data simulasi bot. Lanjutkan? (y/n): ")
    if confirm.lower() == 'y':
        reset_database()
    else:
        print("Dibatalkan.")
