"""
Setup script for profile system
Creates necessary worksheets in Google Sheets for each profile
Run this once to initialize the profile structure
"""

import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from profile_manager import get_individual_profiles, SHEET_NAMES, get_sheet_name_for_profile

def setup_profile_sheets():
    """
    Create all necessary worksheets for each profile in Google Sheets.
    This should be run once to set up the profile structure.
    """
    try:
        # Connect to Google Sheets
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
        client = gspread.authorize(creds)
        
        # Open the main spreadsheet
        spreadsheet = client.open("PortfoyData")
        
        print("📊 Profile sistem kurulumu başlatılıyor...")
        print(f"🔗 Spreadsheet: {spreadsheet.title}")
        print(f"📁 URL: {spreadsheet.url}\n")
        
        # Get existing worksheets
        existing_sheets = {ws.title for ws in spreadsheet.worksheets()}
        
        profiles = get_individual_profiles()
        sheet_types = list(SHEET_NAMES.keys())
        
        created_count = 0
        skipped_count = 0
        
        for profile_name in profiles:
            print(f"\n🎯 Profil: {profile_name}")
            
            for sheet_type in sheet_types:
                sheet_name = get_sheet_name_for_profile(sheet_type, profile_name)
                
                if sheet_name in existing_sheets:
                    print(f"   ✓ {sheet_name} (zaten mevcut)")
                    skipped_count += 1
                    continue
                
                try:
                    # Create new worksheet
                    new_sheet = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=20)
                    
                    # Add headers based on sheet type
                    if sheet_type == "main":
                        headers = ["Kod", "Pazar", "Adet", "Maliyet", "Tip", "Notlar"]
                    elif sheet_type == "sales":
                        headers = ["Tarih", "Kod", "Pazar", "Satılan Adet", "Satış Fiyatı", "Maliyet", "Kâr/Zarar"]
                    elif sheet_type in ["portfolio_history", "history_bist", "history_abd", "history_fon", "history_emtia", "history_nakit"]:
                        headers = ["Tarih", "Değer_TRY", "Değer_USD"]
                    elif sheet_type == "daily_base_prices":
                        headers = ["Tarih", "Saat", "Kod", "Fiyat", "PB"]
                    else:
                        headers = []
                    
                    if headers:
                        new_sheet.append_row(headers)
                    
                    print(f"   ✅ {sheet_name} oluşturuldu")
                    created_count += 1
                    
                except Exception as e:
                    print(f"   ❌ {sheet_name} oluşturulamadı: {str(e)}")
        
        print(f"\n📊 Özet:")
        print(f"   ✅ Oluşturulan: {created_count}")
        print(f"   ✓  Atlanan (zaten mevcut): {skipped_count}")
        print(f"\n✨ Kurulum tamamlandı!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ HATA: {str(e)}")
        print("\nLütfen şunları kontrol edin:")
        print("1. Google Sheets API bağlantısı aktif mi?")
        print("2. st.secrets içinde 'gcp_service_account' tanımlı mı?")
        print("3. Service account'un 'PortfoyData' spreadsheet'ine erişimi var mı?")
        return False


def copy_main_data_to_mert():
    """
    Copy existing data from the main sheet (sheet1) to MERT profile.
    This should be run once during initial setup to migrate existing data.
    """
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
        client = gspread.authorize(creds)
        
        spreadsheet = client.open("PortfoyData")
        
        print("\n📦 Mevcut veri MERT profiline kopyalanıyor...")
        
        # Get main sheet (sheet1 or first sheet)
        try:
            main_sheet = spreadsheet.sheet1
        except:
            main_sheet = spreadsheet.get_worksheet(0)
        
        # Get all data from main sheet
        all_data = main_sheet.get_all_values()
        
        if not all_data:
            print("⚠️  Ana sayfada veri bulunamadı.")
            return True
        
        # Get or create MERT's main sheet
        mert_sheet_name = "PortfoyData_MERT"
        try:
            mert_sheet = spreadsheet.worksheet(mert_sheet_name)
        except:
            print(f"❌ {mert_sheet_name} bulunamadı. Önce setup_profile_sheets() çalıştırın.")
            return False
        
        # Clear MERT sheet and copy data
        mert_sheet.clear()
        mert_sheet.update(all_data)
        
        print(f"✅ {len(all_data)} satır veri {mert_sheet_name} sayfasına kopyalandı")
        print(f"📊 Orijinal veri korundu, MERT profiline başarıyla aktarıldı")
        
        return True
        
    except Exception as e:
        print(f"\n❌ HATA: {str(e)}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("🎯 PORTFOLIO PROFILE SYSTEM SETUP")
    print("=" * 60)
    
    # Step 1: Create profile sheets
    success = setup_profile_sheets()
    
    if success:
        print("\n" + "=" * 60)
        print("📦 OPTIONAL: Mevcut Veriyi MERT Profiline Kopyala")
        print("=" * 60)
        
        response = input("\nMevcut veriyi MERT profiline kopyalamak ister misiniz? (y/n): ")
        if response.lower() == 'y':
            copy_main_data_to_mert()
        else:
            print("⏭️  Veri kopyalama atlandı.")
    
    print("\n" + "=" * 60)
    print("🎉 Kurulum bitti!")
    print("=" * 60)
    print("\nSonraki adımlar:")
    print("1. Streamlit uygulamasını başlatın")
    print("2. Profil seçiciyi kullanarak farklı profiller arasında geçiş yapın")
    print("3. Her profil için ayrı varlıklar ekleyin")
    print("4. TOTAL profili ile tüm profillerin toplamını görüntüleyin")
    print("\n💡 Not: TOTAL profili otomatik hesaplanır ve düzenlenemez.")
