#!/usr/bin/env python3
"""
ANNEM Profili Veri Düzeltme Scripti
Bu script ANNEM profilinin Google Sheets verilerini kontrol eder ve düzeltir.
"""

import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import streamlit as st
from data_loader_profiles import _get_gspread_client, SHEET_NAME, _retry_with_backoff
from data_loader_profiles import _get_profile_sheet, get_data_from_sheet_profile

def check_profile_data():
    """Her iki profilin verilerini kontrol et ve karşılaştır."""
    print("=" * 60)
    print("PROFİL VERİ KONTROLÜ")
    print("=" * 60)
    
    try:
        # MERT profili verilerini al
        print("\n📊 MERT Profili Verileri:")
        print("-" * 60)
        mert_df = get_data_from_sheet_profile(profile_name="MERT")
        print(f"Toplam satır sayısı: {len(mert_df)}")
        if not mert_df.empty:
            print("\nİlk 5 satır:")
            print(mert_df.head().to_string())
            print(f"\nVarlık kodları: {mert_df['Kod'].tolist() if 'Kod' in mert_df.columns else 'N/A'}")
        else:
            print("⚠️ MERT profili boş!")
        
        # ANNEM profili verilerini al
        print("\n\n💝 ANNEM Profili Verileri:")
        print("-" * 60)
        annem_df = get_data_from_sheet_profile(profile_name="ANNEM")
        print(f"Toplam satır sayısı: {len(annem_df)}")
        if not annem_df.empty:
            print("\nİlk 5 satır:")
            print(annem_df.head().to_string())
            print(f"\nVarlık kodları: {annem_df['Kod'].tolist() if 'Kod' in annem_df.columns else 'N/A'}")
        else:
            print("⚠️ ANNEM profili boş!")
        
        # Karşılaştırma
        print("\n\n🔍 KARŞILAŞTIRMA:")
        print("-" * 60)
        if not mert_df.empty and not annem_df.empty:
            # Aynı veriler var mı kontrol et
            mert_codes = set(mert_df['Kod'].tolist()) if 'Kod' in mert_df.columns else set()
            annem_codes = set(annem_df['Kod'].tolist()) if 'Kod' in annem_df.columns else set()
            
            common_codes = mert_codes.intersection(annem_codes)
            print(f"MERT'teki varlık sayısı: {len(mert_codes)}")
            print(f"ANNEM'deki varlık sayısı: {len(annem_codes)}")
            print(f"Ortak varlık sayısı: {len(common_codes)}")
            
            if len(common_codes) > 0:
                print(f"\n⚠️ UYARI: Ortak varlıklar bulundu: {common_codes}")
                print("Bu, ANNEM profilinin MERT'in verileriyle karışmış olabileceğini gösterir.")
            
            # Verilerin aynı olup olmadığını kontrol et
            if len(mert_df) == len(annem_df):
                # Satır satır karşılaştır
                mert_sorted = mert_df.sort_values(by=['Kod'] if 'Kod' in mert_df.columns else mert_df.columns[0])
                annem_sorted = annem_df.sort_values(by=['Kod'] if 'Kod' in annem_df.columns else annem_df.columns[0])
                
                # Sadece veri kolonlarını karşılaştır (Kod, Pazar, Adet, Maliyet)
                compare_cols = ['Kod', 'Pazar', 'Adet', 'Maliyet']
                if all(col in mert_sorted.columns and col in annem_sorted.columns for col in compare_cols):
                    mert_compare = mert_sorted[compare_cols].fillna('').astype(str)
                    annem_compare = annem_sorted[compare_cols].fillna('').astype(str)
                    
                    if mert_compare.equals(annem_compare):
                        print("\n❌ SORUN TESPİT EDİLDİ!")
                        print("ANNEM profili MERT'in verileriyle aynı. ANNEM'in verileri kaybolmuş olabilir.")
                        return True, mert_df, annem_df
                    else:
                        print("\n✅ Veriler farklı görünüyor. Detaylı karşılaştırma gerekebilir.")
        elif not mert_df.empty and annem_df.empty:
            print("\n⚠️ ANNEM profili boş ama MERT'te veri var.")
        elif mert_df.empty and not annem_df.empty:
            print("\n⚠️ MERT profili boş ama ANNEM'de veri var.")
        else:
            print("\n⚠️ Her iki profil de boş!")
        
        return False, mert_df, annem_df
        
    except Exception as e:
        print(f"\n❌ Hata oluştu: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, None, None


def check_sheet_names():
    """Google Sheets'teki sheet isimlerini kontrol et."""
    print("\n\n" + "=" * 60)
    print("GOOGLE SHEETS YAPISI KONTROLÜ")
    print("=" * 60)
    
    try:
        client = _get_gspread_client()
        if client is None:
            print("❌ Google Sheets bağlantısı kurulamadı!")
            return
        
        spreadsheet = _retry_with_backoff(
            lambda: client.open(SHEET_NAME),
            max_retries=2,
            initial_delay=1.0,
            max_delay=30.0
        )
        
        if spreadsheet is None:
            print("❌ Spreadsheet açılamadı!")
            return
        
        worksheets = spreadsheet.worksheets()
        print(f"\n📋 Toplam {len(worksheets)} worksheet bulundu:")
        print("-" * 60)
        
        for ws in worksheets:
            print(f"  • {ws.title} (ID: {ws.id}, Satır: {ws.row_count})")
            
            # Her sheet'in ilk birkaç satırını göster
            try:
                records = ws.get_all_records()
                if records:
                    print(f"    → {len(records)} kayıt var")
                    if len(records) > 0:
                        first_record = records[0]
                        if 'Kod' in first_record:
                            codes = [r.get('Kod', '') for r in records[:5]]
                            print(f"    → İlk varlıklar: {codes}")
            except:
                print(f"    → Veri okunamadı")
        
        # Özellikle "annem" ve "sheet1" sheet'lerini kontrol et
        print("\n\n🔍 ÖNEMLİ SHEET'LER:")
        print("-" * 60)
        
        try:
            sheet1 = spreadsheet.sheet1
            records = sheet1.get_all_records()
            print(f"📄 Sheet1 (MERT): {len(records)} kayıt")
            if records:
                codes = [r.get('Kod', '') for r in records[:5]]
                print(f"   Varlıklar: {codes}")
        except Exception as e:
            print(f"❌ Sheet1 okunamadı: {str(e)}")
        
        try:
            annem_ws = spreadsheet.worksheet("annem")
            records = annem_ws.get_all_records()
            print(f"📄 annem (ANNEM): {len(records)} kayıt")
            if records:
                codes = [r.get('Kod', '') for r in records[:5]]
                print(f"   Varlıklar: {codes}")
        except Exception as e:
            print(f"❌ annem sheet'i bulunamadı: {str(e)}")
        
    except Exception as e:
        print(f"\n❌ Hata oluştu: {str(e)}")
        import traceback
        traceback.print_exc()


def clear_annem_sheet():
    """ANNEM sheet'ini temizle (sadece başlıkları bırak)."""
    print("\n\n" + "=" * 60)
    print("ANNEM SHEET'İNİ TEMİZLEME")
    print("=" * 60)
    
    try:
        worksheet = _get_profile_sheet("main", "ANNEM")
        if worksheet is None:
            print("❌ ANNEM worksheet'i bulunamadı!")
            return False
        
        # Başlıkları koru, verileri temizle
        headers = ["Kod", "Pazar", "Adet", "Maliyet", "Tip", "Notlar"]
        
        def _clear_sheet():
            worksheet.clear()
            worksheet.update([headers], range_name="A1:F1")
            return True
        
        result = _retry_with_backoff(_clear_sheet, max_retries=3, initial_delay=2.0, max_delay=60.0)
        
        if result:
            print("✅ ANNEM sheet'i temizlendi. Artık boş bir sheet var.")
            return True
        else:
            print("❌ ANNEM sheet'i temizlenemedi!")
            return False
            
    except Exception as e:
        print(f"❌ Hata oluştu: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def restore_annem_from_backup():
    """ANNEM verilerini yedekten geri yükle (eğer varsa)."""
    print("\n\n" + "=" * 60)
    print("ANNEM VERİLERİNİ GERİ YÜKLEME")
    print("=" * 60)
    print("⚠️ Bu özellik henüz implement edilmedi.")
    print("Eğer Google Sheets'te bir yedek varsa, manuel olarak geri yükleyebilirsiniz.")
    print("\nÖnerilen adımlar:")
    print("1. Google Sheets'te 'annem' sheet'ine gidin")
    print("2. Sheet geçmişini kontrol edin (File > Version history)")
    print("3. ANNEM'in verilerinin olduğu bir önceki versiyonu bulun")
    print("4. O versiyonu geri yükleyin")


def main():
    """Ana fonksiyon."""
    print("\n" + "=" * 60)
    print("ANNEM PROFİLİ VERİ DÜZELTME ARACI")
    print("=" * 60)
    print("\nBu script şunları yapar:")
    print("1. MERT ve ANNEM profillerinin verilerini kontrol eder")
    print("2. Google Sheets yapısını inceler")
    print("3. Sorun varsa düzeltme önerileri sunar")
    print("\n" + "=" * 60)
    
    # 1. Sheet yapısını kontrol et
    check_sheet_names()
    
    # 2. Profil verilerini kontrol et
    has_issue, mert_df, annem_df = check_profile_data()
    
    # 3. Sorun varsa çözüm öner
    if has_issue:
        print("\n\n" + "=" * 60)
        print("ÇÖZÜM ÖNERİLERİ")
        print("=" * 60)
        print("\n⚠️ ANNEM profili MERT'in verileriyle karışmış görünüyor.")
        print("\nSeçenekler:")
        print("\n1. ANNEM sheet'ini temizle (şu anki yanlış verileri sil)")
        print("   → Bu işlem ANNEM sheet'ini boşaltır")
        print("   → Sonra ANNEM'in doğru verilerini manuel olarak ekleyebilirsiniz")
        print("\n2. Google Sheets versiyon geçmişinden geri yükle")
        print("   → Google Sheets'te File > Version history")
        print("   → ANNEM'in doğru verilerinin olduğu bir önceki versiyonu bulun")
        print("   → O versiyonu geri yükleyin")
        print("\n3. Manuel düzeltme")
        print("   → Google Sheets'te 'annem' sheet'ine gidin")
        print("   → MERT'in verilerini silin")
        print("   → ANNEM'in doğru verilerini ekleyin")
        
        response = input("\nANNEM sheet'ini temizlemek ister misiniz? (e/h): ")
        if response.lower() == 'e':
            confirm = input("⚠️ Bu işlem geri alınamaz! Emin misiniz? (EVET yazın): ")
            if confirm == "EVET":
                clear_annem_sheet()
                print("\n✅ ANNEM sheet'i temizlendi.")
                print("Şimdi ANNEM'in doğru verilerini Google Sheets'ten manuel olarak ekleyebilirsiniz.")
            else:
                print("İşlem iptal edildi.")
        else:
            print("İşlem iptal edildi.")
    else:
        print("\n\n✅ Herhangi bir sorun tespit edilmedi.")
        print("Eğer yine de sorun yaşıyorsanız, Google Sheets'teki sheet isimlerini kontrol edin.")
    
    print("\n" + "=" * 60)
    print("İşlem tamamlandı.")
    print("=" * 60)


if __name__ == "__main__":
    # Streamlit secrets kullanmak için
    try:
        import streamlit as st
        # Streamlit context'i yoksa, secrets'ı manuel yüklemek gerekebilir
        main()
    except Exception as e:
        print(f"Streamlit context hatası: {str(e)}")
        print("Script'i doğrudan çalıştırmak için secrets'ı manuel yükleyin.")
        main()
