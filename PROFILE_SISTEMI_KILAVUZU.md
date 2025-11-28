# 🎯 Profil Sistemi Kılavuzu

## 📋 Genel Bakış

Portföy takip uygulamanıza **4 profil sistemi** eklenmiştir:

### Profiller

1. **🎯 MERT (Ana Profil)** - Varsayılan profil, her açılışta otomatik seçilir
2. **👩 ANNEM** - Anneniz için ayrı portföy
3. **👤 BERGUZAR** - Bergüzar için ayrı portföy
4. **📊 TOTAL** - Tüm profillerin toplamı (salt okunur, otomatik hesaplanır)

## ✨ Özellikler

### ✅ Tam Veri İzolasyonu
- Her profil tamamen ayrı varlıklara sahiptir
- Bir profildeki değişiklik diğerlerini etkilemez
- Her profilin kendi:
  - Varlık listesi
  - Satış geçmişi
  - Portföy tarihçesi
  - Pazar bazlı tarihçe (BIST, ABD, FON, vb.)

### ✅ TOTAL Profili
- Tüm profillerin varlıklarını gösterir
- Toplam değerleri otomatik hesaplar
- Salt okunur (düzenlenemez)
- Grafiklerde tüm profillerin birleşik performansını gösterir

### ✅ Kullanıcı Dostu Arayüz
- Modern profil seçici
- Görsel profil ikonları ve renkleri
- Aktif profil göstergesi
- TOTAL profili seçildiğinde uyarı mesajları

## 🚀 Kurulum

### 1. Google Sheets Yapılandırması

Profil sistemi, her profil için Google Sheets'te ayrı worksheet'ler oluşturur. İlk kurulum için:

```bash
streamlit run setup_profiles.py
```

Bu script:
- Her profil için gerekli worksheet'leri oluşturur
- Mevcut veriyi MERT profiline kopyalama seçeneği sunar
- Tüm gerekli başlıkları ekler

### 2. Worksheet Yapısı

Her profil için aşağıdaki worksheet'ler oluşturulur:

```
PortfoyData_MERT          # Ana portföy verisi
PortfoyData_ANNEM
PortfoyData_BERGUZAR

Satislar_MERT             # Satış geçmişi
Satislar_ANNEM
Satislar_BERGUZAR

portfolio_history_MERT    # Portföy tarihçesi
portfolio_history_ANNEM
portfolio_history_BERGUZAR

history_bist_MERT         # Pazar bazlı tarihçeler
history_bist_ANNEM
history_bist_BERGUZAR

history_abd_MERT
history_abd_ANNEM
history_abd_BERGUZAR

history_fon_MERT
history_fon_ANNEM
history_fon_BERGUZAR

history_emtia_MERT
history_emtia_ANNEM
history_emtia_BERGUZAR

history_nakit_MERT
history_nakit_ANNEM
history_nakit_BERGUZAR

daily_base_prices_MERT
daily_base_prices_ANNEM
daily_base_prices_BERGUZAR
```

## 📖 Kullanım

### Profil Değiştirme

1. Uygulama başlığının altında **Profil Seçici** bulunur
2. Açılır menüden istediğiniz profili seçin
3. Sayfa otomatik olarak yenilenir ve seçili profilin verileri yüklenir

### Varlık Ekleme/Düzenleme

1. İstediğiniz profili seçin (MERT, ANNEM veya BERGUZAR)
2. **Ekle/Çıkar** sekmesine gidin
3. Normal şekilde varlık ekleyin/düzenleyin
4. Değişiklikler sadece aktif profile uygulanır

⚠️ **Önemli:** TOTAL profili seçiliyken Ekle/Çıkar sekmesine giremezsiniz!

### TOTAL Profilini Görüntüleme

1. Profil seçiciden **📊 TOPLAM** seçin
2. Tüm profillerin birleşik görünümünü görün
3. Dashboard ve Portföy sekmelerinde toplam değerleri inceleyin
4. Grafikler tüm profillerin performansını gösterir

## 🔧 Teknik Detaylar

### Dosya Yapısı

```
profile_manager.py          # Profil yönetimi modülü
data_loader_profiles.py     # Profil-aware veri yükleyici
setup_profiles.py           # Kurulum scripti
portfoy.py                  # Ana uygulama (güncellenmiş)
```

### Profil Sistemi Mimarisi

```
User Interface
     ↓
Profile Selector (profile_manager.py)
     ↓
Profile-Aware Data Loader (data_loader_profiles.py)
     ↓
Google Sheets (Profile-specific worksheets)
```

### TOTAL Profili Hesaplaması

TOTAL profili, her veri çekme işleminde:
1. Tüm bireysel profillerin verilerini çeker
2. Aynı tarihteki değerleri toplar
3. Birleşik DataFrame döndürür
4. Grafiklerde toplam performansı gösterir

## 🎨 Profil Renkleri ve İkonları

| Profil | İkon | Renk | Açıklama |
|--------|------|------|----------|
| MERT | 🎯 | Mavi (#6b7fd7) | Ana profil |
| ANNEM | 👩 | Pembe (#ec4899) | Anne portföyü |
| BERGUZAR | 👤 | Yeşil (#10b981) | Bergüzar portföyü |
| TOTAL | 📊 | Turuncu (#f59e0b) | Toplam görünüm |

## 🔒 Güvenlik ve Veri İzolasyonu

- Her profil tamamen ayrı worksheet'lerde saklanır
- Bir profildeki değişiklik diğerlerini etkilemez
- TOTAL profili salt okunur ve düzenlenemez
- Session state ile profil değişiklikleri yönetilir
- Cache'ler profil değiştiğinde otomatik temizlenir

## 📊 Önemli Notlar

1. **İlk Açılış:** Uygulama her açıldığında MERT profili otomatik seçilir
2. **Veri Güvenliği:** Mevcut verileriniz MERT profiline kopyalanmalıdır (setup sırasında)
3. **TOTAL Profili:** Sadece görüntüleme içindir, düzenleme yapılamaz
4. **Performans:** Her profil ayrı cache'lenir, hızlı geçiş sağlar

## 🆘 Sorun Giderme

### Profil worksheets görünmüyor
```bash
# Setup scriptini tekrar çalıştırın
streamlit run setup_profiles.py
```

### Veri görünmüyor
- Doğru profilin seçildiğinden emin olun
- Cache'i temizlemek için sayfayı yenileyin
- Google Sheets bağlantısını kontrol edin

### TOTAL profili yanlış toplam gösteriyor
- Her profilin verilerinin güncel olduğundan emin olun
- Cache'i temizleyin (profil değiştirme otomatik temizler)
- Setup scriptini tekrar çalıştırın

## 🎯 En İyi Pratikler

1. **Düzenli Yedekleme:** Google Sheets'i düzenli yedekleyin
2. **Profil İsimlendirme:** Profil isimlerini değiştirmeyin (kod düzeyinde tanımlı)
3. **TOTAL Kontrolü:** Düzenli olarak TOTAL profilini kontrol edin
4. **Veri Girişi:** Her profil için ayrı ayrı varlık ekleyin
5. **Cache Yönetimi:** Profil değiştirirken cache otomatik temizlenir

## 🔄 Gelecek Güncellemeler (Opsiyonel)

- [ ] Profil ekleme/silme özelliği
- [ ] Profiller arası varlık transfer
- [ ] Profil bazlı raporlama
- [ ] Profil karşılaştırma grafikleri
- [ ] E-posta bildirimleri (profil bazlı)

## 📞 Destek

Herhangi bir sorun veya soru için:
- GitHub Issues açın
- Dokümantasyonu inceleyin
- Setup scriptini çalıştırın

---

**🎉 Profil sisteminiz hazır! İyi kullanımlar!**
