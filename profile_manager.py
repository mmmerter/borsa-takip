"""
Profile Management System
Manages multiple portfolio profiles (MERT, ANNEM, BERGUZAR, TOTAL)
Each profile has separate data storage and calculations.
"""

import streamlit as st
from typing import List, Dict, Optional
from datetime import datetime

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
        "display_name": "👩 Annem",
        "icon": "👩",
        "color": "#ec4899",
        "is_aggregate": False,
        "description": "Anne portföyü"
    },
    "BERGUZAR": {
        "name": "BERGUZAR",
        "display_name": "👤 Bergüzar",
        "icon": "👤",
        "color": "#10b981",
        "is_aggregate": False,
        "description": "Bergüzar portföyü"
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
PROFILE_ORDER = ["MERT", "ANNEM", "BERGUZAR", "TOTAL"]


def get_profile_config(profile_name: str) -> Dict:
    """Get configuration for a specific profile."""
    return PROFILES.get(profile_name, PROFILES[DEFAULT_PROFILE])


def get_all_profiles() -> List[str]:
    """Get list of all profiles in display order."""
    return PROFILE_ORDER


def get_individual_profiles() -> List[str]:
    """Get list of individual profiles (excluding TOTAL)."""
    return [p for p in PROFILE_ORDER if not PROFILES[p]["is_aggregate"]]


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


def get_current_profile() -> str:
    """Get currently active profile."""
    init_session_state()
    return st.session_state.get("current_profile", DEFAULT_PROFILE)


def set_current_profile(profile_name: str):
    """Set currently active profile."""
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
        st.markdown("### 👤")
    
    with cols[1]:
        # Get profile display names
        profile_options = [PROFILES[p]["display_name"] for p in PROFILE_ORDER]
        current_index = PROFILE_ORDER.index(current_profile)
        
        selected_display = st.selectbox(
            "Profil Seç",
            profile_options,
            index=current_index,
            key="profile_selector",
            label_visibility="collapsed"
        )
        
        # Get selected profile name
        selected_profile = PROFILE_ORDER[profile_options.index(selected_display)]
        
        # Check if profile changed
        if selected_profile != current_profile:
            set_current_profile(selected_profile)
            st.rerun()
            return True
    
    # Show current profile info
    config = get_profile_config(current_profile)
    if config["is_aggregate"]:
        st.info(f"🔄 **{config['display_name']}**: Tüm profillerin birleşik görünümü")
    else:
        st.caption(f"📌 Aktif profil: **{config['display_name']}**")
    
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
