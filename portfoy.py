import streamlit as st
import yfinance as yf
import pandas as pd
import time
import plotly.express as px
from streamlit_option_menu import option_menu

# --- MODÜLLER ---
from utils import (
    ANALYSIS_COLS,
    KNOWN_FUNDS,
    MARKET_DATA,
    smart_parse,
    styled_dataframe,
    get_yahoo_symbol,
)
from data_loader import (
    get_data_from_sheet,
    save_data_to_sheet,
    get_sales_history,
    add_sale_record,
    get_usd_try,
    get_tickers_data,
    get_financial_news,
    get_tefas_data,
    get_binance_positions,
)
from charts import (
    render_pie_bar_charts,
    render_pazar_tab,
    render_detail_view,
    get_historical_chart,
)

# --- SAYFA AYARLARI ---
st.set_page_config(
    page_title="Merter’in Terminali",
    layout="wide",
    page_icon="🏦",
    initial_sidebar_state="collapsed",
)

# --- CSS ---
st.markdown(
    """
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
    .market-ticker {
        background-color: #0e1117;
        border-bottom: 1px solid #333;
        padding: 8px 0;
    }
    .portfolio-ticker {
        background-color: #1a1c24;
        border-bottom: 2px solid #FF4B4B;
        padding: 8px 0;
        margin-bottom: 20px;
    }

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
""",
    unsafe_allow_html=True,
)

# --- HABER UI ---
def render_news_section(name, key):
    st.subheader(f"📰 {name}")
    news = get_financial_news(key)
    if news:
        for n in news:
            st.markdown(
                f"""
                <div class="news-card">
                    <a href="{n['link']}" target="_blank" class="news-title">
                        {n['title']}
                    </a>
                    <div class="news-meta">🕒 {n['date']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.info("Haber akışı yüklenemedi.")


# --- ANA DATA ---
portfoy_df = get_data_from_sheet()

c_title, c_toggle = st.columns([3, 1])
with c_title:
    st.title("🏦 Merter'in Varlık Yönetim Terminali")
with c_toggle:
    st.write("")
    GORUNUM_PB = st.radio("Para Birimi:", ["TRY", "USD"], horizontal=True)

USD_TRY = get_usd_try()
sym = "₺" if GORUNUM_PB == "TRY" else "$"

mh, ph = get_tickers_data(portfoy_df, USD_TRY)
st.markdown(
    f"""
<div class="ticker-container market-ticker">{mh}</div>
<div class="ticker-container portfolio-ticker">{ph}</div>
""",
    unsafe_allow_html=True,
)

selected = option_menu(
    menu_title=None,
    options=[
        "Dashboard",
        "Tümü",
        "BIST",
        "ABD",
        "FON",
        "Emtia",
        "Kripto",
        "Vadeli",
        "Nakit",
        "Haberler",
        "İzleme",
        "Satışlar",
        "Ekle/Çıkar",
    ],
    icons=[
        "speedometer2",
        "list-task",
        "graph-up-arrow",
        "currency-dollar",
        "piggy-bank",
        "fuel-pump",
        "currency-bitcoin",
        "lightning-charge",
        "wallet2",
        "newspaper",
        "eye",
        "receipt",
        "gear",
    ],
    menu_icon="cast",
    default_index=0,
    orientation="horizontal",
    styles={
        "container": {
            "padding": "0!important",
            "background-color": "#161616",
        },
        "icon": {"color": "white", "font-size": "18px"},
        "nav-link": {
            "font-size": "14px",
            "text-align": "center",
            "margin": "0px",
            "--hover-color": "#333333",
            "font-weight": "bold",
            "color": "#bfbfbf",
        },
        "nav-link-selected": {"background-color": "#ffffff", "color": "#000"},
    },
)


# --- ANALİZ ---
def run_analysis(df, usd_try_rate, view_currency):
    results = []

    if df.empty:
        return pd.DataFrame(columns=ANALYSIS_COLS)

    for _, row in df.iterrows():
        kod = row.get("Kod", "")
        pazar = row.get("Pazar", "")
        tip = row.get("Tip", "")

        if kod in KNOWN_FUNDS:
            pazar = "FON"
        if "FIZIKI" in str(pazar).upper():
            pazar = "EMTIA"

        adet = smart_parse(row.get("Adet", 0))
        maliyet = smart_parse(row.get("Maliyet", 0))

        if not kod:
            continue

        symbol = get_yahoo_symbol(kod, pazar)

        asset_currency = (
            "TRY"
            if (
                "BIST" in pazar
                or "TL" in kod
                or "FON" in pazar
                or "EMTIA" in pazar
                or "NAKIT" in pazar
            )
            else "USD"
        )

        curr = 0
        prev = 0

        try:
            if "NAKIT" in pazar:
                if kod == "TL":
                    curr = 1
                elif kod == "USD":
                    curr = USD_TRY
                elif kod == "EUR":
                    try:
                        curr = (
                            yf.Ticker("EURTRY=X")
                            .history(period="1d")["Close"]
                            .iloc[-1]
                        )
                    except Exception:
                        curr = 36.0
                prev = curr

            elif "VADELI" in pazar:
                h = yf.Ticker(symbol).history(period="2d")
                curr = h["Close"].iloc[-1] if not h.empty else maliyet

            elif "FON" in pazar:
                curr, prev = get_tefas_data(kod)

            elif "Gram Gümüş" in kod:
                h = yf.Ticker("SI=F").history(period="2d")
                c = h["Close"].iloc[-1]
                p = h["Close"].iloc[-2]
                curr = (c * USD_TRY) / 31.1035
                prev = (p * USD_TRY) / 31.1035

            elif "Gram Altın" in kod:
                h = yf.Ticker("GC=F").history(period="2d")
                c = h["Close"].iloc[-1]
                p = h["Close"].iloc[-2]
                curr = (c * USD_TRY) / 31.1035
                prev = (p * USD_TRY) / 31.1035

            else:
                h = yf.Ticker(symbol).history(period="2d")
                curr = h["Close"].iloc[-1]
                prev = h["Close"].iloc[0]
        except Exception:
            pass

        if curr == 0:
            curr = maliyet
        if prev == 0:
            prev = curr

        if curr > 0 and maliyet > 0 and (maliyet / curr) > 50:
            maliyet /= 100

        if "VADELI" in pazar:
            val_native = (curr - maliyet) * adet
            cost_native = 0
        else:
            val_native = curr * adet
            cost_native = maliyet * adet

        daily_chg_native = (curr - prev) * adet if "VADELI" not in pazar else 0

        if GORUNUM_PB == "TRY":
            if asset_currency == "USD":
                f_g = curr * USD_TRY
                v_g = val_native * USD_TRY
                c_g = cost_native * USD_TRY
                d_g = daily_chg_native * USD_TRY
            else:
                f_g = curr
                v_g = val_native
                c_g = cost_native
                d_g = daily_chg_native
        else:
            if asset_currency == "TRY":
                f_g = curr / USD_TRY
                v_g = val_native / USD_TRY
                c_g = cost_native / USD_TRY
                d_g = daily_chg_native / USD_TRY
            else:
                f_g = curr
                v_g = val_native
                c_g = cost_native
                d_g = daily_chg_native

        if "VADELI" in pazar:
            pnl = v_g
            pnl_pct = 0
        else:
            pnl = v_g - c_g
            pnl_pct = (pnl / c_g * 100) if c_g > 0 else 0

        results.append(
            {
                "Kod": kod,
                "Pazar": pazar,
                "Tip": tip,
                "Adet": adet,
                "Maliyet": maliyet,
                "Fiyat": f_g,
                "PB": GORUNUM_PB,
                "Değer": v_g,
                "Top. Kâr/Zarar": pnl,
                "Top. %": pnl_pct,
                "Gün. Kâr/Zarar": d_g,
                "Notlar": row.get("Notlar", ""),
            }
        )

    return pd.DataFrame(results)


master_df = run_analysis(portfoy_df, USD_TRY, GORUNUM_PB)

portfoy_only = master_df[master_df["Tip"] == "Portfoy"]
takip_only = master_df[master_df["Tip"] == "Takip"]


# --- MENÜLER ---
if selected == "Dashboard":
    if not portfoy_only.empty:
        spot_only = portfoy_only[
            ~portfoy_only["Pazar"].str.contains("VADELI", na=False)
        ]

        t_v = spot_only["Değer"].sum()
        t_p = spot_only["Top. Kâr/Zarar"].sum()

        # Dashboard için yüzde hesapla
        total_cost = (spot_only["Değer"] - spot_only["Top. Kâr/Zarar"]).sum()
        pct = (t_p / total_cost * 100) if total_cost != 0 else 0

        c1, c2 = st.columns(2)
        c1.metric("Toplam Spot Varlık", f"{sym}{t_v:,.0f}")
        c2.metric(
            "Genel Kâr/Zarar",
            f"{sym}{t_p:,.0f}",
            delta=f"{pct:.2f}%"
        )

        st.divider()

        st.subheader("📊 Pazarlara Göre Dağılım")
        dash_pazar = (
            spot_only.groupby("Pazar", as_index=False)
            .agg({"Değer": "sum", "Top. Kâr/Zarar": "sum"})
        )
        # Dashboard → tüm dilimler yazılı (all_tab=False)
        render_pie_bar_charts(dash_pazar, "Pazar", all_tab=False)

        st.divider()

        c_tree_1, c_tree_2 = st.columns([3, 1])
        with c_tree_1:
            st.subheader("🗺️ Portföy Isı Haritası")
        with c_tree_2:
            map_mode = st.radio(
                "Renklendirme:",
                ["Genel Kâr %", "Günlük Değişim %"],
                horizontal=True,
            )

        color_col = "Top. %"
        spot_only = spot_only.copy()
        spot_only["Gün. %"] = (
            spot_only["Gün. Kâr/Zarar"] /
            (spot_only["Değer"] - spot_only["Gün. Kâr/Zarar"])
        ) * 100

        if map_mode == "Günlük Değişim %":
            color_col = "Gün. %"

        fig = px.treemap(
            spot_only,
            path=[px.Constant("Portföy"), "Kod"],
            values="Değer",
            color=color_col,
            custom_data=["Değer", "Top. Kâr/Zarar", color_col],
            color_continuous_scale="RdYlGn",
            color_continuous_midpoint=0,
        )
        fig.update_traces(
            textinfo="label+value+percent entry",
            texttemplate="<b>%{label}</b><br>%{customdata[0]:,.0f}<br><b>%{customdata[2]:.2f}%</b>",
            textposition="middle center",
            textfont=dict(size=20, family="Arial Black"),
        )
        fig.update_layout(margin=dict(t=0, l=0, r=0, b=0))
        st.plotly_chart(fig, use_container_width=True)

    else:
        st.info("Boş.")

elif selected == "Tümü":
    if not portfoy_only.empty:
        st.subheader("📊 Varlık Bazlı Dağılım (Tümü)")
        # SADECE TÜMÜ sekmesinde -> %5 üstü yazılı
        render_pie_bar_charts(portfoy_only, "Kod", all_tab=True)

        st.divider()

        st.dataframe(
            styled_dataframe(portfoy_only),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("Portföy boş.")

elif selected == "Vadeli":
    st.subheader("🚀 Vadeli İşlemler")

    with st.expander("🔑 API ile Otomatik Çek (Opsiyonel)"):
        ak = st.text_input("API Key", type="password")
        ask = st.text_input("Secret", type="password")

        if ak and ask:
            stats, df_pos = get_binance_positions(ak, ask)
            if stats:
                st.metric("Cüzdan", f"${stats['wallet']:,.2f}")
                st.dataframe(df_pos, use_container_width=True)
            else:
                st.error(df_pos)

    st.markdown("---")
    st.markdown("### 📝 Manuel Vadeli Takip")
    render_pazar_tab(portfoy_only, "VADELI", sym, USD_TRY)

elif selected == "Nakit":
    render_pazar_tab(portfoy_only, "NAKIT", sym, USD_TRY)

elif selected == "BIST":
    render_pazar_tab(portfoy_only, "BIST", sym, USD_TRY)

elif selected == "ABD":
    render_pazar_tab(portfoy_only, "ABD", sym, USD_TRY)

elif selected == "FON":
    render_pazar_tab(portfoy_only, "FON", sym, USD_TRY)

elif selected == "Emtia":
    render_pazar_tab(portfoy_only, "EMTIA", sym, USD_TRY)

elif selected == "Kripto":
    render_pazar_tab(portfoy_only, "KRIPTO", sym, USD_TRY)

elif selected == "Haberler":
    tab1, tab2, tab3, tab4 = st.tabs(["BIST", "Kripto", "Global", "Döviz"])
    with tab1:
        render_news_section("BIST Haberleri", "BIST")
    with tab2:
        render_news_section("Kripto Haberleri", "KRIPTO")
    with tab3:
        render_news_section("Global Piyasalar", "GLOBAL")
    with tab4:
        render_news_section("Döviz / Altın", "DOVIZ")

elif selected == "İzleme":
    if not takip_only.empty:
        st.dataframe(
            styled_dataframe(takip_only),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("İzleme listesi boş.")

elif selected == "Satışlar":
    sales_df = get_sales_history()
    if not sales_df.empty:
        st.dataframe(
            styled_dataframe(sales_df),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("Satış kaydı yok.")

elif selected == "Ekle/Çıkar":
    st.header("Varlık Yönetimi")

    tab1, tab2, tab3 = st.tabs(["Ekle", "Düzenle", "Sil/Sat"])

    # --- EKLE ---
    with tab1:
        pazar = st.selectbox(
            "Pazar", list(MARKET_DATA.keys()) + ["VADELI (Manuel)"]
        )
        kod = st.text_input("Kod (Örn: BTC, THYAO)").upper()
        c1, c2 = st.columns(2)
        adet = c1.text_input("Adet/Kontrat", "0")
        maliyet = c2.text_input("Giriş Fiyatı", "0")

        if st.button("Kaydet"):
            a = smart_parse(adet)
            m = smart_parse(maliyet)
            if a > 0:
                portfoy_df = portfoy_df[portfoy_df["Kod"] != kod]
                new_row = pd.DataFrame(
                    {
                        "Kod": [kod],
                        "Pazar": [pazar],
                        "Adet": [a],
                        "Maliyet": [m],
                        "Tip": ["Portfoy"],
                        "Notlar": [""],
                    }
                )
                portfoy_df = pd.concat(
                    [portfoy_df, new_row], ignore_index=True
                )
                save_data_to_sheet(portfoy_df)
                st.success("Eklendi!")
                time.sleep(1)
                st.rerun()

    # --- DÜZENLE ---
    with tab2:
        if not portfoy_df.empty:
            s = st.selectbox("Seç", portfoy_df["Kod"].unique())
            r = portfoy_df[portfoy_df["Kod"] == s].iloc[0]

            na = st.text_input("Yeni Adet", str(r["Adet"]))
            nm = st.text_input("Yeni Maliyet", str(r["Maliyet"]))

            if st.button("Güncelle"):
                portfoy_df = portfoy_df[portfoy_df["Kod"] != s]
                new_row = pd.DataFrame(
                    {
                        "Kod": [s],
                        "Pazar": [r["Pazar"]],
                        "Adet": [smart_parse(na)],
                        "Maliyet": [smart_parse(nm)],
                        "Tip": [r["Tip"]],
                        "Notlar": [""],
                    }
                )
                portfoy_df = pd.concat(
                    [portfoy_df, new_row], ignore_index=True
                )
                save_data_to_sheet(portfoy_df)
                st.success("Güncellendi!")
                time.sleep(1)
                st.rerun()

    # --- SİL ---
    with tab3:
        if not portfoy_df.empty:
            s = st.selectbox(
                "Silinecek", portfoy_df["Kod"].unique(), key="del"
            )
            if st.button("🗑️ Sil"):
                portfoy_df = portfoy_df[portfoy_df["Kod"] != s]
                save_data_to_sheet(portfoy_df)
                st.success("Silindi!")
                time.sleep(1)
                st.rerun()
