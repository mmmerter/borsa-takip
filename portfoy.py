import streamlit as st
import yfinance as yf
import pandas as pd
import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- SAYFA AYARLARI ---
st.set_page_config(
    page_title="Merter’in Portföy Motoru", 
    layout="wide", 
    page_icon="🚀",
    initial_sidebar_state="collapsed" # Yan menüyü kapalı başlat
)

# --- CSS: MOBİL İÇİN ÖZEL AYARLAR ---
st.markdown("""
<style>
    .main .block-container {
        padding-top: 2rem;
        padding-left: 1rem;
        padding-right: 1rem;
    }
    h1 {
        font-size: 1.8rem !important;
        text-align: center;
        color: #4CAF50;
    }
    div[data-testid="stMetric"] {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 10px;
        text-align: center;
    }
    /* Sekmeleri mobilde kaydırılabilir yap */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        flex-wrap: wrap; 
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #f0f2f6;
        border-radius: 5px;
        padding: 5px 10px;
        font-size: 14px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #4CAF50 !important;
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)

st.title("Merter’in Bulut Tabanlı Portföy Takip Motoru")

# --- DEVASA VARLIK LİSTESİ ---
MARKET_DATA = {
    "BIST (Tümü)": [
        "THYAO", "GARAN", "ASELS", "EREGL", "SISE", "BIMAS", "AKBNK", "YKBNK", "KCHOL", "SAHOL",
        "TUPRS", "FROTO", "TOASO", "PGSUS", "TCELL", "PETKM", "HEKTS", "SASA", "ASTOR", "KONTR",
        "AKSEN", "ALARK", "ARCLK", "ENKAI", "EUPWR", "GESAN", "GUBRF", "ISCTR", "KOZAL", "MGROS",
        "ODAS", "OYAKC", "SMRTG", "SOKM", "TAVHL", "TTKOM", "VESTL", "YEOTK", "AGHOL", "AHGAZ",
        "AKFGY", "AKSA", "ALFAS", "AEFES", "ASUZU", "AYDEM", "BAGFS", "BERA", "BIOEN", "BRSAN",
        "BRYAT", "BUCIM", "CANTE", "CCOLA", "CEMTS", "CIMSA", "CWENE", "DOAS", "DOHOL", "ECILC",
        "EGEEN", "EKGYO", "ENJSA", "EUREN", "FENER", "GENIL", "GLYHO", "GSDHO", "GWIND", "HALKB",
        "ISDMR", "ISGYO", "ISMEN", "IZENR", "KCAER", "KMPUR", "KONKA", "KORDS", "KOZAA", "KRDMD",
        "KZBGY", "MAVI", "MIATK", "OTKAR", "OYYAT", "PENTA", "PSGYO", "QUAGR", "RTALB", "SDTTR",
        "SELEC", "SKBNK", "SNGYO", "TATGD", "TKFEN", "TKNSA", "TMSN", "TSKB", "TSPOR", "TTRAK",
        "TURSG", "ULKER", "VAKBN", "VESBE", "ZOREN", "ADEL", "ADESE", "AGROT", "AKCNS", "AKSGY",
        "ALGYO", "ALKIM", "ANACM", "ANELE", "ANGEN", "ANHYT", "ANSGR", "ARASE", "ARDYZ", "ARENA",
        "ARSAN", "ATAGY", "ATAKP", "AVGYO", "AVHOL", "AVOD", "AYEN", "AYES", "AYGAZ", "AZTEK",
        "BJKAS", "BOBET", "BOSSA", "BRISA", "BSOKE", "BTCIM", "CEOEM", "CONSE", "COSMO", "DARDL",
        "EBEBK", "EKSUN", "ELITE", "EMKEL", "ERBOS", "ESEN", "ESCOM", "FORTE", "GEDIK", "GOKNR",
        "GOLTS", "GOODY", "GOZDE", "GRSEL", "HEDEF", "HKTM", "HLGYO", "HUNER", "IHLAS", "IHLGM",
        "INFO", "INVES", "IPEKE", "ISFIN", "ISGSY", "ISKPL", "JANTS", "KAREL", "KARSN", "KARTN",
        "KATMR", "KAYSE", "KFEIN", "KGYO", "KLKIM", "KLMSN", "KNFRT", "KONYA", "KOPOL", "KRGYO",
        "KRONT", "KRPLS", "KSTUR", "KUTPO", "LIDER", "LOGO", "LUKSK", "MAKIM", "MANAS", "MARBL",
        "MEDTR", "MERCN", "METRO", "MOBTL", "MPARK", "MRGYO", "NATEN", "NETAS", "NUGYO", "NUHCM",
        "OFSYM", "ONCSM", "ORCAY", "ORGE", "OSMEN", "OSTIM", "OTTO", "OZKGY", "OZRDN", "OZSUB",
        "PAGYO", "PAMEL", "PAPIL", "PARSN", "PCILT", "PEKGY", "PENGD", "PETUN", "PINSU", "PKART",
        "PNLSN", "PNSUT", "POLHO", "POLTK", "PRDGS", "PRKAB", "PRKME", "RNPOL", "RYGYO", "RYSAS",
        "SANEL", "SANKO", "SARKY", "SAYAS", "SEKFK", "SEKUR", "SELGD", "SELVA", "SEYKM", "SILVR",
        "SKTAS", "SMART", "SNGYO", "SNKRN", "SNPAM", "SODSN", "SOKE", "SONME", "SRVGY", "SUMAS",
        "SUNTK", "SUWEN", "TABGD", "TARKM", "TBORG", "TDGYO", "TEKTU", "TERA", "TETMT", "TEZOL",
        "TGSAS", "TLMAN", "TMPOL", "TNZTP", "TRCAS", "TRGYO", "TRILC", "TSGYO", "TUCLK", "TUKAS",
        "TURGG", "UFUK", "ULAS", "ULUFA", "ULUSE", "ULUUN", "UMPAS", "UNLU", "USAK", "UZERB",
        "VAKFN", "VAKKO", "VANGD", "VBTYZ", "VERTU", "VERUS", "VKFYO", "VKGYO", "VKING", "YAPRK",
        "YATAS", "YAYLA", "YESIL", "YGGYO", "YGYO", "YKSLN", "YONGA", "YUNSA", "YYAPI", "ZEDUR"
    ],
    "ABD (S&P + NASDAQ)": [
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META", "BRK-B", "LLY", "V", "TSM", "UNH", 
        "JPM", "XOM", "WMT", "JNJ", "MA", "PG", "AVGO", "HD", "ORCL", "CVX", "MRK", "KO", "PEP", 
        "COST", "ADBE", "CSCO", "MCD", "CRM", "DIS", "NKE", "WFC", "BAC", "VZ", "QCOM", "IBM", 
        "BA", "GE", "PLTR", "COIN", "PYPL", "UBER", "ABNB", "AMD", "INTC", "NFLX", "TMUS", "CMCSA",
        "TXN", "HON", "AMGN", "INTU", "SBUX", "GILD", "MDLZ", "BKNG", "ADI", "ISRG", "ADP", "LRCX",
        "REGN", "VRTX", "FISV", "KLAC", "SNPS", "CDNS", "MAR", "CSX", "PANW", "ORLY", 
        "MNST", "FTNT", "AEP", "CTAS", "KDP", "DXCM", "PAYX", "ODFL", "MCHP", "AIG", "ALL", "AXP",
        "BK", "BLK", "C", "CAT", "CL", "COF", "COP", "CVS", "D", "DE", "DHR", "DOW", "DUK", "EMR",
        "EXC", "F", "FDX", "GD", "GM", "GS", "HAL", "HPQ", "KR", "KMI", "LMT", "LOW", "MMM", "MET",
        "MO", "MS", "NEE", "NOC", "OXY", "PCG", "PFE", "PM", "PSX", "RTX", "SLB", "SO", "SPG", "T",
        "TGT", "TRV", "USB", "UPS", "WBA", "WMB", "ASML", "AZN", "LTC", "SHOP", "SONY", "TM"
    ],
    "KRIPTO": [
        "BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "AVAX", "DOGE", "SHIB", "DOT", 
        "MATIC", "LTC", "TRX", "UNI", "ATOM", "LINK", "XLM", "ALGO", "VET", "ICP",
        "NEAR", "FIL", "HBAR", "APT", "QNT", "LDO", "ARB", "OP", "RNDR", "GRT",
        "STX", "SAND", "EOS", "MANA", "THETA", "AAVE", "AXS", "FTM", "FLOW", "CHZ",
        "PEPE", "FLOKI", "GALA", "MINA", "SUI", "INJ", "RUNE", "KAS", "IMX", "SNX"
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
        if not data: return pd.DataFrame(columns=["Kod", "Pazar", "Adet", "Maliyet", "Tip", "Notlar"])
        df = pd.DataFrame(data)
        if "Tip" not in df.columns: df["Tip"] = "Portfoy"
        if "Notlar" not in df.columns: df["Notlar"] = ""
        return df
    except Exception as e:
        st.error(f"Hata: {e}")
        return pd.DataFrame(columns=["Kod", "Pazar", "Adet", "Maliyet", "Tip", "Notlar"])

def save_data_to_sheet(df):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = st.secrets["gcp_service_account"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    sheet = client.open(SHEET_NAME).sheet1
    sheet.clear()
    sheet.update([df.columns.values.tolist()] + df.values.tolist())

portfoy_df = get_data_from_sheet()
if not portfoy_df.empty:
    portfoy_df["Adet"] = pd.to_numeric(portfoy_df["Adet"], errors='coerce').fillna(0)
    portfoy_df["Maliyet"] = pd.to_numeric(portfoy_df["Maliyet"], errors='coerce').fillna(0)

# --- DATA MOTORU (FİYAT + ÖNCEKİ KAPANIŞ) ---
def fetch_market_data(kod, pazar, usd_try):
    """
    Hem güncel fiyatı hem de bir önceki kapanışı çeker (Günlük P/L için).
    """
    # --- 1. EŞLEŞTİRME ---
    yahoo_symbol = kod
    currency = "USD"
    
    if "BIST" in pazar:
        yahoo_symbol = f"{kod}.IS"
        currency = "TL"
    elif "KRIPTO" in pazar:
        yahoo_symbol = f"{kod}-USD"
    elif "EMTIA" in pazar:
        if "Altın ONS" in kod: yahoo_symbol = "GC=F"
        elif "Gümüş ONS" in kod: yahoo_symbol = "SI=F"
        elif "Petrol" in kod: yahoo_symbol = "BZ=F"
        elif "Doğalgaz" in kod: yahoo_symbol = "NG=F"
        elif "Bakır" in kod: yahoo_symbol = "HG=F"
        elif "Platin" in kod: yahoo_symbol = "PL=F"
        elif "Paladyum" in kod: yahoo_symbol = "PA=F"
    
    # --- 2. ÖZEL GRAM HESABI ---
    if "Gram Altın (TL)" in kod:
        try:
            hist = yf.Ticker("GC=F").history(period="5d")
            if len(hist) < 2: return 0, 0, "TL"
            ons_now = hist['Close'].iloc[-1]
            ons_prev = hist['Close'].iloc[-2]
            gram_now = (ons_now * usd_try) / 31.1035
            gram_prev = (ons_prev * usd_try) / 31.1035 # Dolar sabit varsayımıyla yaklaşık değişim
            return gram_now, gram_prev, "TL"
        except: return 0, 0, "TL"

    if "Gram Gümüş (TL)" in kod:
        try:
            hist = yf.Ticker("SI=F").history(period="5d")
            if len(hist) < 2: return 0, 0, "TL"
            ons_now = hist['Close'].iloc[-1]
            ons_prev = hist['Close'].iloc[-2]
            gram_now = (ons_now * usd_try) / 31.1035
            gram_prev = (ons_prev * usd_try) / 31.1035
            return gram_now, gram_prev, "TL"
        except: return 0, 0, "TL"
        
    # --- 3. NORMAL VARLIKLAR ---
    try:
        if "FIZIKI" in pazar: return 0, 0, "TL"
        
        ticker = yf.Ticker(yahoo_symbol)
        # Son 5 gün alalım ki hafta sonu vs. sorun olmasın
        hist = ticker.history(period="5d")
        
        if hist.empty: return 0, 0, currency
        
        current_price = hist['Close'].iloc[-1]
        # Eğer veri varsa bir önceki kapanışı al, yoksa bugünü al
        prev_close = hist['Close'].iloc[-2] if len(hist) > 1 else current_price
        
        return current_price, prev_close, currency
    except:
        return 0, 0, currency

# --- ANALİZ FONKSİYONU ---
def run_analysis(df, usd_try_rate):
    results = []
    # Mobilde progress bar bazen donuyor, bu yüzden sadece spinner
    # st.spinner("Fiyatlar güncelleniyor...") 
    
    for i, row in df.iterrows():
        kod, pazar, adet, maliyet = row["Kod"], row["Pazar"], row["Adet"], row["Maliyet"]
        
        curr_price, prev_close, currency = fetch_market_data(kod, pazar, usd_try_rate)
        
        if curr_price == 0 and "FIZIKI" not in pazar:
            curr_price = maliyet # Hata varsa maliyet göster
            prev_close = maliyet
        elif "FIZIKI" in pazar:
            curr_price = maliyet # Fiziki için manuel
            prev_close = maliyet

        val_now = curr_price * adet
        cost_total = maliyet * adet
        
        # Toplam P/L
        total_pnl = val_now - cost_total
        total_pnl_pct = (total_pnl / cost_total * 100) if cost_total > 0 else 0
        
        # Günlük P/L
        daily_change = curr_price - prev_close
        daily_pnl = daily_change * adet
        daily_pnl_pct = (daily_change / prev_close * 100) if prev_close > 0 else 0
        
        # TL Çevrimleri (Dashboard için)
        if currency == "USD":
            val_tl = val_now * usd_try_rate
            cost_tl = cost_total * usd_try_rate
            daily_pnl_tl = daily_pnl * usd_try_rate
        else:
            val_tl = val_now
            cost_tl = cost_total
            daily_pnl_tl = daily_pnl
            
        results.append({
            "Kod": kod, "Pazar": pazar, "Tip": row["Tip"],
            "Adet": adet, "Maliyet": maliyet,
            "Fiyat": curr_price, "Önceki": prev_close, "PB": currency,
            "Değer": val_now, "Top. P/L": total_pnl, "Top. %": total_pnl_pct,
            "Gün. P/L": daily_pnl, "Gün. %": daily_pnl_pct,
            "TL Değer": val_tl, "TL Maliyet": cost_tl, "TL Gün P/L": daily_pnl_tl,
            "Notlar": row["Notlar"]
        })
    return pd.DataFrame(results)

# --- ARAYÜZ: SEKMELER (TABS) ---
# Sidebar yerine en tepede sekmeler
tabs = st.tabs([
    "📊 Özet", "📈 BIST", "🇺🇸 ABD", "₿ Kripto", 
    "🛢️ Emtia", "🏠 Fiziki", "👀 İzleme", "⚙️ Ekle/Çıkar"
])

# Veri Analizi (Eğer veri varsa)
if not portfoy_df.empty:
    master_df = run_analysis(portfoy_df, USD_TRY)
    portfoy_only = master_df[master_df["Tip"] == "Portfoy"]
    takip_only = master_df[master_df["Tip"] == "Takip"]
else:
    master_df = pd.DataFrame()
    portfoy_only = pd.DataFrame()
    takip_only = pd.DataFrame()

# --- FONKSİYON: TABLO & METRİK GÖSTERİCİ ---
def render_category_tab(df_sub, currency_sym):
    if df_sub.empty:
        st.info("Bu kategoride varlık bulunamadı.")
        return

    # 1. ÖZET METRİKLER (Mobilde Yan Yana 2'li Sığar)
    toplam_deger = df_sub["Değer"].sum()
    toplam_kar = df_sub["Top. P/L"].sum()
    gunluk_kar = df_sub["Gün. P/L"].sum()
    
    c1, c2 = st.columns(2)
    c1.metric("Toplam Varlık", f"{currency_sym}{toplam_deger:,.0f}")
    c2.metric("Toplam Kâr/Zarar", f"{currency_sym}{toplam_kar:,.0f}", 
              delta_color="normal", delta=f"{toplam_kar:,.0f}")
    
    st.metric("Bugünkü Değişim (Günlük P/L)", f"{currency_sym}{gunluk_kar:,.0f}", 
              delta=f"{gunluk_kar:,.0f}", delta_color="normal")
    
    st.divider()
    
    # 2. DETAYLI KARTLAR (TABLO YERİNE EXPANDER - MOBİL İÇİN)
    # Mobilde tablo sağa sola kaydırma ister, expander daha rahattır.
    for i, row in df_sub.iterrows():
        with st.expander(f"**{row['Kod']}** | {row['Fiyat']:.2f} {row['PB']} ({row['Gün. %']:+.2f}%)"):
            col_a, col_b = st.columns(2)
            col_a.write(f"**Adet:** {row['Adet']}")
            col_b.write(f"**Maliyet:** {row['Maliyet']:.2f}")
            
            col_c, col_d = st.columns(2)
            col_c.write(f"**Değer:** {row['Değer']:,.0f}")
            col_d.write(f"**Kâr:** {row['Top. P/L']:,.0f} ({row['Top. %']:+.1f}%)")
            
            if row['Notlar']:
                st.caption(f"Not: {row['Notlar']}")

# --- TAB 1: GENEL ÖZET (TOTAL) ---
with tabs[0]:
    if not portfoy_only.empty:
        total_assets_tl = portfoy_only["TL Değer"].sum()
        total_pl_tl = portfoy_only["TL Değer"].sum() - portfoy_only["TL Maliyet"].sum()
        daily_pl_tl = portfoy_only["TL Gün P/L"].sum()
        
        col1, col2 = st.columns(2)
        col1.metric("Toplam Varlık (TL)", f"₺{total_assets_tl:,.0f}")
        col2.metric("Genel Kâr (TL)", f"₺{total_pl_tl:,.0f}", delta=f"{total_pl_tl:,.0f}")
        
        st.metric("Günlük Değişim (TL)", f"₺{daily_pl_tl:,.0f}", delta=f"{daily_pl_tl:,.0f}")
        
        st.divider()
        st.subheader("Varlık Dağılımı")
        # Mobilde grafiklerin taşmaması için use_container_width önemli
        chart_data = portfoy_only.groupby("Pazar")["TL Değer"].sum()
        st.bar_chart(chart_data, color="#4CAF50", use_container_width=True)
    else:
        st.info("Henüz portföy oluşturulmadı. 'Ekle/Çıkar' sekmesine gidin.")

# --- DİĞER TABLAR ---
with tabs[1]: render_category_tab(portfoy_only[portfoy_only["Pazar"].str.contains("BIST")], "₺")
with tabs[2]: render_category_tab(portfoy_only[portfoy_only["Pazar"].str.contains("ABD")], "$")
with tabs[3]: render_category_tab(portfoy_only[portfoy_only["Pazar"].str.contains("KRIPTO")], "$")
with tabs[4]: render_category_tab(portfoy_only[portfoy_only["Pazar"].str.contains("EMTIA")], "")
with tabs[5]: render_category_tab(portfoy_only[portfoy_only["Pazar"].str.contains("FIZIKI")], "")

with tabs[6]: # İZLEME LİSTESİ
    if not takip_only.empty:
        st.subheader("👀 İzleme Listesi")
        for i, row in takip_only.iterrows():
            st.markdown(f"**{row['Kod']}** ({row['Pazar']}) -> **{row['Fiyat']:.2f} {row['PB']}** ({row['Gün. %']:+.2f}%)")
    else:
        st.info("İzleme listeniz boş.")

# --- TAB 7: AYARLAR / EKLE ÇIKAR (FORM BURADA) ---
with tabs[7]:
    st.header("Varlık Yönetimi")
    
    tab_ekle, tab_sil = st.tabs(["➕ Ekle", "🗑️ Sil"])
    
    with tab_ekle:
        islem_tipi = st.radio("Tür", ["Portföy", "Takip"], horizontal=True)
        yeni_pazar = st.selectbox("Pazar", list(MARKET_DATA.keys()))
        secenekler = MARKET_DATA.get(yeni_pazar, [])
        
        with st.form("add_asset_form"):
            yeni_kod = st.selectbox("Varlık", options=secenekler, index=None, placeholder="Seçiniz...")
            manuel_giris = st.checkbox("Listede Yok")
            if manuel_giris:
                yeni_kod = st.text_input("Manuel Kod").upper()
            
            c1, c2 = st.columns(2)
            adet_inp = c1.number_input("Adet", min_value=0.0, step=0.01)
            maliyet_inp = c2.number_input("Maliyet", min_value=0.0, step=0.01)
            not_inp = st.text_input("Not")
            
            if st.form_submit_button("Kaydet", type="primary", use_container_width=True):
                if yeni_kod:
                    # Eski kaydı silip yenisini ekleyerek güncelleme mantığı
                    portfoy_df = portfoy_df[portfoy_df["Kod"] != yeni_kod]
                    tip_str = "Portfoy" if islem_tipi == "Portföy" else "Takip"
                    yeni_satir = pd.DataFrame({
                        "Kod": [yeni_kod], "Pazar": [yeni_pazar], 
                        "Adet": [adet_inp], "Maliyet": [maliyet_inp],
                        "Tip": [tip_str], "Notlar": [not_inp]
                    })
                    portfoy_df = pd.concat([portfoy_df, yeni_satir], ignore_index=True)
                    save_data_to_sheet(portfoy_df)
                    st.success("Kaydedildi!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Varlık seçmelisiniz.")

    with tab_sil:
        if not portfoy_df.empty:
            sil_kod = st.selectbox("Silinecek:", portfoy_df["Kod"].unique())
            if st.button("Seçileni Sil", type="secondary", use_container_width=True):
                portfoy_df = portfoy_df[portfoy_df["Kod"] != sil_kod]
                save_data_to_sheet(portfoy_df)
                st.success("Silindi.")
                st.rerun()
        else:
            st.info("Listeniz boş.")
