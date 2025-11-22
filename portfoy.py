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

# --- SAYFA AYARLARI ---
st.set_page_config(
    page_title="Merter’in Terminali", 
    layout="wide", 
    page_icon="🏦",
    initial_sidebar_state="collapsed"
)

# --- CSS: TASARIM (ÇİFT ŞERİT) ---
st.markdown("""
<style>
    .block-container {padding-top: 1rem;}
    
    /* Metrik Kutuları */
    div[data-testid="stMetric"] {
        background-color: #262730;
        border: 1px solid #464b5f;
        border-radius: 10px;
        padding: 15px;
        color: #ffffff;
    }
    div[data-testid="stMetricValue"] { color: #ffffff !important; }
    div[data-testid="stMetricLabel"] { color: #d0d0d0 !important; }
    
    /* Ticker Tape Genel Ayarlar */
    .ticker-container {
        width: 100%;
        overflow: hidden;
        white-space: nowrap;
        position: relative;
    }
    
    /* Üst Şerit (Piyasa) */
    .market-ticker {
        background-color: #0e1117; /* Daha koyu */
        border-bottom: 1px solid #333;
        padding: 8px 0;
    }
    
    /* Alt Şerit (Portföy) */
    .portfolio-ticker {
        background-color: #161616; /* Hafif açık */
        border-bottom: 1px solid #FF4B4B; /* Portföyü ayıran ince kırmızı çizgi */
        padding: 8px 0;
        margin-bottom: 20px;
    }

    .ticker-text {
        display: inline-block;
        white-space: nowrap;
        padding-left: 0;
        font-family: 'Courier New', Courier, monospace;
        font-size: 16px;
        font-weight: bold;
    }
    
    /* Animasyonlar (Farklı hızlar verilebilir) */
    .animate-market { animation: ticker 65s linear infinite; color: #4da6ff; }
    .animate-portfolio { animation: ticker 55s linear infinite; color: #ffd700; }

    @keyframes ticker {
        0% { transform: translate3d(0, 0, 0); }
        100% { transform: translate3d(-50%, 0, 0); } 
    }

    /* Haber Kartları */
    .news-card {
        background-color: #1E1E1E;
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #FF4B4B;
        margin-bottom: 10px;
    }
    .news-title {
        font-size: 16px;
        font-weight: bold;
        color: #ffffff;
        text-decoration: none;
    }
    .news-meta {
        font-size: 12px;
        color: #888;
        margin-top: 5px;
    }
    a { text-decoration: none !important; }
    a:hover { text-decoration: underline !important; }
</style>
""", unsafe_allow_html=True)

# --- YARDIMCI FONKSİYONLAR ---
def get_yahoo_symbol(kod, pazar):
    if pazar == "FON": return kod 
    if "BIST" in pazar: return f"{kod}.IS" if not kod.endswith(".IS") else kod
    elif "KRIPTO" in pazar: return f"{kod}-USD" if not kod.endswith("-USD") else kod
    elif "EMTIA" in pazar:
        map_emtia = {"Altın ONS": "GC=F", "Gümüş ONS": "SI=F", "Petrol": "BZ=F", "Doğalgaz": "NG=F", "Bakır": "HG=F"}
        for k, v in map_emtia.items():
            if k in kod: return v
        return kod
    return kod 

# --- TEFAS FON VERİSİ ---
@st.cache_data(ttl=14400) 
def get_tefas_data(fund_code):
    try:
        crawler = Crawler()
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
        result = crawler.fetch(start=start_date, end=end_date, name=fund_code, columns=["Price"])
        if not result.empty:
            current_price = result["Price"].iloc[0]
            prev_price = result["Price"].iloc[1] if len(result) > 1 else current_price
            return current_price, prev_price
        return 0, 0
    except: return 0, 0

# --- COINGECKO GLOBAL VERİ (TOTAL 3 EKLENDİ) ---
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
            
            # TOTAL 3 HESABI (Total - (BTC + ETH))
            # CoinGecko doğrudan Total3 vermez, biz hesaplarız:
            # Toplam - (Toplam * (BTC% + ETH%) / 100)
            top_2_share = btc_d + eth_d
            total_3 = total_cap * (1 - (top_2_share / 100))
            
            # Others (Genel Altcoin)
            others_d = 100 - top_2_share
            
            return total_cap, btc_d, total_3, others_d
    except:
        pass
    return 0, 0, 0, 0

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
        st.markdown(f"""<div class="news-card"><a href="{n['link']}" target="_blank" class="news-title">{n['title']}</a><div class="news-meta">🕒 {n['date']}</div></div>""", unsafe_allow_html=True)

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
        if not data: return pd.DataFrame(columns=["Kod", "Pazar", "Adet", "Maliyet", "Tip", "Notlar"])
        df = pd.DataFrame(data)
        expected_cols = ["Kod", "Pazar", "Adet", "Maliyet", "Tip", "Notlar"]
        for col in expected_cols:
            if col not in df.columns: df[col] = "" 
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
        if not data: return pd.DataFrame(columns=["Tarih", "Kod", "Pazar", "Satılan Adet", "Satış Fiyatı", "Maliyet", "Kâr/Zarar"])
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

# --- MARKET VE PORTFÖY ŞERİTLERİ (AYRI FONKSİYONLAR) ---
@st.cache_data(ttl=45) 
def get_tickers_data(df_portfolio, usd_try):
    # --- 1. ÜST ŞERİT (PİYASA) ---
    total_cap, btc_d, total_3, others_d = get_crypto_globals()
    
    market_symbols = [
        ("BIST 100", "XU100.IS"), ("USD", "TRY=X"), ("EUR", "EURTRY=X"),
        ("BTC/USDT", "BTC-USD"), ("ETH/USDT", "ETH-USD"),
        ("Ons Altın", "GC=F"), ("Ons Gümüş", "SI=F"),
        ("NASDAQ", "^IXIC"), ("S&P 500", "^GSPC")
    ]
    
    # Portföy Sembolleri
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
        
        # YARDIMCI: Veri Formatla
        def get_val(symbol):
            try:
                h = yahoo_data.tickers[symbol].history(period="2d")
                if not h.empty:
                    p = h['Close'].iloc[-1]
                    prev = h['Close'].iloc[-2]
                    chg = ((p - prev) / prev) * 100
                    c, a = ("#00e676", "▲") if chg >= 0 else ("#ff5252", "▼")
                    fmt_p = f"{p:,.2f}" if p > 1 else f"{p:,.4f}"
                    if "XU100" in symbol or "^" in symbol: fmt_p = f"{p:,.0f}"
                    return f'<span style="color:white">{fmt_p}</span> <span style="color:{c}">{a}%{chg:.2f}</span>'
            except: return ""
            return ""

        # --- PİYASA ŞERİDİ OLUŞTUR ---
        for name, sym in market_symbols:
            val = get_val(sym)
            if val: market_html += f'{name}: {val} &nbsp;|&nbsp; '
            
            # Araya Gramları Sıkıştır
            if name == "ETH/USDT":
                try:
                    ons = yahoo_data.tickers["GC=F"].history(period="1d")['Close'].iloc[-1]
                    gr = (ons * usd_try) / 31.1035
                    market_html += f'Gr Altın: <span style="color:white">{gr:.2f}</span> &nbsp;|&nbsp; '
                except: pass
                try:
                    ons = yahoo_data.tickers["SI=F"].history(period="1d")['Close'].iloc[-1]
                    gr = (ons * usd_try) / 31.1035
                    market_html += f'Gr Gümüş: <span style="color:white">{gr:.2f}</span> &nbsp;|&nbsp; '
                except: pass

        # Kripto Global Verileri (Sona Ekle)
        if total_cap > 0:
            t3_tril = total_3 / 1_000_000_000_000
            market_html += f'BTC.D: <span style="color:#f2a900">% {btc_d:.2f}</span> &nbsp;|&nbsp; '
            market_html += f'TOTAL 3: <span style="color:#627eea">${t3_tril:.2f}T</span> &nbsp;|&nbsp; '
            market_html += f'OTHERS.D: <span style="color:#627eea">% {others_d:.2f}</span> &nbsp;|&nbsp; '

        # --- PORTFÖY ŞERİDİ OLUŞTUR ---
        if portfolio_symbols:
            for name, sym in portfolio_symbols.items():
                val = get_val(sym)
                if val: portfolio_html += f'{name}: {val} &nbsp;&nbsp;&nbsp; '
        else:
            portfolio_html += "Portföy boş veya veri çekilemiyor."

    except: 
        market_html = "Veri yükleniyor..."
        portfolio_html = "Veri yükleniyor..."
    
    # Sonsuz Döngü İçin Çiftleme
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
        if not hist.empty: return hist['Close'].iloc[-1]
        return 34.0
    except: return 34.0

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
    "BIST (Tümü)": ["THYAO", "GARAN", "ASELS", "EREGL", "SISE", "BIMAS", "AKBNK", "YKBNK", "KCHOL", "SAHOL", "TUPRS", "FROTO", "TOASO", "PGSUS", "TCELL", "PETKM", "HEKTS", "SASA", "ASTOR", "KONTR", "MEGMT", "REEDR", "TABGD", "A1CAP", "ACSEL"], 
    "ABD (S&P + NASDAQ)": ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META"], 
    "KRIPTO": ["BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "AVAX"],
    "FON (TEFAS/BES)": ["TTE", "MAC", "AFT", "AFA", "YAY", "IPJ", "TCD", "NNF", "GMR", "TI2", "TI3", "IHK", "IDH"],
    "EMTIA": ["Gram Altın (TL)", "Gram Gümüş (TL)", "Altın ONS", "Gümüş ONS", "Petrol", "Doğalgaz"],
    "FIZIKI VARLIKLAR": ["Gram Altın (Fiziki)", "Çeyrek Altın", "Yarım Altın", "Tam Altın", "Dolar (Nakit)"]
}

# --- DETAYLI ANALİZ ---
def render_detail_view(symbol, pazar):
    st.markdown(f"### 🔎 {symbol} Detaylı Analizi")
    
    if pazar == "FON":
        price, _ = get_tefas_data(symbol)
        st.metric(f"{symbol} Son Fiyat", f"₺{price:,.6f}")
        st.info("Yatırım fonları için anlık grafik desteği TEFAS kaynaklı sınırlıdır.")
        return

    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="2y")
        
        if not hist.empty:
            fig = go.Figure(data=[go.Candlestick(x=hist.index,
                            open=hist['Open'], high=hist['High'],
                            low=hist['Low'], close=hist['Close'],
                            name=symbol)])
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
            if isinstance(market_cap, int): market_cap = f"{market_cap:,.0f}"
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

def run_analysis(df, usd_try_rate, view_currency):
    results = []
    if df.empty: return pd.DataFrame(columns=ANALYSIS_COLS)
    for i, row in df.iterrows():
        kod = row.get("Kod", "")
        pazar = row.get("Pazar", "")
        adet = float(row.get("Adet", 0))
        maliyet = float(row.get("Maliyet", 0))
        if not kod: continue 
        symbol = get_yahoo_symbol(kod, pazar)
        asset_currency = "USD"
        if "BIST" in pazar or "TL" in kod or "Fiziki" in pazar or pazar == "FON": asset_currency = "TRY"
        
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
                else: curr_price = maliyet
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
            prev_close = maliyet

        val_native = curr_price * adet
        cost_native = maliyet * adet
        
        daily_chg_native = (curr_price - prev_close) * adet

        if view_currency == "TRY":
            if asset_currency == "USD":
                fiyat_goster = curr_price * usd_try_rate
                val_goster = val_native * usd_try_rate
                cost_goster = cost_native * usd_try_rate
                daily_chg = daily_chg_native * usd_try_rate
            else: 
                fiyat_goster = curr_price
                val_goster = val_native
                cost_goster = cost_native
                daily_chg = daily_chg_native
        elif view_currency == "USD":
            if asset_currency == "TRY":
                fiyat_goster = curr_price / usd_try_rate
                val_goster = val_native / usd_try_rate
                cost_goster = cost_native / usd_try_rate
                daily_chg = daily_chg_native / usd_try_rate
            else: 
                fiyat_goster = curr_price
                val_goster = val_native
                cost_goster = cost_native
                daily_chg = daily_chg_native
        
        pnl = val_goster - cost_goster
        pnl_pct = (pnl / cost_goster * 100) if cost_goster > 0 else 0
        
        results.append({
            "Kod": kod, "Pazar": pazar, "Tip": row["Tip"],
            "Adet": adet, "Maliyet": maliyet,
            "Fiyat": fiyat_goster, "PB": view_currency,
            "Değer": val_goster, "Top. Kâr/Zarar": pnl, "Top. %": pnl_pct,
            "Gün. Kâr/Zarar": daily_chg, "Notlar": row.get("Notlar", "")
        })
    return pd.DataFrame(results)

@st.cache_data(ttl=3600)
def get_historical_chart(df, usd_try):
    if df.empty: return None
    tickers_map = {}
    for idx, row in df.iterrows():
        kod = row['Kod']
        pazar = row['Pazar']
        sym = get_yahoo_symbol(kod, pazar)
        if "Gram" not in kod and "Fiziki" not in pazar and pazar != "FON":
            tickers_map[sym] = {"Adet": float(row['Adet']), "Pazar": pazar}
    if not tickers_map: return None
    try:
        data = yf.download(list(tickers_map.keys()), period="6mo")['Close']
    except: return None
    if data.empty: return None
    data = data.ffill()
    portfolio_history = pd.Series(0, index=data.index)
    if isinstance(data, pd.Series): data = data.to_frame(name=list(tickers_map.keys())[0])
    for col in data.columns:
        if col in tickers_map:
            adet = tickers_map[col]["Adet"]
            pazar = tickers_map[col]["Pazar"]
            price_series = data[col]
            if "KRIPTO" in pazar or "ABD" in pazar: portfolio_history += (price_series * adet * usd_try)
            else: portfolio_history += (price_series * adet)
    return portfolio_history

def highlight_pnl(val):
    if isinstance(val, (int, float)):
        color = '#2ecc71' if val > 0 else '#e74c3c' if val < 0 else ''
        return f'color: {color}'
    return ''

def styled_dataframe(df):
    subset_cols = [c for c in df.columns if "Kâr/Zarar" in c or "%" in c]
    format_dict = {c: "{:,.2f}" for c in df.columns if df[c].dtype in ['float64', 'int64']}
    return df.style.map(highlight_pnl, subset=subset_cols).format(format_dict)

# --- MAIN ---
master_df = run_analysis(portfoy_df, USD_TRY, GORUNUM_PB)
if "Tip" in master_df.columns:
    portfoy_only = master_df[master_df["Tip"] == "Portfoy"]
    takip_only = master_df[master_df["Tip"] == "Takip"]
else:
    portfoy_only = pd.DataFrame()
    takip_only = pd.DataFrame()

def render_pazar_tab(df, filter_text, currency_symbol):
    if df.empty: st.info("Veri yok."); return
    df_filtered = df[df["Pazar"].str.contains(filter_text, na=False)]
    if df_filtered.empty: st.info(f"{filter_text} kategorisinde varlık bulunamadı."); return
    total_val = df_filtered["Değer"].sum()
    total_pl = df_filtered["Top. Kâr/Zarar"].sum()
    c1, c2 = st.columns(2)
    c1.metric(f"Toplam {filter_text} Varlık", f"{currency_symbol}{total_val:,.0f}")
    c2.metric(f"Toplam {filter_text} Kâr/Zarar", f"{currency_symbol}{total_pl:,.0f}", delta=f"{total_pl:,.0f}")
    
    st.divider()
    col_pie, col_bar = st.columns([1, 1])
    with col_pie:
        st.subheader(f"{filter_text} Dağılım")
        fig_pie = px.pie(df_filtered, values='Değer', names='Kod', hole=0.4)
        st.plotly_chart(fig_pie, use_container_width=True)
    with col_bar:
        st.subheader(f"{filter_text} Değerleri")
        df_sorted = df_filtered.sort_values(by="Değer", ascending=False)
        fig_bar = px.bar(df_sorted, x='Kod', y='Değer', color='Top. Kâr/Zarar')
        st.plotly_chart(fig_bar, use_container_width=True)
    
    if filter_text not in ["FON", "FIZIKI"]:
        st.divider()
        st.subheader(f"📈 {filter_text} Tarihsel Değer (Simülasyon)")
        hist_data = get_historical_chart(df_filtered, USD_TRY)
        if hist_data is not None: st.line_chart(hist_data, color="#4CAF50")

    st.divider()
    st.markdown("#### 🔍 Detaylı Analiz")
    varlik_listesi = df_filtered["Kod"].unique().tolist()
    secilen_varlik = st.selectbox(f"İncelemek istediğiniz {filter_text} varlığını seçin:", varlik_listesi, index=None, placeholder="Seçiniz...")
    if secilen_varlik:
        row = df_filtered[df_filtered["Kod"] == secilen_varlik].iloc[0]
        sym = get_yahoo_symbol(row["Kod"], row["Pazar"])
        render_detail_view(sym, row["Pazar"])

    st.divider()
    st.subheader(f"{filter_text} Liste")
    st.dataframe(styled_dataframe(df_filtered), use_container_width=True, hide_index=True)

sym = "₺" if GORUNUM_PB == "TRY" else "$"

if selected == "Dashboard":
    if not portfoy_only.empty:
        total_val = portfoy_only["Değer"].sum()
        total_pl = portfoy_only["Top. Kâr/Zarar"].sum()
        c1, c2 = st.columns(2)
        c1.metric("Toplam Portföy", f"{sym}{total_val:,.0f}")
        c2.metric("Genel Kâr/Zarar", f"{sym}{total_pl:,.0f}", delta=f"{total_pl:,.0f}")
        st.divider()
        col_pie, col_bar = st.columns([1, 1])
        with col_pie:
            st.subheader("Dağılım")
            fig_pie = px.pie(portfoy_only, values='Değer', names='Pazar', hole=0.4)
            st.plotly_chart(fig_pie, use_container_width=True)
        with col_bar:
            st.subheader("Pazar Büyüklükleri")
            df_pazar_group = portfoy_only.groupby("Pazar")["Değer"].sum().reset_index().sort_values(by="Değer", ascending=False)
            fig_bar = px.bar(df_pazar_group, x='Pazar', y='Değer', color='Pazar')
            st.plotly_chart(fig_bar, use_container_width=True)
        st.divider()
        st.subheader("📈 Tarihsel Zenginleşme (TL)")
        hist_data = get_historical_chart(portfoy_df, USD_TRY)
        if hist_data is not None: st.line_chart(hist_data, color="#4CAF50")
    else: st.info("Portföy boş.")

elif selected == "Tümü":
    if not portfoy_only.empty:
        st.markdown("#### 🔍 Detaylı Analiz")
        all_assets = portfoy_only["Kod"].unique().tolist()
        secilen = st.selectbox("İncelemek istediğiniz varlığı seçin:", all_assets, index=None, placeholder="Varlık Seç...")
        if secilen:
            row = portfoy_only[portfoy_only["Kod"] == secilen].iloc[0]
            sym = get_yahoo_symbol(row["Kod"], row["Pazar"])
            render_detail_view(sym, row["Pazar"])
        st.divider()
        st.subheader("Tüm Portföy Listesi")
        st.dataframe(styled_dataframe(portfoy_only), use_container_width=True, hide_index=True)
    else: st.info("Veri yok.")

elif selected == "BIST": render_pazar_tab(portfoy_only, "BIST", sym)
elif selected == "ABD": render_pazar_tab(portfoy_only, "ABD", sym)
elif selected == "FON": render_pazar_tab(portfoy_only, "FON", sym)
elif selected == "Emtia": render_pazar_tab(portfoy_only, "EMTIA", sym)
elif selected == "Fiziki": render_pazar_tab(portfoy_only, "FIZIKI", sym)
elif selected == "Kripto": render_pazar_tab(portfoy_only, "KRIPTO", sym)

elif selected == "Haberler":
    st.title("📰 Piyasa Haberleri")
    c1, c2 = st.columns(2)
    with c1: render_news_section("Borsa İstanbul", "BIST")
    with c2: render_news_section("Döviz & Altın", "DOVIZ")
    st.divider()
    c3, c4 = st.columns(2)
    with c3: render_news_section("Kripto Para", "KRIPTO")
    with c4: render_news_section("Küresel Piyasalar", "GLOBAL")

elif selected == "İzleme":
    st.subheader("İzleme Listesi")
    st.dataframe(styled_dataframe(takip_only), use_container_width=True, hide_index=True)

elif selected == "Satışlar":
    st.header("💰 Gerçekleşen Satış Geçmişi")
    sales_df = get_sales_history()
    if not sales_df.empty:
        sales_df["Kâr/Zarar"] = pd.to_numeric(sales_df["Kâr/Zarar"], errors='coerce')
        total_realized_pl = sales_df["Kâr/Zarar"].sum()
        st.metric("Toplam Realize Edilen (Cepteki) Kâr/Zarar", f"{total_realized_pl:,.2f}")
        st.divider()
        st.dataframe(styled_dataframe(sales_df.iloc[::-1]), use_container_width=True, hide_index=True)
    else: st.info("Henüz satış işlemi yok.")

elif selected == "Ekle/Çıkar":
    st.header("Varlık Yönetimi")
    
    # Excel İndir Butonu
    if not portfoy_only.empty:
        st.download_button(
            label="📥 Portföyü Excel Olarak İndir",
            data=portfoy_only.to_csv(index=False).encode('utf-8'),
            file_name='portfoyum.csv',
            mime='text/csv',
        )
    
    tab_ekle, tab_islem = st.tabs(["➕ Ekle", "📉 Satış / 🗑️ Sil"])
    
    # --- EKLEME KISMI ---
    with tab_ekle:
        islem_tipi = st.radio("Tür", ["Portföy", "Takip"], horizontal=True)
        yeni_pazar = st.selectbox("Pazar", list(MARKET_DATA.keys()))
        if "ABD" in yeni_pazar: st.warning("🇺🇸 ABD için Maliyeti DOLAR girin.")
        secenekler = MARKET_DATA.get(yeni_pazar, [])
        with st.form("add_asset_form"):
            yeni_kod = st.selectbox("Listeden Seç", options=secenekler, index=None, placeholder="Seçiniz...")
            manuel_kod = st.text_input("Veya Manuel Yaz (Örn: TTE)").upper()
            c1, c2 = st.columns(2)
            adet_inp = c1.number_input("Adet", min_value=0.0, step=0.001, format="%.3f")
            maliyet_inp = c2.number_input("Maliyet", min_value=0.0, step=0.01)
            not_inp = st.text_input("Not")
            if st.form_submit_button("Kaydet", type="primary", use_container_width=True):
                final_kod = manuel_kod if manuel_kod else yeni_kod
                if final_kod:
                    # Varsa eski kaydı çıkar (üzerine yazmak için)
                    portfoy_df = portfoy_df[portfoy_df["Kod"] != final_kod]
                    tip_str = "Portfoy" if islem_tipi == "Portföy" else "Takip"
                    yeni_satir = pd.DataFrame({
                        "Kod": [final_kod], "Pazar": [yeni_pazar], 
                        "Adet": [adet_inp], "Maliyet": [maliyet_inp],
                        "Tip": [tip_str], "Notlar": [not_inp]
                    })
                    portfoy_df = pd.concat([portfoy_df, yeni_satir], ignore_index=True)
                    save_data_to_sheet(portfoy_df)
                    st.success(f"{final_kod} başarıyla kaydedildi!")
                    time.sleep(1)
                    st.rerun()
                else: st.error("Lütfen bir varlık seçin veya yazın.")

    # --- SATIŞ VE SİLME KISMI ---
    with tab_islem:
        if not portfoy_df.empty:
            varliklar = portfoy_df[portfoy_df["Tip"] == "Portfoy"]["Kod"].unique()
            
            # 1. SATIŞ İŞLEMİ
            st.subheader("💰 Satış Yap (Kâr/Zarar İşler)")
            with st.form("sell_asset_form"):
                satilacak_kod = st.selectbox("Satılacak Varlık", varliklar)
                
                # Bilgi Gösterimi
                if satilacak_kod:
                    mevcut_veri = portfoy_df[portfoy_df["Kod"] == satilacak_kod].iloc[0]
                    mevcut_adet = float(mevcut_veri["Adet"])
                    mevcut_maliyet = float(mevcut_veri["Maliyet"])
                    pazar_yeri = mevcut_veri["Pazar"]
                    st.info(f"Elinizdeki: **{mevcut_adet}** Adet | Ort. Maliyet: **{mevcut_maliyet}**")
                else:
                    mevcut_adet = 0

                c1, c2 = st.columns(2)
                satilan_adet = c1.number_input("Satılacak Adet", min_value=0.0, max_value=mevcut_adet, step=0.01)
                satis_fiyati = c2.number_input("Satış Fiyatı", min_value=0.0, step=0.01)
                
                if st.form_submit_button("✅ Satışı Onayla", type="primary"):
                    if satilan_adet > 0 and satis_fiyati > 0:
                        kar_zarar = (satis_fiyati - mevcut_maliyet) * satilan_adet
                        tarih = datetime.now().strftime("%Y-%m-%d %H:%M")
                        
                        # Satış Geçmişine Ekle
                        add_sale_record(tarih, satilacak_kod, pazar_yeri, satilan_adet, satis_fiyati, mevcut_maliyet, kar_zarar)
                        
                        # Portföyden Düş
                        yeni_adet = mevcut_adet - satilan_adet
                        if yeni_adet <= 0.0001: 
                            portfoy_df = portfoy_df[portfoy_df["Kod"] != satilacak_kod]
                            msg = f"{satilacak_kod} tamamen satıldı."
                        else: 
                            portfoy_df.loc[portfoy_df["Kod"] == satilacak_kod, "Adet"] = yeni_adet
                            msg = f"{satilan_adet} adet satıldı. Kalan: {yeni_adet}"
                            
                        save_data_to_sheet(portfoy_df)
                        st.success(msg)
                        time.sleep(1)
                        st.rerun()
                    else: st.error("Lütfen geçerli adet ve fiyat giriniz.")

            st.markdown("---") # Ayırıcı Çizgi

            # 2. DİREKT SİLME İŞLEMİ (YENİ İSTEĞİN)
            st.subheader("🗑️ Kaydı Direkt Sil")
            st.caption("⚠️ Dikkat: Bu işlem varlığı satış geçmişine eklemeden, kâr/zarar hesaplamadan direkt listeden siler. (Hatalı girişler için)")
            
            with st.form("delete_row_form"):
                silinecek_kod = st.selectbox("Silinecek Varlık Seçin", varliklar, key="sil_box")
                
                if st.form_submit_button("🚫 Listeden Kalıcı Olarak Sil"):
                    if silinecek_kod:
                        portfoy_df = portfoy_df[portfoy_df["Kod"] != silinecek_kod]
                        save_data_to_sheet(portfoy_df)
                        st.warning(f"{silinecek_kod} listeden tamamen silindi!")
                        time.sleep(1)
                        st.rerun()
        else:
            st.info("Portföyünüz boş, işlem yapılacak varlık yok.")
        else: st.info("Satılacak varlık yok.")

