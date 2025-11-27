"""
Portföy Kâr/Zarar Teşhis Aracı
==============================

Bu script portföyünüzdeki her varlığın:
- Maliyetini
- Güncel fiyatını
- Kâr/Zarar durumunu
- Fiyat kaynağını

detaylı şekilde gösterir ve toplam hesaplamayı doğrular.
"""

import pandas as pd
import streamlit as st
from data_loader import get_data_from_sheet, get_usd_try, get_tickers_data, get_tefas_data
from utils import get_yahoo_symbol
import yfinance as yf

def diagnose_portfolio():
    """Portföy kâr/zarar hesaplamasını detaylı şekilde analiz eder."""
    
    st.title("🔍 Portföy Kâr/Zarar Teşhis Aracı")
    
    # Veri çek
    portfoy_df = get_data_from_sheet()
    usd_try_rate = get_usd_try()
    
    if portfoy_df.empty:
        st.error("❌ Portföy verisi bulunamadı!")
        return
    
    st.success(f"✅ {len(portfoy_df)} varlık bulundu")
    st.info(f"💱 USD/TRY Kuru: {usd_try_rate:.4f}")
    
    # Sadece portföy tipindeki varlıkları al
    portfoy_only = portfoy_df[portfoy_df["Tip"] == "Spot"].copy()
    
    st.markdown("---")
    st.header("📊 Varlık Detayları")
    
    # Her varlık için detaylı analiz
    diagnostics = []
    
    for idx, row in portfoy_only.iterrows():
        kod = row["Kod"]
        pazar = row["Pazar"]
        adet = float(row.get("Adet", 0))
        maliyet = float(row.get("Maliyet", 0))
        
        if adet == 0:
            continue
        
        # Para birimi belirle
        pazar_upper = pazar.upper()
        kod_upper = kod.upper()
        
        if "BIST" in pazar_upper or "TL" in kod_upper or "FON" in pazar_upper or "EMTIA" in pazar_upper or "NAKIT" in pazar_upper:
            asset_currency = "TRY"
        else:
            asset_currency = "USD"
        
        # Fiyat çek
        curr_price = 0
        price_source = "Bilinmiyor"
        
        try:
            if "NAKIT" in pazar_upper:
                if kod == "TL":
                    curr_price = 1
                    price_source = "Sabit (TL)"
                elif kod == "USD":
                    curr_price = usd_try_rate
                    price_source = "TCMB (USD/TRY)"
                else:
                    curr_price = 1
                    price_source = f"Varsayılan ({kod})"
            
            elif "FON" in pazar:
                curr_price, _ = get_tefas_data(kod)
                price_source = "TEFAS"
                if curr_price == 0:
                    curr_price = maliyet
                    price_source = "TEFAS (Hata - Maliyet kullanıldı)"
            
            elif "Gram Altın" in kod or "GRAM ALTIN" in kod:
                try:
                    ticker = yf.Ticker("GC=F")
                    h = ticker.history(period="5d")
                    if not h.empty:
                        ons_price = h["Close"].iloc[-1]
                        curr_price = (ons_price * usd_try_rate) / 31.1035
                        price_source = "Yahoo Finance (Altın Ons -> Gram)"
                    else:
                        curr_price = 0
                        price_source = "Yahoo Finance (Veri yok)"
                except Exception as e:
                    curr_price = 0
                    price_source = f"Hata: {str(e)}"
            
            elif "Gram Gümüş" in kod or "GRAM GÜMÜŞ" in kod:
                try:
                    ticker = yf.Ticker("SI=F")
                    h = ticker.history(period="5d")
                    if not h.empty:
                        ons_price = h["Close"].iloc[-1]
                        curr_price = (ons_price * usd_try_rate) / 31.1035
                        price_source = "Yahoo Finance (Gümüş Ons -> Gram)"
                    else:
                        curr_price = 0
                        price_source = "Yahoo Finance (Veri yok)"
                except Exception as e:
                    curr_price = 0
                    price_source = f"Hata: {str(e)}"
            
            else:
                # Yahoo Finance'tan çek
                symbol = get_yahoo_symbol(kod, pazar)
                try:
                    ticker = yf.Ticker(symbol)
                    h = ticker.history(period="5d")
                    if not h.empty:
                        curr_price = h["Close"].iloc[-1]
                        price_source = f"Yahoo Finance ({symbol})"
                    else:
                        curr_price = 0
                        price_source = f"Yahoo Finance (Veri yok - {symbol})"
                except Exception as e:
                    curr_price = 0
                    price_source = f"Hata: {str(e)}"
        
        except Exception as e:
            curr_price = 0
            price_source = f"Genel Hata: {str(e)}"
        
        # Hesaplamalar (TRY bazında)
        if asset_currency == "TRY":
            maliyet_try = maliyet * adet
            deger_try = curr_price * adet
        else:  # USD
            maliyet_try = maliyet * adet * usd_try_rate
            deger_try = curr_price * adet * usd_try_rate
        
        kar_zarar_try = deger_try - maliyet_try
        kar_zarar_pct = (kar_zarar_try / maliyet_try * 100) if maliyet_try > 0 else 0
        
        diagnostics.append({
            "Kod": kod,
            "Pazar": pazar,
            "Para Birimi": asset_currency,
            "Adet": adet,
            "Maliyet (Birim)": maliyet,
            "Güncel Fiyat": curr_price,
            "Fiyat Kaynağı": price_source,
            "Toplam Maliyet (TRY)": maliyet_try,
            "Toplam Değer (TRY)": deger_try,
            "K/Z (TRY)": kar_zarar_try,
            "K/Z (%)": kar_zarar_pct,
        })
    
    # DataFrame oluştur
    diag_df = pd.DataFrame(diagnostics)
    
    # Toplam hesapla
    total_maliyet = diag_df["Toplam Maliyet (TRY)"].sum()
    total_deger = diag_df["Toplam Değer (TRY)"].sum()
    total_kz = diag_df["K/Z (TRY)"].sum()
    total_kz_pct = (total_kz / total_maliyet * 100) if total_maliyet > 0 else 0
    
    # Özet göster
    st.markdown("---")
    st.header("📈 Genel Özet")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Toplam Maliyet", f"₺{total_maliyet:,.2f}")
    col2.metric("Toplam Değer", f"₺{total_deger:,.2f}")
    col3.metric("Toplam K/Z", f"₺{total_kz:,.2f}", delta=f"{total_kz_pct:.2f}%")
    col4.metric("Varlık Sayısı", len(diag_df))
    
    # Sorunlu varlıkları vurgula
    st.markdown("---")
    st.header("🔴 Zarardaki Varlıklar")
    
    losers = diag_df[diag_df["K/Z (TRY)"] < 0].sort_values("K/Z (TRY)")
    
    if not losers.empty:
        st.warning(f"⚠️ {len(losers)} varlık zararda")
        st.dataframe(losers, use_container_width=True, hide_index=True)
        
        # Toplam zarar
        total_loss = losers["K/Z (TRY)"].sum()
        st.error(f"💸 Toplam Zarar: ₺{abs(total_loss):,.2f}")
    else:
        st.success("✅ Hiçbir varlık zararda değil!")
    
    st.markdown("---")
    st.header("🟢 Kârdaki Varlıklar")
    
    winners = diag_df[diag_df["K/Z (TRY)"] > 0].sort_values("K/Z (TRY)", ascending=False)
    
    if not winners.empty:
        st.success(f"✅ {len(winners)} varlık kârda")
        st.dataframe(winners, use_container_width=True, hide_index=True)
        
        # Toplam kâr
        total_profit = winners["K/Z (TRY)"].sum()
        st.success(f"💰 Toplam Kâr: ₺{total_profit:,.2f}")
    else:
        st.warning("⚠️ Hiçbir varlık kârda değil!")
    
    st.markdown("---")
    st.header("📋 Tüm Varlıklar (Detaylı)")
    st.dataframe(diag_df, use_container_width=True, hide_index=True)
    
    # Fiyat çekme sorunları
    st.markdown("---")
    st.header("⚠️ Fiyat Çekme Sorunları")
    
    price_issues = diag_df[
        (diag_df["Güncel Fiyat"] == 0) | 
        (diag_df["Fiyat Kaynağı"].str.contains("Hata|Veri yok", case=False, na=False))
    ]
    
    if not price_issues.empty:
        st.error(f"❌ {len(price_issues)} varlıkta fiyat çekme sorunu var!")
        st.dataframe(price_issues[["Kod", "Pazar", "Güncel Fiyat", "Fiyat Kaynağı"]], use_container_width=True, hide_index=True)
        st.warning("👆 Bu varlıkların fiyatları doğru çekilemiyor. Lütfen kontrol edin!")
    else:
        st.success("✅ Tüm varlıkların fiyatları başarıyla çekildi!")
    
    # Öneriler
    st.markdown("---")
    st.header("💡 Öneriler")
    
    if total_kz < 0:
        st.warning(f"""
        ### Portföyünüz ₺{abs(total_kz):,.2f} zararda görünüyor.
        
        **Olası Nedenler:**
        1. **Fiyat Çekme Hatası**: Yukarıdaki "Fiyat Çekme Sorunları" bölümünü kontrol edin
        2. **Yanlış Maliyet Girişi**: Google Sheets'teki "Maliyet" kolonundaki değerleri kontrol edin
        3. **Para Birimi Karışıklığı**: TRY/USD karışıklığı olabilir
        4. **Piyasa Düşüşü**: Gerçekten piyasa düşmüş olabilir (özellikle BIST ve kripto)
        
        **Yapmanız Gerekenler:**
        - Zarardaki varlıkların maliyetlerini Google Sheets'te kontrol edin
        - Fiyatların doğru çekildiğini doğrulayın
        - Yahoo Finance'ta manuel olarak sembol isimlerini kontrol edin
        """)
    else:
        st.success(f"""
        ### 🎉 Tebrikler! Portföyünüz ₺{total_kz:,.2f} kârda!
        
        Hesaplamalar doğru görünüyor.
        """)

if __name__ == "__main__":
    diagnose_portfolio()
