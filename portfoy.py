# main.py
import streamlit as st
from streamlit_option_menu import option_menu
import pandas as pd

from utils import ANALYSIS_COLS, KNOWN_FUNDS, MARKET_DATA, smart_parse, styled_dataframe
from data_loader import (
    get_data_from_sheet,
    save_data_to_sheet,
    get_usd_try,
    get_tickers_data,
    get_tefas_data,
)
from charts import render_pie_bar_charts, render_pazar_tab

# burada KRAL'daki CSS, set_page_config, news section vs. aynen durabilir

st.set_page_config(
    page_title="Merter’in Terminali",
    layout="wide",
    page_icon="🏦",
    initial_sidebar_state="collapsed",
)

# ... CSS injection ...

portfoy_df = get_data_from_sheet()

c_title, c_toggle = st.columns([3, 1])
with c_title:
    st.title("🏦 Merter'in Varlık Yönetim Terminali")
with c_toggle:
    st.write("")
    GORUNUM_PB = st.radio("Para Birimi:", ["TRY", "USD"], horizontal=True)

USD_TRY = get_usd_try()
sym = "₺" if GORUNUM_PB == "TRY" else "$"

mh, ph = get_tickers_data(portfoy_df, USD_TRY)
st.markdown(
    f"""
<div class="ticker-container market-ticker">{mh}</div>
<div class="ticker-container portfolio-ticker">{ph}</div>
""",
    unsafe_allow_html=True,
)

# menü + run_analysis fonksiyonu vs.
