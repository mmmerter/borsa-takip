import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import yfinance as yf
import pandas as pd

from utils import styled_dataframe
from data_loader import get_tefas_data


# --------------------------------------------------------------------
#  ORTAK PIE + BAR CHART
#  - %1 altını "Diğer" altında toplar
#  - all_tab=True ise (Tümü sekmesi) sadece %5 üzeri dilimlerde yazı gösterir
#  - diğer sekmelerde tüm dilimlerde yazı + yüzde gösterilir (kalın font)
# --------------------------------------------------------------------
def render_pie_bar_charts(df: pd.DataFrame, group_col: str, all_tab: bool = False):
    if df.empty or "Değer" not in df.columns:
        return

    # Aynı grup isimlerini birleştir (Kod/Pazar bazlı toplam)
    agg_cols = {"Değer": "sum"}
    has_pnl = "Top. Kâr/Zarar" in df.columns
    if has_pnl:
        agg_cols["Top. Kâr/Zarar"] = "sum"

    grouped = df.groupby(group_col, as_index=False).agg(agg_cols)

    total_val = grouped["Değer"].sum()
    if total_val <= 0:
        plot_df = grouped.copy()
    else:
        # Yüzde hesabı
        grouped["_pct"] = grouped["Değer"] / total_val * 100

        major = grouped[grouped["_pct"] >= 1].copy()
        minor = grouped[grouped["_pct"] < 1].copy()

        if not minor.empty and not major.empty:
            other_row = {
                group_col: "Diğer",
                "Değer": minor["Değer"].sum(),
            }
            if has_pnl:
                other_row["Top. Kâr/Zarar"] = minor["Top. Kâr/Zarar"].sum()

            major = pd.concat(
                [major, pd.DataFrame([other_row])], ignore_index=True
            )
            plot_df = major.drop(columns=["_pct"], errors="ignore")
        else:
            plot_df = grouped.drop(columns=["_pct"], errors="ignore")

    # Plot df üzerinde tekrar yüzde hesapla (Diğer dahil)
    total_plot_val = plot_df["Değer"].sum()
    if total_plot_val > 0:
        plot_df["_pct"] = plot_df["Değer"] / total_plot_val * 100
    else:
        plot_df["_pct"] = 0

    # Yazı eşiği:
    # - Tümü sekmesi (all_tab=True)    -> sadece %5 ve üstü
    # - Diğer tüm sekmeler (all_tab=False) -> hepsi
    threshold = 5.0 if all_tab else 0.0

    texts = []
    for _, r in plot_df.iterrows():
        if r["_pct"] >= threshold:
            texts.append(f"{r[group_col]} {r['_pct']:.1f}%")
        else:
            texts.append("")  # küçük dilimde yazı yok

    # Pasta daha geniş, bar biraz daha dar
    c_pie, c_bar = st.columns([4, 3])

    # ====================
    # PIE CHART
    # ====================
    pie_fig = px.pie(
        plot_df,
        values="Değer",
        names=group_col,
        hole=0.40,
    )
    pie_fig.update_traces(
        text=texts,
        textinfo="text",
        textfont=dict(
            size=18,
            color="white",
            family="Arial Black",
        ),
    )
    pie_fig.update_layout(
        legend=dict(font=dict(size=14)),
        margin=dict(t=40, l=0, r=0, b=80),
    )
    c_pie.plotly_chart(pie_fig, use_container_width=True)

    # ====================
    # BAR CHART
    # ====================
    if has_pnl:
        bar_fig = px.bar(
            plot_df.sort_values("Değer"),
            x=group_col,
            y="Değer",
            color="Top. Kâr/Zarar",
            text="Değer",
        )
    else:
        bar_fig = px.bar(
            plot_df.sort_values("Değer"),
            x=group_col,
            y="Değer",
            text="Değer",
        )

    bar_fig.update_traces(
        texttemplate="%{text:,.0f}",
        textposition="outside",
        textfont=dict(
            size=14,
            color="white",
            family="Arial Black",
        ),
    )
    bar_fig.update_layout(
        xaxis=dict(tickfont=dict(size=14)),
        yaxis=dict(tickfont=dict(size=14)),
        legend=dict(font=dict(size=14)),
        margin=dict(t=40, l=20, r=20, b=40),
    )
    c_bar.plotly_chart(bar_fig, use_container_width=True)


# --------------------------------------------------------------------
#  TARİHSEL GRAFİK (Şimdilik Stub)
# --------------------------------------------------------------------
def get_historical_chart(df_portfolio: pd.DataFrame, usd_try: float):
    return None


# --------------------------------------------------------------------
#  SEKME BAZLI PAZAR EKRANI
# --------------------------------------------------------------------
def render_pazar_tab(df, filter_key, symb, usd_try):
    if df.empty:
        return st.info("Veri yok.")

    if filter_key == "VADELI":
        sub = df[df["Pazar"].str.contains("VADELI", na=False)]
    else:
        sub = df[df["Pazar"].str.contains(filter_key, na=False)]

    if sub.empty:
        return st.info(f"{filter_key} yok.")

    total_val = sub["Değer"].sum()
    total_pnl = sub["Top. Kâr/Zarar"].sum()

    col1, col2 = st.columns(2)

    label = "Toplam PNL" if filter_key == "VADELI" else "Toplam Varlık"
    col1.metric(label, f"{symb}{total_val:,.0f}")

    if filter_key == "VADELI":
        col2.metric(
            "Toplam Kâr/Zarar",
            f"{symb}{total_pnl:,.0f}",
            delta=f"{symb}{total_pnl:,.0f}",
        )
    else:
        total_cost = (sub["Değer"] - sub["Top. Kâr/Zarar"]).sum()
        pct = (total_pnl / total_cost * 100) if total_cost != 0 else 0
        col2.metric(
            "Toplam Kâr/Zarar",
            f"{symb}{total_pnl:,.0f}",
            delta=f"%{pct:.2f}",
        )

    st.divider()

    if filter_key != "VADELI":
        # BIST / ABD / FON / Emtia / Kripto / Nakit -> all_tab=False (tümü yazılı)
        render_pie_bar_charts(sub, "Kod", all_tab=False)

    st.dataframe(
        styled_dataframe(sub),
        use_container_width=True,
        hide_index=True,
    )


# --------------------------------------------------------------------
#  DETAY SAYFASI
# --------------------------------------------------------------------
def render_detail_view(symbol, pazar):
    st.markdown(f"### 🔎 {symbol} Detaylı Analizi")

    if "FON" in pazar:
        price, _ = get_tefas_data(symbol)
        st.metric(f"{symbol} Son Fiyat", f"₺{price:,.6f}")
        st.info("Yatırım fonu grafik desteği kısıtlıdır.")
        return

    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="2y")

        if hist.empty:
            st.warning("Grafik verisi yok.")
            return

        fig = go.Figure(
            data=[
                go.Candlestick(
                    x=hist.index,
                    open=hist["Open"],
                    high=hist["High"],
                    low=hist["Low"],
                    close=hist["Close"],
                )
            ]
        )

        fig.update_layout(
            title=f"{symbol} Fiyat Grafiği",
            template="plotly_dark",
            yaxis_title="Fiyat",
            height=600,
        )
        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Hata: {e}")
