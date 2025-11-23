import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import requests
import feedparser
from tefas import Crawler
import yfinance as yf
import ccxt
import pandas as pd
import re

from utils import get_yahoo_symbol

SHEET_NAME = "PortfoyData"


# --- GOOGLE SHEETS ---
def get_data_from_sheet():
    try:
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(
            st.secrets["gcp_service_account"], scope
        )
        client = gspread.authorize(creds)
        sheet = client.open(SHEET_NAME).sheet1
        data = sheet.get_all_records()

        if not data:
            return pd.DataFrame(
                columns=["Kod", "Pazar", "Adet", "Maliyet", "Tip", "Notlar"]
            )

        df = pd.DataFrame(data)

        for col in ["Kod", "Pazar", "Adet", "Maliyet", "Tip", "Notlar"]:
            if col not in df.columns:
                df[col] = ""

        if not df.empty:
            df["Pazar"] = df["Pazar"].apply(
                lambda x: "FON" if "FON" in str(x) else x
            )
            df["Pazar"] = df["Pazar"].apply(
                lambda x: "EMTIA" if "FIZIKI" in str(x).upper() else x
            )

        return df
    except Exception:
        return pd.DataFrame(
            columns=["Kod", "Pazar", "Adet", "Maliyet", "Tip", "Notlar"]
        )


def save_data_to_sheet(df):
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        st.secrets["gcp_service_account"], scope
    )
    client = gspread.authorize(creds)
    sheet = client.open(SHEET_NAME).sheet1
    sheet.clear()
    sheet.update([df.columns.values.tolist()] + df.values.tolist())


def get_sales_history():
    try:
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(
            st.secrets["gcp_service_account"], scope
        )
        client = gspread.authorize(creds)
        sheet = client.open(SHEET_NAME).worksheet("Satislar")
        data = sheet.get_all_records()
        if not data:
            return pd.DataFrame(
                columns=[
                    "Tarih",
                    "Kod",
                    "Pazar",
                    "Satılan Adet",
                    "Satış Fiyatı",
                    "Maliyet",
                    "Kâr/Zarar",
                ]
            )
        return pd.DataFrame(data)
    except Exception:
        return pd.DataFrame(
            columns=[
                "Tarih",
                "Kod",
                "Pazar",
                "Satılan Adet",
                "Satış Fiyatı",
                "Maliyet",
                "Kâr/Zarar",
            ]
        )


def add_sale_record(date, code, market, qty, price, cost, profit):
    try:
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(
            st.secrets["gcp_service_account"], scope
        )
        client = gspread.authorize(creds)
        sheet = client.open(SHEET_NAME).worksheet("Satislar")
        sheet.append_row(
            [
                str(date),
                code,
                market,
                float(qty),
                float(price),
                float(cost),
                float(profit),
            ]
        )
    except Exception:
        pass


# --- TEFAS ---
@st.cache_data(ttl=14400)  # 4 saat – KRAL ile aynı
def get_tefas_data(fund_code):
    # Önce TEFAS HTML parse denemesi
    try:
        url = f"https://www.tefas.gov.tr/FonAnaliz.aspx?FonKod={fund_code}"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=5)
        if r.status_code == 200:
            match = re.search(
                r'id="MainContent_PanelInfo_lblPrice">([\d,]+)', r.text
            )
            if match:
                last = float(match.group(1).replace(",", "."))
                return last, last
    except Exception:
        pass

    # Olmazsa Crawler ile son 30 gün
    try:
        crawler = Crawler()
        end = datetime.now().strftime("%Y-%m-%d")
        start = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        res = crawler.fetch(start=start, end=end, name=fund_code, columns=["Price"])
        if not res.empty:
            res = res.sort_index()
            return float(res["Price"].iloc[-1]), float(res["Price"].iloc[-2])
    except Exception:
        pass

    return 0, 0


# --- COINGECKO ---
@st.cache_data(ttl=300)  # 5 dk – KRAL’daki gibi
def get_crypto_globals():
    try:
        d = requests.get(
            "https://api.coingecko.com/api/v3/global", timeout=5
        ).json()["data"]
        total_cap = d["total_market_cap"]["usd"]
        btc_d = d["market_cap_percentage"]["btc"]
        eth_d = d["market_cap_percentage"]["eth"]
        top2 = btc_d + eth_d
        total3 = total_cap * (1 - (top2 / 100))
        others_d = 100 - top2
        return total_cap, btc_d, total3, others_d, total3
    except Exception:
        return 0, 0, 0, 0, 0


# --- USD/TRY ---
@st.cache_data(ttl=300)  # 5 dk – KRAL ile aynı
def get_usd_try():
    try:
        return yf.Ticker("TRY=X").history(period="1d")["Close"].iloc[-1]
    except Exception:
        return 34.0


# --- HABERLER ---
@st.cache_data(ttl=300)
def get_financial_news(topic="finance"):
    urls = {
        "BIST": "https://news.google.com/rss/search?q=Borsa+Istanbul+Hisseler&hl=tr&gl=TR&ceid=TR:tr",
        "KRIPTO": "https://news.google.com/rss/search?q=Kripto+Para+Bitcoin&hl=tr&gl=TR&ceid=TR:tr",
        "GLOBAL": "https://news.google.com/rss/search?q=ABD+Borsaları+Fed&hl=tr&gl=TR&ceid=TR:tr",
        "DOVIZ": "https://news.google.com/rss/search?q=Dolar+Altın+Piyasa&hl=tr&gl=TR&ceid=TR:tr",
    }
    try:
        feed = feedparser.parse(urls.get(topic, urls["BIST"]))
        return [
            {"title": e.title, "link": e.link, "date": e.published}
            for e in feed.entries[:10]
        ]
    except Exception:
        return []


# --- TAPE ---
@st.cache_data(ttl=45)  # KRAL’daki gibi 45 sn
def get_tickers_data(df_portfolio, usd_try):
    # HATA VEREN relative import SİLİNDİ
    # Aynı dosyadaki cache'li fonksiyonu direkt çağırıyoruz
    total_cap, btc_d, total_3, others_d, others_cap = get_crypto_globals()

    market_symbols = [
        ("BIST 100", "XU100.IS"),
        ("USD", "TRY=X"),
        ("EUR", "EURTRY=X"),
        ("BTC/USDT", "BTC-USD"),
        ("ETH/USDT", "ETH-USD"),
        ("Ons Altın", "GC=F"),
        ("Ons Gümüş", "SI=F"),
        ("NASDAQ", "^IXIC"),
        ("S&P 500", "^GSPC"),
    ]

    portfolio_symbols = {}
    if not df_portfolio.empty:
        assets = df_portfolio[df_portfolio["Tip"] == "Portfoy"]
        for _, row in assets.iterrows():
            if (
                "NAKIT" not in row["Pazar"]
                and "Gram" not in row["Kod"]
                and "FON" not in row["Pazar"]
            ):
                portfolio_symbols[row["Kod"]] = get_yahoo_symbol(
                    row["Kod"], row["Pazar"]
                )

    all_fetch = list(
        set([s[1] for s in market_symbols] + list(portfolio_symbols.values()))
    )

    market_html = '<span style="color:#aaa">🌍 PİYASA:</span> &nbsp;'
    portfolio_html = '<span style="color:#aaa">💼 PORTFÖY:</span> &nbsp;'

    try:
        yahoo_data = yf.Tickers(" ".join(all_fetch))

        def get_val(symbol, label=None):
            try:
                h = yahoo_data.tickers[symbol].history(period="2d")
                if not h.empty:
                    p = h["Close"].iloc[-1]
                    prev = h["Close"].iloc[-2]
                    chg = ((p - prev) / prev) * 100
                    col = "#00e676" if chg >= 0 else "#ff5252"
                    arrow = "▲" if chg >= 0 else "▼"

                    if p > 1:
                        fmt = f"{p:,.2f}"
                    else:
                        fmt = f"{p:,.4f}"

                    if "XU100" in symbol or "^" in symbol:
                        fmt = f"{p:,.0f}"

                    return (
                        f'{label if label else symbol}: '
                        f'<span style="color:white">{fmt}</span> '
                        f'<span style="color:{col}">{arrow}%{chg:.2f}</span>'
                    )
            except Exception:
                return ""
            return ""

        # Piyasa
        for name, sym in market_symbols:
            val = get_val(sym, name)
            if val:
                market_html += f"{val} &nbsp;|&nbsp; "

            if name == "ETH/USDT":
                # Gram Altın
                try:
                    ons = (
                        yahoo_data.tickers["GC=F"]
                        .history(period="1d")["Close"]
                        .iloc[-1]
                    )
                    market_html += (
                        f'Gr Altın: <span style="color:white">'
                        f"{(ons * usd_try) / 31.1035:.2f}</span> &nbsp;|&nbsp; "
                    )
                except Exception:
                    pass
                # Gram Gümüş
                try:
                    ons = (
                        yahoo_data.tickers["SI=F"]
                        .history(period="1d")["Close"]
                        .iloc[-1]
                    )
                    market_html += (
                        f'Gr Gümüş: <span style="color:white">'
                        f"{(ons * usd_try) / 31.1035:.2f}</span> &nbsp;|&nbsp; "
                    )
                except Exception:
                    pass

        # Kripto global
        if total_cap > 0:
            market_html += (
                f'BTC.D: <span style="color:#f2a900">% {btc_d:.2f}</span> &nbsp;|&nbsp; '
                f'TOTAL: <span style="color:#00e676">${(total_cap/1e12):.2f}T</span> &nbsp;|&nbsp; '
                f'TOTAL 3: <span style="color:#627eea">${(total_3/1e9):.0f}B</span> &nbsp;|&nbsp; '
                f'OTHERS.D: <span style="color:#627eea">% {others_d:.2f}</span> &nbsp;|&nbsp; '
            )

        # Portföy
        if portfolio_symbols:
            for name, sym in portfolio_symbols.items():
                val = get_val(sym, name)
                if val:
                    portfolio_html += f"{val} &nbsp;&nbsp;&nbsp; "
        else:
            portfolio_html += "Portföy boş veya veri çekilemiyor."
    except Exception:
        market_html, portfolio_html = "Yükleniyor...", "Yükleniyor..."

    return (
        f'<div class="ticker-text animate-market">{market_html} &nbsp;&nbsp;&nbsp; {market_html}</div>',
        f'<div class="ticker-text animate-portfolio">{portfolio_html} &nbsp;&nbsp;&nbsp; {portfolio_html}</div>',
    )


# --- BINANCE VADELİ ---
def get_binance_pnl_stats(exchange):
    try:
        income = exchange.fetch_income(params={"limit": 1000})
        now = datetime.now().timestamp() * 1000

        day_ms = 86400000
        week_ms = 604800000
        month_ms = 2592000000

        pnl_day = pnl_week = pnl_month = pnl_total = 0

        for inc in income:
            amount = float(inc["income"])
            ts = inc["timestamp"]
            if inc["incomeType"] in ["REALIZED_PNL", "COMMISSION", "FUNDING_FEE"]:
                pnl_total += amount
                if now - ts <= day_ms:
                    pnl_day += amount
                if now - ts <= week_ms:
                    pnl_week += amount
                if now - ts <= month_ms:
                    pnl_month += amount

        return pnl_day, pnl_week, pnl_month, pnl_total
    except Exception:
        return 0, 0, 0, 0


def get_binance_positions(api_key, api_secret):
    try:
        exchange = ccxt.binance(
            {
                "apiKey": api_key,
                "secret": api_secret,
                "options": {"defaultType": "future"},
            }
        )

        balance = exchange.fetch_balance()
        total_wallet = balance["total"]["USDT"]
        total_unrealized = balance["info"]["totalUnrealizedProfit"]
        total_equity = float(balance["info"]["totalMarginBalance"])

        p_day, p_week, p_month, p_total = get_binance_pnl_stats(exchange)

        positions = exchange.fetch_positions()
        active_positions = []

        for pos in positions:
            if float(pos["info"]["positionAmt"]) != 0:
                side = "🟢 LONG" if float(pos["info"]["positionAmt"]) > 0 else "🔴 SHORT"
                active_positions.append(
                    {
                        "Sembol": pos["symbol"],
                        "Yön": side,
                        "Lev": f"{pos['leverage']}x",
                        "Giriş": float(pos["entryPrice"]),
                        "Mark": float(pos["markPrice"]),
                        "PNL": float(pos["unrealizedPnl"]),
                        "ROE %": round(float(pos["percentage"]), 2),
                    }
                )

        stats = {
            "wallet": total_wallet,
            "equity": total_equity,
            "unrealized": float(total_unrealized),
            "pnl_day": p_day,
            "pnl_week": p_week,
            "pnl_month": p_month,
        }

        return stats, pd.DataFrame(active_positions)
    except Exception as e:
        return None, str(e)
