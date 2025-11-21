import streamlit as st
import yfinance as yf
import pandas as pd
import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Portföy Yönetimi", layout="wide", page_icon="💰")
st.title("💰 Canlı Portföy Takibi (Bulut Kayıtlı)")

# --- GOOGLE SHEETS BAĞLANTISI ---
SHEET_NAME = "PortfoyData"  # Google Sheet'teki dosya adınla AYNI olmalı

def get_data_from_sheet():
    # Streamlit Secrets'tan bilgileri al
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = st.secrets["gcp_service_account"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    
    # Dosyayı aç
    sheet = client.open(SHEET_NAME).sheet1
    data = sheet.get_all_records()
    
    # Eğer boşsa boş DataFrame döndür
    if not data:
        return pd.DataFrame(columns=["Kod", "Pazar", "Adet", "Maliyet"])
    
    return pd.DataFrame(data)

def save_data_to_sheet(df):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = st.secrets["gcp_service_account"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    
    sheet = client.open(SHEET_NAME).sheet1
    sheet.clear() # Eski veriyi temizle
    
    # Başlıkları ve veriyi yaz
    sheet.update([df.columns.values.tolist()] + df.values.tolist())

# --- VERİLERİ YÜKLE ---
try:
    portfoy_df = get_data_from_sheet()
    # Sayısal çevirimleri garantiye al
    if not portfoy_df.empty:
        portfoy_df["Adet"] = pd.to_numeric(portfoy_df["Adet"])
        portfoy_df["Maliyet"] = pd.to_numeric(portfoy_df["Maliyet"])
except Exception as e:
    st.error(f"Google Sheet Hatası: {e}")
    portfoy_df = pd.DataFrame(columns=["Kod", "Pazar", "Adet", "Maliyet"])

# --- YAN MENÜ ---
with st.sidebar:
    st.header("⚙️ İşlemler")
    st.subheader("Yeni Hisse Ekle")
    with st.form("ekle_form", clear_on_submit=True):
        yeni_kod = st.text_input("Hisse Kodu").upper()
        yeni_pazar = st.selectbox("Pazar", ["BIST", "KRIPTO", "ABD"])
        yeni_adet = st.number_input("Adet", min_value=0.0, step=0.01)
        yeni_maliyet = st.number_input("Maliyet", min_value=0.0, step=0.01)
        
        if st.form_submit_button("Kaydet"):
            yeni_veri = pd.DataFrame({
                "Kod": [yeni_kod], "Pazar": [yeni_pazar], 
                "Adet": [yeni_adet], "Maliyet": [yeni_maliyet]
            })
            portfoy_df = pd.concat([portfoy_df, yeni_veri], ignore_index=True)
            save_data_to_sheet(portfoy_df) # Buluta kaydet
            st.success("Kaydedildi!")
            time.sleep(1)
            st.rerun()
    
    st.divider()
    
    st.subheader("Hisse Sil")
    if not portfoy_df.empty:
        silinecek = st.selectbox("Silinecek", portfoy_df["Kod"].unique())
        if st.button("Sil"):
            portfoy_df = portfoy_df[portfoy_df["Kod"] != silinecek]
            save_data_to_sheet(portfoy_df)
            st.rerun()

# --- HESAPLAMA VE GÖSTERİM (Eski kodun aynısı) ---
def sembol_duzelt(kod, pazar):
    if pazar == "BIST": return f"{kod}.IS"
    elif pazar == "KRIPTO": return f"{kod}-USD"
    else: return kod

def hesapla(df):
    if df.empty: return pd.DataFrame(), 0, 0
    sonuc = []
    t_deg, t_mal = 0, 0
    st.write("Veriler çekiliyor...")
    bar = st.progress(0)
    
    for i, row in df.iterrows():
        bar.progress((i+1)/len(df))
        sym = sembol_duzelt(row["Kod"], row["Pazar"])
        try:
            hist = yf.Ticker(sym).history(period="1d")
            if not hist.empty:
                fiyat = hist['Close'].iloc[-1]
                val = fiyat * row["Adet"]
                mal = row["Maliyet"] * row["Adet"]
                t_deg += val
                t_mal += mal
                sonuc.append({
                    "Kod": row["Kod"], "Adet": row["Adet"], "Maliyet": row["Maliyet"],
                    "Fiyat": fiyat, "Değer": val, "K/Z": val-mal, "Yüzde": ((fiyat-row["Maliyet"])/row["Maliyet"])*100
                })
            else:
                sonuc.append({"Kod": row["Kod"]+" (Hata)", "Adet":0, "Maliyet":0, "Fiyat":0, "Değer":0, "K/Z":0, "Yüzde":0})
        except: pass
    bar.empty()
    return pd.DataFrame(sonuc), t_deg, t_mal

if not portfoy_df.empty:
    df, val, cost = hesapla(portfoy_df)
    kar = val - cost
    yuzde = (kar/cost)*100 if cost > 0 else 0
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Varlık", f"{val:,.2f}")
    c2.metric("Maliyet", f"{cost:,.2f}")
    c3.metric("Kâr", f"{kar:,.2f}", delta=f"%{yuzde:.2f}")
    
    st.dataframe(df.style.format("{:.2f}"))
else:
    st.info("Hisse ekleyin.")
