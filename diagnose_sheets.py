"""
Diagnostic script to check Google Sheets structure and identify the issue
"""

import sys
import os

# Add workspace to path
sys.path.insert(0, '/workspace')

def diagnose_sheets():
    """Check Google Sheets structure and identify issues"""
    try:
        import streamlit as st
        import gspread
        from oauth2client.service_account import ServiceAccountCredentials
        
        print("=" * 80)
        print("🔍 GOOGLE SHEETS YAPISI TESPİTİ")
        print("=" * 80)
        
        # Try to get credentials
        try:
            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            
            # Check if secrets file exists
            secrets_path = "/workspace/.streamlit/secrets.toml"
            if not os.path.exists(secrets_path):
                print(f"\n❌ HATA: Secrets dosyası bulunamadı: {secrets_path}")
                print("\n💡 Çözüm: .streamlit/secrets.toml dosyasını oluşturun ve gcp_service_account ayarlarını ekleyin")
                return False
            
            # Load secrets manually for diagnosis
            import toml
            secrets = toml.load(secrets_path)
            
            if "gcp_service_account" not in secrets:
                print("\n❌ HATA: secrets.toml dosyasında 'gcp_service_account' anahtarı bulunamadı")
                return False
            
            creds = ServiceAccountCredentials.from_json_keyfile_dict(secrets["gcp_service_account"], scope)
            client = gspread.authorize(creds)
            
            print("\n✅ Google Sheets bağlantısı başarılı!\n")
            
        except Exception as e:
            print(f"\n❌ Google Sheets bağlantısı başarısız: {str(e)}")
            return False
        
        # Open spreadsheet
        try:
            spreadsheet = client.open("PortfoyData")
            print(f"📊 Spreadsheet: {spreadsheet.title}")
            print(f"🔗 URL: {spreadsheet.url}\n")
        except Exception as e:
            print(f"❌ PortfoyData spreadsheet'i açılamadı: {str(e)}")
            return False
        
        # List all worksheets
        print("=" * 80)
        print("📋 MEVCUT TÜM WORKSHEETS")
        print("=" * 80)
        
        all_worksheets = spreadsheet.worksheets()
        
        if not all_worksheets:
            print("⚠️  Hiç worksheet bulunamadı!")
            return False
        
        worksheet_map = {}
        for i, ws in enumerate(all_worksheets):
            print(f"\n{i+1}. Worksheet:")
            print(f"   📄 İsim: '{ws.title}'")
            print(f"   🔢 Satır: {ws.row_count}")
            print(f"   🔢 Sütun: {ws.col_count}")
            
            # Check if has data
            try:
                data = ws.get_all_records()
                print(f"   📊 Veri satırı: {len(data)}")
                if data:
                    print(f"   📌 İlk satır başlıkları: {list(data[0].keys())[:5]}")
            except Exception as e:
                print(f"   ⚠️  Veri okunamadı: {str(e)}")
            
            worksheet_map[ws.title.lower()] = ws.title
        
        # Check for profile worksheets
        print("\n" + "=" * 80)
        print("🎯 PROFİL WORKSHEETS KONTROLÜ")
        print("=" * 80)
        
        required_profiles = {
            "MERT (Ana Profil)": ["sheet1", "ana sayfa", "portfoydata_mert"],
            "ANNEM": ["annem", "portfoydata_annem"],
            "BERGUZAR": ["berguzar", "bergüzar", "portfoydata_berguzar"],
            "TOTAL": ["total", "portfoydata_total"]
        }
        
        profile_status = {}
        for profile_name, possible_names in required_profiles.items():
            found = False
            found_name = None
            
            for possible_name in possible_names:
                if possible_name in worksheet_map:
                    found = True
                    found_name = worksheet_map[possible_name]
                    break
            
            profile_status[profile_name] = (found, found_name)
            
            if found:
                print(f"\n✅ {profile_name}: '{found_name}' worksheet'i bulundu")
            else:
                print(f"\n❌ {profile_name}: Worksheet bulunamadı!")
                print(f"   Aranan isimler: {', '.join(possible_names)}")
        
        # Analyze the issue
        print("\n" + "=" * 80)
        print("🔍 SORUN ANALİZİ")
        print("=" * 80)
        
        missing_profiles = [name for name, (found, _) in profile_status.items() if not found]
        
        if missing_profiles:
            print(f"\n⚠️  EKSIK PROFİLLER: {', '.join(missing_profiles)}")
            print("\n💡 ÇÖZÜM ÖNERİLERİ:")
            print("\n1. Manuel olarak Google Sheets'te eksik worksheet'leri oluşturun:")
            for profile in missing_profiles:
                if profile == "ANNEM":
                    print(f"   - 'annem' adında bir worksheet oluşturun")
                elif profile == "BERGUZAR":
                    print(f"   - 'berguzar' adında bir worksheet oluşturun (küçük harf)")
                elif profile == "TOTAL":
                    print(f"   - 'total' adında bir worksheet oluşturun")
            
            print("\n2. Veya setup script'ini çalıştırın:")
            print("   streamlit run setup_profiles_existing.py")
            
            print("\n3. Worksheet'lere şu başlıkları ekleyin:")
            print("   Kod | Pazar | Adet | Maliyet | Tip | Notlar")
            
        else:
            print("\n✅ TÜM PROFİL WORKSHEETS MEVCUT!")
            print("\n💡 Eğer hala veri yüklenemiyor ise:")
            print("   1. Worksheet'lerin içinde veri olduğundan emin olun")
            print("   2. Başlıkların doğru olduğunu kontrol edin")
            print("   3. Service account'un okuma yetkisi olduğunu doğrulayın")
        
        # Check data_loader_profiles.py hardcoded names
        print("\n" + "=" * 80)
        print("📝 data_loader_profiles.py KONTROL")
        print("=" * 80)
        
        print("\ndata_loader_profiles.py dosyasında hardcoded worksheet isimleri:")
        print("   - MERT: spreadsheet.sheet1")
        print("   - ANNEM: spreadsheet.worksheet('annem')")
        print("   - BERGUZAR: spreadsheet.worksheet('berguzar')")
        print("   - TOTAL: spreadsheet.worksheet('total')")
        
        print("\nMevcut worksheet isimleri:")
        for profile_name, (found, found_name) in profile_status.items():
            if found:
                print(f"   - {profile_name}: '{found_name}'")
            else:
                print(f"   - {profile_name}: ❌ BULUNAMADI")
        
        # Final recommendation
        print("\n" + "=" * 80)
        print("🎯 SONUÇ VE ÖNERİLER")
        print("=" * 80)
        
        if missing_profiles:
            print(f"\n❌ {len(missing_profiles)} profil worksheet'i eksik")
            print("\n✨ HIZLI ÇÖZÜM:")
            print("   1. Google Sheets'te PortfoyData spreadsheet'ini açın")
            print("   2. Eksik worksheet'leri oluşturun (küçük harfle):")
            for profile in missing_profiles:
                if profile == "ANNEM":
                    print("      + 'annem' worksheet'i")
                elif profile == "BERGUZAR":
                    print("      + 'berguzar' worksheet'i")
                elif profile == "TOTAL":
                    print("      + 'total' worksheet'i")
            print("   3. Her worksheet'e başlıkları ekleyin: Kod, Pazar, Adet, Maliyet, Tip, Notlar")
            print("   4. streamlit run portfoy.py ile uygulamayı yeniden başlatın")
        else:
            print("\n✅ Tüm worksheet'ler mevcut, sistem hazır!")
        
        return len(missing_profiles) == 0
        
    except ImportError as e:
        print(f"\n❌ Modül yüklenemedi: {str(e)}")
        print("\n💡 Gerekli paketleri yükleyin:")
        print("   pip install streamlit gspread oauth2client toml")
        return False
    except Exception as e:
        print(f"\n❌ Beklenmeyen hata: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("🚀 BAŞLATILIYOR...")
    print("=" * 80)
    
    success = diagnose_sheets()
    
    print("\n" + "=" * 80)
    if success:
        print("✅ TEŞHİS TAMAMLANDI - SİSTEM HAZIR")
    else:
        print("⚠️  TEŞHİS TAMAMLANDI - SORUNLAR TESPİT EDİLDİ")
    print("=" * 80)
    print()
    
    sys.exit(0 if success else 1)
