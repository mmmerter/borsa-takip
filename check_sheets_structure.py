"""
Google Sheets yapısını kontrol eden ve eksik sheet'leri/kolonları düzenleyen script
"""
import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials

SHEET_NAME = "PortfoyData"
DAILY_BASE_SHEET_NAME = "daily_base_prices"

PROFILE_SHEETS = {
    "ANA PROFİL": "PortfoyData",
    "MERT": "PortfoyData",
    "BERGÜZAR": "PortfoyData_BERGÜZAR",
    "ANNEM": "PortfoyData_ANNEM",
}

def get_client():
    """Google Sheets client'ı döndürür"""
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
        return gspread.authorize(creds)
    except Exception as e:
        print(f"Hata: {e}")
        return None

def check_and_fix_sheets():
    """Tüm sheet'leri kontrol eder ve eksik olanları oluşturur"""
    client = get_client()
    if client is None:
        print("Google Sheets'e bağlanılamadı!")
        return
    
    try:
        spreadsheet = client.open(SHEET_NAME)
        print(f"✓ Spreadsheet '{SHEET_NAME}' bulundu\n")
    except Exception as e:
        print(f"✗ Spreadsheet '{SHEET_NAME}' bulunamadı: {e}")
        return
    
    # 1. Ana portföy sheet'leri kontrol et
    print("=" * 60)
    print("1. PROFİL SHEET'LERİ KONTROLÜ")
    print("=" * 60)
    
    for profile_name, sheet_name in PROFILE_SHEETS.items():
        if sheet_name == SHEET_NAME:
            # Ana sheet için sheet1 kullan
            try:
                sheet = spreadsheet.sheet1
                headers = sheet.row_values(1)
                expected_headers = ["Kod", "Pazar", "Adet", "Maliyet", "Tip", "Notlar"]
                
                if not headers or headers != expected_headers:
                    print(f"⚠ '{profile_name}' (sheet1) - Header'lar eksik/yanlış")
                    print(f"   Mevcut: {headers}")
                    print(f"   Beklenen: {expected_headers}")
                    # Header'ları düzelt
                    if headers:
                        sheet.delete_rows(1)
                    sheet.insert_row(expected_headers, 1)
                    print(f"   ✓ Header'lar düzeltildi")
                else:
                    print(f"✓ '{profile_name}' (sheet1) - OK")
            except Exception as e:
                print(f"✗ '{profile_name}' (sheet1) - Hata: {e}")
        else:
            # Diğer profil sheet'leri
            try:
                sheet = spreadsheet.worksheet(sheet_name)
                headers = sheet.row_values(1)
                expected_headers = ["Kod", "Pazar", "Adet", "Maliyet", "Tip", "Notlar"]
                
                if not headers or headers != expected_headers:
                    print(f"⚠ '{profile_name}' ({sheet_name}) - Header'lar eksik/yanlış")
                    print(f"   Mevcut: {headers}")
                    print(f"   Beklenen: {expected_headers}")
                    if headers:
                        sheet.delete_rows(1)
                    sheet.insert_row(expected_headers, 1)
                    print(f"   ✓ Header'lar düzeltildi")
                else:
                    print(f"✓ '{profile_name}' ({sheet_name}) - OK")
            except Exception:
                # Sheet yoksa oluştur
                print(f"⚠ '{profile_name}' ({sheet_name}) - Sheet bulunamadı, oluşturuluyor...")
                try:
                    sheet = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=10)
                    sheet.append_row(["Kod", "Pazar", "Adet", "Maliyet", "Tip", "Notlar"])
                    print(f"   ✓ Sheet oluşturuldu")
                except Exception as e:
                    print(f"   ✗ Sheet oluşturulamadı: {e}")
    
    # 2. Satışlar sheet'i kontrol et
    print("\n" + "=" * 60)
    print("2. SATIŞLAR SHEET'İ KONTROLÜ")
    print("=" * 60)
    
    try:
        sheet = spreadsheet.worksheet("Satislar")
        headers = sheet.row_values(1)
        expected_headers = ["Tarih", "Kod", "Pazar", "Satılan Adet", "Satış Fiyatı", "Maliyet", "Kâr/Zarar"]
        
        if not headers or headers != expected_headers:
            print(f"⚠ 'Satislar' - Header'lar eksik/yanlış")
            print(f"   Mevcut: {headers}")
            print(f"   Beklenen: {expected_headers}")
            if headers:
                sheet.delete_rows(1)
            sheet.insert_row(expected_headers, 1)
            print(f"   ✓ Header'lar düzeltildi")
        else:
            print(f"✓ 'Satislar' - OK")
    except Exception:
        print(f"⚠ 'Satislar' - Sheet bulunamadı, oluşturuluyor...")
        try:
            sheet = spreadsheet.add_worksheet(title="Satislar", rows=1000, cols=10)
            sheet.append_row(["Tarih", "Kod", "Pazar", "Satılan Adet", "Satış Fiyatı", "Maliyet", "Kâr/Zarar"])
            print(f"   ✓ Sheet oluşturuldu")
        except Exception as e:
            print(f"   ✗ Sheet oluşturulamadı: {e}")
    
    # 3. Portfolio history sheet'i kontrol et
    print("\n" + "=" * 60)
    print("3. PORTFÖY TARİHÇE SHEET'İ KONTROLÜ")
    print("=" * 60)
    
    try:
        sheet = spreadsheet.worksheet("portfolio_history")
        headers = sheet.row_values(1)
        expected_headers = ["Tarih", "Değer_TRY", "Değer_USD"]
        
        if not headers or headers != expected_headers:
            print(f"⚠ 'portfolio_history' - Header'lar eksik/yanlış")
            print(f"   Mevcut: {headers}")
            print(f"   Beklenen: {expected_headers}")
            if headers:
                sheet.delete_rows(1)
            sheet.insert_row(expected_headers, 1)
            print(f"   ✓ Header'lar düzeltildi")
        else:
            print(f"✓ 'portfolio_history' - OK")
    except Exception:
        print(f"⚠ 'portfolio_history' - Sheet bulunamadı, oluşturuluyor...")
        try:
            sheet = spreadsheet.add_worksheet(title="portfolio_history", rows=1000, cols=10)
            sheet.append_row(["Tarih", "Değer_TRY", "Değer_USD"])
            print(f"   ✓ Sheet oluşturuldu")
        except Exception as e:
            print(f"   ✗ Sheet oluşturulamadı: {e}")
    
    # 4. Pazar bazlı history sheet'leri kontrol et
    print("\n" + "=" * 60)
    print("4. PAZAR BAZLI TARİHÇE SHEET'LERİ KONTROLÜ")
    print("=" * 60)
    
    market_sheets = ["history_bist", "history_abd", "history_fon", "history_emtia", "history_nakit"]
    expected_headers = ["Tarih", "Değer_TRY", "Değer_USD"]
    
    for sheet_name in market_sheets:
        try:
            sheet = spreadsheet.worksheet(sheet_name)
            headers = sheet.row_values(1)
            
            if not headers or headers != expected_headers:
                print(f"⚠ '{sheet_name}' - Header'lar eksik/yanlış")
                print(f"   Mevcut: {headers}")
                print(f"   Beklenen: {expected_headers}")
                if headers:
                    sheet.delete_rows(1)
                sheet.insert_row(expected_headers, 1)
                print(f"   ✓ Header'lar düzeltildi")
            else:
                print(f"✓ '{sheet_name}' - OK")
        except Exception:
            print(f"⚠ '{sheet_name}' - Sheet bulunamadı, oluşturuluyor...")
            try:
                sheet = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=10)
                sheet.append_row(expected_headers)
                print(f"   ✓ Sheet oluşturuldu")
            except Exception as e:
                print(f"   ✗ Sheet oluşturulamadı: {e}")
    
    # 5. Günlük baz fiyatlar sheet'i kontrol et
    print("\n" + "=" * 60)
    print("5. GÜNLÜK BAZ FİYATLAR SHEET'İ KONTROLÜ")
    print("=" * 60)
    
    try:
        sheet = spreadsheet.worksheet(DAILY_BASE_SHEET_NAME)
        headers = sheet.row_values(1)
        expected_headers = ["Tarih", "Saat", "Kod", "Fiyat", "PB"]
        
        if not headers or headers != expected_headers:
            print(f"⚠ '{DAILY_BASE_SHEET_NAME}' - Header'lar eksik/yanlış")
            print(f"   Mevcut: {headers}")
            print(f"   Beklenen: {expected_headers}")
            if headers:
                sheet.delete_rows(1)
            sheet.insert_row(expected_headers, 1)
            print(f"   ✓ Header'lar düzeltildi")
        else:
            print(f"✓ '{DAILY_BASE_SHEET_NAME}' - OK")
    except Exception:
        print(f"⚠ '{DAILY_BASE_SHEET_NAME}' - Sheet bulunamadı, oluşturuluyor...")
        try:
            sheet = spreadsheet.add_worksheet(title=DAILY_BASE_SHEET_NAME, rows=1000, cols=10)
            sheet.append_row(["Tarih", "Saat", "Kod", "Fiyat", "PB"])
            print(f"   ✓ Sheet oluşturuldu")
        except Exception as e:
            print(f"   ✗ Sheet oluşturulamadı: {e}")
    
    print("\n" + "=" * 60)
    print("KONTROL TAMAMLANDI!")
    print("=" * 60)

if __name__ == "__main__":
    # Streamlit secrets kullanarak çalıştır
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--check":
        # Streamlit olmadan çalıştırma için secrets'ı manuel yükle
        import json
        try:
            with open(".streamlit/secrets.toml", "r") as f:
                # TOML parse etmek yerine direkt secrets kullan
                pass
        except:
            pass
        
        # Streamlit context olmadan çalıştırma
        print("Streamlit context gerekiyor. Lütfen streamlit run ile çalıştırın.")
    else:
        check_and_fix_sheets()
