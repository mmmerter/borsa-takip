# 🔥 Günlük Değişim Oranları 00:30 Reset - Değişiklik Özeti

## 🎯 İstek

Günün Kazananları / Kaybedenleri listeleri ve ısı haritasındaki günlük değişim oranlarının **her gün Türkiye saati ile 00:30'da sıfırlanması** ve o saatten sonra yaşanacak değişime göre sıralanması ve değerlendirilmesi.

## ✅ Yapılan Değişiklikler

### 📝 Değiştirilen Dosyalar

#### 1. **data_loader.py**
Üç fonksiyon güncellendi:

- **`get_daily_base_prices()`**
  - 00:30'da kaydedilen baz fiyatları getiriyor
  - 00:00-00:30 arası: Dünün baz fiyatları
  - 00:30'dan sonra: Bugünün baz fiyatları

- **`should_update_daily_base()`**
  - Türkiye saati ile 00:30 kontrolü yapıyor
  - Her gün sadece bir kez güncelleme yapıyor
  
- **`update_daily_base_prices()`**
  - Mevcut fiyatları baz fiyat olarak kaydediyor
  - Toplu ekleme ile performans optimize edildi
  - Cache otomatik temizleniyor

#### 2. **portfoy.py**
Dört fonksiyon güncellendi:

- **`_compute_daily_pct()`**
  - Baz fiyatlara göre günlük değişim hesaplıyor
  - Para birimi dönüşümlerini otomatik yapıyor
  - Fallback: Baz fiyat yoksa eski yöntem kullanılıyor

- **`get_daily_movers()`**
  - 00:30 bazlı kazanan/kaybeden listesi döndürüyor
  - Baz fiyat parametreleri eklendi

- **`render_daily_movers_section()`**
  - Güncel parametrelerle çalışıyor
  - Baz fiyatları kazanan/kaybeden hesaplamalarına aktarıyor

- **Isı Haritası Günlük Değişim Modu**
  - Baz fiyatları kullanarak renklendirme yapıyor
  - "Günlük Değişim %" seçeneği 00:30 bazında çalışıyor

### 📄 Oluşturulan Dökümanlar

1. **GUNLUK_RESET_DOKUMANTASYON.md** - Detaylı teknik döküman
2. **GUNLUK_RESET_OZET.md** - Hızlı özet ve referans
3. **test_gunluk_reset_minimal.py** - Test paketi (tüm testler başarılı ✅)
4. **DEGISIKLIK_OZETI.md** - Bu dosya

## 🔄 Nasıl Çalışıyor?

### Veri Akışı
```
1. Uygulama başlatılır
   ↓
2. Türkiye saati kontrolü (pytz)
   ↓
3. Saat 00:30'dan önce mi sonra mı?
   ├─ Önce (00:00-00:30) → Dünün baz fiyatları kullan
   └─ Sonra (00:30-23:59) → Bugünün baz fiyatları kullan/kaydet
   ↓
4. Günlük değişim hesapla
   - Günlük K/Z = Mevcut Değer - (Baz Fiyat × Adet)
   - Günlük % = ((Mevcut - Baz) / Baz) × 100
   ↓
5. Görüntüle
   - Kazananlar/Kaybedenler listesi
   - Isı haritası
   - Günlük K/Z metriği
```

### Örnek Senaryo
```
00:30'da:
- THYAO: 270₺ (BAZ FİYAT)
- AAPL: 189 USD (BAZ FİYAT)

14:30'da:
- THYAO: 280₺ → Günlük Değişim: +3.70% ✅
- AAPL: 185 USD → Günlük Değişim: -2.11% ❌

Kazananlar listesinde THYAO üstte görünür!
```

## 🗄️ Veri Saklama

**Google Sheets - Yeni Sheet:**
- Sheet Adı: `daily_base_prices`
- Kolonlar: Tarih, Saat, Kod, Fiyat, PB
- Otomatik oluşturulur (ilk çalıştırmada)

**Örnek Veri:**
```
Tarih       | Saat     | Kod   | Fiyat  | PB
------------|----------|-------|--------|----
2025-11-27  | 00:35:12 | THYAO | 273.50 | TRY
2025-11-27  | 00:35:12 | AAPL  | 189.95 | USD
```

## ✅ Test Sonuçları

**Syntax Kontrol:**
```bash
✅ data_loader.py - Hatasız derlendi
✅ portfoy.py - Hatasız derlendi
```

**Fonksiyonel Testler:**
```bash
✅ Zaman mantığı - 7/7 test başarılı
✅ Hesaplama mantığı - 5/5 test başarılı
✅ Para birimi dönüşümü - 4/4 test başarılı
```

**Toplam:** 16/16 test başarılı ✅

## 🚀 Kullanıma Hazır

### İlk Çalıştırma
1. Uygulama normal şekilde başlatılır
2. Google Sheets'te `daily_base_prices` sheet'i otomatik oluşturulur
3. 00:30'dan sonraki ilk çalıştırmada baz fiyatlar kaydedilir
4. Sonraki çalıştırmalarda bu baz fiyatlar kullanılır

**Manuel işlem gerekmez!**

### Özellik Kullanımı
- **Günün Kazananları/Kaybedenleri:** Otomatik 00:30 bazında sıralanır
- **Isı Haritası:** "Günlük Değişim %" modu 00:30 bazında çalışır
- **Günlük K/Z:** Dashboard üstünde 00:30 bazında gösterilir

## 💡 Önemli Notlar

1. **Zaman Dilimi:** Türkiye saati (Europe/Istanbul) kullanılır
2. **Fallback Mekanizması:** Baz fiyat yoksa eski yöntem kullanılır
3. **Cache Yönetimi:** Güncellemelerden sonra otomatik temizlenir
4. **Performans:** Toplu ekleme ile optimize edildi
5. **Geriye Uyumluluk:** Eski hesaplama yöntemi fallback olarak korundu

## 📊 Etkilenen Özellikler

### 1. Günün Kazananları / Kaybedenleri
- ✅ 00:30'dan itibaren değişim takibi
- ✅ Gün içi performans sıralaması
- ✅ Para birimi dönüşümleri dahil

### 2. Portföy Isı Haritası
- ✅ "Günlük Değişim %" modu 00:30 bazlı
- ✅ Renk kodlaması 00:30 bazlı (yeşil=kazanç, kırmızı=kayıp)
- ✅ Hover bilgileri 00:30 bazlı

### 3. Günlük K/Z Metriği
- ✅ Dashboard üstünde 00:30 bazlı gösterim
- ✅ Toplam günlük kâr/zarar hesabı
- ✅ Sparkline grafikleri (varsa)

## 🎉 Özet

**Durum:** ✅ Tamamlandı ve Test Edildi

**Değişen Dosyalar:** 2 ana dosya (data_loader.py, portfoy.py)

**Eklenen Dökümanlar:** 4 dosya

**Test Durumu:** 16/16 başarılı ✅

**Kullanıma Hazır:** Evet ✅

---

**Tarih:** 27 Kasım 2025  
**Branch:** cursor/reset-daily-change-rates-and-re-rank-claude-4.5-sonnet-thinking-406e  
**Geliştirici:** Claude 4.5 Sonnet
