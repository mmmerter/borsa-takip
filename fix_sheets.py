"""
Google Sheets yapısını kontrol eden ve düzenleyen script
Streamlit context olmadan çalışabilir
"""
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import os

SHEET_NAME = "PortfoyData"
DAILY_BASE_SHEET_NAME = "daily_base_prices"

PROFILE_SHEETS = {
    "ANA PROFİL": "PortfoyData",  # sheet1 kullanılacak
    "MERT": "PortfoyData",  # sheet1 kullanılacak
    "BERGÜZAR": "PortfoyData_BERGÜZAR",
    "ANNEM": "PortfoyData_ANNEM",
}

def get_client_from_secrets():
    """Secrets dosyasından client oluşturur"""
    try:
        # Streamlit secrets dosyasını oku
        secrets_path = ".streamlit/secrets.toml"
        if not os.path.exists(secrets_path):
            print(f"⚠ Secrets dosyası bulunamadı: {secrets_path}")
            print("Lütfen .streamlit/secrets.toml dosyasını kontrol edin.")
            return None
        
        # TOML parse et (basit bir parser)
        with open(secrets_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # gcp_service_account bölümünü bul
        if "gcp_service_account" not in content:
            print("⚠ secrets.toml'da gcp_service_account bulunamadı")
            return None
        
        # JSON kısmını çıkar (basit parsing)
        start = content.find("{", content.find("gcp_service_account"))
        if start == -1:
            print("⚠ gcp_service_account JSON formatı bulunamadı")
            return None
        
        # JSON'u bul
        brace_count = 0
        end = start
        for i in range(start, len(content)):
            if content[i] == '{':
                brace_count += 1
            elif content[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    end = i + 1
                    break
        
        json_str = content[start:end]
        # TOML'daki çok satırlı string formatını düzelt
        json_str = json_str.replace('"""', '"').replace("'''", "'")
        
        try:
            creds_dict = json.loads(json_str)
        except:
            # Alternatif: direkt JSON dosyası olabilir
            json_path = ".streamlit/gcp_service_account.json"
            if os.path.exists(json_path):
                with open(json_path, "r") as f:
                    creds_dict = json.load(f)
            else:
                print("⚠ JSON parse edilemedi")
                return None
        
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        return gspread.authorize(creds)
    except Exception as e:
        print(f"✗ Client oluşturulamadı: {e}")
        return None

def check_and_fix_sheets():
    """Tüm sheet'leri kontrol eder ve eksik olanları oluşturur"""
    client = get_client_from_secrets()
    if client is None:
        print("\n⚠ Google Sheets'e bağlanılamadı!")
        print("Lütfen .streamlit/secrets.toml dosyasını kontrol edin.\n")
        return False
    
    try:
        spreadsheet = client.open(SHEET_NAME)
        print(f"✓ Spreadsheet '{SHEET_NAME}' bulundu\n")
    except Exception as e:
        print(f"✗ Spreadsheet '{SHEET_NAME}' bulunamadı: {e}")
        return False
    
    all_ok = True
    
    # 1. Ana portföy sheet'leri kontrol et
    print("=" * 70)
    print("1. PROFİL SHEET'LERİ KONTROLÜ")
    print("=" * 70)
    
    for profile_name, sheet_name in PROFILE_SHEETS.items():
        if sheet_name == SHEET_NAME:
            # Ana sheet için sheet1 kullan
            try:
                sheet = spreadsheet.sheet1
                headers = sheet.row_values(1)
                expected_headers = ["Kod", "Pazar", "Adet", "Maliyet", "Tip", "Notlar"]
                
                if not headers or headers != expected_headers:
                    print(f"⚠ '{profile_name}' (sheet1) - Header'lar düzeltiliyor...")
                    print(f"   Mevcut: {headers if headers else '(boş)'}")
                    print(f"   Beklenen: {expected_headers}")
                    if headers:
                        sheet.delete_rows(1)
                    sheet.insert_row(expected_headers, 1)
                    print(f"   ✓ Header'lar düzeltildi\n")
                    all_ok = False
                else:
                    print(f"✓ '{profile_name}' (sheet1) - OK\n")
            except Exception as e:
                print(f"✗ '{profile_name}' (sheet1) - Hata: {e}\n")
                all_ok = False
        else:
            # Diğer profil sheet'leri
            try:
                sheet = spreadsheet.worksheet(sheet_name)
                headers = sheet.row_values(1)
                expected_headers = ["Kod", "Pazar", "Adet", "Maliyet", "Tip", "Notlar"]
                
                if not headers or headers != expected_headers:
                    print(f"⚠ '{profile_name}' ({sheet_name}) - Header'lar düzeltiliyor...")
                    print(f"   Mevcut: {headers if headers else '(boş)'}")
                    print(f"   Beklenen: {expected_headers}")
                    if headers:
                        sheet.delete_rows(1)
                    sheet.insert_row(expected_headers, 1)
                    print(f"   ✓ Header'lar düzeltildi\n")
                    all_ok = False
                else:
                    print(f"✓ '{profile_name}' ({sheet_name}) - OK\n")
            except Exception:
                # Sheet yoksa oluştur
                print(f"⚠ '{profile_name}' ({sheet_name}) - Sheet bulunamadı, oluşturuluyor...")
                try:
                    sheet = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=10)
                    sheet.append_row(["Kod", "Pazar", "Adet", "Maliyet", "Tip", "Notlar"])
                    print(f"   ✓ Sheet oluşturuldu ve header'lar eklendi\n")
                    all_ok = False
                except Exception as e:
                    print(f"   ✗ Sheet oluşturulamadı: {e}\n")
                    all_ok = False
    
    # 2. Satışlar sheet'i kontrol et
    print("=" * 70)
    print("2. SATIŞLAR SHEET'İ KONTROLÜ")
    print("=" * 70)
    
    try:
        sheet = spreadsheet.worksheet("Satislar")
        headers = sheet.row_values(1)
        expected_headers = ["Tarih", "Kod", "Pazar", "Satılan Adet", "Satış Fiyatı", "Maliyet", "Kâr/Zarar"]
        
        if not headers or headers != expected_headers:
            print(f"⚠ 'Satislar' - Header'lar düzeltiliyor...")
            print(f"   Mevcut: {headers if headers else '(boş)'}")
            print(f"   Beklenen: {expected_headers}")
            if headers:
                sheet.delete_rows(1)
            sheet.insert_row(expected_headers, 1)
            print(f"   ✓ Header'lar düzeltildi\n")
            all_ok = False
        else:
            print(f"✓ 'Satislar' - OK\n")
    except Exception:
        print(f"⚠ 'Satislar' - Sheet bulunamadı, oluşturuluyor...")
        try:
            sheet = spreadsheet.add_worksheet(title="Satislar", rows=1000, cols=10)
            sheet.append_row(["Tarih", "Kod", "Pazar", "Satılan Adet", "Satış Fiyatı", "Maliyet", "Kâr/Zarar"])
            print(f"   ✓ Sheet oluşturuldu ve header'lar eklendi\n")
            all_ok = False
        except Exception as e:
            print(f"   ✗ Sheet oluşturulamadı: {e}\n")
            all_ok = False
    
    # 3. Portfolio history sheet'i kontrol et
    print("=" * 70)
    print("3. PORTFÖY TARİHÇE SHEET'İ KONTROLÜ")
    print("=" * 70)
    
    try:
        sheet = spreadsheet.worksheet("portfolio_history")
        headers = sheet.row_values(1)
        expected_headers = ["Tarih", "Değer_TRY", "Değer_USD"]
        
        if not headers or headers != expected_headers:
            print(f"⚠ 'portfolio_history' - Header'lar düzeltiliyor...")
            print(f"   Mevcut: {headers if headers else '(boş)'}")
            print(f"   Beklenen: {expected_headers}")
            if headers:
                sheet.delete_rows(1)
            sheet.insert_row(expected_headers, 1)
            print(f"   ✓ Header'lar düzeltildi\n")
            all_ok = False
        else:
            print(f"✓ 'portfolio_history' - OK\n")
    except Exception:
        print(f"⚠ 'portfolio_history' - Sheet bulunamadı, oluşturuluyor...")
        try:
            sheet = spreadsheet.add_worksheet(title="portfolio_history", rows=1000, cols=10)
            sheet.append_row(["Tarih", "Değer_TRY", "Değer_USD"])
            print(f"   ✓ Sheet oluşturuldu ve header'lar eklendi\n")
            all_ok = False
        except Exception as e:
            print(f"   ✗ Sheet oluşturulamadı: {e}\n")
            all_ok = False
    
    # 4. Pazar bazlı history sheet'leri kontrol et
    print("=" * 70)
    print("4. PAZAR BAZLI TARİHÇE SHEET'LERİ KONTROLÜ")
    print("=" * 70)
    
    market_sheets = ["history_bist", "history_abd", "history_fon", "history_emtia", "history_nakit"]
    expected_headers = ["Tarih", "Değer_TRY", "Değer_USD"]
    
    for sheet_name in market_sheets:
        try:
            sheet = spreadsheet.worksheet(sheet_name)
            headers = sheet.row_values(1)
            
            if not headers or headers != expected_headers:
                print(f"⚠ '{sheet_name}' - Header'lar düzeltiliyor...")
                print(f"   Mevcut: {headers if headers else '(boş)'}")
                print(f"   Beklenen: {expected_headers}")
                if headers:
                    sheet.delete_rows(1)
                sheet.insert_row(expected_headers, 1)
                print(f"   ✓ Header'lar düzeltildi\n")
                all_ok = False
            else:
                print(f"✓ '{sheet_name}' - OK\n")
        except Exception:
            print(f"⚠ '{sheet_name}' - Sheet bulunamadı, oluşturuluyor...")
            try:
                sheet = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=10)
                sheet.append_row(expected_headers)
                print(f"   ✓ Sheet oluşturuldu ve header'lar eklendi\n")
                all_ok = False
            except Exception as e:
                print(f"   ✗ Sheet oluşturulamadı: {e}\n")
                all_ok = False
    
    # 5. Günlük baz fiyatlar sheet'i kontrol et
    print("=" * 70)
    print("5. GÜNLÜK BAZ FİYATLAR SHEET'İ KONTROLÜ")
    print("=" * 70)
    
    try:
        sheet = spreadsheet.worksheet(DAILY_BASE_SHEET_NAME)
        headers = sheet.row_values(1)
        expected_headers = ["Tarih", "Saat", "Kod", "Fiyat", "PB"]
        
        if not headers or headers != expected_headers:
            print(f"⚠ '{DAILY_BASE_SHEET_NAME}' - Header'lar düzeltiliyor...")
            print(f"   Mevcut: {headers if headers else '(boş)'}")
            print(f"   Beklenen: {expected_headers}")
            if headers:
                sheet.delete_rows(1)
            sheet.insert_row(expected_headers, 1)
            print(f"   ✓ Header'lar düzeltildi\n")
            all_ok = False
        else:
            print(f"✓ '{DAILY_BASE_SHEET_NAME}' - OK\n")
    except Exception:
        print(f"⚠ '{DAILY_BASE_SHEET_NAME}' - Sheet bulunamadı, oluşturuluyor...")
        try:
            sheet = spreadsheet.add_worksheet(title=DAILY_BASE_SHEET_NAME, rows=1000, cols=10)
            sheet.append_row(["Tarih", "Saat", "Kod", "Fiyat", "PB"])
            print(f"   ✓ Sheet oluşturuldu ve header'lar eklendi\n")
            all_ok = False
        except Exception as e:
            print(f"   ✗ Sheet oluşturulamadı: {e}\n")
            all_ok = False
    
    print("=" * 70)
    if all_ok:
        print("✅ TÜM SHEET'LER VE KOLONLAR DOĞRU!")
    else:
        print("✅ DÜZENLEMELER TAMAMLANDI!")
    print("=" * 70)
    
    return True

if __name__ == "__main__":
    check_and_fix_sheets()
