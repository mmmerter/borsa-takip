import re
import pandas as pd
import streamlit as st

ANALYSIS_COLS = [
    "Kod",
    "Pazar",
    "Tip",
    "Adet",
    "Maliyet",
    "Fiyat",
    "PB",
    "Değer",
    "Top. Kâr/Zarar",
    "Top. %",
    "Gün. Kâr/Zarar",
    "Notlar",
]

KNOWN_FUNDS = [
    "YHB",
    "TTE",
    "MAC",
    "AFT",
    "AFA",
    "YAY",
    "IPJ",
    "TCD",
    "NNF",
    "GMR",
    "TI2",
    "TI3",
    "IHK",
    "IDH",
    "OJT",
    "HKH",
    "IPB",
    "KZL",
    "RPD",
    "URA",
]

MARKET_DATA = {
    "BIST (Tümü)": ["THYAO", "GARAN", "ASELS", "TRMET"],
    "ABD": ["AAPL", "TSLA"],
    "KRIPTO": ["BTC", "ETH"],
    "FON": KNOWN_FUNDS,
    "EMTIA": ["Gram Altın", "Gram Gümüş"],
    "VADELI": ["BTC", "ETH", "SOL"],
    "NAKIT": ["TL", "USD", "EUR"],
}


def get_yahoo_symbol(kod, pazar):
    kod = str(kod).upper()

    if pazar == "NAKIT":
        return kod # Nakit sembolü olduğu gibi döner (TL, USD)
    if pazar == "FON":
        return kod

    if "BIST" in pazar:
        return f"{kod}.IS" if not kod.endswith(".IS") else kod
    elif "KRIPTO" in pazar:
        return f"{kod}-USD" if not kod.endswith("-USD") else kod
    elif "EMTIA" in pazar:
        # Gramlar için Ons sembolü döndür, hesaplama charts.py'da yapılacak
        if "Gram Altın" in kod or "GRAM ALTIN" in kod:
            return "GC=F"
        if "Gram Gümüş" in kod or "GRAM GÜMÜŞ" in kod:
            return "SI=F"
            
        map_emtia = {
            "Altın ONS": "GC=F",
            "Gümüş ONS": "SI=F",
            "Petrol": "BZ=F",
            "Doğalgaz": "NG=F",
            "Bakır": "HG=F",
        }
        for k, v in map_emtia.items():
            if k in kod:
                return v
        return kod

    return kod


def smart_parse(text_val):
    if text_val is None:
        return 0.0
    val = str(text_val).strip()
    if not val:
        return 0.0

    # Rakam dışı her şeyi sil (., hariç)
    val = re.sub(r"[^\d.,]", "", val)

    # Birden fazla nokta varsa ve virgül yoksa -> ilk nokta hariç hepsini kaldır
    if val.count(".") > 1 and "," not in val:
        parts = val.split(".")
        val = f"{parts[0]}.{''.join(parts[1:])}"

    # Hem nokta hem virgül varsa -> binlik ayırıcıları temizle, virgülü ondalık yap
    if "." in val and "," in val:
        val = val.replace(".", "").replace(",", ".")
    elif "," in val:
        val = val.replace(",", ".")

    try:
        return float(val)
    except Exception:
        return 0.0


def styled_dataframe(df: pd.DataFrame):
    """
    Dataframe için ortak stil:
    - Yazılar daha büyük ve kalın
    - Kâr / Zarar kolonları: pozitif yeşil, negatif kırmızı
    """
    if df.empty:
        return df

    # Sayısal kolon formatı
    format_dict = {}
    for col in df.columns:
        if df[col].dtype in ["float64", "float32", "int64", "int32"]:
            format_dict[col] = "{:,.2f}"

    styler = df.style.format(format_dict)

    # Genel font boyutu & kalınlık
    styler = styler.set_table_styles(
        [
            {
                "selector": "th",
                "props": [
                    ("font-size", "22px"),
                    ("font-weight", "900"),
                    ("text-align", "center"),
                ],
            },
            {
                "selector": "td",
                "props": [
                    ("font-size", "20px"),
                    ("font-weight", "900"),
                ],
            },
        ]
    )

    # Sayısal kolonları sağa hizala
    num_cols = [
        col
        for col in df.columns
        if df[col].dtype in ["float64", "float32", "int64", "int32"]
    ]
    if num_cols:
        styler = styler.set_properties(
            subset=num_cols,
            **{"text-align": "right"},
        )

    # Kâr / Zarar ve yüzde kolonlarını renklendir
    def color_pnl(val):
        try:
            v = float(val)
        except Exception:
            return ""
        if v > 0:
            return "color: #00e676;"  # yeşil
        elif v < 0:
            return "color: #ff5252;"  # kırmızı
        else:
            return "color: #cccccc;"  # nötr gri

    pnl_cols = [
        "Top. Kâr/Zarar",
        "Top. %",
        "Gün. Kâr/Zarar",
        "Kâr/Zarar",
        "Değişim %",  # İzleme listesi için
    ]
    for col in pnl_cols:
        if col in df.columns:
            styler = styler.applymap(color_pnl, subset=[col])

    return styler


def get_pnl_color_style(val):
    """Kâr/Zarar değerine göre CSS style döndürür."""
    try:
        v = float(val)
    except Exception:
        return ""
    if v > 0:
        return "color: #00e676;"  # yeşil
    elif v < 0:
        return "color: #ff5252;"  # kırmızı
    else:
        return "color: #cccccc;"  # nötr gri


def get_pazar_icon(pazar: str) -> str:
    """
    Pazar adına göre ikon/emoji döndürür.
    Dashboard ve grafiklerde kullanılacak.
    """
    pazar_upper = str(pazar).upper()
    
    if "EMTIA" in pazar_upper:
        return "⚡"  # Emtia ikonu
    elif "NAKIT" in pazar_upper:
        return "💵"  # Nakit ikonu
    elif "ABD" in pazar_upper or "US" in pazar_upper or "S&P" in pazar_upper or "NASDAQ" in pazar_upper:
        return "🇺🇸"  # ABD bayrağı
    elif "BIST" in pazar_upper:
        return "📈"  # BIST ikonu
    elif "FON" in pazar_upper:
        return "📊"  # Fon ikonu
    elif "KRIPTO" in pazar_upper:
        return "₿"  # Kripto ikonu
    else:
        return "📌"  # Varsayılan


@st.cache_data(ttl=86400)  # 24 saat cache - logolar çok sık değişmez
def get_stock_logo_url(kod: str, pazar: str) -> str:
    """
    Şirket logosu URL'ini döndürür.
    BIST için Paratic, ABD için alternatif kaynaklar kullanır.
    Yeni şirketler eklendiğinde otomatik olarak logo URL'i oluşturulur.
    """
    kod = str(kod).upper().strip()
    pazar_upper = str(pazar).upper()
    
    # BIST için Paratic logo URL'i
    if "BIST" in pazar_upper:
        # Paratic'in logo URL formatı: https://static.paratic.com/logolar/{KOD}.png
        return f"https://static.paratic.com/logolar/{kod}.png"
    
    # ABD için Financial Modeling Prep veya alternatif
    elif "ABD" in pazar_upper or "US" in pazar_upper:
        # Financial Modeling Prep logo URL formatı
        return f"https://financialmodelingprep.com/image-stock/{kod}.png"
    
    # Diğer pazarlar için varsayılan (boş string döner, ikon kullanılır)
    return ""


def get_logo_html(kod: str, pazar: str, size: int = 24) -> str:
    """
    Logo için HTML img tag'i döndürür.
    Treemap ve diğer grafiklerde kullanılacak.
    Logo bulunamazsa boş string döner.
    """
    logo_url = get_stock_logo_url(kod, pazar)
    if not logo_url:
        return ""
    
    # HTML img tag'i - hata durumunda gizlenir
    return f'<img src="{logo_url}" style="width:{size}px;height:{size}px;vertical-align:middle;margin-right:4px;border-radius:4px;object-fit:contain;" onerror="this.style.display=\'none\'" />'


def get_label_with_icon(label: str, pazar: str = "") -> str:
    """
    Label'a pazar ikonu ekler.
    Pasta ve bar chart'larda kullanılacak.
    """
    icon = get_pazar_icon(pazar) if pazar else ""
    if icon:
        return f"{icon} {label}"
    return label
