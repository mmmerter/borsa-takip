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
import ccxt

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
        background-color: #262730 !important;
        border: 1px solid #464b5f;
        border-radius: 10px;
        padding: 15px;
        color: #ffffff !important;
    }
    div[data-testid="stMetricValue"] { color: #ffffff !important; }
    div[data-testid="stMetricLabel"] { color: #bfbfbf !important; }
    
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
    if kod == "TRMET": return "KOZAA.IS"
    
    if pazar == "NAKIT": return kod 
    if pazar == "FON": return kod 
    if "BIST" in pazar: return f"{kod}.IS" if not kod.endswith(".IS") else kod
    elif "KRIPTO" in pazar: return f"{kod}-USD" if not kod.endswith("-USD") else kod
    elif "EMTIA" in pazar:
        map_emtia = {"Altın ONS": "GC=F", "Gümüş ONS": "SI=F", "Petrol": "BZ=F", "Doğalgaz": "NG=F", "Bakır": "HG=F"}
        for k, v in map_emtia.items():
            if k in kod: return v
        return kod
    return kod 

def smart_parse(text_val):
    if text_val is None: return 0.0
    val = str(text_val).strip()
    if not val: return 0.0
    val = re.sub(r"[^\d.,]", "", val)
    if val.count('.') > 1 and ',' not in val:
        parts = val.split('.')
        val = f"{parts[0]}.{''.join(parts[1:])}"
    if "." in val and "," in val:
        val = val.replace(".", "").replace(",", ".")
    elif "," in val:
        val = val.replace(",", ".")
    try: return float(val)
    except: return 0.0

# --- BINANCE VADELİ PNL ---
def get_binance_pnl_stats(exchange):
    try:
        income = exchange.fetch_income(params={"limit": 1000}) 
        now = datetime.now().timestamp() * 1000 
        day_ms, week_ms, month_ms = 86400000, 604800000, 2592000000
        pnl_day, pnl_week, pnl_month, pnl_total = 0, 0, 0, 0
        for inc in income:
            amount = float(inc['income'])
            ts = inc['timestamp']
            if inc['incomeType'] in ['REALIZED_PNL', 'COMMISSION', 'FUNDING_FEE']:
                pnl_total += amount
                if now - ts <= day_ms: pnl_day += amount
                if now - ts <= week_ms: pnl_week += amount
                if now - ts <= month_ms: pnl_month += amount
        return pnl_day, pnl_week, pnl_month, pnl_total
    except: return 0, 0, 0, 0

def get_binance_positions(api_key, api_secret):
    try:
        exchange = ccxt.binance({'apiKey': api_key, 'secret': api_secret, 'options': {'defaultType': 'future'}})
        balance = exchange.fetch_balance()
        total_wallet = balance['total']['USDT']
        total_unrealized = balance['info']['totalUnrealizedProfit']
        total_equity = float(balance['info']['totalMarginBalance'])
        p_day, p_week, p_month, p_total = get_binance_pnl_stats(exchange)
        positions = exchange.fetch_positions()
        active_positions = []
        for pos in positions:
            if float(pos['info']['positionAmt']) != 0:
                side = "🟢 LONG" if float(pos['info']['positionAmt']) > 0 else "🔴 SHORT"
                active_positions.append({
                    "Sembol": pos['symbol'], "Yön": side, "Lev": f"{pos['leverage']}x",
                    "Giriş": float(pos['entryPrice']), "Mark": float(pos['markPrice']),
                    "PNL": float(pos['unrealizedPnl']), "ROE %": round(float(pos['percentage']), 2)
                })
        stats = {"wallet": total_wallet, "equity": total_equity, "unrealized": float(total_unrealized), "pnl_day": p_day, "pnl_week": p_week, "pnl_month": p_month}
        return stats, pd.DataFrame(active_positions)
    except Exception as e: return None, str(e)

# --- TEFAS & COINGECKO ---
@st.cache_data(ttl=14400) 
def get_tefas_data(fund_code):
    try:
        url = f"https://www.tefas.gov.tr/FonAnaliz.aspx?FonKod={fund_code}"
        headers = {'User-Agent': 'Mozilla/5.0'}
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
        d = requests.get("https://api.coingecko.com/api/v3/global", timeout=5).json()['data']
        total_cap = d['total_market_cap']['usd']
        btc_d = d['market_cap_percentage']['btc']
        eth_d = d['market_cap_percentage']['eth']
        top2 = btc_d + eth_d
        total3 = total_cap * (1 - (top2 / 100))
        return total_cap, btc_d, total3, 100 - top2, total3
    except: return 0, 0, 0, 0, 0

# --- HABERLER ---
@st.cache_data(ttl=300)
def get_financial_news(topic="finance"):
    urls = {"BIST": "https://news.google.com/rss/search?q=Borsa+Istanbul+Hisseler&hl=tr&gl=TR&ceid=TR:tr", "KRIPTO": "https://news.google.com/rss/search?q=Kripto+Para+Bitcoin&hl=tr&gl=TR&ceid=TR:tr", "GLOBAL": "https://news.google.com/rss/search?q=ABD+Borsaları+Fed&hl=tr&gl=TR&ceid=TR:tr", "DOVIZ": "https://news.google.com/rss/search?q=Dolar+Altın+Piyasa&hl=tr&gl=TR&ceid=TR:tr"}
    feed = feedparser.parse(urls.get(topic, urls["BIST"]))
    return [{"title": e.title, "link": e.link, "date": e.published} for e in feed.entries[:10]]

def render_news_section(name, key):
    st.subheader(f"📰 {name}")
    for n in get_financial_news(key):
        st.markdown(f"""<div class="news-card"><a href="{n['link']}" target="_blank" class="news-title">{n['title']}</a><div class="news-meta">🕒 {n['date']}</div></div>""", unsafe_allow_html=True)

# --- DATA ---
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
        if not data: return pd.DataFrame(columns=["Tarih", "Kod", "Pazar", "Satılan Adet", "Satış Fiyatı", "Maliyet", "Kâr/Zarar"])
        return pd.DataFrame(data)
    except: return pd.DataFrame(columns=["Tarih", "Kod", "Pazar", "Satılan Adet", "Satış Fiyatı", "Maliyet", "Kâr/Zarar"])

def add_sale_record(date, code, market, qty, price, cost, profit):
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
        client = gspread.authorize(creds)
        sheet = client.open(SHEET_NAME).worksheet("Satislar")
        sheet.append_row([str(date), code, market, float(qty), float(price), float(cost), float(profit)])
    except: pass

# --- TAPE ---
@st.cache_data(ttl=45) 
def get_tickers_data(df_portfolio, usd_try):
    total_cap, btc_d, total_3, others_d, others_cap = get_crypto_globals()
    market_symbols = [("BIST 100", "XU100.IS"), ("USD", "TRY=X"), ("EUR", "EURTRY=X"), ("BTC/USDT", "BTC-USD"), ("ETH/USDT", "ETH-USD"), ("Ons Altın", "GC=F"), ("Ons Gümüş", "SI=F"), ("NASDAQ", "^IXIC"), ("S&P 500", "^GSPC")]
    portfolio_symbols = {}
    if not df_portfolio.empty:
        assets = df_portfolio[df_portfolio["Tip"] == "Portfoy"]
        for _, row in assets.iterrows():
            if "NAKIT" not in row['Pazar'] and "Gram" not in row['Kod'] and "FON" not in row['Pazar']:
                portfolio_symbols[row['Kod']] = get_yahoo_symbol(row['Kod'], row['Pazar'])

    all_fetch = list(set([s[1] for s in market_symbols] + list(portfolio_symbols.values())))
    market_html = '<span style="color:#aaa">🌍 PİYASA:</span> &nbsp;'
    portfolio_html = '<span style="color:#aaa">💼 PORTFÖY:</span> &nbsp;'
    try:
        yahoo_data = yf.Tickers(" ".join(all_fetch))
        def get_val(symbol, label=None):
            try:
                h = yahoo_data.tickers[symbol].history(period="2d")
                if not h.empty:
                    p = h['Close'].iloc[-1]; prev = h['Close'].iloc[-2]
                    chg = ((p-prev)/prev)*100
                    c, a = ("#00e676", "▲") if chg >= 0 else ("#ff5252", "▼")
                    fmt = f"{p:,.2f}" if p > 1 else f"{p:,.4f}"
                    if "XU100" in symbol or "^" in symbol: fmt = f"{p:,.0f}"
                    return f'{label if label else symbol}: <span style="color:white">{fmt}</span> <span style="color:{c}">{a}%{chg:.2f}</span>'
            except: return ""
            return ""

        for name, sym in market_symbols:
            val = get_val(sym, name)
            if val: market_html += f'{val} &nbsp;|&nbsp; '
            if name == "ETH/USDT":
                try:
                    ons = yahoo_data.tickers["GC=F"].history(period="1d")['Close'].iloc[-1]
                    market_html += f'Gr Altın: <span style="color:white">{(ons*usd_try)/31.1035:.2f}</span> &nbsp;|&nbsp; '
                except: pass
                try:
                    ons = yahoo_data.tickers["SI=F"].history(period="1d")['Close'].iloc[-1]
                    market_html += f'Gr Gümüş: <span style="color:white">{(ons*usd_try)/31.1035:.2f}</span> &nbsp;|&nbsp; '
                except: pass

        if total_cap > 0:
            market_html += f'BTC.D: <span style="color:#f2a900">% {btc_d:.2f}</span> &nbsp;|&nbsp; TOTAL: <span style="color:#00e676">${(total_cap/1e12):.2f}T</span> &nbsp;|&nbsp; TOTAL 3: <span style="color:#627eea">${(total_3/1e9):.0f}B</span> &nbsp;|&nbsp; OTHERS.D: <span style="color:#627eea">% {others_d:.2f}</span> &nbsp;|&nbsp; '

        if portfolio_symbols:
            for name, sym in portfolio_symbols.items():
                val = get_val(sym, name)
                if val: portfolio_html += f'{val} &nbsp;&nbsp;&nbsp; '
        else: portfolio_html += "Portföy boş veya veri çekilemiyor."
    except: market_html, portfolio_html = "Yükleniyor...", "Yükleniyor..."
    return f'<div class="ticker-text animate-market">{market_html} &nbsp;&nbsp;&nbsp; {market_html}</div>', f'<div class="ticker-text animate-portfolio">{portfolio_html} &nbsp;&nbsp;&nbsp; {portfolio_html}</div>'

portfoy_df = get_data_from_sheet()
c_title, c_toggle = st.columns([3, 1])
with c_title: st.title("🏦 Merter'in Varlık Yönetim Terminali")
with c_toggle:
    st.write("") 
    GORUNUM_PB = st.radio("Para Birimi:", ["TRY", "USD"], horizontal=True)

@st.cache_data(ttl=300)
def get_usd_try():
    try: return yf.Ticker("TRY=X").history(period="1d")['Close'].iloc[-1]
    except: return 34.0

# --- BURADA SEMBOL TANIMLANIYOR (HATAYI ÇÖZEN SATIR) ---
sym = "₺" if GORUNUM_PB == "TRY" else "$" 

USD_TRY = get_usd_try()
mh, ph = get_tickers_data(portfoy_df, USD_TRY)
st.markdown(f"""<div class="ticker-container market-ticker">{mh}</div><div class="ticker-container portfolio-ticker">{ph}</div>""", unsafe_allow_html=True)

selected = option_menu(
    menu_title=None, 
    options=["Dashboard", "Tümü", "BIST", "ABD", "FON", "Emtia", "Kripto", "Vadeli", "Nakit", "Haberler", "İzleme", "Satışlar", "Ekle/Çıkar"], 
    icons=["speedometer2", "list-task", "graph-up-arrow", "currency-dollar", "piggy-bank", "fuel-pump", "currency-bitcoin", "lightning-charge", "wallet2", "newspaper", "eye", "receipt", "gear"], 
    menu_icon="cast", default_index=0, orientation="horizontal",
    styles={"container": {"padding": "0!important", "background-color": "#161616"}, "icon": {"color": "white", "font-size": "18px"}, "nav-link": {"font-size": "14px", "text-align": "center", "margin":"0px", "--hover-color": "#333333", "font-weight": "bold", "color": "#bfbfbf"}, "nav-link-selected": {"background-color": "#ffffff", "color": "#000000"}}
)

ANALYSIS_COLS = ["Kod", "Pazar", "Tip", "Adet", "Maliyet", "Fiyat", "PB", "Değer", "Top. Kâr/Zarar", "Top. %", "Gün. Kâr/Zarar", "Notlar"]
KNOWN_FUNDS = ["YHB", "TTE", "MAC", "AFT", "AFA", "YAY", "IPJ", "TCD", "NNF", "GMR", "TI2", "TI3", "IHK", "IDH", "OJT", "HKH", "IPB", "KZL", "RPD"]
MARKET_DATA = {
    "BIST (Tümü)": ["THYAO", "GARAN", "ASELS", "TRMET"], 
    "ABD": ["AAPL", "TSLA"], "KRIPTO": ["BTC", "ETH"], "FON": KNOWN_FUNDS, "EMTIA": ["Gram Altın", "Gram Gümüş"], "VADELI": ["BTC", "ETH", "SOL"]
}

# --- MAIN ANALİZ ---
def run_analysis(df):
    results = []
    if df.empty: return pd.DataFrame(columns=ANALYSIS_COLS)
    for i, row in df.iterrows():
        kod = row.get("Kod", "")
        pazar = row.get("Pazar", "")
        if kod in KNOWN_FUNDS: pazar = "FON"
        if "FIZIKI" in str(pazar).upper(): pazar = "EMTIA"
        adet = smart_parse(row.get("Adet", 0))
        maliyet = smart_parse(row.get("Maliyet", 0))
        if not kod: continue
        
        symbol = get_yahoo_symbol(kod, pazar)
        asset_currency = "USD"
        if "BIST" in pazar or "TL" in kod or "FON" in pazar or "EMTIA" in pazar or "NAKIT" in pazar: asset_currency = "TRY"
        
        curr, prev = 0, 0
        # --- FİYAT ÇEKME MANTIKLARI ---
        try:
            if "NAKIT" in pazar:
                if kod == "TL": curr = 1
                elif kod == "USD": curr = USD_TRY
                elif kod == "EUR": 
                     try: curr = yf.Ticker("EURTRY=X").history(period="1d")['Close'].iloc[-1]
                     except: curr = 36.0
                prev = curr
            elif "VADELI" in pazar:
                h = yf.Ticker(symbol).history(period="2d")
                if not h.empty: curr = h['Close'].iloc[-1]
                else: curr = maliyet
            elif "FON" in pazar:
                curr, prev = get_tefas_data(kod)
            elif "Gram Gümüş" in kod:
                h = yf.Ticker("SI=F").history(period="2d")
                if not h.empty:
                    c = h['Close'].iloc[-1]; p = h['Close'].iloc[-2]
                    curr = (c * USD_TRY) / 31.1035; prev = (p * USD_TRY) / 31.1035
            elif "Gram Altın" in kod:
                h = yf.Ticker("GC=F").history(period="2d")
                if not h.empty:
                    c = h['Close'].iloc[-1]; p = h['Close'].iloc[-2]
                    curr = (c * USD_TRY) / 31.1035; prev = (p * USD_TRY) / 31.1035
            else: # Normal Hisseler
                h = yf.Ticker(symbol).history(period="2d")
                if not h.empty:
                    curr = h['Close'].iloc[-1]; prev = h['Close'].iloc[0]
        except: pass
        
        if curr == 0: curr = maliyet
        if prev == 0: prev = curr
        
        # Maliyet Düzeltmesi
        if curr > 0 and maliyet > 0 and (maliyet/curr) > 50: maliyet /= 100
        
        # Vadeli İçin Özel PNL Hesabı (Kaldıraçsız Ham PNL Gösterimi - Manuel Olduğu İçin)
        if "VADELI" in pazar:
            val_native = (curr - maliyet) * adet # PNL (USDT)
            cost_native = 0 
        else:
            val_native = curr * adet
            cost_native = maliyet * adet
        
        daily_chg_native = (curr - prev) * adet if "VADELI" not in pazar else 0
        
        # Kur Çevirimi
        if GORUNUM_PB == "TRY":
            if asset_currency == "USD":
                f_g = curr * USD_TRY; v_g = val_native * USD_TRY
                c_g = cost_native * USD_TRY; d_g = daily_chg_native * USD_TRY
            else:
                f_g = curr; v_g = val_native; c_g = cost_native; d_g = daily_chg_native
        else: # USD GÖRÜNÜM
            if asset_currency == "TRY":
                f_g = curr / USD_TRY; v_g = val_native / USD_TRY
                c_g = cost_native / USD_TRY; d_g = daily_chg_native / USD_TRY
            else:
                f_g = curr; v_g = val_native; c_g = cost_native; d_g = daily_chg_native
        
        if "VADELI" in pazar:
            pnl = v_g 
            pnl_pct = 0 
        else:
            pnl = v_g - c_g
            pnl_pct = (pnl / c_g * 100) if c_g > 0 else 0

        results.append({
            "Kod": kod, "Pazar": pazar, "Tip": row["Tip"], "Adet": adet, "Maliyet": maliyet,
            "Fiyat": f_g, "PB": GORUNUM_PB, "Değer": v_g, "Top. Kâr/Zarar": pnl, "Top. %": pnl_pct,
            "Gün. Kâr/Zarar": d_g, "Notlar": row.get("Notlar", "")
        })
    return pd.DataFrame(results)

master_df = run_analysis(portfoy_df)
if "Tip" in master_df.columns:
    portfoy_only = master_df[master_df["Tip"] == "Portfoy"]
    takip_only = master_df[master_df["Tip"] == "Takip"]
else: portfoy_only, takip_only = pd.DataFrame(), pd.DataFrame()

# --- GÖRÜNÜM FONKSİYONLARI ---
def render_pazar_tab(df, filter, sym):
    if df.empty: return st.info("Veri yok.")
    if filter == "VADELI": sub = df[df["Pazar"].str.contains("VADELI", na=False)]
    else: sub = df[df["Pazar"].str.contains(filter, na=False)]
    
    if sub.empty: return st.info(f"{filter} yok.")
    
    t_val = sub["Değer"].sum()
    t_pl = sub["Top. Kâr/Zarar"].sum()
    
    c1, c2 = st.columns(2)
    lbl = "Toplam PNL" if filter == "VADELI" else "Toplam Varlık"
    c1.metric(lbl, f"{sym}{t_val:,.0f}")
    c2.metric("Toplam Kâr/Zarar", f"{sym}{t_pl:,.0f}", delta=f"{t_pl:,.0f}")
    
    st.divider()
    if filter != "VADELI": 
        c_p, c_b = st.columns(2)
        c_p.plotly_chart(px.pie(sub, values='Değer', names='Kod', hole=0.4), use_container_width=True)
        c_b.plotly_chart(px.bar(sub.sort_values('Değer'), x='Kod', y='Değer', color='Top. Kâr/Zarar'), use_container_width=True)
        if filter not in ["FON", "EMTIA"]:
             h = get_historical_chart(sub, USD_TRY)
             if h is not None: st.line_chart(h, color="#4CAF50")

    st.dataframe(styled_dataframe(sub), use_container_width=True, hide_index=True)

# --- SEKMELER ---
if selected == "Dashboard":
    if not portfoy_only.empty:
        spot_only = portfoy_only[~portfoy_only["Pazar"].str.contains("VADELI")]
        t_v = spot_only["Değer"].sum()
        t_p = spot_only["Top. Kâr/Zarar"].sum()
        
        c1, c2 = st.columns(2)
        c1.metric("Toplam Spot Varlık", f"{sym}{t_v:,.0f}")
        c2.metric("Genel Kâr/Zarar", f"{sym}{t_p:,.0f}", delta=f"{t_p:,.0f}")
        
        st.divider()
        # Treemap
        c_tree_1, c_tree_2 = st.columns([3, 1])
        with c_tree_1: st.subheader("🗺️ Portföy Isı Haritası")
        with c_tree_2: map_mode = st.radio("Renklendirme:", ["Genel Kâr %", "Günlük Değişim %"], horizontal=True)
        
        color_col = 'Top. %'
        spot_only['Gün. %'] = 0
        # Sıfıra bölme hatasını önle
        safe_deger = spot_only['Değer'] - spot_only['Gün. Kâr/Zarar']
        mask = safe_deger != 0
        spot_only.loc[mask, 'Gün. %'] = (spot_only.loc[mask, 'Gün. Kâr/Zarar'] / safe_deger[mask]) * 100
        
        if map_mode == "Günlük Değişim %": color_col = 'Gün. %'

        fig = px.treemap(
            spot_only, path=[px.Constant("Portföy"), 'Kod'], values='Değer', 
            color=color_col, custom_data=['Değer', 'Top. Kâr/Zarar', color_col],
            color_continuous_scale='RdYlGn', color_continuous_midpoint=0
        )
        fig.update_traces(
            textinfo="label+value+percent entry",
            texttemplate="<b>%{label}</b><br>%{customdata[0]:,.0f}<br><b>%{customdata[2]:.2f}%</b>",
            textposition="middle center",
            textfont=dict(size=20, family="Arial Black")
        )
        fig.update_layout(margin=dict(t=0, l=0, r=0, b=0))
        st.plotly_chart(fig, use_container_width=True)
        
        h = get_historical_chart(portfoy_df, USD_TRY)
        if h is not None: st.line_chart(h, color="#4CAF50")
    else: st.info("Boş.")

elif selected == "Tümü":
    st.dataframe(styled_dataframe(portfoy_only), use_container_width=True)

elif selected == "Vadeli":
    st.subheader("🚀 Vadeli İşlemler")
    with st.expander("🔑 API ile Otomatik Çek (Opsiyonel)"):
        ak = st.text_input("API Key", type="password")
        ask = st.text_input("Secret", type="password")
        if ak and ask:
            stats, df_pos = get_binance_positions(ak, ask)
            if stats:
                st.metric("Cüzdan", f"${stats['wallet']:,.2f}")
                st.dataframe(df_pos)
            else: st.error(df_pos)
    
    st.markdown("---")
    st.markdown("### 📝 Manuel Vadeli Takip")
    render_pazar_tab(portfoy_only, "VADELI", sym)

elif selected == "Nakit":
    render_pazar_tab(portfoy_only, "NAKIT", sym)

elif selected == "BIST": render_pazar_tab(portfoy_only, "BIST", sym)
elif selected == "ABD": render_pazar_tab(portfoy_only, "ABD", sym)
elif selected == "FON": render_pazar_tab(portfoy_only, "FON", sym)
elif selected == "Emtia": render_pazar_tab(portfoy_only, "EMTIA", sym)
elif selected == "Kripto": render_pazar_tab(portfoy_only, "KRIPTO", sym)

elif selected == "Ekle/Çıkar":
    st.header("Varlık Yönetimi")
    tab1, tab2, tab3 = st.tabs(["Ekle", "Düzenle", "Sil/Sat"])
    with tab1:
        pazar = st.selectbox("Pazar", list(MARKET_DATA.keys()) + ["VADELI (Manuel)"])
        kod = st.text_input("Kod (Örn: BTC, THYAO)").upper()
        c1, c2 = st.columns(2)
        adet = c1.text_input("Adet/Kontrat", "0")
        maliyet = c2.text_input("Giriş Fiyatı", "0")
        if st.button("Kaydet"):
             a = smart_parse(adet); m = smart_parse(maliyet)
             if a > 0:
                 portfoy_df = portfoy_df[portfoy_df["Kod"] != kod]
                 new_row = pd.DataFrame({"Kod": [kod], "Pazar": [pazar], "Adet": [a], "Maliyet": [m], "Tip": ["Portfoy"], "Notlar": [""]})
                 portfoy_df = pd.concat([portfoy_df, new_row], ignore_index=True)
                 save_data_to_sheet(portfoy_df)
                 st.success("Eklendi!")
                 time.sleep(1)
                 st.rerun()
    
    with tab2:
        if not portfoy_df.empty:
            s = st.selectbox("Seç", portfoy_df["Kod"].unique())
            if s:
                r = portfoy_df[portfoy_df["Kod"]==s].iloc[0]
                na = st.text_input("Yeni Adet", str(r["Adet"]))
                nm = st.text_input("Yeni Maliyet", str(r["Maliyet"]))
                if st.button("Güncelle"):
                    portfoy_df = portfoy_df[portfoy_df["Kod"] != s]
                    new_row = pd.DataFrame({"Kod": [s], "Pazar": [r["Pazar"]], "Adet": [smart_parse(na)], "Maliyet": [smart_parse(nm)], "Tip": [r["Tip"]], "Notlar": [""]})
                    portfoy_df = pd.concat([portfoy_df, new_row], ignore_index=True)
                    save_data_to_sheet(portfoy_df)
                    st.success("Güncellendi!")
                    time.sleep(1)
                    st.rerun()
                    
    with tab3:
        if not portfoy_df.empty:
            s = st.selectbox("Silinecek", portfoy_df["Kod"].unique(), key="del")
            if st.button("🗑️ Sil"):
                portfoy_df = portfoy_df[portfoy_df["Kod"] != s]
                save_data_to_sheet(portfoy_df)
                st.success("Silindi!")
                time.sleep(1)
                st.rerun()
