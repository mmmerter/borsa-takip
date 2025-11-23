import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import yfinance as yf
import pandas as pd
from utils import styled_dataframe, get_yahoo_symbol, SECTOR_MAPPING
from data_loader import get_tefas_data, get_historical_prices, get_usd_try_history, get_fund_history

def render_pie_bar_charts(df, group_col, all_tab=False, varlik_gorunumu="YÜZDE (%)", total_spot_deger=0):
    if df.empty or "Değer" not in df.columns: return
    
    agg = {"Değer": "sum"}
    if "Top. Kâr/Zarar" in df.columns: agg["Top. Kâr/Zarar"] = "sum"
    # Sektör ise şirketleri topla
    if group_col == "Sektör" and "Kod" in df.columns: agg["Kod"] = lambda x: '<br>'.join(x.unique())

    grouped = df.groupby(group_col, as_index=False).agg(agg)
    if group_col == "Sektör": grouped.rename(columns={'Kod': 'Şirketler'}, inplace=True)

    tot = grouped["Değer"].sum()
    if tot > 0:
        grouped["_pct"] = grouped["Değer"] / tot * 100
        major = grouped[grouped["_pct"] >= 1].copy()
        minor = grouped[grouped["_pct"] < 1].copy()
        if not minor.empty:
            other = {group_col: "Diğer", "Değer": minor["Değer"].sum()}
            if "Top. Kâr/Zarar" in minor: other["Top. Kâr/Zarar"] = minor["Top. Kâr/Zarar"].sum()
            if group_col == "Sektör": other["Şirketler"] = '<br>'.join(minor['Şirketler'].explode().unique().tolist())
            major = pd.concat([major, pd.DataFrame([other])], ignore_index=True)
            plot_df = major
        else: plot_df = grouped
    else: plot_df = grouped.copy()

    title_s = "(TUTAR)"
    if varlik_gorunumu == "YÜZDE (%)":
        denom = total_spot_deger if all_tab else plot_df["Değer"].sum()
        if denom > 0: plot_df["Değer"] = plot_df["Değer"] / denom * 100
        title_s = "(Portföy %)" if all_tab else "(Lokal %)"

    texts = []
    for _, r in plot_df.iterrows():
        if r["Değer"] > 0: 
            fmt = f"{r['Değer']:,.1f}%" if varlik_gorunumu == "YÜZDE (%)" else f"{r['Değer']:,.0f}"
            texts.append(f"{r[group_col]} {fmt}")
        else: texts.append("")

    c1, c2 = st.columns([4, 3])
    
    # Tooltip
    hover_cols = ["Değer", "Top. Kâr/Zarar"]
    if group_col == "Sektör" and "Şirketler" in plot_df.columns: hover_cols.insert(0, 'Şirketler')
    
    fig = px.pie(plot_df, values="Değer", names=group_col, hole=0.4, title=f"Dağılım {title_s}", custom_data=hover_cols)
    
    ht = '<b>%{label}</b><br>'
    if 'Şirketler' in hover_cols: ht += 'Şirketler: %{customdata[0]}<br>'
    ht += 'Değer: %{customdata[' + str(len(hover_cols)-2) + ']:.2f}<br>K/Z: %{customdata[' + str(len(hover_cols)-1) + ']:.2f}'

    fig.update_traces(text=texts, textinfo="text", textfont=dict(size=18, color="white", family="Arial Black"), hovertemplate=ht)
    fig.update_layout(legend=dict(font=dict(size=14)), margin=dict(t=40, b=40))
    c1.plotly_chart(fig, use_container_width=True)

    fig2 = px.bar(plot_df.sort_values("Değer"), x=group_col, y="Değer", color="Top. Kâr/Zarar" if "Top. Kâr/Zarar" in plot_df else None, text="Değer", title=f"Değerler {title_s}")
    fmt_bar = "%{text:,.2f}%" if varlik_gorunumu == "YÜZDE (%)" else "%{text:,.0f}"
    fig2.update_traces(texttemplate=fmt_bar, textposition="outside", textfont=dict(size=14, color="white"))
    c2.plotly_chart(fig2, use_container_width=True)

def get_historical_chart(df_portfolio, usd_try, gorunum_pb):
    # Bu fonksiyon 1 yillik gecmis degeri hesaplar
    if df_portfolio.empty: return None
    
    # Map assets
    symbol_map = {}
    fund_map = []
    
    for _, row in df_portfolio.iterrows():
        if "FON" in row["Pazar"]: fund_map.append((row["Kod"], row["Adet"]))
        elif "VADELI" not in row["Pazar"]: 
            s = get_yahoo_symbol(row["Kod"], row["Pazar"])
            symbol_map[row["Kod"]] = s

    # Fetch Data
    hist_df = pd.DataFrame()
    
    # Yahoo
    if symbol_map:
        yh = get_historical_prices(symbol_map)
        if not yh.empty:
            # Miktar ile çarp
            for kod, sym in symbol_map.items():
                if kod in yh.columns:
                    adet = df_portfolio[df_portfolio["Kod"] == kod]["Adet"].sum()
                    # Currency Check (Basitce: BIST disi USD varsayalim, BIST TRY)
                    # Daha dogrusu veriyi cektigimiz yere gore.
                    # Yahoo BIST verisi TRY gelir. USD verisi USD gelir.
                    # Bizim portfoyde Pazar'a bakarak karar verelim.
                    pazar = df_portfolio[df_portfolio["Kod"] == kod]["Pazar"].iloc[0]
                    
                    val_series = yh[kod] * adet
                    
                    # Eger USD ise ve gorunum TRY ise -> carp
                    # Eger TRY ise ve gorunum USD ise -> bol
                    # Bunun icin USDTRY tarihsel lazim
                    if "ABD" in pazar or "KRIPTO" in pazar or "EMTIA" in pazar: # Genelde USD
                         # (Altin/Gumus ons ise USD, gram ise TRY. Ama kodda "Gram" kontrolu var)
                         if "Gram" not in kod: # USD bazli
                             # Bunu TRY'ye cevirip saklayalim, sonra gorunume gore tekrar isleriz
                             # Veya direkt gorunum neyse ona cevir.
                             pass
                    
                    hist_df[kod] = val_series # Simdilik native birak, sonra toplayalim (ZOR - Kur lazim)
                    
    # Simdilik basit: Sadece kapanis fiyatlarini alip, o gunku kurla carpmiyoruz (cok agir olur).
    # Sadece mevcut varliklarin "Bugunku degeri" degil, "Gecmis performansi".
    # Bu kisim karmasik oldugu icin, sadece basit bir "Simdiki fiyatin gecmisi" grafigi cizelim (Normalized)
    # YA DA: Her varligin 1 yillik grafigini normalize edip gosterelim? 
    # HAYIR, Portfoy Buyuklugu isteniyor.
    
    # KOLAY YOL: Her varligin native tarihsel fiyatini al.
    # USDTRY tarihselini al.
    # Hepsini TRY'ye cevirip topla. (Veya USD'ye)
    
    try:
        usd_hist = get_usd_try_history()["TRY=X"]
        
        total_series = pd.Series(0, index=usd_hist.index)
        # Yahoo varliklari
        if symbol_map:
            yh = get_historical_prices(symbol_map) # Index date, cols codes
            # Reindex to match usd_hist
            yh = yh.reindex(usd_hist.index).ffill()
            
            for kod in yh.columns:
                row = df_portfolio[df_portfolio["Kod"] == kod].iloc[0]
                adet = row["Adet"]
                pazar = row["Pazar"]
                
                price_series = yh[kod]
                val_series = price_series * adet
                
                # Convert to Gorunum PB
                # Varsayim: BIST, FON, NAKIT(TL) -> TRY. Digerleri -> USD.
                is_try_asset = "BIST" in pazar or "FON" in pazar or "TL" in kod or "Gram" in kod
                
                if is_try_asset:
                    if gorunum_pb == "USD": val_series = val_series / usd_hist
                else: # USD asset
                    if gorunum_pb == "TRY": val_series = val_series * usd_hist
                
                total_series = total_series.add(val_series, fill_value=0)

        # Fonlar
        for f, adet in fund_map:
            fh = get_fund_history(f)
            if not fh.empty:
                fh = fh.reindex(usd_hist.index).ffill()
                val = fh * adet
                if gorunum_pb == "USD": val = val / usd_hist
                total_series = total_series.add(val, fill_value=0)
        
        # Cizim
        total_series = total_series.dropna()
        if total_series.empty: return None
        
        fig = px.area(total_series, title=f"Portföy Değeri ({gorunum_pb}) - Son 1 Yıl")
        fig.update_layout(showlegend=False, margin=dict(l=0, r=0, t=40, b=0))
        return fig

    except Exception as e:
        print(e)
        return None


def render_pazar_tab(df, filter_key, symb, usd_try, varlik_gorunumu, total_spot_deger):
    if df.empty: return st.info("Veri yok.")
    
    if filter_key == "Tümü": sub = df.copy()
    else: sub = df[df["Pazar"].str.contains(filter_key, na=False)]

    if sub.empty: return st.info("Yok.")
    
    tv = sub["Değer"].sum()
    tp = sub["Top. Kâr/Zarar"].sum()
    
    c1, c2 = st.columns(2)
    c1.metric("Toplam", f"{symb}{tv:,.0f}")
    tc = tv - tp
    pct = (tp / tc * 100) if tc != 0 else 0
    c2.metric("K/Z", f"{symb}{tp:,.0f}", delta=f"{pct:.2f}%")
    
    st.divider()
    
    # --- TARIHSEL GRAFIK (HER SEKME ICIN) ---
    st.subheader(f"📈 {filter_key} Tarihsel Değer")
    h_chart = get_historical_chart(sub, usd_try, "TRY" if symb=="₺" else "USD")
    if h_chart: st.plotly_chart(h_chart, use_container_width=True)
    
    # --- ESKI KOD BAZLI DAGILIM (USTTE) ---
    st.subheader(f"📊 {filter_key} Kod Bazlı Dağılım")
    render_pie_bar_charts(sub, "Kod", filter_key=="Tümü", varlik_gorunumu, total_spot_deger)
    
    st.divider()

    # --- SEKTOR DAGILIMI (ALTTA) ---
    if filter_key not in ["EMTIA", "KRIPTO", "NAKIT"]:
        s_data = sub[sub["Sektör"] != ""].copy()
        s_data["Sektör"] = s_data["Sektör"].map(SECTOR_MAPPING).fillna(s_data["Sektör"])
        s_grp = s_data.groupby("Sektör", as_index=False).agg({"Değer": "sum", "Top. Kâr/Zarar": "sum", "Kod": lambda x: '<br>'.join(x.unique())})
        s_grp.rename(columns={'Kod': 'Şirketler'}, inplace=True)
        
        if not s_grp.empty:
            st.subheader(f"🏭 {filter_key} Sektör Dağılımı")
            render_pie_bar_charts(s_grp, "Sektör", filter_key=="Tümü", varlik_gorunumu, total_spot_deger)

    # Tablo
    disp = sub.copy()
    if varlik_gorunumu == "YÜZDE (%)":
        disp.rename(columns={"Değer": "Tutar"}, inplace=True)
        denom = total_spot_deger if filter_key == "Tümü" else sub["Değer"].sum()
        if denom > 0: disp["Değer"] = disp["Tutar"] / denom * 100
        else: disp["Değer"] = 0
        
    st.dataframe(styled_dataframe(disp), use_container_width=True, hide_index=True)

def render_detail_view(symbol, pazar):
    st.write(symbol) # Stub
