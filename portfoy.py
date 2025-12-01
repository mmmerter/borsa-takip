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

# Profile management
from profile_manager import (
    init_session_state as init_profile_session,
    get_current_profile,
    render_profile_selector,
    is_aggregate_profile,
    get_profile_display_name,
    get_profile_config,
)

# Use profile-aware data loader
from data_loader_profiles import (
    get_data_from_sheet_profile as get_data_from_sheet,
    save_data_to_sheet_profile as save_data_to_sheet,
    get_sales_history_profile as get_sales_history,
    add_sale_record_profile as add_sale_record,
    read_portfolio_history_profile as read_portfolio_history,
    write_portfolio_history_profile as write_portfolio_history,
    read_history_bist_profile as read_history_bist,
    write_history_bist_profile as write_history_bist,
    read_history_abd_profile as read_history_abd,
    write_history_abd_profile as write_history_abd,
    read_history_fon_profile as read_history_fon,
    write_history_fon_profile as write_history_fon,
    read_history_emtia_profile as read_history_emtia,
    write_history_emtia_profile as write_history_emtia,
    read_history_nakit_profile as read_history_nakit,
    write_history_nakit_profile as write_history_nakit,
    get_daily_base_prices_profile as get_daily_base_prices,
    update_daily_base_prices_profile as update_daily_base_prices,
)

# Import non-profile specific functions from data_loader
from data_loader import (
    get_usd_try,
    get_tickers_data,
    get_financial_news,
    get_portfolio_news,
    get_tefas_data,
    get_timeframe_changes,
    get_history_summary,
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
    render_modern_list_header,
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

# Initialize profile system
init_profile_session()

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
# CSS kodları artık ui_styles.py modülünden yükleniyor - kod kalabalığı azaltıldı
from ui_styles import inject_css, get_menu_styles
inject_css()  # Tüm CSS'ler otomatik enjekte edilir (responsive, berguzar, light tema dahil)

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
# Manuel yenileme butonu - F5 yaptığınızda güncel veriler için
col_refresh, col_space = st.columns([0.15, 0.85])
with col_refresh:
    if st.button("🔄 Yenile", help="Tüm verileri yeniden yükle (cache'i temizle)", key="refresh_button"):
        # Tüm kritik cache'leri temizle
        get_data_from_sheet.clear()
        get_usd_try.clear()
        get_tickers_data.clear()
        # Batch cache fonksiyonlarını da temizle
        _fetch_batch_prices_bist_abd.clear()
        _fetch_batch_prices_crypto.clear()
        _fetch_batch_prices_emtia.clear()
        st.rerun()

# Lazy loading ile performans optimizasyonu
with st.spinner("📊 Portföy verileri yükleniyor..."):
    portfoy_df = get_data_from_sheet()

# --- HEADER ---
with st.spinner("💱 Döviz kuru alınıyor..."):
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

# --- PROFİL SEÇİCİ ---
st.markdown("---")
render_profile_selector()
current_profile = get_current_profile()
is_total = is_aggregate_profile(current_profile)

# Profil bazlı CSS class ekle (Bergüzar için pembe tema)
if current_profile == "BERGUZAR":
    st.markdown(
        """
        <div class="profile-berguzar-active">
        <script>
        (function() {
            function addClass() {
                var containers = document.querySelectorAll('[data-testid="stAppViewContainer"]');
                containers.forEach(function(container) {
                    container.classList.add('profile-berguzar-active');
                });
                var body = document.body;
                if (body) body.classList.add('profile-berguzar-active');
            }
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', addClass);
            } else {
                addClass();
            }
        })();
        </script>
        </div>
        """,
        unsafe_allow_html=True
    )

# Profil bazlı CSS class ekle
if current_profile == "BERGUZAR":
    st.markdown('<body class="profile-berguzar">', unsafe_allow_html=True)

# TOTAL profili için uyarı göster
if is_total:
    st.info("📊 **TOPLAM Profili**: Tüm profillerin birleşik görünümü. Veri eklenemez veya düzenlenemez.")

st.markdown("---")

# Ticker verilerini lazy loading ile yükle
with st.spinner("📈 Piyasa verileri güncelleniyor..."):
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

# --- MENÜ (7 Buton) - Modern ---
selected = option_menu(
    menu_title=None,
    options=[
        "Dashboard",
        "Portföy",
        "İzleme",
        "Satışlar",
        "Haberler",
        "Ekle/Çıkar",
        "Profil Yönetimi",
    ],
    icons=[
        "speedometer2",
        "pie-chart-fill",
        "eye",
        "receipt",
        "newspaper",
        "gear",
        "person-gear",
    ],
    menu_icon="cast",
    default_index=0,
    orientation="horizontal",
    styles=get_menu_styles(st.session_state["ui_theme"]),
)


# --- ANALİZ ---
@st.cache_data(ttl=600)  # 10 dakika cache - BIST ve ABD için optimize edildi
def _fetch_batch_prices_bist_abd(symbols_list, period="5d"):
    """Batch olarak BIST ve ABD fiyat verilerini çeker - borsa kapalıyken de son kapanış fiyatını döndürür"""
    if not symbols_list:
        return {}
    prices = {}
    
    # Önce batch deneme - timeout ile optimize edilmiş
    try:
        tickers = yf.Tickers(" ".join(symbols_list))
        for sym in symbols_list:
            try:
                # Timeout ekle - daha hızlı hata yakalama
                h = tickers.tickers[sym].history(period=period, timeout=15)
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

@st.cache_data(ttl=300)  # 5 dakika cache - Kripto için optimize edildi
def _fetch_batch_prices_crypto(symbols_list, period="5d"):
    """Batch olarak Kripto fiyat verilerini çeker - optimize edilmiş"""
    if not symbols_list:
        return {}
    prices = {}
    
    try:
        tickers = yf.Tickers(" ".join(symbols_list))
        for sym in symbols_list:
            try:
                # Timeout ekle - daha hızlı hata yakalama
                h = tickers.tickers[sym].history(period=period, timeout=15)
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

@st.cache_data(ttl=600)  # 10 dakika cache - EMTIA için optimize edildi
def _fetch_batch_prices_emtia(symbols_list, period="5d"):
    """Batch olarak EMTIA fiyat verilerini çeker"""
    if not symbols_list:
        return {}
    prices = {}
    
    try:
        tickers = yf.Tickers(" ".join(symbols_list))
        for sym in symbols_list:
            try:
                # Timeout ekle - daha hızlı hata yakalama
                h = tickers.tickers[sym].history(period=period, timeout=15)
                if not h.empty:
                    curr = h["Close"].iloc[-1]
                    prev = h["Close"].iloc[-2] if len(h) > 1 else curr
                    prices[sym] = {"curr": curr, "prev": prev}
                else:
                    prices[sym] = {"curr": 0, "prev": 0}
            except Exception:
                try:
                    ticker = yf.Ticker(sym)
                    h = ticker.history(period=period, timeout=15)
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

@st.cache_data(ttl=1800)  # 30 dakika cache - sektör bilgileri çok az değişir
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
        elif "Gram Altın" in kod or "GRAM ALTIN" in kod or "22 Ayar" in kod or "22 AYAR" in kod:
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
            elif "22 Ayar" in kod or "22 AYAR" in kod:
                # 22 ayar altın = 22/24 = 0.9167 (91.67% saf altın)
                if "GC=F" in gram_prices_5d:
                    p_data = gram_prices_5d["GC=F"]
                    # Ons fiyatını grama çevir, sonra 22 ayar oranıyla çarp
                    curr = ((p_data["curr"] * usd_try_rate) / 31.1035) * 0.9167
                    prev = ((p_data["prev"] * usd_try_rate) / 31.1035) * 0.9167
            elif "Gram Altın" in kod or "GRAM ALTIN" in kod:
                # 24 ayar (saf) gram altın
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
def render_kral_infobar(df, sym, gorunum_pb=None, usd_try_rate=None, timeframe=None, show_sparklines=False, daily_base_prices=None):
    """
    KRAL infobar:
    - Toplam Varlık
    - Günlük K/Z (00:30'da sıfırlanan)
    - Haftalık / Aylık / YTD (opsiyonel, timeframe ile)
    - İstenirse altında mini sparkline'lar
    """
    if df is None or df.empty:
        return

    # Mevcut görünümdeki toplam değer (df'nin para biriminde)
    total_value_view = df["Değer"].sum()
    
    # Günlük K/Z hesaplama - 00:30 baz fiyatlarını kullan
    if daily_base_prices is not None and not daily_base_prices.empty:
        # Baz fiyatlardan günlük K/Z hesapla
        daily_pnl = 0.0
        for _, row in df.iterrows():
            kod = row["Kod"]
            current_value = row["Değer"]
            adet = row.get("Adet", 0)
            
            # Baz fiyatı bul
            base_row = daily_base_prices[daily_base_prices["Kod"] == kod]
            if not base_row.empty:
                base_price = float(base_row.iloc[0]["Fiyat"])
                
                # Para birimi dönüşümü
                pb = row.get("PB", "TRY")
                if gorunum_pb == "TRY":
                    if pb == "USD":
                        base_value = base_price * adet * usd_try_rate
                    else:
                        base_value = base_price * adet
                else:  # USD
                    if pb == "TRY":
                        base_value = base_price * adet / usd_try_rate
                    else:
                        base_value = base_price * adet
                
                daily_pnl += (current_value - base_value)
            else:
                # Baz fiyat yoksa, eski yöntemi kullan (önceki günün kapanışı)
                daily_pnl += row.get("Gün. Kâr/Zarar", 0)
    else:
        # Baz fiyatlar yoksa, eski yöntemi kullan
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
            weekly_data = timeframe.get("weekly", None)
            monthly_data = timeframe.get("monthly", None)
            ytd_data = timeframe.get("ytd", None)

            # Haftalık / Aylık / YTD değerler her zaman TRY bazlı tutuluyor
            # Görünüm USD ise, gösterirken USD'ye çeviriyoruz.
            show_sym = sym
            
            # Haftalık
            if weekly_data is not None:
                w_val, w_pct = weekly_data
                if gorunum_pb == "USD" and usd_try_rate:
                    weekly_txt = f"{show_sym}{(w_val / usd_try_rate):,.0f} ({w_pct:+.2f}%)"
                else:
                    weekly_txt = f"{show_sym}{w_val:,.0f} ({w_pct:+.2f}%)"
            else:
                weekly_txt = "⚠️ Yetersiz Veri"
                w_pct = 0
            
            # Aylık
            if monthly_data is not None:
                m_val, m_pct = monthly_data
                if gorunum_pb == "USD" and usd_try_rate:
                    monthly_txt = f"{show_sym}{(m_val / usd_try_rate):,.0f} ({m_pct:+.2f}%)"
                else:
                    monthly_txt = f"{show_sym}{m_val:,.0f} ({m_pct:+.2f}%)"
            else:
                monthly_txt = "⚠️ Yetersiz Veri"
                m_pct = 0
            
            # YTD
            if ytd_data is not None:
                y_val, y_pct = ytd_data
                if gorunum_pb == "USD" and usd_try_rate:
                    ytd_txt = f"{show_sym}{(y_val / usd_try_rate):,.0f} ({y_pct:+.2f}%)"
                else:
                    ytd_txt = f"{show_sym}{y_val:,.0f} ({y_pct:+.2f}%)"
            else:
                ytd_txt = "⚠️ Yetersiz Veri"
                y_pct = 0
        except Exception:
            # Herhangi bir sorun olursa placeholder'da kalsın
            weekly_txt = "—"
            monthly_txt = "—"
            ytd_txt = "—"

    # Veri durumu bilgisi (varsa)
    data_info_html = ""
    if timeframe is not None and "data_days" in timeframe:
        data_days = timeframe.get("data_days", 0)
        oldest_date = timeframe.get("oldest_date", "")
        newest_date = timeframe.get("newest_date", "")
        
        if data_days < 30:
            data_info_html = f"""
            <div style="
                background: linear-gradient(135deg, rgba(255, 193, 7, 0.15) 0%, rgba(255, 152, 0, 0.1) 100%);
                border-left: 3px solid #ffc107;
                border-radius: 8px;
                padding: 12px 16px;
                margin-bottom: 16px;
                color: #ffc107;
                font-size: 13px;
                font-weight: 600;
            ">
                ⚠️ <b>Tarihsel Veri Uyarısı:</b> Sadece {data_days} günlük veri var ({oldest_date} - {newest_date}). 
                Doğru haftalık/aylık performans için en az 30 gün veri gerekiyor. 
                Uygulamanın her gün çalışmasıyla veri birikecek.
            </div>
            """
    
    st.markdown(data_info_html, unsafe_allow_html=True)
    
    st.markdown(
        f"""
        <div class="kral-infobar">
            <div class="kral-infobox">
                <div class="kral-infobox-label">Toplam Varlık</div>
                <span class="kral-infobox-value">{sym}{total_value_view:,.0f}</span>
                <div class="kral-infobox-sub">Bu görünümdeki toplam varlık</div>
            </div>
            <div class="kral-infobox">
                <div class="kral-infobox-label">Günlük K/Z</div>
                <span class="kral-infobox-value">{daily_sign} {sym}{abs(daily_pnl):,.0f}</span>
                <div class="kral-infobox-sub">Bugün saat 00:30'dan beri</div>
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


def _compute_daily_pct(df, daily_base_prices=None, usd_try_rate=None, gorunum_pb=None):
    """
    Günlük yüzde değişimi hesaplar.
    
    00:30'da reset edilen baz fiyatları kullanır (varsa).
    Baz fiyatlar yoksa, eski yöntemi kullanır (önceki günün kapanış fiyatı).
    
    Args:
        df: Portfolio dataframe
        daily_base_prices: 00:30'da kaydedilen baz fiyatlar (opsiyonel)
        usd_try_rate: USD/TRY kuru (opsiyonel, baz fiyat kullanımı için gerekli)
        gorunum_pb: Görünüm para birimi (opsiyonel, baz fiyat kullanımı için gerekli)
    """
    if df is None or df.empty:
        return pd.DataFrame()
    required_cols = {"Kod", "Değer", "Gün. Kâr/Zarar"}
    if not required_cols.issubset(df.columns):
        return pd.DataFrame()

    work = df.copy()
    work["Günlük %"] = 0.0
    
    # Baz fiyatlar varsa, bunları kullanarak günlük değişim hesapla
    if daily_base_prices is not None and not daily_base_prices.empty and usd_try_rate is not None and gorunum_pb is not None:
        for idx, row in work.iterrows():
            kod = row["Kod"]
            current_value = row["Değer"]
            adet = row.get("Adet", 0)
            
            # Baz fiyatı bul
            base_row = daily_base_prices[daily_base_prices["Kod"] == kod]
            if not base_row.empty and adet > 0:
                base_price = float(base_row.iloc[0]["Fiyat"])
                base_pb = base_row.iloc[0].get("PB", "TRY")
                
                # Para birimi dönüşümü
                pb = row.get("PB", "TRY")
                if gorunum_pb == "TRY":
                    if base_pb == "USD":
                        base_value = base_price * adet * usd_try_rate
                    else:
                        base_value = base_price * adet
                else:  # USD
                    if base_pb == "TRY":
                        base_value = base_price * adet / usd_try_rate
                    else:
                        base_value = base_price * adet
                
                # Günlük değişim yüzdesi (00:30 baz fiyatına göre)
                if base_value > 0:
                    work.at[idx, "Günlük %"] = ((current_value - base_value) / base_value) * 100
                    # Günlük K/Z'ı da güncelle (00:30 bazında)
                    work.at[idx, "Gün. Kâr/Zarar"] = current_value - base_value
            else:
                # Baz fiyat bulunamazsa, eski yöntemi kullan
                safe_val = current_value - row["Gün. Kâr/Zarar"]
                if safe_val != 0:
                    work.at[idx, "Günlük %"] = (row["Gün. Kâr/Zarar"] / safe_val) * 100
    else:
        # Baz fiyatlar yoksa, eski yöntemi kullan
        safe_val = work["Değer"] - work["Gün. Kâr/Zarar"]
        non_zero = safe_val.notna() & (safe_val != 0)
        if non_zero.any():
            work.loc[non_zero, "Günlük %"] = (
                work.loc[non_zero, "Gün. Kâr/Zarar"] / safe_val[non_zero]
            ) * 100
    
    work["Günlük %"] = work["Günlük %"].fillna(0.0)
    return work


def get_daily_movers(df, top_n=5, daily_base_prices=None, usd_try_rate=None, gorunum_pb=None):
    """
    Günün kazananları ve kaybedenleri listesini döndürür.
    00:30'da reset edilen baz fiyatlara göre sıralanır.
    
    Args:
        df: Portfolio dataframe
        top_n: Kaç varlık gösterilecek
        daily_base_prices: 00:30'da kaydedilen baz fiyatlar (opsiyonel)
        usd_try_rate: USD/TRY kuru (opsiyonel)
        gorunum_pb: Görünüm para birimi (opsiyonel)
    """
    enriched = _compute_daily_pct(df, daily_base_prices, usd_try_rate, gorunum_pb)
    if enriched.empty:
        return pd.DataFrame(), pd.DataFrame()
    winners = enriched.sort_values("Günlük %", ascending=False).head(top_n)
    losers = enriched.sort_values("Günlük %", ascending=True).head(top_n)
    return winners, losers


def render_daily_movers_section(df, currency_symbol, top_n=5, daily_base_prices=None, usd_try_rate=None, gorunum_pb=None):
    """
    Günlük kazanan/kaybeden listesini modern kart formatında göster.
    00:30'da reset edilen baz fiyatlara göre sıralanır.
    
    Args:
        df: Portfolio dataframe
        currency_symbol: Para birimi sembolü (₺ veya $)
        top_n: Kaç varlık gösterilecek
        daily_base_prices: 00:30'da kaydedilen baz fiyatlar (opsiyonel)
        usd_try_rate: USD/TRY kuru (opsiyonel)
        gorunum_pb: Görünüm para birimi (opsiyonel)
    """
    winners, losers = get_daily_movers(df, top_n=top_n, daily_base_prices=daily_base_prices, 
                                       usd_try_rate=usd_try_rate, gorunum_pb=gorunum_pb)
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

        # Günlük baz fiyatları al (00:30'da kaydedilen)
        daily_base_prices = None
        try:
            daily_base_prices = get_daily_base_prices()
            
            # 00:30'dan sonraysa ve henüz bugün için kayıt yoksa, baz fiyatları güncelle
            current_prices_for_base = spot_only[["Kod", "Fiyat", "PB"]].copy()
            update_daily_base_prices(current_prices_for_base)
        except Exception:
            daily_base_prices = None
        
        # ⚠️ ANORMAL GÜNLÜK K/Z UYARISI (Güvenlik Önlemi)
        # Eğer günlük K/Z portföyün %15'inden fazla düşüş gösteriyorsa uyar
        if daily_base_prices is not None and not daily_base_prices.empty:
            daily_pnl_check = 0.0
            for _, row in spot_only.iterrows():
                kod = row["Kod"]
                current_value = row["Değer"]
                adet = row.get("Adet", 0)
                base_row = daily_base_prices[daily_base_prices["Kod"] == kod]
                if not base_row.empty and adet > 0:
                    base_price = float(base_row.iloc[0]["Fiyat"])
                    pb = row.get("PB", "TRY")
                    base_pb = base_row.iloc[0].get("PB", "TRY")
                    if GORUNUM_PB == "TRY":
                        base_value = base_price * adet * (USD_TRY if base_pb == "USD" else 1)
                    else:
                        base_value = base_price * adet * (1 if base_pb == "USD" else 1/USD_TRY)
                    daily_pnl_check += (current_value - base_value)
            
            # Portföy değerinin %15'inden fazla düşüş varsa uyar
            portfolio_value = spot_only["Değer"].sum()
            if portfolio_value > 0:
                daily_pct_check = (daily_pnl_check / portfolio_value) * 100
                if daily_pct_check < -15:
                    st.warning(f"""
                    ⚠️ **ANORMAL GÜNLÜK DEĞİŞİM TESPİT EDİLDİ**
                    
                    Günlük K/Z: **{sym}{daily_pnl_check:,.0f}** ({daily_pct_check:.2f}%)
                    
                    Bu kadar büyük bir günlük düşüş normalden fazla. Olası nedenler:
                    - 🔄 Baz fiyatlar (00:30'da kaydedilen) hatalı olabilir
                    - 📉 Piyasada gerçekten büyük düşüş yaşanmış olabilir
                    - 💱 Para birimi dönüşümlerinde sorun olabilir
                    
                    **Önerilen İşlemler:**
                    1. Portföy sayfasını yenileyin (F5)
                    2. Birkaç dakika sonra tekrar kontrol edin
                    3. Sorun devam ederse, Google Sheets'teki `daily_base_prices` sayfasını kontrol edin
                    """, icon="⚠️")

        # INFO BAR (Toplam Varlık + Günlük K/Z + Haftalık/Aylık/YTD + Sparkline)
        render_kral_infobar(
            spot_only,
            sym,
            gorunum_pb=GORUNUM_PB,
            usd_try_rate=USD_TRY,
            timeframe=kpi_timeframe,
            show_sparklines=True,
            daily_base_prices=daily_base_prices,
        )

        # Eski 2 metric (Toplam Varlık + Genel K/Z) yine dursun
        c1, c2 = st.columns(2)
        # Toplam Varlık için: Toplam kâr/zarar yüzdesi (maliyete göre) - zaman aralığı belirtilmeli
        c1.metric("Toplam Varlık", f"{sym}{t_v:,.0f}", delta=f"{pct:.2f}% (Başlangıçtan Beri)")
        c2.metric("Genel Kâr/Zarar", f"{sym}{t_p:,.0f}", delta=f"{pct:.2f}% (Maliyete Göre)")

        st.divider()

        # --- PAZAR DAĞILIMI ---
        render_modern_list_header(
            title="Pazarlara Göre Dağılım",
            icon="🌍",
            subtitle="Varlıklarınızın hangi pazarlarda dağıldığını görüntüleyin"
        )
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
        render_daily_movers_section(spot_only, sym, top_n=5, 
                                   daily_base_prices=daily_base_prices,
                                   usd_try_rate=USD_TRY, 
                                   gorunum_pb=GORUNUM_PB)

        render_modern_list_header(
            title="Portföy Isı Haritası",
            icon="🗺️",
            subtitle="Varlıklarınızın performansını görsel olarak keşfedin"
        )
        
        c_tree_1, c_tree_2 = st.columns([3, 1])
        with c_tree_1:
            st.write("")  # Boş alan
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
            
            # Günlük değişim hesaplama - 00:30 baz fiyatlarını kullan
            if daily_base_prices is not None and not daily_base_prices.empty and map_mode == "Günlük Değişim %":
                # Baz fiyatları kullanarak günlük değişim hesapla
                heat_df = _compute_daily_pct(heat_df, daily_base_prices, USD_TRY, GORUNUM_PB)
                color_col = "Günlük %"
            else:
                # Eski yöntemi kullan (baz fiyatlar yoksa veya genel kâr modu seçiliyse)
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
            
            # Günlük % kolonunu normalize et (hem "Günlük %" hem "Gün. %" olabilir)
            if "Günlük %" in heat_df.columns and "Gün. %" not in heat_df.columns:
                heat_df["Gün. %"] = heat_df["Günlük %"]
            elif "Gün. %" not in heat_df.columns:
                heat_df["Gün. %"] = 0.0
            
            heat_df["Gün. %_formatted"] = heat_df["Gün. %"].round(1)
            
            # Renk kolonu ayarla
            if color_col == "Günlük %":
                color_col = "Gün. %"

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
            render_modern_list_header(
                title="Sektörel Dağılım",
                icon="🏭",
                subtitle="Hangi sektörlere yatırım yaptığınızı keşfedin • Şirket detayları hover ile görülebilir"
            )
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
        render_modern_list_header(
            title="Portföy Karşılaştırmaları",
            icon="📊",
            subtitle="Portföyünüzün performansını benchmark'larla karşılaştırın"
        )
        
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
        render_modern_list_header(
            title="Tarihsel Portföy Değeri",
            icon="📈",
            subtitle="Portföyünüzün zaman içindeki değer değişimini inceleyin"
        )
        col_title, col_date = st.columns([2, 1])
        with col_title:
            st.write("")  # Boş alan
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
        render_modern_list_header(
            title="Tarihsel Değer - Tümü",
            icon="📈",
            subtitle="Tüm varlıklarınızın toplam değer grafiği"
        )
        col_title, col_date = st.columns([2, 1])
        with col_title:
            st.write("")  # Boş alan
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
            render_modern_list_header(
                title="Sektörel Dağılım - BIST",
                icon="🏭",
                subtitle="BIST hisselerinizin sektörel dağılımı • Şirketler hover ile görünür"
            )
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
        
        render_modern_list_header(
            title="Tarihsel Değer - BIST",
            icon="📈",
            subtitle="BIST varlıklarınızın zaman içindeki performansı"
        )
        col_title, col_date = st.columns([2, 1])
        with col_title:
            st.write("")  # Boş alan
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
            render_modern_list_header(
                title="Sektörel Dağılım - ABD",
                icon="🏭",
                subtitle="ABD hisselerinizin sektörel dağılımı • Şirketler hover ile görünür"
            )
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
        
        render_modern_list_header(
            title="Tarihsel Değer - ABD",
            icon="📈",
            subtitle="ABD varlıklarınızın zaman içindeki performansı"
        )
        col_title, col_date = st.columns([2, 1])
        with col_title:
            st.write("")  # Boş alan
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
        render_modern_list_header(
            title="Tarihsel Değer - Fonlar",
            icon="📈",
            subtitle="Yatırım fonu varlıklarınızın zaman içindeki performansı"
        )
        col_title, col_date = st.columns([2, 1])
        with col_title:
            st.write("")  # Boş alan
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
        render_modern_list_header(
            title="Tarihsel Değer - Emtia",
            icon="📈",
            subtitle="Altın, gümüş ve diğer emtia varlıklarınızın performansı"
        )
        col_title, col_date = st.columns([2, 1])
        with col_title:
            st.write("")  # Boş alan
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
        render_modern_list_header(
            title="Tarihsel Değer - Kripto",
            icon="📈",
            subtitle="Kripto para varlıklarınızın zaman içindeki değişimi"
        )
        col_title, col_date = st.columns([2, 1])
        with col_title:
            st.write("")  # Boş alan
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
        render_modern_list_header(
            title="Tarihsel Değer - Nakit",
            icon="📈",
            subtitle="Nakit ve döviz varlıklarınızın değer değişimi"
        )
        col_title, col_date = st.columns([2, 1])
        with col_title:
            st.write("")  # Boş alan
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
    render_modern_list_header(
        title="İzleme Listesi",
        icon="👁️",
        subtitle="Takip ettiğiniz varlıkların anlık fiyat ve değişim bilgileri"
    )
    
    if not takip_only.empty:
        # İzleme listesi için: Kod, Pazar, Maliyet (eklediğindeki fiyat), Fiyat (güncel), Değişim %
        takip_display = takip_only[["Kod", "Pazar", "Maliyet", "Fiyat", "Top. %"]].copy()
        takip_display = takip_display.rename(columns={"Top. %": "Değişim %"})
        
        # Pazar isimlerini modernize et
        pazar_modernize = {
            "BIST (Tümü)": "🇹🇷 Borsa İstanbul",
            "BIST": "🇹🇷 Borsa İstanbul",
            "ABD (S&P + NASDAQ)": "🇺🇸 ABD Borsaları",
            "ABD": "🇺🇸 Amerika",
            "NASDAQ": "🇺🇸 NASDAQ",
            "S&P": "🇺🇸 S&P 500",
            "FON": "📊 Yatırım Fonları",
            "Fonlar": "📊 Yatırım Fonları",
            "EMTIA": "💎 Altın &귀금속",
            "Emtia": "💎 Altın &귀금속",
            "NAKIT": "💵 Nakit & Döviz",
            "Nakit": "💵 Nakit & Döviz",
            "KRİPTO": "₿ Kripto Paralar",
            "Kripto": "₿ Kripto Paralar",
            "VADELİ": "📈 Vadeli İşlemler",
            "Vadeli": "📈 Vadeli İşlemler",
        }
        takip_display["Pazar"] = takip_display["Pazar"].replace(pazar_modernize)
        
        # Her satır için modern kart oluştur
        for idx, row in takip_display.iterrows():
            pct = row['Değişim %']
            
            # Renk ve emoji belirle
            if pct > 0:
                card_color = "rgba(0, 230, 118, 0.15)"
                border_color = "#00e676"
                pct_color = "#00e676"
                emoji = "📈"
            elif pct < 0:
                card_color = "rgba(255, 82, 82, 0.15)"
                border_color = "#ff5252"
                pct_color = "#ff5252"
                emoji = "📉"
            else:
                card_color = "rgba(255, 255, 255, 0.05)"
                border_color = "#6b7fd7"
                pct_color = "#9da1b3"
                emoji = "➖"
            
            col1, col2 = st.columns([6, 1])
            with col1:
                st.markdown(
                    f"""
                    <div style="
                        background: linear-gradient(135deg, {card_color} 0%, rgba(26, 28, 36, 0.5) 100%);
                        border-radius: 16px;
                        padding: 20px 24px;
                        margin-bottom: 16px;
                        border-left: 4px solid {border_color};
                        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
                        transition: all 0.3s ease;
                    " onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 6px 20px rgba(107, 127, 215, 0.4)';" 
                       onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 12px rgba(0, 0, 0, 0.3)';">
                        <div style="display: grid; grid-template-columns: 1.5fr 1fr 1fr 1fr 1fr; gap: 16px; align-items: center;">
                            <div>
                                <div style="font-size: 11px; color: #9da1b3; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px; font-weight: 600;">🎯 Varlık</div>
                                <div style="font-size: 22px; font-weight: 900; color: #ffffff; display: flex; align-items: center; gap: 8px;">
                                    <span>{emoji}</span>
                                    <span>{row['Kod']}</span>
                                </div>
                            </div>
                            <div>
                                <div style="font-size: 11px; color: #9da1b3; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px; font-weight: 600;">🌍 Piyasa</div>
                                <div style="font-size: 15px; font-weight: 700; color: #ffffff;">{row['Pazar']}</div>
                            </div>
                            <div>
                                <div style="font-size: 11px; color: #9da1b3; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px; font-weight: 600;">💰 Başlangıç</div>
                                <div style="font-size: 15px; font-weight: 700; color: #b0b3c0;">{row['Maliyet']:,.2f}</div>
                            </div>
                            <div>
                                <div style="font-size: 11px; color: #9da1b3; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px; font-weight: 600;">💵 Anlık Değer</div>
                                <div style="font-size: 16px; font-weight: 900; color: #ffffff;">{row['Fiyat']:,.2f}</div>
                            </div>
                            <div>
                                <div style="font-size: 11px; color: #9da1b3; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px; font-weight: 600;">📊 Performans</div>
                                <div style="font-size: 20px; font-weight: 900; color: {pct_color}; text-shadow: 0 0 12px {pct_color}80;">
                                    {'+' if pct > 0 else ''}{pct:.2f}%
                                </div>
                            </div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            with col2:
                # Silme butonu - modern stil
                if st.button("🗑️ Sil", key=f"sil_takip_{row['Kod']}_{idx}", help="Sil", use_container_width=True):
                    # portfoy_df'den bu kodu ve Tip="Takip" olan satırı sil
                    kod = row['Kod']
                    portfoy_df = portfoy_df[~((portfoy_df["Kod"] == kod) & (portfoy_df["Tip"] == "Takip"))]
                    save_data_to_sheet(portfoy_df)
                    st.success(f"{kod} izleme listesinden silindi!")
                    time.sleep(1)
                    st.rerun()
    else:
        st.info("İzleme listesi boş. Varlık eklemek için 'Ekle/Çıkar' sekmesine gidin.")

elif selected == "Satışlar":
    render_modern_list_header(
        title="Satış Geçmişi",
        icon="🧾",
        subtitle="Gerçekleştirdiğiniz tüm satış işlemlerinin detaylı kayıtları"
    )
    
    sales_df = get_sales_history()
    if not sales_df.empty:
        # Kolon isimlerini modernize et
        sales_display = sales_df.copy()
        
        # Pazar isimlerini modernize et
        if "Pazar" in sales_display.columns:
            pazar_modernize = {
                "BIST (Tümü)": "🇹🇷 Borsa İstanbul",
                "BIST": "🇹🇷 Borsa İstanbul",
                "ABD (S&P + NASDAQ)": "🇺🇸 ABD Borsaları",
                "ABD": "🇺🇸 Amerika",
                "NASDAQ": "🇺🇸 NASDAQ",
                "S&P": "🇺🇸 S&P 500",
                "FON": "📊 Yatırım Fonları",
                "Fonlar": "📊 Yatırım Fonları",
                "EMTIA": "💎 Altın &귀금속",
                "Emtia": "💎 Altın &귀금속",
                "NAKIT": "💵 Nakit & Döviz",
                "Nakit": "💵 Nakit & Döviz",
                "KRİPTO": "₿ Kripto Paralar",
                "Kripto": "₿ Kripto Paralar",
                "VADELİ": "📈 Vadeli İşlemler",
                "Vadeli": "📈 Vadeli İşlemler",
            }
            sales_display["Pazar"] = sales_display["Pazar"].replace(pazar_modernize)
        
        sales_display = sales_display.rename(columns={
            "Tarih": "📅 İşlem Tarihi",
            "Kod": "🎯 Varlık",
            "Pazar": "🌍 Piyasa",
            "Satılan Adet": "📦 Adet",
            "Satış Fiyatı": "💰 Satış Fiyatı",
            "Maliyet": "💵 Alış Fiyatı",
            "Kar/Zarar": "📊 Kâr/Zarar"
        })
        
        # Toplam özet metrikler ekle
        if "📊 Kâr/Zarar" in sales_display.columns:
            total_profit = sales_df["Kar/Zarar"].sum()
            total_sales_value = sales_df.get("Satış Tutarı", sales_df.get("Toplam Satış", pd.Series([0]))).sum()
            # Eğer total_sales_value 0 ise, Satış Fiyatı * Satılan Adet'i kullan
            if total_sales_value == 0 and "Satış Fiyatı" in sales_df.columns and "Satılan Adet" in sales_df.columns:
                total_sales_value = (sales_df["Satış Fiyatı"] * sales_df["Satılan Adet"]).sum()
            avg_profit_pct = sales_df["Kar/Zarar"].mean() if len(sales_df) > 0 else 0
            
            col1, col2, col3 = st.columns(3)
            col1.metric(
                "💎 Toplam Kâr/Zarar", 
                f"{sym}{total_profit:,.0f}",
                delta=f"{(total_profit / total_sales_value * 100) if total_sales_value > 0 else 0:.2f}%"
            )
            col2.metric(
                "💰 Toplam Satış Hasılatı", 
                f"{sym}{total_sales_value:,.0f}",
                delta=f"{len(sales_df)} başarılı işlem"
            )
            col3.metric(
                "📈 Ortalama Getiri", 
                f"{sym}{avg_profit_pct:,.0f}",
                delta="İşlem başına ortalama"
            )
            
            st.divider()
        
        st.dataframe(
            styled_dataframe(sales_display),
            use_container_width=True,
            hide_index=True,
            height=min(600, len(sales_display) * 50 + 100)
        )
    else:
        st.info("Henüz satış kaydı bulunmuyor. İlk satışınızı yapmak için 'Ekle/Çıkar' sekmesine gidin.")


elif selected == "Ekle/Çıkar":
    st.header("Varlık Yönetimi")
    
    # TOTAL profili için düzenleme engeli
    if is_total:
        st.error("⛔ **TOPLAM Profili** salt okunurdur. Varlık eklemek/düzenlemek için bireysel bir profil seçin (MERT, ANNEM, BERGUZAR veya İKRAMİYE).")
        st.stop()
    
    tab1, tab2, tab3 = st.tabs(["Ekle", "Düzenle", "Sil/Sat"])

    # ---------------- EKLE ----------------
    with tab1:
        # Pazar seçimi
        pazar = st.selectbox("Pazar", list(MARKET_DATA.keys()), key="ekle_pazar")

        # Kod seçimi - EMTIA için özel dropdown (Gram Altın, 22 Ayar Gram Altın, Gram Gümüş)
        if pazar == "EMTIA":
            kod_options = MARKET_DATA.get("EMTIA", [])
            # 22 Ayar Gram Altın'ı kontrol et ve ekle
            if "22 Ayar Gram Altın" not in kod_options:
                kod_options = ["Gram Altın", "22 Ayar Gram Altın", "Gram Gümüş"]
            if kod_options:
                kod = st.selectbox("Kod", kod_options, key="ekle_kod_emtia")
            else:
                kod = st.text_input("Kod (Örn: Gram Altın, 22 Ayar Gram Altın, Gram Gümüş)", key="ekle_kod_emtia_manu").upper()
        else:
            # Diğer pazarlar için manuel giriş veya öneri
            kod_options = MARKET_DATA.get(pazar, [])
            if kod_options:
                kod_choice = st.radio(
                    "Kod Seçimi",
                    ["Listeden Seç", "Manuel Gir"],
                    horizontal=True,
                    key="ekle_kod_choice"
                )
                if kod_choice == "Listeden Seç":
                    kod = st.selectbox("Kod", kod_options, key="ekle_kod_select")
                else:
                    kod = st.text_input("Kod (Örn: BTC, THYAO)", key="ekle_kod_manu").upper()
            else:
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


elif selected == "Profil Yönetimi":
    st.header("👤 Profil Yönetimi")
    st.markdown("---")
    
    from profile_manager import (
        load_profiles_from_sheets,
        save_profile_to_sheets,
        delete_profile_from_sheets,
        get_next_profile_order,
        get_all_profiles,
        get_current_profile,
        set_current_profile,
        PROFILES,
        PROFILE_ORDER,
    )
    
    # Reload profiles
    try:
        load_profiles_from_sheets()
    except Exception as e:
        st.warning(f"Profil yükleme hatası: {str(e)}")
    
    tab_add, tab_edit, tab_delete = st.tabs(["➕ Yeni Profil Ekle", "✏️ Profil Düzenle", "🗑️ Profil Sil"])
    
    # ==================== YENİ PROFİL EKLE ====================
    with tab_add:
        st.subheader("➕ Yeni Profil Oluştur")
        st.caption("Yeni bir portföy profili ekleyin. Her profil kendi varlıklarını tutar.")
        
        col1, col2 = st.columns(2)
        
        with col1:
            profile_name = st.text_input(
                "Profil Adı *",
                placeholder="Örn: KARDEŞ, DEDE",
                help="Büyük harflerle, boşluk olmadan (örn: KARDEŞ)"
            ).strip().upper()
            
            display_name = st.text_input(
                "Görünen Ad *",
                placeholder="Örn: 👨‍👩‍👧 Kardeş",
                help="Kullanıcı arayüzünde görünecek isim"
            )
            
            icon = st.text_input(
                "İkon (Emoji) *",
                value="👤",
                help="Bir emoji seçin (örn: 👤, 👨, 👩, 🎯)"
            )
        
        with col2:
            color = st.color_picker(
                "Renk *",
                value="#6b7fd7",
                help="Profil için tema rengi"
            )
            
            description = st.text_area(
                "Açıklama",
                placeholder="Bu profil hakkında kısa bir açıklama...",
                help="Profil hakkında notlar"
            )
            
            is_aggregate = st.checkbox(
                "Toplam Profili (TOTAL)",
                value=False,
                help="Bu profil diğer profillerin toplamını gösterir"
            )
        
        if st.button("✅ Profil Ekle", type="primary", use_container_width=True):
            if not profile_name:
                st.error("❌ Profil adı boş olamaz!")
            elif not display_name:
                st.error("❌ Görünen ad boş olamaz!")
            elif profile_name in PROFILES:
                st.error(f"❌ '{profile_name}' adında bir profil zaten mevcut!")
            elif profile_name == "TOTAL" and not is_aggregate:
                st.error("❌ 'TOTAL' adı sadece toplam profilleri için kullanılabilir!")
            else:
                try:
                    profile_data = {
                        "name": profile_name,
                        "display_name": display_name,
                        "icon": icon if icon else "👤",
                        "color": color,
                        "is_aggregate": is_aggregate,
                        "description": description,
                        "order": get_next_profile_order()
                    }
                    
                    if save_profile_to_sheets(profile_data):
                        st.success(f"✅ '{display_name}' profili başarıyla eklendi!")
                        
                        # Create worksheet for the profile if not aggregate
                        if not is_aggregate:
                            try:
                                from data_loader_profiles import _get_profile_sheet
                                from data_loader import _get_gspread_client, SHEET_NAME
                                client = _get_gspread_client()
                                if client:
                                    spreadsheet = client.open(SHEET_NAME)
                                    try:
                                        # Check if worksheet exists
                                        spreadsheet.worksheet(profile_name.lower())
                                    except:
                                        # Create worksheet
                                        ws = spreadsheet.add_worksheet(
                                            title=profile_name.lower(),
                                            rows=1000,
                                            cols=20
                                        )
                                        headers = ["Kod", "Pazar", "Adet", "Maliyet", "Tip", "Notlar"]
                                        ws.append_row(headers)
                                        st.info(f"📄 '{profile_name}' için worksheet oluşturuldu.")
                            except Exception as e:
                                st.warning(f"⚠️ Worksheet oluşturulamadı: {str(e)}")
                        
                        time.sleep(1.5)
                        st.rerun()
                    else:
                        st.error("❌ Profil kaydedilemedi. Google Sheets bağlantısını kontrol edin.")
                except Exception as e:
                    st.error(f"❌ Hata: {str(e)}")
    
    # ==================== PROFİL DÜZENLE ====================
    with tab_edit:
        st.subheader("✏️ Profil Düzenle")
        st.caption("Mevcut profillerin bilgilerini güncelleyin.")
        
        # Get individual profiles (exclude TOTAL from editing)
        editable_profiles = [p for p in PROFILE_ORDER if p in PROFILES and not PROFILES[p].get("is_aggregate", False)]
        
        if not editable_profiles:
            st.info("📝 Düzenlenebilir profil bulunmuyor.")
        else:
            selected_profile = st.selectbox(
                "Düzenlenecek Profil",
                editable_profiles,
                format_func=lambda x: PROFILES[x]["display_name"]
            )
            
            if selected_profile:
                current_profile = PROFILES[selected_profile]
                
                col1, col2 = st.columns(2)
                
                with col1:
                    new_display_name = st.text_input(
                        "Görünen Ad *",
                        value=current_profile["display_name"],
                        key=f"edit_display_{selected_profile}"
                    )
                    
                    new_icon = st.text_input(
                        "İkon (Emoji) *",
                        value=current_profile.get("icon", "👤"),
                        key=f"edit_icon_{selected_profile}"
                    )
                    
                    new_description = st.text_area(
                        "Açıklama",
                        value=current_profile.get("description", ""),
                        key=f"edit_desc_{selected_profile}"
                    )
                
                with col2:
                    new_color = st.color_picker(
                        "Renk *",
                        value=current_profile.get("color", "#6b7fd7"),
                        key=f"edit_color_{selected_profile}"
                    )
                    
                    st.info("💡 **Not**: Profil adı ve toplam profili durumu değiştirilemez.")
                
                if st.button("💾 Değişiklikleri Kaydet", type="primary", use_container_width=True):
                    if not new_display_name:
                        st.error("❌ Görünen ad boş olamaz!")
                    else:
                        try:
                            profile_data = {
                                "name": selected_profile,  # Name cannot be changed
                                "display_name": new_display_name,
                                "icon": new_icon if new_icon else "👤",
                                "color": new_color,
                                "is_aggregate": current_profile.get("is_aggregate", False),  # Cannot be changed
                                "description": new_description,
                                "order": current_profile.get("order", PROFILE_ORDER.index(selected_profile) + 1)
                            }
                            
                            if save_profile_to_sheets(profile_data):
                                st.success(f"✅ '{new_display_name}' profili başarıyla güncellendi!")
                                time.sleep(1.5)
                                st.rerun()
                            else:
                                st.error("❌ Profil güncellenemedi. Google Sheets bağlantısını kontrol edin.")
                        except Exception as e:
                            st.error(f"❌ Hata: {str(e)}")
    
    # ==================== PROFİL SİL ====================
    with tab_delete:
        st.subheader("🗑️ Profil Sil")
        st.caption("⚠️ **Dikkat**: Profil silindiğinde, o profile ait tüm veriler kalıcı olarak silinir!")
        
        # Get individual profiles (exclude TOTAL and MERT from deletion)
        deletable_profiles = [
            p for p in PROFILE_ORDER 
            if p in PROFILES 
            and not PROFILES[p].get("is_aggregate", False)
            and p != "MERT"  # Protect main profile
        ]
        
        if not deletable_profiles:
            st.info("📝 Silinebilir profil bulunmuyor. (MERT profili korunuyor)")
        else:
            selected_profile = st.selectbox(
                "Silinecek Profil",
                deletable_profiles,
                format_func=lambda x: PROFILES[x]["display_name"]
            )
            
            if selected_profile:
                profile_info = PROFILES[selected_profile]
                
                st.warning(f"""
                **⚠️ UYARI: Bu işlem geri alınamaz!**
                
                Silinecek profil: **{profile_info['display_name']}**
                - Profil adı: {selected_profile}
                - Açıklama: {profile_info.get('description', 'Yok')}
                
                Bu profilin tüm varlık verileri ve geçmişi silinecektir.
                """)
                
                confirm_text = st.text_input(
                    "Silmek için profil adını yazın",
                    placeholder=selected_profile,
                    key=f"delete_confirm_{selected_profile}"
                )
                
                col1, col2 = st.columns([1, 1])
                with col1:
                    if st.button("🗑️ Profili Sil", type="primary", use_container_width=True):
                        if confirm_text.strip().upper() != selected_profile:
                            st.error(f"❌ Onay için '{selected_profile}' yazmanız gerekiyor!")
                        else:
                            try:
                                if delete_profile_from_sheets(selected_profile):
                                    st.success(f"✅ '{profile_info['display_name']}' profili başarıyla silindi!")
                                    
                                    # Switch to default profile if deleted profile was active
                                    if get_current_profile() == selected_profile:
                                        set_current_profile("MERT")
                                    
                                    time.sleep(1.5)
                                    st.rerun()
                                else:
                                    st.error("❌ Profil silinemedi. Google Sheets bağlantısını kontrol edin.")
                            except Exception as e:
                                st.error(f"❌ Hata: {str(e)}")
                
                with col2:
                    st.button("❌ İptal", use_container_width=True)
    
    # ==================== PROFİL LİSTESİ ====================
    st.markdown("---")
    st.subheader("📋 Mevcut Profiller")
    
    try:
        load_profiles_from_sheets()
    except:
        pass
    
    if PROFILES:
        profile_df = pd.DataFrame([
            {
                "Profil": PROFILES[p]["display_name"],
                "Ad": p,
                "İkon": PROFILES[p].get("icon", "👤"),
                "Renk": PROFILES[p].get("color", "#6b7fd7"),
                "Tip": "Toplam" if PROFILES[p].get("is_aggregate", False) else "Bireysel",
                "Açıklama": PROFILES[p].get("description", "")
            }
            for p in PROFILE_ORDER if p in PROFILES
        ])
        
        st.dataframe(
            styled_dataframe(profile_df),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("📝 Henüz profil eklenmemiş.")

# Otomatik yenileme kaldırıldı - sadece sayaç gösterimi var
# Burada ayrı bir timer'a gerek yok
