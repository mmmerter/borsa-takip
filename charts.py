import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import yfinance as yf
import pandas as pd
from utils import styled_dataframe
from data_loader import get_tefas_data

def render_pie_bar_charts(df, group_col, all_tab=False, varlik_gorunumu="YÜZDE (%)", total_spot_deger=0):
    if df.empty or "Değer" not in df.columns: return
    
    # Veri Gruplama
    agg = {"Değer": "sum"}
    if "Top. Kâr/Zarar" in df.columns: agg["Top. Kâr/Zarar"] = "sum"
    grouped = df.groupby(group_col, as_index=False).agg(agg)
    
    # Yüzde ve Diğer Hesabı
    tot = grouped["Değer"].sum()
    if tot > 0:
        grouped["_pct"] = grouped["Değer"] / tot * 100
        major = grouped[grouped["_pct"] >= 1].copy()
        minor = grouped[grouped["_pct"] < 1].copy()
        if not minor.empty:
            other = {group_col: "Diğer", "Değer": minor["Değer"].sum()}
            if "Top. Kâr/Zarar" in minor: other["Top. Kâr/Zarar"] = minor["Top. Kâr/Zarar"].sum()
            major = pd.concat([major, pd.DataFrame([other])], ignore_index=True)
            plot_df = major
        else: plot_df = grouped
    else: plot_df = grouped.copy()

    # Denominator Ayarı
    title_s = "(TUTAR)"
    if varlik_gorunumu == "YÜZDE (%)":
        denom = total_spot_deger if all_tab else plot_df["Değer"].sum()
        if denom > 0: plot_df["Değer"] = plot_df["Değer"] / denom * 100
        title_s = "(Portföy %)" if all_tab else "(Lokal %)"

    # Chart Texts
    texts = []
    for _, r in plot_df.iterrows():
        if r["Değer"] > 0: # Sıfırdan büyükse göster
            fmt = f"{r['Değer']:,.1f}%" if varlik_gorunumu == "YÜZDE (%)" else f"{r['Değer']:,.0f}"
            texts.append(f"{r[group_col]} {fmt}")
        else: texts.append("")

    c1, c2 = st.columns([4, 3])
    
    # PIE
    fig = px.pie(plot_df, values="Değer", names=group_col, hole=0.4, title=f"Dağılım {title_s}")
    fig.update_traces(text=texts, textinfo="text", textfont=dict(size=18, color="white", family="Arial Black"))
    fig.update_layout(legend=dict(font=dict(size=14)), margin=dict(t=40, b=40))
    c1.plotly_chart(fig, use_container_width=True)

    # BAR
    if "Top. Kâr/Zarar" in plot_df:
        fig2 = px.bar(plot_df.sort_values("Değer"), x=group_col, y="Değer", color="Top. Kâr/Zarar", text="Değer", title=f"Değerler {title_s}")
    else:
        fig2 = px.bar(plot_df.sort_values("Değer"), x=group_col, y="Değer", text="Değer", title=f"Değerler {title_s}")
    
    fmt_bar = "%{text:,.2f}%" if varlik_gorunumu == "YÜZDE (%)" else "%{text:,.0f}"
    fig2.update_traces(texttemplate=fmt_bar, textposition="outside", textfont=dict(size=14, color="white"))
    c2.plotly_chart(fig2, use_container_width=True)

def render_pazar_tab(df, filter_key, symb, usd_try, varlik_gorunumu, total_spot_deger):
    if df.empty: return st.info("Veri yok.")
    
    if filter_key == "VADELI": sub = df[df["Pazar"].str.contains("VADELI", na=False)]; is_vadeli=True
    elif filter_key == "Tümü": sub = df.copy(); is_vadeli=False
    else: sub = df[df["Pazar"].str.contains(filter_key, na=False)]; is_vadeli=False

    if sub.empty: return st.info("Yok.")
    
    tv = sub["Değer"].sum()
    tp = sub["Top. Kâr/Zarar"].sum()
    
    c1, c2 = st.columns(2)
    c1.metric("Toplam", f"{symb}{tv:,.0f}")
    
    if is_vadeli: c2.metric("PNL", f"{symb}{tp:,.0f}")
    else:
        tc = tv - tp
        pct = (tp / tc * 100) if tc != 0 else 0
        c2.metric("K/Z", f"{symb}{tp:,.0f}", delta=f"{pct:.2f}%")
    
    st.divider()
    
    if not is_vadeli:
        render_pie_bar_charts(sub, "Kod", filter_key=="Tümü", varlik_gorunumu, total_spot_deger)
    
    # Tablo Gösterimi
    disp = sub.copy()
    if varlik_gorunumu == "YÜZDE (%)" and not is_vadeli:
        disp.rename(columns={"Değer": "Tutar"}, inplace=True)
        denom = total_spot_deger if filter_key == "Tümü" else sub["Değer"].sum()
        if denom > 0: disp["Değer"] = disp["Tutar"] / denom * 100
        else: disp["Değer"] = 0
        
    st.dataframe(styled_dataframe(disp), use_container_width=True, hide_index=True)

def render_detail_view(symbol, pazar):
    # ... (Aynı)
    st.write(symbol)
def get_historical_chart(df, usd): return None
