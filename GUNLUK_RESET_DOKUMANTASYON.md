# Günlük Değişim Oranları 00:30 Reset Özelliği

## 📋 Özet

Portföy uygulamasına, **Türkiye saati ile her gün 00:30'da günlük değişim oranlarını sıfırlayan** bir özellik eklendi. Bu sayede:

- ✅ Günün Kazananları / Kaybedenleri listeleri her gün 00:30'da sıfırlanır
- ✅ Isı haritasındaki günlük değişim oranları 00:30'da sıfırlanır
- ✅ 00:30'dan sonra yaşanan değişimlere göre sıralama ve değerlendirme yapılır
- ✅ Daha doğru ve anlamlı günlük performans takibi sağlanır

## 🔧 Yapılan Değişiklikler

### 1. `data_loader.py` - Baz Fiyat Yönetimi

#### `get_daily_base_prices()` Fonksiyonu
```python
# Günlük baz fiyatları getirir (00:30'da kaydedilmiş)
# 00:30'dan önce: Dünün baz fiyatları kullanılır
# 00:30'dan sonra: Bugünün baz fiyatları kullanılır
```

**Mantık:**
- Saat 00:00 - 00:30 arası → Önceki günün baz fiyatları kullanılır
- Saat 00:30'dan sonra → Bugünün baz fiyatları kullanılır (ilk çalıştırmada kaydedilir)

#### `should_update_daily_base()` Fonksiyonu
```python
# Günlük baz fiyatların güncellenmesi gerekip gerekmediğini kontrol eder
# Reset mantığı:
# - 00:00 - 00:30 arası: Güncelleme yapılmaz
# - 00:30'dan sonra: Eğer bugün için kayıt yoksa güncelleme yapılır
# - Her gün sadece bir kez güncellenir
```

#### `update_daily_base_prices()` Fonksiyonu
```python
# Günlük baz fiyatları günceller (00:30'dan sonra çağrılmalı)
# 1. O anki fiyatları "baz fiyat" olarak kaydeder
# 2. Günlük değişim hesaplamaları bu baz fiyatlara göre yapılır
# 3. Toplu ekleme ile hızlı çalışır
```

### 2. `portfoy.py` - Günlük Değişim Hesaplamaları

#### `_compute_daily_pct()` Fonksiyonu
```python
# Günlük yüzde değişimi hesaplar
# 00:30'da reset edilen baz fiyatları kullanır (varsa)
# Baz fiyatlar yoksa, eski yöntemi kullanır (önceki günün kapanış fiyatı)
```

**Özellikler:**
- Baz fiyatlar varsa: 00:30'daki fiyata göre değişim hesaplanır
- Baz fiyatlar yoksa: Önceki günün kapanış fiyatına göre hesaplanır (eski yöntem)
- Para birimi dönüşümlerini otomatik yapar (TRY ↔ USD)

#### `get_daily_movers()` Fonksiyonu
```python
# Günün kazananları ve kaybedenleri listesini döndürür
# 00:30'da reset edilen baz fiyatlara göre sıralanır
```

#### `render_daily_movers_section()` Fonksiyonu
```python
# Günlük kazanan/kaybeden listesini modern kart formatında gösterir
# 00:30'da reset edilen baz fiyatlara göre sıralanır
```

### 3. Isı Haritası Güncellemesi

Isı haritasındaki "Günlük Değişim %" modu da artık 00:30 reset'ini kullanır:

```python
# Günlük değişim hesaplama - 00:30 baz fiyatlarını kullan
if daily_base_prices is not None and not daily_base_prices.empty:
    heat_df = _compute_daily_pct(heat_df, daily_base_prices, USD_TRY, GORUNUM_PB)
```

## 📊 Veri Akışı

```
1. Uygulama başlatılır (Türkiye saati kontrolü)
   ↓
2. Saat kontrolü:
   - 00:00 - 00:30 arası → Dünün baz fiyatları kullanılır
   - 00:30'dan sonra → Bugünün baz fiyatları kontrol edilir
   ↓
3. Baz fiyat güncelleme:
   - Bugün için kayıt yoksa → Mevcut fiyatlar baz fiyat olarak kaydedilir
   - Bugün için kayıt varsa → Kaydedilen baz fiyatlar kullanılır
   ↓
4. Günlük değişim hesaplama:
   - Günlük K/Z = Mevcut Değer - (Baz Fiyat × Adet)
   - Günlük % = ((Mevcut Değer - Baz Değer) / Baz Değer) × 100
   ↓
5. Görüntüleme:
   - Günün Kazananları / Kaybedenleri (00:30 bazında)
   - Isı Haritası - Günlük Değişim % (00:30 bazında)
   - Günlük K/Z metriği (00:30 bazında)
```

## 🗄️ Veri Saklama

Günlük baz fiyatlar **Google Sheets**'te saklanır:

**Sheet Adı:** `daily_base_prices`

**Kolonlar:**
- `Tarih`: Kayıt tarihi (YYYY-MM-DD formatında)
- `Saat`: Kayıt saati (HH:MM:SS formatında)
- `Kod`: Varlık kodu (örn: THYAO, AAPL, YHB)
- `Fiyat`: Baz fiyat (00:30'daki fiyat)
- `PB`: Para birimi (TRY veya USD)

**Örnek Veri:**
```
Tarih       | Saat     | Kod   | Fiyat  | PB
------------|----------|-------|--------|----
2025-11-27  | 00:35:12 | THYAO | 273.50 | TRY
2025-11-27  | 00:35:12 | AAPL  | 189.95 | USD
2025-11-27  | 00:35:12 | YHB   | 1.32   | TRY
```

## ⏰ Zaman Dilimi

Tüm işlemler **Türkiye saati (Europe/Istanbul)** kullanılarak yapılır:

```python
import pytz
turkey_tz = pytz.timezone('Europe/Istanbul')
now_turkey = datetime.now(turkey_tz)
```

Bu sayede sunucu hangi saat diliminde olursa olsun, doğru zaman dilimi kullanılır.

## 🔄 Reset Davranışı

### Senaryo 1: İlk Çalıştırma (00:30'dan önce)
```
Saat: 00:15
→ Dünün baz fiyatları kullanılır
→ Güncelleme yapılmaz
→ Günlük K/Z: Dünkü değerlere göre hesaplanır
```

### Senaryo 2: İlk Çalıştırma (00:30'dan sonra)
```
Saat: 09:00
→ Bugün için baz fiyat yok → Mevcut fiyatlar kaydedilir
→ Günlük K/Z: 0 (henüz değişim yok)
→ Sonraki çalıştırmalarda bu baz fiyatlar kullanılır
```

### Senaryo 3: Gün İçi Çalıştırmalar
```
Saat: 14:30
→ Bugünün baz fiyatları kullanılır (00:30'da kaydedilmiş)
→ Günlük K/Z: 00:30'dan bu yana değişim
→ Günlük %: 00:30 fiyatına göre yüzde değişim
```

### Senaryo 4: Ertesi Gün İlk Çalıştırma
```
Saat: 08:00 (ertesi gün)
→ Bugün için baz fiyat yok → Mevcut fiyatlar kaydedilir
→ Dünün verileri artık kullanılmaz
→ Yeni gün yeni başlangıç
```

## 🎯 Kullanım Senaryoları

### 1. Günün Kazananları / Kaybedenleri
- **Amaç:** Gün içinde en çok değer kazanan/kaybeden varlıkları göster
- **Nasıl Çalışır:** 00:30'daki fiyatlara göre sıralama yapar
- **Örnek:** THYAO 00:30'da 270₺, şu anda 280₺ → +3.70% kazanç

### 2. Isı Haritası - Günlük Değişim %
- **Amaç:** Portföy varlıklarının günlük performansını görselleştir
- **Nasıl Çalışır:** 00:30'daki değerlere göre renklendirme yapar
- **Örnek:** Yeşil = kazanç, Kırmızı = kayıp (00:30 bazında)

### 3. Günlük K/Z Metriği
- **Amaç:** Günlük portföy performansını takip et
- **Nasıl Çalışır:** 00:30'daki toplam değere göre günlük kâr/zarar hesaplar
- **Örnek:** Portföy 00:30'da 100,000₺, şu anda 102,500₺ → +2,500₺ günlük kazanç

## 🧪 Test Senaryoları

### Test 1: 00:30 Öncesi Kontrol
```python
# Saat: 00:15
daily_base_prices = get_daily_base_prices()
# Beklenen: Dünün baz fiyatları dönmeli
```

### Test 2: 00:30 Sonrası İlk Çalıştırma
```python
# Saat: 00:35 (bugün için baz fiyat yok)
update_daily_base_prices(current_prices_df)
# Beklenen: Yeni baz fiyatlar kaydedilmeli
```

### Test 3: Gün İçi Çalıştırma
```python
# Saat: 14:00 (bugün için baz fiyat var)
daily_base_prices = get_daily_base_prices()
# Beklenen: Bugünün baz fiyatları dönmeli (00:30'da kaydedilmiş)
```

### Test 4: Günlük Değişim Hesaplama
```python
# Baz fiyat: 100₺, Mevcut fiyat: 105₺
günlük_değişim = (105 - 100) / 100 * 100  # +5%
# Beklenen: +5% günlük kazanç
```

## 📝 Notlar

1. **İlk Kurulum:** Uygulama ilk kez çalıştırıldığında Google Sheets'te `daily_base_prices` sheet'i otomatik oluşturulur.

2. **Cache Yönetimi:** Baz fiyatlar güncellendiğinde cache otomatik temizlenir (`get_daily_base_prices.clear()`).

3. **Fallback Mekanizması:** Baz fiyatlar yoksa veya hata oluşursa, eski yöntem kullanılır (önceki günün kapanış fiyatı).

4. **Para Birimi Dönüşümleri:** Tüm hesaplamalar görünüm para biriminde (TRY veya USD) yapılır.

5. **Performans:** Toplu ekleme (`append_rows`) kullanılarak Google Sheets API çağrıları minimize edilir.

## 🚀 Gelecek Geliştirmeler

- [ ] Haftalık / Aylık reset seçeneği
- [ ] Özel reset saati ayarlama
- [ ] Reset geçmişi görüntüleme
- [ ] Manuel reset butonu
- [ ] Reset bildirim sistemi

## 📞 Destek

Sorun yaşarsanız veya öneriniz varsa lütfen bildirin.

---

**Son Güncelleme:** 27 Kasım 2025
**Versiyon:** 1.0.0
