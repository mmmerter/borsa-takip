# Haftalık/Aylık/YTD Performans Sorunu ve Çözümü

## 🔴 Sorun

Haftalık K/Z, Aylık K/Z ve YTD Performans metrikleri **hepsi aynı değeri gösteriyordu**: ₺-43,620 (-14.08%)

Bu üç metriğin aynı değeri göstermesi mantıksızdı ve kullanıcıyı yanıltıyordu.

## 🔍 Sorunun Kök Nedeni

`data_loader.py` dosyasındaki `get_timeframe_changes()` fonksiyonunda bir mantık hatası vardı:

### Önceki Davranış (HATALI):
```python
def _calc_period(days: int):
    target_date = today_date - timedelta(days=days)
    sub = df[df["Tarih"] >= target_date]
    if sub.empty:
        # SORUN BURASI: Yeterli veri yoksa ilk kaydı kullanıyordu!
        if not df.empty:
            start_val = float(df["Değer_TRY"].iloc[0])
            diff = today_val - start_val
            # ...
            return diff, pct, spark  # HER ÜÇ METRİK AYNI DEĞERİ DÖNDÜRÜYORDU!
```

**Ne oluyordu?**
- Eğer tarihsel veri 30 günden azsa (örneğin sadece 5 gün)
- Fonksiyon **her üç zaman dilimi için de (haftalık, aylık, YTD)** ilk kaydı (5 gün öncesini) başlangıç noktası olarak kullanıyordu
- Bu yüzden her üç metrik de aynı başlangıç noktasından hesaplanıyordu
- Sonuç: **Her üç metrik de aynı değeri gösteriyordu!**

## ✅ Çözüm

### 1. Veri Yeterliliği Kontrolü Eklendi

```python
def _calc_period(days: int):
    target_date = today_date - timedelta(days=days)
    sub = df[df["Tarih"] >= target_date]
    if sub.empty:
        # YENİ: Yetersiz veri durumunda None döndür
        return None, None, []
    
    # En az 2 gün veri olmalı
    if len(sub) < 2:
        return None, None, []
    
    # Hedef tarihten çok farklı bir başlangıç varsa yetersiz veri
    oldest_date = sub["Tarih"].min()
    if (oldest_date - target_date).days > days * 0.3:
        return None, None, []
    
    # Normal hesaplama
    start_val = float(sub["Değer_TRY"].iloc[0])
    diff = today_val - start_val
    pct = (diff / start_val * 100) if start_val > 0 else 0.0
    spark = list(sub["Değer_TRY"])
    return diff, pct, spark
```

**Yeni Davranış:**
- Veri yetersizse `None` döndürür
- Her metrik bağımsız kontrol edilir
- Haftalık için yeterli veri varsa gösterilir, yoksa "⚠️ Yetersiz Veri" uyarısı verilir

### 2. UI'da Akıllı Gösterim

```python
# Haftalık
if weekly_data is not None:
    w_val, w_pct = weekly_data
    weekly_txt = f"{sym}{w_val:,.0f} ({w_pct:+.2f}%)"
else:
    weekly_txt = "⚠️ Yetersiz Veri"
    w_pct = 0
```

### 3. Veri Durumu Uyarısı

Eğer 30 günden az veri varsa, ekranın üstünde şu uyarı gösterilir:

```
⚠️ Tarihsel Veri Uyarısı: Sadece X günlük veri var (tarih - tarih). 
Doğru haftalık/aylık performans için en az 30 gün veri gerekiyor. 
Uygulamanın her gün çalışmasıyla veri birikecek.
```

### 4. Debug Fonksiyonu Eklendi

`get_history_summary()` fonksiyonu ile tarihsel veri durumu kontrol edilebilir:

```python
from data_loader import get_history_summary

summary = get_history_summary()
print(summary["message"])
# Örnek çıktı: "15 kayıt, 15 günlük veri (2025-11-12 - 2025-11-27) ⚠️ Aylık performans için yetersiz."
```

## 📊 Yeni Özellikler

1. **Veri Yeterliliği Göstergesi**: Her metrik için ayrı ayrı veri kontrolü
2. **Akıllı Uyarılar**: Yetersiz veri durumunda açıklayıcı mesajlar
3. **Veri Durumu Paneli**: Kaç günlük veri olduğunu gösteren bilgi kutusu
4. **Debug Aracı**: Tarihsel veriyi incelemek için `get_history_summary()` fonksiyonu

## 🎯 Sonuç

Artık:
- ✅ Her metrik **bağımsız** hesaplanır
- ✅ Yetersiz veri durumunda **açık uyarı** verilir
- ✅ Kullanıcı **veri durumunu** görebilir
- ✅ **Yanıltıcı değerler** gösterilmez

## 🔧 Gelecek Güncellemeler İçin

- Uygulamanın **her gün çalışması** ve `write_portfolio_history()` fonksiyonunun düzenli çağrılması gerekiyor
- En az **30 gün** veri biriktikten sonra tüm metrikler doğru şekilde çalışacak
- Google Sheets'teki `portfolio_history` tablosu düzenli güncellenmeli

## 📝 Değiştirilen Dosyalar

1. `data_loader.py`:
   - `get_timeframe_changes()` fonksiyonu düzeltildi
   - `get_history_summary()` fonksiyonu eklendi

2. `portfoy.py`:
   - `render_kral_infobar()` fonksiyonu güncellendi
   - Veri durumu uyarı paneli eklendi
   - `get_history_summary` import edildi
