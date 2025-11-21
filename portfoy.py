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
from tefas import Crawler  # YENİ: TEFAS Kütüphanesi

# --- SAYFA AYARLARI ---
st.set_page_config(
    page_title="Merter’in Terminali", 
    layout="wide", 
    page_icon="🏦",
    initial_sidebar_state="collapsed"
)

# --- CSS: TASARIM (SONSUZ ŞERİT DÜZELTMESİ) ---
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
    
    /* SONSUZ KAYAN YAZI (Ticker Tape) */
    .ticker-container {
        width: 100%;
        overflow: hidden;
        background-color: #161616;
        border-bottom: 1px solid #333;
        margin-bottom: 20px;
        white-space: nowrap;
        position: relative;
    }
    
    .ticker-text {
        display: inline-block;
        white-space: nowrap;
        padding-left: 100%;
        animation: ticker 60s linear infinite;
        font-family: 'Courier New', monospace;
        font-size: 16px;
        font-weight: bold;
    }
    
    .ticker-item {
        display: inline-block;
        padding: 0 2rem;
    }

    /* Sonsuz döngü için animasyon */
    @keyframes ticker {
        0% { transform: translate3d(0, 0, 0); }
        100% { transform: translate3d(-50%, 0, 0); } /* İçeriği iki kere yazıp %50 kaydırıyoruz */
    }
</style>
""", unsafe_allow_html=True)

# --- YARDIMCI FONKSİYONLAR ---
def get_symbol_for_data(kod, pazar):
    if pazar == "FON": return kod # TEFAS kodları olduğu gibi (Örn: TTE)
    if "BIST" in pazar: return f"{kod}.IS" if not kod.endswith(".IS") else kod
    elif "KRIPTO" in pazar: return f"{kod}-USD" if not kod.endswith("-USD") else kod
    elif "EMTIA" in pazar:
        map_emtia = {"Altın ONS": "GC=F", "Gümüş ONS": "SI=F", "Petrol": "BZ=F", "Doğalgaz": "NG=F", "Bakır": "HG=F"}
        for k, v in map_emtia.items():
            if k in kod: return v
        return kod
    return kod 

# --- TEFAS VERİ ÇEKME (YENİ) ---
@st.cache_data(ttl=3600) # Fon fiyatları günde 1 değişir, sık yenilemeye gerek yok
def get_tefas_price(fund_code):
    try:
        crawler = Crawler()
        # Son 3 günlük veriyi çek, en sonuncuyu al
        start_date = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
        result = crawler.fetch(start=start_date, name=fund_code, columns=["Price"])
        if not result.empty:
            return result["Price"].iloc[0]
        return 0
    except:
        return 0

# --- GOOGLE SHEETS VERİ ÇEKME ---
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

def save_data_to_sheet(df):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = st.secrets["gcp_service_account"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    sheet = client.open(SHEET_NAME).sheet1
    sheet.clear()
    sheet.update([df.columns.values.tolist()] + df.values.tolist())

# --- MARKET VE PORTFÖY ŞERİDİ ---
@st.cache_data(ttl=60) 
def get_combined_ticker(df_portfolio):
    market_symbols = {"BIST 100": "XU100.IS", "USD": "TRY=X", "EUR": "EURTRY=X", "Altın": "GC=F", "BTC": "BTC-USD"}
    portfolio_symbols = {}
    
    if not df_portfolio.empty:
        assets = df_portfolio[df_portfolio["Tip"] == "Portfoy"]
        for _, row in assets.iterrows():
            kod = row['Kod']
            pazar = row['Pazar']
            if "Fiziki" not in pazar and "Gram" not in kod and pazar != "FON":
                sym = get_symbol_for_data(kod, pazar)
                portfolio_symbols[kod] = sym

    all_tickers = list(market_symbols.values()) + list(portfolio_symbols.values())
    all_tickers = list(set(all_tickers))
    
    data_str = '<span style="color:#4da6ff">🌍 PİYASA:</span> &nbsp;'
    try:
        yahoo_data = yf.Tickers(" ".join(all_tickers))
        for name, sym in market_symbols.items():
            try:
                hist = yahoo_data.tickers[sym].history(period="2d")
                if not hist.empty:
                    price = hist['Close'].iloc[-1]
                    prev = hist['Close'].iloc[-2]
                    change = ((price - prev) / prev) * 100
                    color = "#00e676" if change >= 0 else "#ff5252"
                    arrow = "▲" if change >= 0 else "▼"
                    data_str += f'{name}: <span style="color:white">{price:,.2f}</span> <span style="color:{color}">{arrow}%{change:.2f}</span> &nbsp;&nbsp;|&nbsp;&nbsp; '
            except: pass
        
        if portfolio_symbols:
            data_str += '&nbsp;&nbsp;&nbsp; <span style="color:#ffd700">💼 PORTFÖYÜM:</span> &nbsp;'
            for name, sym in portfolio_symbols.items():
                try:
                    hist = yahoo_data.tickers[sym].history(period="2d")
                    if not hist.empty:
                        price = hist['Close'].iloc[-1]
                        prev = hist['Close'].iloc[-2]
                        change = ((price - prev) / prev) * 100
                        color = "#00e676" if change >= 0 else "#ff5252"
                        arrow = "▲" if change >= 0 else "▼"
                        data_str += f'{name}: <span style="color:white">{price:,.2f}</span> <span style="color:{color}">{arrow}%{change:.2f}</span> &nbsp;&nbsp;|&nbsp;&nbsp; '
                except: pass
    except: data_str = "Veriler yükleniyor..."
    
    # İçeriği iki kere döndür (Sonsuz döngü efekti için)
    return f'<div class="ticker-text" style="animation: ticker 40s linear infinite;">{data_str} &nbsp;&nbsp;&nbsp; {data_str}</div>'

portfoy_df = get_data_from_sheet()

# --- BAŞLIK ---
c_title, c_toggle = st.columns([3, 1])
with c_title:
    st.title("🏦 Merter'in Varlık Yönetim Terminali")
with c_toggle:
    st.write("") 
    GORUNUM_PB = st.radio("Para Birimi:", ["TRY", "USD"], horizontal=True)

# --- KAYAN ŞERİT ---
ticker_html = get_combined_ticker(portfoy_df)
st.markdown(f"""<div class="ticker-container">{ticker_html}</div>""", unsafe_allow_html=True)

# --- NAVİGASYON ---
selected = option_menu(
    menu_title=None, 
    options=["Dashboard", "Tümü", "BIST", "ABD", "FON", "Emtia", "Fiziki", "Kripto", "İzleme", "Satışlar", "Ekle/Çıkar"], 
    icons=["speedometer2", "list-task", "graph-up-arrow", "currency-dollar", "piggy-bank", "fuel-pump", "house", "currency-bitcoin", "eye", "receipt", "gear"], 
    menu_icon="cast", 
    default_index=0, 
    orientation="horizontal",
    styles={
        "container": {"padding": "0!important", "background-color": "#161616"}, 
        "icon": {"color": "white", "font-size": "18px"}, 
        "nav-link": {"font-size": "14px", "text-align": "center", "margin":"0px", "--hover-color": "#333333", "font-weight": "bold", "color": "#bfbfbf"},
        "nav-link-selected": {"background-color": "#ffffff", "color": "#000000"}, 
    }
)

ANALYSIS_COLS = ["Kod", "Pazar", "Tip", "Adet", "Maliyet", "Fiyat", "PB", "Değer", "Top. Kâr/Zarar", "Top. %", "Gün. Kâr/Zarar", "Notlar"]

# --- VARLIK LİSTESİ (FON EKLENDİ) ---
MARKET_DATA = {
    "BIST (Tümü)": ["THYAO", "GARAN", "ASELS", "EREGL", "SISE", "BIMAS", "AKBNK", "YKBNK", "KCHOL", "SAHOL", "TUPRS", "FROTO", "TOASO", "PGSUS", "TCELL", "PETKM", "HEKTS", "SASA", "ASTOR", "KONTR", "MEGMT", "REEDR", "TABGD", "A1CAP", "ACSEL"], 
    "ABD (S&P + NASDAQ)": ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META"], 
    "KRIPTO": ["BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "AVAX"],
    "FON (TEFAS/BES)": ["TTE", "MAC", "AFT", "AFA", "YAY", "IPJ", "TCD", "NNF", "GMR", "TI2", "TI3"], # Örnek popüler fonlar
    "EMTIA": ["Gram Altın (TL)", "Gram Gümüş (TL)", "Altın ONS", "Gümüş ONS", "Petrol", "Doğalgaz"],
    "FIZIKI VARLIKLAR": ["Gram Altın (Fiziki)", "Çeyrek Altın", "Yarım Altın", "Tam Altın", "Dolar (Nakit)"]
}

@st.cache_data(ttl=300)
def get_usd_try():
    try:
        ticker = yf.Ticker("TRY=X")
        hist = ticker.history(period="1d")
        if not hist.empty: return hist['Close'].iloc[-1]
        return 34.0
    except: return 34.0

USD_TRY = get_usd_try()

# --- DETAYLI ANALİZ (MUM GRAFİĞİ İYİLEŞTİRİLDİ) ---
def render_detail_view(symbol, pazar):
    st.markdown(f"### 🔎 {symbol} Detaylı Analizi")
    
    # Fonlar için özel durum (Grafik yok, sadece bilgi)
    if pazar == "FON":
        price = get_tefas_price(symbol)
        st.metric(f"{symbol} Son Fiyat", f"₺{price:,.6f}")
        st.info("⚠️ Yatırım fonları için anlık mum grafiği desteği TEFAS kaynaklı olarak sınırlıdır. Günlük kapanış fiyatı yukarıdadır.")
        return

    # Normal Hisseler için Grafik
    try:
        ticker = yf.Ticker(symbol)
        # 2 Yıllık veri çekelim ki grafik dolsun
        hist = ticker.history(period="2y")
        
        if not hist.empty:
            # MUM GRAFİĞİ
            fig = go.Figure(data=[go.Candlestick(x=hist.index,
                            open=hist['Open'], high=hist['High'],
                            low=hist['Low'], close=hist['Close'],
                            name=symbol)])
            
            # ZAMAN DİLİMİ SEÇİCİ (RANGE SELECTOR) - İSTEDİĞİN ÖZELLİK
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
            
            # Temel Analiz
            info = ticker.info
            market_cap = info.get('marketCap', 'N/A')
            if isinstance(market_cap, int): market_cap = f"{market_cap:,.0f}"
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("F/K", info.get('trailingPE', 'N/A'))
            c2.metric("Piyasa Değeri", market_cap)
            c3.metric("52H Yüksek", info.get('fiftyTwoWeekHigh', 'N/A'))
            c4.metric("52H Düşük", info.get('fiftyTwoWeekLow', 'N/A'))
            
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
        
        # Fiyat Çekme Mantığı
        curr_price = 0
        prev_close = 0
        asset_currency = "USD"
        if "BIST" in pazar or "TL" in kod or "Fiziki" in pazar or pazar == "FON": asset_currency = "TRY"

        try:
            if pazar == "FON":
                curr_price = get_tefas_price(kod)
                prev_close = curr_price # Fonlarda günlük değişim anlık hesaplanmaz
            elif "Gram Altın (TL)" in kod:
                hist = yf.Ticker("GC=F").history(period="2d")
                curr_price = (hist['Close'].iloc[-1] * usd_try_rate) / 31.1035
            elif "Fiziki" in pazar: curr_price = maliyet
            else:
                symbol = get_symbol_for_data(kod, pazar)
                hist = yf.Ticker(symbol).history(period="2d")
                curr_price = hist['Close'].iloc[-1] if not hist.empty else maliyet
        except: curr_price = maliyet

        val_native = curr_price * adet
        cost_native = maliyet * adet
        
        # Para Birimi Dönüşümü
        if view_currency == "TRY":
            if asset_currency == "USD":
                fiyat_goster = curr_price * usd_try_rate
                val_goster = val_native * usd_try_rate
                cost_goster = cost_native * usd_try_rate
            else: 
                fiyat_goster = curr_price
                val_goster = val_native
                cost_goster = cost_native
        elif view_currency == "USD":
            if asset_currency == "TRY":
                fiyat_goster = curr_price / usd_try_rate
                val_goster = val_native / usd_try_rate
                cost_goster = cost_native / usd_try_rate
            else: 
                fiyat_goster = curr_price
                val_goster = val_native
                cost_goster = cost_native
        
        pnl = val_goster - cost_goster
        pnl_pct = (pnl / cost_goster * 100) if cost_goster > 0 else 0
        
        results.append({
            "Kod": kod, "Pazar": pazar, "Tip": row["Tip"],
            "Adet": adet, "Maliyet": maliyet,
            "Fiyat": fiyat_goster, "PB": view_currency,
            "Değer": val_goster, "Top. Kâr/Zarar": pnl, "Top. %": pnl_pct,
            "Gün. Kâr/Zarar": 0, "Notlar": row.get("Notlar", "")
        })
    return pd.DataFrame(results)

# --- DİĞER FONKSİYONLAR (AYNI) ---
# (styled_dataframe, get_historical_chart vb. önceki kodla aynı, yer tutmasın diye özet geçiyorum ama tam kodda hepsi var)
def highlight_pnl(val):
    if isinstance(val, (int, float)):
        color = '#2ecc71' if val > 0 else '#e74c3c' if val < 0 else ''
        return f'color: {color}'
    return ''
def styled_dataframe(df):
    subset_cols = [c for c in df.columns if "Kâr/Zarar" in c or "%" in c]
    format_dict = {c: "{:,.2f}" for c in df.columns if df[c].dtype in ['float64', 'int64']}
    return df.style.map(highlight_pnl, subset=subset_cols).format(format_dict)
@st.cache_data(ttl=3600)
def get_historical_chart(df, usd_try):
    if df.empty: return None
    tickers_map = {}
    for idx, row in df.iterrows():
        kod = row['Kod']
        pazar = row['Pazar']
        if "Gram" not in kod and "Fiziki" not in pazar and pazar != "FON":
            sym = get_symbol_for_data(kod, pazar)
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

# --- MAIN ÇALIŞTIRMA ---
master_df = run_analysis(portfoy_df, USD_TRY, GORUNUM_PB)
if "Tip" in master_df.columns:
    portfoy_only = master_df[master_df["Tip"] == "Portfoy"]
    takip_only = master_df[master_df["Tip"] == "Takip"]
else:
    portfoy_only, takip_only = pd.DataFrame(), pd.DataFrame()

def render_pazar_tab(df, filter_text, currency_symbol):
    if df.empty: st.info("Veri yok."); return
    df_filtered = df[df["Pazar"].str.contains(filter_text, na=False)]
    if df_filtered.empty: st.info(f"{filter_text} yok."); return
    total_val = df_filtered["Değer"].sum()
    total_pl = df_filtered["Top. Kâr/Zarar"].sum()
    c1, c2 = st.columns(2)
    c1.metric(f"Toplam {filter_text} Varlık", f"{currency_symbol}{total_val:,.0f}")
    c2.metric(f"Toplam {filter_text} Kâr/Zarar", f"{currency_symbol}{total_pl:,.0f}", delta=f"{total_pl:,.0f}")
    
    st.divider()
    st.markdown("#### 🔍 Detaylı Analiz")
    varlik_listesi = df_filtered["Kod"].unique().tolist()
    secilen_varlik = st.selectbox(f"İncelemek istediğiniz {filter_text} varlığını seçin:", varlik_listesi, index=None, placeholder="Seçiniz...")
    if secilen_varlik:
        row = df_filtered[df_filtered["Kod"] == secilen_varlik].iloc[0]
        sym = get_symbol_for_data(row["Kod"], row["Pazar"])
        render_detail_view(sym, row["Pazar"])

    st.divider()
    st.subheader(f"{filter_text} Liste")
    st.dataframe(styled_dataframe(df_filtered), use_container_width=True, hide_index=True)

sym = "₺" if GORUNUM_PB == "TRY" else "$"

# --- NAVİGASYON MANTIĞI ---
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
        st.subheader("📈 Tarihsel Zenginleşme")
        hist_data = get_historical_chart(portfoy_df, USD_TRY)
        if hist_data is not None: st.line_chart(hist_data, color="#4CAF50")
    else: st.info("Portföy boş.")

elif selected == "Tümü":
    if not portfoy_only.empty:
        st.markdown("#### 🔍 Detaylı Analiz")
        all_assets = portfoy_only["Kod"].unique().tolist()
        secilen = st.selectbox("İncelemek istediğiniz varlığı seçin:", all_assets, index=None, placeholder="Seçiniz...")
        if secilen:
            row = portfoy_only[portfoy_only["Kod"] == secilen].iloc[0]
            sym = get_symbol_for_data(row["Kod"], row["Pazar"])
            render_detail_view(sym, row["Pazar"])
        st.divider()
        st.subheader("Tüm Portföy Listesi")
        st.dataframe(styled_dataframe(portfoy_only), use_container_width=True, hide_index=True)
    else: st.info("Veri yok.")

elif selected == "BIST": render_pazar_tab(portfoy_only, "BIST", sym)
elif selected == "ABD": render_pazar_tab(portfoy_only, "ABD", sym)
elif selected == "FON": render_pazar_tab(portfoy_only, "FON", sym) # YENİ FON SEKME
elif selected == "Emtia": render_pazar_tab(portfoy_only, "EMTIA", sym)
elif selected == "Fiziki": render_pazar_tab(portfoy_only, "FIZIKI", sym)
elif selected == "Kripto": render_pazar_tab(portfoy_only, "KRIPTO", sym)

elif selected == "İzleme":
    st.subheader("İzleme Listesi")
    st.dataframe(styled_dataframe(takip_only), use_container_width=True, hide_index=True)

# (Satışlar ve Ekle Çıkar sekmeleri önceki kodla aynı, yer kaplamasın diye burayı kısa tuttum, 
# kopyalarken önceki koddan o kısmı alabilirsin veya tam kodu istersen söyle.)
elif selected == "Ekle/Çıkar":
    st.header("Varlık Yönetimi")
    # ... (Eski kodun aynısı) ...
    tab_ekle, tab_sil = st.tabs(["➕ Ekle", "📉 Sat/Sil"])
    with tab_ekle:
        islem_tipi = st.radio("Tür", ["Portföy", "Takip"], horizontal=True)
        yeni_pazar = st.selectbox("Pazar", list(MARKET_DATA.keys()))
        if "ABD" in yeni_pazar: st.warning("🇺🇸 ABD için Maliyeti DOLAR girin.")
        secenekler = MARKET_DATA.get(yeni_pazar, [])
        with st.form("add_asset_form"):
            yeni_kod = st.selectbox("Listeden Seç", options=secenekler, index=None, placeholder="Seçiniz...")
            manuel_kod = st.text_input("Veya Manuel Yaz (Fon Kodu: TTE, MAC vb.)").upper()
            c1, c2 = st.columns(2)
            adet_inp = c1.number_input("Adet", min_value=0.0, step=0.001, format="%.3f")
            maliyet_inp = c2.number_input("Maliyet", min_value=0.0, step=0.01)
            not_inp = st.text_input("Not")
            if st.form_submit_button("Kaydet", type="primary", use_container_width=True):
                final_kod = manuel_kod if manuel_kod else yeni_kod
                if final_kod:
                    portfoy_df = portfoy_df[portfoy_df["Kod"] != final_kod]
                    tip_str = "Portfoy" if islem_tipi == "Portföy" else "Takip"
                    yeni_satir = pd.DataFrame({
                        "Kod": [final_kod], "Pazar": [yeni_pazar], 
                        "Adet": [adet_inp], "Maliyet": [maliyet_inp],
                        "Tip": [tip_str], "Notlar": [not_inp]
                    })
                    portfoy_df = pd.concat([portfoy_df, yeni_satir], ignore_index=True)
                    save_data_to_sheet(portfoy_df)
                    st.success(f"{final_kod} kaydedildi!")
                    time.sleep(1)
                    st.rerun()
                else: st.error("Seçim yapın.")
    # Silme sekmesi aynı...
