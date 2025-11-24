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
    read_portfolio_history,
    write_portfolio_history,
    get_timeframe_changes,
    read_history_bist,
    write_history_bist,
    read_history_abd,
    write_history_abd,
    read_history_fon,
    write_history_fon,
    read_history_emtia,
    write_history_emtia,
    read_history_nakit,
    write_history_nakit,
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
    /* Streamlit Header Gizle */
    header { visibility: hidden; height: 0px; }
    
    /* Kenar Boşluklarını Sıfırla */
    div.st-emotion-cache-1c9v9c4 { padding: 0 !important; }
    .block-container {
        padding-top: 1rem;
        padding-left: 0 !important;
        padding-right: 0 !important;
    }

    /* Metric Kutuları */
    div[data-testid="stMetric"] {
        background-color: #262730 !important;
        border: 1px solid #464b5f;
        border-radius: 10px;
        padding: 15px;
        color: #ffffff !important;
    }
    div[data-testid="stMetricValue"] { color: #ffffff !important; }
    div[data-testid="stMetricLabel"] { color: #bfbfbf !important; }

    /* Ticker Alanı */
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
        font-weight: 900;
        color: #00e676;
    }
    
    /* Animasyonlar */
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

    /* KRAL HEADER (B Şıkkı – hafif renkli kart) */
    .kral-header {
        background: linear-gradient(135deg, #232837, #171b24);
        border-radius: 14px;
        padding: 14px 20px 10px 20px;
        margin-bottom: 14px;
        border: 1px solid #2f3440;
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.35);
    }
    .kral-header-title {
        font-size: 26px;
        font-weight: 900;
        color: #ffffff;
        margin-bottom: 4px;
    }
    .kral-header-sub {
        font-size: 13px;
        color: #b3b7c6;
    }

    /* Mini Info Bar */
    .kral-infobar {
        display: flex;
        gap: 18px;
        flex-wrap: wrap;
        margin-top: 6px;
        margin-bottom: 10px;
    }
    .kral-infobox {
        background: rgba(255, 255, 255, 0.02);
        border-radius: 10px;
        padding: 8px 14px;
        border: 1px solid #303542;
        min-width: 165px;
    }
    .kral-infobox-label {
        font-size: 11px;
        color: #b0b3c0;
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }
    .kral-infobox-value {
        display: block;
        margin-top: 2px;
        font-size: 16px;
        font-weight: 800;
        color: #ffffff;
    }
    .kral-infobox-sub {
        font-size: 11px;
        color: #9da1b3;
    }
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

# --- HEADER (B ŞIKKI – Hafif renkli kart + Para Birimi) ---
with st.container():
    st.markdown('<div class="kral-header">', unsafe_allow_html=True)
    c_title, c_toggle = st.columns([3, 1])
    with c_title:
        st.markdown(
            "<div class='kral-header-title'>🏦 Merter'in Varlık Yönetim Terminali</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<div class='kral-header-sub'>Toplam portföyünü tek ekranda izlemek için kişisel kontrol panelin.</div>",
            unsafe_allow_html=True,
        )
    with c_toggle:
        st.write("")
        GORUNUM_PB = st.radio("Para Birimi:", ["TRY", "USD"], horizontal=True)
    st.markdown("</div>", unsafe_allow_html=True)

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

# --- MENÜ (6 Buton) ---
selected = option_menu(
    menu_title=None,
    options=[
        "Dashboard",
        "Portföy",
        "İzleme",
        "Satışlar",
        "Haberler",
        "Ekle/Çıkar",
    ],
    icons=[
        "speedometer2",
        "pie-chart-fill",
        "eye",
        "receipt",
        "newspaper",
        "gear",
    ],
    menu_icon="cast",
    default_index=0,
    orientation="horizontal",
    styles={
        "container": {"padding": "0!important", "background-color": "#161616"},
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

        # Sektör
        sector = ""
        if "BIST" in pazar or "ABD" in pazar:
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info
                sector = info.get("sector", "Bilinmiyor")
            except Exception:
                sector = "Bilinmiyor"
        elif "FON" in pazar:
            sector = "Yatırım Fonu"
        elif "NAKIT" in pazar:
            sector = "Nakit Varlık"
        elif "EMTIA" in pazar:
            sector = "Emtia"

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

        curr, prev = 0, 0

        try:
            if "NAKIT" in pazar.upper():
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
            elif "FON" in pazar:
                curr, prev = get_tefas_data(kod)
            elif "Gram Gümüş" in kod:
                h = yf.Ticker("SI=F").history(period="5d")
                if not h.empty:
                    c = h["Close"].iloc[-1]
                    p = h["Close"].iloc[-2] if len(h) > 1 else c
                    curr = (c * USD_TRY) / 31.1035
                    prev = (p * USD_TRY) / 31.1035
            elif "Gram Altın" in kod:
                h = yf.Ticker("GC=F").history(period="5d")
                if not h.empty:
                    c = h["Close"].iloc[-1]
                    p = h["Close"].iloc[-2] if len(h) > 1 else c
                    curr = (c * USD_TRY) / 31.1035
                    prev = (p * USD_TRY) / 31.1035
            else:
                h = yf.Ticker(symbol).history(period="2d")
                if not h.empty:
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

        val_native = curr * adet
        cost_native = maliyet * adet
        daily_chg_native = (curr - prev) * adet

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
                "Sektör": sector,
            }
        )

    return pd.DataFrame(results)


master_df = run_analysis(portfoy_df, USD_TRY, GORUNUM_PB)
portfoy_only = master_df[master_df["Tip"] == "Portfoy"]
takip_only = master_df[master_df["Tip"] == "Takip"]


# --- GLOBAL INFO BAR ---

# --- GLOBAL INFO BAR ---
def render_kral_infobar(df, sym, gorunum_pb=None, usd_try_rate=None, timeframe=None, show_sparklines=False):
    """
    KRAL infobar:
    - Toplam Varlık
    - Son 24 Saat K/Z
    - Haftalık / Aylık / YTD (opsiyonel, timeframe ile)
    - İstenirse altında mini sparkline'lar
    """
    if df is None or df.empty:
        return

    # Mevcut görünümdeki toplam değer (df'nin para biriminde)
    total_value_view = df["Değer"].sum()
    daily_pnl = df["Gün. Kâr/Zarar"].sum()

    if daily_pnl > 0:
        daily_sign = "🟢"
    elif daily_pnl < 0:
        daily_sign = "🔴"
    else:
        daily_sign = "⚪"

    # Haftalık / Aylık / YTD metinleri (varsayılan)
    weekly_txt = "—"
    monthly_txt = "—"
    ytd_txt = "—"

    # Timeframe verisi geldiyse gerçek rakamlarla doldur
    if timeframe is not None:
        try:
            w_val, w_pct = timeframe.get("weekly", (0, 0))
            m_val, m_pct = timeframe.get("monthly", (0, 0))
            y_val, y_pct = timeframe.get("ytd", (0, 0))

            # Haftalık / Aylık / YTD değerler her zaman TRY bazlı tutuluyor
            # Görünüm USD ise, gösterirken USD'ye çeviriyoruz.
            show_sym = sym
            if gorunum_pb == "USD" and usd_try_rate:
                weekly_txt = f"{show_sym}{(w_val / usd_try_rate):,.0f} ({w_pct:+.2f}%)"
                monthly_txt = f"{show_sym}{(m_val / usd_try_rate):,.0f} ({m_pct:+.2f}%)"
                ytd_txt = f"{show_sym}{(y_val / usd_try_rate):,.0f} ({y_pct:+.2f}%)"
            else:
                weekly_txt = f"{show_sym}{w_val:,.0f} ({w_pct:+.2f}%)"
                monthly_txt = f"{show_sym}{m_val:,.0f} ({m_pct:+.2f}%)"
                ytd_txt = f"{show_sym}{y_val:,.0f} ({y_pct:+.2f}%)"
        except Exception:
            # Herhangi bir sorun olursa placeholder'da kalsın
            weekly_txt = "—"
            monthly_txt = "—"
            ytd_txt = "—"

    st.markdown(
        f"""
        <div class="kral-infobar">
            <div class="kral-infobox">
                <div class="kral-infobox-label">Toplam Varlık</div>
                <span class="kral-infobox-value">{sym}{total_value_view:,.0f}</span>
                <div class="kral-infobox-sub">Bu görünümdeki toplam varlık</div>
            </div>
            <div class="kral-infobox">
                <div class="kral-infobox-label">Son 24 Saat K/Z</div>
                <span class="kral-infobox-value">{daily_sign} {sym}{daily_pnl:,.0f}</span>
                <div class="kral-infobox-sub">Günlük toplam portföy hareketi</div>
            </div>
            <div class="kral-infobox">
                <div class="kral-infobox-label">Haftalık K/Z</div>
                <span class="kral-infobox-value">{weekly_txt}</span>
                <div class="kral-infobox-sub">Son 7 güne göre</div>
            </div>
            <div class="kral-infobox">
                <div class="kral-infobox-label">Aylık K/Z</div>
                <span class="kral-infobox-value">{monthly_txt}</span>
                <div class="kral-infobox-sub">Son 30 güne göre</div>
            </div>
            <div class="kral-infobox">
                <div class="kral-infobox-label">YTD Performans</div>
                <span class="kral-infobox-value">{ytd_txt}</span>
                <div class="kral-infobox-sub">Yılbaşından bugüne</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # İstenirse altına mini sparkline'lar
    if show_sparklines and timeframe is not None:
        try:
            spark_week = timeframe.get("spark_week", [])
            spark_month = timeframe.get("spark_month", [])
            spark_ytd = timeframe.get("spark_ytd", [])

            cols = st.columns(3)
            # Haftalık spark
            with cols[0]:
                st.caption("Haftalık Trend")
                fig_w = render_kpi_sparkline(spark_week)
                if fig_w is not None:
                    st.plotly_chart(fig_w, use_container_width=True)
            # Aylık spark
            with cols[1]:
                st.caption("Aylık Trend")
                fig_m = render_kpi_sparkline(spark_month)
                if fig_m is not None:
                    st.plotly_chart(fig_m, use_container_width=True)
            # YTD spark
            with cols[2]:
                st.caption("YTD Trend")
                fig_y = render_kpi_sparkline(spark_ytd)
                if fig_y is not None:
                    st.plotly_chart(fig_y, use_container_width=True)
        except Exception:
            # Grafiklerde sorun olsa bile infobar metinleri çalışmaya devam etsin
            pass


def render_kpi_sparkline(values):
    """
    KPI kartları altındaki mini sparkline grafikleri.
    Değer listesi (TRY bazlı) alır, minimalist çizgi döner.
    """
    if not values or len(values) < 2:
        return None

    df = pd.DataFrame({"idx": list(range(len(values))), "val": values})
    fig = px.line(df, x="idx", y="val")
    fig.update_traces(line=dict(width=2))
    fig.update_layout(
        height=70,
        margin=dict(l=0, r=0, t=0, b=0),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
    )
    return fig

# --- GÖRÜNÜM AYARI ---
TOTAL_SPOT_DEGER = portfoy_only["Değer"].sum()
st.markdown("---")
VARLIK_GORUNUMU = st.radio(
    "Varlık Gösterimi:",
    ["YÜZDE (%)", "TUTAR (₺/$)"],
    index=0,
    horizontal=True,
)
st.markdown("---")

# --- MENÜ İÇERİKLERİ ---

if selected == "Dashboard":
    if not portfoy_only.empty:
        # Dashboard genel portföy görünümü
        spot_only = portfoy_only

        # Toplam değer (seçili para biriminde)
        t_v = spot_only["Değer"].sum()
        t_p = spot_only["Top. Kâr/Zarar"].sum()
        t_maliyet = t_v - t_p
        pct = (t_p / t_maliyet * 100) if t_maliyet != 0 else 0

        # Gerçek Haftalık / Aylık / YTD KPI için tarihsel log güncelle
        kpi_timeframe = None
        try:
            if GORUNUM_PB == "TRY":
                total_try = float(t_v)
                total_usd = float(t_v / USD_TRY) if USD_TRY else 0.0
            else:
                total_usd = float(t_v)
                total_try = float(t_v * USD_TRY)

            # Günlük portföy logunu yaz (aynı günse data_loader içinde atlanıyor)
            write_portfolio_history(total_try, total_usd)

            history_df = read_portfolio_history()
            kpi_timeframe = get_timeframe_changes(history_df)
        except Exception:
            kpi_timeframe = None

        # INFO BAR (Toplam Varlık + Son 24 Saat + Haftalık/Aylık/YTD + Sparkline)
        render_kral_infobar(
            spot_only,
            sym,
            gorunum_pb=GORUNUM_PB,
            usd_try_rate=USD_TRY,
            timeframe=kpi_timeframe,
            show_sparklines=True,
        )

        # Eski 2 metric (Toplam Varlık + Genel K/Z) yine dursun
        c1, c2 = st.columns(2)
        c1.metric("Toplam Varlık", f"{sym}{t_v:,.0f}")
        c2.metric("Genel Kâr/Zarar", f"{sym}{t_p:,.0f}", delta=f"{pct:.2f}%")

        st.divider()

        # --- PAZAR DAĞILIMI ---
        st.subheader("📊 Pazarlara Göre Dağılım")
        dash_pazar = spot_only.groupby("Pazar", as_index=False).agg(
            {"Değer": "sum", "Top. Kâr/Zarar": "sum"}
        )
        render_pie_bar_charts(
            dash_pazar,
            "Pazar",
            all_tab=False,
            varlik_gorunumu=VARLIK_GORUNUMU,
            total_spot_deger=TOTAL_SPOT_DEGER,
        )

        st.divider()
        c_tree_1, c_tree_2 = st.columns([3, 1])
        with c_tree_1:
            st.subheader("🗺️ Portföy Isı Haritası")
        with c_tree_2:
            map_mode = st.radio(
                "Renklendirme:",
                ["Genel Kâr %", "Günlük Değişim %"],
                horizontal=True,
                key="heatmap_color_mode",
            )
            heat_scope = st.selectbox(
                "Kapsam:",
                ["Tümü", "BIST", "ABD", "FON", "Emtia", "Kripto", "Nakit"],
                index=0,
                key="heatmap_scope",
            )

        # Çalışılacak kopya
        heat_df = spot_only.copy()

        # Pazar filtresi (sadece görünüm, hesap mantığına karışmaz)
        if heat_scope != "Tümü":
            scope_map = {
                "BIST": "BIST",
                "ABD": "ABD",
                "FON": "FON",
                "Emtia": "EMTIA",
                "Kripto": "KRIPTO",
                "Nakit": "NAKIT",
            }
            target = scope_map.get(heat_scope, heat_scope).upper()
            heat_df = heat_df[
                heat_df["Pazar"].astype(str).str.upper().str.contains(target, na=False)
            ]

        if heat_df.empty:
            st.info("Seçilen kapsam için portföyde varlık bulunmuyor.")
        else:
            # Renk kolonu: Top. % veya Gün. %
            color_col = "Top. %"
            heat_df["Gün. %"] = 0.0
            safe_val = heat_df["Değer"] - heat_df["Gün. Kâr/Zarar"]
            non_zero = safe_val != 0
            heat_df.loc[non_zero, "Gün. %"] = (
                heat_df.loc[non_zero, "Gün. Kâr/Zarar"] / safe_val[non_zero]
            ) * 100

            if map_mode == "Günlük Değişim %":
                color_col = "Gün. %"

            # Daha yumuşak renk skalası için simetrik aralık
            vmax = float(heat_df[color_col].max())
            vmin = float(heat_df[color_col].min())
            abs_max = max(abs(vmax), abs(vmin)) if (vmax or vmin) else 0

            fig = px.treemap(
                heat_df,
                path=[px.Constant("Portföy"), "Kod"],
                values="Değer",
                color=color_col,
                custom_data=["Değer", "Top. Kâr/Zarar", color_col],
                color_continuous_scale="RdYlGn",
                color_continuous_midpoint=0,
            )
            if abs_max > 0:
                fig.update_coloraxes(cmin=-abs_max, cmax=abs_max)

            fig.update_traces(
                textinfo="label+value+percent entry",
                texttemplate="<b>%{label}</b><br>%{customdata[0]:,.0f}<br><b>%{customdata[2]:.2f}%</b>",
                textposition="middle center",
                textfont=dict(size=20, family="Arial Black"),
            )
            fig.update_layout(
                margin=dict(t=0, l=0, r=0, b=0),
                coloraxis_colorbar=dict(title="Top. / Gün. %"),
            )
            st.plotly_chart(fig, use_container_width=True)

        st.divider()

        # --- TARİHSEL GRAFİK EN ALTA ---
        st.subheader("📈 Tarihsel Portföy Değeri (60 Gün)")
        hist_chart = get_historical_chart(spot_only, USD_TRY, GORUNUM_PB)
        if hist_chart:
            st.plotly_chart(hist_chart, use_container_width=True)
        else:
            st.info("Tarihsel veri hazırlanıyor...")
    else:
        st.info("Boş.")

elif selected == "Portföy":
    st.subheader("📊 Portföy Görünümü")

    tab_tumu, tab_bist, tab_abd, tab_fon, tab_emtia, tab_kripto, tab_nakit = st.tabs(
        ["Tümü", "BIST", "ABD", "FON", "Emtia", "Kripto", "Nakit"]
    )

    # Tümü
    with tab_tumu:
        render_kral_infobar(portfoy_only, sym)
        render_pazar_tab(
            portfoy_only,
            "Tümü",
            sym,
            USD_TRY,
            VARLIK_GORUNUMU,
            TOTAL_SPOT_DEGER,
        )
        st.subheader("📈 Tarihsel Değer - Tümü (60 Gün)")
        hist_chart = get_historical_chart(portfoy_only, USD_TRY, GORUNUM_PB)
        if hist_chart:
            st.plotly_chart(hist_chart, use_container_width=True)

    # BIST
    with tab_bist:
        bist_df = portfoy_only[
            portfoy_only["Pazar"].astype(str).str.contains(
                "BIST", case=False, na=False
            )
        ]

        # Haftalık / Aylık / YTD + sparkline için tarihsel log
        timeframe_bist = None
        if not bist_df.empty:
            try:
                t_v = float(bist_df["Değer"].sum())
                if GORUNUM_PB == "TRY":
                    total_try = t_v
                    total_usd = t_v / USD_TRY if USD_TRY else 0.0
                else:
                    total_usd = t_v
                    total_try = t_v * USD_TRY

                write_history_bist(total_try, total_usd)
                hist_bist = read_history_bist()
                timeframe_bist = get_timeframe_changes(hist_bist)
            except Exception:
                timeframe_bist = None

        render_kral_infobar(
            bist_df,
            sym,
            gorunum_pb=GORUNUM_PB,
            usd_try_rate=USD_TRY,
            timeframe=timeframe_bist,
            show_sparklines=True,
        )

        render_pazar_tab(
            portfoy_only,
            "BIST",
            sym,
            USD_TRY,
            VARLIK_GORUNUMU,
            TOTAL_SPOT_DEGER,
        )
        st.subheader("📈 Tarihsel Değer - BIST (60 Gün)")
        hist_chart = get_historical_chart(bist_df, USD_TRY, GORUNUM_PB)
        if hist_chart:
            st.plotly_chart(hist_chart, use_container_width=True)


    # ABD
    with tab_abd:
        abd_df = portfoy_only[
            portfoy_only["Pazar"].astype(str).str.contains("ABD", case=False, na=False)
        ]

        timeframe_abd = None
        if not abd_df.empty:
            try:
                t_v = float(abd_df["Değer"].sum())
                if GORUNUM_PB == "TRY":
                    total_try = t_v
                    total_usd = t_v / USD_TRY if USD_TRY else 0.0
                else:
                    total_usd = t_v
                    total_try = t_v * USD_TRY

                write_history_abd(total_try, total_usd)
                hist_abd = read_history_abd()
                timeframe_abd = get_timeframe_changes(hist_abd)
            except Exception:
                timeframe_abd = None

        render_kral_infobar(
            abd_df,
            sym,
            gorunum_pb=GORUNUM_PB,
            usd_try_rate=USD_TRY,
            timeframe=timeframe_abd,
            show_sparklines=True,
        )

        render_pazar_tab(
            portfoy_only,
            "ABD",
            sym,
            USD_TRY,
            VARLIK_GORUNUMU,
            TOTAL_SPOT_DEGER,
        )
        st.subheader("📈 Tarihsel Değer - ABD (60 Gün)")
        hist_chart = get_historical_chart(abd_df, USD_TRY, GORUNUM_PB)
        if hist_chart:
            st.plotly_chart(hist_chart, use_container_width=True)


    # FON
    with tab_fon:
        fon_df = portfoy_only[
            portfoy_only["Pazar"].astype(str).str.contains("FON", case=False, na=False)
        ]

        timeframe_fon = None
        if not fon_df.empty:
            try:
                t_v = float(fon_df["Değer"].sum())
                if GORUNUM_PB == "TRY":
                    total_try = t_v
                    total_usd = t_v / USD_TRY if USD_TRY else 0.0
                else:
                    total_usd = t_v
                    total_try = t_v * USD_TRY

                write_history_fon(total_try, total_usd)
                hist_fon = read_history_fon()
                timeframe_fon = get_timeframe_changes(hist_fon)
            except Exception:
                timeframe_fon = None

        render_kral_infobar(
            fon_df,
            sym,
            gorunum_pb=GORUNUM_PB,
            usd_try_rate=USD_TRY,
            timeframe=timeframe_fon,
            show_sparklines=True,
        )

        render_pazar_tab(
            portfoy_only,
            "FON",
            sym,
            USD_TRY,
            VARLIK_GORUNUMU,
            TOTAL_SPOT_DEGER,
        )
        st.subheader("📈 Tarihsel Değer - FON (60 Gün)")
        hist_chart = get_historical_chart(fon_df, USD_TRY, GORUNUM_PB)
        if hist_chart:
            st.plotly_chart(hist_chart, use_container_width=True)


    # EMTIA
    with tab_emtia:
        emtia_df = portfoy_only[
            portfoy_only["Pazar"].astype(str).str.contains(
                "EMTIA", case=False, na=False
            )
        ]

        timeframe_emtia = None
        if not emtia_df.empty:
            try:
                t_v = float(emtia_df["Değer"].sum())
                if GORUNUM_PB == "TRY":
                    total_try = t_v
                    total_usd = t_v / USD_TRY if USD_TRY else 0.0
                else:
                    total_usd = t_v
                    total_try = t_v * USD_TRY

                write_history_emtia(total_try, total_usd)
                hist_emtia = read_history_emtia()
                timeframe_emtia = get_timeframe_changes(hist_emtia)
            except Exception:
                timeframe_emtia = None

        render_kral_infobar(
            emtia_df,
            sym,
            gorunum_pb=GORUNUM_PB,
            usd_try_rate=USD_TRY,
            timeframe=timeframe_emtia,
            show_sparklines=True,
        )

        render_pazar_tab(
            portfoy_only,
            "EMTIA",
            sym,
            USD_TRY,
            VARLIK_GORUNUMU,
            TOTAL_SPOT_DEGER,
        )
        st.subheader("📈 Tarihsel Değer - Emtia (60 Gün)")
        hist_chart = get_historical_chart(emtia_df, USD_TRY, GORUNUM_PB)
        if hist_chart:
            st.plotly_chart(hist_chart, use_container_width=True)


    # KRIPTO
    with tab_kripto:
        kripto_df = portfoy_only[
            portfoy_only["Pazar"].astype(str).str.contains(
                "KRIPTO", case=False, na=False
            )
        ]
        render_kral_infobar(kripto_df, sym)
        render_pazar_tab(
            portfoy_only,
            "KRIPTO",
            sym,
            USD_TRY,
            VARLIK_GORUNUMU,
            TOTAL_SPOT_DEGER,
        )
        st.subheader("📈 Tarihsel Değer - Kripto (60 Gün)")
        hist_chart = get_historical_chart(kripto_df, USD_TRY, GORUNUM_PB)
        if hist_chart:
            st.plotly_chart(hist_chart, use_container_width=True)

    # NAKIT
    with tab_nakit:
        nakit_df = portfoy_only[
            portfoy_only["Pazar"].astype(str).str.contains(
                "NAKIT", case=False, na=False
            )
        ]

        timeframe_nakit = None
        if not nakit_df.empty:
            try:
                t_v = float(nakit_df["Değer"].sum())
                if GORUNUM_PB == "TRY":
                    total_try = t_v
                    total_usd = t_v / USD_TRY if USD_TRY else 0.0
                else:
                    total_usd = t_v
                    total_try = t_v * USD_TRY

                write_history_nakit(total_try, total_usd)
                hist_nakit = read_history_nakit()
                timeframe_nakit = get_timeframe_changes(hist_nakit)
            except Exception:
                timeframe_nakit = None

        render_kral_infobar(
            nakit_df,
            sym,
            gorunum_pb=GORUNUM_PB,
            usd_try_rate=USD_TRY,
            timeframe=timeframe_nakit,
            show_sparklines=True,
        )

        render_pazar_tab(
            portfoy_only,
            "NAKIT",
            sym,
            USD_TRY,
            VARLIK_GORUNUMU,
            TOTAL_SPOT_DEGER,
        )
        st.subheader("📈 Tarihsel Değer - Nakit (60 Gün)")
        hist_chart = get_historical_chart(nakit_df, USD_TRY, GORUNUM_PB)
        if hist_chart:
            st.plotly_chart(hist_chart, use_container_width=True)

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
    st.subheader("👁️ İzleme Listesi")
    if not takip_only.empty:
        st.dataframe(
            styled_dataframe(takip_only),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("İzleme listesi boş.")

elif selected == "Satışlar":
    st.subheader("🧾 Satış Geçmişi")
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

    # EKLE
    with tab1:
        pazar = st.selectbox("Pazar", list(MARKET_DATA.keys()))
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
                portfoy_df = pd.concat([portfoy_df, new_row], ignore_index=True)
                save_data_to_sheet(portfoy_df)
                st.success("Eklendi!")
                time.sleep(1)
                st.rerun()

    # DÜZENLE
    with tab2:
        if not portfoy_df.empty:
            s = st.selectbox("Seç", portfoy_df["Kod"].unique())
            if s:
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

    # SİL
    with tab3:
        if not portfoy_df.empty:
            s = st.selectbox("Silinecek", portfoy_df["Kod"].unique(), key="del")
            if st.button("🗑️ Sil"):
                portfoy_df = portfoy_df[portfoy_df["Kod"] != s]
                save_data_to_sheet(portfoy_df)
                st.success("Silindi!")
                time.sleep(1)
                st.rerun()
