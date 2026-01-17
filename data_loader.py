import time
import json
import yfinance as yf
from datetime import datetime
import os

# --- CONFIGURATION ---
UPDATE_INTERVAL = 300  # 5 minutes
CACHE_FILE = "market_snapshot.json"
TICKERS = ["NVDA", "AAPL", "MSFT", "TSLA", "AMD", "EURUSD=X", "^GSPC"] # Add your portfolio tickers here

def fetch_market_data():
    print(f"📥 Fetching data for {len(TICKERS)} tickers...")
    try:
        # Fetch 5 days to calculate % change
        data = yf.download(TICKERS, period="5d", interval="1d", progress=False, group_by='ticker')
        
        snapshot = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "prices": {}
        }
        
        for t in TICKERS:
            try:
                # Handle single vs multi-index columns
                df = data[t] if len(TICKERS) > 1 else data
                
                if not df.empty:
                    current = float(df['Close'].iloc[-1])
                    prev = float(df['Close'].iloc[-2]) if len(df) > 1 else current
                    change = current - prev
                    pct = (change / prev) * 100 if prev != 0 else 0.0
                    
                    snapshot["prices"][t] = {
                        "price": current,
                        "change": change,
                        "pct": pct
                    }
            except Exception:
                snapshot["prices"][t] = {"price": 0.0, "change": 0.0, "pct": 0.0}
                
        return snapshot
    except Exception as e:
        print(f"🔥 Error: {e}")
        return None

def main():
    print("🚀 TIC Data Loader Started (Local Mode)")
    while True:
        data = fetch_market_data()
        if data:
            # Atomic Write: Write to temp file, then rename (prevents reading half-written files)
            with open(CACHE_FILE + ".tmp", 'w') as f:
                json.dump(data, f)
            os.replace(CACHE_FILE + ".tmp", CACHE_FILE)
            print(f"✅ Updated {CACHE_FILE} at {data['timestamp']}")
        
        time.sleep(UPDATE_INTERVAL)

if __name__ == "__main__":
    main()
