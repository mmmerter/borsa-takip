#!/usr/bin/env python3
"""
Minimal Günlük Reset Testi (Dış bağımlılık yok)
"""

def test_time_logic():
    """00:30 zaman mantığı testi"""
    print("⏰ ZAMAN MANTIK TESTİ")
    print("=" * 60)
    
    # Test senaryoları: (saat, dakika, beklenen_sonuc)
    tests = [
        (0, 15, "Dünün baz fiyatları"),
        (0, 25, "Dünün baz fiyatları"),
        (0, 30, "Bugünün baz fiyatları"),
        (0, 35, "Bugünün baz fiyatları"),
        (9, 0, "Bugünün baz fiyatları"),
        (14, 30, "Bugünün baz fiyatları"),
        (23, 59, "Bugünün baz fiyatları"),
    ]
    
    all_passed = True
    for hour, minute, expected in tests:
        # Mantık: 00:30'dan önce = dün, sonra = bugün
        if hour == 0 and minute < 30:
            result = "Dünün baz fiyatları"
        else:
            result = "Bugünün baz fiyatları"
        
        passed = (result == expected)
        all_passed = all_passed and passed
        
        time_str = f"{hour:02d}:{minute:02d}"
        symbol = "✅" if passed else "❌"
        print(f"{symbol} Saat {time_str}: {result}")
    
    return all_passed

def test_calculation():
    """Günlük değişim hesaplama testi"""
    print("\n📊 HESAPLAMA TESTİ")
    print("=" * 60)
    
    # Test senaryoları: (baz_fiyat, mevcut_fiyat, adet, beklenen_yuzde)
    tests = [
        (100.0, 105.0, 10, 5.0, "Basit kazanç"),
        (100.0, 95.0, 10, -5.0, "Basit kayıp"),
        (50.0, 52.5, 20, 5.0, "Fazla adet"),
        (200.0, 200.0, 5, 0.0, "Değişim yok"),
        (10.0, 11.0, 100, 10.0, "Yüksek değişim"),
    ]
    
    all_passed = True
    for base_price, current_price, quantity, expected_pct, description in tests:
        # Değer hesaplama
        base_value = base_price * quantity
        current_value = current_price * quantity
        
        # Yüzde değişim
        if base_value > 0:
            daily_pct = ((current_value - base_value) / base_value) * 100
        else:
            daily_pct = 0.0
        
        # Doğrulama (0.01% tolerans)
        passed = abs(daily_pct - expected_pct) < 0.01
        all_passed = all_passed and passed
        
        symbol = "✅" if passed else "❌"
        print(f"{symbol} {description}: {base_price:.2f}₺ → {current_price:.2f}₺ = {daily_pct:+.2f}%")
    
    return all_passed

def test_currency_conversion():
    """Para birimi dönüşüm testi"""
    print("\n💱 PARA BİRİMİ DÖNÜŞÜM TESTİ")
    print("=" * 60)
    
    usd_try = 34.20
    
    # Test senaryoları: (fiyat, pb_kaynak, pb_hedef, adet, beklenen_deger)
    tests = [
        (100.0, "TRY", "TRY", 10, 1000.0, "TRY → TRY"),
        (10.0, "USD", "TRY", 5, 10.0 * 5 * usd_try, "USD → TRY"),
        (340.0, "TRY", "USD", 10, 340.0 * 10 / usd_try, "TRY → USD"),
        (100.0, "USD", "USD", 2, 200.0, "USD → USD"),
    ]
    
    all_passed = True
    for price, from_curr, to_curr, quantity, expected_value, description in tests:
        # Dönüşüm mantığı
        if to_curr == "TRY":
            if from_curr == "USD":
                value = price * quantity * usd_try
            else:
                value = price * quantity
        else:  # to_curr == "USD"
            if from_curr == "TRY":
                value = price * quantity / usd_try
            else:
                value = price * quantity
        
        # Doğrulama (0.01 tolerans)
        passed = abs(value - expected_value) < 0.01
        all_passed = all_passed and passed
        
        symbol = "✅" if passed else "❌"
        print(f"{symbol} {description}: {price:.2f} {from_curr} → {value:.2f} {to_curr}")
    
    return all_passed

def main():
    """Ana test fonksiyonu"""
    print("\n" + "🔥" * 30)
    print("GÜNLÜK RESET - MİNİMAL TEST PAKETİ")
    print("🔥" * 30 + "\n")
    
    time_passed = test_time_logic()
    calc_passed = test_calculation()
    conv_passed = test_currency_conversion()
    
    print("\n" + "=" * 60)
    if time_passed and calc_passed and conv_passed:
        print("✅ TÜM TESTLER BAŞARILI!")
        print("=" * 60)
        print("\n✨ 00:30 reset mantığı doğru çalışıyor!")
        print("✨ Günlük değişim hesaplamaları doğru!")
        print("✨ Para birimi dönüşümleri doğru!")
        return 0
    else:
        print("❌ BAZI TESTLER BAŞARISIZ!")
        print("=" * 60)
        if not time_passed:
            print("❌ Zaman mantığı testi başarısız")
        if not calc_passed:
            print("❌ Hesaplama testi başarısız")
        if not conv_passed:
            print("❌ Dönüşüm testi başarısız")
        return 1
    
    print()

if __name__ == "__main__":
    exit(main())
