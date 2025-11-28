# 🚀 Profil Sistemi - Hızlı Kullanım Kılavuzu

## 📊 Google Sheets Yapınız

Mevcut Google Sheets yapınız kullanılıyor:

```
PortfoyData (Spreadsheet)
├── Sheet1 (Ana sayfa)  → 🎯 MERT Profili
├── annem               → 👩 ANNEM Profili
├── berguzar            → 👤 BERGUZAR Profili
└── total               → 📊 TOTAL Profili (otomatik)
```

## ✅ Sistem Özellikleri

### Ana Özellikler
- ✅ **Tam veri izolasyonu**: Her profil kendi varlıklarını tutar
- ✅ **Otomatik toplam**: TOTAL profili hepsini birleştirir
- ✅ **Kolay geçiş**: Tek tıkla profil değiştirme
- ✅ **Mevcut veriyi koruma**: Ana profiliniz (MERT) değişmedi

### Profiller

| Profil | Sheet | Açıklama |
|--------|-------|----------|
| 🎯 **MERT** | Sheet1 (ana sayfa) | Sizin mevcut portföyünüz |
| 👩 **ANNEM** | annem | Annenizin portföyü |
| 👤 **BERGUZAR** | berguzar | Bergüzar'ın portföyü |
| 📊 **TOTAL** | total | Otomatik toplam (salt okunur) |

## 🎯 Hızlı Başlangıç

### 1. Uygulamayı Başlatın
```bash
streamlit run portfoy.py
```

### 2. Profil Seçin
- Uygulama başlığının altında **Profil Seçici** var
- Açılır menüden istediğiniz profili seçin
- Sayfa otomatik yenilenir

### 3. Varlık Ekleyin
1. İstediğiniz profili seçin (MERT, ANNEM veya BERGUZAR)
2. **Ekle/Çıkar** sekmesine gidin
3. Normal şekilde varlık ekleyin
4. Değişiklik sadece seçili profile uygulanır

### 4. Toplam Görüntüleyin
- **TOTAL** profilini seçin
- Tüm profillerin birleşik görünümünü görün
- ⚠️ TOTAL'de düzenleme yapılamaz!

## 📖 Kullanım Senaryoları

### Senaryo 1: Anneniz İçin Portföy Ekleme
```
1. Profil seçici → "👩 Annem" seçin
2. Ekle/Çıkar → Ekle
3. Örnek: Gram Altın ekleyin (50 gram, 3000₺)
4. Portföy sekmesinde görüntüleyin
5. MERT profiline geçin → Altın görünmez ✅
```

### Senaryo 2: Tüm Profilleri Kontrol
```
1. Profil seçici → "📊 TOPLAM" seçin
2. Dashboard'da toplam değerleri görün
3. Portföy sekmesinde tüm varlıkları görün
4. Grafikler tüm profillerin performansını gösterir
```

### Senaryo 3: Profiller Arası Geçiş
```
1. MERT → Hisselerinizi görün
2. ANNEM → Altın ve fondları görün
3. BERGUZAR → Kripto varlıkları görün
4. TOTAL → Hepsinin toplamını görün
```

## ⚠️ Önemli Notlar

### ✅ Yapabilecekleriniz
- ✅ Her profile ayrı varlıklar eklemek
- ✅ Profiller arasında hızlıca geçiş yapmak
- ✅ Her profilin ayrı grafiklerini görmek
- ✅ TOTAL'de birleşik görünümü görmek

### ❌ Yapamayacaklarınız
- ❌ TOTAL profilinde düzenleme yapmak
- ❌ Profiller arası varlık kopyalamak (manuel yapmalısınız)
- ❌ Profil isimleri değiştirmek

## 🔧 Sorun Giderme

### "Sheet bulunamadı" hatası
```bash
# Sheets'i kontrol edin ve oluşturun
streamlit run setup_profiles_existing.py
```

### Veri görünmüyor
- Doğru profilin seçildiğinden emin olun
- Sayfayı yenileyin (F5)
- Cache'i temizleyin (profil değiştir → geri dön)

### TOTAL yanlış toplam gösteriyor
- Her profilin verilerini kontrol edin
- Sayfayı yenileyin
- Profil değiştirin (cache temizlenir)

## 📊 Veri Yapısı

### Ana Sheets (Profil Verileri)
```
Sheet1 (MERT)  → Mevcut portföyünüz
annem          → Annenizin varlıkları
berguzar       → Bergüzar'ın varlıkları
total          → Otomatik hesaplanan toplam
```

### Tarihçe Sheets (Opsiyonel)
Her profil için ayrı tarihçe tutulabilir:
```
Satislar_ANNEM             → Annem'in satış geçmişi
Satislar_BERGUZAR          → Bergüzar'ın satış geçmişi
portfolio_history_ANNEM    → Annem'in portföy tarihçesi
portfolio_history_BERGUZAR → Bergüzar'ın portföy tarihçesi
...
```

## 💡 İpuçları

1. **İlk Açılış**: Her zaman MERT profili açılır
2. **Hızlı Geçiş**: Profil seçici her zaman üstte görünür
3. **TOTAL Kontrolü**: Günlük TOTAL'i kontrol edin
4. **Veri Güvenliği**: Her profil ayrı sheet'te, karışma riski yok
5. **Cache**: Profil değiştirince otomatik temizlenir

## 🎯 Sonraki Adımlar

1. ✅ Uygulamayı başlatın
2. ✅ Her profile varlıklar ekleyin
3. ✅ TOTAL'i kontrol edin
4. ✅ Grafikleri inceleyin

## 📞 Destek

Sorun olursa:
1. `setup_profiles_existing.py` çalıştırın
2. Google Sheets'te sheet'leri kontrol edin
3. Dokümantasyonu okuyun: `PROFILE_SISTEMI_KILAVUZU.md`

---
**🎉 Profil sisteminiz hazır! İyi kullanımlar!**

## 🚀 Tek Satırda Başlatma
```bash
streamlit run portfoy.py
```

Hepsi bu kadar! 🎊
