# ANNEM Profili Veri Düzeltme Kılavuzu

## Sorun
ANNEM profilinin Google Sheets verileri ana profil (MERT) ile karışmış. ANNEM'in verileri kaybolmuş ve yerine MERT'in verileri görünüyor.

## Çözüm Yöntemleri

### Yöntem 1: Otomatik Kontrol ve Düzeltme Scripti

1. Script'i çalıştırın:
```bash
python fix_annem_profile.py
```

Bu script:
- MERT ve ANNEM profillerinin verilerini kontrol eder
- Google Sheets yapısını inceler
- Sorun varsa düzeltme önerileri sunar
- İsterseniz ANNEM sheet'ini temizleyebilir

### Yöntem 2: Google Sheets Versiyon Geçmişinden Geri Yükleme (ÖNERİLEN)

Eğer Google Sheets'te versiyon geçmişi varsa, bu en güvenli yöntemdir:

1. Google Sheets'te `PortfoyData` dosyasını açın
2. **File > Version history > See version history** seçeneğine gidin
3. ANNEM'in doğru verilerinin olduğu bir önceki versiyonu bulun
4. O versiyonu seçin ve **Restore this version** butonuna tıklayın
5. Sadece `annem` sheet'ini geri yüklemek istiyorsanız:
   - O versiyondaki `annem` sheet'ini kopyalayın
   - Şu anki versiyona yapıştırın

### Yöntem 3: Manuel Düzeltme

1. Google Sheets'te `PortfoyData` dosyasını açın
2. `annem` sheet'ine gidin
3. Tüm verileri seçin ve silin (başlık satırını koruyun)
4. ANNEM'in doğru verilerini manuel olarak ekleyin

### Yöntem 4: Yedekten Geri Yükleme

Eğer daha önce bir yedek aldıysanız:

1. Yedek dosyayı açın
2. `annem` sheet'ini kopyalayın
3. Ana `PortfoyData` dosyasındaki `annem` sheet'ine yapıştırın

## Önleme

Bu sorunun tekrar olmaması için:

1. **Profil değiştirirken dikkatli olun**: Her zaman hangi profilde olduğunuzu kontrol edin
2. **Düzenli yedek alın**: Google Sheets'te File > Make a copy ile düzenli yedek alın
3. **Versiyon geçmişini kullanın**: Google Sheets otomatik olarak versiyon geçmişi tutar

## Kontrol

Düzeltmeden sonra kontrol etmek için:

1. Uygulamada ANNEM profilini seçin
2. Verilerin doğru olduğundan emin olun
3. MERT profilini seçin ve verilerin değişmediğinden emin olun

## Teknik Detaylar

- MERT profili: `sheet1` (ana sayfa)
- ANNEM profili: `annem` sheet'i
- Her profil kendi sheet'inde saklanır
- Profiller arası veri karışması genellikle yanlış sheet'e yazma işleminden kaynaklanır

## Destek

Sorun devam ederse:
1. `fix_annem_profile.py` script'ini çalıştırıp çıktıyı kontrol edin
2. Google Sheets'teki sheet isimlerini kontrol edin
3. Servis hesabı izinlerini kontrol edin
