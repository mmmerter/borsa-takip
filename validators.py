"""
Data Validation Module
Veri doğrulama fonksiyonları için modül.
"""

from typing import Any, Optional, List
from exceptions import ValidationError
from config import get_config


def validate_price(price: Any, min_price: float = None, max_price: float = None) -> float:
    """
    Fiyat değerini doğrula ve float'a çevir.
    
    Args:
        price: Fiyat değeri (herhangi bir tip)
        min_price: Minimum fiyat (None ise config'den alınır)
        max_price: Maximum fiyat (None ise config'den alınır)
    
    Returns:
        Doğrulanmış float fiyat
    
    Raises:
        ValidationError: Geçersiz fiyat değeri
    """
    config = get_config()
    
    if min_price is None:
        min_price = config.analysis.min_price
    if max_price is None:
        max_price = config.analysis.max_price
    
    try:
        price_float = float(price)
    except (ValueError, TypeError):
        raise ValidationError(
            f"Geçersiz fiyat değeri: {price}",
            field="price",
            value=price
        )
    
    if price_float < min_price:
        raise ValidationError(
            f"Fiyat minimum değerin altında: {price_float} < {min_price}",
            field="price",
            value=price_float
        )
    
    if price_float > max_price:
        raise ValidationError(
            f"Fiyat maximum değerin üzerinde: {price_float} > {max_price}",
            field="price",
            value=price_float
        )
    
    return price_float


def validate_quantity(quantity: Any, min_qty: float = 0.0) -> float:
    """
    Miktar değerini doğrula ve float'a çevir.
    
    Args:
        quantity: Miktar değeri
        min_qty: Minimum miktar (varsayılan: 0.0)
    
    Returns:
        Doğrulanmış float miktar
    
    Raises:
        ValidationError: Geçersiz miktar değeri
    """
    try:
        qty_float = float(quantity)
    except (ValueError, TypeError):
        raise ValidationError(
            f"Geçersiz miktar değeri: {quantity}",
            field="quantity",
            value=quantity
        )
    
    if qty_float < min_qty:
        raise ValidationError(
            f"Miktar minimum değerin altında: {qty_float} < {min_qty}",
            field="quantity",
            value=qty_float
        )
    
    return qty_float


def validate_profile_name(profile_name: str, allowed_profiles: List[str] = None) -> str:
    """
    Profil adını doğrula.
    
    Args:
        profile_name: Profil adı
        allowed_profiles: İzin verilen profil listesi (None ise tüm profiller)
    
    Returns:
        Doğrulanmış profil adı
    
    Raises:
        ValidationError: Geçersiz profil adı
    """
    if not profile_name or not isinstance(profile_name, str):
        raise ValidationError(
            "Profil adı boş veya geçersiz tip",
            field="profile_name",
            value=profile_name
        )
    
    profile_name = profile_name.strip().upper()
    
    if allowed_profiles:
        if profile_name not in [p.upper() for p in allowed_profiles]:
            raise ValidationError(
                f"İzin verilmeyen profil: {profile_name}",
                field="profile_name",
                value=profile_name
            )
    
    return profile_name


def validate_market(market: str, allowed_markets: List[str] = None) -> str:
    """
    Pazar adını doğrula.
    
    Args:
        market: Pazar adı
        allowed_markets: İzin verilen pazar listesi
    
    Returns:
        Doğrulanmış pazar adı
    
    Raises:
        ValidationError: Geçersiz pazar adı
    """
    if not market or not isinstance(market, str):
        raise ValidationError(
            "Pazar adı boş veya geçersiz tip",
            field="market",
            value=market
        )
    
    market = market.strip().upper()
    
    if allowed_markets:
        if market not in [m.upper() for m in allowed_markets]:
            raise ValidationError(
                f"İzin verilmeyen pazar: {market}",
                field="market",
                value=market
            )
    
    return market


def validate_code(code: str, min_length: int = 1, max_length: int = 20) -> str:
    """
    Varlık kodunu doğrula.
    
    Args:
        code: Varlık kodu
        min_length: Minimum uzunluk
        max_length: Maximum uzunluk
    
    Returns:
        Doğrulanmış kod
    
    Raises:
        ValidationError: Geçersiz kod
    """
    if not code or not isinstance(code, str):
        raise ValidationError(
            "Kod boş veya geçersiz tip",
            field="code",
            value=code
        )
    
    code = code.strip().upper()
    
    if len(code) < min_length:
        raise ValidationError(
            f"Kod çok kısa: {len(code)} < {min_length}",
            field="code",
            value=code
        )
    
    if len(code) > max_length:
        raise ValidationError(
            f"Kod çok uzun: {len(code)} > {max_length}",
            field="code",
            value=code
        )
    
    return code


def validate_date_string(date_str: str, format: str = "%Y-%m-%d") -> str:
    """
    Tarih string'ini doğrula.
    
    Args:
        date_str: Tarih string'i
        format: Beklenen format
    
    Returns:
        Doğrulanmış tarih string'i
    
    Raises:
        ValidationError: Geçersiz tarih formatı
    """
    if not date_str or not isinstance(date_str, str):
        raise ValidationError(
            "Tarih string'i boş veya geçersiz tip",
            field="date",
            value=date_str
        )
    
    try:
        from datetime import datetime
        datetime.strptime(date_str, format)
    except ValueError:
        raise ValidationError(
            f"Geçersiz tarih formatı: {date_str} (Beklenen: {format})",
            field="date",
            value=date_str
        )
    
    return date_str


def validate_portfolio_row(row: dict) -> dict:
    """
    Portföy satırını doğrula.
    
    Args:
        row: Portföy satırı dictionary'si
    
    Returns:
        Doğrulanmış ve normalize edilmiş satır
    
    Raises:
        ValidationError: Geçersiz satır verisi
    """
    required_fields = ["Kod", "Pazar", "Adet", "Maliyet"]
    
    for field in required_fields:
        if field not in row:
            raise ValidationError(
                f"Eksik zorunlu alan: {field}",
                field=field
            )
    
    validated_row = {}
    
    # Kod
    validated_row["Kod"] = validate_code(row["Kod"])
    
    # Pazar
    validated_row["Pazar"] = validate_market(row["Pazar"])
    
    # Adet
    validated_row["Adet"] = validate_quantity(row["Adet"])
    
    # Maliyet
    validated_row["Maliyet"] = validate_price(row["Maliyet"], min_price=0.0)
    
    # Opsiyonel alanlar
    if "Tip" in row:
        tip = str(row["Tip"]).strip()
        if tip.upper() not in ["PORTFOY", "TAKIP"]:
            tip = "Portfoy"  # Varsayılan
        validated_row["Tip"] = tip
    
    if "Notlar" in row:
        validated_row["Notlar"] = str(row["Notlar"]).strip()
    
    return validated_row
