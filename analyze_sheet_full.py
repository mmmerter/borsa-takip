#!/usr/bin/env python3
"""
Portföy analizi - TEFAS fonları dahil
"""

import pandas as pd
import yfinance as yf
from datetime import datetime
import sys
sys.path.insert(0, '/workspace')

from data_loader import get_tefas_data

# CSV verisini oku
csv_data = """Kod,Pazar,Adet,Maliyet,Tip,Notlar
MEGMT,BIST (Tümü),119.00,30.26,Portfoy,
UUUU,ABD (S&P + NASDAQ),10.92,21.59,Portfoy,
Gram Altın (TL),EMTIA,2.46,"5,666.50",Portfoy,
YHB,FON,"36,072.00",1.32,Portfoy,
GGK,FON,"1,365.00",4.94,Portfoy,
URA,FON,"1,350.00",1.67,Portfoy,
OTJ,FON,241.00,5.19,Portfoy,
RUT,FON,684.00,1.83,Portfoy,
TKFEN,BIST (Tümü),35.00,84.53,Portfoy,
TRMET,BIST (Tümü),41.00,85.23,Portfoy,
Gram Gümüş (TL),EMTIA,"2,672.84",63.93,Portfoy,
GRID,ABD (S&P + NASDAQ),0.45,155.57,Portfoy,
ACLS,ABD (S&P + NASDAQ),1.52,84.94,Portfoy,
GFS,ABD (S&P + NASDAQ),3.68,35.57,Portfoy,
NB,ABD (S&P + NASDAQ),11.00,9.94,Portfoy,
CRDO,ABD (S&P + NASDAQ),0.81,143.96,Portfoy,
CEG,ABD (S&P + NASDAQ),0.32,362.00,Portfoy,
OSCR,ABD (S&P + NASDAQ),5.42,21.57,Portfoy,
META,ABD (S&P + NASDAQ),0.39,596.97,Portfoy,
AMZN,ABD (S&P + NASDAQ),1.03,225.80,Portfoy,
TSLA,ABD (S&P + NASDAQ),0.57,405.98,Portfoy,
MSFT,ABD,0.49,474.26,Portfoy,
USD,NAKIT,703.50,42.22,Portfoy,"""

# Parse CSV
from io import StringIO
df = pd.read_csv(StringIO(csv_data))

# Sayıları düzelt
def clean_number(val):
    if pd.isna(val):
        return 0.0
    val_str = str(val).replace(',', '')
    try:
        return float(val_str)
    except:
        return 0.0

df['Adet'] = df['Adet'].apply(clean_number)
df['Maliyet'] = df['Maliyet'].apply(clean_number)

# USD/TRY kuru çek
try:
    usd_try = yf.Ticker("TRY=X").history(period="1d")["Close"].iloc[-1]
except:
    usd_try = 34.20

print("="*100)
print("🔍 PORTFÖY ANALİZİ - FON FİYATLARI DAHİL")
print("="*100)
print(f"💱 USD/TRY Kuru: {usd_try:.4f}\n")

portfolio = df[df['Tip'] == 'Portfoy'].copy()

results = []
total_maliyet_try = 0
total_deger_try = 0

for idx, row in portfolio.iterrows():
    kod = row['Kod']
    pazar = row['Pazar']
    adet = row['Adet']
    maliyet = row['Maliyet']
    
    if adet == 0:
        continue
    
    print(f"\n{'─'*100}")
    print(f"🎯 {kod} ({pazar})")
    
    # Para birimini belirle
    if "BIST" in pazar.upper() or "FON" in pazar.upper() or "EMTIA" in pazar.upper():
        asset_currency = "TRY"
    elif "NAKIT" in pazar.upper() and kod != "USD":
        asset_currency = "TRY"
    else:
        asset_currency = "USD"
    
    # Fiyat çek
    curr_price = 0
    price_source = ""
    
    try:
        if "NAKIT" in pazar.upper():
            if kod == "USD":
                curr_price = usd_try
                price_source = "✅ TCMB USD/TRY"
            elif kod == "TL":
                curr_price = 1
                price_source = "✅ Sabit"
        
        elif "Gram Altın" in kod:
            ticker = yf.Ticker("GC=F")
            h = ticker.history(period="5d")
            if not h.empty:
                ons_price_usd = h["Close"].iloc[-1]
                curr_price = (ons_price_usd * usd_try) / 31.1035
                price_source = f"✅ Yahoo (${ons_price_usd:.2f}/oz)"
        
        elif "Gram Gümüş" in kod:
            ticker = yf.Ticker("SI=F")
            h = ticker.history(period="5d")
            if not h.empty:
                ons_price_usd = h["Close"].iloc[-1]
                curr_price = (ons_price_usd * usd_try) / 31.1035
                price_source = f"✅ Yahoo (${ons_price_usd:.2f}/oz)"
        
        elif "FON" in pazar:
            # TEFAS API'sini kullan
            print(f"   📡 TEFAS'tan {kod} fiyatı çekiliyor...")
            curr_price, _ = get_tefas_data(kod)
            if curr_price > 0 and curr_price < 100:
                price_source = f"✅ TEFAS API"
            else:
                curr_price = maliyet
                price_source = f"⚠️ TEFAS'tan çekilemedi - Maliyet kullanıldı"
        
        elif "BIST" in pazar.upper():
            symbol = f"{kod}.IS"
            ticker = yf.Ticker(symbol)
            h = ticker.history(period="5d")
            if not h.empty:
                curr_price = h["Close"].iloc[-1]
                price_source = f"✅ Yahoo ({symbol})"
            else:
                curr_price = maliyet
                price_source = f"⚠️ Veri yok - Maliyet"
        
        elif "ABD" in pazar or "S&P" in pazar or "NASDAQ" in pazar:
            ticker = yf.Ticker(kod)
            h = ticker.history(period="5d")
            if not h.empty:
                curr_price = h["Close"].iloc[-1]
                price_source = f"✅ Yahoo ({kod})"
            else:
                curr_price = maliyet
                price_source = f"⚠️ Veri yok - Maliyet"
    
    except Exception as e:
        curr_price = maliyet
        price_source = f"❌ Hata - Maliyet"
    
    print(f"   Maliyet: {maliyet:,.4f} {asset_currency} × {adet:,.2f} adet")
    print(f"   Güncel:  {curr_price:,.4f} {asset_currency}")
    print(f"   Kaynak:  {price_source}")
    
    # TRY'ye çevir
    if asset_currency == "TRY":
        maliyet_try = maliyet * adet
        deger_try = curr_price * adet
    else:
        maliyet_try = maliyet * adet * usd_try
        deger_try = curr_price * adet * usd_try
    
    kar_zarar_try = deger_try - maliyet_try
    kar_zarar_pct = (kar_zarar_try / maliyet_try * 100) if maliyet_try > 0 else 0
    
    total_maliyet_try += maliyet_try
    total_deger_try += deger_try
    
    if kar_zarar_try >= 0:
        print(f"   🟢 K/Z: ₺{kar_zarar_try:,.2f} ({kar_zarar_pct:+.2f}%)")
        emoji = "🟢"
    else:
        print(f"   🔴 K/Z: ₺{kar_zarar_try:,.2f} ({kar_zarar_pct:+.2f}%)")
        emoji = "🔴"
    
    results.append({
        'Emoji': emoji,
        'Kod': kod,
        'Maliyet (₺)': maliyet_try,
        'Değer (₺)': deger_try,
        'K/Z (₺)': kar_zarar_try,
        'K/Z %': kar_zarar_pct,
    })

# Özet
print("\n" + "="*100)
print("📊 GENEL ÖZET (FON FİYATLARI DAHİL)")
print("="*100)

total_kz = total_deger_try - total_maliyet_try
total_kz_pct = (total_kz / total_maliyet_try * 100) if total_maliyet_try > 0 else 0

print(f"\n   Toplam Maliyet:  ₺{total_maliyet_try:,.2f}")
print(f"   Toplam Değer:    ₺{total_deger_try:,.2f}")

if total_kz >= 0:
    print(f"   🟢 TOPLAM K/Z:   ₺{total_kz:,.2f} ({total_kz_pct:+.2f}%)")
    print(f"\n   🎉 Portföyünüz kârda!")
else:
    print(f"   🔴 TOPLAM K/Z:   ₺{total_kz:,.2f} ({total_kz_pct:+.2f}%)")
    print(f"\n   ⚠️ Portföyünüz zararda.")

# K/Z listesi
results_df = pd.DataFrame(results)
losers = results_df[results_df['K/Z (₺)'] < 0].sort_values('K/Z (₺)')
winners = results_df[results_df['K/Z (₺)'] > 0].sort_values('K/Z (₺)', ascending=False)

if not losers.empty:
    print("\n" + "="*100)
    print(f"🔴 ZARARDAKI VARLIKLAR ({len(losers)} adet)")
    print("="*100)
    for _, row in losers.iterrows():
        print(f"   {row['Emoji']} {row['Kod']:15s} | ₺{row['K/Z (₺)']:12,.2f} ({row['K/Z %']:6.2f}%)")
    print(f"\n💸 Toplam Zarar: ₺{losers['K/Z (₺)'].sum():,.2f}")

if not winners.empty:
    print("\n" + "="*100)
    print(f"🟢 KÂRDAKI VARLIKLAR ({len(winners)} adet)")
    print("="*100)
    for _, row in winners.iterrows():
        print(f"   {row['Emoji']} {row['Kod']:15s} | ₺{row['K/Z (₺)']:12,.2f} ({row['K/Z %']:6.2f}%)")
    print(f"\n💰 Toplam Kâr: ₺{winners['K/Z (₺)'].sum():,.2f}")

print("\n" + "="*100)
