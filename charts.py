import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import yfinance as yf
import pandas as pd

from utils import styled_dataframe
from data_loader import get_tefas_data


def render_pie_bar_charts(df: pd.DataFrame, group_col: str):
    """Pastayı ve bar chart'ı tek yerden üretir."""
    if df.empty or "Değer" not in df.columns:
        return

    c_p, c_b = st.columns(2)

    pie_fig = px.pie(
        df,
        values="Değer",
        names=group_col,
        hole=0.4,
    )
    c_p.plotly_chart(pie_fig, use_container_width=True)

    if "Top. Kâr/Zarar" in df.columns:
        bar_fig = px.bar(
            df.sort_values("Değer"),
            x=group_col,
            y="Değer",
            color="Top. Kâr/Zarar",
        )
    else:
        bar_fig = px.bar(
            df.sort_values("Değer"),
            x=group_col,
            y="Değer",
        )
    c_b.plotly_chart(bar_fig, use_container_width=True)


def get_historical_chart(df_portfolio: pd.DataFrame, usd_try: float):
    """
    Şimdilik stub: Hata vermemesi için None dönüyor.
    KRAL'da da böyleydi, aynen koruyoruz.
    """
    return None


def render_pazar_tab(df, filter_key, symb, usd_try):
    if df.empty:
        return st.info("Veri yok.")

    if filter_key == "VADELI":
        sub = df[df["Pazar"].str.contains("VADELI", na=False)]
    else:
        sub = df[df["Pazar"].str.contains(filter_key, na=False)]

    if sub.empty:
        return st.info(f"{filter_key} yok.")

    t_val = sub["Değer"].sum()
    t_pl = sub["Top. Kâr/Zarar"].sum()

    c1, c2 = st.columns(2)
    lbl = "Toplam PNL" if filter_key == "VADELI" else "Toplam Varlık"
    c1.metric(lbl, f"{symb}{t_val:,.0f}")

    if filter_key == "VADELI":
        # Vadeli için maliyet bilgisi ayrı tutulmadığından delta TL bazlı bırakıldı
        c2.metric(
            "Toplam Kâr/Zarar",
            f"{symb}{t_pl:,.0f}",
            delta=f"{symb}{t_pl:,.0f}",
        )
    else:
        # Spot sekmelerde (BIST, ABD, FON, Emtia, Kripto, Nakit) delta yüzde
        total_cost = (sub["Değer"] - sub["Top. Kâr/Zarar"]).sum()
        total_pct = (t_pl / total_cost * 100) if total_cost != 0 else 0
        c2.metric(
            "Toplam Kâr/Zarar",
            f"{symb}{t_pl:,.0f}",
            delta=f"%{total_pct:,.2f}",
        )

    st.divider()

    if filter_key != "VADELI":
        # Sekmeye göre (BIST, ABD, FON vb.) varlık bazlı grafik
        render_pie_bar_charts(sub, "Kod")

        if filter_key not in ["FON", "EMTIA", "NAKIT"]:
            try:
                h = get_historical_chart(sub, usd_try)
                if h is not None:
                    st.line_chart(h)
            except Exception:
                st.warning("Tarihsel grafik yüklenemedi.")

    st.dataframe(
        styled_dataframe(sub),
        use_container_width=True,
        hide_index=True,
    )


def render_detail_view(symbol, pazar):
    st.markdown(f"### 🔎 {symbol} Detaylı Analizi")

    if "FON" in pazar:
        price, _ = get_tefas_data(symbol)
        st.metric(f"{symbol} Son Fiyat", f"₺{price:,.6f}")
        st.info("Yatırım fonları için anlık grafik desteği TEFAS kaynaklı sınırlıdır.")
        return

    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="2y")

        if not hist.empty:
            fig = go.Figure(
                data=[
                    go.Candlestick(
                        x=hist.index,
                        open=hist["Open"],
                        high=hist["High"],
                        low=hist["Low"],
                        close=hist["Close"],
                        name=symbol,
                    )
                ]
            )
            fig.update_layout(
                title=f"{symbol} Fiyat Grafiği",
                yaxis_title="Fiyat",
                template="plotly_dark",
                height=600,
                xaxis=dict(
                    rangeselector=dict(
                        buttons=list(
                            [
                                dict(
                                    count=1,
                                    label="1A",
                                    step="month",
                                    stepmode="backward",
                                ),
                                dict(
                                    count=3,
                                    label="3A",
                                    step="month",
                                    stepmode="backward",
                                ),
                                dict(
                                    count=6,
                                    label="6A",
                                    step="month",
                                    stepmode="backward",
                                ),
                                dict(
                                    count=1,
                                    label="YTD",
                                    step="year",
                                    stepmode="todate",
                                ),
                                dict(
                                    count=1,
                                    label="1Y",
                                    step="year",
                                    stepmode="backward",
                                ),
                                dict(step="all", label="TÜMÜ"),
                            ]
                        ),
                        bgcolor="#262730",
                        font=dict(color="white"),
                    ),
                    rangeslider=dict(visible=False),
                    type="date",
                ),
            )
            st.plotly_chart(fig, use_container_width=True)

            info = ticker.info
            market_cap = info.get("marketCap", "N/A")
            if isinstance(market_cap, int):
                market_cap = f"{market_cap:,.0f}"

            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Sektör", info.get("sector", "-"))
            c2.metric("F/K", info.get("trailingPE", "-"))
            c3.metric("Piyasa Değeri", market_cap)
            c4.metric("52H Yüksek", info.get("fiftyTwoWeekHigh", "-"))
            c5.metric("52H Düşük", info.get("fiftyTwoWeekLow", "-"))
        else:
            st.warning("Grafik verisi bulunamadı.")
    except Exception as e:
        st.error(f"Veri çekilemedi: {e}")
