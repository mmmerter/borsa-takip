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
    show_companies: bool = False,
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
    
    # Eğer "Kod" kolonu varsa (şirket listesi için), onu da koru
    # Not: "Kod" kolonu zaten birleştirilmiş şirket listesi olmalı (merge sonrası)
    if "Kod" in df.columns:
        # "Kod" kolonu zaten birleştirilmiş şirket listesi, her sektör için tek değer var
        # groupby yaparken "first" kullan (aslında hepsi aynı olmalı)
        grouped = df.groupby(group_col, as_index=False).agg({**agg, "Kod": "first"})
    else:
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
    
    # Şirket listesi için custom_data hazırla (sadece sektör grafikleri için)
    # "Kod" kolonu merge ile eklenmiş olmalı
    if show_companies and "Kod" in grouped.columns:
        # "Kod" kolonu zaten birleştirilmiş şirket listesi
        grouped["SirketListesi"] = grouped["Kod"].fillna("").astype(str)
        # Boş string'leri kontrol et
        grouped["SirketListesi"] = grouped["SirketListesi"].replace("", "Bilinmiyor")
    elif show_companies:
        # Eğer "Kod" kolonu yoksa boş string
        grouped["SirketListesi"] = "Bilinmiyor"
    else:
        grouped["SirketListesi"] = ""

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
        # Hover template'i hazırla
        if show_companies and "SirketListesi" in grouped.columns:
            # Şirket listesi varsa hover template'e ekle
            # customdata kontrolü
            sirket_listesi = grouped["SirketListesi"].fillna("").astype(str)
            # Boş olmayan değerler varsa göster
            if not sirket_listesi.empty and sirket_listesi.str.strip().ne("").any():
                hover_template = "<b style='font-family: Inter, sans-serif; font-size: 14px;'>%{label}</b><br>" + \
                                "<span style='color: #6b7fd7;'>Değer:</span> <b>%{value:,.0f}</b><br>" + \
                                "<span style='color: #6b7fd7;'>Pay:</span> <b>%{percent:.1%}</b><br>" + \
                                "<span style='color: #6b7fd7;'>Şirketler:</span> <span style='font-size: 12px; color: #ffffff;'>%{customdata[0]}</span><extra></extra>"
                customdata_list = sirket_listesi.tolist()
            else:
                hover_template = "<b style='font-family: Inter, sans-serif; font-size: 14px;'>%{label}</b><br>" + \
                                "<span style='color: #6b7fd7;'>Değer:</span> <b>%{value:,.0f}</b><br>" + \
                                "<span style='color: #6b7fd7;'>Pay:</span> <b>%{percent:.1%}</b><extra></extra>"
                customdata_list = None
        else:
            hover_template = "<b style='font-family: Inter, sans-serif; font-size: 14px;'>%{label}</b><br>" + \
                            "<span style='color: #6b7fd7;'>Değer:</span> <b>%{value:,.0f}</b><br>" + \
                            "<span style='color: #6b7fd7;'>Pay:</span> <b>%{percent:.1%}</b><extra></extra>"
            customdata_list = None
        
        # Pie chart için data hazırla
        pie_data = {
            "labels": grouped["Label"].tolist(),
            "values": grouped["Değer"].tolist(),
            "hole": 0.65,
            "marker": dict(
                colors=modern_colors[:len(grouped)],
                line=dict(color="#0e1117", width=2),
            ),
            "textinfo": "percent",
            "textposition": "auto",
            "textfont": dict(
                family="Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
                size=12,
                color="#ffffff",
            ),
            "hovertemplate": hover_template,
        }
        
        # customdata varsa ekle (numpy array olarak)
        if customdata_list is not None and len(customdata_list) > 0:
            import numpy as np
            pie_data["customdata"] = np.array(customdata_list)
        
        fig_pie = go.Figure(data=[go.Pie(**pie_data)])
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
            margin=dict(t=20, b=20, l=20, r=40),
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
    
    # Günlük K/Z yüzdesi (günlük kâr/zararın toplam değere göre yüzdesi)
    daily_pnl_pct = (daily_pnl / total_val * 100) if total_val != 0 else 0.0

    c1, c2, c3 = st.columns(3)
    # Toplam Değer için: Toplam kâr/zarar yüzdesi (maliyete göre)
    c1.metric("Toplam Değer", f"{sym}{total_val:,.0f}", delta=f"{pnl_pct:.2f}%")
    c2.metric("Toplam K/Z", f"{sym}{total_pnl:,.0f}", delta=f"{pnl_pct:.2f}%")
    # Günlük K/Z için: Günlük kâr/zararın toplam değere göre yüzdesi
    c3.metric("Günlük K/Z", f"{sym}{daily_pnl:,.0f}", delta=f"{daily_pnl_pct:.2f}%")

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
    
    # Günlük değişim ve yüzde değişim hesapla
    hist_df["GünlükDeğişim"] = hist_df["ToplamDeğer"].diff()
    hist_df["GünlükDeğişim%"] = (hist_df["ToplamDeğer"].pct_change() * 100).fillna(0)
    
    # Başlangıç değeri (ilk gün)
    başlangıç_değeri = hist_df["ToplamDeğer"].iloc[0]
    son_değer = hist_df["ToplamDeğer"].iloc[-1]
    toplam_değişim = son_değer - başlangıç_değeri
    toplam_değişim_pct = ((son_değer - başlangıç_değeri) / başlangıç_değeri * 100) if başlangıç_değeri > 0 else 0
    
    # Min ve Max değerler
    min_değer = hist_df["ToplamDeğer"].min()
    max_değer = hist_df["ToplamDeğer"].max()
    min_tarih_raw = hist_df.loc[hist_df["ToplamDeğer"].idxmin(), "Tarih"]
    max_tarih_raw = hist_df.loc[hist_df["ToplamDeğer"].idxmax(), "Tarih"]
    
    # Pandas Timestamp'leri string'e çevir (Plotly için)
    if hasattr(min_tarih_raw, 'strftime'):
        min_tarih = min_tarih_raw.strftime('%Y-%m-%d')
    else:
        min_tarih = str(min_tarih_raw)
    
    if hasattr(max_tarih_raw, 'strftime'):
        max_tarih = max_tarih_raw.strftime('%Y-%m-%d')
    else:
        max_tarih = str(max_tarih_raw)
    
    # Para birimi sembolü
    currency_symbol = "₺" if pb == "TRY" else "$"
    
    # Modern grafik oluştur - Area chart ile gradient fill
    fig = go.Figure()
    
    # Area chart (gradient fill ile)
    fig.add_trace(
        go.Scatter(
            x=hist_df["Tarih"],
            y=hist_df["ToplamDeğer"],
            mode="lines",
            name="Portföy Değeri",
            fill="tonexty",
            fillcolor="rgba(107, 127, 215, 0.2)",  # Gradient fill için başlangıç
            line=dict(
                color="#6b7fd7",
                width=3,
                shape="spline",  # Yumuşak çizgiler
            ),
            hovertemplate="<b style='font-family: Inter, sans-serif; font-size: 14px;'>%{x|%d %b %Y}</b><br>" +
                         f"<span style='color: #6b7fd7;'>Değer:</span> <b>{currency_symbol}%{{y:,.0f}}</b><br>" +
                         "<span style='color: #6b7fd7;'>Günlük Değişim:</span> <b>%{customdata[0]:+,.0f}</b><br>" +
                         "<span style='color: #6b7fd7;'>Günlük Değişim %:</span> <b>%{customdata[1]:+.2f}%</b><extra></extra>",
            customdata=hist_df[["GünlükDeğişim", "GünlükDeğişim%"]].values,
        )
    )
    
    # Başlangıç çizgisi (dikey)
    başlangıç_tarih = hist_df["Tarih"].iloc[0]
    # Pandas Timestamp'i string'e çevir (Plotly için)
    if hasattr(başlangıç_tarih, 'strftime'):
        başlangıç_tarih_str = başlangıç_tarih.strftime('%Y-%m-%d')
    else:
        başlangıç_tarih_str = str(başlangıç_tarih)
    
    fig.add_vline(
        x=başlangıç_tarih_str,
        line_dash="dash",
        line_color="#9da1b3",
        line_width=1,
        opacity=0.5,
        annotation_text=f"Başlangıç: {currency_symbol}{başlangıç_değeri:,.0f}",
        annotation_position="top left",
        annotation_font_size=10,
        annotation_font_color="#9da1b3",
    )
    
    # Min ve Max noktaları (annotation ile)
    if min_değer < başlangıç_değeri * 0.95:  # Sadece önemli düşüşlerde göster
        fig.add_annotation(
            x=min_tarih,
            y=min_değer,
            text=f"Min: {currency_symbol}{min_değer:,.0f}",
            showarrow=True,
            arrowhead=2,
            arrowcolor="#ff5252",
            bgcolor="rgba(255, 82, 82, 0.8)",
            bordercolor="#ff5252",
            font=dict(color="#ffffff", size=10, family="Inter, sans-serif"),
        )
    
    if max_değer > başlangıç_değeri * 1.05:  # Sadece önemli yükselişlerde göster
        fig.add_annotation(
            x=max_tarih,
            y=max_değer,
            text=f"Max: {currency_symbol}{max_değer:,.0f}",
            showarrow=True,
            arrowhead=2,
            arrowcolor="#00e676",
            bgcolor="rgba(0, 230, 118, 0.8)",
            bordercolor="#00e676",
            font=dict(color="#ffffff", size=10, family="Inter, sans-serif"),
        )
    
    # Modern layout
    fig.update_layout(
        title=dict(
            text=f"<b>Portföy Değeri (60 Gün)</b><br><span style='font-size: 12px; color: #9da1b3;'>Toplam Değişim: {currency_symbol}{toplam_değişim:+,.0f} ({toplam_değişim_pct:+.2f}%)</span>",
            font=dict(
                family="Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
                size=18,
                color="#ffffff",
            ),
            x=0.5,
            xanchor="center",
        ),
        margin=dict(t=80, b=40, l=60, r=40),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(
            title="",
            showgrid=True,
            gridcolor="rgba(255,255,255,0.05)",
            gridwidth=1,
            tickfont=dict(
                family="Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
                size=11,
                color="#9da1b3",
            ),
            showline=True,
            linecolor="rgba(255,255,255,0.1)",
            linewidth=1,
        ),
        yaxis=dict(
            title=dict(
                text=f"Portföy Değeri ({currency_symbol})",
                font=dict(
                    family="Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
                    size=12,
                    color="#9da1b3",
                ),
            ),
            showgrid=True,
            gridcolor="rgba(255,255,255,0.05)",
            gridwidth=1,
            tickfont=dict(
                family="Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
                size=11,
                color="#9da1b3",
            ),
            showline=True,
            linecolor="rgba(255,255,255,0.1)",
            linewidth=1,
        ),
        hovermode="x unified",
        height=450,
        showlegend=False,
    )
    
    return fig
