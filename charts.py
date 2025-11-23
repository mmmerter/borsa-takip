import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import yfinance as yf
import pandas as pd

from utils import styled_dataframe
from data_loader import get_tefas_data


# --------------------------------------------------------------------
#  ORTAK PIE + BAR CHART (Fixed: Local vs Global Percentage Denominator)
# --------------------------------------------------------------------
def render_pie_bar_charts(df: pd.DataFrame, group_col: str, all_tab: bool = False, varlik_gorunumu: str = "YÜZDE (%)", total_spot_deger: float = 0):
    if df.empty or "Değer" not in df.columns:
        return

    # 1. ORTAK VERİ HAZIRLIĞI (Diğer'i gruplama)
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

    # Plot df üzerinde tekrar yüzdesel değerini hesapla
    total_plot_val = plot_df["Değer"].sum()
    plot_df["_pct"] = (plot_df["Değer"] / total_plot_val * 100) if total_plot_val > 0 else 0
    

    # --------------------------------------------------------------------
    # 2. GÖRÜNÜM TÜRÜNE GÖRE DEĞER SÜTUNUNU GÜNCELLE
    # --------------------------------------------------------------------
    title_suffix = "(TUTAR)"
    if varlik_gorunumu == "YÜZDE (%)":
        
        # Denominatör seçimi: all_tab (Tümü/Dashboard) ise GLOBAL toplam, değilse LOKAL (sekme) toplamı
        if all_tab: 
            denominator = total_spot_deger # GLOBAL toplamı kullan (Dashboard/Tümü için doğru)
            title_suffix = "(Portföy %)"
        else:
            denominator = total_plot_val # LOKAL toplamı kullan (BIST, FON vb. için düzeltildi)
            title_suffix = "(Lokal %)"
            
        if denominator > 0:
            plot_df["Değer"] = (plot_df["Değer"] / denominator * 100)
            
        else:
            plot_df["Değer"] = 0


    # Yazı eşiği:
    threshold = 5.0 if all_tab else 0.0

    texts = []
    for _, r in plot_df.iterrows():
        # Grafikte gösterilecek değer: Yüzde seçildiyse %'li değer, Tutar seçildiyse Tutar değeri
        value_to_display = r["Değer"]
        
        if varlik_gorunumu == "YÜZDE (%)":
            value_fmt = f"{value_to_display:,.1f}%"
        else:
            value_fmt = f"{value_to_display:,.1f}"

        if r["_pct"] >= threshold:
            # Buradaki yüzdesel kontrol (r["_pct"]), pastanın dilim büyüklüğüne göre yapılır (Local slice size)
            texts.append(f"{r[group_col]} {value_fmt}")
        else:
            texts.append("") # küçük dilimde yazı yok


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
        title=f"Portföy Dağılımı {title_suffix}"
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
            title=f"Varlık Değerleri {title_suffix}"
        )
    else:
        bar_fig = px.bar(
            plot_df.sort_values("Değer"),
            x=group_col,
            y="Değer",
            text="Değer",
            title=f"Varlık Değerleri {title_suffix}"
        )

    # Bar chart metin formatı da görünüme göre değişmeli
    if varlik_gorunumu == "YÜZDE (%)":
        bar_text_template = "%{text:,.2f}%"
    else:
        bar_text_template = "%{text:,.0f}"

    bar_fig.update_traces(
        texttemplate=bar_text_template,
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
    """KRAL'daki gibi None dönüyor."""
    return None


# --------------------------------------------------------------------
#  SEKME BAZLI PAZAR EKRANI (SEKTÖR GRAFİĞİ EKLENDİ)
# --------------------------------------------------------------------
def render_pazar_tab(df, filter_key, symb, usd_try, varlik_gorunumu, total_spot_deger):
    if df.empty:
        return st.info("Veri yok.")

    # 1. Filtreleme
    if filter_key == "VADELI":
        sub = df[df["Pazar"].str.contains("VADELI", na=False)]
        is_vadeli = True
    elif filter_key == "Tümü":
        sub = df.copy()
        is_vadeli = False
    else:
        sub = df[df["Pazar"].str.contains(filter_key, na=False)]
        is_vadeli = False


    if sub.empty:
        return st.info(f"{filter_key} yok.")

    total_val = sub["Değer"].sum()
    total_pnl = sub["Top. Kâr/Zarar"].sum()

    col1, col2 = st.columns(2)

    label = "Toplam PNL" if is_vadeli else "Toplam Varlık"
    col1.metric(label, f"{symb}{total_val:,.0f}")

    # Metrikte Yüzde Hesaplama (Sadece spot varlıklar için)
    if is_vadeli:
        col2.metric(
            "Toplam Kâr/Zarar",
            f"{symb}{total_pnl:,.0f}",
            delta=f"{symb}{total_pnl:,.0f}",
        )
    else:
        total_cost = (total_val - total_pnl)
        pct = (total_pnl / total_cost * 100) if total_cost != 0 else 0
        col2.metric(
            "Toplam Kâr/Zarar",
            f"{symb}{total_pnl:,.0f}",
            delta=f"{pct:.2f}%",
        )

    st.divider()
    
    # 2. SEKTÖR DAĞILIMI GRAFİĞİ (YENİ KISIM)
    if not is_vadeli and filter_key not in ["EMTIA", "KRIPTO"]:

        # Sektörlere göre grupla
        sector_data = sub[sub["Sektör"] != ""].copy()
        sector_data_grouped = sector_data.groupby("Sektör", as_index=False).agg({"Değer": "sum", "Top. Kâr/Zarar": "sum"})

        # Lokal Denominator (Grafiğin Lokal Total'ini kullanmak için)
        local_total_for_sector = sub["Değer"].sum()

        if not sector_data_grouped.empty:
            st.subheader(f"📊 {filter_key} Sektör Dağılımı")
            render_pie_bar_charts(
                sector_data_grouped, 
                "Sektör", 
                all_tab=filter_key == "Tümü", # Tümü sekmesi global, diğerleri lokal yüzdelik için
                varlik_gorunumu=varlik_gorunumu,
                total_spot_deger=total_spot_deger # Global total'i geçiriyoruz, all_tab=False olduğunda lokal total kullanılır
            )
            st.divider()


    # 3. KOD BAZLI VARLIK DAĞILIMI GRAFİĞİ (ESKİ KISIM)
    if not is_vadeli:
        is_all_tab = filter_key == "Tümü"
        
        st.subheader(f"📊 {filter_key} Kod Bazlı Dağılım")
        render_pie_bar_charts(sub, "Kod", all_tab=is_all_tab, varlik_gorunumu=varlik_gorunumu, total_spot_deger=total_spot_deger)

    # 4. Tablo Gösterimi (Yüzde veya Tutar)
    df_display = sub.copy()
    
    # Yüzde Görünümü seçiliyse ve Vadeli değilse:
    if varlik_gorunumu == "YÜZDE (%)" and not is_vadeli:
        # Tutar kolonu ismini 'Değer'den 'Tutar'a çeviriyoruz
        df_display.rename(columns={"Değer": "Tutar"}, inplace=True)
        
        # Denominatör seçimi: filter_key="Tümü" ise GLOBAL, diğer sekmeler LOKAL toplamı kullanır.
        if filter_key == "Tümü":
            denominator = total_spot_deger
        else:
            denominator = sub["Değer"].sum() # Lokal toplam
        
        # Yüzdeyi hesaplayıp yeni 'Değer' kolonu olarak atıyoruz (Styler'ın algılaması için)
        if denominator > 0:
            df_display["Değer"] = (df_display["Tutar"] / denominator * 100)
        else:
            df_display["Değer"] = 0

    st.dataframe(
        styled_dataframe(df_display),
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
        st.error(f"Veri çekilemedi: {e}")
