import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import requests
import feedparser
try:
    from tefas import Crawler
except (ImportError, AttributeError):
    Crawler = None  # tefas kütüphanesi yüklü değilse None
import yfinance as yf
import ccxt
import pandas as pd
import re
import unicodedata
import socket
import urllib.parse
from utils import get_yahoo_symbol
import pytz
import time
from functools import wraps
from logger import get_logger

# Google Sheets / network işlemleri sonsuza kadar beklemesin diye global timeout
# Timeout'u optimize et - çok uzun bekleme yerine daha hızlı hata yakalama
socket.setdefaulttimeout(20)

SHEET_NAME = "PortfoyData"
DAILY_BASE_SHEET_NAME = "daily_base_prices"  # Günlük baz fiyatlar için

# Google Sheets client cache
_client_cache = None

# Rate limiting için son istek zamanı
_last_request_time = 0
_min_request_interval = 0.1  # İstekler arası minimum bekleme (100ms)

logger = get_logger()


def _warn_once(key: str, message: str):
    """Streamlit ortamında aynı uyarıyı bir kez göster."""
    try:
        if not hasattr(st, "session_state"):
            return
        state_key = f"_warned_{key}"
        if not st.session_state.get(state_key):
            st.warning(message)
            st.session_state[state_key] = True
    except Exception:
        # Streamlit dışında çağrılıyorsa sessiz geç
        pass


def _normalize_tip_value(value: str) -> str:
    """
    Google Sheet'ten gelen Tip değerlerini normalize eder.
    'Portföy' gibi aksanlı yazımlar Portfoy olarak sadeleştirilir.
    """
    if value is None:
        return "Portfoy"
    text = str(value).strip()
    if not text:
        return "Portfoy"
    normalized = unicodedata.normalize("NFKD", text).encode("ASCII", "ignore").decode("ASCII").lower()
    if normalized == "portfoy":
        return "Portfoy"
    if normalized == "takip":
        return "Takip"
    return text


def _rate_limit():
    """Rate limiting: İstekler arasında minimum bekleme süresi."""
    global _last_request_time
    current_time = time.time()
    elapsed = current_time - _last_request_time
    if elapsed < _min_request_interval:
        sleep_time = _min_request_interval - elapsed
        time.sleep(sleep_time)
    _last_request_time = time.time()


def _retry_with_backoff(func, max_retries=3, initial_delay=1.0, max_delay=60.0, backoff_factor=2.0):
    """
    Google Sheets API çağrıları için exponential backoff ile retry mekanizması.
    429 (quota exceeded) hatalarında özellikle yararlıdır.
    
    Args:
        func: Çağrılacak fonksiyon (lambda veya callable)
        max_retries: Maksimum deneme sayısı
        initial_delay: İlk bekleme süresi (saniye)
        max_delay: Maksimum bekleme süresi (saniye)
        backoff_factor: Her denemede bekleme süresini artırma faktörü
    
    Returns:
        Fonksiyon sonucu
    
    Raises:
        Son exception (tüm denemeler başarısız olursa)
    """
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            # Rate limiting uygula
            _rate_limit()
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
            
            # 429 hatası (quota exceeded) için özel işlem
            if error_code == 429 or '429' in str(e) or 'Quota exceeded' in str(e) or 'quota' in str(e).lower():
                if attempt < max_retries - 1:
                    # Exponential backoff hesapla
                    delay = min(initial_delay * (backoff_factor ** attempt), max_delay)
                    logger.warning(
                        f"Google Sheets API quota aşıldı (deneme {attempt + 1}/{max_retries}). "
                        f"{delay:.1f} saniye bekleniyor..."
                    )
                    time.sleep(delay)
                    continue
                else:
                    logger.error(f"Google Sheets API quota hatası: {str(e)}")
                    raise
            else:
                # Diğer API hataları için de retry yap ama daha kısa bekleme ile
                if attempt < max_retries - 1:
                    delay = min(initial_delay * (backoff_factor ** attempt), max_delay / 2)
                    logger.warning(
                        f"Google Sheets API hatası (deneme {attempt + 1}/{max_retries}): {str(e)}. "
                        f"{delay:.1f} saniye bekleniyor..."
                    )
                    time.sleep(delay)
                    continue
                else:
                    raise
        except Exception as e:
            # Beklenmeyen hatalar için de retry yap
            if attempt < max_retries - 1:
                delay = min(initial_delay * (backoff_factor ** attempt), max_delay / 4)
                logger.warning(
                    f"Google Sheets işlemi başarısız (deneme {attempt + 1}/{max_retries}): {str(e)}. "
                    f"{delay:.1f} saniye bekleniyor..."
                )
                time.sleep(delay)
                last_exception = e
                continue
            else:
                raise
    
    # Tüm denemeler başarısız olduysa son exception'ı fırlat
    if last_exception:
        raise last_exception


def _get_gspread_client():
    """Google Sheets client'ı cache'ler"""
    global _client_cache
    if _client_cache is None:
        try:
            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
            _client_cache = gspread.authorize(creds)
        except Exception:
            _client_cache = None
    return _client_cache

@st.cache_data(ttl=900)  # 15 dakika cache - Sheets verileri daha az sık değişir (quota koruması için artırıldı)
def get_data_from_sheet():
    try:
        client = _get_gspread_client()
        if client is None:
            _warn_once(
                "sheet_client",
                "Google Sheets verisine ulaşılamadı. İnternet bağlantısını veya servis hesabı ayarlarını kontrol et.",
            )
            return pd.DataFrame(columns=["Kod", "Pazar", "Adet", "Maliyet", "Tip", "Notlar"])
        
        # Retry mekanizması ile sheet açma ve veri okuma
        def _fetch_data():
            sheet = client.open(SHEET_NAME).sheet1
            return sheet.get_all_records()
        
        data = _retry_with_backoff(_fetch_data, max_retries=3, initial_delay=2.0, max_delay=60.0)
        
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
            _warn_once(
                "sheet_quota_error",
                "⚠️ Google Sheets API quota limiti aşıldı. Birkaç dakika bekleyip tekrar deneyin.",
            )
        else:
            _warn_once(
                "sheet_client_error",
                "Google Sheets verisi okunurken hata oluştu. Lütfen tekrar deneyin.",
            )
        logger.error(f"Google Sheets veri okuma hatası: {error_msg}", exc_info=True)
        return pd.DataFrame(columns=["Kod", "Pazar", "Adet", "Maliyet", "Tip", "Notlar"])

def save_data_to_sheet(df):
    try:
        client = _get_gspread_client()
        if client is None:
            return
        sheet = client.open(SHEET_NAME).sheet1
        sheet.clear()
        sheet.update([df.columns.values.tolist()] + df.values.tolist())
    except Exception:
        pass

@st.cache_data(ttl=900)  # 15 dakika cache - Satış geçmişi daha az sık değişir (quota koruması için artırıldı)
def get_sales_history():
    try:
        client = _get_gspread_client()
        if client is None:
            return pd.DataFrame(columns=["Tarih", "Kod", "Pazar", "Satılan Adet", "Satış Fiyatı", "Maliyet", "Kâr/Zarar"])
        
        def _fetch_sales():
            sheet = client.open(SHEET_NAME).worksheet("Satislar")
            return sheet.get_all_records()
        
        data = _retry_with_backoff(_fetch_sales, max_retries=3, initial_delay=2.0, max_delay=60.0)
        return pd.DataFrame(data) if data else pd.DataFrame(columns=["Tarih", "Kod", "Pazar", "Satılan Adet", "Satış Fiyatı", "Maliyet", "Kâr/Zarar"])
    except Exception as e:
        logger.error(f"Satış geçmişi okuma hatası: {str(e)}", exc_info=True)
        return pd.DataFrame(columns=["Tarih", "Kod", "Pazar", "Satılan Adet", "Satış Fiyatı", "Maliyet", "Kâr/Zarar"])

def add_sale_record(date, code, market, qty, price, cost, profit):
    try:
        client = _get_gspread_client()
        if client is None:
            return
        sheet = client.open(SHEET_NAME).worksheet("Satislar")
        sheet.append_row([str(date), code, market, float(qty), float(price), float(cost), float(profit)])
        # Cache'i temizle
        get_sales_history.clear()
    except Exception:
        pass

# Cache'i fund_code'ye göre ayrı ayrı tutmak için hash kullan
@st.cache_data(ttl=7200, show_spinner=False)  # 2 saat cache - TEFAS fon fiyatları gün içinde çok değişmez
def get_tefas_data(fund_code):
    """
    TEFAS fon fiyatını çeker. Önce TEFAS API'sini kullanır, sonra tefas-crawler, en son web scraping dener.
    """
    fund_code = str(fund_code).upper().strip()
    
    # ÖNCE TEFAS API'sini dene (en güvenilir yöntem)
    try:
        # TEFAS'ın güncel API endpoint'i - fon detay bilgisi
        api_url = "https://www.tefas.gov.tr/api/DB/BindHistoryInfo"
        payload = {
            "fontip": "YAT",
            "sfontur": "",
            "kurucukod": "",
            "fonkod": fund_code
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Referer": "https://www.tefas.gov.tr/"
        }
        r = requests.post(api_url, json=payload, headers=headers, timeout=15)
        if r.status_code == 200:
            data = r.json()
            if data and isinstance(data, list) and len(data) > 0:
                # Son kayıt en güncel fiyat
                last_record = data[-1]
                # Farklı field isimlerini dene
                price_field = None
                for field in ["birimfiyat", "BirimFiyat", "BIRIMFIYAT", "price", "Price", "fiyat", "Fiyat", "birimFiyat"]:
                    if field in last_record:
                        try:
                            price = float(last_record[field])
                            if price > 0 and price < 100:  # Makul fiyat kontrolü
                                price_field = field
                                break
                        except (ValueError, TypeError):
                            continue
                
                if price_field:
                    # Son kapanış fiyatı (bugünün fiyatı yoksa en son geçerli fiyat)
                    curr_price = float(last_record[price_field])
                    # Önceki günün kapanış fiyatı (günlük kar/zarar hesaplaması için)
                    prev_price = curr_price  # Varsayılan: aynı fiyat (eğer önceki gün yoksa)
                    if len(data) > 1:
                        # Önceki günün fiyatını bul
                        for i in range(len(data) - 2, -1, -1):
                            prev_record = data[i]
                            if price_field in prev_record:
                                try:
                                    candidate_price = float(prev_record[price_field])
                                    if candidate_price > 0 and candidate_price < 100:
                                        prev_price = candidate_price
                                        break
                                except (ValueError, TypeError):
                                    continue
                    return curr_price, prev_price
    except Exception:
        pass
    
    # İKİNCİ: tefas-crawler ile dene (eğer yüklüyse)
    try:
        if Crawler is not None:
            crawler = Crawler()
            end = datetime.now().strftime("%Y-%m-%d")
            start = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")
            res = crawler.fetch(start=start, end=end, name=fund_code, columns=["Price"])
            if not res.empty and len(res) > 0:
                res = res.sort_index()
                valid_prices = res["Price"].dropna()
                if len(valid_prices) > 0:
                    # Son kapanış fiyatı (bugünün fiyatı yoksa en son geçerli fiyat)
                    curr_price = float(valid_prices.iloc[-1])
                    # Önceki günün kapanış fiyatı (günlük kar/zarar hesaplaması için)
                    prev_price = float(valid_prices.iloc[-2]) if len(valid_prices) > 1 else curr_price
                    if curr_price > 0 and curr_price < 100:
                        return curr_price, prev_price
    except Exception:
        pass
    
    # DÖRDÜNCÜ: Web scraping ile dene (son çare)
    try:
        url = f"https://www.tefas.gov.tr/FonAnaliz.aspx?FonKod={fund_code}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://www.tefas.gov.tr/"
        }
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            # Birden fazla pattern dene - daha kapsamlı
            patterns = [
                r'id="MainContent_PanelInfo_lblPrice"[^>]*>([\d,]+\.?\d*)',
                r'id="MainContent_PanelInfo_lblPrice">([\d,]+\.?\d*)',
                r'Birim Fiyat[^<]*<[^>]*>([\d,]+\.?\d*)',
                r'Birim Fiyatı[^<]*<[^>]*>([\d,]+\.?\d*)',
                r'"birimFiyat"[^:]*:\s*"?([\d,]+\.?\d*)"?',
                r'Fiyat[^>]*>([\d,]+\.?\d*)',
                r'<span[^>]*>([\d,]+\.?\d*)</span>',  # Genel span pattern
            ]
            for pattern in patterns:
                matches = re.findall(pattern, r.text, re.IGNORECASE)
                for match in matches:
                    try:
                        price_str = str(match).replace(",", ".").replace(" ", "")
                        price = float(price_str)
                        # Makul fiyat aralığı kontrolü (0.01 - 100 TL arası)
                        if price > 0 and price < 100:
                            return price, price
                    except (ValueError, AttributeError):
                        continue
    except Exception:
        pass
    
    # ÜÇÜNCÜ: Alternatif TEFAS API endpoint'i dene
    try:
        # TEFAS'ın fon detay API'si
        detail_url = f"https://www.tefas.gov.tr/api/DB/BindHistoryInfo?fontip=YAT&sfontur=&kurucukod=&fonkod={fund_code}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
            "Referer": f"https://www.tefas.gov.tr/FonAnaliz.aspx?FonKod={fund_code}"
        }
        r = requests.get(detail_url, headers=headers, timeout=15)
        if r.status_code == 200:
            data = r.json()
            if data and isinstance(data, list) and len(data) > 0:
                last_record = data[-1]
                for field in ["birimfiyat", "BirimFiyat", "BIRIMFIYAT", "price", "Price", "fiyat", "Fiyat"]:
                    if field in last_record:
                        try:
                            # Son kapanış fiyatı
                            price = float(last_record[field])
                            if price > 0 and price < 100:
                                # Önceki günün fiyatı (günlük kar/zarar için)
                                prev_price = price  # Varsayılan
                                if len(data) > 1:
                                    for i in range(len(data) - 2, -1, -1):
                                        if field in data[i]:
                                            try:
                                                candidate = float(data[i][field])
                                                if candidate > 0 and candidate < 100:
                                                    prev_price = candidate
                                                    break
                                            except (ValueError, TypeError):
                                                continue
                                return price, prev_price
                        except (ValueError, TypeError):
                            continue
    except Exception:
        pass
    
    # Hiçbir yöntem çalışmazsa 0 döndür (maliyet kullanılacak)
    return 0, 0

@st.cache_data(ttl=300)
def get_crypto_globals():
    try:
        d = requests.get("https://api.coingecko.com/api/v3/global", timeout=5).json()["data"]
        return d["total_market_cap"]["usd"], d["market_cap_percentage"]["btc"], d["total_market_cap"]["usd"] * (1 - ((d["market_cap_percentage"]["btc"] + d["market_cap_percentage"]["eth"]) / 100)), 100 - (d["market_cap_percentage"]["btc"] + d["market_cap_percentage"]["eth"]), 0
    except: return 0, 0, 0, 0, 0

@st.cache_data(ttl=300)  # 5 dakika cache - F5 ile güncel kur için optimize edildi
def get_usd_try():
    try: 
        ticker = yf.Ticker("TRY=X")
        h = ticker.history(period="5d")
        if not h.empty:
            return h["Close"].iloc[-1]
        else:
            # Fallback: daha uzun period
            h = ticker.history(period="1mo")
            if not h.empty:
                return h["Close"].iloc[-1]
            else:
                return 34.0
    except Exception:
        return 34.0

@st.cache_data(ttl=300)
def get_financial_news(topic="finance"):
    urls = {"BIST": "https://news.google.com/rss/search?q=Borsa+Istanbul+Hisseler&hl=tr&gl=TR&ceid=TR:tr",
            "KRIPTO": "https://news.google.com/rss/search?q=Kripto+Para+Bitcoin&hl=tr&gl=TR&ceid=TR:tr",
            "GLOBAL": "https://news.google.com/rss/search?q=ABD+Borsaları+Fed&hl=tr&gl=TR&ceid=TR:tr",
            "DOVIZ": "https://news.google.com/rss/search?q=Dolar+Altın+Piyasa&hl=tr&gl=TR&ceid=TR:tr"}
    try:
        feed = feedparser.parse(urls.get(topic, urls["BIST"]))
        news_list = []
        for e in feed.entries[:10]:
            # Tarihi parse et (feedparser'in published_parsed özelliğini kullan)
            date_for_sort = ""
            if hasattr(e, 'published_parsed') and e.published_parsed:
                try:
                    from time import mktime
                    date_for_sort = mktime(e.published_parsed)
                except:
                    date_for_sort = e.published
            else:
                date_for_sort = e.published
            news_list.append({
                "title": e.title, 
                "link": e.link, 
                "date": e.published,
                "_sort_date": date_for_sort
            })
        # Tarihe göre sırala (en yeni önce)
        news_list.sort(key=lambda x: x.get("_sort_date", x.get("date", "")), reverse=True)
        # _sort_date kolonunu kaldır
        for item in news_list:
            item.pop("_sort_date", None)
        return news_list
    except: return []

@st.cache_data(ttl=600)  # 10 dakika cache - haberler daha az sık güncellenir
def get_portfolio_news(portfolio_df, watchlist_df=None):
    """
    Portföydeki ve izleme listesindeki varlıklar için haberleri çeker.
    Her varlık için ayrı haberler çeker ve birleştirir.
    """
    all_news = []
    seen_titles = set()  # Duplicate haberleri önlemek için
    
    # Portföy varlıkları
    if portfolio_df is not None and not portfolio_df.empty:
        portfolio_codes = portfolio_df["Kod"].unique().tolist()
        for code in portfolio_codes:
            try:
                if pd.isna(code) or str(code).strip() == "":
                    continue
            except (TypeError, ValueError):
                continue
            code_str = str(code).strip()
            # Özel durumlar için temizleme
            if "Gram" in code_str or "GRAM" in code_str:
                if "Altın" in code_str or "ALTIN" in code_str:
                    code_str = "Altın"
                elif "Gümüş" in code_str or "GÜMÜŞ" in code_str:
                    code_str = "Gümüş"
            elif code_str in ["TL", "USD", "EUR"]:
                continue  # Nakit için haber çekme
            
            try:
                # Google News RSS için Türkçe arama - URL encoding
                encoded_code = urllib.parse.quote(code_str)
                url = f"https://news.google.com/rss/search?q={encoded_code}+hisse+haber&hl=tr&gl=TR&ceid=TR:tr"
                feed = feedparser.parse(url)
                for entry in feed.entries[:5]:  # Her varlık için en fazla 5 haber
                    title = entry.title
                    if title not in seen_titles:
                        seen_titles.add(title)
                        all_news.append({
                            "title": title,
                            "link": entry.link,
                            "date": entry.published,
                            "asset": code_str,
                            "source": "Portföy"
                        })
            except Exception:
                continue
    
    # İzleme listesi varlıkları
    if watchlist_df is not None and not watchlist_df.empty:
        watchlist_codes = watchlist_df["Kod"].unique().tolist()
        for code in watchlist_codes:
            try:
                if pd.isna(code) or str(code).strip() == "":
                    continue
            except (TypeError, ValueError):
                continue
            code_str = str(code).strip()
            # Özel durumlar için temizleme
            if "Gram" in code_str or "GRAM" in code_str:
                if "Altın" in code_str or "ALTIN" in code_str:
                    code_str = "Altın"
                elif "Gümüş" in code_str or "GÜMÜŞ" in code_str:
                    code_str = "Gümüş"
            elif code_str in ["TL", "USD", "EUR"]:
                continue
            
            try:
                url = f"https://news.google.com/rss/search?q={code_str}+hisse+haber&hl=tr&gl=TR&ceid=TR:tr"
                feed = feedparser.parse(url)
                for entry in feed.entries[:3]:  # İzleme listesi için daha az haber
                    title = entry.title
                    if title not in seen_titles:
                        seen_titles.add(title)
                        all_news.append({
                            "title": title,
                            "link": entry.link,
                            "date": entry.published,
                            "asset": code_str,
                            "source": "İzleme"
                        })
            except Exception:
                continue
    
    # Tarihe göre sırala (en yeni önce)
    try:
        all_news.sort(key=lambda x: x["date"], reverse=True)
    except Exception:
        pass
    
    return all_news[:30]  # En fazla 30 haber döndür

@st.cache_data(ttl=120)  # 2 dakika cache - F5 ile güncel veriler için optimize edildi
def get_tickers_data(df_portfolio, usd_try):
    total_cap, btc_d, total_3, others_d, others_cap = get_crypto_globals()
    market_symbols = [("BIST 100", "XU100.IS"), ("USD", "TRY=X"), ("EUR", "EURTRY=X"), ("BTC/USDT", "BTC-USD"),
                      ("ETH/USDT", "ETH-USD"), ("Ons Altın", "GC=F"), ("Ons Gümüş", "SI=F"), ("NASDAQ", "^IXIC"), ("S&P 500", "^GSPC")]
    portfolio_symbols = {}
    if not df_portfolio.empty:
        assets = df_portfolio[df_portfolio["Tip"] == "Portfoy"]
        for _, row in assets.iterrows():
            if "NAKIT" not in row["Pazar"] and "Gram" not in row["Kod"] and "FON" not in row["Pazar"]:
                portfolio_symbols[row["Kod"]] = get_yahoo_symbol(row["Kod"], row["Pazar"])
    
    all_fetch = list(set([s[1] for s in market_symbols] + list(portfolio_symbols.values())))
    market_html = ''
    portfolio_html = ''

    try:
        # Batch işlemi optimize et - timeout ve retry mekanizması ile
        yahoo_data = yf.Tickers(" ".join(all_fetch))
        def get_val(symbol, label=None):
            try:
                # Borsa kapalıyken de çalışması için period'u artır
                # Timeout ekle - daha hızlı hata yakalama
                h = yahoo_data.tickers[symbol].history(period="5d", timeout=10)
                if not h.empty:
                    p, prev = h["Close"].iloc[-1], h["Close"].iloc[-2] if len(h) > 1 else h["Close"].iloc[-1]
                    chg = ((p - prev) / prev) * 100
                    # Modern renkler ve ok işaretleri
                    if p >= prev:
                        col = "#00e676"  # Yeşil
                        arrow = "▲"
                        bg_col = "rgba(0, 230, 118, 0.15)"
                    else:
                        col = "#ff5252"  # Kırmızı
                        arrow = "▼"
                        bg_col = "rgba(255, 82, 82, 0.15)"
                    
                    # Fiyat formatı
                    fmt = f"{p:,.2f}" if p > 1 else f"{p:,.4f}"
                    if "XU100" in symbol or "^" in symbol: fmt = f"{p:,.0f}"
                    
                    # Modern ticker kartı - biraz küçültülmüş
                    return f'''<span style="display: inline-block; background: {bg_col}; border: 1px solid {col}; border-radius: 5px; padding: 3px 8px; margin: 0 2px; font-family: 'Inter', -apple-system, sans-serif;">
                        <span style="color: #8b9aff; font-size: 12px; font-weight: 700; letter-spacing: 0.2px;">{label if label else symbol}</span>
                        <span style="color: #ffffff; font-size: 13px; font-weight: 800; margin: 0 4px;">{fmt}</span>
                        <span style="color: {col}; font-size: 12px; font-weight: 800; background: rgba(0,0,0,0.3); padding: 2px 4px; border-radius: 3px;">{arrow} {chg:+.1f}%</span>
                    </span>'''
                else:
                    # Fallback: daha uzun period dene
                    h = yahoo_data.tickers[symbol].history(period="1mo")
                    if not h.empty:
                        p = h["Close"].iloc[-1]
                        prev = h["Close"].iloc[-2] if len(h) > 1 else p
                        chg = ((p - prev) / prev) * 100
                        if p >= prev:
                            col = "#00e676"
                            arrow = "▲"
                            bg_col = "rgba(0, 230, 118, 0.15)"
                        else:
                            col = "#ff5252"
                            arrow = "▼"
                            bg_col = "rgba(255, 82, 82, 0.15)"
                        fmt = f"{p:,.2f}" if p > 1 else f"{p:,.4f}"
                        if "XU100" in symbol or "^" in symbol: fmt = f"{p:,.0f}"
                        return f'''<span style="display: inline-block; background: {bg_col}; border: 1px solid {col}; border-radius: 5px; padding: 3px 8px; margin: 0 2px; font-family: 'Inter', -apple-system, sans-serif;">
                            <span style="color: #8b9aff; font-size: 12px; font-weight: 700; letter-spacing: 0.2px;">{label if label else symbol}</span>
                            <span style="color: #ffffff; font-size: 13px; font-weight: 800; margin: 0 4px;">{fmt}</span>
                            <span style="color: {col}; font-size: 12px; font-weight: 800; background: rgba(0,0,0,0.3); padding: 2px 4px; border-radius: 3px;">{arrow} {chg:+.1f}%</span>
                        </span>'''
            except Exception:
                # Batch başarısız olursa, tek tek dene
                try:
                    ticker = yf.Ticker(symbol)
                    h = ticker.history(period="5d")
                    if not h.empty:
                        p, prev = h["Close"].iloc[-1], h["Close"].iloc[-2] if len(h) > 1 else h["Close"].iloc[-1]
                        chg = ((p - prev) / prev) * 100
                        if p >= prev:
                            col = "#00e676"
                            arrow = "▲"
                            bg_col = "rgba(0, 230, 118, 0.15)"
                        else:
                            col = "#ff5252"
                            arrow = "▼"
                            bg_col = "rgba(255, 82, 82, 0.15)"
                        fmt = f"{p:,.2f}" if p > 1 else f"{p:,.4f}"
                        if "XU100" in symbol or "^" in symbol: fmt = f"{p:,.0f}"
                        return f'''<span style="display: inline-block; background: {bg_col}; border: 1px solid {col}; border-radius: 5px; padding: 3px 8px; margin: 0 2px; font-family: 'Inter', -apple-system, sans-serif;">
                            <span style="color: #8b9aff; font-size: 12px; font-weight: 700; letter-spacing: 0.2px;">{label if label else symbol}</span>
                            <span style="color: #ffffff; font-size: 13px; font-weight: 800; margin: 0 4px;">{fmt}</span>
                            <span style="color: {col}; font-size: 12px; font-weight: 800; background: rgba(0,0,0,0.3); padding: 2px 4px; border-radius: 3px;">{arrow} {chg:+.1f}%</span>
                        </span>'''
                except Exception:
                    # Hata durumunda boş string döndür - sessiz geç
                    pass
            return ""

        for name, sym in market_symbols:
            val = get_val(sym, name)
            if val: market_html += f"{val} "
            if name == "ETH/USDT":
                try:
                    # Gram Altın
                    h = yahoo_data.tickers["GC=F"].history(period="5d")
                    if not h.empty:
                        gr_altin = (h["Close"].iloc[-1] * usd_try) / 31.1035
                        prev_gr_altin = (h["Close"].iloc[-2] * usd_try) / 31.1035 if len(h) > 1 else gr_altin
                        chg_gr = ((gr_altin - prev_gr_altin) / prev_gr_altin) * 100
                        col_gr = "#00e676" if gr_altin >= prev_gr_altin else "#ff5252"
                        arrow_gr = "▲" if gr_altin >= prev_gr_altin else "▼"
                        bg_gr = "rgba(0, 230, 118, 0.15)" if gr_altin >= prev_gr_altin else "rgba(255, 82, 82, 0.15)"
                        market_html += f'''<span style="display: inline-block; background: {bg_gr}; border: 1px solid {col_gr}; border-radius: 6px; padding: 4px 10px; margin: 0 3px; font-family: 'Inter', -apple-system, sans-serif;">
                            <span style="color: #8b9aff; font-size: 14px; font-weight: 700; letter-spacing: 0.2px;">Gr Altın</span>
                            <span style="color: #ffffff; font-size: 15px; font-weight: 800; margin: 0 5px;">{gr_altin:.2f}</span>
                            <span style="color: {col_gr}; font-size: 14px; font-weight: 800; background: rgba(0,0,0,0.3); padding: 2px 5px; border-radius: 3px;">{arrow_gr} {chg_gr:+.1f}%</span>
                        </span> '''
                except: pass
                try:
                    # Gram Gümüş
                    h = yahoo_data.tickers["SI=F"].history(period="5d")
                    if not h.empty:
                        gr_gumus = (h["Close"].iloc[-1] * usd_try) / 31.1035
                        prev_gr_gumus = (h["Close"].iloc[-2] * usd_try) / 31.1035 if len(h) > 1 else gr_gumus
                        chg_gr = ((gr_gumus - prev_gr_gumus) / prev_gr_gumus) * 100
                        col_gr = "#00e676" if gr_gumus >= prev_gr_gumus else "#ff5252"
                        arrow_gr = "▲" if gr_gumus >= prev_gr_gumus else "▼"
                        bg_gr = "rgba(0, 230, 118, 0.15)" if gr_gumus >= prev_gr_gumus else "rgba(255, 82, 82, 0.15)"
                        market_html += f'''<span style="display: inline-block; background: {bg_gr}; border: 1px solid {col_gr}; border-radius: 6px; padding: 4px 10px; margin: 0 3px; font-family: 'Inter', -apple-system, sans-serif;">
                            <span style="color: #8b9aff; font-size: 14px; font-weight: 700; letter-spacing: 0.2px;">Gr Gümüş</span>
                            <span style="color: #ffffff; font-size: 15px; font-weight: 800; margin: 0 5px;">{gr_gumus:.2f}</span>
                            <span style="color: {col_gr}; font-size: 14px; font-weight: 800; background: rgba(0,0,0,0.3); padding: 2px 5px; border-radius: 3px;">{arrow_gr} {chg_gr:+.1f}%</span>
                        </span> '''
                except: pass

        if total_cap > 0:
            market_html += f'''<span style="display: inline-block; background: rgba(242, 169, 0, 0.15); border: 1px solid #f2a900; border-radius: 6px; padding: 4px 10px; margin: 0 3px; font-family: 'Inter', -apple-system, sans-serif;">
                <span style="color: #8b9aff; font-size: 14px; font-weight: 700; letter-spacing: 0.2px;">BTC.D</span>
                <span style="color: #f2a900; font-size: 15px; font-weight: 800; margin: 0 5px;">{btc_d:.2f}%</span>
            </span> '''
        
        # Portföydeki BIST, ABD, Kripto varlıkları ikinci banda ekle
        if portfolio_symbols:
            for name, sym in portfolio_symbols.items():
                val = get_val(sym, name)
                if val: portfolio_html += f"{val} "
        else: portfolio_html += '<span style="color: #888; font-size: 14px;">Portföy boş.</span>'
    except: market_html, portfolio_html = "Yükleniyor...", "Yükleniyor..."
    
    # Sonsuz döngü için içeriği iki kez tekrarla
    market_html_doubled = market_html + " " + market_html
    portfolio_html_doubled = portfolio_html + " " + portfolio_html
    
    return f'<div class="ticker-text animate-market">{market_html_doubled}</div>', f'<div class="ticker-text animate-portfolio">{portfolio_html_doubled}</div>'

# ==========================================================
#   KRAL ULTRA - Portföy Tarihsel Log & KPI Yardımcıları
#   (charts.py içindeki import'ları karşılamak için)
# ==========================================================

def _get_history_sheet():
    """Portföy tarihçe sheet'ine erişim helper'ı."""
    try:
        client = _get_gspread_client()
        if client is None:
            return None
        # Ana sheet ile aynı dosyada "portfolio_history" isimli sayfa:
        def _open_sheet():
            return client.open(SHEET_NAME).worksheet("portfolio_history")
        sheet = _retry_with_backoff(_open_sheet, max_retries=2, initial_delay=1.0, max_delay=30.0)
        return sheet
    except Exception:
        return None


def read_portfolio_history():
    """
    Google Sheet -> 'portfolio_history' tablosunu okur.
    Beklenen kolonlar: Tarih, Değer_TRY, Değer_USD
    """
    sheet = _get_history_sheet()
    if sheet is None:
        return pd.DataFrame(columns=["Tarih", "Değer_TRY", "Değer_USD"])

    try:
        def _fetch_history():
            return sheet.get_all_records()
        
        data = _retry_with_backoff(_fetch_history, max_retries=3, initial_delay=2.0, max_delay=60.0)
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
        logger.error(f"Portfolio history okuma hatası: {str(e)}", exc_info=True)
        return pd.DataFrame(columns=["Tarih", "Değer_TRY", "Değer_USD"])


def get_history_summary():
    """
    Tarihsel veri özeti döndürür (debugging için).
    Dönüş: dict with 'status', 'days', 'oldest', 'newest', 'records'
    """
    try:
        df = read_portfolio_history()
        if df is None or df.empty:
            return {
                "status": "empty",
                "days": 0,
                "oldest": None,
                "newest": None,
                "records": 0,
                "message": "Tarihsel veri bulunamadı. Lütfen uygulamayı birkaç gün çalıştırın."
            }
        
        oldest = df["Tarih"].min()
        newest = df["Tarih"].max()
        days = (newest - oldest).days + 1
        records = len(df)
        
        status = "good" if days >= 30 else "insufficient"
        message = f"{records} kayıt, {days} günlük veri ({oldest.strftime('%Y-%m-%d')} - {newest.strftime('%Y-%m-%d')})"
        
        if days < 7:
            message += " ⚠️ Haftalık performans için yetersiz."
        elif days < 30:
            message += " ⚠️ Aylık performans için yetersiz."
        else:
            message += " ✅ Tüm metrikler için yeterli veri."
        
        return {
            "status": status,
            "days": days,
            "oldest": oldest.strftime('%Y-%m-%d'),
            "newest": newest.strftime('%Y-%m-%d'),
            "records": records,
            "message": message,
            "data": df  # Detaylı inceleme için
        }
    except Exception as e:
        return {
            "status": "error",
            "days": 0,
            "oldest": None,
            "newest": None,
            "records": 0,
            "message": f"Hata: {str(e)}"
        }


def write_portfolio_history(value_try, value_usd):
    """
    Bugünün tarihine karşılık portföy toplamını (TRY / USD) ekler.
    Aynı güne ikinci kez yazmaya kalkarsak, bırakıyoruz (charts/portföy kodu genelde önce kontrol ediyor).
    """
    sheet = _get_history_sheet()
    if sheet is None:
        return

    today_str = datetime.now().strftime("%Y-%m-%d")
    try:
        # Var olan kayıtları al, aynı gün varsa ekleme
        data = sheet.get_all_records()
        for row in data:
            if str(row.get("Tarih", ""))[:10] == today_str:
                return  # Bugün zaten kaydedilmiş

        new_row = [today_str, float(value_try), float(value_usd)]
        sheet.append_row(new_row)
    except Exception:
        # Sessiz geç, uygulamayı kilitlemesin
        pass


def get_timeframe_changes(history_df, subtract_df=None, subtract_before=None):
    """
    Haftalık / Aylık / YTD gerçek K/Z hesaplar.
    history_df: read_portfolio_history() çıktısı
    subtract_df: Çıkarılacak değerler (örn: fon geçmişi) - opsiyonel
    subtract_before: Bu tarihten önceki subtract_df değerlerini çıkar - opsiyonel
    Dönüş:
      {
        "weekly": (değer, yüzde),
        "monthly": (değer, yüzde),
        "ytd": (değer, yüzde),
        "spark_week": [seri],
        "spark_month": [seri],
        "spark_ytd": [seri],
        "data_days": kaç günlük veri var,
        "oldest_date": en eski tarih,
        "newest_date": en yeni tarih,
      }
    """
    if history_df is None or history_df.empty:
        return None

    # Tarih kolonu garanti olsun
    if "Tarih" not in history_df.columns:
        return None
    df = history_df.copy().sort_values("Tarih")
    df["Tarih"] = pd.to_datetime(df["Tarih"])

    # Ana seri: TRY bazlı toplam
    # Eğer subtract_df varsa ve subtract_before tarihinden önceki kayıtlar varsa,
    # bunları çıkar (fonların reset tarihinden önceki değerlerini çıkarmak için)
    if subtract_df is not None and not subtract_df.empty and subtract_before is not None:
        if "Tarih" in subtract_df.columns and "Değer_TRY" in subtract_df.columns:
            subtract_df_copy = subtract_df.copy()
            subtract_df_copy["Tarih"] = pd.to_datetime(subtract_df_copy["Tarih"])
            # subtract_before tarihinden önceki kayıtları çıkar
            subtract_before_dt = pd.to_datetime(subtract_before)
            subtract_before_mask = subtract_df_copy["Tarih"] < subtract_before_dt
            
            if subtract_before_mask.any():
                subtract_before_df = subtract_df_copy[subtract_before_mask].copy()
                # Her tarih için history_df'deki değerden çıkar
                for _, sub_row in subtract_before_df.iterrows():
                    sub_date = sub_row["Tarih"]
                    sub_val = float(sub_row.get("Değer_TRY", 0))
                    # Aynı tarihli kayıtları bul ve çıkar
                    date_mask = df["Tarih"].dt.date == sub_date.date()
                    if date_mask.any():
                        df.loc[date_mask, "Değer_TRY"] = df.loc[date_mask, "Değer_TRY"] - sub_val

    if "Değer_TRY" not in df.columns:
        return None

    if df.empty:
        return None

    today_val = float(df["Değer_TRY"].iloc[-1])
    dates = df["Tarih"]
    today_date = dates.max()

    def _calc_period(days: int):
        target_date = today_date - timedelta(days=days)
        sub = df[df["Tarih"] >= target_date]
        if sub.empty:
            # Eğer hedef tarihten sonra veri yoksa, None döndür (yetersiz veri)
            return None, None, []
        
        # En az 2 gün veri olmalı ki değişim hesaplanabilsin
        if len(sub) < 2:
            # Tek veri noktası varsa anlamsız, None döndür
            return None, None, []
        
        # Hedef tarihten önce veri var mı kontrol et
        # Eğer en eski veri hedef tarihten çok sonraysa, yetersiz veri demektir
        oldest_date = sub["Tarih"].min()
        if (oldest_date - target_date).days > days * 0.3:  # %30'dan fazla fark varsa yetersiz veri
            return None, None, []
        
        start_val = float(sub["Değer_TRY"].iloc[0])
        diff = today_val - start_val
        pct = (diff / start_val * 100) if start_val > 0 else 0.0
        spark = list(sub["Değer_TRY"])
        return diff, pct, spark

    # 7 gün (haftalık)
    w_val, w_pct, w_spark = _calc_period(7)

    # 30 gün (aylık)
    m_val, m_pct, m_spark = _calc_period(30)

    # YTD: yılın ilk kaydından bugüne
    year_mask = df["Tarih"].dt.year == datetime.now().year
    if year_mask.any():
        ydf = df[year_mask]
        start_val = float(ydf["Değer_TRY"].iloc[0])
        diff = today_val - start_val
        pct = (diff / start_val * 100) if start_val > 0 else 0.0
        y_spark = list(ydf["Değer_TRY"])
        y_val, y_pct = diff, pct
    else:
        # Yıl içinde veri yoksa, tüm veriyi kullan
        if not df.empty:
            start_val = float(df["Değer_TRY"].iloc[0])
            diff = today_val - start_val
            pct = (diff / start_val * 100) if start_val > 0 else 0.0
            y_spark = list(df["Değer_TRY"])
            y_val, y_pct = diff, pct
        else:
            y_val, y_pct, y_spark = 0.0, 0.0, []

    # Veri günü sayısı ve tarih aralığı
    oldest_date = df["Tarih"].min()
    newest_date = df["Tarih"].max()
    data_days = (newest_date - oldest_date).days + 1
    
    return {
        "weekly": (w_val, w_pct) if w_val is not None else None,
        "monthly": (m_val, m_pct) if m_val is not None else None,
        "ytd": (y_val, y_pct) if y_val is not None else None,
        "spark_week": w_spark,
        "spark_month": m_spark,
        "spark_ytd": y_spark,
        "data_days": data_days,
        "oldest_date": oldest_date.strftime("%Y-%m-%d"),
        "newest_date": newest_date.strftime("%Y-%m-%d"),
    }
# ==========================================================
#   Pazar Bazlı Tarihsel Log (BIST / ABD / FON / EMTIA / NAKIT)
#   Sheet isimleri:
#   history_bist, history_abd, history_fon, history_emtia, history_nakit
# ==========================================================

def _get_market_history_sheet(ws_name: str):
    """Belirli bir pazar için sheet'e erişim helper'ı."""
    try:
        client = _get_gspread_client()
        if client is None:
            return None
        def _open_market_sheet():
            return client.open(SHEET_NAME).worksheet(ws_name)
        sheet = _retry_with_backoff(_open_market_sheet, max_retries=2, initial_delay=1.0, max_delay=30.0)
        return sheet
    except Exception:
        return None


def _read_market_history(ws_name: str):
    sheet = _get_market_history_sheet(ws_name)
    if sheet is None:
        return pd.DataFrame(columns=["Tarih", "Değer_TRY", "Değer_USD"])

    try:
        def _fetch_market_history():
            return sheet.get_all_records()
        
        data = _retry_with_backoff(_fetch_market_history, max_retries=3, initial_delay=2.0, max_delay=60.0)
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
        logger.error(f"Market history okuma hatası ({ws_name}): {str(e)}", exc_info=True)
        return pd.DataFrame(columns=["Tarih", "Değer_TRY", "Değer_USD"])


def _write_market_history(ws_name: str, value_try: float, value_usd: float):
    sheet = _get_market_history_sheet(ws_name)
    if sheet is None:
        return

    today_str = datetime.now().strftime("%Y-%m-%d")
    try:
        data = sheet.get_all_records()
        for row in data:
            if str(row.get("Tarih", ""))[:10] == today_str:
                # Bugünün kaydı zaten varsa tekrar ekleme
                return
        new_row = [today_str, float(value_try), float(value_usd)]
        sheet.append_row(new_row)
    except Exception:
        # Hata olursa sessiz geç; uygulamayı kilitlemesin
        pass


# --- Pazar bazlı public helper'lar ---

def read_history_bist():
    return _read_market_history("history_bist")


def write_history_bist(value_try, value_usd):
    _write_market_history("history_bist", value_try, value_usd)


def read_history_abd():
    return _read_market_history("history_abd")


def write_history_abd(value_try, value_usd):
    _write_market_history("history_abd", value_try, value_usd)


def read_history_fon():
    return _read_market_history("history_fon")


def write_history_fon(value_try, value_usd):
    _write_market_history("history_fon", value_try, value_usd)


def read_history_emtia():
    return _read_market_history("history_emtia")


def write_history_emtia(value_try, value_usd):
    _write_market_history("history_emtia", value_try, value_usd)


def read_history_nakit():
    return _read_market_history("history_nakit")


def write_history_nakit(value_try, value_usd):
    _write_market_history("history_nakit", value_try, value_usd)


# ==========================================================
#   Günlük Baz Fiyatlar (00:30'da sıfırlama için)
# ==========================================================

def _get_daily_base_sheet():
    """Günlük baz fiyatlar sheet'ine erişim."""
    try:
        client = _get_gspread_client()
        if client is None:
            return None
        
        def _open_daily_base():
            spreadsheet = client.open(SHEET_NAME)
            try:
                return spreadsheet.worksheet(DAILY_BASE_SHEET_NAME)
            except Exception:
                # Sheet yoksa oluştur
                sheet = spreadsheet.add_worksheet(title=DAILY_BASE_SHEET_NAME, rows=1000, cols=10)
                # Header ekle
                sheet.append_row(["Tarih", "Saat", "Kod", "Fiyat", "PB"])
                return sheet
        
        sheet = _retry_with_backoff(_open_daily_base, max_retries=2, initial_delay=1.0, max_delay=30.0)
        return sheet
    except Exception:
        return None


def get_daily_base_prices():
    """
    Bugün için günlük baz fiyatları getirir (00:30'da kaydedilmiş).
    00:30 Türkiye saatinde reset edilir ve o saatten sonra günlük değişimler bu baz fiyatlara göre hesaplanır.
    Dönüş: DataFrame with columns: Kod, Fiyat, PB
    """
    sheet = _get_daily_base_sheet()
    if sheet is None:
        return pd.DataFrame(columns=["Kod", "Fiyat", "PB"])
    
    try:
        # Türkiye saati
        turkey_tz = pytz.timezone('Europe/Istanbul')
        now_turkey = datetime.now(turkey_tz)
        
        # Bugünün tarihi
        today_str = now_turkey.strftime("%Y-%m-%d")
        
        # Saat 00:30'dan önceyse, dünkü baz fiyatları kullan
        # 00:30'dan sonraysa, bugünkü baz fiyatları kullan (eğer kaydedilmişse)
        if now_turkey.hour == 0 and now_turkey.minute < 30:
            # 00:00 - 00:30 arası: Dünün baz fiyatlarını kullan
            yesterday = now_turkey - timedelta(days=1)
            target_date = yesterday.strftime("%Y-%m-%d")
        else:
            # 00:30'dan sonra: Bugünün baz fiyatlarını kullan
            target_date = today_str
        
        # Sheet'ten hedef tarihin verilerini çek
        def _fetch_daily_base():
            return sheet.get_all_records()
        
        data = _retry_with_backoff(_fetch_daily_base, max_retries=3, initial_delay=2.0, max_delay=60.0)
        if not data:
            return pd.DataFrame(columns=["Kod", "Fiyat", "PB"])
        
        df = pd.DataFrame(data)
        # Hedef tarihine ait kayıtları filtrele
        df_today = df[df["Tarih"] == target_date].copy()
        
        if df_today.empty:
            return pd.DataFrame(columns=["Kod", "Fiyat", "PB"])
        
        # En son kaydedilen değerleri al (her kod için)
        df_today = df_today.groupby("Kod").last().reset_index()
        return df_today[["Kod", "Fiyat", "PB"]]
    
    except Exception as e:
        logger.error(f"Daily base prices okuma hatası: {str(e)}", exc_info=True)
        return pd.DataFrame(columns=["Kod", "Fiyat", "PB"])


def should_update_daily_base():
    """
    Günlük baz fiyatların güncellenmesi gerekip gerekmediğini kontrol eder.
    Türkiye saati ile 00:30'dan sonra ve henüz bugün için kayıt yoksa True döner.
    
    Reset mantığı:
    - 00:00 - 00:30 arası: Güncelleme yapılmaz (önceki günün verileri kullanılır)
    - 00:30'dan sonra: Eğer bugün için kayıt yoksa güncelleme yapılır
    - Her gün sadece bir kez güncellenir (ilk çalıştırmada)
    """
    try:
        turkey_tz = pytz.timezone('Europe/Istanbul')
        now_turkey = datetime.now(turkey_tz)
        
        # Saat 00:30'dan önceyse güncelleme yapma
        if now_turkey.hour == 0 and now_turkey.minute < 30:
            return False
        
        # Bugün için kayıt var mı kontrol et
        sheet = _get_daily_base_sheet()
        if sheet is None:
            # Sheet yoksa güncelleme yap (yeni sheet oluşturulacak)
            return True
        
        today_str = now_turkey.strftime("%Y-%m-%d")
        data = sheet.get_all_records()
        
        if not data:
            # Hiç veri yoksa güncelleme yap
            return True
        
        # Bugünün tarihi ile kayıt var mı?
        for row in data:
            if str(row.get("Tarih", "")) == today_str:
                return False  # Bugün zaten kayıt var, güncelleme yapma
        
        return True  # Bugün için kayıt yok ve 00:30'dan sonra, güncelle
    except Exception:
        return False


def update_daily_base_prices(current_prices_df):
    """
    Günlük baz fiyatları günceller (Türkiye saati ile 00:30'dan sonra çağrılmalı).
    
    Bu fonksiyon:
    1. Saat 00:30'dan sonraysa ve bugün için henüz kayıt yoksa çalışır
    2. O anki fiyatları "baz fiyat" olarak kaydeder
    3. Günlük değişim hesaplamaları bu baz fiyatlara göre yapılır
    
    current_prices_df: DataFrame with columns: Kod, Fiyat, PB
    """
    if not should_update_daily_base():
        return
    
    sheet = _get_daily_base_sheet()
    if sheet is None:
        return
    
    try:
        turkey_tz = pytz.timezone('Europe/Istanbul')
        now_turkey = datetime.now(turkey_tz)
        today_str = now_turkey.strftime("%Y-%m-%d")
        time_str = now_turkey.strftime("%H:%M:%S")
        
        # Her varlık için kayıt ekle
        rows_to_add = []
        for _, row in current_prices_df.iterrows():
            kod = row["Kod"]
            fiyat = float(row["Fiyat"])
            pb = row.get("PB", "TRY")
            
            new_row = [today_str, time_str, kod, fiyat, pb]
            rows_to_add.append(new_row)
        
        # Toplu ekleme (daha hızlı)
        if rows_to_add:
            sheet.append_rows(rows_to_add)
            
            # Cache'i temizle (yeni veriler yüklensin)
            get_daily_base_prices.clear()
    
    except Exception:
        pass
