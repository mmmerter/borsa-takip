import streamlit as st
import yfinance as yf
import pandas as pd
import time
import plotly.express as px
from streamlit_option_menu import option_menu
from datetime import datetime, timedelta

# --- MODÜLLER ---
from utils import (
    ANALYSIS_COLS,
    KNOWN_FUNDS,
    MARKET_DATA,
    smart_parse,
    styled_dataframe,
    get_yahoo_symbol,
)
from data_loader import (
    get_data_from_sheet,
    save_data_to_sheet,
    get_sales_history,
    add_sale_record,
    get_usd_try,
    get_tickers_data,
    get_financial_news,
    get_portfolio_news,
    get_tefas_data,
    get_binance_positions,
    read_portfolio_history,
    write_portfolio_history,
    get_timeframe_changes,
    read_history_bist,
    write_history_bist,
    read_history_abd,
    write_history_abd,
    read_history_fon,
    write_history_fon,
    read_history_emtia,
    write_history_emtia,
    read_history_nakit,
    write_history_nakit,
)

# Fon getirilerinin yeniden dahil edilme tarihi (varsayılan: yarın)
def _init_fon_reset_date():
    tomorrow = (pd.Timestamp.today().normalize() + pd.Timedelta(days=1))
    default_date = tomorrow.strftime("%Y-%m-%d")
    try:
        raw = st.secrets.get("fon_metric_reset_date", default_date)
    except Exception:
        raw = default_date
    try:
        return pd.to_datetime(raw).tz_localize(None)
    except Exception:
        return pd.to_datetime(default_date).tz_localize(None)

from charts import (
    render_pie_bar_charts,
    render_pazar_tab,
    render_detail_view,
    get_historical_chart,
    get_comparison_chart,
)

# --- SAYFA AYARLARI ---
_PAGE_CONFIG = {
    "page_title": "Merter’in Terminali",
    "layout": "wide",
    "page_icon": "🏦",
    "initial_sidebar_state": "collapsed",
}
_THEME_CONFIG = {
    "base": "dark",
    "primaryColor": "#6b7fd7",
    "secondaryBackgroundColor": "#1a1c24",
    "backgroundColor": "#0e1117",
    "textColor": "#ffffff",
}


def _configure_page():
    """Apply page config, gracefully skipping theme on old Streamlit versions."""
    try:
        st.set_page_config(**_PAGE_CONFIG, theme=_THEME_CONFIG)
    except TypeError as exc:
        if "theme" not in str(exc):
            raise
        st.set_page_config(**_PAGE_CONFIG)


_configure_page()

FON_METRIC_RESET_DATE = _init_fon_reset_date()

if "ui_theme" not in st.session_state:
    st.session_state["ui_theme"] = "dark"

# Otomatik yenileme kaldırıldı - artık sadece sayaç var

theme_selector_cols = st.columns([0.85, 0.15])
with theme_selector_cols[0]:
    pass  # Boş alan
with theme_selector_cols[1]:
    toggle_label = "🌞 Açık Tema" if st.session_state["ui_theme"] == "dark" else "🌙 Koyu Tema"
    if st.button(toggle_label, key="theme_toggle_button"):
        st.session_state["ui_theme"] = "light" if st.session_state["ui_theme"] == "dark" else "dark"
        st.rerun()

# --- CSS ---
st.markdown(
    """
<style>
    :root {
        color-scheme: dark;
    }

    html, body, [data-testid="stAppViewContainer"], [data-testid="stAppBody"] {
        background-color: #0e1117 !important;
        color: #ffffff !important;
    }

    /* Streamlit Header Gizle */
    header { visibility: hidden; height: 0px; }
    
    /* Kenar Boşluklarını Sıfırla */
    div.st-emotion-cache-1c9v9c4 { padding: 0 !important; }
    .block-container {
        padding-top: 1rem;
        padding-left: 0 !important;
        padding-right: 0 !important;
    }

    /* Metric Kutuları */
    div[data-testid="stMetric"] {
        background-color: #262730 !important;
        border: 1px solid #464b5f;
        border-radius: 10px;
        padding: 15px;
        color: #ffffff !important;
    }
    div[data-testid="stMetricValue"] { color: #ffffff !important; }
    div[data-testid="stMetricLabel"] { color: #bfbfbf !important; }

    /* Ticker Alanı - Modern */
    .ticker-container {
        width: 100%;
        overflow: hidden;
        background: linear-gradient(135deg, #1a1c24 0%, #0e1117 100%);
        border-bottom: 1px solid #2f3440;
        margin-bottom: 20px;
        white-space: nowrap;
        position: relative;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
        display: flex;
        align-items: center;
    }
    .ticker-label {
        flex-shrink: 0;
        background: linear-gradient(135deg, #1a1c24 0%, #0e1117 100%);
        padding: 10px 15px;
        font-size: 14px;
        font-weight: 700;
        letter-spacing: 0.5px;
        text-transform: uppercase;
        color: #6b7fd7;
        border-right: 1px solid #2f3440;
        z-index: 10;
        pointer-events: none;
    }
    .ticker-content-wrapper {
        flex: 1;
        overflow: hidden;
        position: relative;
    }
    .market-ticker {
        background: linear-gradient(135deg, #0e1117 0%, #1a1c24 100%);
        border-bottom: 1px solid #2f3440;
    }
    .market-ticker .ticker-label {
        background: linear-gradient(135deg, #0e1117 0%, #1a1c24 100%);
    }
    .portfolio-ticker {
        background: linear-gradient(135deg, #1a1c24 0%, #0e1117 100%);
        border-bottom: 2px solid #6b7fd7;
        margin-bottom: 20px;
    }
    .portfolio-ticker .ticker-label {
        background: linear-gradient(135deg, #1a1c24 0%, #0e1117 100%);
    }
    .ticker-text {
        display: inline-block;
        white-space: nowrap;
        padding-left: 0;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        font-weight: 700;
        line-height: 1.6;
    }
    
    /* Animasyonlar - Sonsuz döngü, daha hızlı */
    .animate-market { 
        animation: ticker-infinite 40s linear infinite; 
    }
    .animate-portfolio { 
        animation: ticker-infinite 35s linear infinite; 
    }

    @keyframes ticker-infinite {
        0% { transform: translate3d(0, 0, 0); }
        100% { transform: translate3d(-50%, 0, 0); }
    }
    
    /* Sonsuz döngü için içeriği iki kez tekrarla */
    .ticker-text::before {
        content: attr(data-content);
    }

    /* Modern Haber Kartları */
    .news-card {
        background: linear-gradient(135deg, #1a1c24 0%, #0e1117 100%);
        padding: 20px;
        border-radius: 12px;
        border-left: 4px solid #6b7fd7;
        margin-bottom: 15px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }
    .news-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 4px;
        height: 100%;
        background: linear-gradient(180deg, #6b7fd7 0%, #8b9aff 100%);
    }
    .news-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(107, 127, 215, 0.4);
        border-left-color: #8b9aff;
    }
    .news-title {
        font-size: 17px;
        font-weight: 700;
        color: #ffffff;
        text-decoration: none;
        line-height: 1.5;
        display: block;
        margin-bottom: 10px;
        transition: color 0.3s ease;
    }
    .news-title:hover {
        color: #8b9aff;
        text-decoration: none;
    }
    .news-meta {
        font-size: 13px;
        color: #b0b3c0;
        margin-top: 8px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .news-asset-badge {
        display: inline-block;
        background: rgba(107, 127, 215, 0.2);
        color: #8b9aff;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-left: auto;
    }
    .news-source-badge {
        display: inline-block;
        background: rgba(0, 230, 118, 0.2);
        color: #00e676;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 11px;
        font-weight: 700;
        margin-right: 8px;
    }
    .news-source-badge.izleme {
        background: rgba(255, 165, 0, 0.2);
        color: #ffa500;
    }
    a { text-decoration: none !important; }
    a:hover { text-decoration: none !important; }
    
    /* Portföy Haberleri Özel Stil */
    .portfolio-news-header {
        background: linear-gradient(135deg, #232837, #171b24);
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 20px;
        border: 1px solid #2f3440;
    }
    .portfolio-news-header h3 {
        color: #ffffff;
        font-size: 24px;
        font-weight: 900;
        margin-bottom: 10px;
    }
    .portfolio-news-header p {
        color: #b3b7c6;
        font-size: 14px;
        margin: 0;
    }
    .news-filter-container {
        display: flex;
        gap: 10px;
        margin-bottom: 20px;
        flex-wrap: wrap;
    }
    .news-filter-chip {
        background: rgba(107, 127, 215, 0.15);
        color: #8b9aff;
        padding: 8px 16px;
        border-radius: 20px;
        font-size: 13px;
        font-weight: 700;
        cursor: pointer;
        transition: all 0.3s ease;
        border: 1px solid rgba(107, 127, 215, 0.3);
    }
    .news-filter-chip:hover {
        background: rgba(107, 127, 215, 0.25);
        transform: translateY(-2px);
    }
    .news-filter-chip.active {
        background: linear-gradient(135deg, #6b7fd7 0%, #8b9aff 100%);
        color: #ffffff;
        border-color: #8b9aff;
    }

    /* KRAL HEADER */
    .kral-header {
        background: linear-gradient(135deg, #232837, #171b24);
        border-radius: 14px;
        padding: 14px 20px 10px 20px;
        margin-bottom: 14px;
        border: 1px solid #2f3440;
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.35);
    }
    .kral-header-title {
        font-size: 26px;
        font-weight: 900;
        color: #ffffff;
        margin-bottom: 4px;
    }
    .kral-header-sub {
        font-size: 13px;
        color: #b3b7c6;
    }

    /* Mini Info Bar - Genişletilmiş */
    .kral-infobar {
        display: flex;
        gap: 20px;
        flex-wrap: wrap;
        margin-top: 8px;
        margin-bottom: 12px;
        width: 100%;
    }
    .kral-infobox {
        background: rgba(255, 255, 255, 0.02);
        border-radius: 12px;
        padding: 12px 18px;
        border: 1px solid #303542;
        flex: 1;
        min-width: 200px;
        max-width: calc(20% - 16px);
    }
    .kral-infobox-label {
        font-size: 12px;
        color: #b0b3c0;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        font-weight: 700;
    }
    .kral-infobox-value {
        display: block;
        margin-top: 4px;
        font-size: 20px;
        font-weight: 900;
        color: #ffffff;
        line-height: 1.3;
    }
    .kral-infobox-sub {
        font-size: 11px;
        color: #9da1b3;
        margin-top: 4px;
    }
    
    /* Günlük Kazanan/Kaybeden Kartları - Modern ve Dikkat Çekici */
    .daily-movers-section {
        width: 100%;
        margin: 20px 0 40px;
    }
    .daily-movers-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
        gap: 24px;
    }
    .daily-movers-card {
        background: linear-gradient(135deg, #1b1f2b 0%, #10131b 100%);
        border-radius: 20px;
        border: 1px solid #2f3440;
        padding: 24px;
        box-shadow: 0 12px 32px rgba(0, 0, 0, 0.4), 0 0 0 1px rgba(255, 255, 255, 0.05);
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
        overflow: hidden;
    }
    .daily-movers-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 4px;
        background: linear-gradient(90deg, transparent, currentColor, transparent);
        opacity: 0.6;
    }
    .daily-movers-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 16px 40px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(255, 255, 255, 0.08);
    }
    .daily-movers-card.positive-card {
        border-top: 4px solid #00e676;
        color: #00e676;
    }
    .daily-movers-card.positive-card::before {
        background: linear-gradient(90deg, transparent, #00e676, transparent);
    }
    .daily-movers-card.negative-card {
        border-top: 4px solid #ff5252;
        color: #ff5252;
    }
    .daily-movers-card.negative-card::before {
        background: linear-gradient(90deg, transparent, #ff5252, transparent);
    }
    .daily-movers-card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 20px;
        padding-bottom: 16px;
        border-bottom: 2px solid rgba(255, 255, 255, 0.08);
    }
    .daily-movers-card-title {
        font-weight: 900;
        font-size: 20px;
        color: #ffffff;
        display: flex;
        align-items: center;
        gap: 10px;
        letter-spacing: -0.5px;
    }
    .daily-movers-card-title-icon {
        font-size: 24px;
        filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.3));
    }
    .daily-movers-chip {
        background: rgba(255, 255, 255, 0.1);
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 1px;
        color: #b6bad3;
        font-weight: 700;
        border: 1px solid rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
    }
    .daily-movers-card-body {
        display: flex;
        flex-direction: column;
        gap: 12px;
    }
    .daily-mover-row {
        display: grid;
        grid-template-columns: 1fr auto auto;
        align-items: center;
        gap: 16px;
        padding: 16px 18px;
        border-radius: 14px;
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.03) 0%, rgba(255, 255, 255, 0.01) 100%);
        border: 1px solid rgba(255, 255, 255, 0.06);
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }
    .daily-mover-row::before {
        content: '';
        position: absolute;
        left: 0;
        top: 0;
        bottom: 0;
        width: 4px;
        background: currentColor;
        opacity: 0;
        transition: opacity 0.3s ease;
    }
    .daily-mover-row:hover {
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.06) 0%, rgba(255, 255, 255, 0.02) 100%);
        border-color: rgba(255, 255, 255, 0.12);
        transform: translateX(4px);
    }
    .daily-mover-row:hover::before {
        opacity: 1;
    }
    .daily-mover-row.positive {
        border-left: 4px solid rgba(0, 230, 118, 0.8);
        color: #00e676;
    }
    .daily-mover-row.positive::before {
        background: #00e676;
    }
    .daily-mover-row.negative {
        border-left: 4px solid rgba(255, 82, 82, 0.8);
        color: #ff5252;
    }
    .daily-mover-row.negative::before {
        background: #ff5252;
    }
    .daily-mover-symbol {
        font-size: 18px;
        font-weight: 900;
        color: #ffffff;
        letter-spacing: -0.3px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .daily-mover-symbol-badge {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 32px;
        height: 32px;
        border-radius: 8px;
        background: rgba(255, 255, 255, 0.08);
        font-size: 12px;
        font-weight: 800;
        color: #ffffff;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    .daily-mover-change {
        font-size: 17px;
        font-weight: 900;
        letter-spacing: -0.2px;
        text-align: right;
        display: flex;
        align-items: center;
        justify-content: flex-end;
        gap: 6px;
    }
    .daily-mover-change-icon {
        font-size: 14px;
        filter: drop-shadow(0 1px 2px rgba(0, 0, 0, 0.3));
    }
    .daily-mover-row.positive .daily-mover-change {
        color: #00e676;
        text-shadow: 0 0 10px rgba(0, 230, 118, 0.3);
    }
    .daily-mover-row.negative .daily-mover-change {
        color: #ff5252;
        text-shadow: 0 0 10px rgba(255, 82, 82, 0.3);
    }
    .daily-mover-pl {
        font-size: 14px;
        color: #b6bad3;
        font-weight: 700;
        text-align: right;
        letter-spacing: -0.2px;
    }
    .daily-mover-empty {
        font-size: 14px;
        color: #8f93a6;
        text-align: center;
        padding: 24px;
        border-radius: 14px;
        background: rgba(255, 255, 255, 0.03);
        border: 1px dashed rgba(255, 255, 255, 0.1);
        font-weight: 600;
    }
    .daily-movers-table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
    }
    .daily-movers-table thead th {
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.08) 0%, rgba(255, 255, 255, 0.04) 100%);
        color: #b6bad3;
        font-weight: 800;
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 1px;
        padding: 14px 18px;
        text-align: left;
        border-bottom: 2px solid rgba(255, 255, 255, 0.1);
    }
    .daily-movers-table thead th:first-child {
        border-top-left-radius: 12px;
    }
    .daily-movers-table thead th:last-child {
        border-top-right-radius: 12px;
        text-align: right;
    }
    .daily-movers-table tbody td {
        padding: 16px 18px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        font-size: 15px;
        font-weight: 700;
    }
    .daily-movers-table tbody tr:last-child td {
        border-bottom: none;
    }
    .daily-movers-table tbody tr:hover {
        background: rgba(255, 255, 255, 0.03);
    }
    .daily-movers-table tbody td:last-child {
        text-align: right;
    }
    
    /* Modern Navigation Menu Styling */
    div[data-testid="stHorizontalBlock"]:has(> div[data-testid="stHorizontalBlock"]) {
        background: transparent !important;
    }
    
    /* Option Menu Container */
    .stOptionMenu {
        background: transparent !important;
    }
    
    /* Menu item hover effects - Enhanced */
    [data-testid="stHorizontalBlock"] > div > div > div > div > div > a {
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        position: relative !important;
    }
    
    [data-testid="stHorizontalBlock"] > div > div > div > div > div > a:hover {
        transform: translateY(-3px) scale(1.02) !important;
    }
    
    [data-testid="stHorizontalBlock"] > div > div > div > div > div > a[aria-current="page"] {
        animation: pulse-glow 2s ease-in-out infinite !important;
    }
    
    @keyframes pulse-glow {
        0%, 100% {
            box-shadow: 0 6px 20px rgba(107, 127, 215, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.3);
        }
        50% {
            box-shadow: 0 8px 25px rgba(107, 127, 215, 0.7), inset 0 1px 0 rgba(255, 255, 255, 0.4);
        }
    }
    
    /* Icon animations */
    [data-testid="stHorizontalBlock"] > div > div > div > div > div > a:hover i {
        transform: scale(1.1) rotate(5deg) !important;
        transition: all 0.3s ease !important;
    }
    
    [data-testid="stHorizontalBlock"] > div > div > div > div > div > a[aria-current="page"] i {
        animation: icon-bounce 1.5s ease-in-out infinite !important;
    }
    
    @keyframes icon-bounce {
        0%, 100% {
            transform: translateY(0);
        }
        50% {
            transform: translateY(-3px);
        }
    }
    
    /* Mobil Uyumluluk - Responsive Design */
    @media screen and (max-width: 768px) {
        /* Genel ayarlar */
        .block-container {
            padding: 0.5rem !important;
        }
        
        /* Header küçültme */
        .kral-header {
            padding: 10px 12px !important;
            margin-bottom: 10px !important;
        }
        .kral-header-title {
            font-size: 18px !important;
        }
        .kral-header-sub {
            font-size: 11px !important;
        }
        
        /* Ticker küçültme */
        .ticker-container {
            margin-bottom: 12px !important;
        }
        .ticker-label {
            padding: 8px 10px !important;
            font-size: 11px !important;
        }
        .ticker-content-wrapper {
            padding: 8px 0 !important;
        }
        .ticker-text span {
            font-size: 10px !important;
            padding: 2px 6px !important;
            margin: 0 1px !important;
        }
        
        /* Menü mobil uyumlu */
        [data-testid="stHorizontalBlock"] > div > div > div > div > div > a {
            padding: 8px 10px !important;
            font-size: 11px !important;
            margin: 0px 2px !important;
        }
        [data-testid="stHorizontalBlock"] > div > div > div > div > div > a i {
            font-size: 16px !important;
            margin-right: 4px !important;
        }
        
        /* Info kartları tek sütun */
        .kral-infobar {
            flex-direction: column !important;
            gap: 10px !important;
        }
        .kral-infobox {
            min-width: 100% !important;
            max-width: 100% !important;
            padding: 10px 14px !important;
        }
        .kral-infobox-value {
            font-size: 18px !important;
        }
        .kral-infobox-label {
            font-size: 10px !important;
        }
        
        /* Metric kutuları */
        div[data-testid="stMetric"] {
            padding: 10px !important;
        }
        div[data-testid="stMetricValue"] {
            font-size: 20px !important;
        }
        div[data-testid="stMetricLabel"] {
            font-size: 12px !important;
        }
        
        /* Tablolar */
        .styled-table th {
            font-size: 14px !important;
            padding: 8px 4px !important;
        }
        .styled-table td {
            font-size: 12px !important;
            padding: 8px 4px !important;
        }
        
        /* Subheader'lar */
        h2, h3 {
            font-size: 18px !important;
        }
        
        /* Radio butonlar */
        div[data-testid="stRadio"] {
            font-size: 12px !important;
        }
        
        /* Tabs */
        button[data-baseweb="tab"] {
            font-size: 12px !important;
            padding: 8px 12px !important;
        }
        
        /* İzleme listesi kolonları */
        [data-testid="column"] {
            padding: 0.25rem !important;
        }
        
        /* Haber kartları */
        .news-card {
            padding: 10px !important;
        }
        .news-title {
            font-size: 14px !important;
        }
        
        /* Plotly grafikleri - mobilde tablolarla karışmasın */
        .js-plotly-plot {
            height: 300px !important;
            margin-bottom: 30px !important;
            padding-bottom: 20px !important;
        }
        
        /* Plotly container'ları */
        div[data-testid="stPlotlyChart"] {
            margin-bottom: 30px !important;
            padding-bottom: 20px !important;
        }
        
        /* Treemap ve pasta grafikleri için özel spacing */
        div[data-testid="stPlotlyChart"]:has(svg) {
            margin-bottom: 40px !important;
            padding-bottom: 25px !important;
        }
        
        /* Treemap içindeki text boyutları mobilde küçült */
        .js-plotly-plot text,
        .js-plotly-plot .treemap-label,
        .js-plotly-plot .treemap-value,
        .js-plotly-plot .treemap-pct {
            font-size: 12px !important;
        }
        
        /* Treemap yüksekliği mobilde küçült */
        div[data-testid="stPlotlyChart"] .js-plotly-plot {
            height: 400px !important;
            max-height: 400px !important;
        }
        
        /* Donut chart ve pie chart için mobil optimizasyon */
        .js-plotly-plot .pie {
            transform: scale(0.9) !important;
        }
        
        /* Grafik container'ları mobilde daha kompakt */
        div[data-testid="stPlotlyChart"] {
            max-height: 450px !important;
            overflow: hidden !important;
        }
        
        /* Treemap içindeki tspan elementleri mobilde küçült */
        .js-plotly-plot tspan {
            font-size: 11px !important;
        }
        
        /* Tabloların üstünde boşluk */
        div[data-testid="stDataFrame"] {
            margin-top: 20px !important;
            padding-top: 15px !important;
        }
        
        /* Subheader'dan sonra boşluk */
        h2, h3 {
            margin-bottom: 15px !important;
        }
        
        /* Element'ler arası genel boşluk */
        .element-container {
            margin-bottom: 20px !important;
        }
        
        /* Streamlit column'lar arası boşluk */
        [data-testid="column"] {
            margin-bottom: 20px !important;
        }
    }
    
    /* Çok küçük ekranlar (telefon) */
    @media screen and (max-width: 480px) {
        .kral-header-title {
            font-size: 16px !important;
        }
        .kral-header-sub {
            font-size: 10px !important;
        }
        
        [data-testid="stHorizontalBlock"] > div > div > div > div > div > a {
            padding: 6px 8px !important;
            font-size: 10px !important;
        }
        [data-testid="stHorizontalBlock"] > div > div > div > div > div > a i {
            font-size: 14px !important;
            margin-right: 3px !important;
        }
        
        .ticker-label {
            padding: 6px 8px !important;
            font-size: 10px !important;
        }
        .ticker-content-wrapper {
            padding: 6px 0 !important;
        }
        .ticker-text span {
            font-size: 9px !important;
            padding: 2px 4px !important;
        }
        
        .kral-infobox-value {
            font-size: 16px !important;
        }
        
        div[data-testid="stMetricValue"] {
            font-size: 18px !important;
        }
        
        h2, h3 {
            font-size: 16px !important;
            margin-bottom: 15px !important;
        }
        
        /* Küçük ekranlarda grafikler için daha fazla boşluk */
        .js-plotly-plot {
            margin-bottom: 35px !important;
            padding-bottom: 25px !important;
            height: 350px !important;
            max-height: 350px !important;
        }
        
        div[data-testid="stPlotlyChart"] {
            margin-bottom: 35px !important;
            padding-bottom: 25px !important;
            max-height: 400px !important;
        }
        
        div[data-testid="stPlotlyChart"] .js-plotly-plot {
            height: 350px !important;
            max-height: 350px !important;
        }
        
        div[data-testid="stDataFrame"] {
            margin-top: 25px !important;
            padding-top: 20px !important;
        }
        
        /* Donut chart font boyutları küçük ekranlarda */
        .js-plotly-plot text[class*="annotation"] {
            font-size: 10px !important;
        }
    }
</style>
""",
    unsafe_allow_html=True,
)

LIGHT_OVERRIDE_CSS = """
<style>
    :root {
        color-scheme: light;
    }
    html, body, [data-testid="stAppViewContainer"], [data-testid="stAppBody"] {
        background-color: #f5f7fb !important;
        color: #1f2937 !important;
    }
    .kral-header {
        background: linear-gradient(135deg, #ffffff, #edf1fb);
        border: 1px solid #d5d9ea;
        box-shadow: 0 10px 25px rgba(15, 23, 42, 0.08);
    }
    .kral-header-title {
        color: #111827;
    }
    .kral-header-sub {
        color: #4b5563;
    }
    .ticker-container {
        background: linear-gradient(135deg, #ffffff 0%, #e8edfb 100%);
        border-bottom: 1px solid #d5d9ea;
        box-shadow: 0 2px 12px rgba(15, 23, 42, 0.08);
    }
    .ticker-label {
        background: linear-gradient(135deg, #f8faff 0%, #eef2ff 100%);
        color: #405bbb;
        border-right: 1px solid #d5d9ea;
    }
    .ticker-text span {
        color: #111827 !important;
    }
    .kral-infobox {
        background: #ffffff;
        border: 1px solid #e5e7eb;
    }
    .kral-infobox-label,
    .kral-infobox-sub {
        color: #4b5563;
    }
    .kral-infobox-value {
        color: #111827;
    }
    div[data-testid="stMetric"] {
        background-color: #ffffff !important;
        border: 1px solid #e5e7eb !important;
        color: #111827 !important;
        box-shadow: 0 4px 12px rgba(15, 23, 42, 0.06);
    }
    div[data-testid="stMetricValue"],
    div[data-testid="stMetricLabel"] {
        color: #111827 !important;
    }
    .news-card {
        background: linear-gradient(135deg, #ffffff 0%, #f8faff 100%);
        color: #1f2937;
        border-left-color: #6b7fd7;
        box-shadow: 0 4px 12px rgba(15, 23, 42, 0.08);
    }
    .news-card::before {
        background: linear-gradient(180deg, #6b7fd7 0%, #8b9aff 100%);
    }
    .news-title {
        color: #111827;
    }
    .news-title:hover {
        color: #405bbb;
    }
    .news-meta {
        color: #4b5563;
    }
    .news-asset-badge {
        background: rgba(64, 91, 187, 0.15);
        color: #405bbb;
    }
    .news-source-badge {
        background: rgba(34, 197, 94, 0.15);
        color: #22c55e;
    }
    .news-source-badge.izleme {
        background: rgba(249, 115, 22, 0.15);
        color: #f97316;
    }
    .portfolio-news-header {
        background: linear-gradient(135deg, #ffffff, #edf1fb);
        border: 1px solid #d5d9ea;
    }
    .portfolio-news-header h3 {
        color: #111827;
    }
    .portfolio-news-header p {
        color: #4b5563;
    }
    .news-filter-chip {
        background: rgba(64, 91, 187, 0.1);
        color: #405bbb;
        border: 1px solid rgba(64, 91, 187, 0.2);
    }
    .news-filter-chip:hover {
        background: rgba(64, 91, 187, 0.15);
    }
    .news-filter-chip.active {
        background: linear-gradient(135deg, #6b7fd7 0%, #8b9aff 100%);
        color: #ffffff;
    }
</style>
"""

if st.session_state["ui_theme"] == "light":
    st.markdown(LIGHT_OVERRIDE_CSS, unsafe_allow_html=True)

def get_menu_styles(theme: str):
    if theme == "light":
        return {
            "container": {
                "padding": "0!important",
                "background": "linear-gradient(135deg, #ffffff 0%, #eef2ff 100%)",
                "border-radius": "12px",
                "box-shadow": "0 4px 20px rgba(15, 23, 42, 0.08)",
                "margin-bottom": "20px",
            },
            "icon": {
                "color": "#405bbb",
                "font-size": "20px",
                "margin-right": "8px",
            },
            "nav-link": {
                "font-size": "15px",
                "text-align": "center",
                "margin": "0px 4px",
                "padding": "12px 20px",
                "border-radius": "10px",
                "font-weight": "700",
                "color": "#4b5563",
                "transition": "all 0.3s ease",
                "background": "transparent",
            },
            "nav-link:hover": {
                "background": "rgba(64, 91, 187, 0.12)",
                "color": "#405bbb",
                "transform": "translateY(-2px)",
            },
            "nav-link-selected": {
                "background": "linear-gradient(135deg, #6b7fd7 0%, #8b9aff 100%)",
                "color": "#ffffff",
                "box-shadow": "0 4px 15px rgba(107, 127, 215, 0.35)",
                "font-weight": "900",
                "border": "none",
            },
        }
    return {
        "container": {
            "padding": "0!important",
            "background": "linear-gradient(135deg, #1a1c24 0%, #0e1117 100%)",
            "border-radius": "12px",
            "box-shadow": "0 4px 20px rgba(0, 0, 0, 0.4)",
            "margin-bottom": "20px",
        },
        "icon": {
            "color": "#8b9aff",
            "font-size": "20px",
            "margin-right": "8px",
        },
        "nav-link": {
            "font-size": "15px",
            "text-align": "center",
            "margin": "0px 4px",
            "padding": "12px 20px",
            "border-radius": "10px",
            "font-weight": "700",
            "color": "#b0b3c0",
            "transition": "all 0.3s ease",
            "background": "transparent",
        },
        "nav-link:hover": {
            "background": "rgba(139, 154, 255, 0.1)",
            "color": "#8b9aff",
            "transform": "translateY(-2px)",
        },
        "nav-link-selected": {
            "background": "linear-gradient(135deg, #6b7fd7 0%, #8b9aff 100%)",
            "color": "#ffffff",
            "box-shadow": "0 4px 15px rgba(107, 127, 215, 0.4)",
            "font-weight": "900",
            "border": "none",
        },
    }

# --- HABER UI ---
def render_news_section(name, key):
    st.markdown(f'<div style="margin-bottom: 20px;"><h2 style="color: #ffffff; font-size: 28px; font-weight: 900; margin-bottom: 5px;">📰 {name}</h2></div>', unsafe_allow_html=True)
    news = get_financial_news(key)
    if news:
        for n in news:
            # Tarihi formatla
            try:
                from datetime import datetime
                date_obj = datetime.strptime(n['date'][:25], '%a, %d %b %Y %H:%M:%S')
                formatted_date = date_obj.strftime('%d %b %Y, %H:%M')
            except:
                formatted_date = n['date']
            
            st.markdown(
                f"""
                <div class="news-card">
                    <a href="{n['link']}" target="_blank" class="news-title">
                        {n['title']}
                    </a>
                    <div class="news-meta">
                        <span>🕒 {formatted_date}</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.info("Haber akışı yüklenemedi.")

def render_portfolio_news_section(portfolio_df, watchlist_df=None):
    """Portföy haberleri için özel render fonksiyonu"""
    st.markdown(
        """
        <div class="portfolio-news-header">
            <h3>💼 Portföy Haberleri</h3>
            <p>Portföyünüzdeki ve izleme listesindeki varlıklar için güncel haberler ve güncellemeler</p>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Haberleri çek
    all_news = get_portfolio_news(portfolio_df, watchlist_df)
    
    if not all_news:
        st.info("Portföy haberleri yüklenemedi veya portföyde varlık bulunmuyor.")
        return
    
    # Varlık filtreleme için benzersiz varlıkları al
    unique_assets = sorted(set([n.get("asset", "") for n in all_news if n.get("asset")]))
    unique_sources = sorted(set([n.get("source", "") for n in all_news if n.get("source")]))
    
    # Filtreleme seçenekleri
    col1, col2 = st.columns([3, 1])
    with col1:
        selected_asset = st.selectbox(
            "Varlığa Göre Filtrele",
            ["Tümü"] + unique_assets,
            key="portfolio_news_asset_filter"
        )
    with col2:
        selected_source = st.selectbox(
            "Kaynağa Göre Filtrele",
            ["Tümü"] + unique_sources,
            key="portfolio_news_source_filter"
        )
    
    # Filtreleme uygula
    filtered_news = all_news
    if selected_asset != "Tümü":
        filtered_news = [n for n in filtered_news if n.get("asset") == selected_asset]
    if selected_source != "Tümü":
        filtered_news = [n for n in filtered_news if n.get("source") == selected_source]
    
    # Filtreleme sonrası tarihe göre tekrar sırala (en yeni önce)
    try:
        from datetime import datetime
        def parse_date_for_sort(date_str):
            """Tarih string'ini parse edip sıralama için kullanılabilir hale getirir"""
            try:
                # RFC 2822 formatını dene
                return datetime.strptime(date_str[:25], '%a, %d %b %Y %H:%M:%S')
            except:
                try:
                    # ISO formatını dene
                    return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                except:
                    # Parse edilemezse string olarak kullan
                    return date_str
        filtered_news.sort(key=lambda x: parse_date_for_sort(x.get("date", "")), reverse=True)
    except Exception:
        # Hata durumunda string sıralaması yap
        try:
            filtered_news.sort(key=lambda x: x.get("date", ""), reverse=True)
        except:
            pass
    
    if not filtered_news:
        st.info("Seçilen filtreler için haber bulunamadı.")
        return
    
    # Haberleri göster
    st.markdown(f'<div style="margin-top: 20px; margin-bottom: 10px;"><p style="color: #b0b3c0; font-size: 14px;">Toplam <strong style="color: #8b9aff;">{len(filtered_news)}</strong> haber bulundu</p></div>', unsafe_allow_html=True)
    
    for n in filtered_news:
        # Tarihi formatla
        try:
            from datetime import datetime
            date_obj = datetime.strptime(n['date'][:25], '%a, %d %b %Y %H:%M:%S')
            formatted_date = date_obj.strftime('%d %b %Y, %H:%M')
        except:
            formatted_date = n['date']
        
        asset = n.get("asset", "Bilinmiyor")
        source = n.get("source", "Portföy")
        source_class = "izleme" if source == "İzleme" else ""
        
        st.markdown(
            f"""
            <div class="news-card">
                <a href="{n['link']}" target="_blank" class="news-title">
                    {n['title']}
                </a>
                <div class="news-meta">
                    <span class="news-source-badge {source_class}">{source}</span>
                    <span>🕒 {formatted_date}</span>
                    <span class="news-asset-badge">{asset}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# --- ANA DATA ---
portfoy_df = get_data_from_sheet()

# --- HEADER ---
USD_TRY = get_usd_try()

# Para birimi seçimi için session state
if "gorunum_pb" not in st.session_state:
    st.session_state["gorunum_pb"] = "TRY"

GORUNUM_PB = st.session_state["gorunum_pb"]
sym = "₺" if GORUNUM_PB == "TRY" else "$"

# Header - Başlık
with st.container():
    st.markdown('<div class="kral-header">', unsafe_allow_html=True)
    c_title, c_toggle = st.columns([3, 1])
    with c_title:
        st.markdown(
            "<div class='kral-header-title'>🏦 MERTER VARLIK TAKİP BOTU</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<div class='kral-header-sub'>Toplam portföyünü tek ekranda izlemek için kişisel kontrol panelin.</div>",
            unsafe_allow_html=True,
        )
    with c_toggle:
        st.write("")
        GORUNUM_PB = st.radio("Para Birimi:", ["TRY", "USD"], horizontal=True, key="pb_radio")
        if GORUNUM_PB != st.session_state.get("gorunum_pb"):
            st.session_state["gorunum_pb"] = GORUNUM_PB
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

mh, ph = get_tickers_data(portfoy_df, USD_TRY)
st.markdown(
    f"""
<div class="ticker-container market-ticker">
    <div class="ticker-label">🌍 PİYASA</div>
    <div class="ticker-content-wrapper">{mh}</div>
</div>
<div class="ticker-container portfolio-ticker">
    <div class="ticker-label">💼 PORTFÖY</div>
    <div class="ticker-content-wrapper">{ph}</div>
</div>
""",
    unsafe_allow_html=True,
)

# --- MENÜ (6 Buton) - Modern ---
selected = option_menu(
    menu_title=None,
    options=[
        "Dashboard",
        "Portföy",
        "İzleme",
        "Satışlar",
        "Haberler",
        "Ekle/Çıkar",
    ],
    icons=[
        "speedometer2",
        "pie-chart-fill",
        "eye",
        "receipt",
        "newspaper",
        "gear",
    ],
    menu_icon="cast",
    default_index=0,
    orientation="horizontal",
    styles=get_menu_styles(st.session_state["ui_theme"]),
)


# --- ANALİZ ---
@st.cache_data(ttl=300)  # 5 dakika cache - BIST ve ABD için
def _fetch_batch_prices_bist_abd(symbols_list, period="5d"):
    """Batch olarak BIST ve ABD fiyat verilerini çeker - borsa kapalıyken de son kapanış fiyatını döndürür"""
    if not symbols_list:
        return {}
    prices = {}
    
    # Önce batch deneme
    try:
        tickers = yf.Tickers(" ".join(symbols_list))
        for sym in symbols_list:
            try:
                h = tickers.tickers[sym].history(period=period)
                if not h.empty:
                    # Son geçerli fiyatı al (borsa kapalıysa son kapanış)
                    curr = h["Close"].iloc[-1]
                    # Önceki günü bul (eğer bugün veri yoksa, son iki günden birini al)
                    if len(h) > 1:
                        prev = h["Close"].iloc[-2]
                    else:
                        prev = curr
                    prices[sym] = {"curr": curr, "prev": prev}
                else:
                    # Eğer period="2d" ile veri yoksa, daha uzun period dene
                    h_longer = tickers.tickers[sym].history(period="5d")
                    if not h_longer.empty:
                        curr = h_longer["Close"].iloc[-1]
                        prev = h_longer["Close"].iloc[-2] if len(h_longer) > 1 else curr
                        prices[sym] = {"curr": curr, "prev": prev}
                    else:
                        prices[sym] = {"curr": 0, "prev": 0}
            except Exception as e:
                # Batch başarısız olursa, tek tek dene
                try:
                    ticker = yf.Ticker(sym)
                    h = ticker.history(period="5d")
                    if not h.empty:
                        curr = h["Close"].iloc[-1]
                        prev = h["Close"].iloc[-2] if len(h) > 1 else curr
                        prices[sym] = {"curr": curr, "prev": prev}
                    else:
                        prices[sym] = {"curr": 0, "prev": 0}
                except Exception:
                    prices[sym] = {"curr": 0, "prev": 0}
    except Exception:
        # Batch tamamen başarısız olursa, her sembolü tek tek çek
        for sym in symbols_list:
            try:
                ticker = yf.Ticker(sym)
                h = ticker.history(period="5d")
                if not h.empty:
                    curr = h["Close"].iloc[-1]
                    prev = h["Close"].iloc[-2] if len(h) > 1 else curr
                    prices[sym] = {"curr": curr, "prev": prev}
                else:
                    prices[sym] = {"curr": 0, "prev": 0}
            except Exception:
                prices[sym] = {"curr": 0, "prev": 0}
    
    return prices

@st.cache_data(ttl=120)  # 2 dakika cache - Kripto için
def _fetch_batch_prices_crypto(symbols_list, period="5d"):
    """Batch olarak Kripto fiyat verilerini çeker"""
    if not symbols_list:
        return {}
    prices = {}
    
    try:
        tickers = yf.Tickers(" ".join(symbols_list))
        for sym in symbols_list:
            try:
                h = tickers.tickers[sym].history(period=period)
                if not h.empty:
                    curr = h["Close"].iloc[-1]
                    prev = h["Close"].iloc[-2] if len(h) > 1 else curr
                    prices[sym] = {"curr": curr, "prev": prev}
                else:
                    prices[sym] = {"curr": 0, "prev": 0}
            except Exception:
                try:
                    ticker = yf.Ticker(sym)
                    h = ticker.history(period=period)
                    if not h.empty:
                        curr = h["Close"].iloc[-1]
                        prev = h["Close"].iloc[-2] if len(h) > 1 else curr
                        prices[sym] = {"curr": curr, "prev": prev}
                    else:
                        prices[sym] = {"curr": 0, "prev": 0}
                except Exception:
                    prices[sym] = {"curr": 0, "prev": 0}
    except Exception:
        for sym in symbols_list:
            try:
                ticker = yf.Ticker(sym)
                h = ticker.history(period=period)
                if not h.empty:
                    curr = h["Close"].iloc[-1]
                    prev = h["Close"].iloc[-2] if len(h) > 1 else curr
                    prices[sym] = {"curr": curr, "prev": prev}
                else:
                    prices[sym] = {"curr": 0, "prev": 0}
            except Exception:
                prices[sym] = {"curr": 0, "prev": 0}
    
    return prices

@st.cache_data(ttl=300)  # 5 dakika cache - EMTIA için
def _fetch_batch_prices_emtia(symbols_list, period="5d"):
    """Batch olarak EMTIA fiyat verilerini çeker"""
    if not symbols_list:
        return {}
    prices = {}
    
    try:
        tickers = yf.Tickers(" ".join(symbols_list))
        for sym in symbols_list:
            try:
                h = tickers.tickers[sym].history(period=period)
                if not h.empty:
                    curr = h["Close"].iloc[-1]
                    prev = h["Close"].iloc[-2] if len(h) > 1 else curr
                    prices[sym] = {"curr": curr, "prev": prev}
                else:
                    prices[sym] = {"curr": 0, "prev": 0}
            except Exception:
                try:
                    ticker = yf.Ticker(sym)
                    h = ticker.history(period=period)
                    if not h.empty:
                        curr = h["Close"].iloc[-1]
                        prev = h["Close"].iloc[-2] if len(h) > 1 else curr
                        prices[sym] = {"curr": curr, "prev": prev}
                    else:
                        prices[sym] = {"curr": 0, "prev": 0}
                except Exception:
                    prices[sym] = {"curr": 0, "prev": 0}
    except Exception:
        for sym in symbols_list:
            try:
                ticker = yf.Ticker(sym)
                h = ticker.history(period=period)
                if not h.empty:
                    curr = h["Close"].iloc[-1]
                    prev = h["Close"].iloc[-2] if len(h) > 1 else curr
                    prices[sym] = {"curr": curr, "prev": prev}
                else:
                    prices[sym] = {"curr": 0, "prev": 0}
            except Exception:
                prices[sym] = {"curr": 0, "prev": 0}
    
    return prices

def _translate_sector(sector_en):
    """İngilizce sektör isimlerini Türkçe'ye çevirir"""
    sector_map = {
        "Technology": "Teknoloji",
        "Financial Services": "Finansal Hizmetler",
        "Healthcare": "Sağlık",
        "Consumer Cyclical": "Tüketim (Döngüsel)",
        "Consumer Defensive": "Tüketim (Savunmacı)",
        "Energy": "Enerji",
        "Industrials": "Sanayi",
        "Basic Materials": "Temel Malzemeler",
        "Real Estate": "Gayrimenkul",
        "Communication Services": "İletişim Hizmetleri",
        "Utilities": "Kamu Hizmetleri",
        "Consumer Staples": "Tüketim Malları",
        "Consumer Discretionary": "Tüketim (İsteğe Bağlı)",
        "Materials": "Malzemeler",
        "Information Technology": "Bilgi Teknolojisi",
        "Financials": "Finans",
        "Health Care": "Sağlık",
        "Consumer Services": "Tüketim Hizmetleri",
        "Telecommunications": "Telekomünikasyon",
        "Real Estate Investment Trusts": "Gayrimenkul Yatırım Ortaklıkları",
        "REIT": "Gayrimenkul Yatırım Ortaklıkları",
    }
    return sector_map.get(sector_en, sector_en)  # Eğer çeviri yoksa orijinal ismi döndür

@st.cache_data(ttl=300)
def _fetch_sector_info(symbols_list):
    """Batch olarak sektör bilgilerini çeker"""
    if not symbols_list:
        return {}
    sectors = {}
    try:
        tickers = yf.Tickers(" ".join(symbols_list))
        for sym in symbols_list:
            try:
                info = tickers.tickers[sym].info
                sector_en = info.get("sector", "Bilinmiyor")
                # Türkçe'ye çevir
                sectors[sym] = _translate_sector(sector_en) if sector_en != "Bilinmiyor" else "Bilinmiyor"
            except Exception:
                sectors[sym] = "Bilinmiyor"
    except Exception:
        pass
    return sectors

def run_analysis(df, usd_try_rate, view_currency):
    if df.empty:
        return pd.DataFrame(columns=ANALYSIS_COLS)

    # DataFrame'i kopyala ve normalize et
    df_work = df.copy()
    df_work["Kod"] = df_work["Kod"].astype(str)
    df_work["Pazar"] = df_work["Pazar"].astype(str)
    
    # Pazar normalizasyonu (vectorized)
    df_work.loc[df_work["Kod"].isin(KNOWN_FUNDS), "Pazar"] = "FON"
    df_work.loc[df_work["Pazar"].str.upper().str.contains("FIZIKI", na=False), "Pazar"] = "EMTIA"
    
    # Boş kodları filtrele
    df_work = df_work[df_work["Kod"].str.strip() != ""].copy()
    
    if df_work.empty:
        return pd.DataFrame(columns=ANALYSIS_COLS)

    # Adet ve Maliyet parse (vectorized)
    df_work["Adet"] = df_work["Adet"].apply(smart_parse)
    df_work["Maliyet"] = df_work["Maliyet"].apply(smart_parse)
    
    # Symbol mapping
    df_work["Symbol"] = df_work.apply(lambda row: get_yahoo_symbol(row["Kod"], row["Pazar"]), axis=1)
    
    # Asset currency belirleme (vectorized)
    df_work["AssetCurrency"] = df_work.apply(
        lambda row: "TRY" if (
            "BIST" in row["Pazar"] or "TL" in str(row["Kod"]) or 
            "FON" in row["Pazar"] or "EMTIA" in row["Pazar"] or "NAKIT" in row["Pazar"]
        ) else "USD",
        axis=1
    )
    
    # Sektör belirleme
    df_work["Sektör"] = ""
    bist_abd_mask = df_work["Pazar"].str.contains("BIST|ABD", case=False, na=False)
    df_work.loc[df_work["Pazar"].str.contains("FON", case=False, na=False), "Sektör"] = "Yatırım Fonu"
    df_work.loc[df_work["Pazar"].str.contains("NAKIT", case=False, na=False), "Sektör"] = "Nakit Varlık"
    df_work.loc[df_work["Pazar"].str.contains("EMTIA", case=False, na=False), "Sektör"] = "Emtia"
    
    # Batch sektör bilgisi çekme
    if bist_abd_mask.any():
        sector_symbols = df_work[bist_abd_mask]["Symbol"].unique().tolist()
        sector_info = _fetch_sector_info(sector_symbols)
        df_work.loc[bist_abd_mask, "Sektör"] = df_work[bist_abd_mask]["Symbol"].map(sector_info).fillna("Bilinmiyor")
    
    # Fiyat verilerini batch olarak çek - varlık türüne göre ayrı cache
    bist_abd_symbols = []
    crypto_symbols = []
    emtia_symbols = []
    symbol_map = {}  # idx -> (symbol, asset_type) mapping
    
    for idx, row in df_work.iterrows():
        kod = row["Kod"]
        pazar = row["Pazar"]
        symbol = row["Symbol"]
        
        if "NAKIT" in pazar.upper():
            continue  # Nakitler özel işlenecek
        elif "FON" in pazar:
            continue  # Fonlar TEFAS'tan çekilecek, Yahoo Finance'ten değil
        elif "Gram Gümüş" in kod or "GRAM GÜMÜŞ" in kod:
            if "SI=F" not in emtia_symbols:
                emtia_symbols.append("SI=F")
            symbol_map[idx] = ("SI=F", "EMTIA")
        elif "Gram Altın" in kod or "GRAM ALTIN" in kod:
            if "GC=F" not in emtia_symbols:
                emtia_symbols.append("GC=F")
            symbol_map[idx] = ("GC=F", "EMTIA")
        elif "KRIPTO" in pazar.upper():
            if symbol not in crypto_symbols:
                crypto_symbols.append(symbol)
            symbol_map[idx] = (symbol, "KRIPTO")
        elif "BIST" in pazar.upper() or "ABD" in pazar.upper():
            if symbol not in bist_abd_symbols:
                bist_abd_symbols.append(symbol)
            symbol_map[idx] = (symbol, "BIST_ABD")
        elif "EMTIA" in pazar.upper():
            if symbol not in emtia_symbols:
                emtia_symbols.append(symbol)
            symbol_map[idx] = (symbol, "EMTIA")
        else:
            # Varsayılan olarak BIST/ABD gibi işle
            if symbol not in bist_abd_symbols:
                bist_abd_symbols.append(symbol)
            symbol_map[idx] = (symbol, "BIST_ABD")
    
    # Varlık türüne göre farklı cache süreleri ile fiyat çekme
    batch_prices = {}
    
    # BIST ve ABD: 5 dakika cache, borsa kapalıyken de çalışır
    if bist_abd_symbols:
        bist_abd_prices = _fetch_batch_prices_bist_abd(bist_abd_symbols, period="5d")
        batch_prices.update(bist_abd_prices)
    
    # Kripto: 2 dakika cache
    if crypto_symbols:
        crypto_prices = _fetch_batch_prices_crypto(crypto_symbols, period="5d")
        batch_prices.update(crypto_prices)
    
    # EMTIA: 5 dakika cache
    gram_prices_5d = {}
    if emtia_symbols:
        emtia_prices = _fetch_batch_prices_emtia(emtia_symbols, period="5d")
        batch_prices.update(emtia_prices)
        # Gram altın/gümüş için özel mapping
        if "SI=F" in emtia_prices:
            gram_prices_5d["SI=F"] = emtia_prices["SI=F"]
        if "GC=F" in emtia_prices:
            gram_prices_5d["GC=F"] = emtia_prices["GC=F"]
    
    # EURTRY için özel - borsa kapalıyken de çalışması için period artır
    eurtry_price = None
    if (df_work["Pazar"].str.contains("NAKIT", case=False, na=False) & 
        (df_work["Kod"] == "EUR")).any():
        try:
            ticker = yf.Ticker("EURTRY=X")
            h = ticker.history(period="5d")
            if not h.empty:
                eurtry_price = h["Close"].iloc[-1]
            else:
                eurtry_price = 36.0
        except Exception:
            try:
                # Fallback: daha uzun period dene
                ticker = yf.Ticker("EURTRY=X")
                h = ticker.history(period="1mo")
                if not h.empty:
                    eurtry_price = h["Close"].iloc[-1]
                else:
                    eurtry_price = 36.0
            except Exception:
                eurtry_price = 36.0
    
    # Fiyatları hesapla
    results = []
    for idx, row in df_work.iterrows():
        kod = row["Kod"]
        pazar = row["Pazar"]
        tip = row["Tip"]
        adet = row["Adet"]
        maliyet = row["Maliyet"]
        asset_currency = row["AssetCurrency"]
        sector = row["Sektör"]
        symbol = row["Symbol"]

        curr, prev = 0, 0

        try:
            if "NAKIT" in pazar.upper():
                if kod == "TL":
                    curr = 1
                elif kod == "USD":
                    curr = usd_try_rate
                elif kod == "EUR":
                    curr = eurtry_price if eurtry_price else 36.0
                prev = curr
            elif "FON" in pazar:
                # TEFAS fon fiyatını çek - kesinlikle TEFAS'tan, başka kaynaktan değil
                curr, prev = get_tefas_data(kod)
                
                # Fiyat validasyonu ve düzeltme
                if curr == 0:
                    # TEFAS'tan fiyat çekilemedi - maliyet kullan
                    curr = maliyet if maliyet > 0 else 0
                    prev = curr
                elif curr > 100:  # Çok yüksek fiyat - muhtemelen yanlış (TEFAS fonları genelde 0.01-50 TL arası)
                    # Şüpheli fiyat - cache'i temizle ve tekrar dene
                    try:
                        # Bu fon için cache'i temizle
                        get_tefas_data.clear()
                        curr_new, prev_new = get_tefas_data(kod)
                        if curr_new > 0 and curr_new < 100:  # Makul aralıkta ise kullan
                            curr = curr_new
                            prev = prev_new
                        else:
                            # Hala sorun varsa maliyet kullan
                            curr = maliyet if maliyet > 0 else curr
                            prev = curr
                    except Exception:
                        # Hata olursa maliyet kullan
                        curr = maliyet if maliyet > 0 else curr
                        prev = curr
                elif maliyet > 0 and curr > 0:
                    # Fiyat maliyetten çok farklıysa kontrol et
                    ratio = abs(curr - maliyet) / maliyet
                    if ratio > 10 and curr > 10:  # %1000'den fazla farklı VE yüksekse şüpheli
                        # Cache'i temizle ve tekrar dene
                        try:
                            get_tefas_data.clear()
                            curr_new, prev_new = get_tefas_data(kod)
                            if curr_new > 0 and curr_new < 100 and abs(curr_new - maliyet) / maliyet < 10:
                                curr = curr_new
                                prev = prev_new
                        except Exception:
                            pass
            elif "Gram Gümüş" in kod or "GRAM GÜMÜŞ" in kod:
                if "SI=F" in gram_prices_5d:
                    p_data = gram_prices_5d["SI=F"]
                    curr = (p_data["curr"] * usd_try_rate) / 31.1035
                    prev = (p_data["prev"] * usd_try_rate) / 31.1035
            elif "Gram Altın" in kod or "GRAM ALTIN" in kod:
                if "GC=F" in gram_prices_5d:
                    p_data = gram_prices_5d["GC=F"]
                    curr = (p_data["curr"] * usd_try_rate) / 31.1035
                    prev = (p_data["prev"] * usd_try_rate) / 31.1035
            else:
                if idx in symbol_map:
                    sym_key, asset_type = symbol_map[idx]
                    if sym_key in batch_prices:
                        p_data = batch_prices[sym_key]
                        curr = p_data["curr"]
                        prev = p_data["prev"]
                    else:
                        # Batch'te yoksa, tek tek dene (borsa kapalıyken fallback)
                        try:
                            ticker = yf.Ticker(sym_key)
                            h = ticker.history(period="5d")
                            if not h.empty:
                                curr = h["Close"].iloc[-1]
                                prev = h["Close"].iloc[-2] if len(h) > 1 else curr
                            else:
                                # Daha uzun period dene
                                h = ticker.history(period="1mo")
                                if not h.empty:
                                    curr = h["Close"].iloc[-1]
                                    prev = h["Close"].iloc[-2] if len(h) > 1 else curr
                                else:
                                    curr = 0
                                    prev = 0
                        except Exception:
                            curr = 0
                            prev = 0
                else:
                    # Symbol map'te yoksa, direkt sembol ile dene
                    try:
                        ticker = yf.Ticker(symbol)
                        h = ticker.history(period="5d")
                        if not h.empty:
                            curr = h["Close"].iloc[-1]
                            prev = h["Close"].iloc[-2] if len(h) > 1 else curr
                        else:
                            # Daha uzun period dene
                            h = ticker.history(period="1mo")
                            if not h.empty:
                                curr = h["Close"].iloc[-1]
                                prev = h["Close"].iloc[-2] if len(h) > 1 else curr
                            else:
                                curr = 0
                                prev = 0
                    except Exception:
                        curr = 0
                        prev = 0
        except Exception:
            pass

        # Eğer hala fiyat yoksa, maliyet kullan (ama önce bir daha dene)
        if curr == 0:
            # Son bir deneme - daha uzun period ile
            try:
                if symbol and symbol not in ["TL", "USD", "EUR"]:
                    ticker = yf.Ticker(symbol)
                    h = ticker.history(period="1mo")
                    if not h.empty:
                        curr = h["Close"].iloc[-1]
                        prev = h["Close"].iloc[-2] if len(h) > 1 else curr
                    else:
                        curr = maliyet
                        prev = maliyet
                else:
                    curr = maliyet
                    prev = maliyet
            except Exception:
                curr = maliyet
                prev = maliyet
        
        if prev == 0:
            prev = curr
        if curr > 0 and maliyet > 0 and (maliyet / curr) > 50:
            maliyet /= 100

        val_native = curr * adet
        cost_native = maliyet * adet
        daily_chg_native = (curr - prev) * adet

        if view_currency == "TRY":
            if asset_currency == "USD":
                f_g = curr * usd_try_rate
                v_g = val_native * usd_try_rate
                c_g = cost_native * usd_try_rate
                d_g = daily_chg_native * usd_try_rate
            else:
                f_g = curr
                v_g = val_native
                c_g = cost_native
                d_g = daily_chg_native
        else:  # USD
            if asset_currency == "TRY":
                f_g = curr / usd_try_rate
                v_g = val_native / usd_try_rate
                c_g = cost_native / usd_try_rate
                d_g = daily_chg_native / usd_try_rate
            else:
                f_g = curr
                v_g = val_native
                c_g = cost_native
                d_g = daily_chg_native

        pnl = v_g - c_g
        pnl_pct = (pnl / c_g * 100) if c_g > 0 else 0

        # Günlük fiyat değişimi yüzdesi (izleme listesi için)
        # prev ve curr'ü view_currency'ye çevir
        if view_currency == "TRY":
            if asset_currency == "USD":
                prev_g = prev * usd_try_rate
            else:
                prev_g = prev
        else:  # USD
            if asset_currency == "TRY":
                prev_g = prev / usd_try_rate
            else:
                prev_g = prev
        
        daily_pct_change = ((f_g - prev_g) / prev_g * 100) if prev_g > 0 else 0
        
        results.append({
                "Kod": kod,
                "Pazar": pazar,
                "Tip": tip,
                "Adet": adet,
                "Maliyet": maliyet,
                "Fiyat": f_g,
            "PB": view_currency,
                "Yatırılan": c_g,  # Yatırılan para = Adet * Maliyet (view_currency'de)
                "Değer": v_g,
                "Top. Kâr/Zarar": pnl,
                "Top. %": pnl_pct,
                "Gün. Kâr/Zarar": d_g,
            "Günlük Değişim %": daily_pct_change,  # İzleme listesi için
                "Notlar": row.get("Notlar", ""),
                "Sektör": sector,
        })

    return pd.DataFrame(results)


# Session state ile önceki sonucu sakla - sekme değişimlerinde boş görünmesini önle
# Cache key: portfoy_df hash'i + USD_TRY + GORUNUM_PB
portfoy_df_hash = hash(str(portfoy_df.values.tolist())) if not portfoy_df.empty else 0
cache_key = f"master_df_{portfoy_df_hash}_{USD_TRY}_{GORUNUM_PB}"

# Eğer cache'de varsa ve veri değişmemişse kullan
if cache_key in st.session_state:
    master_df = st.session_state[cache_key]
else:
    # İlk yükleme veya veri değişmiş - yeniden hesapla
    with st.spinner("Portföy verileri yükleniyor..."):
        master_df = run_analysis(portfoy_df, USD_TRY, GORUNUM_PB)
        st.session_state[cache_key] = master_df
        # Eski cache'leri temizle (sadece son 3 cache'i tut)
        cache_keys = [k for k in st.session_state.keys() if k.startswith("master_df_")]
        if len(cache_keys) > 3:
            for old_key in cache_keys[:-3]:
                del st.session_state[old_key]

portfoy_only = master_df[master_df["Tip"] == "Portfoy"] if not master_df.empty else pd.DataFrame(columns=ANALYSIS_COLS)
takip_only = master_df[master_df["Tip"] == "Takip"] if not master_df.empty else pd.DataFrame(columns=ANALYSIS_COLS)


# --- GLOBAL INFO BAR ---

# Kâr/Zarar göstergesi için yardımcı fonksiyon
def get_pnl_indicator(pct_value):
    """Yüzde değerine göre kırmızı/yeşil nokta döndürür"""
    try:
        pct = float(pct_value)
        if pct > 0:
            return '<span style="color: #00e676; font-size: 16px;">🟢</span>'
        elif pct < 0:
            return '<span style="color: #ff5252; font-size: 16px;">🔴</span>'
        else:
            return '<span style="color: #888; font-size: 16px;">⚪</span>'
    except:
        return '<span style="color: #888; font-size: 16px;">⚪</span>'

# --- GLOBAL INFO BAR ---
def render_kral_infobar(df, sym, gorunum_pb=None, usd_try_rate=None, timeframe=None, show_sparklines=False):
    """
    KRAL infobar:
    - Toplam Varlık
    - Son 24 Saat K/Z
    - Haftalık / Aylık / YTD (opsiyonel, timeframe ile)
    - İstenirse altında mini sparkline'lar
    """
    if df is None or df.empty:
        return

    # Mevcut görünümdeki toplam değer (df'nin para biriminde)
    total_value_view = df["Değer"].sum()
    daily_pnl = df["Gün. Kâr/Zarar"].sum()

    # Görsel işaretler - kırmızı/yeşil
    if daily_pnl > 0:
        daily_sign = '<span style="color: #00e676; font-size: 16px;">🟢</span>'
    elif daily_pnl < 0:
        daily_sign = '<span style="color: #ff5252; font-size: 16px;">🔴</span>'
    else:
        daily_sign = '<span style="color: #888; font-size: 16px;">⚪</span>'

    # Haftalık / Aylık / YTD metinleri (varsayılan)
    weekly_txt = "—"
    monthly_txt = "—"
    ytd_txt = "—"

    # Timeframe verisi geldiyse gerçek rakamlarla doldur
    w_pct, m_pct, y_pct = 0, 0, 0
    if timeframe is not None:
        try:
            w_val, w_pct = timeframe.get("weekly", (0, 0))
            m_val, m_pct = timeframe.get("monthly", (0, 0))
            y_val, y_pct = timeframe.get("ytd", (0, 0))

            # Haftalık / Aylık / YTD değerler her zaman TRY bazlı tutuluyor
            # Görünüm USD ise, gösterirken USD'ye çeviriyoruz.
            show_sym = sym
            if gorunum_pb == "USD" and usd_try_rate:
                weekly_txt = f"{show_sym}{(w_val / usd_try_rate):,.0f} ({w_pct:+.2f}%)"
                monthly_txt = f"{show_sym}{(m_val / usd_try_rate):,.0f} ({m_pct:+.2f}%)"
                ytd_txt = f"{show_sym}{(y_val / usd_try_rate):,.0f} ({y_pct:+.2f}%)"
            else:
                weekly_txt = f"{show_sym}{w_val:,.0f} ({w_pct:+.2f}%)"
                monthly_txt = f"{show_sym}{m_val:,.0f} ({m_pct:+.2f}%)"
                ytd_txt = f"{show_sym}{y_val:,.0f} ({y_pct:+.2f}%)"
        except Exception:
            # Herhangi bir sorun olursa placeholder'da kalsın
            weekly_txt = "—"
            monthly_txt = "—"
            ytd_txt = "—"

    st.markdown(
        f"""
        <div class="kral-infobar">
            <div class="kral-infobox">
                <div class="kral-infobox-label">Toplam Varlık</div>
                <span class="kral-infobox-value">{sym}{total_value_view:,.0f}</span>
                <div class="kral-infobox-sub">Bu görünümdeki toplam varlık</div>
            </div>
            <div class="kral-infobox">
                <div class="kral-infobox-label">Son 24 Saat K/Z</div>
                <span class="kral-infobox-value">{daily_sign} {sym}{abs(daily_pnl):,.0f}</span>
                <div class="kral-infobox-sub">Günlük toplam portföy hareketi</div>
            </div>
            <div class="kral-infobox">
                <div class="kral-infobox-label">Haftalık K/Z</div>
                <span class="kral-infobox-value">{get_pnl_indicator(w_pct)} {weekly_txt}</span>
                <div class="kral-infobox-sub">Son 7 güne göre</div>
            </div>
            <div class="kral-infobox">
                <div class="kral-infobox-label">Aylık K/Z</div>
                <span class="kral-infobox-value">{get_pnl_indicator(m_pct)} {monthly_txt}</span>
                <div class="kral-infobox-sub">Son 30 güne göre</div>
            </div>
            <div class="kral-infobox">
                <div class="kral-infobox-label">YTD Performans</div>
                <span class="kral-infobox-value">{get_pnl_indicator(y_pct)} {ytd_txt}</span>
                <div class="kral-infobox-sub">Yılbaşından bugüne</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # İstenirse altına mini sparkline'lar
    if show_sparklines and timeframe is not None:
        try:
            spark_week = timeframe.get("spark_week", [])
            spark_month = timeframe.get("spark_month", [])
            spark_ytd = timeframe.get("spark_ytd", [])

            cols = st.columns(3)
            # Haftalık spark
            with cols[0]:
                st.caption("Haftalık Trend")
                fig_w = render_kpi_sparkline(spark_week)
                if fig_w is not None:
                    st.plotly_chart(fig_w, use_container_width=True)
            # Aylık spark
            with cols[1]:
                st.caption("Aylık Trend")
                fig_m = render_kpi_sparkline(spark_month)
                if fig_m is not None:
                    st.plotly_chart(fig_m, use_container_width=True)
            # YTD spark
            with cols[2]:
                st.caption("YTD Trend")
                fig_y = render_kpi_sparkline(spark_ytd)
                if fig_y is not None:
                    st.plotly_chart(fig_y, use_container_width=True)
        except Exception:
            # Grafiklerde sorun olsa bile infobar metinleri çalışmaya devam etsin
            pass


def render_kpi_sparkline(values):
    """
    KPI kartları altındaki mini sparkline grafikleri.
    Değer listesi (TRY bazlı) alır, minimalist çizgi döner.
    """
    if not values or len(values) < 2:
        return None

    df = pd.DataFrame({"idx": list(range(len(values))), "val": values})
    fig = px.line(df, x="idx", y="val")
    fig.update_traces(line=dict(width=2))
    fig.update_layout(
        height=70,
        margin=dict(l=0, r=0, t=0, b=0),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
    )
    return fig


def _compute_daily_pct(df):
    """Safely compute günlük yüzde değişimi for hareket listesi."""
    if df is None or df.empty:
        return pd.DataFrame()
    required_cols = {"Kod", "Değer", "Gün. Kâr/Zarar"}
    if not required_cols.issubset(df.columns):
        return pd.DataFrame()

    work = df.copy()
    work["Günlük %"] = 0.0
    safe_val = work["Değer"] - work["Gün. Kâr/Zarar"]
    non_zero = safe_val.notna() & (safe_val != 0)
    if non_zero.any():
        work.loc[non_zero, "Günlük %"] = (
            work.loc[non_zero, "Gün. Kâr/Zarar"] / safe_val[non_zero]
        ) * 100
    work["Günlük %"] = work["Günlük %"].fillna(0.0)
    return work


def get_daily_movers(df, top_n=5):
    """Return top gainers/losers DataFrames according to günlük yüzde."""
    enriched = _compute_daily_pct(df)
    if enriched.empty:
        return pd.DataFrame(), pd.DataFrame()
    winners = enriched.sort_values("Günlük %", ascending=False).head(top_n)
    losers = enriched.sort_values("Günlük %", ascending=True).head(top_n)
    return winners, losers


def render_daily_movers_section(df, currency_symbol, top_n=5):
    """Render günlük kazanan/kaybeden listesini modern kart formatında göster."""
    winners, losers = get_daily_movers(df, top_n=top_n)
    if winners.empty and losers.empty:
        st.info("Günlük kazanan/kaybeden verisi bulunamadı.")
        return

    # Başlık
    st.markdown(
        """
        <div style="margin-bottom: 30px;">
            <h2 style="font-size: 32px; font-weight: 900; color: #ffffff; margin-bottom: 8px; display: flex; align-items: center; gap: 14px;">
                <span style="font-size: 38px; filter: drop-shadow(0 2px 6px rgba(255, 255, 255, 0.2));">🔥</span>
                Günün Kazananları / Kaybedenleri
            </h2>
            <p style="font-size: 14px; color: #9da1b3; margin: 0; font-weight: 600;">En yüksek ve en düşük günlük performans gösteren varlıklarınız</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # İki sütunlu layout
    col1, col2 = st.columns(2, gap="large")

    # Günün Kazananları
    with col1:
        # Kart başlığı
        st.markdown(
            """
            <div class="daily-movers-card positive-card" style="background: linear-gradient(135deg, #1b1f2b 0%, #10131b 100%); 
                        border-radius: 20px; 
                        border-top: 4px solid #00e676; 
                        padding: 24px; 
                        margin-bottom: 20px;
                        box-shadow: 0 12px 32px rgba(0, 230, 118, 0.15), 0 0 0 1px rgba(0, 230, 118, 0.1);">
                <div class="daily-movers-card-header">
                    <div class="daily-movers-card-title">
                        <span class="daily-movers-card-title-icon">🏆</span>
                        <span style="font-size: 22px;">Günün Kazananları</span>
                    </div>
                    <div class="daily-movers-chip" style="background: rgba(0, 230, 118, 0.2); color: #00e676; border-color: rgba(0, 230, 118, 0.3);">
                        TOP 5
                    </div>
                </div>
                <div class="daily-movers-card-body">
            """,
            unsafe_allow_html=True,
        )
        
        if not winners.empty:
            # Her bir kazanan için satır oluştur
            for idx, (_, row) in enumerate(winners.iterrows(), 1):
                symbol = row["Kod"]
                change_pct = row["Günlük %"]
                pl_value = row["Gün. Kâr/Zarar"]
                
                # Değer formatla
                change_sign = "+" if change_pct > 0 else ""
                change_str = f"{change_sign}{change_pct:.2f}%"
                pl_str = f"{currency_symbol}{pl_value:,.0f}"
                
                # Emoji ve renk seç
                if change_pct > 5:
                    emoji = "🚀"
                elif change_pct > 2:
                    emoji = "📈"
                else:
                    emoji = "↗️"
                
                st.markdown(
                    f"""
                    <div class="daily-mover-row positive" style="display: grid; grid-template-columns: 1fr auto auto; align-items: center; gap: 16px;
                                padding: 18px 20px; border-radius: 14px; margin-bottom: 12px;
                                background: linear-gradient(135deg, rgba(0, 230, 118, 0.06) 0%, rgba(0, 230, 118, 0.02) 100%);
                                border: 1px solid rgba(0, 230, 118, 0.15); border-left: 4px solid #00e676;
                                transition: all 0.3s ease;">
                        <div class="daily-mover-symbol" style="display: flex; align-items: center; gap: 12px;">
                            <span class="daily-mover-symbol-badge" style="width: 36px; height: 36px; border-radius: 10px; 
                                        background: rgba(0, 230, 118, 0.15); border: 1px solid rgba(0, 230, 118, 0.3);
                                        display: flex; align-items: center; justify-content: center; 
                                        font-size: 14px; font-weight: 900; color: #00e676;">
                                {idx}
                            </span>
                            <span style="font-size: 20px; font-weight: 900; color: #ffffff; letter-spacing: -0.5px;">
                                {symbol}
                            </span>
                        </div>
                        <div class="daily-mover-change" style="display: flex; align-items: center; gap: 8px; font-size: 19px; font-weight: 900; color: #00e676; text-shadow: 0 0 12px rgba(0, 230, 118, 0.4);">
                            <span>{emoji}</span>
                            <span style="letter-spacing: -0.3px;">{change_str}</span>
                        </div>
                        <div class="daily-mover-pl" style="font-size: 16px; font-weight: 700; color: #b6bad3; text-align: right; letter-spacing: -0.2px;">
                            {pl_str}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.markdown(
                """
                <div class="daily-mover-empty" style="text-align: center; padding: 32px; border-radius: 14px; 
                            background: rgba(255, 255, 255, 0.03); border: 1px dashed rgba(255, 255, 255, 0.1);">
                    <span style="font-size: 16px; color: #8f93a6; font-weight: 600;">📊 Veri bulunamadı</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        
        st.markdown("</div></div>", unsafe_allow_html=True)

    # Günün Kaybedenleri
    with col2:
        # Kart başlığı
        st.markdown(
            """
            <div class="daily-movers-card negative-card" style="background: linear-gradient(135deg, #1b1f2b 0%, #10131b 100%); 
                        border-radius: 20px; 
                        border-top: 4px solid #ff5252; 
                        padding: 24px; 
                        margin-bottom: 20px;
                        box-shadow: 0 12px 32px rgba(255, 82, 82, 0.15), 0 0 0 1px rgba(255, 82, 82, 0.1);">
                <div class="daily-movers-card-header">
                    <div class="daily-movers-card-title">
                        <span class="daily-movers-card-title-icon">⚠️</span>
                        <span style="font-size: 22px;">Günün Kaybedenleri</span>
                    </div>
                    <div class="daily-movers-chip" style="background: rgba(255, 82, 82, 0.2); color: #ff5252; border-color: rgba(255, 82, 82, 0.3);">
                        TOP 5
                    </div>
                </div>
                <div class="daily-movers-card-body">
            """,
            unsafe_allow_html=True,
        )
        
        if not losers.empty:
            # Her bir kaybeden için satır oluştur
            for idx, (_, row) in enumerate(losers.iterrows(), 1):
                symbol = row["Kod"]
                change_pct = row["Günlük %"]
                pl_value = row["Gün. Kâr/Zarar"]
                
                # Değer formatla
                change_sign = "" if change_pct < 0 else "+"
                change_str = f"{change_sign}{change_pct:.2f}%"
                pl_str = f"{currency_symbol}{pl_value:,.0f}"
                
                # Emoji seç
                if change_pct < -5:
                    emoji = "💥"
                elif change_pct < -2:
                    emoji = "📉"
                else:
                    emoji = "↘️"
                
                st.markdown(
                    f"""
                    <div class="daily-mover-row negative" style="display: grid; grid-template-columns: 1fr auto auto; align-items: center; gap: 16px;
                                padding: 18px 20px; border-radius: 14px; margin-bottom: 12px;
                                background: linear-gradient(135deg, rgba(255, 82, 82, 0.06) 0%, rgba(255, 82, 82, 0.02) 100%);
                                border: 1px solid rgba(255, 82, 82, 0.15); border-left: 4px solid #ff5252;
                                transition: all 0.3s ease;">
                        <div class="daily-mover-symbol" style="display: flex; align-items: center; gap: 12px;">
                            <span class="daily-mover-symbol-badge" style="width: 36px; height: 36px; border-radius: 10px; 
                                        background: rgba(255, 82, 82, 0.15); border: 1px solid rgba(255, 82, 82, 0.3);
                                        display: flex; align-items: center; justify-content: center; 
                                        font-size: 14px; font-weight: 900; color: #ff5252;">
                                {idx}
                            </span>
                            <span style="font-size: 20px; font-weight: 900; color: #ffffff; letter-spacing: -0.5px;">
                                {symbol}
                            </span>
                        </div>
                        <div class="daily-mover-change" style="display: flex; align-items: center; gap: 8px; font-size: 19px; font-weight: 900; color: #ff5252; text-shadow: 0 0 12px rgba(255, 82, 82, 0.4);">
                            <span>{emoji}</span>
                            <span style="letter-spacing: -0.3px;">{change_str}</span>
                        </div>
                        <div class="daily-mover-pl" style="font-size: 16px; font-weight: 700; color: #b6bad3; text-align: right; letter-spacing: -0.2px;">
                            {pl_str}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.markdown(
                """
                <div class="daily-mover-empty" style="text-align: center; padding: 32px; border-radius: 14px; 
                            background: rgba(255, 255, 255, 0.03); border: 1px dashed rgba(255, 255, 255, 0.1);">
                    <span style="font-size: 16px; color: #8f93a6; font-weight: 600;">📊 Veri bulunamadı</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        
        st.markdown("</div></div>", unsafe_allow_html=True)

# --- GÖRÜNÜM AYARI ---
TOTAL_SPOT_DEGER = portfoy_only["Değer"].sum()
st.markdown("---")
VARLIK_GORUNUMU = st.radio(
    "Varlık Gösterimi:",
    ["YÜZDE (%)", "TUTAR (₺/$)"],
    index=0,
    horizontal=True,
)
st.markdown("---")

# --- MENÜ İÇERİKLERİ ---

if selected == "Dashboard":
    if not portfoy_only.empty:
        # Dashboard genel portföy görünümü
        spot_only = portfoy_only

        # Toplam değer (seçili para biriminde)
        t_v = spot_only["Değer"].sum()
        t_p = spot_only["Top. Kâr/Zarar"].sum()
        t_maliyet = t_v - t_p
        pct = (t_p / t_maliyet * 100) if t_maliyet != 0 else 0

        # Gerçek Haftalık / Aylık / YTD KPI için tarihsel log güncelle
        kpi_timeframe = None
        try:
            if GORUNUM_PB == "TRY":
                total_try = float(t_v)
                total_usd = float(t_v / USD_TRY) if USD_TRY else 0.0
            else:
                total_usd = float(t_v)
                total_try = float(t_v * USD_TRY)

            # Günlük portföy logunu yaz (aynı günse data_loader içinde atlanıyor)
            write_portfolio_history(total_try, total_usd)

            # Fon toplamını ayrıca logla (haftalık/aylık hesaplardan düşebilmek için)
            fon_mask = spot_only["Pazar"].astype(str).str.contains("FON", case=False, na=False)
            fon_total_view = float(spot_only.loc[fon_mask, "Değer"].sum()) if fon_mask.any() else 0.0
            if GORUNUM_PB == "TRY":
                fon_try = fon_total_view
                fon_usd = fon_total_view / USD_TRY if USD_TRY else 0.0
            else:
                fon_usd = fon_total_view
                fon_try = fon_total_view * USD_TRY
            write_history_fon(fon_try, fon_usd)

            history_df = read_portfolio_history()
            history_fon = read_history_fon()
            if not history_fon.empty and "Tarih" in history_fon.columns:
                history_fon_filtered = history_fon.copy()
            else:
                history_fon_filtered = history_fon
            kpi_timeframe = get_timeframe_changes(
                history_df,
                subtract_df=history_fon_filtered,
                subtract_before=FON_METRIC_RESET_DATE,
            )
        except Exception:
            kpi_timeframe = None

        # INFO BAR (Toplam Varlık + Son 24 Saat + Haftalık/Aylık/YTD + Sparkline)
        render_kral_infobar(
            spot_only,
            sym,
            gorunum_pb=GORUNUM_PB,
            usd_try_rate=USD_TRY,
            timeframe=kpi_timeframe,
            show_sparklines=True,
        )

        # Eski 2 metric (Toplam Varlık + Genel K/Z) yine dursun
        c1, c2 = st.columns(2)
        # Toplam Varlık için: Toplam kâr/zarar yüzdesi (maliyete göre) - zaman aralığı belirtilmeli
        c1.metric("Toplam Varlık", f"{sym}{t_v:,.0f}", delta=f"{pct:.2f}% (Başlangıçtan Beri)")
        c2.metric("Genel Kâr/Zarar", f"{sym}{t_p:,.0f}", delta=f"{pct:.2f}% (Maliyete Göre)")

        st.divider()

        # --- PAZAR DAĞILIMI ---
        st.subheader("📊 Pazarlara Göre Dağılım")
        dash_pazar = spot_only.groupby("Pazar", as_index=False).agg(
            {"Değer": "sum", "Top. Kâr/Zarar": "sum"}
        )
        render_pie_bar_charts(
            dash_pazar,
            "Pazar",
            all_tab=False,
            varlik_gorunumu=VARLIK_GORUNUMU,
            total_spot_deger=TOTAL_SPOT_DEGER,
        )

        st.divider()
        render_daily_movers_section(spot_only, sym)

        c_tree_1, c_tree_2 = st.columns([3, 1])
        with c_tree_1:
            st.subheader("🗺️ Portföy Isı Haritası")
        with c_tree_2:
            map_mode = st.radio(
                "Renklendirme:",
                ["Genel Kâr %", "Günlük Değişim %"],
                horizontal=True,
                key="heatmap_color_mode",
            )
            heat_scope = st.selectbox(
                "Kapsam:",
                ["Tümü", "BIST", "ABD", "FON", "Emtia", "Kripto", "Nakit"],
                index=0,
                key="heatmap_scope",
            )

        # Pazar filtresi (sadece görünüm, hesap mantığına karışmaz)
        if heat_scope == "Tümü":
            heat_df = spot_only
        else:
            scope_map = {
                "BIST": "BIST",
                "ABD": "ABD",
                "FON": "FON",
                "Emtia": "EMTIA",
                "Kripto": "KRIPTO",
                "Nakit": "NAKIT",
            }
            target = scope_map.get(heat_scope, heat_scope).upper()
            # Vectorized filtreleme - gereksiz copy() yok
            pazar_upper = spot_only["Pazar"].astype(str).str.upper()
            mask = pazar_upper.str.contains(target, na=False)
            heat_df = spot_only[mask]

        if heat_df.empty:
            st.info("Seçilen kapsam için portföyde varlık bulunmuyor.")
        else:
            # Renk kolonu: Top. % veya Gün. %
            color_col = "Top. %"
            heat_df["Gün. %"] = 0.0
            safe_val = heat_df["Değer"] - heat_df["Gün. Kâr/Zarar"]
            non_zero = safe_val != 0
            heat_df.loc[non_zero, "Gün. %"] = (
                heat_df.loc[non_zero, "Gün. Kâr/Zarar"] / safe_val[non_zero]
            ) * 100

            if map_mode == "Günlük Değişim %":
                color_col = "Gün. %"

            # Yüzdeleri 1 ondalık basamağa yuvarla (görüntü için)
            heat_df["Top. %_formatted"] = heat_df["Top. %"].round(1)
            heat_df["Gün. %_formatted"] = heat_df["Gün. %"].round(1)

            # Modern renk skalası için simetrik aralık
            vmax = float(heat_df[color_col].max())
            vmin = float(heat_df[color_col].min())
            abs_max = max(abs(vmax), abs(vmin)) if (vmax or vmin) else 0

            # Para birimi sembolü
            currency_symbol = "₺" if GORUNUM_PB == "TRY" else "$"

            # Formatlanmış yüzde kolonu seç
            color_col_formatted = "Top. %_formatted" if color_col == "Top. %" else "Gün. %_formatted"
            
            # Modern treemap oluştur
            fig = px.treemap(
                heat_df,
                path=[px.Constant("Portföy"), "Kod"],
                values="Değer",
                color=color_col,
                custom_data=["Değer", "Top. Kâr/Zarar", color_col_formatted, "Kod"],
                color_continuous_scale="RdYlGn",  # Kırmızı-Sarı-Yeşil
                color_continuous_midpoint=0,
                hover_data={"Kod": True, "Değer": ":,.0f", color_col: ":.1f"},
            )
            
            # Renk aralığını ayarla
            if abs_max > 0:
                fig.update_coloraxes(
                    cmin=-abs_max, 
                    cmax=abs_max,
                    colorscale="RdYlGn",
                    colorbar=dict(
                        title=dict(
                            text="Performans %",
                            font=dict(size=14, color="#ffffff", family="Inter, sans-serif")
                        ),
                        tickfont=dict(size=12, color="#ffffff", family="Inter, sans-serif"),
                        thickness=20,
                        len=0.8,
                        x=1.02,
                        xpad=10,
                        bgcolor="rgba(0,0,0,0)",
                        bordercolor="#2f3440",
                        borderwidth=1,
                    )
                )

            # Modern tipografi ve stil - okunabilir yazılar, büyük kodlar, kısa yüzdeler
            # Mobil için CSS ile font boyutları küçültülecek
            fig.update_traces(
                textinfo="label+value+percent entry",
                texttemplate="<b class='treemap-label' style='font-size:22px; font-family:Inter, sans-serif; color:#ffffff; text-shadow: 2px 2px 4px rgba(0,0,0,0.9), -1px -1px 2px rgba(0,0,0,0.9); font-weight:900;'>%{label}</b><br>" +
                            f"<span class='treemap-value' style='font-size:14px; color:#ffffff; text-shadow: 2px 2px 4px rgba(0,0,0,0.8), -1px -1px 2px rgba(0,0,0,0.8);'>%{{customdata[0]:,.0f}} {currency_symbol}</span><br>" +
                            "<b class='treemap-pct' style='font-size:16px; font-family:Inter, sans-serif; color:#ffffff; text-shadow: 2px 2px 4px rgba(0,0,0,0.9), -1px -1px 2px rgba(0,0,0,0.9); font-weight:700;'>%{customdata[2]:+.1f}%</b>",
                textposition="middle center",
                textfont=dict(
                    size=22, 
                    family="Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
                    color="#ffffff"
                ),
                hovertemplate="<b style='font-size:16px;'>%{customdata[3]}</b><br>" +
                             f"Değer: %{{customdata[0]:,.0f}} {currency_symbol}<br>" +
                             f"Toplam K/Z: %{{customdata[1]:,.0f}} {currency_symbol}<br>" +
                             "Performans: %{customdata[2]:+.1f}%<br>" +
                             "<extra></extra>",
                marker=dict(
                    line=dict(
                        width=2,
                        color="#1a1c24"
                    ),
                    pad=dict(t=6, l=6, r=6, b=6),
                    cornerradius=4,
                ),
            )
            
            # Modern layout - mobilde CSS ile yükseklik ayarlanacak
            fig.update_layout(
                margin=dict(t=10, l=10, r=10, b=10),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(
                    family="Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
                    color="#ffffff",
                    size=12
                ),
                height=600,
                title=dict(
                    text="",
                    font=dict(size=18, color="#ffffff")
                ),
            )
            
            st.plotly_chart(fig, use_container_width=True, config={
                "displayModeBar": True,
                "displaylogo": False,
                "modeBarButtonsToRemove": ["pan2d", "lasso2d"],
                "toImageButtonOptions": {
                    "format": "png",
                    "filename": "portfoy_heatmap",
                    "height": 600,
                    "width": 1200,
                    "scale": 2
                }
            })

        st.divider()

        # --- SEKTÖREL DAĞILIM ---
        if "Sektör" in spot_only.columns:
            st.subheader("🏭 Sektörel Dağılım")
            sektor_df = spot_only[spot_only["Sektör"] != ""].copy()
            if not sektor_df.empty:
                # Her sektör için şirket listesini hazırla
                sektor_sirketler = sektor_df.groupby("Sektör")["Kod"].apply(lambda x: ", ".join(x.unique())).reset_index()
                sektor_sirketler.columns = ["Sektör", "Kod"]
                # Gruplama yap ve şirket listesini ekle
                sektor_grouped = sektor_df.groupby("Sektör", as_index=False).agg(
                    {"Değer": "sum", "Top. Kâr/Zarar": "sum"}
                )
                sektor_grouped = sektor_grouped.merge(sektor_sirketler, on="Sektör", how="left")
                render_pie_bar_charts(
                    sektor_grouped,
                    "Sektör",
                    all_tab=False,
                    varlik_gorunumu=VARLIK_GORUNUMU,
                    total_spot_deger=TOTAL_SPOT_DEGER,
                    show_companies=True,  # Şirket listesini göster
                )
            else:
                st.info("Sektör bilgisi bulunamadı.")
        
        st.divider()

        # --- KARŞILAŞTIRMALI GRAFİKLER ---
        st.subheader("📊 Portföy Karşılaştırmaları")
        
        # Buton switch'li seçim
        comparison_options = ["BIST 100", "Altın", "SP500", "Enflasyon"]
        selected_comparison = st.radio(
            "Karşılaştırma:",
            comparison_options,
            horizontal=True,
            key="comparison_selector",
        )
        
        comparison_chart = get_comparison_chart(spot_only, USD_TRY, GORUNUM_PB, selected_comparison)
        if comparison_chart:
            st.plotly_chart(comparison_chart, use_container_width=True)
        else:
            st.info(f"{selected_comparison} karşılaştırması için veri hazırlanıyor...")
        
        st.divider()

        # --- TARİHSEL GRAFİK EN ALTA ---
        col_title, col_date = st.columns([2, 1])
        with col_title:
            st.subheader("📈 Tarihsel Portföy Değeri")
        with col_date:
            # Tarih seçici - varsayılan: None (son 60 gün)
            use_custom_date = st.checkbox("Belirli bir günden itibaren göster", key="dashboard_date_toggle")
            if use_custom_date:
                # En az 60 gün öncesine kadar seçim yapılabilir
                min_date = (pd.Timestamp.today() - pd.Timedelta(days=365)).date()
                max_date = pd.Timestamp.today().date()
                selected_date = st.date_input(
                    "Başlangıç Tarihi",
                    value=max_date - timedelta(days=30),
                    min_value=min_date,
                    max_value=max_date,
                    key="dashboard_start_date"
                )
                start_date = pd.Timestamp(selected_date)
            else:
                start_date = None
        
        hist_chart = get_historical_chart(spot_only, USD_TRY, GORUNUM_PB, start_date=start_date)
        if hist_chart:
            st.plotly_chart(hist_chart, use_container_width=True)
        else:
            st.info("Tarihsel veri hazırlanıyor...")
    else:
        st.info("Boş.")

elif selected == "Portföy":
    st.subheader("📊 Portföy Görünümü")

    tab_tumu, tab_bist, tab_abd, tab_fon, tab_emtia, tab_kripto, tab_nakit = st.tabs(
        ["Tümü", "BIST", "ABD", "FON", "Emtia", "Kripto", "Nakit"]
    )

    # Tümü
    with tab_tumu:
        render_kral_infobar(portfoy_only, sym)
        render_pazar_tab(
            portfoy_only,
            "Tümü",
            sym,
            USD_TRY,
            VARLIK_GORUNUMU,
            TOTAL_SPOT_DEGER,
        )
        col_title, col_date = st.columns([2, 1])
        with col_title:
            st.subheader("📈 Tarihsel Değer - Tümü")
        with col_date:
            use_custom_date = st.checkbox("Belirli bir günden itibaren göster", key="tumu_date_toggle")
            if use_custom_date:
                min_date = (pd.Timestamp.today() - pd.Timedelta(days=365)).date()
                max_date = pd.Timestamp.today().date()
                selected_date = st.date_input(
                    "Başlangıç Tarihi",
                    value=max_date - timedelta(days=30),
                    min_value=min_date,
                    max_value=max_date,
                    key="tumu_start_date"
                )
                start_date = pd.Timestamp(selected_date)
            else:
                start_date = None
        hist_chart = get_historical_chart(portfoy_only, USD_TRY, GORUNUM_PB, start_date=start_date)
        if hist_chart:
            st.plotly_chart(hist_chart, use_container_width=True)

    # BIST
    with tab_bist:
        # Vectorized filtreleme - daha hızlı
        pazar_str = portfoy_only["Pazar"].astype(str)
        bist_df = portfoy_only[pazar_str.str.contains("BIST", case=False, na=False)]

        # Haftalık / Aylık / YTD + sparkline için tarihsel log
        timeframe_bist = None
        if not bist_df.empty:
            try:
                t_v = float(bist_df["Değer"].sum())
                if GORUNUM_PB == "TRY":
                    total_try = t_v
                    total_usd = t_v / USD_TRY if USD_TRY else 0.0
                else:
                    total_usd = t_v
                    total_try = t_v * USD_TRY

                write_history_bist(total_try, total_usd)
                hist_bist = read_history_bist()
                timeframe_bist = get_timeframe_changes(hist_bist)
            except Exception:
                timeframe_bist = None

        render_kral_infobar(
            bist_df,
            sym,
            gorunum_pb=GORUNUM_PB,
            usd_try_rate=USD_TRY,
            timeframe=timeframe_bist,
            show_sparklines=True,
        )

        render_pazar_tab(
            portfoy_only,
            "BIST",
            sym,
            USD_TRY,
            VARLIK_GORUNUMU,
            TOTAL_SPOT_DEGER,
        )
        
        # --- SEKTÖREL DAĞILIM - BIST ---
        if "Sektör" in bist_df.columns:
            st.subheader("🏭 Sektörel Dağılım - BIST")
            sektor_bist = bist_df[bist_df["Sektör"] != ""].copy()
            if not sektor_bist.empty:
                # Her sektör için şirket listesini hazırla
                sektor_sirketler = sektor_bist.groupby("Sektör")["Kod"].apply(lambda x: ", ".join(x.unique())).reset_index()
                sektor_sirketler.columns = ["Sektör", "Kod"]
                # Gruplama yap ve şirket listesini ekle
                sektor_grouped = sektor_bist.groupby("Sektör", as_index=False).agg(
                    {"Değer": "sum", "Top. Kâr/Zarar": "sum"}
                )
                sektor_grouped = sektor_grouped.merge(sektor_sirketler, on="Sektör", how="left")
                render_pie_bar_charts(
                    sektor_grouped,
                    "Sektör",
                    all_tab=False,
                    varlik_gorunumu=VARLIK_GORUNUMU,
                    total_spot_deger=TOTAL_SPOT_DEGER,
                    show_companies=True,  # Şirket listesini göster
                )
            else:
                st.info("Sektör bilgisi bulunamadı.")
        
        col_title, col_date = st.columns([2, 1])
        with col_title:
            st.subheader("📈 Tarihsel Değer - BIST")
        with col_date:
            use_custom_date = st.checkbox("Belirli bir günden itibaren göster", key="bist_date_toggle")
            if use_custom_date:
                min_date = (pd.Timestamp.today() - pd.Timedelta(days=365)).date()
                max_date = pd.Timestamp.today().date()
                selected_date = st.date_input(
                    "Başlangıç Tarihi",
                    value=max_date - timedelta(days=30),
                    min_value=min_date,
                    max_value=max_date,
                    key="bist_start_date"
                )
                start_date = pd.Timestamp(selected_date)
            else:
                start_date = None
        hist_chart = get_historical_chart(bist_df, USD_TRY, GORUNUM_PB, start_date=start_date)
        if hist_chart:
            st.plotly_chart(hist_chart, use_container_width=True)


    # ABD
    with tab_abd:
        pazar_str = portfoy_only["Pazar"].astype(str)
        abd_df = portfoy_only[pazar_str.str.contains("ABD", case=False, na=False)]

        timeframe_abd = None
        if not abd_df.empty:
            try:
                t_v = float(abd_df["Değer"].sum())
                if GORUNUM_PB == "TRY":
                    total_try = t_v
                    total_usd = t_v / USD_TRY if USD_TRY else 0.0
                else:
                    total_usd = t_v
                    total_try = t_v * USD_TRY

                write_history_abd(total_try, total_usd)
                hist_abd = read_history_abd()
                timeframe_abd = get_timeframe_changes(hist_abd)
            except Exception:
                timeframe_abd = None

        render_kral_infobar(
            abd_df,
            sym,
            gorunum_pb=GORUNUM_PB,
            usd_try_rate=USD_TRY,
            timeframe=timeframe_abd,
            show_sparklines=True,
        )

        render_pazar_tab(
            portfoy_only,
            "ABD",
            sym,
            USD_TRY,
            VARLIK_GORUNUMU,
            TOTAL_SPOT_DEGER,
        )
        
        # --- SEKTÖREL DAĞILIM - ABD ---
        if "Sektör" in abd_df.columns:
            st.subheader("🏭 Sektörel Dağılım - ABD")
            sektor_abd = abd_df[abd_df["Sektör"] != ""].copy()
            if not sektor_abd.empty:
                # Her sektör için şirket listesini hazırla
                sektor_sirketler = sektor_abd.groupby("Sektör")["Kod"].apply(lambda x: ", ".join(x.unique())).reset_index()
                sektor_sirketler.columns = ["Sektör", "Kod"]
                # Gruplama yap ve şirket listesini ekle
                sektor_grouped = sektor_abd.groupby("Sektör", as_index=False).agg(
                    {"Değer": "sum", "Top. Kâr/Zarar": "sum"}
                )
                sektor_grouped = sektor_grouped.merge(sektor_sirketler, on="Sektör", how="left")
                render_pie_bar_charts(
                    sektor_grouped,
                    "Sektör",
                    all_tab=False,
                    varlik_gorunumu=VARLIK_GORUNUMU,
                    total_spot_deger=TOTAL_SPOT_DEGER,
                    show_companies=True,  # Şirket listesini göster
                )
            else:
                st.info("Sektör bilgisi bulunamadı.")
        
        col_title, col_date = st.columns([2, 1])
        with col_title:
            st.subheader("📈 Tarihsel Değer - ABD")
        with col_date:
            use_custom_date = st.checkbox("Belirli bir günden itibaren göster", key="abd_date_toggle")
            if use_custom_date:
                min_date = (pd.Timestamp.today() - pd.Timedelta(days=365)).date()
                max_date = pd.Timestamp.today().date()
                selected_date = st.date_input(
                    "Başlangıç Tarihi",
                    value=max_date - timedelta(days=30),
                    min_value=min_date,
                    max_value=max_date,
                    key="abd_start_date"
                )
                start_date = pd.Timestamp(selected_date)
            else:
                start_date = None
        hist_chart = get_historical_chart(abd_df, USD_TRY, GORUNUM_PB, start_date=start_date)
        if hist_chart:
            st.plotly_chart(hist_chart, use_container_width=True)


    # FON
    with tab_fon:
        pazar_str = portfoy_only["Pazar"].astype(str)
        fon_df = portfoy_only[pazar_str.str.contains("FON", case=False, na=False)]

        timeframe_fon = None
        if not fon_df.empty:
            try:
                t_v = float(fon_df["Değer"].sum())
                if GORUNUM_PB == "TRY":
                    total_try = t_v
                    total_usd = t_v / USD_TRY if USD_TRY else 0.0
                else:
                    total_usd = t_v
                    total_try = t_v * USD_TRY

                write_history_fon(total_try, total_usd)
                hist_fon = read_history_fon()
                timeframe_fon = get_timeframe_changes(hist_fon)
            except Exception:
                timeframe_fon = None

        render_kral_infobar(
            fon_df,
            sym,
            gorunum_pb=GORUNUM_PB,
            usd_try_rate=USD_TRY,
            timeframe=timeframe_fon,
            show_sparklines=True,
        )

        render_pazar_tab(
            portfoy_only,
            "FON",
            sym,
            USD_TRY,
            VARLIK_GORUNUMU,
            TOTAL_SPOT_DEGER,
        )
        col_title, col_date = st.columns([2, 1])
        with col_title:
            st.subheader("📈 Tarihsel Değer - FON")
        with col_date:
            use_custom_date = st.checkbox("Belirli bir günden itibaren göster", key="fon_date_toggle")
            if use_custom_date:
                min_date = (pd.Timestamp.today() - pd.Timedelta(days=365)).date()
                max_date = pd.Timestamp.today().date()
                selected_date = st.date_input(
                    "Başlangıç Tarihi",
                    value=max_date - timedelta(days=30),
                    min_value=min_date,
                    max_value=max_date,
                    key="fon_start_date"
                )
                start_date = pd.Timestamp(selected_date)
            else:
                start_date = None
        hist_chart = get_historical_chart(fon_df, USD_TRY, GORUNUM_PB, start_date=start_date)
        if hist_chart:
            st.plotly_chart(hist_chart, use_container_width=True)


    # EMTIA
    with tab_emtia:
        pazar_str = portfoy_only["Pazar"].astype(str)
        emtia_df = portfoy_only[pazar_str.str.contains("EMTIA", case=False, na=False)]

        timeframe_emtia = None
        if not emtia_df.empty:
            try:
                t_v = float(emtia_df["Değer"].sum())
                if GORUNUM_PB == "TRY":
                    total_try = t_v
                    total_usd = t_v / USD_TRY if USD_TRY else 0.0
                else:
                    total_usd = t_v
                    total_try = t_v * USD_TRY

                write_history_emtia(total_try, total_usd)
                hist_emtia = read_history_emtia()
                timeframe_emtia = get_timeframe_changes(hist_emtia)
            except Exception:
                timeframe_emtia = None

        render_kral_infobar(
            emtia_df,
            sym,
            gorunum_pb=GORUNUM_PB,
            usd_try_rate=USD_TRY,
            timeframe=timeframe_emtia,
            show_sparklines=True,
        )

        render_pazar_tab(
            portfoy_only,
            "EMTIA",
            sym,
            USD_TRY,
            VARLIK_GORUNUMU,
            TOTAL_SPOT_DEGER,
        )
        col_title, col_date = st.columns([2, 1])
        with col_title:
            st.subheader("📈 Tarihsel Değer - Emtia")
        with col_date:
            use_custom_date = st.checkbox("Belirli bir günden itibaren göster", key="emtia_date_toggle")
            if use_custom_date:
                min_date = (pd.Timestamp.today() - pd.Timedelta(days=365)).date()
                max_date = pd.Timestamp.today().date()
                selected_date = st.date_input(
                    "Başlangıç Tarihi",
                    value=max_date - timedelta(days=30),
                    min_value=min_date,
                    max_value=max_date,
                    key="emtia_start_date"
                )
                start_date = pd.Timestamp(selected_date)
            else:
                start_date = None
        hist_chart = get_historical_chart(emtia_df, USD_TRY, GORUNUM_PB, start_date=start_date)
        if hist_chart:
            st.plotly_chart(hist_chart, use_container_width=True)


    # KRIPTO
    with tab_kripto:
        pazar_str = portfoy_only["Pazar"].astype(str)
        kripto_df = portfoy_only[pazar_str.str.contains("KRIPTO", case=False, na=False)]
        render_kral_infobar(kripto_df, sym)
        render_pazar_tab(
            portfoy_only,
            "KRIPTO",
            sym,
            USD_TRY,
            VARLIK_GORUNUMU,
            TOTAL_SPOT_DEGER,
        )
        col_title, col_date = st.columns([2, 1])
        with col_title:
            st.subheader("📈 Tarihsel Değer - Kripto")
        with col_date:
            use_custom_date = st.checkbox("Belirli bir günden itibaren göster", key="kripto_date_toggle")
            if use_custom_date:
                min_date = (pd.Timestamp.today() - pd.Timedelta(days=365)).date()
                max_date = pd.Timestamp.today().date()
                selected_date = st.date_input(
                    "Başlangıç Tarihi",
                    value=max_date - timedelta(days=30),
                    min_value=min_date,
                    max_value=max_date,
                    key="kripto_start_date"
                )
                start_date = pd.Timestamp(selected_date)
            else:
                start_date = None
        hist_chart = get_historical_chart(kripto_df, USD_TRY, GORUNUM_PB, start_date=start_date)
        if hist_chart:
            st.plotly_chart(hist_chart, use_container_width=True)

    # NAKIT
    with tab_nakit:
        pazar_str = portfoy_only["Pazar"].astype(str)
        nakit_df = portfoy_only[pazar_str.str.contains("NAKIT", case=False, na=False)]

        timeframe_nakit = None
        if not nakit_df.empty:
            try:
                t_v = float(nakit_df["Değer"].sum())
                if GORUNUM_PB == "TRY":
                    total_try = t_v
                    total_usd = t_v / USD_TRY if USD_TRY else 0.0
                else:
                    total_usd = t_v
                    total_try = t_v * USD_TRY

                write_history_nakit(total_try, total_usd)
                hist_nakit = read_history_nakit()
                timeframe_nakit = get_timeframe_changes(hist_nakit)
            except Exception:
                timeframe_nakit = None

        render_kral_infobar(
            nakit_df,
            sym,
            gorunum_pb=GORUNUM_PB,
            usd_try_rate=USD_TRY,
            timeframe=timeframe_nakit,
            show_sparklines=True,
        )

        render_pazar_tab(
            portfoy_only,
            "NAKIT",
            sym,
            USD_TRY,
            VARLIK_GORUNUMU,
            TOTAL_SPOT_DEGER,
        )
        col_title, col_date = st.columns([2, 1])
        with col_title:
            st.subheader("📈 Tarihsel Değer - Nakit")
        with col_date:
            use_custom_date = st.checkbox("Belirli bir günden itibaren göster", key="nakit_date_toggle")
            if use_custom_date:
                min_date = (pd.Timestamp.today() - pd.Timedelta(days=365)).date()
                max_date = pd.Timestamp.today().date()
                selected_date = st.date_input(
                    "Başlangıç Tarihi",
                    value=max_date - timedelta(days=30),
                    min_value=min_date,
                    max_value=max_date,
                    key="nakit_start_date"
                )
                start_date = pd.Timestamp(selected_date)
            else:
                start_date = None
        hist_chart = get_historical_chart(nakit_df, USD_TRY, GORUNUM_PB, start_date=start_date)
        if hist_chart:
            st.plotly_chart(hist_chart, use_container_width=True)

elif selected == "Haberler":
    tab_portfolio, tab_bist, tab_kripto, tab_global, tab_doviz = st.tabs([
        "💼 Portföy Haberleri", 
        "📈 BIST", 
        "₿ Kripto", 
        "🌍 Global", 
        "💱 Döviz"
    ])
    
    # Portföy Haberleri Sekmesi
    with tab_portfolio:
        # Portföy ve izleme listesi verilerini hazırla
        portfolio_assets = portfoy_only if not portfoy_only.empty else pd.DataFrame()
        watchlist_assets = takip_only if not takip_only.empty else pd.DataFrame()
        
        render_portfolio_news_section(portfolio_assets, watchlist_assets)
    
    # Diğer sekmeler
    with tab_bist:
        render_news_section("BIST Haberleri", "BIST")
    with tab_kripto:
        render_news_section("Kripto Haberleri", "KRIPTO")
    with tab_global:
        render_news_section("Global Piyasalar", "GLOBAL")
    with tab_doviz:
        render_news_section("Döviz / Altın", "DOVIZ")

elif selected == "İzleme":
    st.subheader("👁️ İzleme Listesi")
    if not takip_only.empty:
        # İzleme listesi için: Kod, Pazar, Maliyet (eklediğindeki fiyat), Fiyat (güncel), Değişim %
        takip_display = takip_only[["Kod", "Pazar", "Maliyet", "Fiyat", "Top. %"]].copy()
        takip_display = takip_display.rename(columns={"Top. %": "Değişim %"})
        
        # Tablo başlıkları
        header_col1, header_col2, header_col3, header_col4, header_col5, header_col6 = st.columns([2, 2, 2, 2, 2, 1])
        with header_col1:
            st.markdown("**Kod**")
        with header_col2:
            st.markdown("**Pazar**")
        with header_col3:
            st.markdown("**Maliyet**")
        with header_col4:
            st.markdown("**Fiyat**")
        with header_col5:
            st.markdown("**Değişim %**")
        with header_col6:
            st.markdown("**İşlem**")
        
        st.markdown("<hr style='margin: 5px 0; border-color: #2f3440;'>", unsafe_allow_html=True)
        
        # Her satır için silme butonu ekle
        for idx, row in takip_display.iterrows():
            col1, col2, col3, col4, col5, col6 = st.columns([2, 2, 2, 2, 2, 1])
            
            with col1:
                st.write(f"**{row['Kod']}**")
            with col2:
                st.write(row['Pazar'])
            with col3:
                st.write(f"{row['Maliyet']:,.2f}")
            with col4:
                st.write(f"{row['Fiyat']:,.2f}")
            with col5:
                # Değişim % renklendirilmiş göster
                pct = row['Değişim %']
                if pct > 0:
                    st.markdown(f'<span style="color: #00e676; font-weight: 900;">+{pct:.2f}%</span>', unsafe_allow_html=True)
                elif pct < 0:
                    st.markdown(f'<span style="color: #ff5252; font-weight: 900;">{pct:.2f}%</span>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<span style="color: #cccccc; font-weight: 900;">{pct:.2f}%</span>', unsafe_allow_html=True)
            with col6:
                # Silme butonu
                if st.button("🗑️", key=f"sil_takip_{row['Kod']}_{idx}", help="Sil"):
                    # portfoy_df'den bu kodu ve Tip="Takip" olan satırı sil
                    kod = row['Kod']
                    portfoy_df = portfoy_df[~((portfoy_df["Kod"] == kod) & (portfoy_df["Tip"] == "Takip"))]
                    save_data_to_sheet(portfoy_df)
                    st.success(f"{kod} izleme listesinden silindi!")
                    time.sleep(1)
                    st.rerun()
            
            # Satırlar arası ayırıcı
            st.markdown("<hr style='margin: 5px 0; border-color: #2f3440;'>", unsafe_allow_html=True)
    else:
        st.info("İzleme listesi boş.")

elif selected == "Satışlar":
    st.subheader("🧾 Satış Geçmişi")
    sales_df = get_sales_history()
    if not sales_df.empty:
        st.dataframe(
            styled_dataframe(sales_df),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("Satış kaydı yok.")


elif selected == "Ekle/Çıkar":
    st.header("Varlık Yönetimi")
    tab1, tab2, tab3 = st.tabs(["Ekle", "Düzenle", "Sil/Sat"])

    # ---------------- EKLE ----------------
    with tab1:
        # Pazar seçimi
        pazar = st.selectbox("Pazar", list(MARKET_DATA.keys()), key="ekle_pazar")

        # Kod manuel girilecek
        kod = st.text_input("Kod (Örn: BTC, THYAO)", key="ekle_kod_manu").upper()

        # Takip mi, portföy mü?
        is_takip = st.checkbox(
            "Sadece izleme listesine ekle (Takip)",
            value=False,
            key="ekle_is_takip",
        )

        if is_takip:
            st.caption(
                "Takip modunda adet girmen gerekmiyor; sistem 1 adet ve güncel fiyatla kaydeder."
            )
            adet_str = "1"
            maliyet_str = "0"
        else:
            c1, c2 = st.columns(2)
            adet_str = c1.text_input("Adet/Kontrat", "0", key="ekle_adet")
            maliyet_str = c2.text_input("Giriş Fiyatı", "0", key="ekle_maliyet")

        if st.button("Kaydet", key="ekle_kaydet"):
            if not kod:
                st.error("Kod boş olamaz.")
            else:
                if is_takip:
                    # İZLEME LİSTESİ: adet=1, fiyatı internetten çek
                    tip = "Takip"
                    a = 1

                    try:
                        yahoo_code = get_yahoo_symbol(kod, pazar)
                        t = yf.Ticker(yahoo_code)
                        h = t.history(period="1d")
                        if not h.empty:
                            m = float(h["Close"].iloc[-1])
                        else:
                            m = 0.0
                    except Exception:
                        m = 0.0

                    if m <= 0:
                        st.error(
                            "Güncel fiyat alınamadı. İstersen fiyatı elle girmek için "
                            "'Takip' kutusunu kaldırıp normal ekleme yap."
                        )
                        st.stop()
                else:
                    # PORTFÖY KAYDI
                    tip = "Portfoy"
                    a = smart_parse(adet_str)
                    m = smart_parse(maliyet_str)
                    if a <= 0 or m <= 0:
                        st.error("Adet ve maliyet pozitif olmalı.")
                        st.stop()

                # Aynı Kod + Tip varsa -> ağırlıklı ortalama maliyet
                if "Tip" in portfoy_df.columns:
                    mask = (portfoy_df["Kod"] == kod) & (portfoy_df["Tip"] == tip)
                else:
                    mask = portfoy_df["Kod"] == kod

                if mask.any():
                    eski = portfoy_df[mask].iloc[0]
                    eski_adet = smart_parse(eski.get("Adet", 0))
                    eski_maliyet = smart_parse(eski.get("Maliyet", 0))

                    if tip == "Portfoy":
                        toplam_adet = eski_adet + a
                        if toplam_adet > 0:
                            yeni_maliyet = (
                                eski_adet * eski_maliyet + a * m
                            ) / toplam_adet
                        else:
                            yeni_maliyet = m
                        a = toplam_adet
                        m = yeni_maliyet
                    else:
                        # Takip satırında adet 1 kalır, sadece son fiyat güncellenir
                        pass

                    # Eski satırı temizle
                    portfoy_df = portfoy_df[~mask]

                # Yeni / güncellenmiş satırı ekle
                new_row = pd.DataFrame(
                    {
                        "Kod": [kod],
                        "Pazar": [pazar],
                        "Adet": [a],
                        "Maliyet": [m],
                        "Tip": [tip],
                        "Notlar": [""],
                    }
                )
                portfoy_df = pd.concat([portfoy_df, new_row], ignore_index=True)
                save_data_to_sheet(portfoy_df)

                st.success(
                    "İzleme listesine eklendi!"
                    if is_takip
                    else "Portföye eklendi!"
                )
                time.sleep(1)
                st.rerun()


    # DÜZENLE
    with tab2:
        if not portfoy_df.empty:
            s = st.selectbox("Seç", portfoy_df["Kod"].unique())
            if s:
                r = portfoy_df[portfoy_df["Kod"] == s].iloc[0]
                na = st.text_input("Yeni Adet", str(r["Adet"]))
                nm = st.text_input("Yeni Maliyet", str(r["Maliyet"]))
                if st.button("Güncelle"):
                    portfoy_df = portfoy_df[portfoy_df["Kod"] != s]
                    new_row = pd.DataFrame(
                        {
                            "Kod": [s],
                            "Pazar": [r["Pazar"]],
                            "Adet": [smart_parse(na)],
                            "Maliyet": [smart_parse(nm)],
                            "Tip": [r["Tip"]],
                            "Notlar": [""],
                        }
                    )
                    portfoy_df = pd.concat(
                        [portfoy_df, new_row], ignore_index=True
                    )
                    save_data_to_sheet(portfoy_df)
                    st.success("Güncellendi!")
                    time.sleep(1)
                    st.rerun()

    # SİL / SAT
    with tab3:
        if portfoy_df.empty:
            st.info("Portföyde silinecek / satılacak varlık yok.")
        else:
            islem_turu = st.radio(
                "İşlem Türü",
                ["Sil", "Sat (Satış Kaydı Oluştur)"],
                horizontal=True,
            )

            if islem_turu == "Sil":
                s = st.selectbox("Silinecek Kod", portfoy_df["Kod"].unique(), key="del")
                if st.button("🗑️ Sil"):
                    portfoy_df = portfoy_df[portfoy_df["Kod"] != s]
                    save_data_to_sheet(portfoy_df)
                    st.success("Silindi!")
                    time.sleep(1)
                    st.rerun()

            else:  # Satış Kaydı
                kodlar = sorted(portfoy_df["Kod"].unique())
                kod_sec = st.selectbox("Satılacak Kod", kodlar, key="sell_code")

                secili = portfoy_df[portfoy_df["Kod"] == kod_sec].iloc[0]
                mevcut_adet = smart_parse(secili["Adet"])
                birim_maliyet = smart_parse(secili["Maliyet"])
                pazar = secili["Pazar"]

                st.write(f"Mevcut Adet: **{mevcut_adet}**")
                st.write(f"Birim Maliyet: **{birim_maliyet}**")

                c1, c2 = st.columns(2)
                sat_adet_str = c1.text_input("Satılacak Adet", str(mevcut_adet))
                satis_fiyat_str = c2.text_input("Satış Fiyatı (Birim)", "0")

                if st.button("💰 Satışı Kaydet"):
                    sat_adet = smart_parse(sat_adet_str)
                    satis_fiyat = smart_parse(satis_fiyat_str)

                    if sat_adet <= 0 or satis_fiyat <= 0:
                        st.error("Satış adedi ve fiyatı pozitif olmalı.")
                    elif sat_adet > mevcut_adet:
                        st.error("Satılacak adet mevcut adetten fazla olamaz.")
                    else:
                        # Hesaplar
                        toplam_satis = sat_adet * satis_fiyat
                        maliyet_tutar = sat_adet * birim_maliyet
                        kar_zarar = toplam_satis - maliyet_tutar

                        # Satış kaydını Sheets'e yaz
                        add_sale_record(
                            datetime.now().date(),
                            kod_sec,
                            pazar,
                            sat_adet,
                            satis_fiyat,
                            maliyet_tutar,
                            kar_zarar,
                        )

                        # Portföyde adeti güncelle / sıfırsa satır sil
                        kalan_adet = mevcut_adet - sat_adet
                        if kalan_adet <= 0:
                            portfoy_df = portfoy_df[portfoy_df["Kod"] != kod_sec]
                        else:
                            portfoy_df.loc[
                                portfoy_df["Kod"] == kod_sec, "Adet"
                            ] = kalan_adet

                        save_data_to_sheet(portfoy_df)

                        st.success(
                            f"Satış kaydedildi. Toplam satış: {toplam_satis:,.2f}, "
                            f"Maliyet: {maliyet_tutar:,.2f}, Kâr/Zarar: {kar_zarar:,.2f}"
                        )
                        time.sleep(1)
                        st.rerun()

# Otomatik yenileme kaldırıldı - sadece sayaç gösterimi var
# Burada ayrı bir timer'a gerek yok
