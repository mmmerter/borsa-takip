import streamlit as st
import yfinance as yf
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
from tefas import Crawler
import feedparser
import requests
import re
import ccxt
from utils import smart_parse  # utils'den çağırdık

# --- SABİTLER ---
SHEET_NAME = "PortfoyData"
KNOWN_FUNDS = ["YHB", "TTE", "MAC", "AFT", "AFA", "YAY", "IPJ", "TCD", "NNF", 
               "GMR", "TI2", "TI3", "IHK", "IDH", "OJT", "HKH", "IPB", "KZL", "RPD"]

MARKET_DATA = {
    "BIST (Tümü)": ["THYAO", "GARAN", "ASELS", "TRMET"],
    "ABD": ["AAPL", "TSLA"],
    "KRIPTO": ["BTC", "ETH"],
    "FON": KNOWN_FUNDS,
    "EMTIA": ["Gram Altın", "Gram Gümüş"],
    "VADELI": ["BTC", "ETH", "SOL"],
    "NAKIT": ["TL", "USD", "EUR"],
}

# --- YARDIMCI ---
def get_yahoo_symbol(kod, pazar):
    kod = str(kod).upper()
    if kod == "TRMET": return "KOZAA.IS"
    if pazar == "NAKIT" or pazar == "FON": return kod
    if "BIST" in pazar: return f"{kod}.IS" if not kod.endswith(".IS") else kod
    elif "KRIPTO" in pazar: return f"{kod}-USD" if not kod.endswith("-USD") else kod
    elif "EMTIA" in pazar:
        map_emtia = {"Altın ONS": "GC=F", "Gümüş ONS": "SI=F", "Petrol": "BZ=F", 
                     "Doğalgaz": "NG=F", "Bakır": "HG=F"}
        for k, v in map_emtia.items():
            if k in kod: return v
        return kod
    return kod

# --- DATA FETCHING & CACHING ---

@st.cache_data(ttl=14400) # 4 SAAT CACHE (Fonlar geç güncellenir)
def get_tefas_data(fund_code):
    try:
        crawler = Crawler()
        end = datetime.now().strftime("%Y-%m-%d")
        start = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        res = crawler.fetch(start=start, end=end, name=fund_code, columns=["Price"])
        if not res.empty:
            res = res.sort_index()
            return float(res["Price"].iloc[-1]), float(res["Price"].iloc[-2])
    except: pass
    return 0, 0

@st.cache_data(ttl=300) # 5 DAKİKA CACHE
def get_crypto_globals():
    try:
        d = requests.get("https://api.coingecko.com/api/v3/global", timeout=5).json()["data"]
        total_cap = d["total_market_cap"]["usd"]
        btc_d = d["market_cap_percentage"]["btc"]
        eth_d = d["market_cap_percentage"]["eth"]
        top2 = btc_d + eth_d
        total3 = total_cap * (1 - (top2 / 100))
        others_d = 100 - top2
        return total_cap, btc_d, total3, others_d, total3
    except: return 0, 0, 0, 0, 0

@st.cache_data(ttl=600) # 10 DAKİKA CACHE (Haberler)
def get_financial_news(topic="finance"):
    urls = {
        "BIST": "https://news.google.com/rss/search?q=Borsa+Istanbul+Hisseler&hl=tr&gl=TR&ceid=TR:tr",
        "KRIPTO": "https://news.google.com/rss/search?q=Kripto+Para+Bitcoin&hl=tr&gl=TR&ceid=TR:tr",
        "GLOBAL": "https://news.google.com/rss/search?q=ABD+Borsaları+Fed&hl=tr&gl=TR&ceid=TR:tr",
        "DOVIZ": "https://news.google.com/rss/search?q=Dolar+Altın+Piyasa&hl=tr&gl=TR&ceid=TR:tr",
    }
    try:
        feed = feedparser.parse(urls.get(topic, urls["BIST"]))
        return [{"title": e.title, "link": e.link, "date": e.published} for e in feed.entries[:10]]
    except: return []

def get_data_from_sheet():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
        client = gspread.authorize(creds)
        sheet = client.open(SHEET_NAME).sheet1
        data = sheet.get_all_records()
        if not data: return pd.DataFrame(columns=["Kod", "Pazar", "Adet", "Maliyet", "Tip", "Notlar"])
        df = pd.DataFrame(data)
        for col in ["Kod", "Pazar", "Adet", "Maliyet", "Tip", "Notlar"]:
            if col not in df.columns: df[col] = ""
        return df
    except: return pd.DataFrame(columns=["Kod", "Pazar", "Adet", "Maliyet", "Tip", "Notlar"])

def save_data_to_sheet(df):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
    client = gspread.authorize(creds)
    sheet = client.open(SHEET_NAME).sheet1
    sheet.clear()
    sheet.update([df.columns.values.tolist()] + df.values.tolist())

@st.cache_data(ttl=300)
def get_usd_try():
    try: return yf.Ticker("TRY=X").history(period="1d")["Close"].iloc[-1]
    except: return 34.0

@st.cache_data(ttl=30) # 30 SANİYE CACHE (Canlı Ticker için Hızlandırıldı)
def get_tickers_data(df_portfolio_dict, usd_try): # DataFrame hashlenemez, dict olarak alacagiz
    # Not: Cache mekanizması dataframe'i parametre olarak sevmez, bu yüzden çağıran yerde df.to_dict() yapıp buraya yollayacağız.
    # Ancak basitlik olsun diye şimdilik cache'i kaldırıp st.cache_resource kullanabiliriz veya
    # buradaki mantığı sadeleştirebiliriz. Şimdilik 30sn TTL ile çalışır.
    
    # DataFrame'i geri oluştur
    df_portfolio = pd.DataFrame(df_portfolio_dict) if df_portfolio_dict else pd.DataFrame()
    
    total_cap, btc_d, total_3, others_d, others_cap = get_crypto_globals()
    market_symbols = [("BIST 100", "XU100.IS"), ("USD", "TRY=X"), ("EUR", "EURTRY=X"),
                      ("BTC/USDT", "BTC-USD"), ("Ons Altın", "GC=F"), ("NASDAQ", "^IXIC")]
    
    portfolio_symbols = {}
    if not df_portfolio.empty:
        assets = df_portfolio[df_portfolio["Tip"] == "Portfoy"]
        for _, row in assets.iterrows():
            if "NAKIT" not in row["Pazar"] and "FON" not in row["Pazar"]:
                portfolio_symbols[row["Kod"]] = get_yahoo_symbol(row["Kod"], row["Pazar"])

    all_fetch = list(set([s[1] for s in market_symbols] + list(portfolio_symbols.values())))
    market_html = '<span style="color:#aaa">🌍 PİYASA:</span> &nbsp;'
    portfolio_html = '<span style="color:#aaa">💼 PORTFÖY:</span> &nbsp;'

    try:
        yahoo_data = yf.Tickers(" ".join(all_fetch))
        
        def get_val(symbol, label=None):
            try:
                h = yahoo_data.tickers[symbol].history(period="2d")
                if h.empty: return ""
                p = h["Close"].iloc[-1]
                prev = h["Close"].iloc[-2]
                chg = ((p - prev) / prev) * 100
                col = "#00e676" if chg >= 0 else "#ff5252"
                arrow = "▲" if chg >= 0 else "▼"
                fmt = f"{p:,.2f}" if p > 1 else f"{p:,.4f}"
                if "XU100" in symbol: fmt = f"{p:,.0f}"
                return f'{label if label else symbol}: <span style="color:white">{fmt}</span> <span style="color:{col}">{arrow}%{chg:.2f}</span>'
            except: return ""

        for name, sym in market_symbols:
            val = get_val(sym, name)
            if val: market_html += f"{val} &nbsp;|&nbsp; "
            
        if portfolio_symbols:
            for name, sym in portfolio_symbols.items():
                val = get_val(sym, name)
                if val: portfolio_html += f"{val} &nbsp;&nbsp;&nbsp; "
    except: pass

    return (
        f'<div class="ticker-text animate-market">{market_html} &nbsp;&nbsp;&nbsp; {market_html}</div>',
        f'<div class="ticker-text animate-portfolio">{portfolio_html} &nbsp;&nbsp;&nbsp; {portfolio_html}</div>',
    )

# Binance Fonksiyonları
def get_binance_positions(api_key, api_secret):
    try:
        exchange = ccxt.binance({"apiKey": api_key, "secret": api_secret, "options": {"defaultType": "future"}})
        balance = exchange.fetch_balance()
        positions = exchange.fetch_positions()
        active_positions = []
        for pos in positions:
            if float(pos["info"]["positionAmt"]) != 0:
                active_positions.append({
                    "Sembol": pos["symbol"],
                    "Yön": "🟢 LONG" if float(pos["info"]["positionAmt"]) > 0 else "🔴 SHORT",
                    "PNL": float(pos["unrealizedPnl"])
                })
        return {"wallet": balance["total"]["USDT"]}, pd.DataFrame(active_positions)
    except Exception as e:
        return None, str(e)

def get_sales_history():
    # ... (Eski koddaki get_sales_history içeriği aynen buraya)
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
        client = gspread.authorize(creds)
        sheet = client.open(SHEET_NAME).worksheet("Satislar")
        data = sheet.get_all_records()
        return pd.DataFrame(data) if data else pd.DataFrame()
    except: return pd.DataFrame()

def add_sale_record(date, code, market, qty, price, cost, profit):
    # ... (Eski koddaki add_sale_record içeriği)
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
        client = gspread.authorize(creds)
        sheet = client.open(SHEET_NAME).worksheet("Satislar")
        sheet.append_row([str(date), code, market, float(qty), float(price), float(cost), float(profit)])
    except: pass
