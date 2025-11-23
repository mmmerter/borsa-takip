import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime
import yfinance as yf
import feedparser
import requests


# ---------------------------------------------------------
# AUTH
# ---------------------------------------------------------
def get_sheet_client():
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name("creds.json", scope)
    client = gspread.authorize(creds)
    return client


# ---------------------------------------------------------
# ANA PORTFÖY DATA OKUMA / YAZMA
# ---------------------------------------------------------
def get_data_from_sheet():
    client = get_sheet_client()
    sheet = client.open("PortfoyData").worksheet("Sheet1")
    df = pd.DataFrame(sheet.get_all_records())
    return df


def save_data_to_sheet(df):
    client = get_sheet_client()
    sheet = client.open("PortfoyData").worksheet("Sheet1")
    sheet.clear()
    sheet.update([df.columns.values.tolist()] + df.values.tolist())


# ---------------------------------------------------------
# SATIŞ GEÇMİŞİ
# ---------------------------------------------------------
def get_sales_history():
    client = get_sheet_client()
    sheet = client.open("PortfoyData").worksheet("Satışlar")
    df = pd.DataFrame(sheet.get_all_records())
    return df


def add_sale_record(row):
    client = get_sheet_client()
    sheet = client.open("PortfoyData").worksheet("Satışlar")
    sheet.append_row(row)


# ---------------------------------------------------------
# USD/TRY
# ---------------------------------------------------------
def get_usd_try():
    try:
        data = yf.Ticker("USDTRY=X").history(period="1d")
        if not data.empty:
            return float(data["Close"].iloc[-1])
    except:
        pass
    return 30.00  # fallback


# ---------------------------------------------------------
# TEFAS (Fon)
# ---------------------------------------------------------
def get_tefas_data(kod):
    url = f"https://arka.tefas.gov.tr/api/fon/bilgi?FonKod={kod}"
    try:
        r = requests.get(url, timeout=5)
        j = r.json()
        f = j["data"]
        return float(f["Fiyat"]), float(f["OncekiFiyat"])
    except:
        return 0, 0


# ---------------------------------------------------------
# HABERLER
# ---------------------------------------------------------
def get_financial_news(category):
    RSS = {
        "BIST": "https://www.bloomberght.com/rss/borsa.xml",
        "KRIPTO": "https://www.coindesk.com/arc/outboundfeeds/rss/",
        "GLOBAL": "https://www.investing.com/rss/news_285.rss",
        "DOVIZ": "https://www.bloomberght.com/rss/doviz.xml",
    }
    try:
        feed = feedparser.parse(RSS.get(category, RSS["GLOBAL"]))
        news = []
        for e in feed.entries[:12]:
            news.append({"title": e.title, "link": e.link, "date": e.published})
        return news
    except:
        return []


# ---------------------------------------------------------
# İZLEME İÇİN TICKER VERİSİ
# ---------------------------------------------------------
def get_tickers_data(df, usd_try):
    mh = ""
    ph = ""
    try:
        for _, row in df.iterrows():
            kod = row.get("Kod", "")
            pazar = row.get("Pazar", "")
            adet = row.get("Adet", 0)

            if not kod:
                continue

            if "BIST" in pazar.upper():
                symbol = f"{kod}.IS"
            elif "ABD" in pazar.upper():
                symbol = kod
            elif "KRIPTO" in pazar.upper():
                symbol = f"{kod}-USD"
            else:
                continue

            try:
                data = yf.Ticker(symbol).history(period="1d")
                if not data.empty:
                    price = float(data["Close"].iloc[-1])
                else:
                    price = 0
            except:
                price = 0

            mh += f" {kod}: {price} | "

    except:
        pass

    # Portföy ticker
    try:
        total_value = df["Değer"].sum()
        ph = f" Toplam Portföy: {total_value:,.0f}"
    except:
        ph = ""

    return mh, ph


# ===================================================================
# 📌 **YENİ BÖLÜM — KRAL ULTRA v3**
#     Günlük Portföy Log Sistemi (GERÇEK Haftalık / Aylık / YTD için)
# ===================================================================

# ---------------------------------------------------------
# 1) portfolio_history tablosunu oku
# ---------------------------------------------------------
def read_portfolio_history():
    client = get_sheet_client()
    sheet = client.open("PortfoyData").worksheet("portfolio_history")

    df = pd.DataFrame(sheet.get_all_records())

    if df.empty:
        return pd.DataFrame(columns=["Tarih", "Değer_TRY", "Değer_USD"])

    # Tarihi datetime'e çevir
    df["Tarih"] = pd.to_datetime(df["Tarih"])
    return df.sort_values("Tarih")


# ---------------------------------------------------------
# 2) Bugünün kaydı var mı kontrol et
# ---------------------------------------------------------
def today_history_exists(df):
    today = pd.to_datetime(datetime.now().strftime("%Y-%m-%d"))
    return any(df["Tarih"] == today)


# ---------------------------------------------------------
# 3) Bugünün kaydını ekle
# ---------------------------------------------------------
def write_portfolio_history(value_try, value_usd):
    client = get_sheet_client()
    sheet = client.open("PortfoyData").worksheet("portfolio_history")

    today = datetime.now().strftime("%Y-%m-%d")

    new_row = [today, float(value_try), float(value_usd)]
    sheet.append_row(new_row)


# ---------------------------------------------------------
# 4) Haftalık / Aylık / YTD hesaplamaları için tek fonksiyon
# ---------------------------------------------------------
def get_timeframe_changes(history_df):
    """
    history_df → read_portfolio_history()

    Dönüş:
    {
        "weekly": (value, pct),
        "monthly": (value, pct),
        "ytd": (value, pct),
        "spark_week": [...],
        "spark_month": [...],
        "spark_ytd": [...],
    }
    """

    if history_df.empty:
        return None

    today = history_df.iloc[-1]["Değer_TRY"]
    dates = history_df["Tarih"]

    def calc_period(days):
        target = dates.max() - pd.Timedelta(days=days)
        subset = history_df[history_df["Tarih"] >= target]
        if subset.empty:
            return 0, 0, []
        start = subset.iloc[0]["Değer_TRY"]
        val = today - start
        pct = (val / start * 100) if start > 0 else 0
        spark = list(subset["Değer_TRY"])
        return val, pct, spark

    # Haftalık
    week_val, week_pct, week_spark = calc_period(7)

    # Aylık
    month_val, month_pct, month_spark = calc_period(30)

    # YTD
    year_start = history_df[history_df["Tarih"].dt.month == 1]
    if not year_start.empty:
        start = year_start.iloc[0]["Değer_TRY"]
        ytd_val = today - start
        ytd_pct = (ytd_val / start * 100) if start > 0 else 0
        ytd_spark = list(history_df[history_df["Tarih"] >= year_start.iloc[0]["Tarih"]]["Değer_TRY"])
    else:
        ytd_val, ytd_pct, ytd_spark = 0, 0, []

    return {
        "weekly": (week_val, week_pct),
        "monthly": (month_val, month_pct),
        "ytd": (ytd_val, ytd_pct),
        "spark_week": week_spark,
        "spark_month": month_spark,
        "spark_ytd": ytd_spark,
    }
