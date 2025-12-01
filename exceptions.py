"""
Custom Exception Classes
Özel exception sınıfları için modül.
"""


class PortfolioError(Exception):
    """Portföy uygulaması için base exception."""
    pass


class DataLoadError(PortfolioError):
    """Veri yükleme hatası."""
    
    def __init__(self, message: str, source: str = None, original_error: Exception = None):
        super().__init__(message)
        self.source = source
        self.original_error = original_error
    
    def __str__(self):
        msg = super().__str__()
        if self.source:
            msg = f"[{self.source}] {msg}"
        if self.original_error:
            msg = f"{msg} (Original: {type(self.original_error).__name__}: {self.original_error})"
        return msg


class GoogleSheetsError(DataLoadError):
    """Google Sheets bağlantı/veri hatası."""
    pass


class TEFASError(DataLoadError):
    """TEFAS API hatası."""
    pass


class YahooFinanceError(DataLoadError):
    """Yahoo Finance API hatası."""
    pass


class ProfileError(PortfolioError):
    """Profil yönetimi hatası."""
    pass


class ProfileNotFoundError(ProfileError):
    """Profil bulunamadı hatası."""
    
    def __init__(self, profile_name: str):
        super().__init__(f"Profil bulunamadı: {profile_name}")
        self.profile_name = profile_name


class InvalidProfileError(ProfileError):
    """Geçersiz profil hatası."""
    
    def __init__(self, profile_name: str, reason: str = None):
        msg = f"Geçersiz profil: {profile_name}"
        if reason:
            msg = f"{msg} - {reason}"
        super().__init__(msg)
        self.profile_name = profile_name
        self.reason = reason


class ConfigurationError(PortfolioError):
    """Yapılandırma hatası."""
    pass


class ValidationError(PortfolioError):
    """Veri doğrulama hatası."""
    
    def __init__(self, message: str, field: str = None, value: any = None):
        super().__init__(message)
        self.field = field
        self.value = value
    
    def __str__(self):
        msg = super().__str__()
        if self.field:
            msg = f"Field '{self.field}': {msg}"
        if self.value is not None:
            msg = f"{msg} (Value: {self.value})"
        return msg


class CacheError(PortfolioError):
    """Cache işlemi hatası."""
    pass


class NetworkError(PortfolioError):
    """Ağ bağlantı hatası."""
    
    def __init__(self, message: str, url: str = None, status_code: int = None):
        super().__init__(message)
        self.url = url
        self.status_code = status_code
    
    def __str__(self):
        msg = super().__str__()
        if self.url:
            msg = f"{msg} (URL: {self.url})"
        if self.status_code:
            msg = f"{msg} (Status: {self.status_code})"
        return msg
