import re
import pandas as pd
import streamlit as st

from st_aggrid import AgGrid, GridOptionsBuilder
from st_aggrid.shared import JsCode

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


# Eski stil fonksiyonu kalsın, ihtiyaç olursa kullanırız
def styled_dataframe(df: pd.DataFrame):
    if df.empty:
        return df
    return df


# --- AGGRID TABLO RENDERER ---
def render_table(df: pd.DataFrame, height: int = 420):
    """
    Tüm sekmelerde tablo gösterimi:
    - Büyük ve kalın font (CSS ile portfoy.py içinde ayarlı)
    - Kâr/Zarar kolonlarında pozitif yeşil, negatif kırmızı
    """
    if df.empty:
        st.info("Veri yok.")
        return

    gb = GridOptionsBuilder.from_dataframe(df)

    # Varsayılan kolon davranışı
    gb.configure_default_column(
        resizable=True,
        filter=True,
        sortable=True,
    )

    # Sayısal kolonlar için sağ hizalama
    num_cols = [
        col
        for col in df.columns
        if df[col].dtype in ["float64", "float32", "int64", "int32"]
    ]
    for col in num_cols:
        gb.configure_column(col, type=["numericColumn", "rightAligned"])

    # Kâr / Zarar kolonları için JS bazlı renk fonksiyonu
    pnl_style = JsCode(
        """
        function(params) {
            if (params.value === null || params.value === undefined || params.value === '') {
                return {'color': '#cccccc', 'font-weight': 'bold'};
            }
            let v = Number(params.value);
            if (isNaN(v)) {
                return {'color': '#cccccc', 'font-weight': 'bold'};
            }
            if (v > 0) {
                return {'color': '#00e676', 'font-weight': 'bold'};
            } else if (v < 0) {
                return {'color': '#ff5252', 'font-weight': 'bold'};
            } else {
                return {'color': '#cccccc', 'font-weight': 'bold'};
            }
        }
        """
    )

    pnl_cols = [
        "Top. Kâr/Zarar",
        "Top. %",
        "Gün. Kâr/Zarar",
        "Kâr/Zarar",  # Satışlar sekmesi için
    ]
    for col in pnl_cols:
        if col in df.columns:
            gb.configure_column(col, cellStyle=pnl_style)

    # Satır yüksekliği + genel grid ayarları
    gb.configure_grid_options(
        rowHeight=32,
    )

    grid_options = gb.build()

    # Basit çağrı: sorun çıkaran ekstra parametre yok
    AgGrid(
        df,
        gridOptions=grid_options,
        height=height,
    )
