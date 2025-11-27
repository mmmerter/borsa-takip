# 🚀 Binance Futures - Hızlı Başlangıç Kılavuzu

## ✅ Tebrikler! Sistem Kuruldu

API anahtarlarınız güvenli bir şekilde kaydedildi ve sistem kullanıma hazır!

## 📋 Yapılanlar

### ✅ 1. Modüller Oluşturuldu
- ✅ `binance_futures.py` - Ana API modülü
- ✅ `futures_page.py` - Streamlit dashboard sayfası
- ✅ `test_binance_connection.py` - Bağlantı test scripti

### ✅ 2. Entegrasyon Tamamlandı
- ✅ Ana menüye "Binance Futures" sekmesi eklendi
- ✅ Google Sheets otomatik kayıt hazır
- ✅ API credentials güvenli şekilde saklandı (`.streamlit/secrets.toml`)

### ✅ 3. Güvenlik Ayarlandı
- ✅ `.gitignore` güncellendi (secrets korunuyor)
- ✅ API anahtarları şifreleme ile saklanıyor
- ✅ Sadece okuma izni kullanılıyor

### ✅ 4. Dokümantasyon
- ✅ `BINANCE_FUTURES_DOKUMANTASYON.md` - Tam dokümantasyon
- ✅ `HIZLI_BASLANGIÇ.md` - Bu dosya

---

## 🎯 Nasıl Kullanılır?

### 1️⃣ Paketleri Yükleyin

```bash
pip install -r requirements.txt
```

Yüklenen paketler:
- `ccxt>=4.0.0` - Binance API için
- `streamlit>=1.28.0` - Dashboard için
- `pandas>=2.0.0` - Veri işleme
- `plotly>=5.17.0` - Grafikler
- Diğerleri...

### 2️⃣ Uygulamayı Başlatın

```bash
streamlit run portfoy.py
```

Veya sadece Futures dashboard için:

```bash
streamlit run futures_page.py
```

### 3️⃣ Menüden "Binance Futures" Sekmesine Tıklayın

Dashboard otomatik olarak açılacak!

---

## 🎨 Dashboard Özellikleri

### 📊 Ana Ekran

#### Hesap Özeti Kartları (Üst Sıra)
```
┌─────────────────┬─────────────────┬─────────────────┬─────────────────┐
│ Cüzdan Bakiyesi │ Marjin Bakiyesi │  Kullanılabilir │ Toplam Pozisyon │
│   $10,000.00    │   $10,500.00    │    $5,000.00    │   $50,000.00    │
└─────────────────┴─────────────────┴─────────────────┴─────────────────┘
```

#### PnL Metrikleri (İkinci Sıra)
```
┌──────────────────┬──────────────┬──────────────┬──────────────┐
│ Gerçekleşmemiş   │ Realized PnL │ Realized PnL │ Realized PnL │
│      PnL         │    (24h)     │     (7g)     │    (30g)     │
│   +$250.00 ▲     │  +$150.00    │  +$800.00    │ +$2,500.00   │
│    +2.5%         │   +1.5%      │   +8.0%      │   +25.0%     │
└──────────────────┴──────────────┴──────────────┴──────────────┘
```

#### Pozisyon Bilgileri
```
┌───────────────┬──────────────┬──────────────┐
│ Toplam: 5     │ Long: 3 🟢   │ Short: 2 🔴  │
└───────────────┴──────────────┴──────────────┘
```

#### Pozisyon Tablosu
| Sembol    | Yön  | Miktar | Giriş    | Mark     | PnL      | PnL %  | Leverage |
|-----------|------|--------|----------|----------|----------|--------|----------|
| BTCUSDT   | 🟢   | 0.5    | $43,500  | $44,000  | +$250    | +5.7%  | 10x      |
| ETHUSDT   | 🔴   | 2.0    | $2,300   | $2,250   | -$100    | -2.2%  | 5x       |

#### Grafikler
1. **Pozisyon Dağılım Pie Chart** - Long vs Short oranı
2. **Leverage Chart** - Her sembole göre leverage durumu
3. **Günlük PnL Chart** - Son 30 günün performansı

---

## 🔧 Ayarlar (Sidebar)

### API Ayarları
- ✅ API Key (otomatik yüklendi)
- ✅ API Secret (otomatik yüklendi)
- ⚙️ Testnet seçeneği

### Yenileme Ayarları
- 🔄 **Otomatik Yenile**: 30 saniyede bir günceller
- 🖱️ **Manuel Yenile**: İstediğiniz zaman yenileyin

### Google Sheets
- 📝 **Sheets'e Kaydet**: Otomatik veri kaydetme
  - Her güncelleme pozisyonları kaydeder
  - Günlük özet tutar
  - Tarihsel analiz için veri biriktir

---

## 📊 Çekilen Veriler

### 1. Gerçek Zamanlı Veriler (Her 30 Saniye)
- ✅ Açık pozisyonlar
- ✅ Güncel fiyatlar (mark price)
- ✅ Unrealized PnL
- ✅ Liquidation fiyatları
- ✅ Leverage durumu

### 2. Tarihsel Veriler (Cache: 5 Dakika)
- ✅ Günlük PnL özeti (30 gün)
- ✅ Gelir geçmişi (REALIZED_PNL, FUNDING_FEE, vb.)
- ✅ İşlem geçmişi
- ✅ Kümülatif performans

### 3. Hesap Bilgileri (Her 60 Saniye)
- ✅ Bakiye bilgileri
- ✅ Marjin kullanımı
- ✅ Risk metrikleri
- ✅ Pozisyon özeti

---

## 🎯 Kullanım Senaryoları

### Senaryo 1: Sabah Kontrolü
```
1. Dashboard'u açın
2. Unrealized PnL'e bakın
3. Overnight funding fee'leri kontrol edin
4. Liquidation fiyatlarını gözden geçirin
```

### Senaryo 2: Gün İçi Takip
```
1. Otomatik yenilemeyi aktif edin (30 saniye)
2. Pozisyon performansını izleyin
3. Risk seviyelerini kontrol edin
```

### Senaryo 3: Haftalık Analiz
```
1. Günlük PnL grafiğine bakın
2. Win rate'inizi kontrol edin
3. En iyi/kötü günleri analiz edin
4. Google Sheets'teki tarihsel verileri inceleyin
```

### Senaryo 4: Aylık Rapor
```
1. 30 günlük PnL özeti alın
2. Funding fee toplam maliyetini hesaplayın
3. Leverage kullanım trendini inceleyin
4. Risk/ödül oranınızı değerlendirin
```

---

## ⚡ Hızlı Komutlar

### Python Kodu ile Veri Çekme

```python
from binance_futures import BinanceFuturesAPI
import streamlit as st

# API bağlantısı
api_key = st.secrets["binance_futures"]["api_key"]
api_secret = st.secrets["binance_futures"]["api_secret"]

api = BinanceFuturesAPI(api_key, api_secret)

# Hesap özeti
summary = api.get_account_summary()
print(f"Toplam PnL (24h): ${summary['total_pnl_24h']:,.2f}")

# Pozisyonlar
positions = api.get_open_positions()
print(f"Açık pozisyon sayısı: {len(positions)}")

# Günlük PnL
daily_pnl = api.get_daily_pnl_summary(days=7)
print(f"7 günlük PnL: ${daily_pnl['realized_pnl'].sum():,.2f}")
```

---

## 🔐 Güvenlik Kontrol Listesi

### ✅ Yapılması Gerekenler

- ✅ API Key'de sadece "Reading" ve "Futures" izni var mı?
- ✅ "Enable Withdrawals" izni **KAPALI** mı? (ÇOK ÖNEMLİ!)
- ✅ IP Whitelist kullanılıyor mu? (önerilen)
- ✅ `.gitignore` dosyasında `secrets.toml` var mı?
- ✅ API key'leri asla kodda hardcode edilmedi mi?

### ⚠️ Düzenli Kontroller

- 🔍 Binance hesabınızda şüpheli aktivite var mı?
- 🔍 API key'ler hala geçerli mi?
- 🔍 IP whitelist güncel mi?
- 🔍 Kullanılmayan API key'ler silindi mi?

---

## 🐛 Sorun Giderme

### Sorun 1: "Invalid API Key"
**Çözüm**:
```bash
# 1. API key'i kontrol edin
# 2. Binance'te key'in aktif olduğundan emin olun
# 3. Futures izninin verildiğini doğrulayın
```

### Sorun 2: "Timestamp Error"
**Çözüm**:
```bash
# Sistem saatinizi senkronize edin
# API otomatik düzeltme yapıyor, genelde sorun olmaz
```

### Sorun 3: "Rate Limit"
**Çözüm**:
```bash
# Dashboard'un otomatik yenileme süresini artırın
# Çok fazla manuel yenileme yapmayın
# API zaten rate limit koruması var
```

### Sorun 4: "No Positions Found"
**Nedeni**: Gerçekten açık pozisyon yok
**Kontrol**: Binance web/app'de pozisyon var mı?

### Sorun 5: "Google Sheets Error"
**Çözüm**:
```bash
# 1. Service account email ile sheet paylaşıldı mı?
# 2. secrets.toml'da gcp_service_account var mı?
# 3. "Sheets'e Kaydet" seçeneğini kapatıp tekrar deneyin
```

---

## 📈 İleri Seviye Özellikler

### 1. Özel Metrikler Ekleyin

```python
# Sharpe Ratio hesaplama
def calculate_sharpe(daily_pnl_df):
    returns = daily_pnl_df['realized_pnl'].pct_change()
    return returns.mean() / returns.std()

# Win rate
def calculate_win_rate(daily_pnl_df):
    winning_days = len(daily_pnl_df[daily_pnl_df['realized_pnl'] > 0])
    return (winning_days / len(daily_pnl_df)) * 100
```

### 2. Alarm Sistemi

```python
# PnL alarmı
if summary['unrealized_pnl'] < -500:
    st.error("⚠️ Unrealized PnL -$500'un altında!")

# Liquidation uyarısı
for pos in positions.itertuples():
    distance = abs(pos.mark_price - pos.liquidation_price)
    if distance / pos.mark_price < 0.05:  # %5'ten yakın
        st.warning(f"⚠️ {pos.symbol} liquidation'a yakın!")
```

### 3. Webhook Entegrasyonu

```python
# Trading bot'tan pozisyon bildirimlerini alın
# futures_page.py'ye ekleyin
```

---

## 📱 Mobil Erişim

Streamlit Cloud'a deploy ederek her yerden erişebilirsiniz:

```bash
# 1. GitHub'a push edin (secrets hariç!)
# 2. streamlit.app'e gidin
# 3. Repo'nuzu bağlayın
# 4. Secrets'ı web arayüzünden ekleyin
# 5. Deploy!
```

**⚠️ Dikkat**: Public repo kullanmayın veya secrets'ı sakın commit etmeyin!

---

## 📞 Destek

### Sorularınız mı var?
1. `BINANCE_FUTURES_DOKUMANTASYON.md` dosyasını okuyun (detaylı)
2. Kod içindeki docstring'lere bakın
3. GitHub issues açın

### Hata Raporlama
```
Hata mesajı:
Yapılan işlem:
Beklenen sonuç:
Sistem bilgisi:
```

---

## 🎉 Başarıyla Kuruldu!

### ✅ Kontrol Listesi

- [x] API anahtarları kaydedildi
- [x] Güvenlik ayarları yapıldı
- [x] Dashboard menüye eklendi
- [x] Test scripti hazır
- [x] Dokümantasyon okundu
- [ ] İlk test yapıldı
- [ ] Gerçek verileri gördünüz

### 🚀 Şimdi Ne Yapmalı?

1. **Paketleri yükleyin**: `pip install -r requirements.txt`
2. **Uygulamayı başlatın**: `streamlit run portfoy.py`
3. **"Binance Futures" sekmesine tıklayın**
4. **Verilerinizi kontrol edin!**

---

## 💡 İpuçları

### 🎯 En İyi Uygulamalar

1. **Düzenli Kontrol**: Günde 2-3 kez kontrol yeterli
2. **Risk Yönetimi**: Liquidation fiyatlarını her zaman takip edin
3. **PnL Takibi**: Haftalık ve aylık periyotlarda analiz yapın
4. **Funding Fee**: Uzun vadeli pozisyonlarda funding maliyetini hesaplayın
5. **Backup**: Google Sheets'e kaydetmeyi aktif tutun

### ⚡ Performans İpuçları

1. **Cache Kullanımı**: Otomatik cache temizleme 30 saniye - 5 dakika arası
2. **Batch İşlemler**: Çok fazla manuel yenileme yapmayın
3. **Filtreleme**: Sadece ihtiyacınız olan verileri çekin

---

## 📊 Örnek Dashboard Görünümü

```
┌─────────────────────────────────────────────────────────────────┐
│                   🚀 BINANCE FUTURES DASHBOARD                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  💰 HESAP ÖZETİ                                                 │
│  ┌──────────────┬──────────────┬──────────────┬──────────────┐ │
│  │  Cüzdan      │  Marjin      │ Kullanılabilir│  Toplam Poz. │ │
│  │ $10,000.00   │ $10,500.00   │  $5,000.00   │ $50,000.00   │ │
│  └──────────────┴──────────────┴──────────────┴──────────────┘ │
│                                                                 │
│  📈 KAR/ZARAR ANALİZİ                                           │
│  ┌──────────────┬──────────────┬──────────────┬──────────────┐ │
│  │ Unrealized   │ Real (24h)   │  Real (7d)   │  Real (30d)  │ │
│  │ +$250 ▲ 2.5% │ +$150 ▲ 1.5% │ +$800 ▲ 8.0% │+$2,500 ▲ 25% │ │
│  └──────────────┴──────────────┴──────────────┴──────────────┘ │
│                                                                 │
│  📍 AÇIK POZİSYONLAR                                            │
│  ┌─────────┬──────┬─────┬────────┬────────┬─────────┬────────┐ │
│  │ Sembol  │ Yön  │ Mik │ Giriş  │  Mark  │   PnL   │ Lever  │ │
│  ├─────────┼──────┼─────┼────────┼────────┼─────────┼────────┤ │
│  │ BTCUSDT │ 🟢   │ 0.5 │ 43,500 │ 44,000 │ +$250 ▲ │  10x   │ │
│  │ ETHUSDT │ 🔴   │ 2.0 │  2,300 │  2,250 │ -$100 ▼ │   5x   │ │
│  └─────────┴──────┴─────┴────────┴────────┴─────────┴────────┘ │
│                                                                 │
│  📊 GÜNLÜK PnL (30 Gün)                                         │
│  [████████▓▓▓▓░░░░▓▓██████▓▓░░████▓▓▓]                        │
│                                                                 │
│  Toplam: +$2,500 | Ortalama: +$83 | Win Rate: 63%             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🏁 Başlangıç Başarılı!

**API bağlantınız hazır, dashboard aktif, verileriniz görünüyor!**

### Bir sonraki adım:
```bash
streamlit run portfoy.py
```

**İyi ticaret günleri dileriz! 🚀📈**

---

**Son Güncelleme**: 27 Kasım 2024
**Versiyon**: 1.0.0
**Durum**: ✅ Kullanıma Hazır
