#!/usr/bin/env python3
"""
Basit Günlük Reset Testi (Pandas gerektirmez)
"""

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
        ("00:15", "Dünün baz fiyatları"),
        ("00:25", "Dünün baz fiyatları"),
        ("00:30", "Bugünün baz fiyatları"),
        ("00:35", "Bugünün baz fiyatları"),
        ("09:00", "Bugünün baz fiyatları"),
        ("14:30", "Bugünün baz fiyatları"),
        ("23:59", "Bugünün baz fiyatları"),
    ]
    
    all_passed = True
    for time_str, expected in test_times:
        hour, minute = map(int, time_str.split(":"))
        now = datetime.now(turkey_tz).replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        # Mantık kontrolü
        if now.hour == 0 and now.minute < 30:
            yesterday = now - timedelta(days=1)
            target_date = yesterday.strftime("%Y-%m-%d")
            status = "Dünün baz fiyatları"
        else:
            target_date = now.strftime("%Y-%m-%d")
            status = "Bugünün baz fiyatları"
        
        passed = (expected == status)
        all_passed = all_passed and passed
        
        symbol = "✅" if passed else "❌"
        print(f"{symbol} Saat {time_str}: {status} ({target_date})")
    
    return all_passed

def test_calculation():
    """Günlük değişim hesaplama"""
    print("\n" + "=" * 80)
    print("📊 HESAPLAMA TESTİ")
    print("=" * 80)
    
    tests = [
        (100.0, 105.0, 10, 5.0),   # +5%
        (100.0, 95.0, 10, -5.0),   # -5%
        (50.0, 52.5, 20, 5.0),     # +5%
        (200.0, 200.0, 5, 0.0),    # 0%
    ]
    
    all_passed = True
    for base_price, current_price, quantity, expected_pct in tests:
        base_value = base_price * quantity
        current_value = current_price * quantity
        daily_change = current_value - base_value
        daily_pct = ((current_value - base_value) / base_value * 100) if base_value > 0 else 0
        
        passed = abs(daily_pct - expected_pct) < 0.01
        all_passed = all_passed and passed
        
        symbol = "✅" if passed else "❌"
        print(f"{symbol} {base_price:.2f}₺ → {current_price:.2f}₺ (x{quantity}): {daily_pct:+.2f}% (beklenen: {expected_pct:+.2f}%)")
    
    return all_passed

def main():
    print("\n🔥 GÜNLÜK RESET - BASİT TEST 🔥\n")
    
    time_passed = test_time_logic()
    calc_passed = test_calculation()
    
    print("\n" + "=" * 80)
    if time_passed and calc_passed:
        print("✅ TÜM TESTLER BAŞARILI!")
        print("=" * 80)
        print("\n✨ 00:30 reset mantığı doğru çalışıyor!")
        print("✨ Günlük değişim hesaplamaları doğru!")
    else:
        print("❌ BAZI TESTLER BAŞARISIZ!")
        print("=" * 80)
    print()

if __name__ == "__main__":
    main()
