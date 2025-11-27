#!/usr/bin/env python3
"""
Portföy analizi - DOĞRU SAYILARI
"""

import pandas as pd
import yfinance as yf
import sys
sys.path.insert(0, '/workspace')
from data_loader import get_tefas_data

# CSV - Türkçe format (virgül = ondalık, nokta = binlik)
csv_data = """Kod,Pazar,Adet,Maliyet,Tip
MEGMT,BIST (Tümü),119.00,30.26,Portfoy
UUUU,ABD (S&P + NASDAQ),10.92,21.59,Portfoy
Gram Altın (TL),EMTIA,2.46,5666.50,Portfoy
YHB,FON,36.072,1.32,Portfoy
GGK,FON,1.365,4.94,Portfoy
URA,FON,1.350,1.67,Portfoy
OTJ,FON,241.00,5.19,Portfoy
RUT,FON,684.00,1.83,Portfoy
TKFEN,BIST (Tümü),35.00,84.53,Portfoy
TRMET,BIST (Tümü),41.00,85.23,Portfoy
Gram Gümüş (TL),EMTIA,2672.84,63.93,Portfoy
GRID,ABD (S&P + NASDAQ),0.45,155.57,Portfoy
ACLS,ABD (S&P + NASDAQ),1.52,84.94,Portfoy
GFS,ABD (S&P + NASDAQ),3.68,35.57,Portfoy
NB,ABD (S&P + NASDAQ),11.00,9.94,Portfoy
CRDO,ABD (S&P + NASDAQ),0.81,143.96,Portfoy
CEG,ABD (S&P + NASDAQ),0.32,362.00,Portfoy
OSCR,ABD (S&P + NASDAQ),5.42,21.57,Portfoy
META,ABD (S&P + NASDAQ),0.39,596.97,Portfoy
AMZN,ABD (S&P + NASDAQ),1.03,225.80,Portfoy
TSLA,ABD (S&P + NASDAQ),0.57,405.98,Portfoy
MSFT,ABD,0.49,474.26,Portfoy
USD,NAKIT,703.50,42.22,Portfoy"""

from io import StringIO
df = pd.read_csv(StringIO(csv_data))

# USD/TRY
try:
    usd_try = yf.Ticker("TRY=X").history(period="1d")["Close"].iloc[-1]
except:
    usd_try = 34.20

print("="*100)
print("🔍 PORTFÖY ANALİZİ - DOĞRU SAYILARLA")
print("="*100)
print(f"💱 USD/TRY Kuru: {usd_try:.4f}\n")

total_maliyet_try = 0
total_deger_try = 0
results = []

for idx, row in df.iterrows():
    kod = row['Kod']
    pazar = row['Pazar']
    adet = float(row['Adet'])
    maliyet = float(row['Maliyet'])
    
    if adet == 0:
        continue
    
    # Para birimi
    if "BIST" in pazar.upper() or "FON" in pazar.upper() or "EMTIA" in pazar.upper():
        asset_currency = "TRY"
    elif "NAKIT" in pazar.upper() and kod != "USD":
        asset_currency = "TRY"
    else:
        asset_currency = "USD"
    
    # Fiyat çek
    curr_price = 0
    
    if "NAKIT" in pazar.upper():
        if kod == "USD":
            curr_price = usd_try
        elif kod == "TL":
            curr_price = 1
    
    elif "Gram Altın" in kod:
        ticker = yf.Ticker("GC=F")
        h = ticker.history(period="5d")
        if not h.empty:
            ons_price_usd = h["Close"].iloc[-1]
            curr_price = (ons_price_usd * usd_try) / 31.1035
    
    elif "Gram Gümüş" in kod:
        ticker = yf.Ticker("SI=F")
        h = ticker.history(period="5d")
        if not h.empty:
            ons_price_usd = h["Close"].iloc[-1]
            curr_price = (ons_price_usd * usd_try) / 31.1035
    
    elif "FON" in pazar:
        curr_price, _ = get_tefas_data(kod)
        if curr_price == 0 or curr_price > 100:
            curr_price = maliyet
    
    elif "BIST" in pazar.upper():
        symbol = f"{kod}.IS"
        ticker = yf.Ticker(symbol)
        h = ticker.history(period="5d")
        if not h.empty:
            curr_price = h["Close"].iloc[-1]
        else:
            curr_price = maliyet
    
    elif "ABD" in pazar or "S&P" in pazar or "NASDAQ" in pazar:
        ticker = yf.Ticker(kod)
        h = ticker.history(period="5d")
        if not h.empty:
            curr_price = h["Close"].iloc[-1]
        else:
            curr_price = maliyet
    
    if curr_price == 0:
        curr_price = maliyet
    
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
    
    emoji = "🟢" if kar_zarar_try >= 0 else "🔴"
    
    print(f"{emoji} {kod:15s} | Adet: {adet:10,.2f} | Maliyet: ₺{maliyet_try:12,.2f} | Değer: ₺{deger_try:12,.2f} | K/Z: ₺{kar_zarar_try:10,.2f}")
    
    results.append({
        'Kod': kod,
        'Maliyet (₺)': maliyet_try,
        'Değer (₺)': deger_try,
        'K/Z (₺)': kar_zarar_try,
    })

print("\n" + "="*100)
print("📊 GENEL ÖZET")
print("="*100)

total_kz = total_deger_try - total_maliyet_try
total_kz_pct = (total_kz / total_maliyet_try * 100) if total_maliyet_try > 0 else 0

print(f"\n   Toplam Maliyet:  ₺{total_maliyet_try:,.2f}")
print(f"   Toplam Değer:    ₺{total_deger_try:,.2f}")

if total_kz >= 0:
    print(f"   🟢 TOPLAM K/Z:   ₺{total_kz:,.2f} ({total_kz_pct:+.2f}%)")
else:
    print(f"   🔴 TOPLAM K/Z:   ₺{total_kz:,.2f} ({total_kz_pct:+.2f}%)")

print("\n" + "="*100)
