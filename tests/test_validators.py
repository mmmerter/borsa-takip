"""
Validator Tests
Validators modülü için unit testler.
"""

import unittest
from exceptions import ValidationError
from validators import (
    validate_price,
    validate_quantity,
    validate_profile_name,
    validate_market,
    validate_code,
    validate_date_string,
    validate_portfolio_row,
)


class TestValidators(unittest.TestCase):
    """Validator fonksiyonları için testler."""
    
    def test_validate_price_valid(self):
        """Geçerli fiyat değerleri."""
        self.assertEqual(validate_price(10.5), 10.5)
        self.assertEqual(validate_price("10.5"), 10.5)
        self.assertEqual(validate_price(0.01), 0.01)
        self.assertEqual(validate_price(99.99), 99.99)
    
    def test_validate_price_invalid(self):
        """Geçersiz fiyat değerleri."""
        with self.assertRaises(ValidationError):
            validate_price("invalid")
        
        with self.assertRaises(ValidationError):
            validate_price(None)
        
        with self.assertRaises(ValidationError):
            validate_price(-1)
        
        with self.assertRaises(ValidationError):
            validate_price(200)  # Max değerin üzerinde
    
    def test_validate_quantity_valid(self):
        """Geçerli miktar değerleri."""
        self.assertEqual(validate_quantity(10), 10.0)
        self.assertEqual(validate_quantity("5.5"), 5.5)
        self.assertEqual(validate_quantity(0), 0.0)
    
    def test_validate_quantity_invalid(self):
        """Geçersiz miktar değerleri."""
        with self.assertRaises(ValidationError):
            validate_quantity("invalid")
        
        with self.assertRaises(ValidationError):
            validate_quantity(-1, min_qty=0)
    
    def test_validate_profile_name_valid(self):
        """Geçerli profil adları."""
        self.assertEqual(validate_profile_name("MERT"), "MERT")
        self.assertEqual(validate_profile_name("mert"), "MERT")
        self.assertEqual(validate_profile_name("  MERT  "), "MERT")
    
    def test_validate_profile_name_invalid(self):
        """Geçersiz profil adları."""
        with self.assertRaises(ValidationError):
            validate_profile_name("")
        
        with self.assertRaises(ValidationError):
            validate_profile_name(None)
        
        with self.assertRaises(ValidationError):
            validate_profile_name("INVALID", allowed_profiles=["MERT", "ANNEM"])
    
    def test_validate_market_valid(self):
        """Geçerli pazar adları."""
        self.assertEqual(validate_market("BIST"), "BIST")
        self.assertEqual(validate_market("bist"), "BIST")
    
    def test_validate_code_valid(self):
        """Geçerli kodlar."""
        self.assertEqual(validate_code("THYAO"), "THYAO")
        self.assertEqual(validate_code("  thyao  "), "THYAO")
    
    def test_validate_code_invalid(self):
        """Geçersiz kodlar."""
        with self.assertRaises(ValidationError):
            validate_code("")
        
        with self.assertRaises(ValidationError):
            validate_code("A" * 30)  # Çok uzun
    
    def test_validate_date_string_valid(self):
        """Geçerli tarih string'leri."""
        self.assertEqual(validate_date_string("2024-01-01"), "2024-01-01")
        self.assertEqual(validate_date_string("2024-12-31"), "2024-12-31")
    
    def test_validate_date_string_invalid(self):
        """Geçersiz tarih string'leri."""
        with self.assertRaises(ValidationError):
            validate_date_string("invalid-date")
        
        with self.assertRaises(ValidationError):
            validate_date_string("01/01/2024")  # Yanlış format
    
    def test_validate_portfolio_row_valid(self):
        """Geçerli portföy satırı."""
        row = {
            "Kod": "THYAO",
            "Pazar": "BIST",
            "Adet": 100,
            "Maliyet": 50.5,
            "Tip": "Portfoy",
            "Notlar": "Test notu"
        }
        validated = validate_portfolio_row(row)
        self.assertEqual(validated["Kod"], "THYAO")
        self.assertEqual(validated["Adet"], 100.0)
        self.assertEqual(validated["Maliyet"], 50.5)
    
    def test_validate_portfolio_row_invalid(self):
        """Geçersiz portföy satırı."""
        # Eksik alan
        with self.assertRaises(ValidationError):
            validate_portfolio_row({"Kod": "THYAO"})
        
        # Geçersiz fiyat
        with self.assertRaises(ValidationError):
            validate_portfolio_row({
                "Kod": "THYAO",
                "Pazar": "BIST",
                "Adet": 100,
                "Maliyet": "invalid"
            })


if __name__ == "__main__":
    unittest.main()
