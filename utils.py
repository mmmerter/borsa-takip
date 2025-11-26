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
    "Yatırılan",
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
    Dataframe için modern stil:
    - Modern Inter font ailesi
    - Dengeli font boyutları ve ağırlıkları
    - Hover efektleri ve yumuşak geçişler
    - Gradient arka planlar
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

    # Modern tablo stilleri
    styler = styler.set_table_styles(
        [
            # Tablo genel stil
            {
                "selector": "table",
                "props": [
                    ("border-collapse", "separate"),
                    ("border-spacing", "0"),
                    ("width", "100%"),
                    ("border-radius", "12px"),
                    ("overflow", "hidden"),
                    ("box-shadow", "0 4px 12px rgba(0, 0, 0, 0.3)"),
                    ("background", "linear-gradient(135deg, #1a1c24 0%, #0e1117 100%)"),
                ],
            },
            # Başlık hücresi stil
            {
                "selector": "th",
                "props": [
                    ("font-family", "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"),
                    ("font-size", "14px"),
                    ("font-weight", "700"),
                    ("text-align", "center"),
                    ("padding", "16px 12px"),
                    ("background", "linear-gradient(135deg, #232837 0%, #171b24 100%)"),
                    ("color", "#b0b3c0"),
                    ("text-transform", "uppercase"),
                    ("letter-spacing", "0.5px"),
                    ("border-bottom", "2px solid #6b7fd7"),
                    ("position", "sticky"),
                    ("top", "0"),
                    ("z-index", "10"),
                ],
            },
            # Veri hücresi stil
            {
                "selector": "td",
                "props": [
                    ("font-family", "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"),
                    ("font-size", "15px"),
                    ("font-weight", "500"),
                    ("padding", "14px 12px"),
                    ("color", "#ffffff"),
                    ("border-bottom", "1px solid rgba(255, 255, 255, 0.05)"),
                    ("transition", "all 0.3s ease"),
                ],
            },
            # Satır hover efekti
            {
                "selector": "tbody tr",
                "props": [
                    ("transition", "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)"),
                    ("background", "transparent"),
                ],
            },
            {
                "selector": "tbody tr:hover",
                "props": [
                    ("background", "rgba(107, 127, 215, 0.08)"),
                    ("transform", "scale(1.01)"),
                    ("box-shadow", "0 2px 8px rgba(107, 127, 215, 0.2)"),
                ],
            },
            # Alternatif satır rengi
            {
                "selector": "tbody tr:nth-child(even)",
                "props": [
                    ("background", "rgba(255, 255, 255, 0.02)"),
                ],
            },
        ]
    )

    # Sayısal kolonları sağa hizala ve daha belirgin yap
    num_cols = [
        col
        for col in df.columns
        if df[col].dtype in ["float64", "float32", "int64", "int32"]
    ]
    if num_cols:
        styler = styler.set_properties(
            subset=num_cols,
            **{
                "text-align": "right",
                "font-weight": "600",
                "font-variant-numeric": "tabular-nums",
            },
        )

    # Kâr / Zarar ve yüzde kolonlarını modern renklerle renklendir
    def color_pnl(val):
        try:
            v = float(val)
        except Exception:
            return ""
        if v > 0:
            return "color: #00e676; font-weight: 700; text-shadow: 0 0 8px rgba(0, 230, 118, 0.3);"
        elif v < 0:
            return "color: #ff5252; font-weight: 700; text-shadow: 0 0 8px rgba(255, 82, 82, 0.3);"
        else:
            return "color: #9da1b3; font-weight: 500;"

    pnl_cols = [
        "Top. Kâr/Zarar",
        "Top. %",
        "Gün. Kâr/Zarar",
        "Kâr/Zarar",
        "Değişim %",
        "Pay (%)",
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
