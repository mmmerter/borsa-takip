#!/usr/bin/env python3
"""
Hızlı Profil Kurulum Scripti
Eksik worksheet'leri otomatik oluşturur ve yapılandırır.

Kullanım:
    python3 hizli_profil_kurulum.py
    
veya Streamlit ile:
    streamlit run hizli_profil_kurulum.py
"""

import sys
import os

# Add workspace to path
sys.path.insert(0, '/workspace')

def main():
    """Ana kurulum fonksiyonu"""
    
    print("=" * 80)
    print("🚀 HIZLI PROFİL SİSTEMİ KURULUMU")
    print("=" * 80)
    print()
    print("Bu script şunları yapacak:")
    print("  ✅ Google Sheets bağlantısını kontrol eder")
    print("  ✅ Eksik profile worksheet'lerini oluşturur")
    print("  ✅ Gerekli başlıkları ekler")
    print()
    
    try:
        # Import required modules
        print("📦 Gerekli modüller yükleniyor...")
        try:
            import gspread
            from oauth2client.service_account import ServiceAccountCredentials
            import toml
            print("   ✅ Modüller yüklendi\n")
        except ImportError as e:
            print(f"   ❌ Modül yüklenemedi: {e}")
            print("\n💡 Gerekli paketleri yükleyin:")
            print("   pip install gspread oauth2client toml")
            return False
        
        # Load credentials
        print("🔐 Google Sheets kimlik bilgileri yükleniyor...")
        secrets_path = "/workspace/.streamlit/secrets.toml"
        
        if not os.path.exists(secrets_path):
            print(f"   ⚠️  Secrets dosyası bulunamadı: {secrets_path}")
            print("\n   Streamlit ile çalıştırıyorsanız:")
            print("   streamlit run hizli_profil_kurulum.py")
            
            # Try with streamlit secrets
            try:
                import streamlit as st
                if hasattr(st, 'secrets') and 'gcp_service_account' in st.secrets:
                    creds_dict = st.secrets["gcp_service_account"]
                    print("   ✅ Streamlit secrets'tan yüklendi\n")
                else:
                    print("   ❌ Streamlit secrets'ta 'gcp_service_account' bulunamadı")
                    return False
            except:
                print("   ❌ Secrets yüklenemedi")
                return False
        else:
            secrets = toml.load(secrets_path)
            if "gcp_service_account" not in secrets:
                print("   ❌ 'gcp_service_account' anahtarı bulunamadı")
                return False
            creds_dict = secrets["gcp_service_account"]
            print("   ✅ Kimlik bilgileri yüklendi\n")
        
        # Connect to Google Sheets
        print("🔗 Google Sheets'e bağlanılıyor...")
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        
        try:
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
            client = gspread.authorize(creds)
            print("   ✅ Bağlantı başarılı\n")
        except Exception as e:
            print(f"   ❌ Bağlantı hatası: {e}")
            return False
        
        # Open spreadsheet
        print("📊 PortfoyData spreadsheet'i açılıyor...")
        try:
            spreadsheet = client.open("PortfoyData")
            print(f"   ✅ Spreadsheet açıldı: {spreadsheet.title}")
            print(f"   🔗 URL: {spreadsheet.url}\n")
        except Exception as e:
            print(f"   ❌ Spreadsheet açılamadı: {e}")
            return False
        
        # Get existing worksheets
        print("📋 Mevcut worksheet'ler kontrol ediliyor...")
        existing_sheets = {}
        all_worksheets = spreadsheet.worksheets()
        
        for ws in all_worksheets:
            existing_sheets[ws.title.lower()] = ws.title
            print(f"   • {ws.title}")
        
        print()
        
        # Define required profile sheets
        required_sheets = {
            "annem": {
                "display_name": "ANNEM Profili",
                "headers": ["Kod", "Pazar", "Adet", "Maliyet", "Tip", "Notlar"]
            },
            "berguzar": {
                "display_name": "BERGUZAR Profili",
                "headers": ["Kod", "Pazar", "Adet", "Maliyet", "Tip", "Notlar"]
            },
            "ikramiye": {
                "display_name": "İKRAMİYE Profili",
                "headers": ["Kod", "Pazar", "Adet", "Maliyet", "Tip", "Notlar"]
            },
            "total": {
                "display_name": "TOTAL Profili (Opsiyonel)",
                "headers": ["Kod", "Pazar", "Adet", "Maliyet", "Tip", "Notlar"]
            }
        }
        
        # Check which sheets need to be created
        print("=" * 80)
        print("🔍 PROFİL WORKSHEET'LERİ KONTROLÜ")
        print("=" * 80)
        print()
        
        sheets_to_create = []
        for sheet_name, config in required_sheets.items():
            # Check various name variations
            variations = [
                sheet_name,
                sheet_name.capitalize(),
                sheet_name.upper()
            ]
            
            found = False
            for var in variations:
                if var.lower() in existing_sheets:
                    print(f"✅ {config['display_name']}: '{existing_sheets[var.lower()]}' mevcut")
                    found = True
                    break
            
            if not found:
                print(f"❌ {config['display_name']}: Bulunamadı, oluşturulacak")
                sheets_to_create.append((sheet_name, config))
        
        print()
        
        # Create missing sheets
        if sheets_to_create:
            print("=" * 80)
            print("📝 EKSİK WORKSHEET'LER OLUŞTURULUYOR")
            print("=" * 80)
            print()
            
            for sheet_name, config in sheets_to_create:
                try:
                    # Skip TOTAL if user doesn't want it
                    if sheet_name == "total":
                        response = input(f"'{sheet_name}' worksheet'ini oluşturmak ister misiniz? (y/n): ")
                        if response.lower() != 'y':
                            print(f"   ⏭️  '{sheet_name}' atlandı (TOTAL otomatik hesaplanır)\n")
                            continue
                    
                    print(f"   🔨 '{sheet_name}' oluşturuluyor...")
                    new_sheet = spreadsheet.add_worksheet(
                        title=sheet_name,
                        rows=1000,
                        cols=20
                    )
                    
                    # Add headers
                    new_sheet.append_row(config["headers"])
                    
                    print(f"   ✅ '{sheet_name}' başarıyla oluşturuldu!")
                    print(f"      Başlıklar: {', '.join(config['headers'])}\n")
                    
                except Exception as e:
                    print(f"   ❌ '{sheet_name}' oluşturulamadı: {e}\n")
        else:
            print("✅ Tüm gerekli worksheet'ler zaten mevcut!\n")
        
        # Optional: Create history sheets
        print("=" * 80)
        print("📊 TARİHÇE WORKSHEET'LERİ (OPSİYONEL)")
        print("=" * 80)
        print()
        print("Her profil için aşağıdaki tarihçe worksheet'leri oluşturulabilir:")
        print("  • Satislar_[PROFIL] - Satış geçmişi")
        print("  • portfolio_history_[PROFIL] - Portföy değeri tarihçesi")
        print("  • history_bist_[PROFIL] - BIST tarihçesi")
        print("  • history_abd_[PROFIL] - ABD hisse tarihçesi")
        print("  • history_fon_[PROFIL] - Fon tarihçesi")
        print("  • history_emtia_[PROFIL] - Emtia tarihçesi")
        print("  • history_nakit_[PROFIL] - Nakit tarihçesi")
        print()
        
        response = input("Tarihçe worksheet'lerini şimdi oluşturmak ister misiniz? (y/n): ")
        
        if response.lower() == 'y':
            profiles = ["ANNEM", "BERGUZAR", "İKRAMİYE"]
            history_types = {
                "Satislar": ["Tarih", "Kod", "Pazar", "Satılan Adet", "Satış Fiyatı", "Maliyet", "Kâr/Zarar"],
                "portfolio_history": ["Tarih", "Değer_TRY", "Değer_USD"],
                "history_bist": ["Tarih", "Değer_TRY", "Değer_USD"],
                "history_abd": ["Tarih", "Değer_TRY", "Değer_USD"],
                "history_fon": ["Tarih", "Değer_TRY", "Değer_USD"],
                "history_emtia": ["Tarih", "Değer_TRY", "Değer_USD"],
                "history_nakit": ["Tarih", "Değer_TRY", "Değer_USD"],
            }
            
            created = 0
            print()
            for profile in profiles:
                print(f"📁 {profile} profili için tarihçe worksheet'leri:")
                for hist_type, headers in history_types.items():
                    sheet_name = f"{hist_type}_{profile}"
                    
                    if sheet_name.lower() not in existing_sheets:
                        try:
                            new_sheet = spreadsheet.add_worksheet(
                                title=sheet_name,
                                rows=1000,
                                cols=20
                            )
                            new_sheet.append_row(headers)
                            print(f"   ✅ {sheet_name}")
                            created += 1
                        except Exception as e:
                            print(f"   ❌ {sheet_name}: {str(e)}")
                    else:
                        print(f"   ⏭️  {sheet_name} (zaten mevcut)")
                print()
            
            print(f"✅ {created} tarihçe worksheet'i oluşturuldu!\n")
        else:
            print("   ⏭️  Tarihçe worksheet'leri atlandı\n")
        
        # Final summary
        print("=" * 80)
        print("🎉 KURULUM TAMAMLANDI!")
        print("=" * 80)
        print()
        print("✨ Sonraki Adımlar:")
        print()
        print("1. 🚀 Uygulamayı başlatın:")
        print("      streamlit run portfoy.py")
        print()
        print("2. 👤 Profil seçin:")
        print("      • Üstteki profil seçiciyi kullanın")
        print("      • ANNEM, BERGUZAR veya İKRAMİYE'yi seçin")
        print()
        print("3. ➕ Varlık ekleyin:")
        print("      • 'Ekle/Çıkar' sekmesine gidin")
        print("      • Her profile ayrı ayrı varlıklar ekleyin")
        print()
        print("4. 📊 TOTAL görüntüleyin:")
        print("      • TOTAL profilini seçin")
        print("      • Tüm profillerin birleşik görünümünü görün")
        print()
        print("=" * 80)
        print("📖 Daha fazla bilgi: PROFIL_SORUNU_COZUM.md")
        print("=" * 80)
        print()
        
        return True
        
    except Exception as e:
        print(f"\n❌ BEKLENMEYEN HATA: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    try:
        # Check if running with streamlit
        import streamlit as st
        st.set_page_config(
            page_title="Profil Kurulum",
            page_icon="🚀",
            layout="wide"
        )
        
        st.title("🚀 Profil Sistemi Kurulumu")
        st.markdown("---")
        
        if st.button("Kurulumu Başlat", type="primary"):
            with st.spinner("Kurulum yapılıyor..."):
                success = main()
                if success:
                    st.success("✅ Kurulum başarıyla tamamlandı!")
                else:
                    st.error("❌ Kurulum sırasında hatalar oluştu.")
        
    except ImportError:
        # Not running with streamlit, run as regular script
        success = main()
        sys.exit(0 if success else 1)
