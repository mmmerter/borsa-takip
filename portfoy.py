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

    all_fetch = list(set([s[1] for s in market_symbols] + list(portfolio_symbols.values())))
    
    market_html = '<span style="color:#aaa">🌍 PİYASA:</span> &nbsp;'
    portfolio_html = '<span style="color:#aaa">💼 PORTFÖY:</span> &nbsp;'
    
    try:
        yahoo_data = yf.Tickers(" ".join(all_fetch))
        
        def get_val(symbol, label=None):
            try:
                h = yahoo_data.tickers[symbol].history(period="2d")
                if not h.empty:
                    p = h['Close'].iloc[-1]
                    prev = h['Close'].iloc[-2]
                    chg = ((p - prev) / prev) * 100
                    c, a = ("#00e676", "▲") if chg >= 0 else ("#ff5252", "▼")
                    fmt_p = f"{p:,.2f}" if p > 1 else f"{p:,.4f}"
                    if "XU100" in symbol or "^" in symbol:
                        fmt_p = f"{p:,.0f}"
                    return f'{label if label else symbol}: <span style="color:white">{fmt_p}</span> <span style="color:{c}">{a}%{chg:.2f}</span>'
            except:
                return ""
            return ""

        for name, sym in market_symbols:
            val = get_val(sym, name)
            if val:
                market_html += f'{val} &nbsp;|&nbsp; '
            
            if name == "ETH/USDT":
                try:
                    ons = yahoo_data.tickers["GC=F"].history(period="1d")['Close'].iloc[-1]
                    gr = (ons * usd_try) / 31.1035
                    market_html += f'Gr Altın: <span style="color:white">{gr:.2f}</span> &nbsp;|&nbsp; '
                except:
                    pass
                try:
                    ons = yahoo_data.tickers["SI=F"].history(period="1d")['Close'].iloc[-1]
                    gr = (ons * usd_try) / 31.1035
                    market_html += f'Gr Gümüş: <span style="color:white">{gr:.2f}</span> &nbsp;|&nbsp; '
                except:
                    pass

        if total_cap > 0:
            t3_tril = total_3 / 1_000_000_000_000 
            market_html += f'BTC.D: <span style="color:#f2a900">% {btc_d:.2f}</span> &nbsp;|&nbsp; '
            market_html += f'TOTAL: <span style="color:#00e676">${(total_cap/1_000_000_000_000):.2f}T</span> &nbsp;|&nbsp; '
            market_html += f'TOTAL 3: <span style="color:#627eea">${t3_tril:.2f}T</span> &nbsp;|&nbsp; '
            market_html += f'OTHERS.D: <span style="color:#627eea">% {others_d:.2f}</span> &nbsp;|&nbsp; '

        if portfolio_symbols:
            for name, sym in portfolio_symbols.items():
                val = get_val(sym, name)
                if val:
                    portfolio_html += f'{val} &nbsp;&nbsp;&nbsp; '
        else:
            portfolio_html += "Portföy boş veya veri çekilemiyor."

    except: 
        market_html = "Veri yükleniyor..."
        portfolio_html = "Veri yükleniyor..."
    
    final_market = f'<div class="ticker-text animate-market">{market_html} &nbsp;&nbsp;&nbsp; {market_html}</div>'
    final_portfolio = f'<div class="ticker-text animate-portfolio">{portfolio_html} &nbsp;&nbsp;&nbsp; {portfolio_html}</div>'
    return final_market, final_portfolio

portfoy_df = get_data_from_sheet()

# --- BAŞLIK ---
c_title, c_toggle = st.columns([3, 1])
with c_title:
    st.title("🏦 Merter'in Varlık Yönetim Terminali")
with c_toggle:
    st.write("") 
    GORUNUM_PB = st.radio("Para Birimi:", ["TRY", "USD"], horizontal=True)

@st.cache_data(ttl=300)
def get_usd_try():
    try:
        ticker = yf.Ticker("TRY=X")
        hist = ticker.history(period="1d")
        if not hist.empty:
            return hist['Close'].iloc[-1]
        return 34.0
    except:
        return 34.0

USD_TRY = get_usd_try()

# --- ÇİFT KAYAN ŞERİT GÖSTERİMİ ---
market_html, portfolio_html = get_tickers_data(portfoy_df, USD_TRY)

st.markdown(f"""
<div class="ticker-container market-ticker">
    {market_html}
</div>
<div class="ticker-container portfolio-ticker">
    {portfolio_html}
</div>
""", unsafe_allow_html=True)

# --- NAVİGASYON MENÜSÜ ---
selected = option_menu(
    menu_title=None, 
    options=["Dashboard", "Tümü", "BIST", "ABD", "FON", "Emtia", "Fiziki", "Kripto", "Haberler", "İzleme", "Satışlar", "Ekle/Çıkar"], 
    icons=["speedometer2", "list-task", "graph-up-arrow", "currency-dollar", "piggy-bank", "fuel-pump", "house", "currency-bitcoin", "newspaper", "eye", "receipt", "gear"], 
    menu_icon="cast", 
    default_index=0, 
    orientation="horizontal",
    styles={
        "container": {"padding": "0!important", "background-color": "#161616"}, 
        "icon": {"color": "white", "font-size": "18px"}, 
        "nav-link": {
            "font-size": "14px", 
            "text-align": "center", 
            "margin":"0px", 
            "--hover-color": "#333333", 
            "font-weight": "bold", 
            "color": "#bfbfbf"
        },
        "nav-link-selected": {"background-color": "#ffffff", "color": "#000000"}, 
    }
)

ANALYSIS_COLS = ["Kod", "Pazar", "Tip", "Adet", "Maliyet", "Fiyat", "PB", "Değer", "Top. Kâr/Zarar", "Top. %", "Gün. Kâr/Zarar", "Notlar"]

# --- VARLIK LİSTESİ ---
MARKET_DATA = {
    "BIST (Tümü)": [
        "THYAO", "GARAN", "ASELS", "EREGL", "SISE", "BIMAS", "AKBNK", "YKBNK",
        "KCHOL", "SAHOL", "TUPRS", "FROTO", "TOASO", "PGSUS", "TCELL", "PETKM",
        "HEKTS", "SASA", "ASTOR", "KONTR", "MEGMT", "REEDR", "TABGD", "A1CAP", "ACSEL"
    ], 
    "ABD (S&P + NASDAQ)": ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META"], 
    "KRIPTO": ["BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "AVAX"],
    "FON (TEFAS/BES)": [
        "TTE", "MAC", "AFT", "AFA", "YAY", "IPJ", "TCD", "NNF",
        "GMR", "TI2", "TI3", "IHK", "IDH",
        "YHB", "GGK", "URA", "OTJ", "RUT"
    ],
    "EMTIA": ["Gram Altın (TL)", "Gram Gümüş (TL)", "Altın ONS", "Gümüş ONS", "Petrol", "Doğalgaz"],
    "FIZIKI VARLIKLAR": ["Gram Altın (Fiziki)", "Çeyrek Altın", "Yarım Altın", "Tam Altın", "Dolar (Nakit)"]
}

# Fon kategorileri
FON_CATEGORY_MAP = {
    "TTE": "Altın Fon",
    "MAC": "Altın Fon",
    "AFT": "Karma Fon",
    "AFA": "Karma Fon",
    "YAY": "Hisse Fon",
    "IPJ": "Hisse Fon",
    "TCD": "Karma Fon",
    "NNF": "Döviz Fon",
    "GMR": "Kira Sertifikası Fon",
    "TI2": "Endeks Fon",
    "TI3": "Endeks Fon",
    "IHK": "Hisse Fon",
    "IDH": "Hisse Fon",
    "YHB": "Altın Fon",
    "GGK": "Altın Fon",
    "URA": "Yabancı Hisse Fon",
    "OTJ": "Yabancı Hisse Fon",
    "RUT": "Yabancı Hisse Fon"
}

# --- DETAYLI ANALİZ ---
def render_detail_view(symbol, pazar):
    st.markdown(f"### 🔎 {symbol} Detaylı Analizi")
    
    if pazar == "FON":
        # Son fiyat + değişim
        price, prev = get_tefas_data(symbol)
        delta = price - prev
        delta_pct = (delta / prev * 100) if prev not in [0, None] else 0
        st.metric(f"{symbol} Son Fiyat", f"₺{price:,.6f}", delta=f"{delta_pct:.2f}%")

        # Tarihsel grafik + risk
        hist = get_tefas_history(symbol, days=365)
        if hist is not None and not hist.empty:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=hist.index,
                y=hist["Price"],
                mode="lines",
                name=symbol
            ))
            fig.update_layout(
                title=f"{symbol} - Son 1 Yıl Fiyat Grafiği (TEFAS)",
                yaxis_title="Fiyat (TL)",
                xaxis_title="Tarih",
                template="plotly_dark",
                height=500
            )
            st.plotly_chart(fig, use_container_width=True)

            total_ret, vol_annual, max_dd = calc_fund_risk(symbol, days=365)
            c1, c2, c3 = st.columns(3)
            c1.metric("1Y Toplam Getiri", f"{total_ret*100:.2f}%")
            c2.metric("Yıllık Volatilite", f"{vol_annual*100:.2f}%")
            c3.metric("Maksimum Düşüş", f"{max_dd*100:.2f}%")
        else:
            st.info("Bu fon için yeterli TEFAS tarihsel veri bulunamadı.")
        return

    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="2y")
        
        if not hist.empty:
            fig = go.Figure(data=[go.Candlestick(
                x=hist.index,
                open=hist['Open'],
                high=hist['High'],
                low=hist['Low'],
                close=hist['Close'],
                name=symbol
            )])
            fig.update_layout(
                title=f'{symbol} Fiyat Grafiği',
                yaxis_title='Fiyat',
                template="plotly_dark",
                height=600,
                xaxis=dict(
                    rangeselector=dict(
                        buttons=list([
                            dict(count=1, label="1A", step="month", stepmode="backward"),
                            dict(count=3, label="3A", step="month", stepmode="backward"),
                            dict(count=6, label="6A", step="month", stepmode="backward"),
                            dict(count=1, label="YTD", step="year", stepmode="todate"),
                            dict(count=1, label="1Y", step="year", stepmode="backward"),
                            dict(step="all", label="TÜMÜ")
                        ]),
                        bgcolor="#262730",
                        font=dict(color="white")
                    ),
                    rangeslider=dict(visible=False),
                    type="date"
                )
            )
            st.plotly_chart(fig, use_container_width=True)
            
            info = ticker.info
            market_cap = info.get('marketCap', 'N/A')
            if isinstance(market_cap, int):
                market_cap = f"{market_cap:,.0f}"
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Sektör", info.get('sector', '-'))
            c2.metric("F/K", info.get('trailingPE', '-'))
            c3.metric("Piyasa Değeri", market_cap)
            c4.metric("52H Yüksek", info.get('fiftyTwoWeekHigh', '-'))
            c5.metric("52H Düşük", info.get('fiftyTwoWeekLow', '-'))
        else:
            st.warning("Grafik verisi bulunamadı.")
    except Exception as e:
        st.error(f"Veri çekilemedi: {e}")

# --- HESAPLAMA MOTORU (DÜZELTİLDİ) ---
def run_analysis(df, usd_try_rate, view_currency):
    results = []
    if df.empty:
        return pd.DataFrame(columns=ANALYSIS_COLS)
    for i, row in df.iterrows():
        kod = row.get("Kod", "")
        pazar = row.get("Pazar", "")
        
        adet = smart_parse(row.get("Adet", 0))
        maliyet = smart_parse(row.get("Maliyet", 0))
        
        if not kod:
            continue 
        symbol = get_yahoo_symbol(kod, pazar)
        asset_currency = "USD"
        if "BIST" in pazar or "TL" in kod or "Fiziki" in pazar or pazar == "FON":
            asset_currency = "TRY"
        
        curr_price = 0
        prev_close = 0
        
        try:
            if pazar == "FON":
                curr_price, prev_close = get_tefas_data(kod)
            elif "Gram Altın (TL)" in kod:
                hist = yf.Ticker("GC=F").history(period="2d")
                if len(hist) > 1:
                    curr_price = (hist['Close'].iloc[-1] * usd_try_rate) / 31.1035
                    prev_close = (hist['Close'].iloc[-2] * usd_try_rate) / 31.1035
                else:
                    curr_price = maliyet
                    prev_close = maliyet
            elif "Fiziki" in pazar: 
                curr_price = maliyet
                prev_close = maliyet
            else:
                hist = yf.Ticker(symbol).history(period="2d")
                if not hist.empty:
                    curr_price = hist['Close'].iloc[-1]
                    prev_close = hist['Close'].iloc[0] 
                else: 
                    curr_price = maliyet
                    prev_close = maliyet
        except:
            curr_price = maliyet
       


::contentReference[oaicite:0]{index=0}
