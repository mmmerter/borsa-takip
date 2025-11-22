import streamlit as st
import pandas as pd
import time
from streamlit_option_menu import option_menu
from datetime import datetime

# Modüllerden import
from utils import smart_parse, styled_dataframe
import data_loader as dl
import charts as ch

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Merter’in Terminali", layout="wide", page_icon="🏦", initial_sidebar_state="collapsed")

# --- CSS ---
st.markdown("""
<style>
    .block-container {padding-top: 1rem;}
    div[data-testid="stMetric"] { background-color: #262730; border-radius: 10px; padding: 15px; color: #fff; }
    .ticker-container { width: 100%; overflow: hidden; background-color: #161616; margin-bottom: 20px; white-space: nowrap; }
    .market-ticker { background-color: #0e1117; border-bottom: 1px solid #333; padding: 8px 0; }
    .portfolio-ticker { background-color: #1a1c24; border-bottom: 2px solid #FF4B4B; padding: 8px 0; margin-bottom: 20px; }
    .ticker-text { display: inline-block; font-family: 'Courier New'; font-weight: 900; color: #00e676; }
    .animate-market { animation: ticker 65s linear infinite; color: #4da6ff; }
    .animate-portfolio { animation: ticker 55s linear infinite; color: #ffd700; }
    @keyframes ticker { 0% { transform: translate3d(0, 0, 0); } 100% { transform: translate3d(-50%, 0, 0); } }
    .news-card { background-color: #1E1E1E; padding: 15px; border-radius: 8px; border-left: 4px solid #FF4B4B; margin-bottom: 10px; }
    a { text-decoration: none !important; color: white !important; }
</style>
""", unsafe_allow_html=True)

# --- ANA DATA ---
portfoy_df = dl.get_data_from_sheet()
USD_TRY = dl.get_usd_try()

c_title, c_toggle = st.columns([3, 1])
with c_title: st.title("🏦 Merter'in Varlık Yönetim Terminali")
with c_toggle:
    st.write("")
    GORUNUM_PB = st.radio("Para Birimi:", ["TRY", "USD"], horizontal=True)

sym = "₺" if GORUNUM_PB == "TRY" else "$"

# Ticker (Cache hilesi: Dict olarak gönderiyoruz)
mh, ph = dl.get_tickers_data(portfoy_df.to_dict(), USD_TRY)
st.markdown(f'<div class="ticker-container market-ticker">{mh}</div><div class="ticker-container portfolio-ticker">{ph}</div>', unsafe_allow_html=True)

# Menü
selected = option_menu(
    menu_title=None,
    options=["Dashboard", "Tümü", "BIST", "ABD", "FON", "Emtia", "Kripto", "Vadeli", "Nakit", "Haberler", "İzleme", "Satışlar", "Ekle/Çıkar"],
    icons=["speedometer2", "list-task", "graph-up-arrow", "currency-dollar", "piggy-bank", "fuel-pump", "currency-bitcoin", "lightning-charge", "wallet2", "newspaper", "eye", "receipt", "gear"],
    menu_icon="cast", default_index=0, orientation="horizontal",
    styles={"container": {"padding": "0", "background-color": "#161616"}, "nav-link": {"font-size": "14px", "color": "#bfbfbf"}, "nav-link-selected": {"background-color": "#fff", "color": "#000"}}
)

# --- ANALİZ MOTORU (Burada main içinde durabilir veya data_loader'a taşınabilir, şimdilik burada) ---
def run_analysis_local(df):
    results = []
    if df.empty: return pd.DataFrame()
    
    for _, row in df.iterrows():
        kod, pazar, adet, maliyet = row["Kod"], row["Pazar"], smart_parse(row["Adet"]), smart_parse(row["Maliyet"])
        if not kod: continue
        
        symbol = dl.get_yahoo_symbol(kod, pazar)
        curr, prev = maliyet, maliyet # Default

        # Fiyat çekme mantığı (Basitleştirilmiş)
        try:
            if "NAKIT" in pazar:
                curr = 1 if kod == "TL" else (USD_TRY if kod == "USD" else 36.0)
            elif "FON" in pazar:
                curr, _ = dl.get_tefas_data(kod)
            elif "VADELI" not in pazar:
                t = yf.Ticker(symbol)
                h = t.history(period="1d")
                if not h.empty: curr = h["Close"].iloc[-1]
        except: pass
        
        if curr == 0: curr = maliyet
        
        # Hesaplamalar
        if "VADELI" in pazar:
            val_native = (curr - maliyet) * adet # PNL
            cost_native = 0
        else:
            val_native = curr * adet
            cost_native = maliyet * adet
            
        # Kur dönüşümü
        asset_currency = "TRY" if any(x in pazar for x in ["BIST", "FON", "EMTIA", "NAKIT"]) or "TL" in kod else "USD"
        
        if GORUNUM_PB == "TRY":
            rate = USD_TRY if asset_currency == "USD" else 1.0
        else:
            rate = (1.0 / USD_TRY) if asset_currency == "TRY" else 1.0
            
        v_g = val_native * rate
        c_g = cost_native * rate
        pnl = v_g - c_g if "VADELI" not in pazar else v_g
        
        results.append({
            "Kod": kod, "Pazar": pazar, "Tip": row["Tip"], "Değer": v_g,
            "Top. Kâr/Zarar": pnl, "Maliyet": maliyet, "Adet": adet
        })
    return pd.DataFrame(results)

master_df = run_analysis_local(portfoy_df)
portfoy_only = master_df[master_df["Tip"] == "Portfoy"] if not master_df.empty else pd.DataFrame()
takip_only = master_df[master_df["Tip"] == "Takip"] if not master_df.empty else pd.DataFrame()

# --- SAYFALAR ---
if selected == "Dashboard":
    if not portfoy_only.empty:
        spot = portfoy_only[~portfoy_only["Pazar"].str.contains("VADELI", na=False)]
        c1, c2 = st.columns(2)
        c1.metric("Toplam Varlık", f"{sym}{spot['Değer'].sum():,.0f}")
        c2.metric("Toplam Kâr/Zarar", f"{sym}{spot['Top. Kâr/Zarar'].sum():,.0f}")
        ch.render_pie_bar_charts(spot, "Pazar")
        
        # Treemap
        if not spot.empty:
            st.subheader("Portföy Haritası")
            import plotly.express as px
            fig = px.treemap(spot, path=[px.Constant("Portföy"), "Kod"], values="Değer", color="Top. Kâr/Zarar", color_continuous_scale="RdYlGn")
            st.plotly_chart(fig, use_container_width=True)

elif selected == "Haberler":
    tabs = st.tabs(["BIST", "Kripto", "Global", "Döviz"])
    keys = ["BIST", "KRIPTO", "GLOBAL", "DOVIZ"]
    for i, tab in enumerate(tabs):
        with tab:
            news = dl.get_financial_news(keys[i])
            for n in news:
                st.markdown(f'<div class="news-card"><a href="{n["link"]}">{n["title"]}</a><br><small>{n["date"]}</small></div>', unsafe_allow_html=True)

elif selected == "Ekle/Çıkar":
    st.header("Varlık Yönetimi")
    t1, t2, t3 = st.tabs(["Ekle", "Düzenle", "Sil"])
    with t1:
        k = st.text_input("Kod").upper()
        p = st.selectbox("Pazar", list(dl.MARKET_DATA.keys()))
        a = st.text_input("Adet", "0")
        m = st.text_input("Maliyet", "0")
        if st.button("Kaydet"):
            # Kaydetme mantığı basitçe:
            new_row = pd.DataFrame({"Kod": [k], "Pazar": [p], "Adet": [smart_parse(a)], "Maliyet": [smart_parse(m)], "Tip": ["Portfoy"], "Notlar": [""]})
            portfoy_df = pd.concat([portfoy_df, new_row], ignore_index=True)
            dl.save_data_to_sheet(portfoy_df)
            st.success("Kaydedildi")
            time.sleep(1)
            st.rerun()
            
    with t3:
        to_del = st.selectbox("Silinecek", portfoy_df["Kod"].unique()) if not portfoy_df.empty else None
        if st.button("Sil") and to_del:
            portfoy_df = portfoy_df[portfoy_df["Kod"] != to_del]
            dl.save_data_to_sheet(portfoy_df)
            st.success("Silindi")
            time.sleep(1)
            st.rerun()

else:
    # Diğer sekmeler (BIST, ABD, vb.) için generic render
    st.subheader(f"{selected} Portföyü")
    sub = portfoy_only[portfoy_only["Pazar"].str.contains(selected, na=False)] if selected != "Tümü" else portfoy_only
    if not sub.empty:
        ch.render_pie_bar_charts(sub, "Kod")
        st.dataframe(styled_dataframe(sub), use_container_width=True)
    else:
        st.info("Veri yok.")
