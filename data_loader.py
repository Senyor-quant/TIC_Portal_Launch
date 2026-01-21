import json
import pandas as pd
import yfinance as yf
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, date
import os
import toml 
import math
import concurrent.futures
import time

# --- CONFIGURATION ---
UPDATE_INTERVAL = 300  # 5 minutes (Prices & Sheets)
EVENTS_INTERVAL = 43200 # 12 Hours (Earnings Dates)
MARKET_FILE = "market_snapshot.json"
DB_FILE = "database_snapshot.json"
HISTORY_FILE = "history.json" # <--- NEW FILE

# --- GOOGLE AUTH SETUP ---
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def get_gspread_client():
    """Reads secrets.toml and authenticates with Google."""
    try:
        with open(".streamlit/secrets.toml", "r") as f:
            secrets = toml.load(f)
        creds_info = secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
        return gspread.authorize(creds)
    except Exception as e:
        print(f"❌ Auth Error: {e}")
        return None

def fetch_database_snapshot():
    """Fetches ALL tabs from Google Sheets and SCRUBS sensitive data."""
    print("📥 Fetching Google Sheets Database...")
    client = get_gspread_client()
    if not client: return None
    
    snapshot = {}
    try:
        sheet = client.open("TIC_Database_Master")
        tabs = ["Fundamentals", "Quant", "Members", "Events", "Proposals", "Votes", "Attendance", "Expenses"]
        
        for tab in tabs:
            try:
                ws = sheet.worksheet(tab)
                data = ws.get_all_values()
                
                # --- SECURITY SCRUBBER ---
                if tab == "Members" and len(data) > 0:
                    headers = [h.lower() for h in data[0]]
                    sensitive_indices = [
                        i for i, h in enumerate(headers) 
                        if "password" in h or "secret" in h or "key" in h
                    ]
                    
                    if sensitive_indices:
                        print(f"   🛡️ Scrubbing sensitive columns from {tab}...")
                        clean_data = []
                        clean_data.append(data[0]) 
                        for row in data[1:]:
                            new_row = list(row) 
                            for idx in sensitive_indices:
                                if idx < len(new_row):
                                    new_row[idx] = "" 
                            clean_data.append(new_row)
                        data = clean_data 
                # -------------------------------

                snapshot[tab] = data
                print(f"   - Fetched {tab} ({len(data)} rows)")
            except Exception as e:
                print(f"   ⚠️ Could not fetch {tab}: {e}")
                snapshot[tab] = []
                
        snapshot["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return snapshot
        
    except Exception as e:
        print(f"🔥 Google Sheet Error: {e}")
        return None

TICKER_MAP = {
    "ADYEN": "ADYEN.AS", "PRX": "PRX.AS", "INGA": "INGA.AS", "FLOW": "FLOW.AS", 
    "VLK": "VLK.AS", "RWE": "RWE.DE", "ENR": "ENR.DE", "HEI": "HEI.DE", 
    "DIE": "DIE.BR", "AGS": "AGS.BR", "UMI": "UMI.BR", "ENGI": "ENGI.PA", 
    "AIR": "AIR.PA", "RR.": "RR.L", "BFT": "BFT.BR", "IOC": "IOC.L", "NURS": "NURS.DE"
}

def extract_tickers_from_snapshot(db_snapshot):
    """Helper to get a clean list of unique tickers from the loaded DB."""
    tickers = set()
    
    def get_from_tab(tab_name, col_options):
        data = db_snapshot.get(tab_name, [])
        if len(data) < 2: return
        headers = [h.lower() for h in data[0]]
        
        idx = -1
        for opt in col_options:
            if opt in headers:
                idx = headers.index(opt)
                break
        
        if idx != -1:
            for row in data[1:]:
                if len(row) > idx:
                    raw_t = row[idx].strip().upper()
                    if raw_t and "CASH" not in raw_t and "EUR" not in raw_t:
                        if raw_t in TICKER_MAP:
                            mapped_t = TICKER_MAP[raw_t]
                            tickers.add(mapped_t)
                        else:
                            tickers.add(raw_t)

    get_from_tab("Fundamentals", ["ticker"])
    get_from_tab("Quant", ["ticker", "model_id"])
    return list(tickers)

def fetch_single_calendar_event(t):
    """Helper: Fetches one ticker's earnings date (runs in parallel)."""
    try:
        if not isinstance(t, str): return None
        stock = yf.Ticker(t)
        cal = stock.calendar
        if cal and 'Earnings Date' in cal:
            dates = cal['Earnings Date']
            if dates:
                next_date = dates[0]
                if next_date >= date.today():
                    return {
                        'title': f"{t} Earnings", 'ticker': t,
                        'date': next_date.strftime('%Y-%m-%d'),
                        'type': 'market', 'audience': 'all'
                    }
    except:
        return None
    return None

def fetch_market_events_parallel(ticker_list):
    """Runs the heavy earnings fetch in parallel threads."""
    print(f"📅 Updating Earnings Calendar for {len(ticker_list)} tickers...")
    events = []
    safe_tickers = ticker_list[:50] 
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch_single_calendar_event, t): t for t in safe_tickers}
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res:
                events.append(res)
    
    print(f"✅ Found {len(events)} upcoming events.")
    return events

def fetch_market_prices(ticker_list):
    """
    SUPER STEALTH MODE: 
    1. Uses a fake Browser User-Agent to fix '401 Unauthorized'
    2. Fetches 1-by-1 to avoid 'Rate Limit'
    """
    print(f"💹 Fetching Prices for {len(ticker_list)} assets (Stealth Mode)...")
    
    # 1. Define the 'Browser Mask' (The Secret Sauce)
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    })

    # 2. Add Indices manually
    full_list = set(ticker_list)
    full_list.update(["EURUSD=X", "^GSPC", "^VIX", "BTC-USD", "JPYEUR=X", "GBPEUR=X"])
    
    market_snap = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "prices": {}
    }
    
    # 3. Sequential Loop
    for t in full_list:
        try:
            time.sleep(0.25) # Sleep to look human
            
            # Pass the 'session' to yfinance
            dat = yf.Ticker(t, session=session)
            
            # Try Fast Info
            price = dat.info.get('regularMarketPrice') or dat.info.get('currentPrice') or dat.info.get('previousClose')
            prev = dat.info.get('previousClose')
            
            # Fallback to History
            if price is None:
                hist = dat.history(period="5d")
                if not hist.empty:
                    price = float(hist['Close'].iloc[-1])
                    prev = float(hist['Close'].iloc[-2]) if len(hist) > 1 else price
            
            # Calculate Data
            if price and prev:
                change = price - prev
                pct = (change / prev) * 100
            else:
                price = 0.0; change = 0.0; pct = 0.0

            market_snap["prices"][t] = {"price": price, "change": change, "pct": pct}
            print(f"   ✅ {t}: {price}")

        except Exception as e:
            print(f"   ⚠️ Failed {t}: {e}")
            market_snap["prices"][t] = {"price": 0.0, "change": 0.0, "pct": 0.0}

    return market_snap
    
# ==========================================
# NEW SECTION: HISTORICAL UNITIZATION ENGINE
# ==========================================

def get_trades_and_flows():
    """
    MOCK DATA GENERATOR. 
    TODO: Replace this with pd.read_csv('mexem_trades.csv') later.
    """
    # Mock Deposits: 10k start, 5k top-up
    cf_data = {
        'Date': ['2024-01-02', '2024-06-01'],
        'Type': ['Deposit', 'Deposit'],
        'Amount': [10000.0, 5000.0]
    }
    
    # Mock Trades: Tech stocks
    tr_data = {
        'Date': ['2024-01-03', '2024-01-03', '2024-01-03', '2024-06-02'],
        'Ticker': ['AAPL', 'MSFT', 'GOOGL', 'NVDA'],
        'Action': ['BUY', 'BUY', 'BUY', 'BUY'],
        'Quantity': [25, 15, 20, 5],
        'Price': [185.0, 370.0, 140.0, 1100.0] 
    }
    return pd.DataFrame(tr_data), pd.DataFrame(cf_data)

def generate_unitized_history():
    """Reconstructs the daily NAV history for the chart."""
    print("⏳ Starting History Reconstruction...")
    
    # A. Load Data
    trades_df, cash_flows_df = get_trades_and_flows()
    
    # B. Setup Timeframe
    start_date = "2024-01-01"
    end_date = datetime.now().date()
    dates = pd.date_range(start=start_date, end=end_date, freq='B')
    
    # C. Batch Download Prices
    all_tickers = trades_df['Ticker'].unique().tolist()
    if not all_tickers: return []
    
    print(f"   Fetching history for: {all_tickers}")
    try:
        raw_prices = yf.download(all_tickers, start=start_date, progress=False)['Close']
        
        # --- CRITICAL FIX IS HERE ---
        # 1. Reindex to match our loop 'dates' exactly (adds rows for Holidays)
        # 2. Forward Fill (ffill) copies Friday's price to the holiday Monday
        raw_prices = raw_prices.reindex(dates).ffill().bfill()
        # ----------------------------
        
    except Exception as e:
        print(f"   History Fetch Error: {e}")
        return []
    
    # D. Time Machine Loop
    portfolio = {} 
    cash = 0.0
    total_units = 0.0
    current_nav = 100.00 # Par Value
    
    history_records = []
    
    for day in dates:
        day_str = day.strftime('%Y-%m-%d')
        
        # 1. Process Deposits (Cash In -> Units Out)
        todays_flows = cash_flows_df[cash_flows_df['Date'] == day_str]
        for _, flow in todays_flows.iterrows():
            amt = flow['Amount']
            # Issue units at CURRENT NAV (protects existing holders)
            new_units = amt / current_nav if total_units > 0 else amt / 100.0
            if total_units == 0: current_nav = 100.0 
            
            total_units += new_units
            cash += amt
            
        # 2. Process Trades (Cash <-> Stock)
        todays_trades = trades_df[trades_df['Date'] == day_str]
        for _, trade in todays_trades.iterrows():
            t = trade['Ticker']
            q = trade['Quantity']
            p = trade['Price']
            
            if trade['Action'] == 'BUY':
                portfolio[t] = portfolio.get(t, 0) + q
                cash -= (q * p)
            elif trade['Action'] == 'SELL':
                portfolio[t] = portfolio.get(t, 0) - q
                cash += (q * p)

        # 3. Mark-to-Market (Calculate NAV)
        assets_val = 0.0
        for t, shares in portfolio.items():
            if shares > 0:
                try:
                    # Look up price (Now guaranteed to exist because of reindex)
                    if isinstance(raw_prices, pd.Series):
                        price = raw_prices.loc[day]
                    else:
                        price = raw_prices.loc[day, t]
                        
                    # Safety check for NaNs (e.g. bad ticker)
                    if pd.isna(price): price = 0.0
                    
                    assets_val += shares * price
                except:
                    pass 
        
        total_aum = assets_val + cash
        
        # Safety: If AUM drops to zero but we have shares, reuse yesterday's NAV
        # This prevents "flash crashes" if data is momentarily missing
        if total_aum <= 0 and sum(portfolio.values()) > 0 and history_records:
             current_nav = history_records[-1]['NAV']
             total_aum = history_records[-1]['AUM']
        elif total_units > 0:
            current_nav = total_aum / total_units
            
        history_records.append({
            "Date": day_str,
            "NAV": round(current_nav, 2),
            "AUM": round(total_aum, 2)
        })

    print(f"✅ History generated: {len(history_records)} days.")
    return history_records

# ==========================================

def save_json(data, filename):
    temp = filename + ".tmp"
    with open(temp, 'w') as f:
        json.dump(data, f)
    os.replace(temp, filename)
    print(f"💾 Saved {filename}")


def main():
    print("🚀 FULL STACK Data Loader Started...")
    
    # State variables for the "Once a Day" logic
    cached_events = [] 
    last_events_update = 0
    
    while True:
        loop_start = time.time()
        
        # 1. ALWAYS Fetch DB (Google Sheets)
        db_data = fetch_database_snapshot()
        
        if db_data:
            current_tickers = extract_tickers_from_snapshot(db_data)
            
            # 2. Earnings Events (Every 12 hours)
            time_since_last = time.time() - last_events_update
            if time_since_last > EVENTS_INTERVAL or not cached_events:
                cached_events = fetch_market_events_parallel(current_tickers)
                last_events_update = time.time()
            else:
                print(f"⏳ Skipping Earnings Fetch (Next update in {int((EVENTS_INTERVAL - time_since_last)/60)} min)")

            db_data["Market_Events"] = cached_events
            save_json(db_data, DB_FILE)
            
            # 3. ALWAYS Fetch Market Prices (Real-time)
            market_data = fetch_market_prices(current_tickers)
            if market_data:
                save_json(market_data, MARKET_FILE)
                
            # 4. ALWAYS Generate Historical Graph Data (NEW)
            try:
                history_data = generate_unitized_history()
                if history_data:
                    save_json(history_data, HISTORY_FILE)
            except Exception as e:
                print(f"⚠️ History Gen Failed: {e}")
            
        # Smart Sleep
        elapsed = time.time() - loop_start
        sleep_time = max(10, UPDATE_INTERVAL - elapsed)
        
        print(f"💤 Sleeping for {int(sleep_time)}s...\n" + "-"*40)
        time.sleep(sleep_time)

if __name__ == "__main__":
    main()
