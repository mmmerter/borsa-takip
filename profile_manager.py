"""
Profile Management System
Manages multiple portfolio profiles (MERT, ANNEM, BERGUZAR, İKRAMİYE, TOTAL)
Each profile has separate data storage and calculations.
"""

import streamlit as st
from typing import List, Dict, Optional
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import time

# Profile definitions
PROFILES = {
    "MERT": {
        "name": "MERT",
        "display_name": "🎯 Mert (Ana Profil)",
        "icon": "🎯",
        "color": "#6b7fd7",
        "is_aggregate": False,
        "description": "Ana portföy profili"
    },
    "ANNEM": {
        "name": "ANNEM",
        "display_name": "💝 Annem",
        "icon": "💝",
        "color": "#ec4899",
        "is_aggregate": False,
        "description": "Anne portföyü"
    },
    "BERGUZAR": {
        "name": "BERGUZAR",
        "display_name": "👸 Bergüzar",
        "icon": "👸",
        "color": "#ec4899",
        "is_aggregate": False,
        "description": "Bergüzar portföyü - Pembe prenses teması"
    },
    "İKRAMİYE": {
        "name": "İKRAMİYE",
        "display_name": "🎁 İkramiye",
        "icon": "🎁",
        "color": "#10b981",
        "is_aggregate": False,
        "description": "İkramiye portföyü"
    },
    "TOTAL": {
        "name": "TOTAL",
        "display_name": "📊 TOPLAM",
        "icon": "📊",
        "color": "#f59e0b",
        "is_aggregate": True,
        "description": "Tüm profillerin toplamı"
    }
}

# Default profile
DEFAULT_PROFILE = "MERT"

# Profile order for display
PROFILE_ORDER = ["MERT", "ANNEM", "BERGUZAR", "İKRAMİYE", "TOTAL"]


def get_profile_config(profile_name: str) -> Dict:
    """Get configuration for a specific profile."""
    return PROFILES.get(profile_name, PROFILES[DEFAULT_PROFILE])


def get_all_profiles() -> List[str]:
    """Get list of all profiles in display order."""
    # Profiles are loaded on module init and cached
    # No need to reload every time
    return PROFILE_ORDER


def get_individual_profiles(include_berguzar: bool = None) -> List[str]:
    """
    Get list of individual profiles (excluding TOTAL).
    
    Args:
        include_berguzar: If None, uses session state setting. If False, excludes BERGUZAR.
    """
    # Profiles are loaded on module init and cached
    # No need to reload every time
    
    if include_berguzar is None:
        include_berguzar = st.session_state.get("total_include_berguzar", True)
    
    profiles = [p for p in PROFILE_ORDER if p in PROFILES and not PROFILES[p].get("is_aggregate", False)]
    
    if not include_berguzar and "BERGUZAR" in profiles:
        profiles.remove("BERGUZAR")
    
    return profiles


def is_aggregate_profile(profile_name: str) -> bool:
    """Check if profile is an aggregate (TOTAL) profile."""
    config = get_profile_config(profile_name)
    return config.get("is_aggregate", False)


def init_session_state():
    """Initialize profile-related session state."""
    if "current_profile" not in st.session_state:
        st.session_state["current_profile"] = DEFAULT_PROFILE
    
    if "profile_initialized" not in st.session_state:
        st.session_state["profile_initialized"] = True
    
    # TOTAL profili için Bergüzar dahil/çıkar seçeneği
    if "total_include_berguzar" not in st.session_state:
        st.session_state["total_include_berguzar"] = True


def get_current_profile() -> str:
    """Get currently active profile."""
    init_session_state()
    return st.session_state.get("current_profile", DEFAULT_PROFILE)


def set_current_profile(profile_name: str):
    """Set currently active profile."""
    # Profiles are cached, no need to reload every time
    # This reduces API calls significantly
    
    if profile_name in PROFILES:
        st.session_state["current_profile"] = profile_name
        # Clear cache when switching profiles
        st.cache_data.clear()
    else:
        raise ValueError(f"Invalid profile: {profile_name}")


def get_profile_sheet_name(base_name: str, profile_name: str) -> str:
    """
    Get sheet name for a specific profile.
    For main data: PortfoyData_MERT, PortfoyData_ANNEM, etc.
    For history: portfolio_history_MERT, etc.
    """
    if profile_name == "TOTAL":
        # TOTAL profile is computed, not stored
        return None
    return f"{base_name}_{profile_name}"


def render_profile_selector():
    """
    Render modern profile selector in the UI.
    Returns True if profile changed, False otherwise.
    """
    init_session_state()
    # Profiles are cached, only reload periodically (not every render)
    
    current_profile = get_current_profile()
    
    # Modern profile selector with custom CSS
    st.markdown(
        """
        <style>
        .profile-selector-container {
            background: linear-gradient(135deg, rgba(107, 127, 215, 0.15) 0%, rgba(139, 154, 255, 0.08) 100%);
            border-radius: 16px;
            padding: 16px 20px;
            margin-bottom: 20px;
            border: 1px solid rgba(107, 127, 215, 0.3);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
        }
        .profile-selector-title {
            font-size: 14px;
            font-weight: 700;
            color: #9da1b3;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 12px;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
    
    # Profile selector UI
    cols = st.columns([0.15, 0.85])
    
    with cols[0]:
        # Profil ikonunu göster
        current_config = get_profile_config(current_profile)
        profile_icon = current_config.get("icon", "👤")
        st.markdown(f"### {profile_icon}")
    
    with cols[1]:
        # Get profile display names from cache
        profile_options = [PROFILES[p]["display_name"] for p in PROFILE_ORDER if p in PROFILES]
        
        # Handle case where current profile might not be in list
        try:
            current_index = PROFILE_ORDER.index(current_profile) if current_profile in PROFILE_ORDER else 0
        except:
            current_index = 0
        
        if not profile_options:
            profile_options = ["🎯 Mert (Ana Profil)"]
            current_index = 0
        
        selected_display = st.selectbox(
            "Profil Seç",
            profile_options,
            index=min(current_index, len(profile_options) - 1),
            key="profile_selector",
            label_visibility="collapsed"
        )
        
        # Get selected profile name
        try:
            selected_profile = PROFILE_ORDER[profile_options.index(selected_display)]
        except:
            selected_profile = current_profile
        
        # Check if profile changed
        if selected_profile != current_profile and selected_profile in PROFILES:
            set_current_profile(selected_profile)
            st.rerun()
            return True
    
    # Show current profile info with icon
    config = get_profile_config(current_profile)
    profile_icon = config.get("icon", "👤")
    if config["is_aggregate"]:
        # TOTAL profili için Bergüzar dahil/çıkar seçeneği göster
        include_berguzar = st.session_state.get("total_include_berguzar", True)
        st.info(f"🔄 **{config['display_name']}**: Tüm profillerin birleşik görünümü")
        
        def on_berguzar_change():
            # Cache'i temizle ve sayfayı yenile
            st.cache_data.clear()
            st.rerun()
        
        new_value = st.checkbox(
            "Bergüzar profilini dahil et",
            value=include_berguzar,
            key="total_include_berguzar",
            help="Bergüzar profilini TOTAL hesaplamalarına dahil edip etmeyeceğinizi seçin",
            on_change=on_berguzar_change
        )
    else:
        st.caption(f"📌 Aktif profil: **{profile_icon} {config['display_name'].replace(profile_icon, '').strip()}**")
    
    return False


def get_profile_display_name(profile_name: str) -> str:
    """Get display name for a profile."""
    config = get_profile_config(profile_name)
    return config.get("display_name", profile_name)


def get_profile_icon(profile_name: str) -> str:
    """Get icon for a profile."""
    config = get_profile_config(profile_name)
    return config.get("icon", "👤")


def get_profile_color(profile_name: str) -> str:
    """Get color for a profile."""
    config = get_profile_config(profile_name)
    return config.get("color", "#6b7fd7")


# Profile-specific sheet names
SHEET_NAMES = {
    "main": "PortfoyData",
    "sales": "Satislar",
    "portfolio_history": "portfolio_history",
    "history_bist": "history_bist",
    "history_abd": "history_abd",
    "history_fon": "history_fon",
    "history_emtia": "history_emtia",
    "history_nakit": "history_nakit",
    "daily_base_prices": "daily_base_prices"
}


def get_sheet_name_for_profile(sheet_type: str, profile_name: str) -> str:
    """
    Get the actual Google Sheet worksheet name for a profile.
    
    Args:
        sheet_type: Type of sheet (e.g., 'main', 'sales', 'portfolio_history')
        profile_name: Profile name (e.g., 'MERT', 'ANNEM')
    
    Returns:
        Sheet name with profile suffix (e.g., 'PortfoyData_MERT')
    """
    if profile_name == "TOTAL":
        # TOTAL is computed, not stored - return None
        return None
    
    base_name = SHEET_NAMES.get(sheet_type, sheet_type)
    return f"{base_name}_{profile_name}"


def log_profile_action(action: str, profile_name: str, details: str = ""):
    """Log profile-related actions for debugging."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_message = f"[{timestamp}] Profile: {profile_name} | Action: {action}"
    if details:
        log_message += f" | Details: {details}"
    
    # Store in session state for debugging
    if "profile_logs" not in st.session_state:
        st.session_state["profile_logs"] = []
    
    st.session_state["profile_logs"].append(log_message)
    
    # Keep only last 100 logs
    if len(st.session_state["profile_logs"]) > 100:
        st.session_state["profile_logs"] = st.session_state["profile_logs"][-100:]


# ==================== DYNAMIC PROFILE MANAGEMENT ====================

# Cache for profile data to prevent excessive API calls
_profiles_cache = None
_profiles_cache_time = 0
_profiles_cache_ttl = 900  # 15 minutes cache

# Rate limiting for profile loading
_last_profile_load_time = 0
_min_profile_load_interval = 5.0  # Minimum 5 seconds between profile loads

def _get_gspread_client():
    """Get Google Sheets client."""
    try:
        creds_dict = st.secrets["gcp_service_account"]
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Google Sheets bağlantı hatası: {str(e)}")
        return None


def _retry_with_backoff(func, max_retries=3, initial_delay=1.0, max_delay=60.0, backoff_factor=2.0):
    """
    Retry mechanism with exponential backoff for API calls.
    Handles 429 (quota exceeded) errors specifically.
    """
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            return func()
        except gspread.exceptions.APIError as e:
            last_exception = e
            # Handle response object properly - it might be a Response object or dict
            error_code = None
            if hasattr(e, 'response'):
                response = e.response
                if isinstance(response, dict):
                    error_code = response.get('status', None)
                elif hasattr(response, 'status_code'):
                    error_code = response.status_code
                elif hasattr(response, 'status'):
                    error_code = response.status
            
            # 429 error (quota exceeded) - use longer backoff
            if error_code == 429 or '429' in str(e) or 'Quota exceeded' in str(e) or 'quota' in str(e).lower():
                if attempt < max_retries - 1:
                    # 429 hatası için minimum 60 saniye bekle (quota per minute)
                    # Exponential backoff ile artır ama minimum 60 saniye
                    base_delay = max(60.0, initial_delay * (backoff_factor ** attempt))
                    delay = min(base_delay, max_delay)
                    st.warning(
                        f"⏳ Google Sheets API quota aşıldı. {delay:.0f} saniye bekleniyor... (Deneme {attempt + 1}/{max_retries}, quota per minute limiti nedeniyle)"
                    )
                    time.sleep(delay)
                    continue
                else:
                    raise
            else:
                # Other API errors - shorter backoff
                if attempt < max_retries - 1:
                    delay = min(initial_delay * (backoff_factor ** attempt), max_delay / 2)
                    time.sleep(delay)
                    continue
                else:
                    raise
        except Exception as e:
            # Unexpected errors
            if attempt < max_retries - 1:
                delay = min(initial_delay * (backoff_factor ** attempt), max_delay / 4)
                time.sleep(delay)
                last_exception = e
                continue
            else:
                raise
    
    if last_exception:
        raise last_exception


def _get_profiles_sheet():
    """Get or create the profiles configuration sheet."""
    try:
        client = _get_gspread_client()
        if client is None:
            return None
        
        spreadsheet = client.open("PortfoyData")
        
        # Try to find existing profiles sheet
        try:
            ws = spreadsheet.worksheet("Profiller")
            return ws
        except:
            # Create new profiles sheet
            ws = spreadsheet.add_worksheet(title="Profiller", rows=100, cols=10)
            # Add headers
            headers = ["name", "display_name", "icon", "color", "is_aggregate", "description", "order"]
            ws.append_row(headers)
            
            # Add default profiles
            default_profiles = [
                ["MERT", "🎯 Mert (Ana Profil)", "🎯", "#6b7fd7", "False", "Ana portföy profili", "1"],
                ["ANNEM", "💝 Annem", "💝", "#ec4899", "False", "Anne portföyü", "2"],
                ["BERGUZAR", "👸 Bergüzar", "👸", "#ec4899", "False", "Bergüzar portföyü - Pembe prenses teması", "3"],
                ["İKRAMİYE", "🎁 İkramiye", "🎁", "#10b981", "False", "İkramiye portföyü", "4"],
                ["TOTAL", "📊 TOPLAM", "📊", "#f59e0b", "True", "Tüm profillerin toplamı", "5"],
            ]
            for profile in default_profiles:
                ws.append_row(profile)
            
            return ws
    except Exception as e:
        st.error(f"Profil yapılandırma hatası: {str(e)}")
        return None


def load_profiles_from_sheets(force_reload=False) -> Dict[str, Dict]:
    """
    Load profiles from Google Sheets with caching and rate limiting.
    
    Args:
        force_reload: Force reload even if cache is valid
    
    Returns:
        Dictionary of profile configurations
    """
    global _profiles_cache, _profiles_cache_time, _last_profile_load_time
    
    # Check cache first (unless force reload)
    if not force_reload:
        current_time = time.time()
        
        # Return cached data if still valid
        if _profiles_cache is not None and (current_time - _profiles_cache_time) < _profiles_cache_ttl:
            return _profiles_cache
        
        # Rate limiting - prevent too frequent API calls
        time_since_last_load = current_time - _last_profile_load_time
        if time_since_last_load < _min_profile_load_interval:
            # Too soon, return cached data or defaults
            if _profiles_cache is not None:
                return _profiles_cache
            else:
                return PROFILES
    
    # Update last load time
    _last_profile_load_time = time.time()
    
    try:
        # Get profiles sheet with retry mechanism
        ws = _retry_with_backoff(_get_profiles_sheet, max_retries=2, initial_delay=60.0, max_delay=120.0)
        if ws is None:
            # Return cached or default profiles
            if _profiles_cache is not None:
                return _profiles_cache
            return PROFILES
        
        # Read data with retry mechanism
        def _fetch_profile_data():
            return ws.get_all_records()
        
        # 429 hataları için daha uzun bekleme (quota per minute)
        data = _retry_with_backoff(_fetch_profile_data, max_retries=3, initial_delay=60.0, max_delay=120.0)
        
        profiles = {}
        profile_order = []
        
        # Sort by order column
        sorted_data = sorted(data, key=lambda x: int(x.get("order", 999)))
        
        for row in sorted_data:
            name = row.get("name", "").strip()
            if not name:
                continue
            
            profiles[name] = {
                "name": name,
                "display_name": row.get("display_name", name),
                "icon": row.get("icon", "👤"),
                "color": row.get("color", "#6b7fd7"),
                "is_aggregate": row.get("is_aggregate", "False").lower() == "true",
                "description": row.get("description", ""),
            }
            profile_order.append(name)
        
        # Update global PROFILES and PROFILE_ORDER
        PROFILES.update(profiles)
        global PROFILE_ORDER
        PROFILE_ORDER = profile_order if profile_order else ["MERT", "ANNEM", "BERGUZAR", "İKRAMİYE", "TOTAL"]
        
        # Update cache
        _profiles_cache = profiles
        _profiles_cache_time = time.time()
        
        return profiles
    except gspread.exceptions.APIError as e:
        error_msg = str(e)
        if '429' in error_msg or 'quota' in error_msg.lower() or 'Quota exceeded' in error_msg:
            st.warning(
                f"⚠️ Google Sheets API quota limiti aşıldı. Önbellekteki veriler kullanılıyor. "
                f"Profil değişiklikleri birkaç dakika sonra yansıyacak."
            )
        else:
            st.warning(f"Profil yükleme hatası, varsayılan profiller kullanılıyor: {error_msg}")
        
        # Return cached data if available, otherwise defaults
        if _profiles_cache is not None:
            return _profiles_cache
        return PROFILES
    except Exception as e:
        st.warning(f"Profil yükleme hatası, varsayılan profiller kullanılıyor: {str(e)}")
        # Return cached data if available, otherwise defaults
        if _profiles_cache is not None:
            return _profiles_cache
        return PROFILES


def clear_profiles_cache():
    """Manually clear the profiles cache to force reload on next access."""
    global _profiles_cache, _profiles_cache_time
    _profiles_cache = None
    _profiles_cache_time = 0


def save_profile_to_sheets(profile_data: Dict) -> bool:
    """Save a profile to Google Sheets."""
    ws = _get_profiles_sheet()
    if ws is None:
        return False
    
    try:
        def _fetch_and_save():
            data = ws.get_all_records()
            
            # Check if profile exists
            existing_row = None
            for idx, row in enumerate(data, start=2):  # Start from row 2 (skip header)
                if row.get("name", "").strip().upper() == profile_data["name"].upper():
                    existing_row = idx
                    break
            
            # Prepare row data
            row_data = [
                profile_data["name"],
                profile_data["display_name"],
                profile_data["icon"],
                profile_data["color"],
                str(profile_data.get("is_aggregate", False)),
                profile_data.get("description", ""),
                str(profile_data.get("order", len(data) + 1))
            ]
            
            if existing_row:
                # Update existing profile
                ws.update(f"A{existing_row}:G{existing_row}", [row_data])
            else:
                # Add new profile
                ws.append_row(row_data)
            
            return True
        
        # Use retry mechanism for saving
        # 429 hataları için daha uzun bekleme (quota per minute)
        result = _retry_with_backoff(_fetch_and_save, max_retries=3, initial_delay=60.0, max_delay=120.0)
        
        # Clear cache and force reload
        clear_profiles_cache()
        load_profiles_from_sheets(force_reload=True)
        return result
    except Exception as e:
        st.error(f"Profil kaydetme hatası: {str(e)}")
        return False


def delete_profile_from_sheets(profile_name: str) -> bool:
    """Delete a profile from Google Sheets."""
    ws = _get_profiles_sheet()
    if ws is None:
        return False
    
    try:
        def _fetch_and_delete():
            data = ws.get_all_records()
            
            # Find and delete row
            for idx, row in enumerate(data, start=2):  # Start from row 2 (skip header)
                if row.get("name", "").strip().upper() == profile_name.upper():
                    ws.delete_rows(idx)
                    return True
            return False
        
        # Use retry mechanism for deletion
        # 429 hataları için daha uzun bekleme (quota per minute)
        result = _retry_with_backoff(_fetch_and_delete, max_retries=3, initial_delay=60.0, max_delay=120.0)
        
        if result:
            # Clear cache and force reload
            clear_profiles_cache()
            load_profiles_from_sheets(force_reload=True)
        
        return result
    except Exception as e:
        st.error(f"Profil silme hatası: {str(e)}")
        return False


def get_next_profile_order() -> int:
    """Get the next order number for a new profile."""
    ws = _get_profiles_sheet()
    if ws is None:
        return len(PROFILE_ORDER) + 1
    
    try:
        data = ws.get_all_records()
        if not data:
            return 1
        max_order = max([int(row.get("order", 0)) for row in data], default=0)
        return max_order + 1
    except:
        return len(PROFILE_ORDER) + 1


# Initialize profiles from sheets on module load (with caching)
# This will only happen once per session or when cache expires
try:
    load_profiles_from_sheets()
except Exception as e:
    # Silently use default profiles if loading fails
    # Errors are already handled in load_profiles_from_sheets()
    pass
