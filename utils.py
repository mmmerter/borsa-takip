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
    Dataframe görünümü:
    - Daha büyük ve kalın font
    - Sayısal kolonlar formatlı
    - Kâr/Zarar kolonları: pozitif yeşil, negatif kırmızı
    """
    if df.empty:
        return df

    # Sayısal kolonları 2 haneli formatla
    format_dict = {}
    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            format_dict[col] = "{:,.2f}"

    styler = df.style.format(format_dict)

    # Genel font boyutu ve kalınlık
    styler = styler.set_table_styles(
        [
            {
                "selector": "th",
                "props": [("font-size", "14px"), ("font-weight", "bold")],
            },
            {
                "selector": "td",
                "props": [("font-size", "13px"), ("font-weight", "bold")],
            },
        ]
    )

    # Kâr/Zarar kolonlarını renklendir
    def pnl_style(val):
        try:
            v = float(val)
        except (TypeError, ValueError):
            return ""
        if v > 0:
            return "color: #00e676; font-weight: bold;"
        elif v < 0:
            return "color: #ff5252; font-weight: bold;"
        else:
            return "color: #dddddd; font-weight: bold;"

    pnl_cols = ["Top. Kâr/Zarar", "Top. %", "Gün. Kâr/Zarar", "Kâr/Zarar"]
    existing = [c for c in pnl_cols if c in df.columns]
    if existing:
        styler = styler.applymap(pnl_style, subset=existing)

    return styler
