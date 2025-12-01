"""
Helper Functions Module
Tekrarlanan kodları azaltmak için yardımcı fonksiyonlar.
"""

from typing import Any, Optional, Callable, TypeVar, Tuple
from functools import wraps
import pandas as pd
from exceptions import DataLoadError, NetworkError, ValidationError
from logger import get_logger

logger = get_logger()
T = TypeVar('T')


def safe_execute(
    func: Callable[[], T],
    default: T = None,
    error_message: str = "İşlem başarısız",
    log_error: bool = True,
    raise_error: bool = False
) -> Optional[T]:
    """
    Güvenli fonksiyon çalıştırma - tekrarlanan try-except bloklarını azaltır.
    
    Args:
        func: Çalıştırılacak fonksiyon
        default: Hata durumunda döndürülecek varsayılan değer
        error_message: Hata mesajı
        log_error: Hata loglanacak mı?
        raise_error: Hata fırlatılacak mı?
    
    Returns:
        Fonksiyon sonucu veya default değer
    
    Example:
        result = safe_execute(
            lambda: risky_function(),
            default=0,
            error_message="Fonksiyon başarısız"
        )
    """
    try:
        return func()
    except Exception as e:
        if log_error:
            logger.error(f"{error_message}: {e}", exc_info=True)
        
        if raise_error:
            raise
        
        return default


def safe_api_call(
    func: Callable[[], T],
    default: T = None,
    source: str = "API",
    timeout: int = 15
) -> Optional[T]:
    """
    API çağrıları için güvenli wrapper - NetworkError handling.
    
    Args:
        func: API çağrısı yapan fonksiyon
        default: Hata durumunda varsayılan değer
        source: API kaynağı (hata mesajı için)
        timeout: Timeout süresi (saniye)
    
    Returns:
        API sonucu veya default değer
    """
    try:
        return func()
    except Exception as e:
        logger.warning(f"{source} çağrısı başarısız: {e}")
        return default


def safe_dataframe_operation(
    df: pd.DataFrame,
    operation: Callable[[pd.DataFrame], pd.DataFrame],
    default: pd.DataFrame = None
) -> pd.DataFrame:
    """
    DataFrame işlemleri için güvenli wrapper.
    
    Args:
        df: İşlenecek DataFrame
        operation: Uygulanacak işlem
        default: Hata durumunda varsayılan DataFrame
    
    Returns:
        İşlenmiş DataFrame veya default
    """
    if df is None or df.empty:
        return default if default is not None else pd.DataFrame()
    
    try:
        return operation(df)
    except Exception as e:
        logger.error(f"DataFrame işlemi başarısız: {e}")
        return default if default is not None else pd.DataFrame()


def retry_on_failure(
    max_retries: int = 3,
    delay: float = 1.0,
    exceptions: tuple = (Exception,)
):
    """
    Retry decorator - başarısız işlemleri tekrar dener.
    
    Args:
        max_retries: Maksimum deneme sayısı
        delay: Denemeler arası bekleme süresi (saniye)
        exceptions: Yakalanacak exception tipleri
    
    Example:
        @retry_on_failure(max_retries=3, delay=1.0)
        def fetch_data():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        import time
                        logger.warning(
                            f"{func.__name__} başarısız (deneme {attempt + 1}/{max_retries}): {e}"
                        )
                        time.sleep(delay)
                    else:
                        logger.error(f"{func.__name__} tüm denemeler başarısız: {e}")
            
            raise last_exception
        
        return wrapper
    return decorator


def normalize_string(value: Any, default: str = "") -> str:
    """
    String normalizasyonu - tekrarlanan kodları azaltır.
    
    Args:
        value: Normalize edilecek değer
        default: Varsayılan değer
    
    Returns:
        Normalize edilmiş string
    """
    if value is None:
        return default
    
    try:
        return str(value).strip()
    except Exception:
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    """
    Güvenli float dönüşümü.
    
    Args:
        value: Dönüştürülecek değer
        default: Hata durumunda varsayılan değer
    
    Returns:
        Float değer veya default
    """
    if value is None:
        return default
    
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    """
    Güvenli int dönüşümü.
    
    Args:
        value: Dönüştürülecek değer
        default: Hata durumunda varsayılan değer
    
    Returns:
        Int değer veya default
    """
    if value is None:
        return default
    
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def format_currency(
    value: float,
    currency: str = "TRY",
    decimals: int = 2
) -> str:
    """
    Para birimi formatlama - tekrarlanan format kodlarını azaltır.
    
    Args:
        value: Formatlanacak değer
        currency: Para birimi (TRY, USD, EUR)
        decimals: Ondalık basamak sayısı
    
    Returns:
        Formatlanmış string
    """
    symbols = {
        "TRY": "₺",
        "USD": "$",
        "EUR": "€"
    }
    
    symbol = symbols.get(currency, currency)
    
    if abs(value) >= 1000000:
        return f"{symbol}{value/1000000:.{decimals}f}M"
    elif abs(value) >= 1000:
        return f"{symbol}{value/1000:.{decimals}f}K"
    else:
        return f"{symbol}{value:,.{decimals}f}"


def format_percentage(value: float, decimals: int = 2) -> str:
    """
    Yüzde formatlama.
    
    Args:
        value: Formatlanacak değer (0.05 = %5)
        decimals: Ondalık basamak sayısı
    
    Returns:
        Formatlanmış yüzde string
    """
    return f"{value * 100:+.{decimals}f}%"


def get_pnl_color(value: float) -> Tuple[str, str]:
    """
    Kâr/Zarar rengi döndürür - tekrarlanan renk kodlarını azaltır.
    
    Args:
        value: Kâr/Zarar değeri
    
    Returns:
        (renk, ok) tuple'ı
    """
    if value > 0:
        return ("#00e676", "▲")  # Yeşil, yukarı ok
    elif value < 0:
        return ("#ff5252", "▼")  # Kırmızı, aşağı ok
    else:
        return ("#9da1b3", "─")  # Gri, çizgi


def chunk_list(lst: list, chunk_size: int) -> list:
    """
    Listeyi küçük parçalara böler - batch işlemler için.
    
    Args:
        lst: Bölünecek liste
        chunk_size: Parça boyutu
    
    Returns:
        Parçalara bölünmüş liste listesi
    """
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def merge_dataframes(dfs: list, how: str = "outer") -> pd.DataFrame:
    """
    Birden fazla DataFrame'i birleştirir.
    
    Args:
        dfs: Birleştirilecek DataFrame listesi
        how: Birleştirme yöntemi (outer, inner, left, right)
    
    Returns:
        Birleştirilmiş DataFrame
    """
    if not dfs:
        return pd.DataFrame()
    
    if len(dfs) == 1:
        return dfs[0]
    
    result = dfs[0]
    for df in dfs[1:]:
        if not df.empty:
            result = pd.merge(result, df, how=how)
    
    return result
