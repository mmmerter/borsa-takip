import streamlit as st
import yfinance as yf
import pandas as pd
import time
import gspread
import plotly.express as px
import plotly.graph_objects as go
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta

# --- SAYFA AYARLARI ---
st.set_page_config(
    page_title="Merter’in Dashboard'u", 
    layout="wide", 
    page_icon="🏦",
    initial_sidebar_state="collapsed"
)

# --- CSS: TASARIM İYİLEŞTİRMELERİ ---
st.markdown("""
<style>
    .block-container {padding-top: 1rem;}
    div[data-testid="stMetric"] {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 10px;
        border: 1px solid #dcdcdc;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 5px;
        flex-wrap: wrap; 
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #ffffff;
        border-radius: 5px;
        padding: 5px 10px;
        font-size: 14px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #FF4B4B !important;
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)

# --- BAŞLIK VE AYARLAR ---
c_title, c_toggle = st.columns([3, 1])
with c_title:
    # İSTEĞİN ÜZERİNE GÜNCELLENEN BAŞLIK
    st.title("🏦 Merter'in Varlık Yönetim Dashboard'u")
with c_toggle:
    st.write("") 
    # DÖVİZ BAZLI GÖRÜNÜM TUŞU
    GORUNUM_PB = st.radio("Para Birimi:", ["TRY", "USD"], horizontal=True)

# --- SABİT KOLON İSİMLERİ ---
ANALYSIS_COLS = ["Kod", "Pazar", "Tip", "Adet", "Maliyet", "Fiyat", "PB", 
                 "Değer", "Top. P/L", "Top. %", "Gün. P/L", "Notlar"]

# --- VARLIK LİSTESİ (FULL) ---
MARKET_DATA = {
    "BIST (Tümü)": [
        "A1CAP", "ACSEL", "ADEL", "ADESE", "ADGYO", "AEFES", "AFYON", "AGESA", "AGHOL", "AGROT", "AGYO", "AHGAZ", "AKBNK", "AKCNS", "AKENR", "AKFGY", "AKFYE", "AKGRT", "AKMGY", "AKSA", "AKSEN", "AKSGY", "AKSUE", "AKYHO", "ALARK", "ALBRK", "ALCAR", "ALCTL", "ALFAS", "ALGYO", "ALKA", "ALKIM", "ALMAD", "ALTIN", "ALTNY", "ALVES", "ANELE", "ANGEN", "ANHYT", "ANSGR", "ARASE", "ARCLK", "ARDYZ", "ARENA", "ARSAN", "ARTMS", "ARZUM", "ASELS", "ASGYO", "ASTOR", "ASUZU", "ATAGY", "ATAKP", "ATATP", "ATEKS", "ATLAS", "ATSYH", "AVGYO", "AVHOL", "AVOD", "AVPGY", "AVTUR", "AYCES", "AYDEM", "AYEN", "AYES", "AYGAZ", "AZTEK", "BAGFS", "BAKAB", "BALAT", "BANVT", "BARMA", "BASCM", "BASGZ", "BAYRK", "BEGYO", "BEYAZ", "BFREN", "BIENY", "BIGCH", "BIMAS", "BINHO", "BIOEN", "BIZIM", "BJKAS", "BLCYT", "BMSCH", "BMSTL", "BNTAS", "BOBET", "BORLS", "BOSSA", "BRISA", "BRKO", "BRKSN", "BRKVY", "BRLSM", "BRMEN", "BRSAN", "BRYAT", "BSOKE", "BTCIM", "BUCIM", "BURCE", "BURVA", "BVSAN", "BYDNR", "CANTE", "CATES", "CCOLA", "CELHA", "CEMAS", "CEMTS", "CEOEM", "CIMSA", "CLEBI", "CMBTN", "CMENT", "CONSE", "COSMO", "CRDFA", "CRFSA", "CUSAN", "CVKMD", "CWENE", "DAGHL", "DAGI", "DAPGM", "DARDL", "DENGE", "DERHL", "DERIM", "DESA", "DESPC", "DEVA", "DGATE", "DGGYO", "DGNMO", "DIRIT", "DITAS", "DMSAS", "DNISI", "DOAS", "DOBUR", "DOCO", "DOGUB", "DOHOL", "DOKTA", "DURDO", "DYOBY", "DZGYO", "EBEBK", "ECILC", "ECZYT", "EDATA", "EDIP", "EGEEN", "EGEPO", "EGGUB", "EGPRO", "EGSER", "EKGYO", "EKKAL", "EKOSE", "EKSUN", "ELITE", "EMKEL", "EMNIS", "ENERY", "ENJSA", "ENKAI", "ENSRI", "EPLAS", "ERBOS", "ERCB", "EREGL", "ERSU", "ESCAR", "ESCOM", "ESEN", "ETILR", "ETYAT", "EUHOL", "EUKYO", "EUPWR", "EUREN", "EUYO", "EYGYO", "FADE", "FENER", "FLAP", "FMIZP", "FONET", "FORMT", "FORTE", "FRIGO", "FROTO", "FZLGY", "GARAN", "GARFA", "GEDIK", "GEDZA", "GENIL", "GENTS", "GEREL", "GESAN", "GLBMD", "GLCVY", "GLRYH", "GLYHO", "GMTAS", "GOKNR", "GOLTS", "GOODY", "GOZDE", "GRNYO", "GRSEL", "GSDDE", "GSDHO", "GSRAY", "GUBRF", "GWIND", "GZNMI", "HALKB", "HATEK", "HATSN", "HDFGS", "HEDEF", "HEKTS", "HKTM", "HLGYO", "HRKET", "HTTBT", "HUBVC", "HUNER", "HURGZ", "ICBCT", "ICUGS", "IDGYO", "IEYHO", "IHAAS", "IHEVA", "IHGZT", "IHLAS", "IHLGM", "IHYAY", "IMASM", "INDES", "INFO", "INGRM", "INTEM", "INVES", "IPEKE", "ISATR", "ISBIR", "ISBTR", "ISCTR", "ISDMR", "ISFIN", "ISGSY", "ISGYO", "ISKPL", "ISKUR", "ISMEN", "ISSEN", "ISYAT", "IZENR", "IZFAS", "IZINV", "IZMDC", "JANTS", "KAPLM", "KAREL", "KARSN", "KARTN", "KARYE", "KATMR", "KAYSE", "KCAER", "KCHOL", "KENT", "KERVN", "KERVT", "KFEIN", "KGYO", "KIMMR", "KLGYO", "KLKIM", "KLMSN", "KLNMA", "KLRHO", "KLSER", "KMPUR", "KNFRT", "KONKA", "KONTR", "KONYA", "KOPOL", "KORDS", "KOZAA", "KOZAL", "KRDMA", "KRDMB", "KRDMD", "KRGYO", "KRONT", "KRPLS", "KRSTL", "KRTEK", "KRVGD", "KSTUR", "KTLEV", "KTSKR", "KUTPO", "KUVVA", "KUYAS", "KZBGY", "KZGYO", "LIDER", "LIDFA", "LINK", "LKMNH", "LOGO", "LUKSK", "MAALT", "MACKO", "MAGEN", "MAKIM", "MAKTK", "MANAS", "MARBL", "MARK", "MARTI", "MAVI", "MEDTR", "MEGAP", "MEGMT", "MEKAG", "MNDTR", "MENBA", "MERCN", "MERIT", "MERKO", "METRO", "METUR", "MGROS", "MIATK", "MIPAZ", "MMCAS", "MNDRS", "MOBTL", "MOGAN", "MPARK", "MRGYO", "MRSHL", "MSGYO", "MTRKS", "MTRYO", "MZHLD", "NATEN", "NETAS", "NIBAS", "NTGAZ", "NUGYO", "NUHCM", "OBAMS", "ODAS", "OFSYM", "ONCSM", "ORCAY", "ORGE", "ORMA", "OSMEN", "OSTIM", "OTKAR", "OTTO", "OYAKC", "OYAYO", "OYLUM", "OYYAT", "OZGYO", "OZKGY", "OZRDN", "OZSUB", "PAGYO", "PAMEL", "PAPIL", "PARSN", "PASEU", "PCILT", "PEGYO", "PEKGY", "PENGD", "PENTA", "PETKM", "PETUN", "PGSUS", "PINSU", "PKART", "PKENT", "PLTUR", "PNLSN", "PNSUT", "POLHO", "POLTK", "PRDGS", "PRKAB", "PRKME", "PRZMA", "PSGYO", "PUMAS", "QUAGR", "RALYH", "RAYSG", "REEDR", "RNPOL", "RODRG", "ROYAL", "RTALB", "RUBNS", "RYGYO", "RYSAS", "SAHOL", "SAMAT", "SANEL", "SANFM", "SANKO", "SARKY", "SASA", "SAYAS", "SDTTR", "SEKFK", "SEKUR", "SELEC", "SELGD", "SELVA", "SEYKM", "SILVR", "SISE", "SKBNK", "SKTAS", "SKYMD", "SMART", "SMRTG", "SNGYO", "SNICA", "SNKRN", "SNPAM", "SODSN", "SOKE", "SOKM", "SONME", "SRVGY", "SUMAS", "SUNTK", "SURGY", "SUWEN", "TABGD", "TARKM", "TATEN", "TATGD", "TAVHL", "TBORG", "TCELL", "TDGYO", "TEKTU", "TERA", "TETMT", "TEZOL", "TGSAS", "THYAO", "TKFEN", "TKNSA", "TLMAN", "TMPOL", "TMSN", "TNZTP", "TOASO", "TRCAS", "TRGYO", "TRILC", "TSGYO", "TSKB", "TSPOR", "TTKOM", "TTRAK", "TUCLK", "TUKAS", "TUPRS", "TUREX", "TURGG", "TURSG", "UFUK", "ULAS", "ULKER", "ULUFA", "ULUSE", "ULUUN", "UMPAS", "UNLU", "USAK", "UZERB", "VAKBN", "VAKFN", "VAKKO", "VANGD", "VBTYZ", "VERTU", "VERUS", "VESBE", "VESTL", "VKFYO", "VKGYO", "VKING", "VRGYO", "YAPRK", "YATAS", "YAYLA", "YBTAS", "YEOTK", "YESIL", "YGGYO", "YGYO", "YKBNK", "YKSLN", "YONGA", "YUNSA", "YYAPI", "YYLGD", "ZEDUR", "ZGOLD", "ZOREN", "ZRGYO"
    ],
    "ABD (S&P + NASDAQ)": [
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META", "BRK-B", "LLY", "V", "TSM", "UNH", 
        "JPM", "XOM", "WMT", "JNJ", "MA", "PG", "AVGO", "HD", "ORCL", "CVX", "MRK", "KO", "PEP", 
        "COST", "ADBE", "CSCO", "MCD", "CRM", "DIS", "NKE", "WFC", "BAC", "VZ", "QCOM", "IBM", 
        "BA", "GE", "PLTR", "COIN", "PYPL", "UBER", "ABNB", "AMD", "INTC", "NFLX", "TMUS", "CMCSA",
        "TXN", "HON", "AMGN", "INTU", "SBUX", "GILD", "MDLZ", "BKNG", "ADI", "ISRG", "ADP", "LRCX",
        "REGN", "VRTX", "FISV", "KLAC", "SNPS", "CDNS", "MAR", "CSX", "PANW", "ORLY", "MNST", "FTNT", 
        "AEP", "CTAS", "KDP", "DXCM", "PAYX", "ODFL", "MCHP", "AIG", "ALL", "AXP", "BK", "BLK", "C", 
        "CAT", "CL", "COF", "COP", "CVS", "D", "DE", "DHR", "DOW", "DUK", "EMR", "EXC", "F", "FDX", 
        "GD", "GM", "GS", "HAL", "HPQ", "KR", "KMI", "LMT", "LOW", "MMM", "MET", "MO", "MS", "NEE", 
        "NOC", "OXY", "PCG", "PFE", "PM", "PSX", "RTX", "SLB", "SO", "SPG", "T", "TGT", "TRV", "USB", 
        "UPS", "WBA", "WMB", "ASML", "AZN", "LTC", "SHOP", "SONY", "TM"
    ],
    "KRIPTO": [
        "BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "AVAX", "DOGE", "SHIB", "DOT", "MATIC", "LTC", 
        "TRX", "UNI", "ATOM", "LINK", "XLM", "ALGO", "VET", "ICP", "NEAR", "FIL", "HBAR", "APT", 
        "QNT", "LDO", "ARB", "OP", "RNDR", "GRT", "STX", "SAND", "EOS", "MANA", "THETA", "AAVE", 
        "AXS", "FTM", "FLOW", "CHZ", "PEPE", "FLOKI", "GALA", "MINA", "SUI", "INJ", "RUNE", "KAS", 
        "IMX", "SNX"
    ],
    "EMTIA": [
        "Gram Altın (TL)", "Gram Gümüş (TL)", "Altın ONS ($)", "Gümüş ONS ($)", 
        "Petrol (Brent)", "Doğalgaz", "Bakır", "Platin", "Paladyum"
    ],
    "FIZIKI VARLIKLAR": [
        "Gram Altın (Fiziki)", "Çeyrek Altın", "Yarım Altın", "Tam Altın", 
        "Cumhuriyet Altın", "Ata Lira", "Dolar (Nakit)", "Euro (Nakit)", "Sterlin (Nakit)"
    ]
}

# --- SABİTLER ---
SHEET_NAME = "PortfoyData" 

@st.cache_data(ttl=300)
def get_usd_try():
    try:
        ticker = yf.Ticker("TRY=X")
        hist = ticker.history(period="1d")
        if not hist.empty:
            return hist['Close'].iloc[-1]
        return 34.0
    except: return 34.0

USD_TRY = get_usd_try()

# --- GOOGLE SHEETS ---
def get_data_from_sheet():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        sheet = client.open(SHEET_NAME).sheet1
        data = sheet.get_all_records()
        if not data: 
            return pd.DataFrame(columns=["Kod", "Pazar", "Adet", "Maliyet", "Tip", "Notlar"])
        df = pd.DataFrame(data)
        expected_cols = ["Kod", "Pazar", "Adet", "Maliyet", "Tip", "Notlar"]
        for col in expected_cols:
            if col not in df.columns: df[col] = "" 
        return df
    except Exception as e:
        st.error(f"Veri çekme hatası: {e}")
        return pd.DataFrame(columns=["Kod", "Pazar", "Adet", "Maliyet", "Tip", "Notlar"])

def save_data_to_sheet(df):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = st.secrets["gcp_service_account"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    sheet = client.open(SHEET_NAME).sheet1
    sheet.clear()
    sheet.update([df.columns.values.tolist()] + df.values.tolist())

# --- DATA MOTORU ---
def get_yahoo_symbol(kod, pazar):
    if "BIST" in pazar:
        return f"{kod}.IS" if not kod.endswith(".IS") else kod
    elif "KRIPTO" in pazar:
        return f"{kod}-USD" if not kod.endswith("-USD") else kod
    elif "EMTIA" in pazar:
        map_emtia = {"Altın ONS": "GC=F", "Gümüş ONS": "SI=F", "Petrol": "BZ=F", "Doğalgaz": "NG=F", "Bakır": "HG=F"}
        for k, v in map_emtia.items():
            if k in kod: return v
        return kod
    return kod # ABD ve diğerleri

def run_analysis(df, usd_try_rate, view_currency):
    results = []
    if df.empty: return pd.DataFrame(columns=ANALYSIS_COLS)
        
    for i, row in df.iterrows():
        kod = row.get("Kod", "")
        pazar = row.get("Pazar", "")
        adet = float(row.get("Adet", 0))
        maliyet = float(row.get("Maliyet", 0))
        
        if not kod: continue 

        symbol = get_yahoo_symbol(kod, pazar)
        
        asset_currency = "USD"
        if "BIST" in pazar or "TL" in kod or "Fiziki" in pazar:
            asset_currency = "TRY"
        
        try:
            if "Gram Altın (TL)" in kod:
                hist = yf.Ticker("GC=F").history(period="2d")
                curr_price = (hist['Close'].iloc[-1] * usd_try_rate) / 31.1035
            elif "Fiziki" in pazar: 
                curr_price = maliyet
            else:
                hist = yf.Ticker(symbol).history(period="2d")
                if hist.empty: curr_price = maliyet
                else: curr_price = hist['Close'].iloc[-1]
        except:
            curr_price = maliyet

        # Dönüşüm Hesaplamaları
        val_native = curr_price * adet
        cost_native = maliyet * adet
        
        if view_currency == "TRY":
            if asset_currency == "USD":
                fiyat_goster = curr_price * usd_try_rate
                val_goster = val_native * usd_try_rate
                cost_goster = cost_native * usd_try_rate
            else: 
                fiyat_goster = curr_price
                val_goster = val_native
                cost_goster = cost_native
        elif view_currency == "USD":
            if asset_currency == "TRY":
                fiyat_goster = curr_price / usd_try_rate
                val_goster = val_native / usd_try_rate
                cost_goster = cost_native / usd_try_rate
            else: 
                fiyat_goster = curr_price
                val_goster = val_native
                cost_goster = cost_native

        pnl = val_goster - cost_goster
        pnl_pct = (pnl / cost_goster * 100) if cost_goster > 0 else 0
        
        # Günlük Değişim (Basitleştirilmiş)
        daily_chg = 0 

        results.append({
            "Kod": kod, "Pazar": pazar, "Tip": row["Tip"],
            "Adet": adet, "Maliyet": maliyet,
            "Fiyat": fiyat_goster, "PB": view_currency,
            "Değer": val_goster, "Top. P/L": pnl, "Top. %": pnl_pct,
            "Gün. P/L": daily_chg, 
            "Notlar": row.get("Notlar", "")
        })
        
    return pd.DataFrame(results)

# --- TARİHSEL ZENGİNLEŞME ANALİZİ ---
@st.cache_data(ttl=3600)
def get_historical_chart(df, usd_try):
    if df.empty: return None
    tickers_map = {}
    for idx, row in df.iterrows():
        kod = row['Kod']
        pazar = row['Pazar']
        sym = get_yahoo_symbol(kod, pazar)
        if "Gram" not in kod and "Fiziki" not in pazar:
            tickers_map[sym] = {"Adet": float(row['Adet']), "Pazar": pazar}
    if not tickers_map: return None
    try:
        data = yf.download(list(tickers_map.keys()), period="6mo")['Close']
    except: return None
    if data.empty: return None
    portfolio_history = pd.Series(0, index=data.index)
    if isinstance(data, pd.Series): data = data.to_frame(name=list(tickers_map.keys())[0])
    for col in data.columns:
        if col in tickers_map:
            adet = tickers_map[col]["Adet"]
            pazar = tickers_map[col]["Pazar"]
            price_series = data[col]
            if "KRIPTO" in pazar or "ABD" in pazar:
                portfolio_history += (price_series * adet * usd_try)
            else:
                portfolio_history += (price_series * adet)
    return portfolio_history

# --- MAIN ---
portfoy_df = get_data_from_sheet()
master_df = run_analysis(portfoy_df, USD_TRY, GORUNUM_PB)

if "Tip" in master_df.columns:
    portfoy_only = master_df[master_df["Tip"] == "Portfoy"]
    takip_only = master_df[master_df["Tip"] == "Takip"]
else:
    portfoy_only = pd.DataFrame()
    takip_only = pd.DataFrame()

# --- TAB RENDER FONKSİYONU ---
def render_pazar_tab(df, filter_text, currency_symbol):
    if df.empty: 
        st.info("Veri yok.")
        return
    
    # Filtreleme
    df_filtered = df[df["Pazar"].str.contains(filter_text, na=False)]
    
    if df_filtered.empty:
        st.info(f"{filter_text} kategorisinde varlık bulunamadı.")
        return

    # Metrikler
    total_val = df_filtered["Değer"].sum()
    total_pl = df_filtered["Top. P/L"].sum()
    
    c1, c2 = st.columns(2)
    c1.metric(f"Toplam {filter_text} Varlık", f"{currency_symbol}{total_val:,.0f}")
    c2.metric(f"Toplam {filter_text} Kâr/Zarar", f"{currency_symbol}{total_pl:,.0f}", delta=f"{total_pl:,.0f}")
    
    st.dataframe(df_filtered, use_container_width=True, hide_index=True)


# --- ARAYÜZ VE SEKMELER ---
# Yeni Sekme Yapısı
tabs = st.tabs([
    "📊 Dashboard", 
    "📋 Tümü", 
    "📈 BIST", 
    "🇺🇸 ABD", 
    "₿ Kripto", 
    "🛢️ Emtia", 
    "🏠 Fiziki",
    "👀 İzleme", 
    "⚙️ Ekle/Çıkar"
])

sym = "₺" if GORUNUM_PB == "TRY" else "$"

# 1. DASHBOARD
with tabs[0]:
    if not portfoy_only.empty:
        total_val = portfoy_only["Değer"].sum()
        total_pl = portfoy_only["Top. P/L"].sum()
        
        c1, c2 = st.columns(2)
        c1.metric("Toplam Portföy", f"{sym}{total_val:,.0f}")
        c2.metric("Genel Kâr/Zarar", f"{sym}{total_pl:,.0f}", delta=f"{total_pl:,.0f}")
        
        st.divider()
        col_pie, col_bar = st.columns([1, 1])
        with col_pie:
            st.subheader("Dağılım")
            fig_pie = px.pie(portfoy_only, values='Değer', names='Pazar', hole=0.4)
            st.plotly_chart(fig_pie, use_container_width=True)
        with col_bar:
            st.subheader("En Büyük Varlıklar")
            top_assets = portfoy_only.sort_values(by="Değer", ascending=False).head(10)
            fig_bar = px.bar(top_assets, x='Kod', y='Değer', color='Top. P/L')
            st.plotly_chart(fig_bar, use_container_width=True)
            
        st.divider()
        st.subheader("📈 Tarihsel Zenginleşme (TL)")
        hist_data = get_historical_chart(portfoy_df, USD_TRY)
        if hist_data is not None: st.line_chart(hist_data, color="#4CAF50")
    else:
        st.info("Portföy boş.")

# 2. TÜMÜ
with tabs[1]:
    st.subheader("Tüm Portföy Listesi")
    st.dataframe(portfoy_only, use_container_width=True, hide_index=True)

# 3. BIST
with tabs[2]:
    render_pazar_tab(portfoy_only, "BIST", sym)

# 4. ABD
with tabs[3]:
    render_pazar_tab(portfoy_only, "ABD", sym)

# 5. KRIPTO
with tabs[4]:
    render_pazar_tab(portfoy_only, "KRIPTO", sym)

# 6. EMTIA
with tabs[5]:
    render_pazar_tab(portfoy_only, "EMTIA", sym)

# 7. FIZIKI
with tabs[6]:
    render_pazar_tab(portfoy_only, "FIZIKI", sym)

# 8. İZLEME
with tabs[7]:
    st.subheader("İzleme Listesi")
    st.dataframe(takip_only, use_container_width=True, hide_index=True)

# 9. EKLE/ÇIKAR
with tabs[8]:
    st.header("Varlık Yönetimi")
    tab_ekle, tab_sil = st.tabs(["➕ Ekle", "🗑️ Sil"])
    
    with tab_ekle:
        islem_tipi = st.radio("Tür", ["Portföy", "Takip"], horizontal=True)
        yeni_pazar = st.selectbox("Pazar", list(MARKET_DATA.keys()))
        if "ABD" in yeni_pazar: st.warning("🇺🇸 ABD için Maliyeti DOLAR girin.")
        
        secenekler = MARKET_DATA.get(yeni_pazar, [])
        with st.form("add_asset_form"):
            yeni_kod = st.selectbox("Listeden Seç", options=secenekler, index=None, placeholder="Seçiniz...")
            manuel_kod = st.text_input("Veya Manuel Yaz").upper()
            
            c1, c2 = st.columns(2)
            adet_inp = c1.number_input("Adet", min_value=0.0, step=0.001, format="%.3f")
            maliyet_inp = c2.number_input("Maliyet", min_value=0.0, step=0.01)
            not_inp = st.text_input("Not")
            
            if st.form_submit_button("Kaydet", type="primary", use_container_width=True):
                final_kod = manuel_kod if manuel_kod else yeni_kod
                if final_kod:
                    portfoy_df = portfoy_df[portfoy_df["Kod"] != final_kod]
                    tip_str = "Portfoy" if islem_tipi == "Portföy" else "Takip"
                    yeni_satir = pd.DataFrame({
                        "Kod": [final_kod], "Pazar": [yeni_pazar], 
                        "Adet": [adet_inp], "Maliyet": [maliyet_inp],
                        "Tip": [tip_str], "Notlar": [not_inp]
                    })
                    portfoy_df = pd.concat([portfoy_df, yeni_satir], ignore_index=True)
                    save_data_to_sheet(portfoy_df)
                    st.success(f"{final_kod} kaydedildi!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Seçim yapın.")

    with tab_sil:
        if not portfoy_df.empty:
            sil_kod = st.selectbox("Silinecek:", portfoy_df["Kod"].unique())
            if st.button("Sil", type="secondary"):
                portfoy_df = portfoy_df[portfoy_df["Kod"] != sil_kod]
                save_data_to_sheet(portfoy_df)
                st.success("Silindi.")
                st.rerun()
