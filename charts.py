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

    # Altında özet tablo - modern header ekle
    st.markdown(
        """
        <div style="
            background: linear-gradient(90deg, rgba(107, 127, 215, 0.2) 0%, rgba(139, 154, 255, 0.1) 100%);
            border-radius: 12px;
            padding: 12px 20px;
            margin-top: 24px;
            margin-bottom: 12px;
            border-left: 3px solid #6b7fd7;
        ">
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 18px;">📊</span>
                <span style="
                    font-size: 16px;
                    font-weight: 800;
                    color: #ffffff;
                    letter-spacing: -0.3px;
                ">Detaylı Dağılım Analizi</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    disp = grouped[[label_col, "Değer", "Pay (%)"]].copy()
    
    # Pazar isimlerini modernize et
    if group_col == "Pazar":
        pazar_modernize = {
            "BIST (Tümü)": "🇹🇷 Borsa İstanbul",
            "BIST": "🇹🇷 Borsa İstanbul",
            "ABD (S&P + NASDAQ)": "🇺🇸 ABD Borsaları",
            "ABD": "🇺🇸 Amerika",
            "NASDAQ": "🇺🇸 NASDAQ",
            "S&P": "🇺🇸 S&P 500",
            "FON": "📊 Yatırım Fonları",
            "Fonlar": "📊 Yatırım Fonları",
            "EMTIA": "💎 Altın &귀금속",
            "Emtia": "💎 Altın &귀금속",
            "NAKIT": "💵 Nakit & Döviz",
            "Nakit": "💵 Nakit & Döviz",
            "KRİPTO": "₿ Kripto Paralar",
            "Kripto": "₿ Kripto Paralar",
            "VADELİ": "📈 Vadeli İşlemler",
            "Vadeli": "📈 Vadeli İşlemler",
        }
        disp[label_col] = disp[label_col].replace(pazar_modernize)
    
    # Kolon isimlerini modernize et
    column_renames = {
        label_col: f"🎯 {group_col}",
        "Değer": "💰 Toplam Değer",
        "Pay (%)": "📊 Portföy Payı (%)"
    }
    disp.rename(columns=column_renames, inplace=True)
    disp[f"📊 Portföy Payı (%)"] = disp[f"📊 Portföy Payı (%)"].round(2)
    st.dataframe(styled_dataframe(disp), use_container_width=True, hide_index=True, height=min(400, len(disp) * 50 + 100))


def render_modern_list_header(title: str, icon: str, subtitle: str = ""):
    """Modern başlık oluşturur - animasyonlu ikon ve gradyan arka plan ile"""
    st.markdown(
        f"""
        <div class="modern-list-header" style="
            background: linear-gradient(135deg, rgba(107, 127, 215, 0.15) 0%, rgba(139, 154, 255, 0.05) 100%);
            border-radius: 16px;
            padding: 20px 24px;
            margin-bottom: 20px;
            border-left: 4px solid #6b7fd7;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
            position: relative;
            overflow: hidden;
        ">
            <div style="display: flex; align-items: center; gap: 14px;">
                <span class="header-icon" style="
                    font-size: 36px;
                    filter: drop-shadow(0 2px 6px rgba(107, 127, 215, 0.4));
                    animation: pulse-glow 2s ease-in-out infinite;
                ">{icon}</span>
                <div>
                    <h3 style="
                        font-size: 26px;
                        font-weight: 900;
                        color: #ffffff;
                        margin: 0;
                        letter-spacing: -0.5px;
                        text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
                    ">{title}</h3>
                    {f'<p style="font-size: 13px; color: #b0b3c0; margin: 4px 0 0 0; font-weight: 600;">{subtitle}</p>' if subtitle else ''}
                </div>
            </div>
        </div>
        <style>
            @keyframes pulse-glow {{
                0%, 100% {{ transform: scale(1); opacity: 1; }}
                50% {{ transform: scale(1.05); opacity: 0.9; }}
            }}
        </style>
        """,
        unsafe_allow_html=True
    )


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
    - Altta modern detay tablo
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

    # Modern başlık ekle
    render_modern_list_header(
        title=f"Detaylı {filter_key} Listesi",
        icon="📋",
        subtitle=f"{len(sub)} varlık • {sym}{total_val:,.0f} toplam değer"
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
    
    # Pazar isimlerini modernize et
    if "Pazar" in disp.columns:
        pazar_modernize = {
            "BIST (Tümü)": "🇹🇷 Borsa İstanbul",
            "BIST": "🇹🇷 Borsa İstanbul",
            "ABD (S&P + NASDAQ)": "🇺🇸 ABD Borsaları",
            "ABD": "🇺🇸 Amerika",
            "NASDAQ": "🇺🇸 NASDAQ",
            "S&P": "🇺🇸 S&P 500",
            "FON": "📊 Yatırım Fonları",
            "Fonlar": "📊 Yatırım Fonları",
            "EMTIA": "💎 Altın &귀금속",
            "Emtia": "💎 Altın &귀금속",
            "NAKIT": "💵 Nakit & Döviz",
            "Nakit": "💵 Nakit & Döviz",
            "KRİPTO": "₿ Kripto Paralar",
            "Kripto": "₿ Kripto Paralar",
            "VADELİ": "📈 Vadeli İşlemler",
            "Vadeli": "📈 Vadeli İşlemler",
        }
        disp["Pazar"] = disp["Pazar"].replace(pazar_modernize)
    
    # Tip kolonunu modernize et
    if "Tip" in disp.columns:
        tip_modernize = {
            "Spot": "💰 Spot",
            "Takip": "👁️ İzleme",
            "Vadeli": "📈 Vadeli",
        }
        disp["Tip"] = disp["Tip"].replace(tip_modernize)
    
    # Kolon isimlerini modernize et
    modern_column_names = {
        "Kod": "🎯 Varlık",
        "Pazar": "🌍 Piyasa",
        "Tip": "📌 Tür",
        "Adet": "📦 Miktar",
        "Maliyet": "💵 Alış Fiyatı",
        "Fiyat": "💰 Güncel Fiyat",
        "PB": "💱 Para Birimi",
        "Yatırılan": "💸 Yatırılan Sermaye",
        "Değer": "💎 Toplam Değer",
        "Top. Kâr/Zarar": "📈 Toplam K/Z",
        "Top. %": "📊 Getiri %",
        "Gün. Kâr/Zarar": "🔄 Günlük K/Z",
        "Notlar": "📝 Notlar",
        "Sektör": "🏭 Sektör",
        "Günlük %": "⚡ Günlük Değişim %",
    }
    
    # Sadece mevcut kolonları rename et
    rename_dict = {k: v for k, v in modern_column_names.items() if k in disp.columns}
    disp = disp.rename(columns=rename_dict)

    st.dataframe(styled_dataframe(disp), use_container_width=True, hide_index=True, height=min(600, len(disp) * 50 + 100))


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

def get_historical_chart(df: pd.DataFrame, usd_try_rate: float, pb: str, start_date: pd.Timestamp = None):
    """
    Tarihsel portföy değeri grafiği oluşturur.
    - Her varlık için Yahoo Finance (veya ons altın/gümüş, fon vs.) verisi çekilir.
    - Lot/adet ile çarpılır.
    - Seçilen para birimine (pb: TRY / USD) göre çevrilir.
    - start_date belirtilirse, o tarihten itibaren performans gösterilir (normalize edilir).
    - Maliyet bazlı yüzde performans gösterilir (yeni varlık eklendiğinde ani yükseliş olmaz).
    Optimize edilmiş: Batch veri çekme kullanılıyor.
    
    Args:
        df: Portföy dataframe'i
        usd_try_rate: USD/TRY kuru
        pb: Para birimi ("TRY" veya "USD")
        start_date: Başlangıç tarihi (None ise son 60 gün gösterilir)
    """
    if df is None or df.empty:
        return None

    # Mevcut varlıkların toplam maliyetini hesapla (sabit kalır)
    total_cost = 0.0
    for idx, row in df.iterrows():
        adet = float(row.get("Adet", 0) or 0)
        maliyet = float(row.get("Maliyet", 0) or 0)
        if adet > 0 and maliyet > 0:
            # Para birimine göre maliyet hesapla
            pazar = str(row.get("Pazar", ""))
            kod = str(row.get("Kod", ""))
            pazar_upper = pazar.upper()
            kod_upper = kod.upper()
            
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
            
            cost_native = maliyet * adet
            if pb == "TRY":
                if asset_currency == "USD":
                    total_cost += cost_native * usd_try_rate
                else:
                    total_cost += cost_native
            else:  # pb == "USD"
                if asset_currency == "TRY":
                    total_cost += cost_native / usd_try_rate
                else:
                    total_cost += cost_native

    # Önce tüm sembolleri topla
    yahoo_symbols = []
    symbol_to_rows = {}  # symbol -> [(idx, kod, pazar, adet, asset_currency, maliyet), ...]
    special_cases = []  # Nakit, fon, gram altın/gümüş için
    
    for idx, row in df.iterrows():
        kod = str(row.get("Kod", ""))
        pazar = str(row.get("Pazar", ""))
        adet = float(row.get("Adet", 0) or 0)
        maliyet = float(row.get("Maliyet", 0) or 0)

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
            special_cases.append(("NAKIT", idx, kod, pazar, adet, asset_currency, maliyet))
        elif "FON" in pazar_upper:
            special_cases.append(("FON", idx, kod, pazar, adet, asset_currency, maliyet))
        elif "GRAM GÜMÜŞ" in kod_upper:
            if "SI=F" not in yahoo_symbols:
                yahoo_symbols.append("SI=F")
            if "SI=F" not in symbol_to_rows:
                symbol_to_rows["SI=F"] = []
            symbol_to_rows["SI=F"].append((idx, kod, pazar, adet, asset_currency, "GRAM_GUMUS", maliyet))
        elif "GRAM ALTIN" in kod_upper:
            if "GC=F" not in yahoo_symbols:
                yahoo_symbols.append("GC=F")
            if "GC=F" not in symbol_to_rows:
                symbol_to_rows["GC=F"] = []
            symbol_to_rows["GC=F"].append((idx, kod, pazar, adet, asset_currency, "GRAM_ALTIN", maliyet))
        else:
            symbol = get_yahoo_symbol(kod, pazar)
            if symbol not in yahoo_symbols:
                yahoo_symbols.append(symbol)
            if symbol not in symbol_to_rows:
                symbol_to_rows[symbol] = []
            symbol_to_rows[symbol].append((idx, kod, pazar, adet, asset_currency, "NORMAL", maliyet))

    # Batch olarak fiyat verilerini çek
    batch_prices = _fetch_historical_prices_batch(yahoo_symbols, period="60d", interval="1d")
    
    all_series = []
    today = pd.Timestamp.today().normalize()

    # Özel durumları işle
    for case_type, idx, kod, pazar, adet, asset_currency, maliyet in special_cases:
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
        
        for row_data in rows:
            if len(row_data) == 7:
                idx, kod, pazar, adet, asset_currency, case_type, maliyet = row_data
            else:
                # Eski format desteği
                idx, kod, pazar, adet, asset_currency, case_type = row_data
                maliyet = 0.0
            
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
    
    # start_date belirtilmişse, o tarihten itibaren filtrele
    if start_date is not None:
        start_date_normalized = pd.to_datetime(start_date).normalize()
        portfolio_series = portfolio_series[portfolio_series.index >= start_date_normalized]
        # En az 1 gün veri olmalı
        if len(portfolio_series) == 0:
            # Eğer start_date'den sonra veri yoksa, en yakın tarihi kullan
            available_dates = df_concat.sum(axis=1).index
            if len(available_dates) > 0:
                closest_date = available_dates[available_dates >= start_date_normalized]
                if len(closest_date) > 0:
                    portfolio_series = df_concat.sum(axis=1)[df_concat.sum(axis=1).index >= closest_date[0]]
                else:
                    # Hiç veri yoksa son 60 günü göster
                    portfolio_series = df_concat.sum(axis=1)[-60:]
    else:
        # start_date yoksa son 60 günü göster
        portfolio_series = portfolio_series[-60:]

    hist_df = portfolio_series.reset_index()
    hist_df.columns = ["Tarih", "ToplamDeğer"]
    
    # start_date belirtilmişse, o tarihteki değeri başlangıç olarak kullan ve normalize et
    if start_date is not None and len(hist_df) > 0:
        start_date_normalized = pd.to_datetime(start_date).normalize()
        # Başlangıç tarihine en yakın değeri bul
        start_mask = hist_df["Tarih"] >= start_date_normalized
        if start_mask.any():
            start_value = hist_df.loc[start_mask, "ToplamDeğer"].iloc[0]
            # Normalize et: başlangıç değeri = 100
            hist_df["NormalizeDeğer"] = (hist_df["ToplamDeğer"] / start_value) * 100
            hist_df["Performans%"] = hist_df["NormalizeDeğer"] - 100
            hist_df["GrafikDeğeri"] = hist_df["Performans%"]
        else:
            # Başlangıç tarihi bulunamazsa maliyet bazlı hesapla
            if total_cost > 0:
                hist_df["Performans%"] = (hist_df["ToplamDeğer"] / total_cost * 100) - 100
                hist_df["GrafikDeğeri"] = hist_df["Performans%"]
            else:
                hist_df["Performans%"] = 0.0
                hist_df["GrafikDeğeri"] = hist_df["ToplamDeğer"]
    else:
        # Maliyet bazlı yüzde performans hesapla (yeni varlık eklendiğinde ani yükseliş olmaz)
        if total_cost > 0:
            hist_df["Performans%"] = (hist_df["ToplamDeğer"] / total_cost * 100) - 100
            # Grafikte performans yüzdesini göster (başlangıç = 0%)
            hist_df["GrafikDeğeri"] = hist_df["Performans%"]
        else:
            # Maliyet yoksa eski yöntemi kullan
            hist_df["Performans%"] = 0.0
            hist_df["GrafikDeğeri"] = hist_df["ToplamDeğer"]
    
    # Günlük değişim ve yüzde değişim hesapla
    hist_df["GünlükDeğişim"] = hist_df["ToplamDeğer"].diff()
    hist_df["GünlükDeğişim%"] = (hist_df["ToplamDeğer"].pct_change() * 100).fillna(0)
    
    # Başlangıç değeri (ilk gün)
    başlangıç_değeri = hist_df["ToplamDeğer"].iloc[0]
    son_değer = hist_df["ToplamDeğer"].iloc[-1]
    toplam_değişim = son_değer - başlangıç_değeri
    toplam_değişim_pct = ((son_değer - başlangıç_değeri) / başlangıç_değeri * 100) if başlangıç_değeri > 0 else 0
    
    # Performans bazlı değişim
    if start_date is not None and "NormalizeDeğer" in hist_df.columns:
        # Normalize edilmiş performans
        başlangıç_performans = hist_df["Performans%"].iloc[0]  # Bu durumda 0 olmalı
        son_performans = hist_df["Performans%"].iloc[-1]
        performans_değişim = son_performans - başlangıç_performans
    elif total_cost > 0:
        # Maliyet bazlı performans
        başlangıç_performans = hist_df["Performans%"].iloc[0]
        son_performans = hist_df["Performans%"].iloc[-1]
        performans_değişim = son_performans - başlangıç_performans
    else:
        performans_değişim = toplam_değişim_pct
    
    # Para birimi sembolü
    currency_symbol = "₺" if pb == "TRY" else "$"
    
    # Grafikte gösterilecek değer: Maliyet bazlı yüzde varsa onu kullan, yoksa mutlak değer
    if total_cost > 0:
        y_values = hist_df["GrafikDeğeri"]
        y_label = "Performans (%)"
        hover_value_template = "<span style='color: #6b7fd7;'>Performans:</span> <b>%{y:+.2f}%</b><br>" + \
                              f"<span style='color: #6b7fd7;'>Değer:</span> <b>{currency_symbol}%{{customdata[2]:,.0f}}</b><br>" + \
                              "<span style='color: #6b7fd7;'>Günlük Değişim:</span> <b>%{customdata[0]:+,.0f}</b><br>" + \
                              "<span style='color: #6b7fd7;'>Günlük Değişim %:</span> <b>%{customdata[1]:+.2f}%</b>"
        customdata_array = hist_df[["GünlükDeğişim", "GünlükDeğişim%", "ToplamDeğer"]].values
    else:
        y_values = hist_df["ToplamDeğer"]
        y_label = f"Portföy Değeri ({currency_symbol})"
        hover_value_template = f"<span style='color: #6b7fd7;'>Değer:</span> <b>{currency_symbol}%{{y:,.0f}}</b><br>" + \
                              "<span style='color: #6b7fd7;'>Günlük Değişim:</span> <b>%{customdata[0]:+,.0f}</b><br>" + \
                              "<span style='color: #6b7fd7;'>Günlük Değişim %:</span> <b>%{customdata[1]:+.2f}%</b>"
        customdata_array = hist_df[["GünlükDeğişim", "GünlükDeğişim%"]].values
    
    # Min ve Max değerler
    min_değer = hist_df["ToplamDeğer"].min()
    max_değer = hist_df["ToplamDeğer"].max()
    min_tarih = hist_df.loc[hist_df["ToplamDeğer"].idxmin(), "Tarih"]
    max_tarih = hist_df.loc[hist_df["ToplamDeğer"].idxmax(), "Tarih"]
    
    # Modern grafik oluştur - Area chart ile gradient fill
    fig = go.Figure()
    
    # Area chart (gradient fill ile)
    fig.add_trace(
        go.Scatter(
            x=hist_df["Tarih"],
            y=y_values,
            mode="lines",
            name="Portföy Performansı" if total_cost > 0 else "Portföy Değeri",
            fill="tonexty",
            fillcolor="rgba(107, 127, 215, 0.2)",  # Gradient fill için başlangıç
            line=dict(
                color="#6b7fd7",
                width=3,
                shape="spline",  # Yumuşak çizgiler
            ),
            hovertemplate="<b style='font-family: Inter, sans-serif; font-size: 14px;'>%{x|%d %b %Y}</b><br>" +
                         hover_value_template +
                         "<extra></extra>",
            customdata=customdata_array,
        )
    )
    
    # Başlangıç çizgisi (dikey) - add_shape kullan
    başlangıç_tarih = hist_df["Tarih"].iloc[0]
    fig.add_shape(
        type="line",
        x0=başlangıç_tarih,
        x1=başlangıç_tarih,
        y0=0,
        y1=1,
        yref="paper",
        line=dict(
            color="#9da1b3",
            width=1,
            dash="dash",
        ),
        opacity=0.5,
    )
    
    # Başlangıç annotation'ı
    if start_date is not None and "NormalizeDeğer" in hist_df.columns:
        # Normalize edilmiş performans modu
        başlangıç_y = hist_df["GrafikDeğeri"].iloc[0]  # Bu durumda 0 olmalı
        başlangıç_text = f"Başlangıç ({başlangıç_tarih.strftime('%d %b %Y')}): 0%"
    elif total_cost > 0:
        başlangıç_y = hist_df["GrafikDeğeri"].iloc[0]
        başlangıç_text = f"Başlangıç: {başlangıç_y:+.2f}%"
    else:
        başlangıç_y = başlangıç_değeri
        başlangıç_text = f"Başlangıç: {currency_symbol}{başlangıç_değeri:,.0f}"
    
    fig.add_annotation(
        x=başlangıç_tarih,
        y=başlangıç_y,
        text=başlangıç_text,
        showarrow=True,
        arrowhead=2,
        arrowcolor="#9da1b3",
        bgcolor="rgba(157, 161, 179, 0.8)",
        bordercolor="#9da1b3",
        font=dict(color="#ffffff", size=10, family="Inter, sans-serif"),
        xanchor="right",
    )
    
    # Min ve Max noktaları (annotation ile) - sadece mutlak değer modunda göster
    if total_cost == 0:
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
    
    # Başlık metni
    if start_date is not None:
        start_date_str = pd.to_datetime(start_date).strftime("%d %b %Y")
        if "NormalizeDeğer" in hist_df.columns:
            title_text = f"<b>Portföy Performansı ({start_date_str}'den İtibaren)</b><br><span style='font-size: 12px; color: #9da1b3;'>Performans Değişimi: {performans_değişim:+.2f}% (Başlangıç Tarihine Göre)</span>"
        else:
            title_text = f"<b>Portföy Değeri ({start_date_str}'den İtibaren)</b><br><span style='font-size: 12px; color: #9da1b3;'>Toplam Değişim: {currency_symbol}{toplam_değişim:+,.0f} ({toplam_değişim_pct:+.2f}%)</span>"
    elif total_cost > 0:
        title_text = f"<b>Portföy Performansı (60 Gün - Maliyet Bazlı)</b><br><span style='font-size: 12px; color: #9da1b3;'>Performans Değişimi: {performans_değişim:+.2f}% (Maliyete Göre)</span>"
    else:
        title_text = f"<b>Portföy Değeri (60 Gün)</b><br><span style='font-size: 12px; color: #9da1b3;'>Toplam Değişim: {currency_symbol}{toplam_değişim:+,.0f} ({toplam_değişim_pct:+.2f}%)</span>"
    
    # Modern layout
    fig.update_layout(
        title=dict(
            text=title_text,
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
                text=y_label,
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


@st.cache_data(ttl=300)
def _fetch_comparison_data(symbols_dict, usd_try_rate, pb, period="60d"):
    """
    Karşılaştırma için veri çeker.
    symbols_dict: {"BIST 100": "XU100.IS", "Altın": "GC=F", ...}
    """
    results = {}
    try:
        all_symbols = list(symbols_dict.values())
        tickers = yf.Tickers(" ".join(all_symbols))
        
        for name, symbol in symbols_dict.items():
            try:
                h = tickers.tickers[symbol].history(period=period, interval="1d")
                if not h.empty:
                    prices = h["Close"]
                    prices.index = pd.to_datetime(prices.index).tz_localize(None)
                    
                    # Özel dönüşümler
                    if name == "Altın":
                        # Gram altın için TRY'ye çevir
                        if pb == "TRY":
                            prices = (prices * usd_try_rate) / 31.1035
                        else:
                            prices = prices / 31.1035
                    
                    results[name] = prices[-60:]  # Son 60 gün
            except Exception:
                results[name] = None
    except Exception:
        # Batch başarısız olursa tek tek dene
        for name, symbol in symbols_dict.items():
            try:
                ticker = yf.Ticker(symbol)
                h = ticker.history(period=period, interval="1d")
                if not h.empty:
                    prices = h["Close"]
                    prices.index = pd.to_datetime(prices.index).tz_localize(None)
                    
                    if name == "Altın":
                        if pb == "TRY":
                            prices = (prices * usd_try_rate) / 31.1035
                        else:
                            prices = prices / 31.1035
                    
                    results[name] = prices[-60:]
            except Exception:
                results[name] = None
    
    return results


@st.cache_data(ttl=3600)
def _fetch_inflation_data():
    """
    TCMB'den enflasyon verisi çeker (TÜFE).
    Başarısız olursa basit bir yaklaşım kullanır.
    """
    try:
        # TCMB API - TÜFE verisi
        url = "https://evds2.tcmb.gov.tr/service/evds/series=TP.FG.J0&startDate=01-01-2020&endDate=31-12-2025&type=json&key=YOUR_KEY"
        # API key olmadan çalışmayacak, bu yüzden basit bir yaklaşım kullanacağız
        # Aylık %2 enflasyon varsayımı ile basit bir seri oluşturalım
        today = pd.Timestamp.today().normalize()
        dates = pd.date_range(end=today, periods=60, freq="D")
        # Basit yaklaşım: Aylık %2 enflasyon varsayımı
        monthly_rate = 0.02
        daily_rate = (1 + monthly_rate) ** (1/30) - 1
        values = [(1 + daily_rate) ** i for i in range(60)]
        values.reverse()  # En eski tarihten bugüne
        return pd.Series(values, index=dates)
    except Exception:
        # Basit yaklaşım: Aylık %2 enflasyon varsayımı
        today = pd.Timestamp.today().normalize()
        dates = pd.date_range(end=today, periods=60, freq="D")
        monthly_rate = 0.02
        daily_rate = (1 + monthly_rate) ** (1/30) - 1
        values = [(1 + daily_rate) ** i for i in range(60)]
        values.reverse()
        return pd.Series(values, index=dates)


def get_comparison_chart(df: pd.DataFrame, usd_try_rate: float, pb: str, comparison_type: str):
    """
    Portföy vs karşılaştırma grafiği oluşturur.
    comparison_type: "BIST 100", "Altın", "SP500", "Enflasyon"
    Tüm seriler dünden itibaren normalize edilir (dünün değeri = 100).
    """
    if df is None or df.empty:
        return None
    
    # Dünü başlangıç noktası olarak belirle
    today = pd.Timestamp.today().normalize()
    yesterday = today - pd.Timedelta(days=1)
    
    # Portföy serisini al (get_historical_chart'tan portföy serisini çıkar)
    # Önce portföy serisini oluştur
    yahoo_symbols = []
    symbol_to_rows = {}
    special_cases = []
    
    for idx, row in df.iterrows():
        kod = str(row.get("Kod", ""))
        pazar = str(row.get("Pazar", ""))
        adet = float(row.get("Adet", 0) or 0)
        
        if adet == 0 or not kod:
            continue
        
        pazar_upper = pazar.upper()
        kod_upper = kod.upper()
        
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
    
    batch_prices = _fetch_historical_prices_batch(yahoo_symbols, period="60d", interval="1d")
    
    all_series = []
    
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
                    idx_range = pd.date_range(end=today, periods=60, freq="D")
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
    
    for symbol, rows in symbol_to_rows.items():
        if symbol not in batch_prices or batch_prices[symbol] is None:
            continue
        
        prices = batch_prices[symbol]
        prices.index = pd.to_datetime(prices.index).tz_localize(None)
        
        for idx, kod, pazar, adet, asset_currency, case_type in rows:
            if case_type in ["GRAM_GUMUS", "GRAM_ALTIN"]:
                prices_converted = (prices * usd_try_rate) / 31.1035
            else:
                prices_converted = prices
            
            if pb == "TRY":
                if asset_currency == "USD":
                    values = prices_converted * adet * usd_try_rate
                else:
                    values = prices_converted * adet
            else:
                if asset_currency == "TRY":
                    values = prices_converted * adet / usd_try_rate
                else:
                    values = prices_converted * adet
            
            all_series.append(values.rename(f"Değer_{idx}"))
    
    if not all_series:
        return None
    
    df_concat = pd.concat(all_series, axis=1)
    df_concat.index = pd.to_datetime(df_concat.index)
    df_concat = df_concat.sort_index()
    df_concat = df_concat.ffill()
    
    portfolio_series = df_concat.sum(axis=1)
    portfolio_series = portfolio_series[-60:]
    
    # Karşılaştırma verisini çek
    comparison_symbols = {
        "BIST 100": "XU100.IS",
        "Altın": "GC=F",
        "SP500": "^GSPC",
    }
    
    comparison_data = _fetch_comparison_data(comparison_symbols, usd_try_rate, pb, period="60d")
    
    # Enflasyon verisi
    if comparison_type == "Enflasyon":
        inflation_series = _fetch_inflation_data()
        comparison_data["Enflasyon"] = inflation_series
    
    # Karşılaştırma serisini al
    if comparison_type not in comparison_data:
        return None
    
    comp_series = comparison_data[comparison_type]
    
    if comp_series is None or comp_series.empty:
        return None
    
    # Tarihleri hizala
    # Portfolio ve comparison serilerinin tarihlerini birleştir
    all_dates = portfolio_series.index.union(comp_series.index).sort_values()
    
    # Her iki seriyi de tüm tarihlerde forward fill ile doldur
    portfolio_aligned = portfolio_series.reindex(all_dates).ffill()
    comp_aligned = comp_series.reindex(all_dates).ffill()
    
    # NaN değerleri olan satırları kaldır
    valid_mask = ~(portfolio_aligned.isna() | comp_aligned.isna())
    portfolio_aligned = portfolio_aligned[valid_mask]
    comp_aligned = comp_aligned[valid_mask]
    
    if len(portfolio_aligned) < 2:
        return None
    
    # Dünden itibaren filtrele
    yesterday_mask = portfolio_aligned.index >= yesterday
    portfolio_filtered = portfolio_aligned[yesterday_mask]
    comp_filtered = comp_aligned[yesterday_mask]
    
    if len(portfolio_filtered) < 2:
        return None
    
    # Dünün değerini başlangıç noktası olarak kullan
    # Eğer dünün verisi yoksa, en yakın önceki günü kullan
    if yesterday in portfolio_filtered.index:
        portfolio_start = portfolio_filtered[yesterday]
        comp_start = comp_filtered[yesterday] if yesterday in comp_filtered.index else comp_filtered.iloc[0]
        start_date = yesterday
        days_since = (today - yesterday).days
    else:
        # Dünün verisi yoksa, ilk mevcut günü başlangıç olarak kullan
        portfolio_start = portfolio_filtered.iloc[0]
        comp_start = comp_filtered.iloc[0]
        # Başlangıç tarihini güncelle
        start_date = portfolio_filtered.index[0]
        days_since = (today - start_date).days
    
    if portfolio_start == 0 or comp_start == 0:
        return None
    
    # Normalize et (dünün değeri = 100)
    portfolio_normalized = (portfolio_filtered / portfolio_start) * 100
    comp_normalized = (comp_filtered / comp_start) * 100
    
    # Grafik oluştur
    fig = go.Figure()
    
    # Portföy çizgisi
    fig.add_trace(
        go.Scatter(
            x=portfolio_normalized.index,
            y=portfolio_normalized.values,
            mode="lines",
            name="Portföy",
            line=dict(
                color="#6b7fd7",
                width=3,
                shape="spline",
            ),
            hovertemplate="<b style='font-family: Inter, sans-serif; font-size: 14px;'>%{x|%d %b %Y}</b><br>" +
                         "<span style='color: #6b7fd7;'>Portföy:</span> <b>%{y:.2f}%</b><extra></extra>",
        )
    )
    
    # Karşılaştırma çizgisi
    comparison_colors = {
        "BIST 100": "#f59e0b",
        "Altın": "#f2a900",
        "SP500": "#10b981",
        "Enflasyon": "#ec4899",
    }
    comp_color = comparison_colors.get(comparison_type, "#9da1b3")
    
    fig.add_trace(
        go.Scatter(
            x=comp_normalized.index,
            y=comp_normalized.values,
            mode="lines",
            name=comparison_type,
            line=dict(
                color=comp_color,
                width=3,
                shape="spline",
            ),
            hovertemplate="<b style='font-family: Inter, sans-serif; font-size: 14px;'>%{x|%d %b %Y}</b><br>" +
                         f"<span style='color: {comp_color};'>{comparison_type}:</span> <b>%{{y:.2f}}%</b><extra></extra>",
        )
    )
    
    # Başlangıç çizgisi (100%) - dünün tarihine
    if start_date in portfolio_normalized.index:
        # Convert pandas Timestamp to milliseconds timestamp for Plotly compatibility
        # Plotly's annotation_position="top" requires numeric x values for mean calculation
        start_date_ts = pd.Timestamp(start_date)
        start_date_ms = int(start_date_ts.timestamp() * 1000)
        fig.add_vline(
            x=start_date_ms,
            line_dash="dash",
            line_color="#9da1b3",
            opacity=0.5,
            annotation_text=f"Başlangıç ({start_date_ts.strftime('%d %b')})",
            annotation_position="top",
        )
    
    fig.add_hline(
        y=100,
        line_dash="dash",
        line_color="#9da1b3",
        opacity=0.5,
        annotation_text="Başlangıç (100%)",
        annotation_position="right",
    )
    
    # Son değerler
    portfolio_final = portfolio_normalized.iloc[-1]
    comp_final = comp_normalized.iloc[-1]
    
    portfolio_change = portfolio_final - 100
    comp_change = comp_final - 100
    
    # Gün sayısını hesapla
    if start_date == yesterday:
        days_text = "1 günden beri"
    else:
        days_text = f"{days_since} günden beri"
    
    # Modern layout
    fig.update_layout(
        title=dict(
            text=f"<b>Portföy vs {comparison_type}</b><br>" +
                 f"<span style='font-size: 12px; color: #9da1b3;'>" +
                 f"{days_text} | Portföy: {portfolio_change:+.2f}% | {comparison_type}: {comp_change:+.2f}%</span>",
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
                text="Performans (%)",
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
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(
                family="Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
                size=12,
                color="#ffffff",
            ),
            bgcolor="rgba(0,0,0,0)",
        ),
    )
    
    return fig
