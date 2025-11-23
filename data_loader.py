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
# ==========================================================
#   KRAL ULTRA - Portföy Tarihsel Log & KPI Yardımcıları
#   (charts.py içindeki import'ları karşılamak için)
# ==========================================================

def _get_history_sheet():
    """Portföy tarihçe sheet'ine erişim helper'ı."""
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
        client = gspread.authorize(creds)
        # Ana sheet ile aynı dosyada "portfolio_history" isimli sayfa:
        sheet = client.open(SHEET_NAME).worksheet("portfolio_history")
        return sheet
    except Exception:
        return None


def read_portfolio_history():
    """
    Google Sheet -> 'portfolio_history' tablosunu okur.
    Beklenen kolonlar: Tarih, Değer_TRY, Değer_USD
    """
    sheet = _get_history_sheet()
    if sheet is None:
        return pd.DataFrame(columns=["Tarih", "Değer_TRY", "Değer_USD"])

    try:
        data = sheet.get_all_records()
        if not data:
            return pd.DataFrame(columns=["Tarih", "Değer_TRY", "Değer_USD"])
        df = pd.DataFrame(data)
        if "Tarih" in df.columns:
            df["Tarih"] = pd.to_datetime(df["Tarih"])
        else:
            df["Tarih"] = pd.to_datetime(datetime.now().strftime("%Y-%m-%d"))
        if "Değer_TRY" not in df.columns:
            df["Değer_TRY"] = 0.0
        if "Değer_USD" not in df.columns:
            df["Değer_USD"] = 0.0
        return df.sort_values("Tarih")
    except Exception:
        return pd.DataFrame(columns=["Tarih", "Değer_TRY", "Değer_USD"])


def write_portfolio_history(value_try, value_usd):
    """
    Bugünün tarihine karşılık portföy toplamını (TRY / USD) ekler.
    Aynı güne ikinci kez yazmaya kalkarsak, bırakıyoruz (charts/portföy kodu genelde önce kontrol ediyor).
    """
    sheet = _get_history_sheet()
    if sheet is None:
        return

    today_str = datetime.now().strftime("%Y-%m-%d")
    try:
        # Var olan kayıtları al, aynı gün varsa ekleme
        data = sheet.get_all_records()
        for row in data:
            if str(row.get("Tarih", ""))[:10] == today_str:
                return  # Bugün zaten kaydedilmiş

        new_row = [today_str, float(value_try), float(value_usd)]
        sheet.append_row(new_row)
    except Exception:
        # Sessiz geç, uygulamayı kilitlemesin
        pass


def get_timeframe_changes(history_df):
    """
    Haftalık / Aylık / YTD gerçek K/Z hesaplar.
    history_df: read_portfolio_history() çıktısı
    Dönüş:
      {
        "weekly": (değer, yüzde),
        "monthly": (değer, yüzde),
        "ytd": (değer, yüzde),
        "spark_week": [seri],
        "spark_month": [seri],
        "spark_ytd": [seri],
      }
    """
    if history_df is None or history_df.empty:
        return None

    # Tarih kolonu garanti olsun
    if "Tarih" not in history_df.columns:
        return None
    df = history_df.copy().sort_values("Tarih")
    df["Tarih"] = pd.to_datetime(df["Tarih"])

    # Ana seri: TRY bazlı toplam
    if "Değer_TRY" not in df.columns:
        return None

    today_val = float(df["Değer_TRY"].iloc[-1])
    dates = df["Tarih"]

    def _calc_period(days: int):
        target_date = dates.max() - timedelta(days=days)
        sub = df[df["Tarih"] >= target_date]
        if sub.empty:
            return 0.0, 0.0, []
        start_val = float(sub["Değer_TRY"].iloc[0])
        diff = today_val - start_val
        pct = (diff / start_val * 100) if start_val > 0 else 0.0
        spark = list(sub["Değer_TRY"])
        return diff, pct, spark

    # 7 gün (haftalık)
    w_val, w_pct, w_spark = _calc_period(7)

    # 30 gün (aylık)
    m_val, m_pct, m_spark = _calc_period(30)

    # YTD: yılın ilk kaydından bugüne
    year_mask = df["Tarih"].dt.year == datetime.now().year
    if year_mask.any():
        ydf = df[year_mask]
        start_val = float(ydf["Değer_TRY"].iloc[0])
        diff = today_val - start_val
        pct = (diff / start_val * 100) if start_val > 0 else 0.0
        y_spark = list(ydf["Değer_TRY"])
        y_val, y_pct = diff, pct
    else:
        y_val, y_pct, y_spark = 0.0, 0.0, []

    return {
        "weekly": (w_val, w_pct),
        "monthly": (m_val, m_pct),
        "ytd": (y_val, y_pct),
        "spark_week": w_spark,
        "spark_month": m_spark,
        "spark_ytd": y_spark,
    }
# ==========================================================
#   Pazar Bazlı Tarihsel Log (BIST / ABD / FON / EMTIA / NAKIT)
#   Sheet isimleri:
#   history_bist, history_abd, history_fon, history_emtia, history_nakit
# ==========================================================

def _get_market_history_sheet(ws_name: str):
    """Belirli bir pazar için sheet'e erişim helper'ı."""
    try:
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(
            st.secrets["gcp_service_account"], scope
        )
        client = gspread.authorize(creds)
        sheet = client.open(SHEET_NAME).worksheet(ws_name)
        return sheet
    except Exception:
        return None


def _read_market_history(ws_name: str):
    sheet = _get_market_history_sheet(ws_name)
    if sheet is None:
        return pd.DataFrame(columns=["Tarih", "Değer_TRY", "Değer_USD"])

    try:
        data = sheet.get_all_records()
        if not data:
            return pd.DataFrame(columns=["Tarih", "Değer_TRY", "Değer_USD"])
        df = pd.DataFrame(data)
        if "Tarih" in df.columns:
            df["Tarih"] = pd.to_datetime(df["Tarih"])
        else:
            df["Tarih"] = pd.to_datetime(datetime.now().strftime("%Y-%m-%d"))
        if "Değer_TRY" not in df.columns:
            df["Değer_TRY"] = 0.0
        if "Değer_USD" not in df.columns:
            df["Değer_USD"] = 0.0
        return df.sort_values("Tarih")
    except Exception:
        return pd.DataFrame(columns=["Tarih", "Değer_TRY", "Değer_USD"])


def _write_market_history(ws_name: str, value_try: float, value_usd: float):
    sheet = _get_market_history_sheet(ws_name)
    if sheet is None:
        return

    today_str = datetime.now().strftime("%Y-%m-%d")
    try:
        data = sheet.get_all_records()
        for row in data:
            if str(row.get("Tarih", ""))[:10] == today_str:
                # Bugünün kaydı zaten varsa tekrar ekleme
                return
        new_row = [today_str, float(value_try), float(value_usd)]
        sheet.append_row(new_row)
    except Exception:
        # Hata olursa sessiz geç; uygulamayı kilitlemesin
        pass


# --- Pazar bazlı public helper'lar ---

def read_history_bist():
    return _read_market_history("history_bist")


def write_history_bist(value_try, value_usd):
    _write_market_history("history_bist", value_try, value_usd)


def read_history_abd():
    return _read_market_history("history_abd")


def write_history_abd(value_try, value_usd):
    _write_market_history("history_abd", value_try, value_usd)


def read_history_fon():
    return _read_market_history("history_fon")


def write_history_fon(value_try, value_usd):
    _write_market_history("history_fon", value_try, value_usd)


def read_history_emtia():
    return _read_market_history("history_emtia")


def write_history_emtia(value_try, value_usd):
    _write_market_history("history_emtia", value_try, value_usd)


def read_history_nakit():
    return _read_market_history("history_nakit")


def write_history_nakit(value_try, value_usd):
    _write_market_history("history_nakit", value_try, value_usd)
