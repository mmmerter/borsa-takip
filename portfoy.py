def run_analysis(df, usd_try_rate, view_currency):
    results = []
    if df.empty:
        return pd.DataFrame(columns=ANALYSIS_COLS)

    for i, row in df.iterrows():
        kod = row.get("Kod", "")
        pazar = row.get("Pazar", "")

        # Veriyi çekerken smart_parse ile temizle
        adet = smart_parse(row.get("Adet", 0))
        maliyet = smart_parse(row.get("Maliyet", 0))

        if not kod:
            continue

        symbol = get_yahoo_symbol(kod, pazar)
        asset_currency = "USD"
        if "BIST" in str(pazar) or "TL" in str(kod) or "Fiziki" in str(pazar) or pazar == "FON":
            asset_currency = "TRY"

        curr_price = 0
        prev_close = 0

        try:
            if pazar == "FON":
                curr_price, prev_close = get_tefas_data(kod)

            elif "Gram Altın (TL)" in kod:
                hist = yf.Ticker("GC=F").history(period="2d")
                if len(hist) > 1:
                    curr_price = (hist["Close"].iloc[-1] * usd_try_rate) / 31.1035
                    prev_close = (hist["Close"].iloc[-2] * usd_try_rate) / 31.1035
                else:
                    curr_price = maliyet
                    prev_close = maliyet

            elif "Fiziki" in pazar:
                curr_price = maliyet
                prev_close = maliyet

            else:
                hist = yf.Ticker(symbol).history(period="2d")
                if not hist.empty:
                    curr_price = hist["Close"].iloc[-1]
                    prev_close = hist["Close"].iloc[0]
                else:
                    curr_price = maliyet
                    prev_close = maliyet

        except:
            curr_price = maliyet
            prev_close = maliyet

        # 🔥 BURASI ÖNEMLİ: BIST için 3026 gibi sapık maliyetleri düzelt
        if "BIST" in str(pazar):
            # örn: maliyet 3026, fiyat 30–40 TL civarıysa → 100'e böl
            if maliyet >= 1000 and curr_price > 0 and curr_price < 100 and maliyet > curr_price * 10:
                maliyet = maliyet / 100.0

        # Bundan sonrası aynı
        val_native = curr_price * adet
        cost_native = maliyet * adet
        daily_chg_native = (curr_price - prev_close) * adet

        if view_currency == "TRY":
            if asset_currency == "USD":
                fiyat_goster = curr_price * usd_try_rate
                val_goster = val_native * usd_try_rate
                cost_goster = cost_native * usd_try_rate
                daily_chg = daily_chg_native * usd_try_rate
            else:
                fiyat_goster = curr_price
                val_goster = val_native
                cost_goster = cost_native
                daily_chg = daily_chg_native

        elif view_currency == "USD":
            if asset_currency == "TRY":
                fiyat_goster = curr_price / usd_try_rate
                val_goster = val_native / usd_try_rate
                cost_goster = cost_native / usd_try_rate
                daily_chg = daily_chg_native / usd_try_rate
            else:
                fiyat_goster = curr_price
                val_goster = val_native
                cost_goster = cost_native
                daily_chg = daily_chg_native

        pnl = val_goster - cost_goster
        pnl_pct = (pnl / cost_goster * 100) if cost_goster > 0 else 0

        results.append(
            {
                "Kod": kod,
                "Pazar": pazar,
                "Tip": row.get("Tip", ""),
                "Adet": adet,
                "Maliyet": maliyet,
                "Fiyat": fiyat_goster,
                "PB": view_currency,
                "Değer": val_goster,
                "Top. Kâr/Zarar": pnl,
                "Top. %": pnl_pct,
                "Gün. Kâr/Zarar": daily_chg,
                "Notlar": row.get("Notlar", ""),
            }
        )

    return pd.DataFrame(results)
