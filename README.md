# 🏦 Merter'in Terminali - Portföy Yönetim Sistemi

Profesyonel portföy takip ve analiz uygulaması. BIST, ABD borsaları, kripto paralar, fonlar ve emtialar için kapsamlı portföy yönetimi.

## ✨ Özellikler

### 📊 Portföy Yönetimi
- **Çoklu Profil Desteği**: MERT, ANNEM, BERGUZAR, İKRAMİYE ve TOPLAM profilleri
- **Gerçek Zamanlı Fiyat Güncellemeleri**: Yahoo Finance, TEFAS ve CoinGecko entegrasyonu
- **Kapsamlı Analiz**: Kâr/zarar hesaplamaları, performans metrikleri, grafikler
- **Pazar Bazlı Takip**: BIST, ABD, Kripto, Fon, Emtia ve Nakit ayrımı

### 📈 Analiz ve Raporlama
- **Performans Metrikleri**: Haftalık, aylık ve YTD performans
- **Görselleştirme**: Modern pie/bar chart'lar, tarihsel grafikler
- **Günlük Hareketler**: En çok kazandıran/kaybettiren varlıklar
- **Haberler**: Portföy varlıkları için otomatik haber toplama

### 🔧 Teknik Özellikler
- **Modüler Mimari**: Ayrılmış modüller (data_loader, charts, utils, vb.)
- **Profesyonel Logging**: Detaylı log sistemi
- **Hata Yönetimi**: Custom exception sınıfları
- **Veri Doğrulama**: Kapsamlı validator fonksiyonları
- **Config Yönetimi**: Merkezi yapılandırma sistemi

## 🚀 Kurulum

### Gereksinimler
- Python 3.8+
- Google Sheets API credentials
- Streamlit

### Adımlar

1. **Repository'yi klonlayın**
```bash
git clone <repository-url>
cd portfoy
```

2. **Virtual environment oluşturun**
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

3. **Bağımlılıkları yükleyin**
```bash
pip install -r requirements.txt
```

4. **Google Sheets API ayarlarını yapın**
   - `GOOGLE_SHEETS_KURULUM.md` dosyasını takip edin
   - Service account credentials'ı `.streamlit/secrets.toml` dosyasına ekleyin

5. **Uygulamayı başlatın**
```bash
streamlit run portfoy.py
```

## 📁 Proje Yapısı

```
portfoy/
├── portfoy.py              # Ana Streamlit uygulaması
├── data_loader.py          # Google Sheets ve API entegrasyonları
├── data_loader_profiles.py # Profil bazlı veri yükleme
├── profile_manager.py     # Profil yönetim sistemi
├── charts.py              # Grafik ve görselleştirme
├── utils.py               # Yardımcı fonksiyonlar
├── config.py              # Yapılandırma yönetimi
├── logger.py              # Logging sistemi
├── exceptions.py          # Custom exception sınıfları
├── validators.py          # Veri doğrulama
├── tests/                 # Unit testler
│   ├── test_config.py
│   └── test_validators.py
├── requirements.txt       # Python bağımlılıkları
├── pytest.ini            # Pytest yapılandırması
└── README.md             # Bu dosya
```

## 🧪 Test

```bash
# Tüm testleri çalıştır
pytest

# Belirli bir test dosyası
pytest tests/test_validators.py

# Verbose mod
pytest -v

# Coverage ile
pytest --cov=. --cov-report=html
```

## 🔧 Yapılandırma

Yapılandırma ayarları `config.py` modülünde merkezi olarak yönetilir:

```python
from config import get_config

config = get_config()

# App ayarları
config.app.page_title = "Özel Başlık"
config.app.cache_ttl_sheet_data = 300  # 5 dakika

# Market ayarları
config.market.known_funds.append("YENI_FON")
```

## 📝 Logging

Profesyonel logging sistemi kullanımı:

```python
from logger import get_logger

logger = get_logger()

logger.info("Bilgi mesajı")
logger.warning("Uyarı mesajı")
logger.error("Hata mesajı")
```

Log dosyaları `logs/` klasöründe günlük olarak saklanır.

## 🛡️ Hata Yönetimi

Custom exception sınıfları kullanımı:

```python
from exceptions import DataLoadError, GoogleSheetsError, ValidationError

try:
    data = load_data()
except GoogleSheetsError as e:
    logger.error(f"Sheets hatası: {e}")
except ValidationError as e:
    logger.error(f"Doğrulama hatası: {e.field}: {e}")
```

## ✅ Veri Doğrulama

Validator fonksiyonları ile veri doğrulama:

```python
from validators import validate_price, validate_portfolio_row

# Fiyat doğrulama
price = validate_price(10.5)

# Portföy satırı doğrulama
row = validate_portfolio_row({
    "Kod": "THYAO",
    "Pazar": "BIST",
    "Adet": 100,
    "Maliyet": 50.5
})
```

## 🔐 Güvenlik

- API anahtarları `.streamlit/secrets.toml` dosyasında saklanır (git'e commit edilmez)
- Google Sheets service account kullanılır
- Input validation tüm kullanıcı girdilerinde yapılır

## 📚 Dokümantasyon

- `HIZLI_BASLANGIÇ.md` - Hızlı başlangıç kılavuzu
- `GOOGLE_SHEETS_KURULUM.md` - Google Sheets kurulum rehberi
- `BASLATMA_KILAVUZU.md` - Detaylı başlatma kılavuzu

## 🤝 Katkıda Bulunma

1. Fork edin
2. Feature branch oluşturun (`git checkout -b feature/amazing-feature`)
3. Commit edin (`git commit -m 'Add amazing feature'`)
4. Push edin (`git push origin feature/amazing-feature`)
5. Pull Request açın

## 📄 Lisans

Bu proje özel kullanım içindir.

## 👨‍💻 Geliştirici

Merter'in Terminali - Profesyonel Portföy Yönetim Sistemi

## 🆘 Destek

Sorularınız için:
- GitHub Issues kullanın
- Dokümantasyon dosyalarını kontrol edin
- Log dosyalarını inceleyin (`logs/` klasörü)

---

**Son Güncelleme**: 2024
**Versiyon**: 2.0.0 (Profesyonel İyileştirmeler)
