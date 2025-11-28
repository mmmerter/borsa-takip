# 🎯 PROFİL SİSTEMİ - BAŞLATMA KILAVUZU

## ✅ SİSTEM HAZIR!

Profil sisteminiz mevcut Google Sheets yapınızı kullanacak şekilde yapılandırıldı:

```
✅ Sheet1 (Ana sayfa)  → 🎯 MERT Profili (mevcut verileriniz)
✅ annem               → 👩 ANNEM Profili  
✅ berguzar            → 👑 BERGUZAR Profili
✅ total               → 📊 TOTAL Profili (otomatik toplam)
```

## 🚀 İLK KURULUM (Bir Kere Yapılacak)

### Adım 1: Sheets Yapısını Doğrula
```bash
streamlit run setup_profiles_existing.py
```

Bu script:
- Mevcut sheet'leri kontrol eder
- Eksik varsa oluşturur
- İsteğe bağlı tarihçe sheet'leri ekler

### Adım 2: Uygulamayı Başlat
```bash
streamlit run portfoy.py
```

**Hepsi bu kadar!** 🎉

## 📖 HIZLI KULLANIM

### Profil Değiştirme
1. Uygulama açılır (MERT profili otomatik seçili)
2. Başlık altında **Profil Seçici** var
3. Açılır menüden profil seçin → Sayfa yenilenir

### Varlık Ekleme
1. İstediğiniz profili seçin (MERT/ANNEM/BERGUZAR)
2. Ekle/Çıkar sekmesine gidin
3. Normal şekilde varlık ekleyin
4. **ÖNEMLİ:** Her profil ayrı varlıklara sahip!

### TOTAL Görüntüleme
1. Profil seçici → "📊 TOPLAM" seçin
2. Tüm profillerin birleşik görünümünü görün
3. **DİKKAT:** TOTAL'de düzenleme yapılamaz!

## 🎨 PROFİL ÖZELLİKLERİ

### 🎯 MERT (Ana Profil)
- **Sheet:** Sheet1 (mevcut verileriniz)
- **Renk:** Mavi
- **Durum:** Her açılışta varsayılan
- **Özellik:** Şu anki tüm verilerinizi içeriyor

### 👩 ANNEM
- **Sheet:** annem
- **Renk:** Pembe
- **Durum:** Boş (ekleyeceksiniz)
- **Özellik:** Tamamen ayrı portföy

### 👑 BERGUZAR
- **Sheet:** berguzar
- **Renk:** Yeşil
- **Durum:** Boş (ekleyeceksiniz)
- **Özellik:** Tamamen ayrı portföy

### 📊 TOTAL
- **Sheet:** total (otomatik güncellenir)
- **Renk:** Turuncu
- **Durum:** Otomatik hesaplanır
- **Özellik:** Salt okunur, tüm profillerin toplamı

## 💡 ÖNEMLİ BİLGİLER

### ✅ Güvenlik
- Her profil tamamen ayrı
- Bir profildeki değişiklik diğerlerini etkilemez
- Mevcut verileriniz (MERT) korunuyor

### ✅ Otomasyonlar
- TOTAL otomatik hesaplanır
- Cache otomatik temizlenir
- Profil değişimi anlıktır

### ⚠️ Dikkat Edilecekler
- TOTAL'de düzenleme yapılamaz
- Her profile ayrı varlık ekleyin
- Profil isimleri değiştirilemez

## 📊 KULLANIM ÖRNEKLERİ

### Örnek 1: Anneniz İçin Altın Ekleme
```
1. Profil Seçici → "👩 Annem"
2. Ekle/Çıkar → Ekle
3. Pazar: EMTIA
4. Kod: Gram Altın
5. Adet: 50
6. Fiyat: 3000
7. Kaydet
✅ Sadece ANNEM profilinde görünür!
```

### Örnek 2: Tüm Portföyleri Görme
```
1. MERT → Kendi varlıklarınızı görün
2. ANNEM → Annenizin varlıklarını görün
3. BERGUZAR → Bergüzar'ın varlıklarını görün
4. TOTAL → Hepsinin toplamını görün
✅ Her biri ayrı, TOTAL'de hepsi!
```

## 🔧 SORUN GİDERME

### "annem" sheet'i bulunamadı
```bash
streamlit run setup_profiles_existing.py
# Eksik sheet'leri oluşturacak
```

### Veri görünmüyor
- Doğru profil seçili mi kontrol edin
- Sayfayı yenileyin (F5)
- Profil değiştirip tekrar dönün

### TOTAL yanlış gösteriyor
- Her profilin verilerini kontrol edin
- Sayfayı yenileyin
- setup_profiles_existing.py'yi tekrar çalıştırın

## 📁 OLUŞTURULAN DOSYALAR

### Ana Sistem Dosyaları
- ✅ `profile_manager.py` - Profil yönetimi
- ✅ `data_loader_profiles.py` - Profil-aware veri yükleyici
- ✅ `portfoy.py` - Ana uygulama (güncellendi)

### Kurulum ve Test
- ✅ `setup_profiles_existing.py` - Sheets kurulum scripti
- ✅ `verify_profile_files.py` - Dosya doğrulama
- ✅ `test_profile_system.py` - Test scripti

### Dokümantasyon
- ✅ `HIZLI_KULLANIM.md` - Hızlı kullanım kılavuzu
- ✅ `PROFILE_SISTEMI_KILAVUZU.md` - Detaylı kılavuz
- ✅ `PROFILE_SYSTEM_SUMMARY.md` - Teknik özet
- ✅ `BASLATMA_KILAVUZU.md` - Bu dosya

## 🎯 SONRAKİ ADIMLAR

### 1. İlk Çalıştırma
```bash
# Sheets'i kontrol et
streamlit run setup_profiles_existing.py

# Uygulamayı başlat
streamlit run portfoy.py
```

### 2. Profilleri Test Et
1. MERT → Mevcut varlıklarınızı görün
2. ANNEM → Boş olmalı, yeni varlık ekleyin
3. BERGUZAR → Boş olmalı, yeni varlık ekleyin
4. TOTAL → Hepsini görmeli

### 3. Günlük Kullanım
- Her gün TOTAL'i kontrol edin
- Her profile ayrı varlıklar ekleyin
- Grafikleri inceleyin

## 🎊 HAZIR!

Profil sisteminiz kullanıma hazır! 

**Tek komut:**
```bash
streamlit run portfoy.py
```

---

## 📞 İletişim

Sorun yaşarsanız:
1. `HIZLI_KULLANIM.md` dosyasını okuyun
2. `setup_profiles_existing.py` çalıştırın
3. Google Sheets'te sheet'leri kontrol edin

**🎉 Başarılar! İyi kullanımlar!**
