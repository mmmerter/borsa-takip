import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import yfinance as yf
import pandas as pd

from utils import styled_dataframe, get_yahoo_symbol
from data_loader import get_tefas_data


def render_pie_bar_charts(
    df: pd.DataFrame,
    group_col: str,
    all_tab: bool = False,
    varlik_gorunumu: str = "YÜZDE (%)",
    total_spot_deger: float = 0.0,
) -> None:
    """
    Modern donut + bar kombinasyonu.

    - df: En azından [group_col, "Değer"] kolonlarını içeren dataframe.
    - group_col: Gruplama yapılacak kolon (ör: "Pazar" veya "Kod").
    - all_tab: Eğer True ise yüzde hesaplarında total_spot_deger kullanılabilir.
    - varlik_gorunumu: "YÜZDE (%)" veya "TUTAR (₺/$)".
    - total_spot_deger: Toplam spot portföy değeri (Tümü sekmesinde kullanılıyor).
    """
    if df is None or df.empty or "Değer" not in df.columns:
        st.info("Grafik üretmek için veri bulunamadı.")
        return

    # Gruplama
    agg = {"Değer": "sum"}
    if "Top. Kâr/Zarar" in df.columns:
        agg["Top. Kâr/Zarar"] = "sum"

    grouped = df.groupby(group_col, as_index=False).agg(agg)
    grouped = grouped.sort_values("Değer", ascending=False)

    # Yüzde hesaplama
    if all_tab and total_spot_deger and total_spot_deger > 0:
        denom = float(total_spot_deger)
    else:
        denom = float(grouped["Değer"].sum())

    grouped["Pay (%)"] = grouped["Değer"] / denom * 100 if denom > 0 else 0

    # Metin kolonları
    label_col = group_col
    grouped["Label"] = grouped[label_col].astype(str)

    # Donut + Bar layout
    col_pie, col_bar = st.columns([1.2, 1])

    # --- Donut (Pie) ---
    with col_pie:
        fig_pie = go.Figure(
            data=[
                go.Pie(
                    labels=grouped["Label"],
                    values=grouped["Değer"],
                    hole=0.60,
                    hovertemplate="<b>%{label}</b><br>Değer: %{value:,.0f}<br>Pay: %{percent:.1%}<extra></extra>",
                )
            ]
        )
        fig_pie.update_layout(
            margin=dict(t=0, b=0, l=0, r=0),
            showlegend=True,
            legend_title=group_col,
            annotations=[
                dict(
                    text="TOPLAM",
                    x=0.5,
                    y=0.52,
                    font=dict(size=11, color="#bfc3d4"),
                    showarrow=False,
                ),
                dict(
                    text=f"{grouped['Değer'].sum():,.0f}",
                    x=0.5,
                    y=0.42,
                    font=dict(size=16, color="#ffffff"),
                    showarrow=False,
                ),
            ],
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    # --- Bar (Dağılım) ---
    with col_bar:
        fig_bar = go.Figure()
        fig_bar.add_trace(
            go.Bar(
                x=grouped["Değer"],
                y=grouped["Label"],
                orientation="h",
                hovertemplate="<b>%{y}</b><br>Değer: %{x:,.0f}<extra></extra>",
            )
        )
        fig_bar.update_layout(
            margin=dict(t=10, b=0, l=0, r=0),
            yaxis=dict(autorange="reversed"),
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    # Altında özet tablo
    disp = grouped[[label_col, "Değer", "Pay (%)"]].copy()
    disp.rename(columns={label_col: group_col}, inplace=True)
    disp["Pay (%)"] = disp["Pay (%)"].round(2)
    st.dataframe(styled_dataframe(disp), use_container_width=True, hide_index=True)


def render_pazar_tab(
    df: pd.DataFrame,
    filter_key: str,
    sym: str,
    usd_try_rate: float,
    varlik_gorunumu: str,
    total_spot_deger: float,
) -> None:
    """
    Portföy sayfasındaki her pazar sekmesi için:
    - Üstte pazar özeti metric'ler
    - Ortada donut + bar grafikleri
    - Altta detay tablo
    """

    if df is None or df.empty:
        st.info("Bu görünüm için portföyde varlık bulunmuyor.")
        return

    # Filtreleme
    if filter_key == "Tümü":
        sub = df.copy()
    else:
        pazar_str = df["Pazar"].astype(str)
        sub = df[pazar_str.str.contains(filter_key, case=False, na=False)].copy()

    is_vadeli = filter_key.upper().startswith("VADEL")
    if sub.empty:
        st.info(f"{filter_key} için portföyde varlık bulunmuyor.")
        return

    # Özet rakamlar
    total_val = float(sub["Değer"].sum())
    total_pnl = float(sub["Top. Kâr/Zarar"].sum()) if "Top. Kâr/Zarar" in sub.columns else 0.0
    base = total_val - total_pnl
    pnl_pct = (total_pnl / base * 100) if base != 0 else 0.0
    daily_pnl = float(sub["Gün. Kâr/Zarar"].sum()) if "Gün. Kâr/Zarar" in sub.columns else 0.0

    c1, c2, c3 = st.columns(3)
    c1.metric("Toplam Değer", f"{sym}{total_val:,.0f}")
    c2.metric("Toplam K/Z", f"{sym}{total_pnl:,.0f}", delta=f"{pnl_pct:.2f}%")
    c3.metric("Günlük K/Z", f"{sym}{daily_pnl:,.0f}")

    st.divider()

    # Donut + bar (vadeli dışındakiler için)
    if not is_vadeli:
        render_pie_bar_charts(
            sub,
            group_col="Kod",
            all_tab=(filter_key == "Tümü"),
            varlik_gorunumu=varlik_gorunumu,
            total_spot_deger=total_spot_deger,
        )

    # Detay tablo
    disp = sub.copy()
    if varlik_gorunumu == "YÜZDE (%)" and not is_vadeli:
        # Değer'i yüzdeye çevir
        disp.rename(columns={"Değer": "Tutar"}, inplace=True)
        denom = total_spot_deger if filter_key == "Tümü" else float(sub["Değer"].sum())
        if denom > 0:
            disp["Değer"] = disp["Tutar"] / denom * 100
        else:
            disp["Değer"] = 0.0

    st.dataframe(styled_dataframe(disp), use_container_width=True, hide_index=True)


def render_detail_view(symbol: str, pazar: str) -> None:
    """
    İleride detay sayfası eklemek için placeholder.
    Şu an sadece seçilen kodu gösteriyor.
    """
    st.write(f"Detay görünüm: {symbol} ({pazar})")


def get_historical_chart(df: pd.DataFrame, usd_try_rate: float, pb: str):
    """
    Son 60 güne ait yaklaşık tarihsel portföy değeri grafiği oluşturur.
    - Her varlık için Yahoo Finance (veya ons altın/gümüş, fon vs.) verisi çekilir.
    - Lot/adet ile çarpılır.
    - Seçilen para birimine (pb: TRY / USD) göre çevrilir.
    - Hepsi toplanıp tek zaman serisi olarak çizilir.
    """
    if df is None or df.empty:
        return None

    all_series = []

    for _, row in df.iterrows():
        kod = str(row.get("Kod", ""))
        pazar = str(row.get("Pazar", ""))
        adet = float(row.get("Adet", 0) or 0)

        if adet == 0 or not kod:
            continue

        pazar_upper = pazar.upper()
        kod_upper = kod.upper()

        # TRY mi USD mi?
        if (
            "BIST" in pazar_upper
            or "TL" in kod_upper
            or "FON" in pazar_upper
            or "EMTIA" in pazar_upper
            or "NAKIT" in pazar_upper
        ):
            asset_currency = "TRY"
        else:
            asset_currency = "USD"

        prices = None

        try:
            # Nakitler
            if "NAKIT" in pazar_upper:
                today = pd.Timestamp.today().normalize()
                if kod_upper == "TL":
                    prices = pd.Series([1.0], index=[today])
                elif kod_upper == "USD":
                    prices = pd.Series([usd_try_rate], index=[today])
                else:
                    prices = pd.Series([1.0], index=[today])

            # Fonlar: sabit seri
            elif "FON" in pazar_upper:
                price, _ = get_tefas_data(kod)
                if price and price > 0:
                    idx = pd.date_range(
                        end=pd.Timestamp.today().normalize(), periods=30, freq="D"
                    )
                    prices = pd.Series(price, index=idx)

            # Gram Gümüş
            elif "GRAM GÜMÜŞ" in kod_upper:
                h = yf.Ticker("SI=F").history(period="60d", interval="1d")
                if not h.empty:
                    s = (h["Close"] * usd_try_rate) / 31.1035
                    prices = s

            # Gram Altın
            elif "GRAM ALTIN" in kod_upper:
                h = yf.Ticker("GC=F").history(period="60d", interval="1d")
                if not h.empty:
                    s = (h["Close"] * usd_try_rate) / 31.1035
                    prices = s

            # Hisse / Kripto
            else:
                symbol = get_yahoo_symbol(kod, pazar)
                h = yf.Ticker(symbol).history(period="60d", interval="1d")
                if not h.empty:
                    prices = h["Close"]

        except Exception:
            prices = None

        if prices is None or prices.empty:
            continue

        # 🔧 TZ-FIX: timezone'lu index varsa timezone'u sıfırla
        prices.index = pd.to_datetime(prices.index).tz_localize(None)

        # TRY / USD çevirisi
        if pb == "TRY":
            if asset_currency == "USD":
                values = prices * adet * usd_try_rate
            else:
                values = prices * adet
        else:  # pb == "USD"
            if asset_currency == "TRY":
                values = prices * adet / usd_try_rate
            else:
                values = prices * adet

        all_series.append(values.rename("Değer"))

    if not all_series:
        return None

    # Tüm serileri hizalayıp topla
    portfolio_series = pd.concat(all_series, axis=1).sum(axis=1)
    portfolio_series = portfolio_series.sort_index()
    portfolio_series = portfolio_series[-60:]  # son 60 gün

    hist_df = portfolio_series.reset_index()
    hist_df.columns = ["Tarih", "ToplamDeğer"]

    fig = px.line(
        hist_df,
        x="Tarih",
        y="ToplamDeğer",
        title="Portföy Değeri (60 Gün)",
    )
    fig.update_layout(
        margin=dict(t=30, b=0, l=0, r=0),
        xaxis_title="Tarih",
        yaxis_title=f"Portföy ({'₺' if pb == 'TRY' else '$'})",
    )
    return fig
