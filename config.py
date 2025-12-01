"""
Configuration Management Module
Merkezi yapılandırma yönetimi için modül.
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class AppConfig:
    """Uygulama genel ayarları."""
    page_title: str = "Merter'in Terminali"
    page_icon: str = "🏦"
    layout: str = "wide"
    initial_sidebar_state: str = "collapsed"
    
    # Theme ayarları
    theme_base: str = "dark"
    theme_primary_color: str = "#6b7fd7"
    theme_secondary_bg: str = "#1a1c24"
    theme_bg: str = "#0e1117"
    theme_text: str = "#ffffff"
    
    # Google Sheets ayarları
    sheet_name: str = "PortfoyData"
    daily_base_sheet_name: str = "daily_base_prices"
    
    # Cache ayarları (saniye cinsinden)
    cache_ttl_sheet_data: int = 120  # 2 dakika
    cache_ttl_sales_history: int = 180  # 3 dakika
    cache_ttl_tefas: int = 7200  # 2 saat
    cache_ttl_tickers: int = 60  # 1 dakika
    cache_ttl_crypto: int = 300  # 5 dakika
    cache_ttl_news: int = 300  # 5 dakika
    
    # Network ayarları
    socket_timeout: int = 15  # saniye
    
    # TEFAS API ayarları
    tefas_api_url: str = "https://www.tefas.gov.tr/api/DB/BindHistoryInfo"
    tefas_timeout: int = 15
    
    # Yahoo Finance ayarları
    yahoo_period_default: str = "5d"
    yahoo_period_fallback: str = "1mo"
    
    # CoinGecko API ayarları
    coingecko_api_url: str = "https://api.coingecko.com/api/v3/global"
    coingecko_timeout: int = 5
    
    # Günlük baz fiyat reset saati (Türkiye saati)
    daily_reset_hour: int = 0
    daily_reset_minute: int = 30
    
    # Profil ayarları
    default_profile: str = "MERT"
    
    # UI ayarları
    ticker_refresh_interval: int = 30  # saniye
    max_news_items: int = 30
    max_portfolio_news_per_asset: int = 5
    max_watchlist_news_per_asset: int = 3


@dataclass
class MarketConfig:
    """Piyasa ve sembol ayarları."""
    # Bilinen fon kodları
    known_funds: list = field(default_factory=lambda: [
        "YHB", "TTE", "MAC", "AFT", "AFA", "YAY", "IPJ", "TCD", "NNF",
        "GMR", "TI2", "TI3", "IHK", "IDH", "OJT", "HKH", "IPB", "KZL",
        "RPD", "URA"
    ])
    
    # Pazar verileri
    market_data: Dict[str, list] = field(default_factory=lambda: {
        "BIST (Tümü)": ["THYAO", "GARAN", "ASELS", "TRMET"],
        "ABD": ["AAPL", "TSLA"],
        "KRIPTO": ["BTC", "ETH"],
        "FON": ["YHB", "TTE", "MAC", "AFT", "AFA", "YAY", "IPJ", "TCD", "NNF",
                "GMR", "TI2", "TI3", "IHK", "IDH", "OJT", "HKH", "IPB", "KZL",
                "RPD", "URA"],
        "EMTIA": ["Gram Altın", "22 Ayar Gram Altın", "Gram Gümüş"],
        "VADELI": ["BTC", "ETH", "SOL"],
        "NAKIT": ["TL", "USD", "EUR"],
    })
    
    # Emtia sembol eşleştirmeleri
    emtia_symbol_map: Dict[str, str] = field(default_factory=lambda: {
        "Altın ONS": "GC=F",
        "Gümüş ONS": "SI=F",
        "Petrol": "BZ=F",
        "Doğalgaz": "NG=F",
        "Bakır": "HG=F",
    })
    
    # Market sembolleri (ticker için)
    market_symbols: list = field(default_factory=lambda: [
        ("BIST 100", "XU100.IS"),
        ("USD", "TRY=X"),
        ("EUR", "EURTRY=X"),
        ("BTC/USDT", "BTC-USD"),
        ("ETH/USDT", "ETH-USD"),
        ("Ons Altın", "GC=F"),
        ("Ons Gümüş", "SI=F"),
        ("NASDAQ", "^IXIC"),
        ("S&P 500", "^GSPC"),
    ])


@dataclass
class ColorConfig:
    """Renk ve tema ayarları."""
    # Standart renkler
    profit_color: str = "#00e676"  # Yeşil
    loss_color: str = "#ff5252"  # Kırmızı
    neutral_color: str = "#9da1b3"  # Gri
    
    # Profil renkleri
    profile_colors: Dict[str, str] = field(default_factory=lambda: {
        "MERT": "#6b7fd7",
        "ANNEM": "#ec4899",
        "BERGUZAR": "#ec4899",
        "İKRAMİYE": "#10b981",
        "TOTAL": "#f59e0b",
    })
    
    # Chart renkleri
    chart_colors_standard: list = field(default_factory=lambda: [
        "#6366f1", "#8b5cf6", "#ec4899", "#f59e0b", "#10b981",
        "#3b82f6", "#f97316", "#06b6d4", "#84cc16", "#ef4444",
    ])
    
    chart_colors_berguzar: list = field(default_factory=lambda: [
        "#ec4899", "#f472b6", "#ff69b4", "#d946ef", "#fb7185",
        "#f9a8d4", "#db2777", "#fbbf24", "#be185d", "#ff1493",
    ])


@dataclass
class AnalysisConfig:
    """Analiz ve hesaplama ayarları."""
    # Analiz kolonları
    analysis_columns: list = field(default_factory=lambda: [
        "Kod", "Pazar", "Tip", "Adet", "Maliyet", "Fiyat", "PB",
        "Yatırılan", "Değer", "Top. Kâr/Zarar", "Top. %",
        "Gün. Kâr/Zarar", "Notlar",
    ])
    
    # Fiyat aralıkları (makul kontrol için)
    min_price: float = 0.01
    max_price: float = 100.0  # TEFAS fonları için
    
    # Günlük hareket edenler
    daily_movers_top_n: int = 5
    
    # Performans metrikleri
    performance_periods: Dict[str, int] = field(default_factory=lambda: {
        "weekly": 7,
        "monthly": 30,
        "ytd": None,  # Yıl başından bugüne
    })


class ConfigManager:
    """Yapılandırma yöneticisi."""
    
    def __init__(self):
        self.app = AppConfig()
        self.market = MarketConfig()
        self.color = ColorConfig()
        self.analysis = AnalysisConfig()
        self._env_overrides: Dict[str, Any] = {}
        self._load_env_overrides()
    
    def _load_env_overrides(self):
        """Ortam değişkenlerinden override'ları yükle."""
        # Örnek: SOCKET_TIMEOUT gibi env var'ları okuyabilir
        if timeout := os.getenv("SOCKET_TIMEOUT"):
            try:
                self.app.socket_timeout = int(timeout)
            except ValueError:
                pass
    
    def get(self, section: str, key: str, default: Any = None) -> Any:
        """Yapılandırma değeri al."""
        try:
            section_obj = getattr(self, section)
            return getattr(section_obj, key, default)
        except AttributeError:
            return default
    
    def set(self, section: str, key: str, value: Any):
        """Yapılandırma değeri ayarla."""
        try:
            section_obj = getattr(self, section)
            setattr(section_obj, key, value)
        except AttributeError:
            raise ValueError(f"Unknown section: {section}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Tüm yapılandırmayı dictionary olarak döndür."""
        return {
            "app": self.app.__dict__,
            "market": self.market.__dict__,
            "color": self.color.__dict__,
            "analysis": self.analysis.__dict__,
        }


# Global config instance
config = ConfigManager()


def get_config() -> ConfigManager:
    """Global config instance'ı döndür."""
    return config
