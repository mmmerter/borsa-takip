import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import yfinance as yf
import pandas as pd

from utils import styled_dataframe, get_yahoo_symbol, get_pazar_icon, get_label_with_icon, get_logo_html
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

    # Metin kolonları - pazar ikonları ve logolar ekle
    label_col = group_col
    if group_col == "Pazar":
        # Pazar kolonu için ikonlar ekle
        grouped["Label"] = grouped[label_col].apply(lambda x: get_label_with_icon(str(x), str(x)))
    else:
        grouped["Label"] = grouped[label_col].astype(str)
        # Kod kolonu için logo URL'lerini hazırla (bar chart için)
        if "Pazar" in df.columns:
            grouped = grouped.merge(
                df[[group_col, "Pazar"]].drop_duplicates(),
                on=group_col,
                how="left"
            )
        else:
            grouped["Pazar"] = ""

    # Modern renk paleti - profesyonel ve tutarlı
    modern_colors = [
        "#6366f1",  # Indigo
        "#8b5cf6",  # Purple
        "#ec4899",  # Pink
        "#f59e0b",  # Amber
        "#10b981",  # Emerald
        "#3b82f6",  # Blue
        "#f97316",  # Orange
        "#06b6d4",  # Cyan
        "#84cc16",  # Lime
        "#ef4444",  # Red
    ]
    
    # Donut + Bar layout
    col_pie, col_bar = st.columns([1.2, 1])

    # --- Donut (Pie) - Modern ve Profesyonel ---
    with col_pie:
        fig_pie = go.Figure(
            data=[
                go.Pie(
                    labels=grouped["Label"],
                    values=grouped["Değer"],
                    hole=0.65,
                    marker=dict(
                        colors=modern_colors[:len(grouped)],
                        line=dict(color="#0e1117", width=2),
                    ),
                    textinfo="percent",
                    textposition="auto",
                    textfont=dict(
                        family="Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
                        size=12,
                        color="#ffffff",
                    ),
                    hovertemplate="<b style='font-family: Inter, sans-serif; font-size: 14px;'>%{label}</b><br>" +
                                  "<span style='color: #6b7fd7;'>Değer:</span> <b>%{value:,.0f}</b><br>" +
                                  "<span style='color: #6b7fd7;'>Pay:</span> <b>%{percent:.1%}</b><extra></extra>",
                )
            ]
        )
        fig_pie.update_layout(
            margin=dict(t=20, b=20, l=20, r=20),
            showlegend=True,
            legend=dict(
                title=dict(
                    text=f"<b>{group_col}</b>",
                    font=dict(
                        family="Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
                        size=13,
                        color="#6b7fd7",
                    ),
                ),
                font=dict(
                    family="Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
                    size=12,
                    color="#b0b3c0",
                ),
                bgcolor="rgba(0,0,0,0)",
                bordercolor="rgba(255,255,255,0.1)",
                borderwidth=1,
                itemclick="toggleothers",
                itemdoubleclick="toggle",
            ),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            annotations=[
                dict(
                    text="<b>TOPLAM</b>",
                    x=0.5,
                    y=0.55,
                    font=dict(
                        family="Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
                        size=11,
                        color="#9da1b3",
                    ),
                    showarrow=False,
                ),
                dict(
                    text=f"<b>{grouped['Değer'].sum():,.0f}</b>",
                    x=0.5,
                    y=0.42,
                    font=dict(
                        family="Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
                        size=20,
                        color="#ffffff",
                    ),
                    showarrow=False,
                ),
            ],
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    # --- Bar (Dağılım) - Modern ve Profesyonel ---
    with col_bar:
        fig_bar = go.Figure()
        
        # Bar chart için logo URL'lerini hazırla (sadece Kod kolonu için)
        # Plotly'de image annotation'ları için images parametresi kullanılır
        images = []
        if group_col == "Kod" and "Pazar" in grouped.columns:
            from utils import get_stock_logo_url
            for idx, (_, row) in enumerate(grouped.iterrows()):
                kod = str(row[group_col])
                pazar = str(row.get("Pazar", ""))
                logo_url = get_stock_logo_url(kod, pazar)
                if logo_url and ("BIST" in pazar.upper() or "ABD" in pazar.upper() or "US" in pazar.upper() or "S&P" in pazar.upper() or "NASDAQ" in pazar.upper()):
                    # Y pozisyonu: bar'ın y pozisyonu (reversed olduğu için, 0'dan başlar)
                    # Plotly'de y-axis reversed olduğu için, y değeri label'ın index'i
                    y_pos = idx
                    images.append(
                        dict(
                            source=logo_url,
                            xref="paper",
                            yref="y",
                            x=0.01,  # Sol tarafta, biraz içeride
                            y=y_pos,
                            sizex=0.04,  # Logo boyutu
                            sizey=0.6,  # Logo yüksekliği
                            xanchor="left",
                            yanchor="middle",
                            sizing="contain",
                            layer="above",
                        )
                    )
        
        fig_bar.add_trace(
            go.Bar(
                x=grouped["Değer"],
                y=grouped["Label"],
                orientation="h",
                marker=dict(
                    color=modern_colors[:len(grouped)],
                    line=dict(color="#0e1117", width=1.5),
                    opacity=0.9,
                ),
                text=[f"{val:,.0f}" for val in grouped["Değer"]],
                textposition="outside",
                textfont=dict(
                    family="Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
                    size=11,
                    color="#ffffff",
                ),
                hovertemplate="<b style='font-family: Inter, sans-serif; font-size: 14px;'>%{y}</b><br>" +
                              "<span style='color: #6b7fd7;'>Değer:</span> <b>%{x:,.0f}</b><br>" +
                              "<span style='color: #6b7fd7;'>Pay:</span> <b>%{customdata:.2f}%</b><extra></extra>",
                customdata=grouped["Pay (%)"],
            )
        )
        fig_bar.update_layout(
            margin=dict(t=20, b=20, l=60, r=40),  # Sol margin artırıldı logo için
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(
                title="",
                showgrid=True,
                gridcolor="rgba(255,255,255,0.05)",
                gridwidth=1,
                zeroline=False,
                tickfont=dict(
                    family="Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
                    size=11,
                    color="#9da1b3",
                ),
            ),
            yaxis=dict(
                title="",
                autorange="reversed",
                showgrid=False,
                tickfont=dict(
                    family="Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
                    size=12,
                    color="#ffffff",
                ),
            ),
            images=images if images else None,
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


@st.cache_data(ttl=300)
def _fetch_historical_prices_batch(symbols_list, period="60d", interval="1d"):
    """Batch olarak tarihsel fiyat verilerini çeker"""
    if not symbols_list:
        return {}
    try:
        tickers = yf.Tickers(" ".join(symbols_list))
        prices_dict = {}
        for sym in symbols_list:
            try:
                h = tickers.tickers[sym].history(period=period, interval=interval)
                if not h.empty:
                    prices_dict[sym] = h["Close"]
            except Exception:
                prices_dict[sym] = None
        return prices_dict
    except Exception:
        return {}

def get_historical_chart(df: pd.DataFrame, usd_try_rate: float, pb: str):
    """
    Son 60 güne ait yaklaşık tarihsel portföy değeri grafiği oluşturur.
    - Her varlık için Yahoo Finance (veya ons altın/gümüş, fon vs.) verisi çekilir.
    - Lot/adet ile çarpılır.
    - Seçilen para birimine (pb: TRY / USD) göre çevrilir.
    - Hepsi toplanıp tek zaman serisi olarak çizilir.
    Optimize edilmiş: Batch veri çekme kullanılıyor.
    """
    if df is None or df.empty:
        return None

    # Önce tüm sembolleri topla
    yahoo_symbols = []
    symbol_to_rows = {}  # symbol -> [(idx, kod, pazar, adet, asset_currency), ...]
    special_cases = []  # Nakit, fon, gram altın/gümüş için
    
    for idx, row in df.iterrows():
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

        # Özel durumları ayır
        if "NAKIT" in pazar_upper:
            special_cases.append(("NAKIT", idx, kod, pazar, adet, asset_currency))
        elif "FON" in pazar_upper:
            special_cases.append(("FON", idx, kod, pazar, adet, asset_currency))
        elif "GRAM GÜMÜŞ" in kod_upper:
            if "SI=F" not in yahoo_symbols:
                yahoo_symbols.append("SI=F")
            if "SI=F" not in symbol_to_rows:
                symbol_to_rows["SI=F"] = []
            symbol_to_rows["SI=F"].append((idx, kod, pazar, adet, asset_currency, "GRAM_GUMUS"))
        elif "GRAM ALTIN" in kod_upper:
            if "GC=F" not in yahoo_symbols:
                yahoo_symbols.append("GC=F")
            if "GC=F" not in symbol_to_rows:
                symbol_to_rows["GC=F"] = []
            symbol_to_rows["GC=F"].append((idx, kod, pazar, adet, asset_currency, "GRAM_ALTIN"))
        else:
            symbol = get_yahoo_symbol(kod, pazar)
            if symbol not in yahoo_symbols:
                yahoo_symbols.append(symbol)
            if symbol not in symbol_to_rows:
                symbol_to_rows[symbol] = []
            symbol_to_rows[symbol].append((idx, kod, pazar, adet, asset_currency, "NORMAL"))

    # Batch olarak fiyat verilerini çek
    batch_prices = _fetch_historical_prices_batch(yahoo_symbols, period="60d", interval="1d")
    
    all_series = []
    today = pd.Timestamp.today().normalize()

    # Özel durumları işle
    for case_type, idx, kod, pazar, adet, asset_currency in special_cases:
        prices = None
        try:
            if case_type == "NAKIT":
                kod_upper = kod.upper()
                if kod_upper == "TL":
                    prices = pd.Series([1.0], index=[today])
                elif kod_upper == "USD":
                    prices = pd.Series([usd_try_rate], index=[today])
                else:
                    prices = pd.Series([1.0], index=[today])
            elif case_type == "FON":
                price, _ = get_tefas_data(kod)
                if price and price > 0:
                    idx_range = pd.date_range(end=today, periods=30, freq="D")
                    prices = pd.Series(price, index=idx_range)
        except Exception:
            pass
        
        if prices is not None and not prices.empty:
            prices.index = pd.to_datetime(prices.index).tz_localize(None)
            if pb == "TRY":
                if asset_currency == "USD":
                    values = prices * adet * usd_try_rate
                else:
                    values = prices * adet
            else:
                if asset_currency == "TRY":
                    values = prices * adet / usd_try_rate
                else:
                    values = prices * adet
            all_series.append(values.rename(f"Değer_{idx}"))

    # Normal sembolleri işle
    for symbol, rows in symbol_to_rows.items():
        if symbol not in batch_prices or batch_prices[symbol] is None:
            continue
        
        prices = batch_prices[symbol]
        prices.index = pd.to_datetime(prices.index).tz_localize(None)
        
        for idx, kod, pazar, adet, asset_currency, case_type in rows:
            if case_type in ["GRAM_GUMUS", "GRAM_ALTIN"]:
                # Gram altın/gümüş için özel dönüşüm
                prices_converted = (prices * usd_try_rate) / 31.1035
            else:
                prices_converted = prices
            
            # TRY / USD çevirisi
            if pb == "TRY":
                if asset_currency == "USD":
                    values = prices_converted * adet * usd_try_rate
                else:
                    values = prices_converted * adet
            else:  # pb == "USD"
                if asset_currency == "TRY":
                    values = prices_converted * adet / usd_try_rate
                else:
                    values = prices_converted * adet
            
            all_series.append(values.rename(f"Değer_{idx}"))

    if not all_series:
        return None

    # Tüm serileri hizalayıp topla + forward fill
    df_concat = pd.concat(all_series, axis=1)
    df_concat.index = pd.to_datetime(df_concat.index)
    df_concat = df_concat.sort_index()
    df_concat = df_concat.ffill()  # eksik günleri son değerle doldur

    portfolio_series = df_concat.sum(axis=1)
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
