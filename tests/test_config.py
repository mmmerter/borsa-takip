"""
Config Tests
Config modülü için unit testler.
"""

import unittest
from config import ConfigManager, get_config


class TestConfig(unittest.TestCase):
    """Config yönetimi için testler."""
    
    def test_config_initialization(self):
        """Config başlatma testi."""
        config = ConfigManager()
        self.assertIsNotNone(config.app)
        self.assertIsNotNone(config.market)
        self.assertIsNotNone(config.color)
        self.assertIsNotNone(config.analysis)
    
    def test_app_config_defaults(self):
        """App config varsayılan değerleri."""
        config = ConfigManager()
        self.assertEqual(config.app.page_title, "Merter'in Terminali")
        self.assertEqual(config.app.page_icon, "🏦")
        self.assertEqual(config.app.socket_timeout, 15)
    
    def test_market_config_defaults(self):
        """Market config varsayılan değerleri."""
        config = ConfigManager()
        self.assertGreater(len(config.market.known_funds), 0)
        self.assertIn("BIST (Tümü)", config.market.market_data)
    
    def test_config_get_set(self):
        """Config get/set işlemleri."""
        config = ConfigManager()
        
        # Get
        value = config.get("app", "page_title")
        self.assertEqual(value, "Merter'in Terminali")
        
        # Set
        config.set("app", "page_title", "Test Title")
        value = config.get("app", "page_title")
        self.assertEqual(value, "Test Title")
        
        # Restore
        config.set("app", "page_title", "Merter'in Terminali")
    
    def test_config_to_dict(self):
        """Config dictionary dönüşümü."""
        config = ConfigManager()
        config_dict = config.to_dict()
        
        self.assertIn("app", config_dict)
        self.assertIn("market", config_dict)
        self.assertIn("color", config_dict)
        self.assertIn("analysis", config_dict)
    
    def test_get_config_singleton(self):
        """Global config singleton testi."""
        config1 = get_config()
        config2 = get_config()
        self.assertIs(config1, config2)


if __name__ == "__main__":
    unittest.main()
