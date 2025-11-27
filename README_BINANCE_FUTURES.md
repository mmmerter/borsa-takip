# 🚀 Binance Futures API Entegrasyonu

## 📋 Proje Özeti

Bu proje, **Binance Futures hesabınızdan tüm verileri otomatik olarak çeker**, **PnL'inizi gerçek zamanlı takip eder** ve **kapsamlı analizler sunar**.

## ✨ Özellikler

### 🔥 Temel Özellikler
- ✅ **Gerçek Zamanlı Veri**: Pozisyonlar, fiyatlar, PnL anlık güncellenir
- ✅ **PnL Takibi**: Realized ve unrealized PnL otomatik hesaplanır
- ✅ **Google Sheets Entegrasyonu**: Tüm veriler otomatik kaydedilir
- ✅ **Modern Dashboard**: Kullanıcı dostu Streamlit arayüzü
- ✅ **Tarihsel Analiz**: Günlük, haftalık, aylık performans
- ✅ **Risk Yönetimi**: Leverage, liquidation, margin bilgileri
- ✅ **Multi-Timeframe**: 24 saat, 7 gün, 30 gün bazlı raporlar

### 📊 Çekilen Veriler

#### Hesap Bilgileri
- Toplam cüzdan bakiyesi (USDT)
- Marjin bakiyesi
- Kullanılabilir bakiye
- Cross/Isolated margin durumu

#### Pozisyon Bilgileri
- Sembol (BTCUSDT, ETHUSDT, vb.)
- Yön (Long/Short)
- Pozisyon büyüklüğü
- Giriş fiyatı
- Güncel mark fiyatı
- Unrealized PnL ($ ve %)
- Leverage
- Liquidation fiyatı
- Marjin tipi
- Notional değer

#### PnL Verileri
- Unrealized PnL (açık pozisyonlar)
- Realized PnL (kapatılmış pozisyonlar)
- Günlük PnL özeti (30 güne kadar)
- Kümülatif PnL
- Haftalık/Aylık performans

#### Gelir Geçmişi
- REALIZED_PNL (gerçekleşen kar/zarar)
- FUNDING_FEE (funding ücreti)
- COMMISSION (işlem komisyonları)
- INSURANCE_CLEAR (sigorta tasfiyesi)
- TRANSFER (transfer işlemleri)

## 🗂️ Dosya Yapısı

```
workspace/
├── binance_futures.py              # Ana API modülü
├── futures_page.py                 # Streamlit dashboard sayfası
├── test_binance_connection.py      # Bağlantı test scripti
├── .streamlit/
│   └── secrets.toml               # API credentials (GİZLİ!)
├── BINANCE_FUTURES_DOKUMANTASYON.md   # Detaylı dokümantasyon
├── HIZLI_BASLANGIÇ.md             # Hızlı başlangıç kılavuzu
├── README_BINANCE_FUTURES.md      # Bu dosya
├── requirements.txt               # Python paketleri
└── .gitignore                     # Git ignore (secrets korumalı)
```

## 🚀 Kurulum

### 1. Paketleri Yükleyin

```bash
pip install -r requirements.txt
```

### 2. API Anahtarlarını Ayarlayın

`.streamlit/secrets.toml` dosyası zaten oluşturuldu ve API anahtarlarınız kaydedildi.

**⚠️ ÖNEMLİ**: Bu dosya `.gitignore`'a eklendi, asla commit edilmeyecek!

### 3. Uygulamayı Başlatın

Ana dashboard (tüm özelliklerle):
```bash
streamlit run portfoy.py
```

Sadece Futures dashboard:
```bash
streamlit run futures_page.py
```

### 4. Test Edin

```bash
python3 test_binance_connection.py
```

## 📖 Kullanım

### Dashboard Erişimi

1. Uygulamayı başlatın: `streamlit run portfoy.py`
2. Üst menüden **"Binance Futures"** sekmesine tıklayın
3. Dashboard otomatik olarak açılır

### API ile Programatik Erişim

```python
from binance_futures import BinanceFuturesAPI
import streamlit as st

# API bağlantısı
api_key = st.secrets["binance_futures"]["api_key"]
api_secret = st.secrets["binance_futures"]["api_secret"]

api = BinanceFuturesAPI(api_key, api_secret)

# Hesap özeti
summary = api.get_account_summary()
print(f"Bakiye: ${summary['wallet_balance']:,.2f}")
print(f"Unrealized PnL: ${summary['unrealized_pnl']:,.2f}")
print(f"Realized PnL (24h): ${summary['realized_pnl_24h']:,.2f}")

# Pozisyonlar
positions = api.get_open_positions()
for _, pos in positions.iterrows():
    print(f"{pos['symbol']}: {pos['side']} | PnL: ${pos['unrealized_pnl']:,.2f}")

# Günlük PnL
daily_pnl = api.get_daily_pnl_summary(days=7)
print(f"7 günlük toplam PnL: ${daily_pnl['realized_pnl'].sum():,.2f}")
```

## 🎨 Dashboard Özellikleri

### Hesap Özeti
- 💰 Cüzdan bakiyesi
- 💰 Marjin bakiyesi
- 💰 Kullanılabilir bakiye
- 💰 Toplam pozisyon değeri

### PnL Metrikleri
- 📈 Unrealized PnL (gerçekleşmemiş)
- 📈 Realized PnL (24 saat)
- 📈 Realized PnL (7 gün)
- 📈 Realized PnL (30 gün)

### Pozisyon Tablosu
Her pozisyon için:
- Sembol
- Yön (🟢 Long / 🔴 Short)
- Miktar
- Giriş fiyatı
- Mark fiyatı
- PnL ($ ve %)
- Leverage
- Liquidation fiyatı
- Marjin tipi
- Notional değer

### Grafikler
1. **Pozisyon Dağılım Pie Chart** - Long vs Short
2. **Leverage Chart** - Sembol bazlı leverage
3. **Günlük PnL Chart** - 30 günlük performans

### İstatistikler
- Toplam realized PnL
- Ortalama günlük PnL
- Kazanan gün oranı (win rate)
- En iyi gün PnL'i

## 🔐 Güvenlik

### ✅ Yapılması Gerekenler

1. **API İzinleri**
   - ✅ Sadece "Reading" ve "Futures" izni
   - ❌ "Enable Withdrawals" ASLA vermeyin!

2. **IP Whitelist**
   - Mümkünse IP whitelist kullanın
   - Binance API settings'ten yapılabilir

3. **Secrets Yönetimi**
   - API key'leri asla kodda saklamayın
   - `.streamlit/secrets.toml` kullanın
   - `.gitignore`'a ekleyin

4. **Düzenli Kontrol**
   - API key'lerinizi düzenli kontrol edin
   - Şüpheli aktivite varsa hemen iptal edin

### 🔒 Korunan Dosyalar

`.gitignore` dosyası aşağıdakileri korur:
```
.streamlit/secrets.toml
*.key
*.pem
.env
credentials.json
```

## 📊 Google Sheets Entegrasyonu

### Kaydedilen Veriler

#### Sheet 1: futures_positions
Güncel pozisyonlar (her güncellemede yenilenir)

#### Sheet 2: futures_daily_summary
Günlük özet (her gün bir kayıt)

### Nasıl Aktif Edilir?

1. Dashboard'da sidebar'dan "Sheets'e Kaydet" seçeneğini aktif edin
2. Veriler otomatik olarak kaydedilecek
3. Tarihsel analiz için kullanın

## 🐛 Sorun Giderme

### "Invalid API Key"
- API key'i kontrol edin
- Binance'te Futures iznini aktif edin
- IP whitelist ayarlarını kontrol edin

### "Timestamp Error"
- Sistem saatini senkronize edin
- API otomatik düzeltme yapar

### "Rate Limit"
- Otomatik yenileme süresini artırın
- Çok fazla manuel yenileme yapmayın

### "No Positions"
- Binance web/app'de pozisyon var mı kontrol edin
- Futures hesabında pozisyon olmayabilir

## 📚 Dokümantasyon

- **BINANCE_FUTURES_DOKUMANTASYON.md** - Detaylı dokümantasyon (API kullanımı, örnekler, vb.)
- **HIZLI_BASLANGIÇ.md** - Hızlı başlangıç kılavuzu
- **README_BINANCE_FUTURES.md** - Bu dosya (genel bakış)

## 🎯 Kullanım Senaryoları

### Sabah Kontrolü
1. Dashboard'u aç
2. Overnight PnL'i kontrol et
3. Liquidation fiyatlarını gözden geçir

### Gün İçi Takip
1. Otomatik yenilemeyi aktif et
2. Pozisyon performansını izle
3. Risk seviyelerini kontrol et

### Haftalık Analiz
1. Günlük PnL grafiğine bak
2. Win rate'i kontrol et
3. En iyi/kötü günleri analiz et

### Aylık Rapor
1. 30 günlük PnL özeti al
2. Funding fee maliyetini hesapla
3. Leverage kullanım trendini incele

## 🤝 Katkı

Pull request'ler memnuniyetle karşılanır!

### Geliştirme Alanları
- [ ] Alarm sistemi (PnL, liquidation uyarıları)
- [ ] Webhook entegrasyonu (trading bot'lar için)
- [ ] Mobil uygulama
- [ ] Daha fazla metrik (Sharpe ratio, max drawdown, vb.)
- [ ] Email bildirimleri

## 📜 Lisans

MIT License

## ⚠️ Sorumluluk Reddi

Bu yazılım **sadece bilgilendirme amaçlıdır** ve **yatırım tavsiyesi değildir**.

- Kripto para ticareti yüksek risk içerir
- Kaybedebileceğinizden fazlasını yatırmayın
- Yazılım "olduğu gibi" sağlanır, garanti verilmez

**KENDİ RİSKİNİZE KULLANIN!**

## 📞 Destek

### Sorularınız mı var?
1. Dokümantasyonu okuyun
2. Kod içindeki docstring'lere bakın
3. GitHub issues açın

## 🎉 Başarıyla Kuruldu!

### ✅ Sonraki Adımlar

1. **Paketleri yükleyin**: `pip install -r requirements.txt`
2. **Uygulamayı başlatın**: `streamlit run portfoy.py`
3. **"Binance Futures" sekmesine tıklayın**
4. **Verilerinizi görün!**

---

**Son Güncelleme**: 27 Kasım 2024
**Versiyon**: 1.0.0
**Durum**: ✅ Kullanıma Hazır

**İyi ticaret günleri dileriz! 🚀📈**
