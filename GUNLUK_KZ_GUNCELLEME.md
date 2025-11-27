# 🕐 Günlük K/Z Güncelleme - Saat 00:30 Sıfırlama

## ✅ YAPILAN DEĞİŞİKLİKLER

### 1. **Label Değişikliği**
- **ESKİ:** "Son 24 Saat K/Z"
- **YENİ:** "Günlük K/Z"
- **Alt Yazı:** "Bugün saat 00:30'dan beri"

### 2. **Hesaplama Mantığı**
- **ESKİ:** Önceki günün kapanış fiyatına göre hesaplama
- **YENİ:** Her gün saat 00:30'daki fiyatlara göre hesaplama

---

## 🔧 TEKNİK DETAYLAR

### Yeni Fonksiyonlar (`data_loader.py`)

#### 1. `get_daily_base_prices()`
- Her gün saat 00:30'da kaydedilen baz fiyatları getirir
- Türkiye saati (Europe/Istanbul) kullanır
- 00:30'dan önceyse dünün baz fiyatlarını kullanır

#### 2. `should_update_daily_base()`
- Baz fiyatların güncellenmesi gerekip gerekmediğini kontrol eder
- 00:30'dan sonra VE bugün için henüz kayıt yoksa `True` döner

#### 3. `update_daily_base_prices(current_prices_df)`
- Günlük baz fiyatları günceller
- Google Sheets'te `daily_base_prices` tablosuna kaydeder
- Kolonlar: Tarih, Saat, Kod, Fiyat, PB

### Değiştirilen Fonksiyonlar

#### `render_kral_infobar()` - portfoy.py
- Yeni parametre eklendi: `daily_base_prices`
- Günlük K/Z hesaplaması güncellendi:
  ```python
  # Baz fiyatlardan günlük K/Z hesapla
  daily_pnl = current_value - base_value_at_00:30
  ```

---

## 📊 ÇALIŞMA MANTIĞI

### Saat 00:29'da:
1. Dünün baz fiyatları kullanılır
2. Günlük K/Z = Bugünkü değer - Dünün 00:30 fiyatları

### Saat 00:30'da (ilk çalıştırmada):
1. O anki fiyatlar "bugünün baz fiyatları" olarak kaydedilir
2. Google Sheets'te `daily_base_prices` tablosuna yazılır
3. Günlük K/Z = ₺0 (baz = şimdiki fiyat)

### Saat 00:31 - 23:59 arası:
1. Sabah 00:30'da kaydedilen baz fiyatlar kullanılır
2. Günlük K/Z = Şimdiki değer - Sabah 00:30'daki değer
3. Gün içi kazanç/kayıp gösterilir

---

## 🗂️ GOOGLE SHEETS YAPISI

### Yeni Tablo: `daily_base_prices`

| Tarih | Saat | Kod | Fiyat | PB |
|-------|------|-----|-------|-----|
| 2025-11-27 | 00:30:15 | THYAO | 175.50 | TRY |
| 2025-11-27 | 00:30:15 | UUUU | 14.36 | USD |
| 2025-11-27 | 00:30:15 | YHB | 1.84 | TRY |
| ... | ... | ... | ... | ... |

---

## 🕐 ZAMAN DİLİMİ

- **Türkiye Saati (Europe/Istanbul)** kullanılır
- pytz kütüphanesi ile timezone desteği eklendi
- Yaz/Kış saati otomatik ayarlanır

---

## ⚠️ ÖNEMLİ NOTLAR

### İlk Kullanımda:
- İlk gün veri olmayacağı için eski yöntem (önceki gün kapanışı) kullanılır
- Ertesi gün saat 00:30'dan sonra düzgün çalışmaya başlar

### Baz Fiyat Yoksa:
- Kod otomatik olarak eski yönteme döner (geriye uyumlu)
- Hata durumunda uygulama kilitlenmez

### Google Sheets Erişimi:
- Eğer sheets'e erişim yoksa, eski yöntem kullanılır
- Kullanıcı uyarılmaz (sessiz hata yönetimi)

---

## 🎯 KULLANIM ÖRNEĞİ

### Senaryo:
```
27 Kasım 2025 - Saat 00:30:
- THYAO: ₺175.50
- Baz fiyat kaydedildi

27 Kasım 2025 - Saat 10:00:
- THYAO: ₺180.00
- Günlük K/Z = (₺180 - ₺175.50) × 100 adet = ₺450

27 Kasım 2025 - Saat 16:00:
- THYAO: ₺178.00
- Günlük K/Z = (₺178 - ₺175.50) × 100 adet = ₺250

28 Kasım 2025 - Saat 00:30:
- THYAO: ₺177.00
- YENİ baz fiyat kaydedildi: ₺177.00
- Günlük K/Z sıfırlandı

28 Kasım 2025 - Saat 10:00:
- THYAO: ₺179.00
- Günlük K/Z = (₺179 - ₺177) × 100 adet = ₺200
```

---

## ✅ TEST EDİLDİ

- [x] Syntax kontrolü geçti
- [x] Import'lar doğru
- [x] Timezone desteği eklendi (pytz)
- [x] Geriye uyumlu (eski yöntem fallback)
- [x] Hata yönetimi eklendi

---

## 📦 GEREKLİ PAKETLER

```bash
pip install pytz
```

Zaten kurulu: pandas, gspread, streamlit, yfinance

---

## 🚀 SONUÇ

**Günlük K/Z artık her gün saat 00:30'da sıfırlanır ve gün içi performansı gösterir!**

Eski "Son 24 Saat" yerine gerçek "günlük" performansı görürsünüz. ✅
