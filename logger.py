"""
Professional Logging Module
Profesyonel loglama sistemi için modül.
"""

import logging
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime
import streamlit as st


class StreamlitHandler(logging.Handler):
    """Streamlit ortamı için özel log handler."""
    
    def emit(self, record):
        """Log kaydını Streamlit'e yaz."""
        try:
            msg = self.format(record)
            if record.levelno >= logging.ERROR:
                st.error(f"❌ {msg}")
            elif record.levelno >= logging.WARNING:
                st.warning(f"⚠️ {msg}")
            elif record.levelno >= logging.INFO:
                st.info(f"ℹ️ {msg}")
            else:
                st.text(f"📝 {msg}")
        except Exception:
            pass  # Streamlit yoksa sessiz geç


def setup_logger(
    name: str = "portfoy",
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    use_streamlit: bool = True,
    format_string: Optional[str] = None
) -> logging.Logger:
    """
    Profesyonel logger kurulumu.
    
    Args:
        name: Logger adı
        level: Log seviyesi (logging.DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Log dosyası yolu (None ise dosyaya yazmaz)
        use_streamlit: Streamlit handler kullanılsın mı?
        format_string: Özel format string (None ise varsayılan kullanılır)
    
    Returns:
        Yapılandırılmış logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Zaten handler'lar varsa tekrar ekleme
    if logger.handlers:
        return logger
    
    # Format string
    if format_string is None:
        format_string = (
            "%(asctime)s | %(name)s | %(levelname)-8s | "
            "%(filename)s:%(lineno)d | %(message)s"
        )
    
    formatter = logging.Formatter(
        format_string,
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Console handler (her zaman)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Streamlit handler (opsiyonel)
    if use_streamlit:
        try:
            streamlit_handler = StreamlitHandler()
            streamlit_handler.setLevel(logging.WARNING)  # Sadece warning ve üzeri
            streamlit_handler.setFormatter(formatter)
            logger.addHandler(streamlit_handler)
        except Exception:
            pass  # Streamlit yoksa sessiz geç
    
    # File handler (opsiyonel)
    if log_file:
        try:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.FileHandler(log_path, encoding="utf-8")
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            logger.warning(f"Log dosyası oluşturulamadı: {e}")
    
    return logger


def get_logger(name: str = "portfoy") -> logging.Logger:
    """
    Logger instance'ı al (lazy initialization).
    
    Args:
        name: Logger adı
    
    Returns:
        Logger instance
    """
    logger = logging.getLogger(name)
    
    # Eğer handler yoksa varsayılan kurulumu yap
    if not logger.handlers:
        # Log dosyası yolu (logs/ klasöründe)
        log_dir = Path("logs")
        log_file = log_dir / f"portfoy_{datetime.now().strftime('%Y%m%d')}.log"
        
        setup_logger(
            name=name,
            level=logging.INFO,
            log_file=str(log_file),
            use_streamlit=True
        )
    
    return logger


# Context manager ile log seviyesi geçici değiştirme
class LogLevelContext:
    """Geçici log seviyesi değiştirme için context manager."""
    
    def __init__(self, logger: logging.Logger, level: int):
        self.logger = logger
        self.new_level = level
        self.old_level = None
    
    def __enter__(self):
        self.old_level = self.logger.level
        self.logger.setLevel(self.new_level)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.logger.setLevel(self.old_level)


# Decorator: Fonksiyon çağrılarını logla
def log_function_call(logger: Optional[logging.Logger] = None):
    """
    Fonksiyon çağrılarını loglayan decorator.
    
    Usage:
        @log_function_call()
        def my_function(arg1, arg2):
            ...
    """
    def decorator(func):
        nonlocal logger
        if logger is None:
            logger = get_logger()
        
        def wrapper(*args, **kwargs):
            logger.debug(f"Calling {func.__name__} with args={args}, kwargs={kwargs}")
            try:
                result = func(*args, **kwargs)
                logger.debug(f"{func.__name__} completed successfully")
                return result
            except Exception as e:
                logger.error(f"{func.__name__} failed: {e}", exc_info=True)
                raise
        
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper
    
    return decorator


# Performance logging decorator
def log_performance(logger: Optional[logging.Logger] = None, threshold_ms: float = 1000.0):
    """
    Fonksiyon performansını loglayan decorator.
    
    Args:
        logger: Logger instance (None ise varsayılan kullanılır)
        threshold_ms: Bu sürenin üzerindeki çağrıları logla (milisaniye)
    
    Usage:
        @log_performance(threshold_ms=500)
        def slow_function():
            ...
    """
    def decorator(func):
        nonlocal logger
        if logger is None:
            logger = get_logger()
        
        def wrapper(*args, **kwargs):
            import time
            start = time.time()
            try:
                result = func(*args, **kwargs)
                elapsed_ms = (time.time() - start) * 1000
                if elapsed_ms >= threshold_ms:
                    logger.warning(
                        f"{func.__name__} took {elapsed_ms:.2f}ms "
                        f"(threshold: {threshold_ms}ms)"
                    )
                else:
                    logger.debug(f"{func.__name__} took {elapsed_ms:.2f}ms")
                return result
            except Exception as e:
                elapsed_ms = (time.time() - start) * 1000
                logger.error(
                    f"{func.__name__} failed after {elapsed_ms:.2f}ms: {e}",
                    exc_info=True
                )
                raise
        
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper
    
    return decorator
