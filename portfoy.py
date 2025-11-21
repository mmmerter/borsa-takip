import streamlit as st
import yfinance as yf
import pandas as pd
import time
import os

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Portföy Yönetimi", layout="wide", page_icon="💰")
st.title("💰 Canlı Portföy Takibi")

# --- DOSYA İŞLEMLERİ ---
dosya_adi = "portfoy.csv"

def veri_yukle():
    if os.path.exists(dosya_adi):
        return pd.read_csv(dosya_adi)
    else:
        return pd.DataFrame(columns=["Kod", "Pazar", "Adet", "Maliyet"])

def veri_kaydet(df):
    df.to_csv(dosya_adi, index=False)

# Verileri Yükle
portfoy_df = veri_yukle()

# --- YAN MENÜ ---
with st.sidebar:
    st.header("⚙️ İşlemler")
    
    # HİSSE EKLEME
    st.subheader("Yeni Hisse Ekle")
    with st.form("ekle_form", clear_on_submit=True):
        yeni_kod = st.text_input("Hisse Kodu (Örn: THYAO, BTC)").upper()
        yeni_pazar = st.selectbox("Pazar Seç", ["BIST", "KRIPTO", "ABD"])
        yeni_adet = st.number_input("Adet", min_value=0.0, step=0.01, format="%.2f")
        yeni_maliyet = st.number_input("Birim Maliyet", min_value=0.0, step=0.01, format="%.2f")
        
        ekle_btn = st.form_submit_button("Portföye Ekle")
        
        if ekle_btn:
            if yeni_kod and yeni_adet > 0:
                yeni_veri = pd.DataFrame({
                    "Kod": [yeni_kod], 
                    "Pazar": [yeni_pazar], 
                    "Adet": [yeni_adet], 
                    "Maliyet": [yeni_maliyet]
                })
                portfoy_df = pd.concat([portfoy_df, yeni_veri], ignore_index=True)
                veri_kaydet(portfoy_df)
                st.success(f"{yeni_kod} eklendi!")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("Eksik bilgi girdiniz.")

    st.divider()

    # HİSSE SİLME
    st.subheader("Hisse Sil")
    if not portfoy_df.empty:
        silinecek = st.selectbox("Silinecek Hisse", portfoy_df["Kod"].unique())
        if st.button("Seçili Olanı Sil"):
            portfoy_df = portfoy_df[portfoy_df["Kod"] != silinecek]
            veri_kaydet(portfoy_df)
            st.warning(f"{silinecek} silindi.")
            time.sleep(0.5)
            st.rerun()

# --- CANLI VERİ ÇEKME ---
def sembol_duzelt(kod, pazar):
    if pazar == "BIST": return f"{kod}.IS"
    elif pazar == "KRIPTO": return f"{kod}-USD"
    else: return kod

def hesapla(df):
    if df.empty:
        return pd.DataFrame(), 0, 0

    sonuc_listesi = []
    toplam_deger = 0
    toplam_maliyet = 0
    
    st.write("⏳ Veriler güncelleniyor...")
    bar = st.progress(0)
    
    for i, row in df.iterrows():
        bar.progress((i + 1) / len(df))
        symbol = sembol_duzelt(row["Kod"], row["Pazar"])
        
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="1d")
            
            if not hist.empty:
                fiyat = hist['Close'].iloc[-1]
                adet = row["Adet"]
                maliyet = row["Maliyet"]
                
                guncel_deger = fiyat * adet
                maliyet_toplam = maliyet * adet
                kar_tl = guncel_deger - maliyet_toplam
                kar_yuzde = ((fiyat - maliyet) / maliyet) * 100 if maliyet > 0 else 0
                
                toplam_deger += guncel_deger
                toplam_maliyet += maliyet_toplam
                
                sonuc_listesi.append({
                    "Kod": row["Kod"],
                    "Adet": adet,
                    "Ort. Maliyet": maliyet,
                    "Anlık Fiyat": fiyat,
                    "Toplam Değer": guncel_deger,
                    "Kâr/Zarar": kar_tl,
                    "Değişim %": kar_yuzde
                })
            else:
                 sonuc_listesi.append({
                    "Kod": row["Kod"] + " (Hata)",
                    "Adet": row["Adet"], "Ort. Maliyet": row["Maliyet"],
                    "Anlık Fiyat": 0, "Toplam Değer": 0, "Kâr/Zarar": 0, "Değişim %": 0
                })
        except:
            pass
        time.sleep(0.1)
        
    bar.empty()
    return pd.DataFrame(sonuc_listesi), toplam_deger, toplam_maliyet

# --- ANA EKRAN ---
if not portfoy_df.empty:
    sonuc_df, t_val, t_cost = hesapla(portfoy_df)
    
    # Kâr Zarar Hesabı
    if t_cost > 0:
        genel_kar = t_val - t_cost
        genel_yuzde = (genel_kar / t_cost) * 100
    else:
        genel_kar = 0
        genel_yuzde = 0

    c1, c2, c3 = st.columns(3)
    c1.metric("Toplam Varlık", f"{t_val:,.2f}")
    c2.metric("Ana Para", f"{t_cost:,.2f}")
    c3.metric("Net Durum", f"{genel_kar:,.2f}", delta=f"%{genel_yuzde:.2f}")
    
    st.divider()
    
    def renk(val):
        color = '#2ecc71' if val > 0 else '#e74c3c' if val < 0 else 'white'
        return f'color: {color}; font-weight: bold'

    if not sonuc_df.empty:
        st.dataframe(
            sonuc_df.style.map(renk, subset=['Kâr/Zarar', 'Değişim %'])
                    .format({
                        "Adet": "{:.2f}",
                        "Ort. Maliyet": "{:.2f}",
                        "Anlık Fiyat": "{:.2f}",
                        "Toplam Değer": "{:.2f}",
                        "Kâr/Zarar": "{:.2f}",
                        "Değişim %": "{:.2f}"
                    }),
            use_container_width=True,
            height=500,
            hide_index=True
        )
else:
    st.info("👈 Sol taraftaki menüden hisse ekleyerek başla!")