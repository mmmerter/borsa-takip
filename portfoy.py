import streamlit as st
import pandas as pd
from streamlit_option_menu import option_menu

# --- IMPORTS ---
from utils import ANALYSIS_COLS, KNOWN_FUNDS, MARKET_DATA, smart_parse, styled_dataframe, get_yahoo_symbol
from data_loader import get_data_from_sheet, save_data_to_sheet, get_sales_history, get_usd_try, get_tickers_data, get_financial_news, get_tefas_data, get_binance_positions
from charts import render_pie_bar_charts, render_pazar_tab, get_historical_chart

st.set_page_config(page_title="Merter’in Terminali", layout="wide", page_icon="🏦", initial_sidebar_state="collapsed")

# --- CSS ---
st.markdown("""
<style>
    header { visibility: hidden; height: 0px; }
    div.st-emotion-cache-1c9v9c4 { padding: 0 !important; }
    .block-container { padding-top: 1rem; padding-left: 0 !important; padding-right: 0 !important; }
    div[data-testid="stMetric"] { background-color: #262730 !important; border-radius: 10px; padding: 15px; }
    .ticker-text { font-weight: 900; color: #00e676; }
    .animate-market { animation: ticker 65s linear infinite; color: #4da6ff; }
    .animate-portfolio { animation: ticker 55s linear infinite; color: #ffd700; }
    @keyframes ticker { 0% { transform: translate3d(0, 0, 0); } 100% { transform: translate3d(-50%, 0, 0); } }
    .ticker-container { width: 100%; overflow: hidden; background-color: #161616; white-space: nowrap; }
</style>
""", unsafe_allow_html=True)

# --- DATA ---
portfoy_df = get_data_from_sheet()
c_title, c_toggle = st.columns([3, 1])
with c_title: st.title("🏦 Merter'in Varlık Yönetim Terminali")
with c_toggle:
    st.write("")
    GORUNUM_PB = st.radio("PB:", ["TRY", "USD"], horizontal=True)

USD_TRY = get_usd_try()
sym = "₺" if GORUNUM_PB == "TRY" else "$"

mh, ph = get_tickers_data(portfoy_df, USD_TRY)
st.markdown(f'<div class="ticker-container"><div class="ticker-text animate-market">{mh}</div></div>', unsafe_allow_html=True)
st.markdown(f'<div class="ticker-container"><div class="ticker-text animate-portfolio">{ph}</div></div>', unsafe_allow_html=True)

selected = option_menu(None, ["Dashboard", "Tümü", "BIST", "ABD", "FON", "Emtia", "Kripto", "Vadeli", "Nakit", "Haberler", "İzleme", "Satışlar", "Ekle/Çıkar"], 
    icons=["speedometer2", "list-task"], menu_icon="cast", default_index=0, orientation="horizontal",
    styles={"container": {"padding": "0", "background-color": "#161616"}, "nav-link": {"font-size": "14px", "margin": "0px"}})

# --- ANALİZ MOTORU ---
def run_analysis(df, usd_try_rate, view_currency):
    results = []
    if df.empty: return pd.DataFrame(columns=ANALYSIS_COLS)
    for _, row in df.iterrows():
        kod, pazar, tip = row["Kod"], row["Pazar"], row["Tip"]
        adet, maliyet = smart_parse(row["Adet"]), smart_parse(row["Maliyet"])
        if not kod: continue
        
        symbol = get_yahoo_symbol(kod, pazar)
        curr = maliyet # Default
        
        # Basit Fiyat Çekme
        try:
            if "NAKIT" in pazar: curr = 1 if kod == "TL" else usd_try_rate
            elif "VADELI" in pazar: pass 
            elif "FON" in pazar: curr, _ = get_tefas_data(kod)
            elif "Gram" in kod: # Basit Gram hesabı (daha detaylısı charts'ta)
                 import yfinance as yf
                 ons = yf.Ticker("GC=F" if "Altın" in kod else "SI=F").history(period="1d")["Close"].iloc[-1]
                 curr = (ons * usd_try_rate) / 31.1035
            else:
                 import yfinance as yf
                 curr = yf.Ticker(symbol).history(period="1d")["Close"].iloc[-1]
        except: pass
        
        if curr == 0: curr = maliyet
        
        val_native = curr * adet
        cost_native = maliyet * adet
        
        # PB Çevrimi
        is_try = "BIST" in pazar or "FON" in pazar or "TL" in kod or "Gram" in kod
        if view_currency == "USD":
            f_g = curr / usd_try_rate if is_try else curr
            v_g = val_native / usd_try_rate if is_try else val_native
        else: # TRY
            f_g = curr if is_try else curr * usd_try_rate
            v_g = val_native if is_try else val_native * usd_try_rate
            
        pnl = v_g - (cost_native / usd_try_rate if is_try and view_currency=="USD" else cost_native * usd_try_rate if not is_try and view_currency=="TRY" else cost_native)
        
        results.append({"Kod": kod, "Pazar": pazar, "Tip": tip, "Adet": adet, "Maliyet": maliyet, "Fiyat": f_g, "Değer": v_g, "Top. Kâr/Zarar": pnl, "Notlar": row.get("Notlar", "")})
    return pd.DataFrame(results)

master_df = run_analysis(portfoy_df, USD_TRY, GORUNUM_PB)
portfoy_only = master_df[master_df["Tip"] == "Portfoy"]
takip_only = master_df[master_df["Tip"] == "Takip"]

TOTAL_SPOT = portfoy_only[~portfoy_only["Pazar"].str.contains("VADELI", na=False)]["Değer"].sum()
st.markdown("---")
VARLIK_GORUNUMU = st.radio("Varlık:", ["YÜZDE (%)", "TUTAR"], horizontal=True)
st.markdown("---")

if selected == "Dashboard":
    if not portfoy_only.empty:
        spot = portfoy_only[~portfoy_only["Pazar"].str.contains("VADELI", na=False)]
        tv = spot["Değer"].sum()
        tp = spot["Top. Kâr/Zarar"].sum()
        c1, c2 = st.columns(2)
        c1.metric("Toplam", f"{sym}{tv:,.0f}")
        c2.metric("K/Z", f"{sym}{tp:,.0f}")
        
        st.subheader("📈 Tarihsel Değer")
        hc = get_historical_chart(spot, USD_TRY, GORUNUM_PB)
        if hc: st.plotly_chart(hc, use_container_width=True)
        
        st.subheader("Dağılım")
        dash_pazar = spot.groupby("Pazar", as_index=False).agg({"Değer": "sum", "Top. Kâr/Zarar": "sum"})
        render_pie_bar_charts(dash_pazar, "Pazar", False, VARLIK_GORUNUMU, TOTAL_SPOT)
    else: st.info("Boş")

elif selected == "Tümü":
    render_pazar_tab(portfoy_only, "Tümü", sym, USD_TRY, VARLIK_GORUNUMU, TOTAL_SPOT)
elif selected == "Vadeli":
    st.info("Vadeli Sekmesi")
    render_pazar_tab(portfoy_only, "VADELI", sym, USD_TRY, "TUTAR", TOTAL_SPOT)
elif selected == "Haberler":
    render_news_section("BIST", "BIST")
elif selected == "İzleme":
    st.dataframe(styled_dataframe(takip_only), use_container_width=True)
elif selected == "Satışlar":
    st.dataframe(styled_dataframe(get_sales_history()), use_container_width=True)
elif selected == "Ekle/Çıkar":
    st.write("Ekleme Modülü")
else:
    render_pazar_tab(portfoy_only, selected, sym, USD_TRY, VARLIK_GORUNUMU, TOTAL_SPOT)
