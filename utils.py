import re
import pandas as pd

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

    # Özel mapping
    if kod == "TRMET":
        return "KOZAA.IS"

    if pazar == "NAKIT":
        return kod
    if pazar == "FON":
        return kod

    if "BIST" in pazar:
        return f"{kod}.IS" if not kod.endswith(".IS") else kod
    elif "KRIPTO" in pazar:
        return f"{kod}-USD" if not kod.endswith("-USD") else kod
    elif "EMTIA" in pazar:
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
    Tüm sekmeler için tablo görünümü:
    - Font daha büyük ve kalın
    - Kâr/Zarar kolonları yeşil/kırmızı
    """
    if df.empty:
        return df

    # Sayısal kolonları 2 hane formatla
    format_dict = {}
    for col in df.columns:
        if df[col].dtype in ["float64", "float32", "int64", "int32"]:
            format_dict[col] = "{:,.2f}"

    # Kâr/Zarar kolonları
    pnl_cols = [
        c
        for c in ["Top. Kâr/Zarar", "Top. %", "Gün. Kâr/Zarar", "Kâr/Zarar"]
        if c in df.columns
    ]

    def pnl_style(val):
        try:
            v = float(val)
        except Exception:
            return ""
        if v > 0:
            return "color:#00e676; font-weight:bold;"
        elif v < 0:
            return "color:#ff5252; font-weight:bold;"
        else:
            return "font-weight:bold;"

    # Genel font büyüklüğü
    table_styles = [
        {
            "selector": "th",
            "props": [
                ("font-size", "13px"),
                ("font-weight", "600"),
            ],
        },
        {
            "selector": "td",
            "props": [
                ("font-size", "13px"),
                ("font-weight", "600"),
            ],
        },
    ]

    styler = df.style.format(format_dict)

    if pnl_cols:
        styler = styler.applymap(pnl_style, subset=pd.IndexSlice[:, pnl_cols])

    styler = styler.set_table_styles(table_styles)

    return styler
