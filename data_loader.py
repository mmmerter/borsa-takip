import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import requests
import feedparser
from tefas import Crawler
import yfinance as yf
import ccxt
import pandas as pd
import re
from utils import get_yahoo_symbol

SHEET_NAME = "PortfoyData"

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
        if not df.empty:
            df["Pazar"] = df["Pazar"].apply(lambda x: "FON" if "FON" in str(x) else x)
            df["Pazar"] = df["Pazar"].apply(lambda x: "EMTIA" if "FIZIKI" in str(x).upper() else x)
        return df
    except: return pd.DataFrame(columns=["Kod", "Pazar", "Adet", "Maliyet", "Tip", "Notlar"])

def save_data_to_sheet(df):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
    client = gspread.authorize(creds)
    sheet = client.open(SHEET_NAME).sheet1
    sheet.clear()
    sheet.update([df.columns.values.tolist()] + df.values.tolist())

def get_sales_history():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
        client = gspread.authorize(creds)
        sheet = client.open(SHEET_NAME).worksheet("Satislar")
        data = sheet.get_all_records()
        return pd.DataFrame(data) if data else pd.DataFrame(columns=["Tarih", "Kod", "Pazar", "Satılan Adet", "Satış Fiyatı", "Maliyet", "Kâr/Zarar"])
    except: return pd.DataFrame(columns=["Tarih", "Kod", "Pazar", "Satılan Adet", "Satış Fiyatı", "Maliyet", "Kâr/Zarar"])

def add_sale_record(date, code, market, qty, price, cost, profit):
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
        client = gspread.authorize(creds)
        sheet = client.open(SHEET_NAME).worksheet("Satislar")
        sheet.append_row([str(date), code, market, float(qty), float(price), float(cost), float(profit)])
    except: pass

@st.cache_data(ttl=14400)
def get_tefas_data(fund_code):
    try:
        url = f"https://www.tefas.gov.tr/FonAnaliz.aspx?FonKod={fund_code}"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=5)
        if r.status_code == 200:
            match = re.search(r'id="MainContent_PanelInfo_lblPrice">([\d,]+)', r.text)
            if match: return float(match.group(1).replace(",", ".")), float(match.group(1).replace(",", "."))
    except: pass
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

@st.cache_data(ttl=300)
def get_crypto_globals():
    try:
        d = requests.get("https://api.coingecko.com/api/v3/global", timeout=5).json()["data"]
        return d["total_market_cap"]["usd"], d["market_cap_percentage"]["btc"], d["total_market_cap"]["usd"] * (1 - ((d["market_cap_percentage"]["btc"] + d["market_cap_percentage"]["eth"]) / 100)), 100 - (d["market_cap_percentage"]["btc"] + d["market_cap_percentage"]["eth"]), 0
    except: return 0, 0, 0, 0, 0

@st.cache_data(ttl=300)
def get_usd_try():
    try: return yf.Ticker("TRY=X").history(period="1d")["Close"].iloc[-1]
    except: return 34.0

@st.cache_data(ttl=300)
def get_financial_news(topic="finance"):
    urls = {"BIST": "https://news.google.com/rss/search?q=Borsa+Istanbul+Hisseler&hl=tr&gl=TR&ceid=TR:tr",
            "KRIPTO": "https://news.google.com/rss/search?q=Kripto+Para+Bitcoin&hl=tr&gl=TR&ceid=TR:tr",
            "GLOBAL": "https://news.google.com/rss/search?q=ABD+Borsaları+Fed&hl=tr&gl=TR&ceid=TR:tr",
            "DOVIZ": "https://news.google.com/rss/search?q=Dolar+Altın+Piyasa&hl=tr&gl=TR&ceid=TR:tr"}
    try:
        feed = feedparser.parse(urls.get(topic, urls["BIST"]))
        return [{"title": e.title, "link": e.link, "date": e.published} for e in feed.entries[:10]]
    except: return []

@st.cache_data(ttl=45)
def get_tickers_data(df_portfolio, usd_try):
    total_cap, btc_d, total_3, others_d, others_cap = get_crypto_globals()
    market_symbols = [("BIST 100", "XU100.IS"), ("USD", "TRY=X"), ("EUR", "EURTRY=X"), ("BTC/USDT", "BTC-USD"),
                      ("ETH/USDT", "ETH-USD"), ("Ons Altın", "GC=F"), ("Ons Gümüş", "SI=F"), ("NASDAQ", "^IXIC"), ("S&P 500", "^GSPC")]
    portfolio_symbols = {}
    if not df_portfolio.empty:
        assets = df_portfolio[df_portfolio["Tip"] == "Portfoy"]
        for _, row in assets.iterrows():
            if "NAKIT" not in row["Pazar"] and "Gram" not in row["Kod"] and "FON" not in row["Pazar"]:
                portfolio_symbols[row["Kod"]] = get_yahoo_symbol(row["Kod"], row["Pazar"])
    
    all_fetch = list(set([s[1] for s in market_symbols] + list(portfolio_symbols.values())))
    market_html = '<span style="color:#aaa; font-size: 22px; font-weight: 900;">🌍 PİYASA:</span> &nbsp;'
    portfolio_html = '<span style="color:#aaa; font-size: 22px; font-weight: 900;">💼 PORTFÖY:</span> &nbsp;'

    try:
        yahoo_data = yf.Tickers(" ".join(all_fetch))
        def get_val(symbol, label=None):
            try:
                h = yahoo_data.tickers[symbol].history(period="2d")
                if not h.empty:
                    p, prev = h["Close"].iloc[-1], h["Close"].iloc[-2]
                    chg, col, arrow = ((p - prev) / prev) * 100, "#00e676" if p >= prev else "#ff5252", "▲" if p >= prev else "▼"
                    fmt = f"{p:,.2f}" if p > 1 else f"{p:,.4f}"
                    if "XU100" in symbol or "^" in symbol: fmt = f"{p:,.0f}"
                    return f'<span style="font-size: 22px; font-weight: 900; color: #bbbbff;">{label if label else symbol}: </span><span style="color:white; font-size: 22px; font-weight: 900;">{fmt}</span> <span style="color:{col}; font-size: 22px; font-weight: 900;">{arrow}%{chg:.2f}</span>'
            except: return ""
            return ""

        for name, sym in market_symbols:
            val = get_val(sym, name)
            if val: market_html += f"{val} &nbsp;|&nbsp; "
            if name == "ETH/USDT":
                try:
                    # 5d FIX
                    h = yahoo_data.tickers["GC=F"].history(period="5d")
                    if not h.empty: market_html += f'<span style="font-size: 22px; font-weight: 900; color: #bbbbff;">Gr Altın: </span><span style="color:white; font-size: 22px; font-weight: 900;">{(h["Close"].iloc[-1] * usd_try) / 31.1035:.2f}</span> &nbsp;|&nbsp; '
                except: pass
                try:
                    # 5d FIX
                    h = yahoo_data.tickers["SI=F"].history(period="5d")
                    if not h.empty: market_html += f'<span style="font-size: 22px; font-weight: 900; color: #bbbbff;">Gr Gümüş: </span><span style="color:white; font-size: 22px; font-weight: 900;">{(h["Close"].iloc[-1] * usd_try) / 31.1035:.2f}</span> &nbsp;|&nbsp; '
                except: pass

        if total_cap > 0:
            market_html += f'<span style="font-size: 22px; font-weight: 900; color: #bbbbff;">BTC.D: </span><span style="color:#f2a900; font-size: 22px; font-weight: 900;">% {btc_d:.2f}</span> &nbsp;|&nbsp; '
        
        if portfolio_symbols:
            for name, sym in portfolio_symbols.items():
                val = get_val(sym, name)
                if val: portfolio_html += f"{val} &nbsp;&nbsp;&nbsp; "
        else: portfolio_html += "Portföy boş."
    except: market_html, portfolio_html = "Yükleniyor...", "Yükleniyor..."
    
    return f'<div class="ticker-text animate-market">{market_html}</div>', f'<div class="ticker-text animate-portfolio">{portfolio_html}</div>'

def get_binance_pnl_stats(exchange):
    return 0,0,0,0 # Stub

def get_binance_positions(api_key, api_secret):
    try:
        exchange = ccxt.binance({"apiKey": api_key, "secret": api_secret, "options": {"defaultType": "future"}})
        balance = exchange.fetch_balance()
        positions = exchange.fetch_positions()
        active = []
        for pos in positions:
            if float(pos["info"]["positionAmt"]) != 0:
                active.append({"Sembol": pos["symbol"], "Yön": "🟢" if float(pos["info"]["positionAmt"]) > 0 else "🔴", "PNL": float(pos["unrealizedPnl"])})
        return {"wallet": balance["total"]["USDT"]}, pd.DataFrame(active)
    except Exception as e: return None, str(e)
