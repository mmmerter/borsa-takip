"""
Portföy Kâr/Zarar Teşhis Aracı - Basit Versiyon
================================================
"""

import pandas as pd
from data_loader import get_data_from_sheet, get_usd_try, get_tefas_data
from utils import get_yahoo_symbol
import yfinance as yf

def diagnose_simple():
    """Portföy kâr/zarar hesaplamasını detaylı şekilde analiz eder."""
    
    print("="*80)
    print("🔍 PORTFÖY KÂR/ZARAR TEŞHİS ARACI")
    print("="*80)
    
    # Veri çek
    try:
        portfoy_df = get_data_from_sheet()
    except Exception as e:
        print(f"❌ HATA: Portföy verisi çekilemedi: {e}")
        return
    
    try:
        usd_try_rate = get_usd_try()
    except Exception as e:
        print(f"❌ HATA: USD/TRY kuru çekilemedi: {e}")
        usd_try_rate = 34.0  # Varsayılan
    
    if portfoy_df.empty:
        print("❌ HATA: Portföy verisi bulunamadı!")
        return
    
    print(f"\n✅ {len(portfoy_df)} varlık bulundu")
    print(f"💱 USD/TRY Kuru: {usd_try_rate:.4f}")
    
    # Sadece portföy tipindeki varlıkları al
    portfoy_only = portfoy_df[portfoy_df["Tip"] == "Spot"].copy()
    
    print(f"📊 Portföy varlıkları: {len(portfoy_only)}")
    print("\n" + "="*80)
    print("DETAYLI ANALİZ")
    print("="*80 + "\n")
    
    # Her varlık için detaylı analiz
    diagnostics = []
    
    for idx, row in portfoy_only.iterrows():
        kod = row["Kod"]
        pazar = row["Pazar"]
        adet = float(row.get("Adet", 0))
        maliyet = float(row.get("Maliyet", 0))
        
        if adet == 0:
            continue
        
        print(f"\n{'─'*80}")
        print(f"🎯 {kod} ({pazar})")
        print(f"{'─'*80}")
        
        # Para birimi belirle
        pazar_upper = pazar.upper()
        kod_upper = kod.upper()
        
        if "BIST" in pazar_upper or "TL" in kod_upper or "FON" in pazar_upper or "EMTIA" in pazar_upper or "NAKIT" in pazar_upper:
            asset_currency = "TRY"
        else:
            asset_currency = "USD"
        
        print(f"   Para Birimi: {asset_currency}")
        print(f"   Adet: {adet:,.2f}")
        print(f"   Maliyet (Birim): {maliyet:,.4f} {asset_currency}")
        
        # Fiyat çek
        curr_price = 0
        price_source = "Bilinmiyor"
        
        try:
            if "NAKIT" in pazar_upper:
                if kod == "TL":
                    curr_price = 1
                    price_source = "Sabit (TL)"
                elif kod == "USD":
                    curr_price = usd_try_rate
                    price_source = "TCMB (USD/TRY)"
                else:
                    curr_price = 1
                    price_source = f"Varsayılan ({kod})"
            
            elif "FON" in pazar:
                curr_price, _ = get_tefas_data(kod)
                price_source = "TEFAS"
                if curr_price == 0:
                    curr_price = maliyet
                    price_source = "⚠️ TEFAS (Hata - Maliyet kullanıldı)"
                elif curr_price > 100:
                    price_source = f"⚠️ TEFAS (Şüpheli yüksek fiyat: {curr_price:.2f})"
            
            elif "Gram Altın" in kod or "GRAM ALTIN" in kod:
                try:
                    ticker = yf.Ticker("GC=F")
                    h = ticker.history(period="5d")
                    if not h.empty:
                        ons_price = h["Close"].iloc[-1]
                        curr_price = (ons_price * usd_try_rate) / 31.1035
                        price_source = f"Yahoo Finance (Altın: ${ons_price:.2f}/ons -> ₺{curr_price:.2f}/gram)"
                    else:
                        curr_price = 0
                        price_source = "❌ Yahoo Finance (Veri yok)"
                except Exception as e:
                    curr_price = 0
                    price_source = f"❌ Hata: {str(e)}"
            
            elif "Gram Gümüş" in kod or "GRAM GÜMÜŞ" in kod:
                try:
                    ticker = yf.Ticker("SI=F")
                    h = ticker.history(period="5d")
                    if not h.empty:
                        ons_price = h["Close"].iloc[-1]
                        curr_price = (ons_price * usd_try_rate) / 31.1035
                        price_source = f"Yahoo Finance (Gümüş: ${ons_price:.2f}/ons -> ₺{curr_price:.2f}/gram)"
                    else:
                        curr_price = 0
                        price_source = "❌ Yahoo Finance (Veri yok)"
                except Exception as e:
                    curr_price = 0
                    price_source = f"❌ Hata: {str(e)}"
            
            else:
                # Yahoo Finance'tan çek
                symbol = get_yahoo_symbol(kod, pazar)
                try:
                    ticker = yf.Ticker(symbol)
                    h = ticker.history(period="5d")
                    if not h.empty:
                        curr_price = h["Close"].iloc[-1]
                        price_source = f"Yahoo Finance ({symbol})"
                    else:
                        curr_price = 0
                        price_source = f"❌ Yahoo Finance (Veri yok - {symbol})"
                except Exception as e:
                    curr_price = 0
                    price_source = f"❌ Hata: {str(e)[:50]}"
        
        except Exception as e:
            curr_price = 0
            price_source = f"❌ Genel Hata: {str(e)[:50]}"
        
        print(f"   Güncel Fiyat: {curr_price:,.4f} {asset_currency}")
        print(f"   Fiyat Kaynağı: {price_source}")
        
        # Hesaplamalar (TRY bazında)
        if asset_currency == "TRY":
            maliyet_try = maliyet * adet
            deger_try = curr_price * adet
        else:  # USD
            maliyet_try = maliyet * adet * usd_try_rate
            deger_try = curr_price * adet * usd_try_rate
        
        kar_zarar_try = deger_try - maliyet_try
        kar_zarar_pct = (kar_zarar_try / maliyet_try * 100) if maliyet_try > 0 else 0
        
        print(f"\n   💰 HESAPLAMA:")
        print(f"      Toplam Maliyet: ₺{maliyet_try:,.2f}")
        print(f"      Toplam Değer:   ₺{deger_try:,.2f}")
        
        if kar_zarar_try >= 0:
            print(f"      🟢 Kâr/Zarar:   ₺{kar_zarar_try:,.2f} ({kar_zarar_pct:+.2f}%)")
        else:
            print(f"      🔴 Kâr/Zarar:   ₺{kar_zarar_try:,.2f} ({kar_zarar_pct:+.2f}%)")
        
        diagnostics.append({
            "Kod": kod,
            "Pazar": pazar,
            "Para Birimi": asset_currency,
            "Adet": adet,
            "Maliyet (Birim)": maliyet,
            "Güncel Fiyat": curr_price,
            "Fiyat Kaynağı": price_source,
            "Toplam Maliyet (TRY)": maliyet_try,
            "Toplam Değer (TRY)": deger_try,
            "K/Z (TRY)": kar_zarar_try,
            "K/Z (%)": kar_zarar_pct,
        })
    
    # DataFrame oluştur
    diag_df = pd.DataFrame(diagnostics)
    
    # Toplam hesapla
    total_maliyet = diag_df["Toplam Maliyet (TRY)"].sum()
    total_deger = diag_df["Toplam Değer (TRY)"].sum()
    total_kz = diag_df["K/Z (TRY)"].sum()
    total_kz_pct = (total_kz / total_maliyet * 100) if total_maliyet > 0 else 0
    
    # Özet göster
    print("\n" + "="*80)
    print("📈 GENEL ÖZET")
    print("="*80 + "\n")
    
    print(f"   Toplam Maliyet:   ₺{total_maliyet:,.2f}")
    print(f"   Toplam Değer:     ₺{total_deger:,.2f}")
    
    if total_kz >= 0:
        print(f"   🟢 Toplam K/Z:    ₺{total_kz:,.2f} ({total_kz_pct:+.2f}%)")
    else:
        print(f"   🔴 Toplam K/Z:    ₺{total_kz:,.2f} ({total_kz_pct:+.2f}%)")
    
    print(f"   Varlık Sayısı:    {len(diag_df)}")
    
    # Zarardaki varlıklar
    losers = diag_df[diag_df["K/Z (TRY)"] < 0].sort_values("K/Z (TRY)")
    
    if not losers.empty:
        print("\n" + "="*80)
        print(f"🔴 ZARARDAKI VARLIKLAR ({len(losers)} adet)")
        print("="*80 + "\n")
        
        for _, row in losers.iterrows():
            print(f"   {row['Kod']:20s} | Zarar: ₺{row['K/Z (TRY)']:>12,.2f} ({row['K/Z (%)']:>6.2f}%)")
        
        total_loss = losers["K/Z (TRY)"].sum()
        print(f"\n   💸 Toplam Zarar: ₺{abs(total_loss):,.2f}")
    
    # Kârdaki varlıklar
    winners = diag_df[diag_df["K/Z (TRY)"] > 0].sort_values("K/Z (TRY)", ascending=False)
    
    if not winners.empty:
        print("\n" + "="*80)
        print(f"🟢 KÂRDAKI VARLIKLAR ({len(winners)} adet)")
        print("="*80 + "\n")
        
        for _, row in winners.iterrows():
            print(f"   {row['Kod']:20s} | Kâr: ₺{row['K/Z (TRY)']:>12,.2f} ({row['K/Z (%)']:>6.2f}%)")
        
        total_profit = winners["K/Z (TRY)"].sum()
        print(f"\n   💰 Toplam Kâr: ₺{total_profit:,.2f}")
    
    # Fiyat çekme sorunları
    price_issues = diag_df[
        (diag_df["Güncel Fiyat"] == 0) | 
        (diag_df["Fiyat Kaynağı"].str.contains("❌|⚠️", case=False, na=False))
    ]
    
    if not price_issues.empty:
        print("\n" + "="*80)
        print(f"⚠️ FİYAT ÇEKME SORUNLARI ({len(price_issues)} adet)")
        print("="*80 + "\n")
        
        for _, row in price_issues.iterrows():
            print(f"   {row['Kod']:20s} | {row['Fiyat Kaynağı']}")
    
    # Öneriler
    print("\n" + "="*80)
    print("💡 ÖNERİLER VE SONUÇ")
    print("="*80 + "\n")
    
    if total_kz < 0:
        print(f"⚠️ Portföyünüz ₺{abs(total_kz):,.2f} zararda görünüyor.\n")
        print("OLASI NEDENLER:")
        print("1. Fiyat Çekme Hatası: Yukarıdaki 'FİYAT ÇEKME SORUNLARI' bölümünü kontrol edin")
        print("2. Yanlış Maliyet Girişi: Google Sheets'teki 'Maliyet' kolonundaki değerleri kontrol edin")
        print("3. Para Birimi Karışıklığı: TRY/USD karışıklığı olabilir")
        print("4. Piyasa Düşüşü: Gerçekten piyasa düşmüş olabilir (özellikle BIST ve kripto)")
        print("\nYAPMANIZ GEREKENLER:")
        print("- Zarardaki varlıkların maliyetlerini Google Sheets'te kontrol edin")
        print("- Fiyatların doğru çekildiğini doğrulayın")
        print("- Yahoo Finance'ta manuel olarak sembol isimlerini kontrol edin")
    else:
        print(f"🎉 Tebrikler! Portföyünüz ₺{total_kz:,.2f} kârda!\n")
        print("Hesaplamalar doğru görünüyor.")
    
    print("\n" + "="*80)
    print("TEŞHİS TAMAMLANDI")
    print("="*80)
    
    return diag_df

if __name__ == "__main__":
    try:
        result = diagnose_simple()
    except Exception as e:
        print(f"\n❌ BEKLENMEYEN HATA: {e}")
        import traceback
        traceback.print_exc()
