"""
Setup script for profile system using EXISTING Google Sheets
Verifies and uses: sheet1 (MERT), annem, berguzar, total
"""

import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials

def verify_existing_sheets():
    """
    Verify that all required sheets exist in Google Sheets.
    Required sheets: sheet1 (ana sayfa), annem, berguzar, total
    """
    try:
        # Connect to Google Sheets
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
        client = gspread.authorize(creds)
        
        # Open the main spreadsheet
        spreadsheet = client.open("PortfoyData")
        
        print("=" * 70)
        print("📊 MEVCUT SHEETS DOĞRULAMA")
        print("=" * 70)
        print(f"\n🔗 Spreadsheet: {spreadsheet.title}")
        print(f"📁 URL: {spreadsheet.url}\n")
        
        # Get all existing worksheets
        all_sheets = spreadsheet.worksheets()
        sheet_names = [ws.title.lower() for ws in all_sheets]
        
        print("📋 Mevcut tüm sheets:")
        for ws in all_sheets:
            row_count = ws.row_count
            col_count = ws.col_count
            print(f"   • {ws.title} ({row_count} satır, {col_count} sütun)")
        
        print("\n" + "=" * 70)
        print("🔍 PROFİL SHEETS KONTROLÜ")
        print("=" * 70)
        
        required_sheets = {
            "Ana Profil (MERT)": "sheet1",  # veya "ana sayfa"
            "Annem Profili": "annem",
            "Bergüzar Profili": "berguzar",
            "Total Profili": "total"
        }
        
        all_found = True
        for profile_name, sheet_name in required_sheets.items():
            # sheet1 için özel kontrol (ana sayfa olabilir)
            if sheet_name == "sheet1":
                # sheet1 her zaman vardır (spreadsheet.sheet1)
                try:
                    ws = spreadsheet.sheet1
                    print(f"✅ {profile_name}: '{ws.title}' (ana sayfa)")
                except:
                    print(f"❌ {profile_name}: Ana sayfa bulunamadı!")
                    all_found = False
            else:
                if sheet_name in sheet_names:
                    ws = spreadsheet.worksheet(sheet_name)
                    print(f"✅ {profile_name}: '{sheet_name}' sheet'i mevcut")
                else:
                    print(f"❌ {profile_name}: '{sheet_name}' sheet'i BULUNAMADI!")
                    all_found = False
        
        print("\n" + "=" * 70)
        
        if all_found:
            print("✅ TÜM PROFİL SHEETS MEVCUT!")
            print("=" * 70)
            print("\n🎉 Sistem kullanıma hazır!")
            print("\nArtık şunları yapabilirsiniz:")
            print("1. streamlit run portfoy.py")
            print("2. Profil seçiciyi kullanarak geçiş yapın")
            print("3. Her profile ayrı varlıklar ekleyin\n")
            return True
        else:
            print("⚠️ EKSIK SHEETS VAR!")
            print("=" * 70)
            print("\nEksik sheet'leri oluşturmak ister misiniz? (y/n): ")
            return False
            
    except Exception as e:
        print(f"\n❌ HATA: {str(e)}")
        print("\nLütfen şunları kontrol edin:")
        print("1. Google Sheets API bağlantısı aktif mi?")
        print("2. st.secrets içinde 'gcp_service_account' tanımlı mı?")
        print("3. Service account'un 'PortfoyData' spreadsheet'ine erişimi var mı?")
        return False


def create_missing_sheets():
    """
    Create any missing profile sheets.
    """
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
        client = gspread.authorize(creds)
        
        spreadsheet = client.open("PortfoyData")
        existing_sheets = {ws.title.lower(): ws for ws in spreadsheet.worksheets()}
        
        print("\n📝 Eksik sheet'ler oluşturuluyor...\n")
        
        required_sheets = ["annem", "berguzar", "total"]
        headers = ["Kod", "Pazar", "Adet", "Maliyet", "Tip", "Notlar"]
        
        created = 0
        for sheet_name in required_sheets:
            if sheet_name not in existing_sheets:
                try:
                    new_sheet = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=20)
                    new_sheet.append_row(headers)
                    print(f"✅ '{sheet_name}' sheet'i oluşturuldu")
                    created += 1
                except Exception as e:
                    print(f"❌ '{sheet_name}' oluşturulamadı: {str(e)}")
            else:
                print(f"ℹ️  '{sheet_name}' zaten mevcut")
        
        if created > 0:
            print(f"\n✅ {created} yeni sheet oluşturuldu!")
        else:
            print("\nℹ️  Tüm sheet'ler zaten mevcut.")
        
        return True
        
    except Exception as e:
        print(f"\n❌ HATA: {str(e)}")
        return False


def create_history_sheets():
    """
    Create history sheets for each profile (optional).
    """
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
        client = gspread.authorize(creds)
        
        spreadsheet = client.open("PortfoyData")
        existing_sheets = {ws.title.lower(): ws for ws in spreadsheet.worksheets()}
        
        print("\n📊 Tarihçe sheet'leri oluşturuluyor...\n")
        
        profiles = ["ANNEM", "BERGUZAR"]  # MERT için zaten mevcut olanları kullan
        history_types = ["Satislar", "portfolio_history", "history_bist", "history_abd", 
                        "history_fon", "history_emtia", "history_nakit"]
        
        created = 0
        for profile in profiles:
            for history_type in history_types:
                sheet_name = f"{history_type}_{profile}"
                
                if sheet_name.lower() not in existing_sheets:
                    try:
                        new_sheet = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=20)
                        
                        # Add appropriate headers
                        if history_type == "Satislar":
                            headers = ["Tarih", "Kod", "Pazar", "Satılan Adet", "Satış Fiyatı", "Maliyet", "Kâr/Zarar"]
                        else:
                            headers = ["Tarih", "Değer_TRY", "Değer_USD"]
                        
                        new_sheet.append_row(headers)
                        print(f"   ✅ {sheet_name}")
                        created += 1
                    except Exception as e:
                        print(f"   ❌ {sheet_name}: {str(e)}")
        
        if created > 0:
            print(f"\n✅ {created} tarihçe sheet'i oluşturuldu!")
        else:
            print("\nℹ️  Tüm tarihçe sheet'leri zaten mevcut.")
        
        return True
        
    except Exception as e:
        print(f"\n❌ HATA: {str(e)}")
        return False


if __name__ == "__main__":
    print("=" * 70)
    print("🎯 PORTFOLIO PROFILE SYSTEM - MEVCUT SHEETS KURULUMU")
    print("=" * 70)
    print("\nBu script mevcut Google Sheets yapınızı kullanır:")
    print("  • Ana sayfa (sheet1) → MERT profili")
    print("  • annem → ANNEM profili")
    print("  • berguzar → BERGUZAR profili")
    print("  • total → TOTAL profili (otomatik hesaplanır)\n")
    
    # Step 1: Verify existing sheets
    success = verify_existing_sheets()
    
    if not success:
        response = input("\nEksik sheet'leri oluşturmak ister misiniz? (y/n): ")
        if response.lower() == 'y':
            create_missing_sheets()
            print("\n" + "=" * 70)
            # Verify again
            verify_existing_sheets()
    
    # Step 2: Optional - create history sheets
    print("\n" + "=" * 70)
    response = input("\nTarihçe sheet'lerini oluşturmak ister misiniz? (ANNEM ve BERGUZAR için) (y/n): ")
    if response.lower() == 'y':
        create_history_sheets()
    
    print("\n" + "=" * 70)
    print("🎉 KURULUM TAMAMLANDI!")
    print("=" * 70)
    print("\n✨ Artık uygulamayı başlatabilirsiniz:")
    print("   streamlit run portfoy.py")
    print("\n📖 Kullanım kılavuzu:")
    print("   cat HIZLI_KULLANIM.md")
