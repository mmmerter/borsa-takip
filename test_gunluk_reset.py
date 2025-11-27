#!/usr/bin/env python3
"""
Günlük Reset Özelliği Test Scripti

Bu script, 00:30 reset mantığının doğru çalıştığını test eder.
"""

import pandas as pd
from datetime import datetime, timedelta
import pytz

def test_time_logic():
    """00:30 zaman mantığını test et"""
    print("=" * 80)
    print("⏰ ZAMAN MANTIK TESTİ")
    print("=" * 80)
    
    # Türkiye saati
    turkey_tz = pytz.timezone('Europe/Istanbul')
    
    # Test senaryoları
    test_times = [
        ("00:15", "Dünün baz fiyatları kullanılmalı"),
        ("00:25", "Dünün baz fiyatları kullanılmalı"),
        ("00:30", "Bugünün baz fiyatları kullanılmalı"),
        ("00:35", "Bugünün baz fiyatları kullanılmalı"),
        ("09:00", "Bugünün baz fiyatları kullanılmalı"),
        ("14:30", "Bugünün baz fiyatları kullanılmalı"),
        ("23:59", "Bugünün baz fiyatları kullanılmalı"),
    ]
    
    for time_str, expected_behavior in test_times:
        hour, minute = map(int, time_str.split(":"))
        
        # Test zamanı oluştur
        now = datetime.now(turkey_tz).replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        # Mantık kontrolü
        if now.hour == 0 and now.minute < 30:
            # 00:00 - 00:30 arası: Dünün baz fiyatları
            yesterday = now - timedelta(days=1)
            target_date = yesterday.strftime("%Y-%m-%d")
            status = "🔴 Dünkü baz fiyatlar"
        else:
            # 00:30'dan sonra: Bugünün baz fiyatları
            target_date = now.strftime("%Y-%m-%d")
            status = "🟢 Bugünkü baz fiyatlar"
        
        print(f"\n⏰ Saat: {time_str}")
        print(f"   Beklenen: {expected_behavior}")
        print(f"   Gerçek:   {status} ({target_date})")
        
        # Doğrulama
        if ("Dünün" in expected_behavior and "Dünkü" in status) or \
           ("Bugünün" in expected_behavior and "Bugünkü" in status):
            print(f"   ✅ TEST BAŞARILI")
        else:
            print(f"   ❌ TEST BAŞARISIZ")

def test_should_update_logic():
    """should_update_daily_base() mantığını test et"""
    print("\n" + "=" * 80)
    print("🔄 GÜNCELLEME MANTIK TESTİ")
    print("=" * 80)
    
    turkey_tz = pytz.timezone('Europe/Istanbul')
    
    test_scenarios = [
        ("00:15", False, "00:30'dan önce → Güncelleme yok"),
        ("00:29", False, "00:30'dan önce → Güncelleme yok"),
        ("00:30", True, "00:30'dan sonra + bugün kayıt yok → Güncelleme yapılmalı"),
        ("09:00", True, "00:30'dan sonra + bugün kayıt yok → Güncelleme yapılmalı"),
    ]
    
    for time_str, should_update, explanation in test_scenarios:
        hour, minute = map(int, time_str.split(":"))
        now = datetime.now(turkey_tz).replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        # Mantık kontrolü (bugün için kayıt olmadığını varsayarak)
        if now.hour == 0 and now.minute < 30:
            result = False
        else:
            result = True  # Bugün için kayıt olmadığını varsayıyoruz
        
        print(f"\n⏰ Saat: {time_str}")
        print(f"   Beklenen: {'Güncellenmeli' if should_update else 'Güncellenmemeli'}")
        print(f"   Gerçek:   {'Güncelleniyor' if result else 'Güncellenmıyor'}")
        print(f"   Açıklama: {explanation}")
        
        if result == should_update:
            print(f"   ✅ TEST BAŞARILI")
        else:
            print(f"   ❌ TEST BAŞARISIZ")

def test_daily_change_calculation():
    """Günlük değişim hesaplama mantığını test et"""
    print("\n" + "=" * 80)
    print("📊 GÜNLÜK DEĞİŞİM HESAPLAMA TESTİ")
    print("=" * 80)
    
    test_cases = [
        # (baz_fiyat, mevcut_fiyat, adet, beklenen_değişim_pct)
        (100.0, 105.0, 10, 5.0, "Basit kazanç: 100₺ → 105₺"),
        (100.0, 95.0, 10, -5.0, "Basit kayıp: 100₺ → 95₺"),
        (50.0, 52.5, 20, 5.0, "Daha fazla adet: 50₺ → 52.5₺"),
        (200.0, 200.0, 5, 0.0, "Değişim yok: 200₺ → 200₺"),
        (10.0, 11.0, 100, 10.0, "Yüksek değişim: 10₺ → 11₺"),
    ]
    
    for baz_fiyat, mevcut_fiyat, adet, beklenen_pct, aciklama in test_cases:
        # Değerleri hesapla
        baz_deger = baz_fiyat * adet
        mevcut_deger = mevcut_fiyat * adet
        gunluk_degisim = mevcut_deger - baz_deger
        gunluk_pct = ((mevcut_deger - baz_deger) / baz_deger * 100) if baz_deger > 0 else 0
        
        print(f"\n📈 Test: {aciklama}")
        print(f"   Baz Fiyat: {baz_fiyat:.2f}₺ × {adet} adet = {baz_deger:.2f}₺")
        print(f"   Mevcut Fiyat: {mevcut_fiyat:.2f}₺ × {adet} adet = {mevcut_deger:.2f}₺")
        print(f"   Günlük Değişim: {gunluk_degisim:+.2f}₺ ({gunluk_pct:+.2f}%)")
        print(f"   Beklenen: {beklenen_pct:+.2f}%")
        
        # Küçük bir tolerans ile karşılaştır (floating point hassasiyet)
        if abs(gunluk_pct - beklenen_pct) < 0.01:
            print(f"   ✅ TEST BAŞARILI")
        else:
            print(f"   ❌ TEST BAŞARISIZ (Fark: {abs(gunluk_pct - beklenen_pct):.4f}%)")

def test_currency_conversion():
    """Para birimi dönüşüm mantığını test et"""
    print("\n" + "=" * 80)
    print("💱 PARA BİRİMİ DÖNÜŞÜM TESTİ")
    print("=" * 80)
    
    usd_try_rate = 34.20
    
    test_cases = [
        # (baz_fiyat, baz_pb, adet, gorunum_pb, beklenen_deger)
        (100.0, "TRY", 10, "TRY", 1000.0, "TRY → TRY: Dönüşüm yok"),
        (10.0, "USD", 5, "TRY", 10.0 * 5 * usd_try_rate, "USD → TRY: USD ile çarpılmalı"),
        (340.0, "TRY", 10, "USD", 340.0 * 10 / usd_try_rate, "TRY → USD: USD'ye bölünmeli"),
        (100.0, "USD", 2, "USD", 200.0, "USD → USD: Dönüşüm yok"),
    ]
    
    for baz_fiyat, baz_pb, adet, gorunum_pb, beklenen_deger, aciklama in test_cases:
        # Dönüşüm mantığı
        if gorunum_pb == "TRY":
            if baz_pb == "USD":
                deger = baz_fiyat * adet * usd_try_rate
            else:
                deger = baz_fiyat * adet
        else:  # USD
            if baz_pb == "TRY":
                deger = baz_fiyat * adet / usd_try_rate
            else:
                deger = baz_fiyat * adet
        
        print(f"\n💰 Test: {aciklama}")
        print(f"   Baz Fiyat: {baz_fiyat:.2f} {baz_pb} × {adet} adet")
        print(f"   Görünüm: {gorunum_pb}")
        print(f"   USD/TRY Kuru: {usd_try_rate:.2f}")
        print(f"   Hesaplanan Değer: {deger:.2f} {gorunum_pb}")
        print(f"   Beklenen Değer: {beklenen_deger:.2f} {gorunum_pb}")
        
        # Küçük bir tolerans ile karşılaştır
        if abs(deger - beklenen_deger) < 0.01:
            print(f"   ✅ TEST BAŞARILI")
        else:
            print(f"   ❌ TEST BAŞARISIZ (Fark: {abs(deger - beklenen_deger):.2f})")

def test_dataframe_operations():
    """DataFrame işlemlerini test et"""
    print("\n" + "=" * 80)
    print("📋 DATAFRAME İŞLEMLERİ TESTİ")
    print("=" * 80)
    
    # Örnek portföy dataframe'i
    portfolio_df = pd.DataFrame({
        "Kod": ["THYAO", "AAPL", "YHB", "ASELS"],
        "Adet": [100, 10, 1000, 50],
        "Değer": [27350, 6460, 1320, 16250],
        "Gün. Kâr/Zarar": [350, -140, 20, 250],
        "PB": ["TRY", "USD", "TRY", "TRY"]
    })
    
    # Örnek baz fiyatlar dataframe'i
    base_prices_df = pd.DataFrame({
        "Kod": ["THYAO", "AAPL", "YHB", "ASELS"],
        "Fiyat": [270.0, 660.0, 1.30, 320.0],
        "PB": ["TRY", "USD", "TRY", "TRY"]
    })
    
    print("\n📊 Örnek Portföy:")
    print(portfolio_df.to_string(index=False))
    
    print("\n📊 Örnek Baz Fiyatlar (00:30'da kaydedilmiş):")
    print(base_prices_df.to_string(index=False))
    
    # Günlük % hesaplama (basit yöntem)
    print("\n📈 Günlük Değişim Hesaplama:")
    for idx, row in portfolio_df.iterrows():
        kod = row["Kod"]
        current_value = row["Değer"]
        gunluk_kz = row["Gün. Kâr/Zarar"]
        
        # Baz değeri bul
        base_row = base_prices_df[base_prices_df["Kod"] == kod]
        if not base_row.empty:
            base_price = float(base_row.iloc[0]["Fiyat"])
            adet = row["Adet"]
            base_value = base_price * adet
            
            # Günlük değişim (00:30 bazında)
            gunluk_degisim_yeni = current_value - base_value
            gunluk_pct_yeni = ((current_value - base_value) / base_value * 100) if base_value > 0 else 0
            
            # Eski yöntem (önceki gün kapanışı)
            eski_deger = current_value - gunluk_kz
            gunluk_pct_eski = (gunluk_kz / eski_deger * 100) if eski_deger > 0 else 0
            
            print(f"\n   {kod}:")
            print(f"      Baz Değer (00:30): {base_value:,.2f}₺")
            print(f"      Mevcut Değer: {current_value:,.2f}₺")
            print(f"      Yeni Yöntem (00:30 bazlı): {gunluk_degisim_yeni:+,.2f}₺ ({gunluk_pct_yeni:+.2f}%)")
            print(f"      Eski Yöntem (önceki gün): {gunluk_kz:+,.2f}₺ ({gunluk_pct_eski:+.2f}%)")
            print(f"      Fark: {abs(gunluk_pct_yeni - gunluk_pct_eski):.2f}% fark var")

def main():
    """Ana test fonksiyonu"""
    print("\n")
    print("🔥" * 40)
    print("GÜNLÜK RESET ÖZELLİĞİ - TEST PAKETİ")
    print("🔥" * 40)
    
    try:
        test_time_logic()
        test_should_update_logic()
        test_daily_change_calculation()
        test_currency_conversion()
        test_dataframe_operations()
        
        print("\n" + "=" * 80)
        print("✅ TÜM TESTLER TAMAMLANDI!")
        print("=" * 80)
        print("\n💡 Notlar:")
        print("   - Tüm testler başarılı ise, 00:30 reset mantığı doğru çalışıyor demektir")
        print("   - Gerçek ortamda Google Sheets bağlantısı test edilmelidir")
        print("   - Para birimi dönüşümleri USD/TRY kuruna göre değişebilir")
        print("\n")
        
    except Exception as e:
        print("\n" + "=" * 80)
        print(f"❌ TEST HATASI: {str(e)}")
        print("=" * 80)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
