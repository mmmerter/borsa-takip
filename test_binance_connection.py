"""
Binance Futures API Bağlantı Test Scripti
=========================================
Bu script API bağlantınızı test eder ve temel bilgileri gösterir
"""

import streamlit as st
from binance_futures import BinanceFuturesAPI
from datetime import datetime

def test_connection():
    """API bağlantısını test et"""
    
    print("=" * 70)
    print("🚀 BINANCE FUTURES API BAĞLANTI TESTİ")
    print("=" * 70)
    
    # API credentials
    try:
        api_key = st.secrets["binance_futures"]["api_key"]
        api_secret = st.secrets["binance_futures"]["api_secret"]
        testnet = st.secrets["binance_futures"].get("testnet", False)
        
        print(f"\n✅ API bilgileri secrets'tan alındı")
        print(f"   Testnet: {'Evet' if testnet else 'Hayır'}")
        print(f"   API Key: {api_key[:10]}...{api_key[-10:]}")
        
    except Exception as e:
        print(f"\n❌ HATA: Secrets dosyası okunamadı: {str(e)}")
        print("\n💡 Çözüm: .streamlit/secrets.toml dosyasını kontrol edin")
        return False
    
    # API bağlantısı
    try:
        print(f"\n🔌 Binance'e bağlanılıyor...")
        api = BinanceFuturesAPI(api_key, api_secret, testnet)
        
        if not api.test_connection():
            print("❌ Bağlantı başarısız!")
            return False
        
        print("✅ Bağlantı başarılı!")
        
    except Exception as e:
        print(f"❌ HATA: {str(e)}")
        return False
    
    # Hesap bilgileri
    print("\n" + "=" * 70)
    print("📊 HESAP BİLGİLERİ")
    print("=" * 70)
    
    try:
        balance = api.get_account_balance()
        
        print(f"\n💰 Bakiye:")
        print(f"   Toplam Cüzdan: ${balance['total_wallet_balance']:,.2f}")
        print(f"   Marjin Bakiyesi: ${balance['total_margin_balance']:,.2f}")
        print(f"   Kullanılabilir: ${balance['available_balance']:,.2f}")
        print(f"   Unrealized PnL: ${balance['total_unrealized_pnl']:,.2f}")
        
    except Exception as e:
        print(f"❌ Bakiye bilgisi alınamadı: {str(e)}")
    
    # Pozisyonlar
    print("\n" + "=" * 70)
    print("📍 AÇIK POZİSYONLAR")
    print("=" * 70)
    
    try:
        positions = api.get_open_positions()
        
        if positions.empty:
            print("\n📝 Açık pozisyon yok")
        else:
            print(f"\n✅ {len(positions)} açık pozisyon bulundu:\n")
            
            for idx, pos in positions.iterrows():
                side_emoji = "🟢" if pos['side'] == 'LONG' else "🔴"
                pnl_emoji = "✅" if pos['unrealized_pnl'] >= 0 else "❌"
                
                print(f"{side_emoji} {pos['symbol']}")
                print(f"   Yön: {pos['side']} | Leverage: {pos['leverage']}x")
                print(f"   Miktar: {pos['size']}")
                print(f"   Giriş: ${pos['entry_price']:,.4f} | Mark: ${pos['mark_price']:,.4f}")
                print(f"   {pnl_emoji} PnL: ${pos['unrealized_pnl']:,.2f} ({pos['unrealized_pnl_percent']:.2f}%)")
                print(f"   Tasfiye: ${pos['liquidation_price']:,.4f}")
                print(f"   Notional: ${pos['notional']:,.0f}")
                print()
        
    except Exception as e:
        print(f"❌ Pozisyon bilgisi alınamadı: {str(e)}")
    
    # Günlük PnL
    print("=" * 70)
    print("📈 SON 7 GÜN PnL ÖZETİ")
    print("=" * 70)
    
    try:
        daily_pnl = api.get_daily_pnl_summary(days=7)
        
        if daily_pnl.empty:
            print("\n📝 PnL verisi yok")
        else:
            total_pnl = daily_pnl['realized_pnl'].sum()
            avg_pnl = daily_pnl['realized_pnl'].mean()
            winning_days = len(daily_pnl[daily_pnl['realized_pnl'] > 0])
            
            print(f"\n💰 Toplam Realized PnL: ${total_pnl:,.2f}")
            print(f"📊 Ortalama Günlük: ${avg_pnl:,.2f}")
            print(f"✅ Kazanan Günler: {winning_days}/{len(daily_pnl)}\n")
            
            for _, day in daily_pnl.iterrows():
                pnl = day['realized_pnl']
                emoji = "✅" if pnl >= 0 else "❌"
                print(f"   {emoji} {day['date']}: ${pnl:,.2f}")
        
    except Exception as e:
        print(f"❌ PnL özeti alınamadı: {str(e)}")
    
    # Özet
    print("\n" + "=" * 70)
    print("🎯 HESAP ÖZETİ")
    print("=" * 70)
    
    try:
        summary = api.get_account_summary()
        
        print(f"\n💼 Genel Durum:")
        print(f"   Cüzdan: ${summary['wallet_balance']:,.2f}")
        print(f"   Açık Pozisyon: {summary['num_positions']} (Long: {summary['num_long']}, Short: {summary['num_short']})")
        print(f"   Toplam Notional: ${summary['total_notional']:,.0f}")
        
        print(f"\n📊 Performans:")
        print(f"   Unrealized PnL: ${summary['unrealized_pnl']:,.2f}")
        print(f"   Realized PnL (24h): ${summary['realized_pnl_24h']:,.2f}")
        print(f"   Realized PnL (7d): ${summary['realized_pnl_7d']:,.2f}")
        print(f"   Realized PnL (30d): ${summary['realized_pnl_30d']:,.2f}")
        
    except Exception as e:
        print(f"❌ Özet alınamadı: {str(e)}")
    
    # Başarı
    print("\n" + "=" * 70)
    print("✅ TÜM TESTLER BAŞARIYLA TAMAMLANDI!")
    print("=" * 70)
    print(f"\n⏰ Test Zamanı: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n🚀 Streamlit dashboard'unu başlatmak için:")
    print("   streamlit run futures_page.py")
    print("\n📚 Dokümantasyon için:")
    print("   BINANCE_FUTURES_DOKUMANTASYON.md dosyasını okuyun")
    print("\n" + "=" * 70)
    
    return True


if __name__ == "__main__":
    try:
        success = test_connection()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ Test iptal edildi")
        exit(1)
    except Exception as e:
        print(f"\n\n❌ Beklenmeyen hata: {str(e)}")
        exit(1)
