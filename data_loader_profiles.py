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


def _find_worksheet_flexible(spreadsheet, possible_names):
    """
    Try to find a worksheet by trying multiple possible names.
    Returns (worksheet, found_name) or (None, None) if not found.
    """
    for name in possible_names:
        try:
            ws = spreadsheet.worksheet(name)
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
            return None
        
        spreadsheet = client.open(SHEET_NAME)
        
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
                        worksheet = spreadsheet.add_worksheet(title="annem", rows=1000, cols=20)
                        headers = ["Kod", "Pazar", "Adet", "Maliyet", "Tip", "Notlar"]
                        worksheet.append_row(headers)
                        _warn_once(f"sheet_created_annem", 
                                 f"✅ 'annem' worksheet'i otomatik oluşturuldu. Artık ANNEM profiline varlık ekleyebilirsiniz!")
                    except Exception as e:
                        _warn_once(f"sheet_missing_annem", 
                                 f"❌ ANNEM profili worksheet'i bulunamadı ve oluşturulamadı. Google Sheets'te 'annem' adlı bir worksheet oluşturun.")
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
                        _warn_once(f"sheet_created_berguzar", 
                                 f"✅ 'berguzar' worksheet'i otomatik oluşturuldu. Artık BERGUZAR profiline varlık ekleyebilirsiniz!")
                    except Exception as e:
                        _warn_once(f"sheet_missing_berguzar", 
                                 f"❌ BERGUZAR profili worksheet'i bulunamadı ve oluşturulamadı. Google Sheets'te 'berguzar' adlı bir worksheet oluşturun.")
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
            
            try:
                worksheet = spreadsheet.worksheet(sheet_name)
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
    except Exception as e:
        return None


@st.cache_data(ttl=30)
def get_data_from_sheet_profile(profile_name=None):
    """
    Get portfolio data for a specific profile.
    If profile is TOTAL, aggregates data from all individual profiles.
    """
    if profile_name is None:
        profile_name = get_current_profile()
    
    # Handle TOTAL profile (aggregate)
    if is_aggregate_profile(profile_name):
        return _get_aggregated_data()
    
    # Get data for individual profile
    try:
        worksheet = _get_profile_sheet("main", profile_name)
        if worksheet is None:
            _warn_once(
                f"sheet_client_{profile_name}",
                f"Google Sheets verisine ulaşılamadı ({profile_name} profili).",
            )
            return pd.DataFrame(columns=["Kod", "Pazar", "Adet", "Maliyet", "Tip", "Notlar"])
        
        data = worksheet.get_all_records()
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
    except Exception:
        _warn_once(
            f"sheet_client_error_{profile_name}",
            f"Google Sheets verisi okunurken hata oluştu ({profile_name} profili).",
        )
        return pd.DataFrame(columns=["Kod", "Pazar", "Adet", "Maliyet", "Tip", "Notlar"])


def _get_aggregated_data():
    """
    Aggregate data from all individual profiles for TOTAL profile.
    Combines all assets with their quantities and costs.
    """
    all_profiles = get_individual_profiles()
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
        worksheet = _get_profile_sheet("main", profile_name)
        if worksheet is None:
            return
        
        # Remove profile column if it exists
        df_to_save = df.copy()
        if "_profile" in df_to_save.columns:
            df_to_save = df_to_save.drop(columns=["_profile"])
        
        worksheet.clear()
        worksheet.update([df_to_save.columns.values.tolist()] + df_to_save.values.tolist())
        
        # Clear cache
        get_data_from_sheet_profile.clear()
    except Exception:
        pass


@st.cache_data(ttl=60)
def get_sales_history_profile(profile_name=None):
    """
    Get sales history for a specific profile.
    If TOTAL, aggregates from all profiles.
    """
    if profile_name is None:
        profile_name = get_current_profile()
    
    # Handle TOTAL profile
    if is_aggregate_profile(profile_name):
        all_profiles = get_individual_profiles()
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
        
        data = worksheet.get_all_records()
        return pd.DataFrame(data) if data else pd.DataFrame(columns=["Tarih", "Kod", "Pazar", "Satılan Adet", "Satış Fiyatı", "Maliyet", "Kâr/Zarar"])
    except Exception:
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
        
        data = worksheet.get_all_records()
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
    except Exception:
        return pd.DataFrame(columns=["Tarih", "Değer_TRY", "Değer_USD"])


def _get_aggregated_history():
    """
    Aggregate portfolio history from all individual profiles.
    """
    all_profiles = get_individual_profiles()
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
        # Check if today's record already exists
        data = worksheet.get_all_records()
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
        all_profiles = get_individual_profiles()
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
        
        data = worksheet.get_all_records()
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
    except Exception:
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
        data = worksheet.get_all_records()
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
