# Katkıda Bulunma Rehberi

Merter'in Terminali projesine katkıda bulunmak için bu rehberi takip edin.

## 🚀 Başlangıç

1. **Repository'yi fork edin**
2. **Local clone oluşturun**
```bash
git clone https://github.com/your-username/portfoy.git
cd portfoy
```

3. **Development environment kurun**
```bash
make install-dev
make setup
```

## 📝 Geliştirme Süreci

### 1. Branch Oluşturma

```bash
git checkout -b feature/amazing-feature
# veya
git checkout -b fix/bug-description
```

### 2. Kod Yazma

- **Type hints kullanın**: Tüm fonksiyonlara type annotations ekleyin
- **Docstring yazın**: Google style docstring kullanın
- **Test yazın**: Yeni özellikler için test ekleyin
- **Logging kullanın**: `logger.py` modülünden logger kullanın

### 3. Kod Kalitesi

```bash
# Format kontrolü
make format-check

# Linting
make lint

# Testler
make test
```

### 4. Commit Mesajları

Açıklayıcı commit mesajları yazın:

```
feat: Yeni özellik eklendi
fix: Bug düzeltildi
docs: Dokümantasyon güncellendi
test: Test eklendi
refactor: Kod refaktör edildi
style: Formatting değişiklikleri
```

### 5. Pull Request

- PR açmadan önce tüm testlerin geçtiğinden emin olun
- PR açıklamasında değişiklikleri detaylı açıklayın
- İlgili issue numarasını belirtin (varsa)

## 🧪 Test Yazma

### Unit Testler

```python
# tests/test_my_module.py
import unittest
from my_module import my_function

class TestMyModule(unittest.TestCase):
    def test_my_function_valid(self):
        result = my_function("valid_input")
        self.assertEqual(result, expected_value)
    
    def test_my_function_invalid(self):
        with self.assertRaises(ValidationError):
            my_function("invalid_input")
```

### Test Çalıştırma

```bash
# Tüm testler
make test

# Belirli test dosyası
pytest tests/test_validators.py

# Coverage ile
pytest --cov=. --cov-report=html
```

## 📚 Kod Standartları

### Python Style Guide

- **PEP 8** standartlarına uyun
- **Black** formatter kullanın (100 karakter satır uzunluğu)
- **Type hints** kullanın
- **Docstrings** yazın (Google style)

### Örnek Kod

```python
from typing import Optional, List
from logger import get_logger
from exceptions import ValidationError

logger = get_logger()

def my_function(
    param1: str,
    param2: Optional[int] = None
) -> List[str]:
    """
    Fonksiyon açıklaması.
    
    Args:
        param1: İlk parametre açıklaması
        param2: İkinci parametre açıklaması (opsiyonel)
    
    Returns:
        Sonuç listesi
    
    Raises:
        ValidationError: Geçersiz parametre durumunda
    
    Example:
        >>> result = my_function("test", 10)
        >>> print(result)
        ['test']
    """
    logger.info(f"my_function çağrıldı: param1={param1}, param2={param2}")
    
    if not param1:
        raise ValidationError("param1 boş olamaz", field="param1")
    
    return [param1]
```

## 🐛 Bug Raporlama

Bug raporu açarken şunları ekleyin:

1. **Açıklama**: Ne oldu?
2. **Beklenen**: Ne olması gerekiyordu?
3. **Adımlar**: Nasıl tekrarlanır?
4. **Loglar**: İlgili log dosyaları
5. **Versiyon**: Python ve uygulama versiyonu

## 💡 Özellik Önerileri

Özellik önerisi için:

1. Issue açın ve "enhancement" label'ı ekleyin
2. Özelliği detaylı açıklayın
3. Kullanım senaryolarını belirtin
4. UI mockup'ları ekleyin (varsa)

## 📖 Dokümantasyon

- Kod değişikliklerinde ilgili dokümantasyonu güncelleyin
- README.md'yi güncelleyin (gerekirse)
- Yeni modüller için docstring ekleyin

## ✅ Checklist

PR göndermeden önce:

- [ ] Kod formatlandı (`make format`)
- [ ] Linting geçti (`make lint`)
- [ ] Testler geçti (`make test`)
- [ ] Yeni özellikler için test eklendi
- [ ] Docstring'ler güncellendi
- [ ] README güncellendi (gerekirse)
- [ ] Commit mesajları açıklayıcı

## 🙏 Teşekkürler

Katkılarınız için teşekkürler! 🎉
