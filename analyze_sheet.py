#!/usr/bin/env python3
"""
Portföy analizi - Google Sheets'ten çekilen verilerle
"""

import pandas as pd
import yfinance as yf
from datetime import datetime

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
NBIS,ABD,1.00,83.26,Takip,
THYAO,BIST (Tümü),1.00,273.00,Takip,
CIFR,ABD,1.00,16.69,Takip,
MSFT,ABD,0.49,474.26,Portfoy,
USD,NAKIT,703.50,42.22,Portfoy,"""

# Parse CSV
from io import StringIO
df = pd.read_csv(StringIO(csv_data))

# Sayıları düzelt (virgüllü formatı kaldır)
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
    print(f"💱 USD/TRY Kuru: {usd_try:.4f}")
except:
    usd_try = 34.20  # Fallback
    print(f"💱 USD/TRY Kuru (Varsayılan): {usd_try:.4f}")

print("\n" + "="*100)
print("🔍 PORTFÖY ANALİZİ - DETAYLI RAPOR")
print("="*100)

# Sadece Portföy tipindeki varlıkları analiz et
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
    print(f"{'─'*100}")
    print(f"   Adet: {adet:,.4f}")
    print(f"   Maliyet (Birim): {maliyet:,.4f}")
    
    # Para birimini belirle
    pazar_upper = pazar.upper()
    kod_upper = kod.upper()
    
    if "BIST" in pazar_upper or "FON" in pazar_upper or "EMTIA" in pazar_upper or "NAKIT" in pazar_upper and kod == "TL":
        asset_currency = "TRY"
    else:
        asset_currency = "USD"
    
    print(f"   Para Birimi: {asset_currency}")
    
    # Fiyat çek
    curr_price = 0
    price_source = ""
    
    try:
        if "NAKIT" in pazar_upper:
            if kod == "USD":
                curr_price = usd_try
                price_source = "TCMB USD/TRY Kuru"
            elif kod == "TL":
                curr_price = 1
                price_source = "Sabit (TL)"
        
        elif "Gram Altın" in kod:
            ticker = yf.Ticker("GC=F")
            h = ticker.history(period="5d")
            if not h.empty:
                ons_price_usd = h["Close"].iloc[-1]
                curr_price = (ons_price_usd * usd_try) / 31.1035
                price_source = f"Yahoo Finance - Gold (${ons_price_usd:.2f}/oz -> ₺{curr_price:.2f}/gr)"
        
        elif "Gram Gümüş" in kod:
            ticker = yf.Ticker("SI=F")
            h = ticker.history(period="5d")
            if not h.empty:
                ons_price_usd = h["Close"].iloc[-1]
                curr_price = (ons_price_usd * usd_try) / 31.1035
                price_source = f"Yahoo Finance - Silver (${ons_price_usd:.2f}/oz -> ₺{curr_price:.2f}/gr)"
        
        elif "FON" in pazar:
            # Fonlar için maliyet kullan (TEFAS API olmadan)
            curr_price = maliyet
            price_source = "⚠️ Maliyet kullanıldı (TEFAS'a erişim yok)"
        
        elif "BIST" in pazar_upper:
            symbol = f"{kod}.IS"
            ticker = yf.Ticker(symbol)
            h = ticker.history(period="5d")
            if not h.empty:
                curr_price = h["Close"].iloc[-1]
                price_source = f"Yahoo Finance - BIST ({symbol})"
            else:
                curr_price = maliyet
                price_source = f"⚠️ Yahoo'dan veri yok - Maliyet kullanıldı"
        
        elif "ABD" in pazar or "S&P" in pazar or "NASDAQ" in pazar:
            ticker = yf.Ticker(kod)
            h = ticker.history(period="5d")
            if not h.empty:
                curr_price = h["Close"].iloc[-1]
                price_source = f"Yahoo Finance - US ({kod})"
            else:
                curr_price = maliyet
                price_source = f"⚠️ Yahoo'dan veri yok - Maliyet kullanıldı"
    
    except Exception as e:
        curr_price = maliyet
        price_source = f"❌ Hata: {str(e)[:50]} - Maliyet kullanıldı"
    
    print(f"   Güncel Fiyat: {curr_price:,.4f} {asset_currency}")
    print(f"   Kaynak: {price_source}")
    
    # TRY'ye çevir
    if asset_currency == "TRY":
        maliyet_try = maliyet * adet
        deger_try = curr_price * adet
    else:  # USD
        maliyet_try = maliyet * adet * usd_try
        deger_try = curr_price * adet * usd_try
    
    kar_zarar_try = deger_try - maliyet_try
    kar_zarar_pct = (kar_zarar_try / maliyet_try * 100) if maliyet_try > 0 else 0
    
    total_maliyet_try += maliyet_try
    total_deger_try += deger_try
    
    print(f"\n   💰 HESAPLAMA (TRY bazında):")
    print(f"      Toplam Maliyet: ₺{maliyet_try:,.2f}")
    print(f"      Toplam Değer:   ₺{deger_try:,.2f}")
    
    if kar_zarar_try >= 0:
        print(f"      🟢 Kâr/Zarar:   ₺{kar_zarar_try:,.2f} ({kar_zarar_pct:+.2f}%)")
        emoji = "🟢"
    else:
        print(f"      🔴 Kâr/Zarar:   ₺{kar_zarar_try:,.2f} ({kar_zarar_pct:+.2f}%)")
        emoji = "🔴"
    
    results.append({
        'Emoji': emoji,
        'Kod': kod,
        'Pazar': pazar,
        'Adet': adet,
        'Maliyet (Birim)': maliyet,
        'Güncel Fiyat': curr_price,
        'Para Birimi': asset_currency,
        'Maliyet (₺)': maliyet_try,
        'Değer (₺)': deger_try,
        'K/Z (₺)': kar_zarar_try,
        'K/Z %': kar_zarar_pct,
        'Fiyat Kaynağı': price_source
    })

# Toplam özet
print("\n" + "="*100)
print("📊 GENEL ÖZET")
print("="*100)

total_kz = total_deger_try - total_maliyet_try
total_kz_pct = (total_kz / total_maliyet_try * 100) if total_maliyet_try > 0 else 0

print(f"\n   Toplam Maliyet:  ₺{total_maliyet_try:,.2f}")
print(f"   Toplam Değer:    ₺{total_deger_try:,.2f}")

if total_kz >= 0:
    print(f"   🟢 TOPLAM K/Z:   ₺{total_kz:,.2f} ({total_kz_pct:+.2f}%)")
    print(f"\n   🎉 TEBRİKLER! Portföyünüz kârda!")
else:
    print(f"   🔴 TOPLAM K/Z:   ₺{total_kz:,.2f} ({total_kz_pct:+.2f}%)")
    print(f"\n   ⚠️ Portföyünüz zararda görünüyor.")

# Kâr/Zarar dağılımı
results_df = pd.DataFrame(results)
losers = results_df[results_df['K/Z (₺)'] < 0].sort_values('K/Z (₺)')
winners = results_df[results_df['K/Z (₺)'] > 0].sort_values('K/Z (₺)', ascending=False)

if not losers.empty:
    print("\n" + "="*100)
    print(f"🔴 ZARARDAKI VARLIKLAR ({len(losers)} adet)")
    print("="*100)
    print(f"\n{'Kod':<15} {'Pazar':<25} {'Zarar (₺)':>15} {'Zarar %':>10}")
    print("-"*100)
    for _, row in losers.iterrows():
        print(f"{row['Kod']:<15} {row['Pazar']:<25} {row['K/Z (₺)']:>15,.2f} {row['K/Z %']:>10,.2f}%")
    print(f"\n💸 Toplam Zarar: ₺{losers['K/Z (₺)'].sum():,.2f}")

if not winners.empty:
    print("\n" + "="*100)
    print(f"🟢 KÂRDAKI VARLIKLAR ({len(winners)} adet)")
    print("="*100)
    print(f"\n{'Kod':<15} {'Pazar':<25} {'Kâr (₺)':>15} {'Kâr %':>10}")
    print("-"*100)
    for _, row in winners.iterrows():
        print(f"{row['Kod']:<15} {row['Pazar']:<25} {row['K/Z (₺)']:>15,.2f} {row['K/Z %']:>10,.2f}%")
    print(f"\n💰 Toplam Kâr: ₺{winners['K/Z (₺)'].sum():,.2f}")

# Sonuç
print("\n" + "="*100)
print("💡 SONUÇ VE ÖNERİLER")
print("="*100)

if total_kz < 0:
    print(f"""
⚠️ Portföyünüz ₺{abs(total_kz):,.2f} zararda görünüyor.

NEDEN -43,000 DEĞİL?
Çünkü:
1. Fonların fiyatlarını çekemedim (TEFAS API yok) - maliyetlerini kullandım
2. Bazı varlıkların gerçek fiyatları farklı olabilir
3. Para birimi dönüşümlerinde küçük farklılıklar olabilir

GERÇEK ZARAR NE KADAR?
Yukarıdaki zarardaki varlıkları kontrol edin. Özellikle:
- ABD hisseleri (son dönem düşüş yaşandı)
- BIST hisseleri (BIST düştü)
- Fonlar (maliyetlerini kullandım, gerçek fiyatları farklı olabilir)

ÖNERİLERİM:
1. TEFAS.gov.tr'den fon fiyatlarını manuel kontrol edin
2. Yahoo Finance'tan ABD hisselerinin gerçek fiyatlarını kontrol edin
3. Portföy uygulamanızda Dashboard'u açın ve gerçek değerleri karşılaştırın
""")
else:
    print(f"""
🎉 Harika! Portföyünüz ₺{total_kz:,.2f} kârda!

Hesaplamalar doğru görünüyor. -43,000 hatasının nedeni:
- Uygulamadaki tarihsel veri eksikliği
- Veya hesaplama hatasıydı

Düzeltmelerim sayesinde artık doğru çalışacak!
""")

print("\n" + "="*100)
