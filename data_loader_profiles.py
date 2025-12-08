"""
Profile-aware data loader wrapper
Wraps data_loader.py functions to support multiple profiles
"""

import streamlit as st
import pandas as pd
from data_loader import (
    _get_gspread_client,
    _warn_once,
    _normalize_tip_value,
    _retry_with_backoff,
    SHEET_NAME,
    DAILY_BASE_SHEET_NAME,
    # Import other functions that don't need modification
    get_tefas_data,
    get_crypto_globals,
    get_usd_try,
    get_financial_news,
    get_portfolio_news,
    get_tickers_data,
)
from profile_manager import (
    get_current_profile,
    get_sheet_name_for_profile,
    is_aggregate_profile,
    get_individual_profiles,
)
from datetime import datetime, timedelta
from logger import get_logger

logger = get_logger()


def _find_worksheet_flexible(spreadsheet, possible_names):
    """
    Try to find a worksheet by trying multiple possible names.
    Returns (worksheet, found_name) or (None, None) if not found.
    Uses retry mechanism for reliability.
    """
    for name in possible_names:
        try:
            def _get_worksheet():
                return spreadsheet.worksheet(name)
            ws = _retry_with_backoff(_get_worksheet, max_retries=2, initial_delay=60.0, max_delay=120.0)
            if ws:
                return ws, name
        except:
            continue
    return None, None


def _get_profile_sheet(sheet_type="main", profile_name=None):
    """
    Get Google Sheet worksheet for a specific profile.
    Uses existing sheets with flexible name matching: ana sayfa (MERT), annem/Annem, berguzar/Berguzar, total
    
    Args:
        sheet_type: Type of sheet ('main', 'sales', 'portfolio_history', etc.)
        profile_name: Profile name (if None, uses current profile)
    
    Returns:
        Worksheet object or None
    """
    if profile_name is None:
        profile_name = get_current_profile()
    
    try:
        client = _get_gspread_client()
        if client is None:
            error_msg = f"❌ Google Sheets bağlantısı kurulamadı ({profile_name} profili). Lütfen Google Sheets servis hesabı ayarlarını kontrol edin veya internet bağlantınızı kontrol edin."
            st.error(error_msg)
            _warn_once(f"sheet_client_connection_{profile_name}", error_msg)
            return None
        
        def _open_spreadsheet():
            return client.open(SHEET_NAME)
        
        spreadsheet = _retry_with_backoff(_open_spreadsheet, max_retries=2, initial_delay=60.0, max_delay=120.0)
        if spreadsheet is None:
            return None
        
        # Determine sheet name based on profile and type
        if sheet_type == "main":
            # Use existing sheets for main portfolio data
            if profile_name == "MERT":
                # Ana profil için sheet1 (ana sayfa)
                worksheet = spreadsheet.sheet1
            elif profile_name == "ANNEM":
                # Farklı olası isimleri dene
                possible_names = ["annem", "Annem", "ANNEM", "Anne", "anne"]
                worksheet, found_name = _find_worksheet_flexible(spreadsheet, possible_names)
                if worksheet is None:
                    # Worksheet bulunamadı, oluştur
                    try:
                        # Retry mechanism ile oluştur
                        def _create_annem_worksheet():
                            ws = spreadsheet.add_worksheet(title="annem", rows=1000, cols=20)
                            headers = ["Kod", "Pazar", "Adet", "Maliyet", "Tip", "Notlar"]
                            ws.append_row(headers)
                            return ws
                        
                        worksheet = _retry_with_backoff(_create_annem_worksheet, max_retries=2, initial_delay=60.0, max_delay=120.0)
                        if worksheet:
                            st.success("✅ 'annem' worksheet'i otomatik oluşturuldu. Artık ANNEM profiline varlık ekleyebilirsiniz!")
                    except Exception as e:
                        error_msg = f"❌ ANNEM profili için Google Sheets worksheet'i bulunamadı ve otomatik oluşturulamadı.\n\n**Çözüm:**\n1. Google Sheets'te '{SHEET_NAME}' dosyasını açın\n2. 'annem' adlı yeni bir worksheet (sekme) oluşturun\n3. İlk satıra şu başlıkları ekleyin: Kod, Pazar, Adet, Maliyet, Tip, Notlar\n4. Servis hesabının bu dosyaya yazma izni olduğundan emin olun\n\n**Teknik Hata:** {str(e)}"
                        st.error(error_msg)
                        _warn_once(f"sheet_missing_annem", error_msg)
                        return None
            elif profile_name == "BERGUZAR":
                # Farklı olası isimleri dene (ü/u varyasyonları)
                possible_names = ["berguzar", "Berguzar", "BERGUZAR", "bergüzar", "Bergüzar", "BERGÜZAR"]
                worksheet, found_name = _find_worksheet_flexible(spreadsheet, possible_names)
                if worksheet is None:
                    # Worksheet bulunamadı, oluştur
                    try:
                        worksheet = spreadsheet.add_worksheet(title="berguzar", rows=1000, cols=20)
                        headers = ["Kod", "Pazar", "Adet", "Maliyet", "Tip", "Notlar"]
                        worksheet.append_row(headers)
                        st.success("✅ 'berguzar' worksheet'i otomatik oluşturuldu. Artık BERGUZAR profiline varlık ekleyebilirsiniz!")
                    except Exception as e:
                        error_msg = f"❌ BERGUZAR profili worksheet'i bulunamadı ve oluşturulamadı. Hata: {str(e)}. Google Sheets'te 'berguzar' adlı bir worksheet oluşturun veya servis hesabına gerekli izinleri verin."
                        st.error(error_msg)
                        _warn_once(f"sheet_missing_berguzar", error_msg)
                        return None
            elif profile_name == "İKRAMİYE":
                # Farklı olası isimleri dene
                possible_names = ["ikramiye", "İkramiye", "İKRAMİYE", "ikramiye", "IKRAMIYE"]
                worksheet, found_name = _find_worksheet_flexible(spreadsheet, possible_names)
                if worksheet is None:
                    # Worksheet bulunamadı, oluştur
                    try:
                        worksheet = spreadsheet.add_worksheet(title="ikramiye", rows=1000, cols=20)
                        headers = ["Kod", "Pazar", "Adet", "Maliyet", "Tip", "Notlar"]
                        worksheet.append_row(headers)
                        st.success("✅ 'ikramiye' worksheet'i otomatik oluşturuldu. Artık İKRAMİYE profiline varlık ekleyebilirsiniz!")
                    except Exception as e:
                        error_msg = f"❌ İKRAMİYE profili worksheet'i bulunamadı ve oluşturulamadı. Hata: {str(e)}. Google Sheets'te 'ikramiye' adlı bir worksheet oluşturun veya servis hesabına gerekli izinleri verin."
                        st.error(error_msg)
                        _warn_once(f"sheet_missing_ikramiye", error_msg)
                        return None
            elif profile_name == "TOTAL":
                # TOTAL için de sekme var ama otomatik hesaplanacak
                # Sadece okuma için kullanılabilir
                possible_names = ["total", "Total", "TOTAL", "Toplam", "toplam"]
                worksheet, found_name = _find_worksheet_flexible(spreadsheet, possible_names)
                if worksheet is None:
                    # TOTAL için worksheet opsiyonel
                    return None
            else:
                return None
        else:
            # Diğer sheet tipleri için profil-specific isimler kullan
            sheet_name = get_sheet_name_for_profile(sheet_type, profile_name)
            if sheet_name is None:
                return None
            
            # MERT profili için özel isimler (underscore'suz)
            if profile_name == "MERT":
                # MERT için orijinal isimleri kullan
                base_names = {
                    "sales": "Satislar",
                    "portfolio_history": "portfolio_history",
                    "history_bist": "history_bist",
                    "history_abd": "history_abd",
                    "history_fon": "history_fon",
                    "history_emtia": "history_emtia",
                    "history_nakit": "history_nakit",
                    "daily_base_prices": "daily_base_prices"
                }
                sheet_name = base_names.get(sheet_type, sheet_name)
            
            def _get_or_create_worksheet():
                try:
                    return spreadsheet.worksheet(sheet_name)
                except Exception:
                    # Worksheet doesn't exist, create it
                    worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=20)
                    
                    # Add headers based on sheet type
                    if sheet_type == "sales":
                        headers = ["Tarih", "Kod", "Pazar", "Satılan Adet", "Satış Fiyatı", "Maliyet", "Kâr/Zarar"]
                        worksheet.append_row(headers)
                    elif sheet_type in ["portfolio_history", "history_bist", "history_abd", "history_fon", "history_emtia", "history_nakit"]:
                        headers = ["Tarih", "Değer_TRY", "Değer_USD"]
                        worksheet.append_row(headers)
                    elif sheet_type == "daily_base_prices":
                        headers = ["Tarih", "Saat", "Kod", "Fiyat", "PB"]
                        worksheet.append_row(headers)
                    return worksheet
            
            worksheet = _retry_with_backoff(_get_or_create_worksheet, max_retries=2, initial_delay=60.0, max_delay=120.0)
        
        return worksheet
    except Exception as e:
        error_msg = f"❌ Google Sheets işlemi başarısız oldu ({profile_name} profili). Hata: {str(e)}. Lütfen Google Sheets bağlantısını ve servis hesabı izinlerini kontrol edin."
        st.error(error_msg)
        _warn_once(f"sheet_error_{profile_name}", error_msg)
        return None


@st.cache_data(ttl=900)  # 15 dakika cache - Sheets verileri daha az sık değişir (quota koruması için artırıldı)
def get_data_from_sheet_profile(profile_name=None):
    """
    Get portfolio data for a specific profile.
    If profile is TOTAL, aggregates data from all individual profiles.
    
    IMPORTANT: profile_name is used as cache key, so each profile has separate cache.
    Always pass profile_name explicitly to ensure correct caching.
    """
    if profile_name is None:
        profile_name = get_current_profile()
    
    # Ensure profile_name is used in cache key by including it in function signature
    # Cache will be separate for each profile - Streamlit automatically uses function arguments as cache key
    
    # Handle TOTAL profile (aggregate)
    if is_aggregate_profile(profile_name):
        return _get_aggregated_data()
    
    # Get data for individual profile
    try:
        worksheet = _get_profile_sheet("main", profile_name)
        if worksheet is None:
            # Hata mesajı zaten _get_profile_sheet içinde gösterildi, burada sadece boş DataFrame döndür
            return pd.DataFrame(columns=["Kod", "Pazar", "Adet", "Maliyet", "Tip", "Notlar"])
        
        # Retry mekanizması ile veri okuma
        def _fetch_profile_data():
            return worksheet.get_all_records()
        
        # 429 hataları için daha uzun bekleme (quota per minute)
        data = _retry_with_backoff(_fetch_profile_data, max_retries=3, initial_delay=60.0, max_delay=120.0)
        if not data:
            return pd.DataFrame(columns=["Kod", "Pazar", "Adet", "Maliyet", "Tip", "Notlar"])
        
        df = pd.DataFrame(data)
        for col in ["Kod", "Pazar", "Adet", "Maliyet", "Tip", "Notlar"]:
            if col not in df.columns:
                df[col] = ""
        
        if not df.empty:
            # Vectorized işlemler
            df["Pazar"] = df["Pazar"].astype(str)
            df.loc[df["Pazar"].str.contains("FON", case=False, na=False), "Pazar"] = "FON"
            df.loc[df["Pazar"].str.upper().str.contains("FIZIKI", na=False), "Pazar"] = "EMTIA"
            df["Tip"] = df["Tip"].apply(_normalize_tip_value)
        
        return df
    except Exception as e:
        error_msg = str(e)
        if '429' in error_msg or 'quota' in error_msg.lower() or 'Quota exceeded' in error_msg:
            display_msg = f"⚠️ Google Sheets API quota limiti aşıldı ({profile_name} profili). Birkaç dakika bekleyip tekrar deneyin."
            st.error(display_msg)
            _warn_once(
                f"sheet_quota_error_{profile_name}",
                display_msg,
            )
        else:
            display_msg = f"❌ Google Sheets verisi okunurken hata oluştu ({profile_name} profili). Hata: {error_msg}"
            st.error(display_msg)
            _warn_once(
                f"sheet_client_error_{profile_name}",
                display_msg,
            )
        logger.error(f"Google Sheets veri okuma hatası ({profile_name}): {error_msg}", exc_info=True)
        return pd.DataFrame(columns=["Kod", "Pazar", "Adet", "Maliyet", "Tip", "Notlar"])


def _get_aggregated_data():
    """
    Aggregate data from all individual profiles for TOTAL profile.
    Combines all assets with their quantities and costs.
    Uses session state to determine if BERGUZAR should be included.
    """
    # Get profiles based on berguzar inclusion setting
    include_berguzar = st.session_state.get("total_include_berguzar", True)
    all_profiles = get_individual_profiles(include_berguzar=include_berguzar)
    aggregated_rows = []
    
    for profile_name in all_profiles:
        df = get_data_from_sheet_profile(profile_name)
        if df is not None and not df.empty:
            # Add profile identifier to differentiate same assets from different profiles
            df_copy = df.copy()
            df_copy["_profile"] = profile_name
            aggregated_rows.append(df_copy)
    
    if not aggregated_rows:
        return pd.DataFrame(columns=["Kod", "Pazar", "Adet", "Maliyet", "Tip", "Notlar", "_profile"])
    
    # Combine all data
    combined_df = pd.concat(aggregated_rows, ignore_index=True)
    
    # For TOTAL view, we want to show each profile's assets separately
    # but we could also aggregate same assets (optional)
    # For now, keep them separate with profile identifier
    
    return combined_df


def save_data_to_sheet_profile(df, profile_name=None):
    """
    Save portfolio data for a specific profile.
    TOTAL profile is computed but can also be saved to the 'total' sheet.
    """
    if profile_name is None:
        profile_name = get_current_profile()
    
    # TOTAL profili için uyarı göster ama kaydetmeye izin ver (otomatik güncellemeler için)
    if is_aggregate_profile(profile_name):
        # TOTAL'i sessizce kaydet (arka planda otomatik güncellemeler için)
        # Kullanıcı manuel düzenleme yapamaz ama sistem yazabilir
        pass
    
    try:
        # Retry mechanism ile worksheet'i al veya oluştur
        def _get_or_create_worksheet():
            worksheet = _get_profile_sheet("main", profile_name)
            if worksheet is None:
                # Worksheet bulunamadı, tekrar dene veya oluştur
                client = _get_gspread_client()
                if client is None:
                    return None
                
                spreadsheet = _retry_with_backoff(
                    lambda: client.open(SHEET_NAME),
                    max_retries=2,
                    initial_delay=60.0,
                    max_delay=120.0
                )
                if spreadsheet is None:
                    return None
                
                # ANNEM profili için özel işlem
                if profile_name == "ANNEM":
                    try:
                        worksheet = spreadsheet.worksheet("annem")
                        return worksheet
                    except:
                        # Oluştur
                        worksheet = spreadsheet.add_worksheet(title="annem", rows=1000, cols=20)
                        headers = ["Kod", "Pazar", "Adet", "Maliyet", "Tip", "Notlar"]
                        worksheet.append_row(headers)
                        return worksheet
                else:
                    # Diğer profiller için de benzer mantık
                    sheet_name = profile_name.lower()
                    try:
                        worksheet = spreadsheet.worksheet(sheet_name)
                        return worksheet
                    except:
                        worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=20)
                        headers = ["Kod", "Pazar", "Adet", "Maliyet", "Tip", "Notlar"]
                        worksheet.append_row(headers)
                        return worksheet
            return worksheet
        
        worksheet = _retry_with_backoff(_get_or_create_worksheet, max_retries=3, initial_delay=60.0, max_delay=120.0)
        
        if worksheet is None:
            error_msg = f"⚠️ {profile_name} profili için worksheet bulunamadı ve oluşturulamadı. Lütfen Google Sheets'te '{profile_name.lower()}' adlı bir worksheet oluşturun."
            st.error(error_msg)
            return
        
        # Remove profile column if it exists
        df_to_save = df.copy()
        if "_profile" in df_to_save.columns:
            df_to_save = df_to_save.drop(columns=["_profile"])
        
        # Ensure all required columns exist
        required_cols = ["Kod", "Pazar", "Adet", "Maliyet", "Tip", "Notlar"]
        for col in required_cols:
            if col not in df_to_save.columns:
                df_to_save[col] = ""
        
        # Save with retry
        def _save_data():
            worksheet.clear()
            if not df_to_save.empty:
                worksheet.update([df_to_save.columns.values.tolist()] + df_to_save.values.tolist())
            else:
                # Empty dataframe - just set headers
                worksheet.update([required_cols], range_name="A1:F1")
        
        _retry_with_backoff(_save_data, max_retries=3, initial_delay=60.0, max_delay=120.0)
        
        # Clear cache for this specific profile
        # Cache key includes profile_name, so we need to clear it explicitly
        try:
            get_data_from_sheet_profile.clear()
            # Also clear cache for the specific profile by calling with the profile name
            # This ensures the cache is invalidated for the correct profile
            if hasattr(get_data_from_sheet_profile, 'clear'):
                # Clear all cached entries - Streamlit cache_data decorator handles this
                get_data_from_sheet_profile.clear()
        except Exception:
            pass
    except Exception as e:
        error_msg = f"❌ Veri kaydedilirken hata oluştu ({profile_name} profili). Hata: {str(e)}"
        st.error(error_msg)
        logger.error(f"Save data error ({profile_name}): {error_msg}", exc_info=True)


@st.cache_data(ttl=900)  # 15 dakika cache - Satış geçmişi daha az sık değişir (quota koruması için artırıldı)
def get_sales_history_profile(profile_name=None):
    """
    Get sales history for a specific profile.
    If TOTAL, aggregates from all profiles.
    """
    if profile_name is None:
        profile_name = get_current_profile()
    
    # Handle TOTAL profile
    if is_aggregate_profile(profile_name):
        include_berguzar = st.session_state.get("total_include_berguzar", True)
        all_profiles = get_individual_profiles(include_berguzar=include_berguzar)
        all_sales = []
        
        for prof in all_profiles:
            sales_df = get_sales_history_profile(prof)
            if sales_df is not None and not sales_df.empty:
                sales_df_copy = sales_df.copy()
                sales_df_copy["Profil"] = prof
                all_sales.append(sales_df_copy)
        
        if not all_sales:
            return pd.DataFrame(columns=["Tarih", "Kod", "Pazar", "Satılan Adet", "Satış Fiyatı", "Maliyet", "Kâr/Zarar", "Profil"])
        
        return pd.concat(all_sales, ignore_index=True)
    
    try:
        worksheet = _get_profile_sheet("sales", profile_name)
        if worksheet is None:
            return pd.DataFrame(columns=["Tarih", "Kod", "Pazar", "Satılan Adet", "Satış Fiyatı", "Maliyet", "Kâr/Zarar"])
        
        def _fetch_sales():
            return worksheet.get_all_records()
        
        # 429 hataları için daha uzun bekleme (quota per minute)
        data = _retry_with_backoff(_fetch_sales, max_retries=3, initial_delay=60.0, max_delay=120.0)
        return pd.DataFrame(data) if data else pd.DataFrame(columns=["Tarih", "Kod", "Pazar", "Satılan Adet", "Satış Fiyatı", "Maliyet", "Kâr/Zarar"])
    except Exception as e:
        logger.error(f"Satış geçmişi okuma hatası ({profile_name}): {str(e)}", exc_info=True)
        return pd.DataFrame(columns=["Tarih", "Kod", "Pazar", "Satılan Adet", "Satış Fiyatı", "Maliyet", "Kâr/Zarar"])


def add_sale_record_profile(date, code, market, qty, price, cost, profit, profile_name=None):
    """
    Add a sale record for a specific profile.
    """
    if profile_name is None:
        profile_name = get_current_profile()
    
    # Cannot add to TOTAL profile
    if is_aggregate_profile(profile_name):
        st.error("TOTAL profiline satış eklenemez. Lütfen bireysel bir profil seçin.")
        return
    
    try:
        worksheet = _get_profile_sheet("sales", profile_name)
        if worksheet is None:
            return
        
        worksheet.append_row([str(date), code, market, float(qty), float(price), float(cost), float(profit)])
        
        # Clear cache
        get_sales_history_profile.clear()
    except Exception:
        pass


def read_portfolio_history_profile(profile_name=None):
    """
    Read portfolio history for a specific profile.
    If TOTAL, aggregates from all profiles.
    """
    if profile_name is None:
        profile_name = get_current_profile()
    
    # Handle TOTAL profile
    if is_aggregate_profile(profile_name):
        return _get_aggregated_history()
    
    try:
        worksheet = _get_profile_sheet("portfolio_history", profile_name)
        if worksheet is None:
            return pd.DataFrame(columns=["Tarih", "Değer_TRY", "Değer_USD"])
        
        def _fetch_history():
            expected_headers = ["Tarih", "Değer_TRY", "Değer_USD"]
            
            try:
                # Get first row to check headers
                first_row = worksheet.row_values(1)
                if not first_row:
                    # Empty worksheet, add headers
                    headers = ["Tarih", "Değer_TRY", "Değer_USD"]
                    worksheet.update([headers], range_name="A1:C1")
                    return []
                
                # Check for duplicate headers and fix them if needed
                first_row_cleaned = [h.strip() if h else "" for h in first_row]
                headers_need_fixing = (
                    len(first_row_cleaned) != len(set(first_row_cleaned)) or 
                    any(h == "" for h in first_row_cleaned[:3])
                )
                
                # Normalize headers for comparison (case-insensitive, strip whitespace)
                first_row_normalized = [h.strip().lower() if h else "" for h in first_row[:3]]
                expected_normalized = [h.strip().lower() for h in expected_headers]
                headers_match = (
                    len(first_row_normalized) >= 3 and
                    first_row_normalized[0] == expected_normalized[0] and
                    first_row_normalized[1] == expected_normalized[1] and
                    first_row_normalized[2] == expected_normalized[2]
                )
                
                if headers_need_fixing or not headers_match:
                    # Headers need fixing or don't match - fix them
                    if headers_need_fixing:
                        logger.warning(f"Duplicate or invalid headers detected, fixing headers")
                    headers = ["Tarih", "Değer_TRY", "Değer_USD"]
                    worksheet.update([headers], range_name="A1:C1")
                    # After fixing, read row by row to avoid timing issues
                    all_rows = worksheet.get_all_values()
                    if len(all_rows) <= 1:
                        return []
                    records = []
                    for row in all_rows[1:]:
                        if len(row) >= 3 and any(cell.strip() for cell in row[:3]):
                            records.append({
                                "Tarih": row[0] if len(row) > 0 else "",
                                "Değer_TRY": row[1] if len(row) > 1 else "",
                                "Değer_USD": row[2] if len(row) > 2 else ""
                            })
                    return records
                
                # Headers are valid and match - try using expected_headers for efficient reading
                # But catch any errors and fall back to row-by-row reading
                try:
                    return worksheet.get_all_records(expected_headers=expected_headers)
                except Exception:
                    # If expected_headers fails (e.g., extra columns, order issues), read row by row
                    all_rows = worksheet.get_all_values()
                    if len(all_rows) <= 1:
                        return []
                    records = []
                    for row in all_rows[1:]:
                        if len(row) >= 3 and any(cell.strip() for cell in row[:3]):
                            records.append({
                                "Tarih": row[0] if len(row) > 0 else "",
                                "Değer_TRY": row[1] if len(row) > 1 else "",
                                "Değer_USD": row[2] if len(row) > 2 else ""
                            })
                    return records
            except Exception as e:
                # If there's still an error, try reading rows directly
                try:
                    # Read all rows and manually parse (skip header row)
                    all_rows = worksheet.get_all_values()
                    if len(all_rows) <= 1:
                        return []
                    
                    # Skip header row and parse data rows
                    records = []
                    for row in all_rows[1:]:
                        if len(row) >= 3 and any(cell.strip() for cell in row[:3]):
                            records.append({
                                "Tarih": row[0] if len(row) > 0 else "",
                                "Değer_TRY": row[1] if len(row) > 1 else "",
                                "Değer_USD": row[2] if len(row) > 2 else ""
                            })
                    return records
                except Exception as e2:
                    logger.error(f"Veri okuma başarısız: {str(e2)}")
                    return []
        
        # 429 hataları için daha uzun bekleme (quota per minute)
        data = _retry_with_backoff(_fetch_history, max_retries=3, initial_delay=60.0, max_delay=120.0)
        if not data:
            return pd.DataFrame(columns=["Tarih", "Değer_TRY", "Değer_USD"])
        
        df = pd.DataFrame(data)
        if "Tarih" in df.columns:
            df["Tarih"] = pd.to_datetime(df["Tarih"])
        else:
            df["Tarih"] = pd.to_datetime(datetime.now().strftime("%Y-%m-%d"))
        if "Değer_TRY" not in df.columns:
            df["Değer_TRY"] = 0.0
        if "Değer_USD" not in df.columns:
            df["Değer_USD"] = 0.0
        
        return df.sort_values("Tarih")
    except Exception as e:
        logger.error(f"Portfolio history okuma hatası ({profile_name}): {str(e)}", exc_info=True)
        return pd.DataFrame(columns=["Tarih", "Değer_TRY", "Değer_USD"])


def _get_aggregated_history():
    """
    Aggregate portfolio history from all individual profiles.
    Uses session state to determine if BERGUZAR should be included.
    """
    include_berguzar = st.session_state.get("total_include_berguzar", True)
    all_profiles = get_individual_profiles(include_berguzar=include_berguzar)
    all_dates = set()
    profile_data = {}
    
    # Collect data from all profiles
    for profile_name in all_profiles:
        df = read_portfolio_history_profile(profile_name)
        if df is not None and not df.empty:
            profile_data[profile_name] = df
            all_dates.update(df["Tarih"].dt.date.tolist())
    
    if not profile_data:
        return pd.DataFrame(columns=["Tarih", "Değer_TRY", "Değer_USD"])
    
    # Create aggregated dataframe
    all_dates = sorted(list(all_dates))
    aggregated_rows = []
    
    for date in all_dates:
        total_try = 0.0
        total_usd = 0.0
        
        for profile_name, df in profile_data.items():
            # Find value for this date
            date_mask = df["Tarih"].dt.date == date
            if date_mask.any():
                row = df[date_mask].iloc[-1]  # Take last entry if multiple
                total_try += float(row.get("Değer_TRY", 0))
                total_usd += float(row.get("Değer_USD", 0))
        
        aggregated_rows.append({
            "Tarih": pd.Timestamp(date),
            "Değer_TRY": total_try,
            "Değer_USD": total_usd
        })
    
    return pd.DataFrame(aggregated_rows)


def write_portfolio_history_profile(value_try, value_usd, profile_name=None):
    """
    Write portfolio history for a specific profile.
    TOTAL profile history is computed, not stored.
    """
    if profile_name is None:
        profile_name = get_current_profile()
    
    # Don't write to TOTAL profile
    if is_aggregate_profile(profile_name):
        return
    
    worksheet = _get_profile_sheet("portfolio_history", profile_name)
    if worksheet is None:
        return
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    try:
        # Ensure headers are correct before reading
        first_row = worksheet.row_values(1)
        expected_headers = ["Tarih", "Değer_TRY", "Değer_USD"]
        
        if not first_row:
            # Empty worksheet, add headers
            worksheet.update([expected_headers], range_name="A1:C1")
        else:
            # Check if headers match (normalized comparison)
            first_row_normalized = [h.strip().lower() if h else "" for h in first_row[:3]]
            expected_normalized = [h.strip().lower() for h in expected_headers]
            headers_match = (
                len(first_row_normalized) >= 3 and
                first_row_normalized[0] == expected_normalized[0] and
                first_row_normalized[1] == expected_normalized[1] and
                first_row_normalized[2] == expected_normalized[2]
            )
            
            if not headers_match:
                # Headers don't match - fix them
                worksheet.update([expected_headers], range_name="A1:C1")
        
        # Check if today's record already exists
        data = worksheet.get_all_records(expected_headers=expected_headers)
        for row in data:
            if str(row.get("Tarih", ""))[:10] == today_str:
                return  # Already recorded today
        
        new_row = [today_str, float(value_try), float(value_usd)]
        worksheet.append_row(new_row)
    except Exception:
        pass


# Market-specific history functions (BIST, ABD, FON, EMTIA, NAKIT)
def read_history_market_profile(market_type, profile_name=None):
    """
    Read market-specific history for a profile.
    market_type: 'bist', 'abd', 'fon', 'emtia', 'nakit'
    """
    if profile_name is None:
        profile_name = get_current_profile()
    
    sheet_type = f"history_{market_type}"
    
    # Handle TOTAL profile - aggregate from all profiles
    if is_aggregate_profile(profile_name):
        include_berguzar = st.session_state.get("total_include_berguzar", True)
        all_profiles = get_individual_profiles(include_berguzar=include_berguzar)
        all_dates = set()
        profile_data = {}
        
        for prof in all_profiles:
            df = read_history_market_profile(market_type, prof)
            if df is not None and not df.empty:
                profile_data[prof] = df
                all_dates.update(df["Tarih"].dt.date.tolist())
        
        if not profile_data:
            return pd.DataFrame(columns=["Tarih", "Değer_TRY", "Değer_USD"])
        
        # Aggregate by date
        all_dates = sorted(list(all_dates))
        aggregated_rows = []
        
        for date in all_dates:
            total_try = 0.0
            total_usd = 0.0
            
            for prof, df in profile_data.items():
                date_mask = df["Tarih"].dt.date == date
                if date_mask.any():
                    row = df[date_mask].iloc[-1]
                    total_try += float(row.get("Değer_TRY", 0))
                    total_usd += float(row.get("Değer_USD", 0))
            
            aggregated_rows.append({
                "Tarih": pd.Timestamp(date),
                "Değer_TRY": total_try,
                "Değer_USD": total_usd
            })
        
        return pd.DataFrame(aggregated_rows)
    
    # Individual profile
    try:
        worksheet = _get_profile_sheet(sheet_type, profile_name)
        if worksheet is None:
            return pd.DataFrame(columns=["Tarih", "Değer_TRY", "Değer_USD"])
        
        def _fetch_market_history():
            expected_headers = ["Tarih", "Değer_TRY", "Değer_USD"]
            
            try:
                # Get first row to check headers
                first_row = worksheet.row_values(1)
                if not first_row:
                    # Empty worksheet, add headers
                    headers = ["Tarih", "Değer_TRY", "Değer_USD"]
                    worksheet.update([headers], range_name="A1:C1")
                    return []
                
                # Check for duplicate headers and fix them if needed
                first_row_cleaned = [h.strip() if h else "" for h in first_row]
                headers_need_fixing = (
                    len(first_row_cleaned) != len(set(first_row_cleaned)) or 
                    any(h == "" for h in first_row_cleaned[:3])
                )
                
                # Normalize headers for comparison (case-insensitive, strip whitespace)
                first_row_normalized = [h.strip().lower() if h else "" for h in first_row[:3]]
                expected_normalized = [h.strip().lower() for h in expected_headers]
                headers_match = (
                    len(first_row_normalized) >= 3 and
                    first_row_normalized[0] == expected_normalized[0] and
                    first_row_normalized[1] == expected_normalized[1] and
                    first_row_normalized[2] == expected_normalized[2]
                )
                
                if headers_need_fixing or not headers_match:
                    # Headers need fixing or don't match - fix them
                    if headers_need_fixing:
                        logger.warning(f"Duplicate or invalid headers detected, fixing headers")
                    headers = ["Tarih", "Değer_TRY", "Değer_USD"]
                    worksheet.update([headers], range_name="A1:C1")
                    # After fixing, read row by row to avoid timing issues
                    all_rows = worksheet.get_all_values()
                    if len(all_rows) <= 1:
                        return []
                    records = []
                    for row in all_rows[1:]:
                        if len(row) >= 3 and any(cell.strip() for cell in row[:3]):
                            records.append({
                                "Tarih": row[0] if len(row) > 0 else "",
                                "Değer_TRY": row[1] if len(row) > 1 else "",
                                "Değer_USD": row[2] if len(row) > 2 else ""
                            })
                    return records
                
                # Headers are valid and match - try using expected_headers for efficient reading
                # But catch any errors and fall back to row-by-row reading
                try:
                    return worksheet.get_all_records(expected_headers=expected_headers)
                except Exception:
                    # If expected_headers fails (e.g., extra columns, order issues), read row by row
                    all_rows = worksheet.get_all_values()
                    if len(all_rows) <= 1:
                        return []
                    records = []
                    for row in all_rows[1:]:
                        if len(row) >= 3 and any(cell.strip() for cell in row[:3]):
                            records.append({
                                "Tarih": row[0] if len(row) > 0 else "",
                                "Değer_TRY": row[1] if len(row) > 1 else "",
                                "Değer_USD": row[2] if len(row) > 2 else ""
                            })
                    return records
            except Exception as e:
                # If there's still an error, try reading rows directly
                try:
                    # Read all rows and manually parse (skip header row)
                    all_rows = worksheet.get_all_values()
                    if len(all_rows) <= 1:
                        return []
                    
                    # Skip header row and parse data rows
                    records = []
                    for row in all_rows[1:]:
                        if len(row) >= 3 and any(cell.strip() for cell in row[:3]):
                            records.append({
                                "Tarih": row[0] if len(row) > 0 else "",
                                "Değer_TRY": row[1] if len(row) > 1 else "",
                                "Değer_USD": row[2] if len(row) > 2 else ""
                            })
                    return records
                except Exception as e2:
                    logger.error(f"Veri okuma başarısız: {str(e2)}")
                    return []
        
        # 429 hataları için daha uzun bekleme (quota per minute)
        data = _retry_with_backoff(_fetch_market_history, max_retries=3, initial_delay=60.0, max_delay=120.0)
        if not data:
            return pd.DataFrame(columns=["Tarih", "Değer_TRY", "Değer_USD"])
        
        df = pd.DataFrame(data)
        if "Tarih" in df.columns:
            df["Tarih"] = pd.to_datetime(df["Tarih"])
        else:
            df["Tarih"] = pd.to_datetime(datetime.now().strftime("%Y-%m-%d"))
        if "Değer_TRY" not in df.columns:
            df["Değer_TRY"] = 0.0
        if "Değer_USD" not in df.columns:
            df["Değer_USD"] = 0.0
        
        return df.sort_values("Tarih")
    except Exception as e:
        logger.error(f"Market history okuma hatası ({profile_name}, {market_type}): {str(e)}", exc_info=True)
        return pd.DataFrame(columns=["Tarih", "Değer_TRY", "Değer_USD"])


def write_history_market_profile(market_type, value_try, value_usd, profile_name=None):
    """
    Write market-specific history for a profile.
    """
    if profile_name is None:
        profile_name = get_current_profile()
    
    # Don't write to TOTAL profile
    if is_aggregate_profile(profile_name):
        return
    
    sheet_type = f"history_{market_type}"
    worksheet = _get_profile_sheet(sheet_type, profile_name)
    if worksheet is None:
        return
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    try:
        # Ensure headers are correct before reading
        first_row = worksheet.row_values(1)
        expected_headers = ["Tarih", "Değer_TRY", "Değer_USD"]
        
        if not first_row:
            # Empty worksheet, add headers
            worksheet.update([expected_headers], range_name="A1:C1")
        else:
            # Check if headers match (normalized comparison)
            first_row_normalized = [h.strip().lower() if h else "" for h in first_row[:3]]
            expected_normalized = [h.strip().lower() for h in expected_headers]
            headers_match = (
                len(first_row_normalized) >= 3 and
                first_row_normalized[0] == expected_normalized[0] and
                first_row_normalized[1] == expected_normalized[1] and
                first_row_normalized[2] == expected_normalized[2]
            )
            
            if not headers_match:
                # Headers don't match - fix them
                worksheet.update([expected_headers], range_name="A1:C1")
        
        # Check if today's record already exists
        data = worksheet.get_all_records(expected_headers=expected_headers)
        for row in data:
            if str(row.get("Tarih", ""))[:10] == today_str:
                return
        
        new_row = [today_str, float(value_try), float(value_usd)]
        worksheet.append_row(new_row)
    except Exception:
        pass


# Convenience wrappers for each market type
def read_history_bist_profile(profile_name=None):
    return read_history_market_profile("bist", profile_name)

def write_history_bist_profile(value_try, value_usd, profile_name=None):
    write_history_market_profile("bist", value_try, value_usd, profile_name)

def read_history_abd_profile(profile_name=None):
    return read_history_market_profile("abd", profile_name)

def write_history_abd_profile(value_try, value_usd, profile_name=None):
    write_history_market_profile("abd", value_try, value_usd, profile_name)

def read_history_fon_profile(profile_name=None):
    return read_history_market_profile("fon", profile_name)

def write_history_fon_profile(value_try, value_usd, profile_name=None):
    write_history_market_profile("fon", value_try, value_usd, profile_name)

def read_history_emtia_profile(profile_name=None):
    return read_history_market_profile("emtia", profile_name)

def write_history_emtia_profile(value_try, value_usd, profile_name=None):
    write_history_market_profile("emtia", value_try, value_usd, profile_name)

def read_history_nakit_profile(profile_name=None):
    return read_history_market_profile("nakit", profile_name)

def write_history_nakit_profile(value_try, value_usd, profile_name=None):
    write_history_market_profile("nakit", value_try, value_usd, profile_name)


# Daily base prices (shared across profiles for now)
def get_daily_base_prices_profile(profile_name=None):
    """
    Get daily base prices for a profile.
    For simplicity, using shared daily base prices across all profiles.
    """
    from data_loader import get_daily_base_prices
    return get_daily_base_prices()


def update_daily_base_prices_profile(current_prices_df, profile_name=None):
    """
    Update daily base prices for a profile.
    """
    from data_loader import update_daily_base_prices
    update_daily_base_prices(current_prices_df)
