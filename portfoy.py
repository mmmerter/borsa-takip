import streamlit as st
import yfinance as yf
import pandas as pd
import time
import gspread
import plotly.express as px
import plotly.graph_objects as go
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
from streamlit_option_menu import option_menu
from tefas import Crawler 
import feedparser
import requests
import re 

# --- SAYFA AYARLARI ---
st.set_page_config(
    page_title="Merter’in Terminali", 
    layout="wide", 
    page_icon="🏦",
    initial_sidebar_state="collapsed"
)

# --- CSS: TASARIM ---
st.markdown("""
<style>
    .block-container {padding-top: 1rem;}
    div[data-testid="stMetric"] {
        background-color: #262730;
        border: 1px solid #464b5f;
        border-radius: 10px;
        padding: 15px;
        color: #ffffff;
    }
    div[data-testid="stMetricValue"] { color: #ffffff !important; }
    div[data-testid="stMetricLabel"] { color: #d0d0d0 !important; }
    
    .ticker-container {
        width: 100%;
        overflow: hidden;
        background-color: #161616;
        border-bottom: 1px solid #333;
        margin-bottom: 20px;
        white-space: nowrap;
        position: relative;
    }
    
    .market-ticker { background-color: #0e1117; border-bottom: 1px solid #333; padding: 8px 0; }
    .portfolio-ticker { background-color: #1a1c24; border-bottom: 2px solid #FF4B4B; padding: 8px 0; margin-bottom: 20px; }

    .ticker-text {
        display: inline-block;
        white-space: nowrap;
        padding-left: 0;
        font-family: 'Courier New', Courier, monospace;
        font-size: 16px;
        font-weight: 900; 
        color: #00e676;
    }
    
    .animate-market { animation: ticker 65s linear infinite; color: #4da6ff; }
    .animate-portfolio { animation: ticker 55s linear infinite; color: #ffd700; }

    @keyframes ticker {
        0% { transform: translate3d(0, 0, 0); }
        100% { transform: translate3d(-50%, 0, 0); } 
    }

    .news-card {
        background-color: #1E1E1E;
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #FF4B4B;
        margin-bottom: 10px;
    }
    .news-title { font-size: 16px; font-weight: bold; color: #ffffff; text-decoration: none; }
    .news-meta { font-size: 12px; color: #888; margin-top: 5px; }
    a { text-decoration: none !important; }
    a:hover { text-decoration: underline !important; }
</style>
""", unsafe_allow_html=True)

# --- YARDIMCI FONKSİYONLAR ---
def get_yahoo_symbol(kod, pazar):
    kod = str(kod).upper()
    pazar = str(pazar)

    # --- ÖZEL MAP: BIST yeni kodlar için eski Yahoo sembolleri ---
    special_map = {
        "TRMET": "KOZAA.IS",  # KOZAA -> TRMET
        "TRALT": "KOZAL.IS",  # KOZAL -> TRALT
        "TRENJ": "IPEKE.IS",  # IPEKE -> TRENJ
    }
    if kod in special_map:
        return special_map[kod]

    # --- Normal eşleştirme ---
    if pazar == "FON":
        return kod 

    if "BIST" in pazar:
        return f"{kod}.IS" if not kod.endswith(".IS") else kod

    elif "KRIPTO" in pazar:
        return f"{kod}-USD" if not kod.endswith("-USD") else kod

    elif "EMTIA" in pazar:
        map_emtia = {
            "Altın ONS": "GC=F",
            "Gümüş ONS": "SI=F",
            "Petrol": "BZ=F",
            "Doğalgaz": "NG=F",
            "Bakır": "HG=F"
        }
        up_kod = kod.upper()
        for k, v in map_emtia.items():
            if k.upper() in up_kod:
                return v
        return kod

    return kod 

# --- ZIRHLI SAYI ÇEVİRİCİ (GELİŞMİŞ) ---
def smart_parse(val):
    """
    Kullanıcı girişlerinde (adet, maliyet, fiyat) hem TR hem EN formatlarını
    otomatik doğru float'a çeviren stabil sürüm.
    """
    if val is None:
        return 0.0

    text = str(val).strip()
    if text == "":
        return 0.0

    # Tamamen sayısal ise direkt dön
    if text.replace(".", "").replace(",", "").isdigit():
        # TR formatı (virgül ondalık)
        if "," in text and "." not in text:
            text = text.replace(",", ".")
        return float(text.replace(",", "").replace(" ", ""))

    # 1) Hem nokta hem virgül varsa (örn: 1.234,56 veya 1,234.56)
    if "." in text and "," in text:
        # Önce binlik ayırıcıyı kaldır
        if text.find(".") < text.find(","):
            # format: 1.234,56 → 1234.56
            text = text.replace(".", "").replace(",", ".")
        else:
            # format: 1,234.56 → 1234.56
            text = text.replace(",", "")
        try:
            return float(text)
        except:
            return 0.0

    # 2) Sadece virgül varsa → TR ondalık
    if "," in text and "." not in text:
        return float(text.replace(".", "").replace(",", "."))

    # 3) Sadece nokta varsa
    if "." in text:
        try:
            as_float = float(text)
            if as_float < 1000:
                return as_float
            else:
                # 1.234 → 1234
                return float(text.replace(".", ""))
        except:
            pass

    # fallback
    try:
        return float(text)
    except:
        return 0.0


# --- TEFAS FON VERİSİ (SON FİYAT) ---
@st.cache_data(ttl=14400) 
def get_tefas_data(fund_code):
    try:
        crawler = Crawler()
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
        result = crawler.fetch(start=start_date, end=end_date, name=fund_code, columns=["Price"])
        if not result.empty:
            result = result.sort_index()
            current_price = result["Price"].iloc[-1]
            prev_price = result["Price"].iloc[-2] if len(result) > 1 else current_price
            return current_price, prev_price
        return 0, 0
    except:
        return 0, 0

# --- TEFAS FON TARİHÇE (GRAFİK + RİSK İÇİN) ---
@st.cache_data(ttl=14400)
def get_tefas_history(fund_code, days=365):
    try:
        crawler = Crawler()
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        df = crawler.fetch(start=start_date, end=end_date, name=fund_code, columns=["Price"])
        if df is None or df.empty:
            return None
        df = df.sort_index()
        df = df[df["Price"] > 0]
        if df.empty:
            return None
        return df
    except:
        return None

def calc_fund_risk(fund_code, days=365):
    """
    TEFAS fiyat serisinden:
    - 1Y getiri
    - yıllık volatilite
    - maksimum düşüş (max drawdown)
    hesaplar.
    """
    hist = get_tefas_history(fund_code, days=days)
    if hist is None or hist.empty:
        return 0.0, 0.0, 0.0

    prices = pd.to_numeric(hist["Price"], errors="coerce").dropna()
    if prices.empty:
        return 0.0, 0.0, 0.0

    returns = prices.pct_change().dropna()
    if returns.empty:
        return 0.0, 0.0, 0.0

    total_return = (1 + returns).prod() - 1
    vol_annual = returns.std() * (252 ** 0.5)

    cum = (1 + returns).cumprod()
    running_max = cum.cummax()
    drawdown = cum / running_max - 1
    max_dd = drawdown.min() if not drawdown.empty else 0.0

    return float(total_return), float(vol_annual), float(max_dd)


# --- COINGECKO GLOBAL VERİ ---
@st.cache_data(ttl=300)
def get_crypto_globals():
    try:
        url = "https://api.coingecko.com/api/v3/global"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            d = response.json()['data']
            total_cap = d['total_market_cap']['usd']
            btc_d = d['market_cap_percentage']['btc']
            eth_d = d['market_cap_percentage']['eth']
            top2_share = btc_d + eth_d
            total_3_cap = total_cap * (1 - (top2_share / 100))
            others_d = 100 - top2_share
            others_cap = total_3_cap 
            return total_cap, btc_d, total_3_cap, others_d, others_cap
    except:
        pass
    return 0, 0, 0, 0, 0

# --- HABER AKIŞI ---
@st.cache_data(ttl=300)
def get_financial_news(topic="finance"):
    urls = {
        "BIST": "https://news.google.com/rss/search?q=Borsa+Istanbul+Hisseler&hl=tr&gl=TR&ceid=TR:tr",
        "KRIPTO": "https://news.google.com/rss/search?q=Kripto+Para+Bitcoin&hl=tr&gl=TR&ceid=TR:tr",
        "GLOBAL": "https://news.google.com/rss/search?q=ABD+Borsaları+Fed&hl=tr&gl=TR&ceid=TR:tr",
        "DOVIZ": "https://news.google.com/rss/search?q=Dolar+Altın+Piyasa&hl=tr&gl=TR&ceid=TR:tr"
    }
    url = urls.get(topic, urls["BIST"])
    feed = feedparser.parse(url)
    news_list = []
    for entry in feed.entries[:10]:
        news_list.append({"title": entry.title, "link": entry.link, "date": entry.published})
    return news_list

def render_news_section(category_name, rss_key):
    st.subheader(f"📰 {category_name}")
    news = get_financial_news(rss_key)
    for n in news:
        st.markdown(
            f"""<div class="news-card">
                    <a href="{n['link']}" target="_blank" class="news-title">{n['title']}</a>
                    <div class="news-meta">🕒 {n['date']}</div>
                </div>""",
            unsafe_allow_html=True
        )

# --- GOOGLE SHEETS VERİ ---
SHEET_NAME = "PortfoyData" 

def get_data_from_sheet():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        sheet = client.open(SHEET_NAME).sheet1
        data = sheet.get_all_records()
        if not data:
            return pd.DataFrame(columns=["Kod", "Pazar", "Adet", "Maliyet", "Tip", "Notlar"])
        df = pd.DataFrame(data)
        expected_cols = ["Kod", "Pazar", "Adet", "Maliyet", "Tip", "Notlar"]
        for col in expected_cols:
            if col not in df.columns:
                df[col] = "" 
        return df
    except:
        return pd.DataFrame(columns=["Kod", "Pazar", "Adet", "Maliyet", "Tip", "Notlar"])

def get_sales_history():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        sheet = client.open(SHEET_NAME).worksheet("Satislar") 
        data = sheet.get_all_records()
        if not data:
            return pd.DataFrame(columns=["Tarih", "Kod", "Pazar", "Satılan Adet", "Satış Fiyatı", "Maliyet", "Kâr/Zarar"])
        return pd.DataFrame(data)
    except:
        return pd.DataFrame(columns=["Tarih", "Kod", "Pazar", "Satılan Adet", "Satış Fiyatı", "Maliyet", "Kâr/Zarar"])

def add_sale_record(date, code, market, qty, price, cost, profit):
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        sheet = client.open(SHEET_NAME).worksheet("Satislar")
        row = [str(date), code, market, float(qty), float(price), float(cost), float(profit)]
        sheet.append_row(row)
    except Exception as e:
        st.error(f"Satış kaydedilemedi: {e}")

def save_data_to_sheet(df):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = st.secrets["gcp_service_account"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    sheet = client.open(SHEET_NAME).sheet1
    sheet.clear()
    sheet.update([df.columns.values.tolist()] + df.values.tolist())

# --- MARKET VE PORTFÖY ŞERİDİ ---
@st.cache_data(ttl=45) 
def get_tickers_data(df_portfolio, usd_try):
    total_cap, btc_d, total_3, others_d, others_cap = get_crypto_globals()
    
    market_symbols = [
        ("BIST 100", "XU100.IS"), ("USD", "TRY=X"), ("EUR", "EURTRY=X"),
        ("BTC/USDT", "BTC-USD"), ("ETH/USDT", "ETH-USD"),
        ("Ons Altın", "GC=F"), ("Ons Gümüş", "SI=F"),
        ("NASDAQ", "^IXIC"), ("S&P 500", "^GSPC")
    ]
    
    portfolio_symbols = {}
    if not df_portfolio.empty:
        assets = df_portfolio[df_portfolio["Tip"] == "Portfoy"]
        for _, row in assets.iterrows():
            kod = row['Kod']
            pazar = row['Pazar']
            if "Fiziki" not in pazar and "Gram" not in kod and pazar != "FON":
                sym = get_yahoo_symbol(kod, pazar)
                portfolio_symbols[kod] = sym

    all_fetch = list(set([s[1] for s in market_symbols] + list(portfolio_symbols.values()))
