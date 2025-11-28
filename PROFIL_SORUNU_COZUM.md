# 🔧 Profil Sistemi Sorunu ve Çözümü

## 📋 Sorun Özeti

**Bergüzar** ve **Annem** profillerinde Google Sheets verisine ulaşılamıyor.

## 🔍 Sorunun Nedeni

Profil sistemi, her profil için Google Sheets'te **ayrı worksheet'ler** kullanıyor. `data_loader_profiles.py` dosyasında şu worksheet isimleri **hardcoded** olarak tanımlanmış:

```python
# data_loader_profiles.py - Satır 56-69
if profile_name == "MERT":
    worksheet = spreadsheet.sheet1  # Ana sayfa
elif profile_name == "ANNEM":
    worksheet = spreadsheet.worksheet("annem")  # ❌ Bu worksheet yoksa hata!
elif profile_name == "BERGUZAR":
    worksheet = spreadsheet.worksheet("berguzar")  # ❌ Bu worksheet yoksa hata!
elif profile_name == "TOTAL":
    worksheet = spreadsheet.worksheet("total")
```

### ⚠️ Sorun:
Google Sheets'te **"annem"** ve **"berguzar"** worksheet'leri **YOK** veya **farklı isimlerle** mevcut!

---

## ✅ Çözüm Adımları

### 🎯 Çözüm 1: Google Sheets'te Worksheet'leri Oluşturun (ÖNERİLEN)

1. **Google Sheets'te PortfoyData spreadsheet'ini açın**
   - Tarayıcınızda Google Sheets'e gidin
   - "PortfoyData" isimli spreadsheet'i açın

2. **Yeni worksheet'ler oluşturun** (küçük harflerle!):
   
   #### a) "annem" worksheet'i:
   - Sol alttaki **+** butonuna tıklayın veya mevcut bir sekmeye sağ tıklayın
   - "Insert sheet" seçin
   - İsim: **`annem`** (küçük harf, tam olarak böyle)
   - İlk satıra şu başlıkları ekleyin:
     ```
     Kod | Pazar | Adet | Maliyet | Tip | Notlar
     ```
   
   #### b) "berguzar" worksheet'i:
   - Aynı şekilde yeni bir worksheet oluşturun
   - İsim: **`berguzar`** (küçük harf, ü değil u!)
   - İlk satıra aynı başlıkları ekleyin:
     ```
     Kod | Pazar | Adet | Maliyet | Tip | Notlar
     ```
   
   #### c) "total" worksheet'i (opsiyonel):
   - Total profili otomatik hesaplanır ama görsel amaçlı oluşturabilirsiniz
   - İsim: **`total`** (küçük harf)
   - Aynı başlıkları ekleyin

3. **Uygulamayı yeniden başlatın**
   ```bash
   streamlit run portfoy.py
   ```

---

### 🛠️ Çözüm 2: Otomatik Kurulum Scripti Kullanın

Eğer terminal erişiminiz varsa, hazır scripti çalıştırın:

```bash
cd /workspace
streamlit run setup_profiles_existing.py
```

Bu script:
- ✅ Mevcut worksheet'leri kontrol eder
- ✅ Eksik olanları otomatik oluşturur
- ✅ Gerekli başlıkları ekler
- ✅ Tarihçe worksheet'lerini de oluşturabilir

---

### 🔧 Çözüm 3: Kod Seviyesinde Düzeltme

Eğer worksheet isimleriniz farklıysa (örn. "Annem", "Bergüzar" gibi büyük harfle), kodu düzenleyebilirsiniz:

**`data_loader_profiles.py` dosyasını düzenleyin (satır 56-69):**

```python
# ÖNCEKİ (Hardcoded):
elif profile_name == "ANNEM":
    worksheet = spreadsheet.worksheet("annem")  # Tam bu isim gerekli!
elif profile_name == "BERGUZAR":
    worksheet = spreadsheet.worksheet("berguzar")  # Tam bu isim gerekli!

# SONRA (Flexible):
elif profile_name == "ANNEM":
    # Farklı isimleri dene
    try:
        worksheet = spreadsheet.worksheet("annem")
    except:
        try:
            worksheet = spreadsheet.worksheet("Annem")
        except:
            worksheet = spreadsheet.worksheet("ANNEM")
elif profile_name == "BERGUZAR":
    try:
        worksheet = spreadsheet.worksheet("berguzar")
    except:
        try:
            worksheet = spreadsheet.worksheet("Berguzar")
        except:
            worksheet = spreadsheet.worksheet("Bergüzar")
```

---

## 🎯 Profil Sistemi Nasıl Çalışır?

### 📊 Profil Yapısı

Sisteminizde **4 profil** var:

| Profil | İkon | Worksheet İsmi | Açıklama |
|--------|------|----------------|-----------|
| **MERT** | 🎯 | `sheet1` (ana sayfa) | Ana profil, varsayılan |
| **ANNEM** | 👩 | `annem` | Anne portföyü |
| **BERGUZAR** | 👑 | `berguzar` | Bergüzar portföyü |
| **TOTAL** | 📊 | `total` (otomatik) | Tüm profillerin toplamı |

### 🔄 Veri İzolasyonu

- Her profil **tamamen ayrı** varlıklara sahiptir
- Bir profildeki değişiklik diğerlerini **ETKİLEMEZ**
- TOTAL profili **otomatik hesaplanır** (düzenlenemez)

### 📁 Google Sheets Yapısı

```
PortfoyData (Spreadsheet)
├── Sheet1 (ana sayfa)     ← MERT profili
├── annem                   ← ANNEM profili ⚠️ EKSIK OLABİLİR
├── berguzar                ← BERGUZAR profili ⚠️ EKSIK OLABİLİR
├── total                   ← TOTAL profili (opsiyonel)
│
├── Satislar                ← MERT satış geçmişi
├── Satislar_ANNEM          ← ANNEM satış geçmişi
├── Satislar_BERGUZAR       ← BERGUZAR satış geçmişi
│
├── portfolio_history       ← MERT tarihçesi
├── portfolio_history_ANNEM
├── portfolio_history_BERGUZAR
│
└── ... (diğer tarihçe worksheet'leri)
```

---

## 🚀 Hızlı Başlangıç Kontrolü

### 1️⃣ Worksheet'lerin Olup Olmadığını Kontrol Edin

1. Google Sheets'te PortfoyData'yı açın
2. Sol altta worksheet sekmelerine bakın
3. Şunlar olmalı:
   - ✅ Ana sayfa (veya Sheet1) - MERT için
   - ✅ annem - ANNEM için
   - ✅ berguzar - BERGUZAR için

### 2️⃣ Worksheet İsimlerini Kontrol Edin

⚠️ **Önemli:** İsimler **tam olarak** şöyle olmalı:
- ❌ Yanlış: "Annem", "ANNEM", "Anne"
- ✅ Doğru: "annem"
- ❌ Yanlış: "Bergüzar", "BERGUZAR", "Berguzar"
- ✅ Doğru: "berguzar"

### 3️⃣ Başlıkları Kontrol Edin

Her worksheet'in ilk satırında şu başlıklar olmalı:
```
Kod | Pazar | Adet | Maliyet | Tip | Notlar
```

---

## 💡 Toplam Hesaplama Sistemi

### TOTAL Profili Nasıl Çalışır?

TOTAL profili seçildiğinde sistem:

1. **MERT** profilinden veri çeker
2. **ANNEM** profilinden veri çeker
3. **BERGUZAR** profilinden veri çeker
4. Hepsini **birleştirir** ve toplam değerleri gösterir

```python
# data_loader_profiles.py - _get_aggregated_data()
def _get_aggregated_data():
    all_profiles = ["MERT", "ANNEM", "BERGUZAR"]
    aggregated_rows = []
    
    for profile_name in all_profiles:
        df = get_data_from_sheet_profile(profile_name)  # Her profilden veri çek
        if df is not None and not df.empty:
            df_copy = df.copy()
            df_copy["_profile"] = profile_name  # Profil etiketle
            aggregated_rows.append(df_copy)
    
    # Tüm verileri birleştir
    combined_df = pd.concat(aggregated_rows, ignore_index=True)
    return combined_df
```

---

## 🔍 Sorun Giderme

### Hata: "Google Sheets verisine ulaşılamadı (ANNEM profili)"

**Neden:** `annem` worksheet'i bulunamıyor

**Çözüm:**
1. Google Sheets'te "annem" worksheet'ini oluşturun (küçük harf!)
2. Başlıkları ekleyin: Kod, Pazar, Adet, Maliyet, Tip, Notlar
3. Uygulamayı yeniden başlatın

### Hata: "Google Sheets verisine ulaşılamadı (BERGUZAR profili)"

**Neden:** `berguzar` worksheet'i bulunamıyor

**Çözüm:**
1. Google Sheets'te "berguzar" worksheet'ini oluşturun (küçük harf, ü değil u!)
2. Başlıkları ekleyin
3. Uygulamayı yeniden başlatın

### MERT Profili Çalışıyor Ama Diğerleri Çalışmıyor

**Neden:** MERT profili `sheet1` (ana sayfa) kullanıyor, her zaman vardır. Diğer profiller özel worksheet'ler gerektirir.

**Çözüm:** Çözüm 1 veya 2'yi uygulayın (yukarıda)

---

## 📚 İlgili Dosyalar

| Dosya | Açıklama |
|-------|----------|
| `profile_manager.py` | Profil tanımları ve yönetimi |
| `data_loader_profiles.py` | Profil-aware veri yükleme (SORUN BURADA!) |
| `setup_profiles_existing.py` | Otomatik kurulum scripti |
| `PROFILE_SISTEMI_KILAVUZU.md` | Detaylı kullanım kılavuzu |
| `portfoy.py` | Ana uygulama |

---

## ✨ Kurulumdan Sonra

Worksheet'leri oluşturduktan sonra:

1. **Uygulamayı Başlatın:**
   ```bash
   streamlit run portfoy.py
   ```

2. **Profil Seçin:**
   - Uygulama açıldığında üstteki profil seçiciyi kullanın
   - ANNEM veya BERGUZAR profilini seçin

3. **Varlık Ekleyin:**
   - "Ekle/Çıkar" sekmesine gidin
   - İstediğiniz varlıkları ekleyin
   - Her profil için ayrı ayrı varlıklar eklenmelidir

4. **TOTAL Görüntüleyin:**
   - TOTAL profilini seçin
   - Tüm profillerin birleşik görünümünü görün

---

## 🎉 Başarı Kriterleri

Sistem düzgün çalışıyorsa:

- ✅ MERT profilinde varlıklar görünüyor
- ✅ ANNEM profiline geçiş yapılabiliyor ve veri yükleniyor
- ✅ BERGUZAR profiline geçiş yapılabiliyor ve veri yükleniyor
- ✅ TOTAL profilinde tüm profillerin verisi birleşik görünüyor
- ✅ Her profilde ayrı varlıklar eklenip düzenlenebiliyor

---

## 🆘 Hala Çalışmıyor mu?

1. **Cache'i Temizleyin:**
   - Streamlit uygulamasında Ctrl+R ile sayfayı yenileyin
   - Veya menüden "Clear cache" seçin

2. **Bağlantıyı Kontrol Edin:**
   - Google Sheets'in açık olduğundan emin olun
   - Service account erişim yetkilerini kontrol edin

3. **Log'ları İnceleyin:**
   - Terminal'de hata mesajlarına bakın
   - Google Sheets API limitlerini kontrol edin

4. **Yedek Alın:**
   - Veri eklemeden önce mevcut spreadsheet'i kopyalayın

---

**📞 Ek Yardım:** Daha fazla bilgi için `PROFILE_SISTEMI_KILAVUZU.md` dosyasına bakın.

**✅ ÖZET:** "annem" ve "berguzar" worksheet'lerini Google Sheets'te oluşturun, başlıkları ekleyin, uygulamayı yeniden başlatın!
