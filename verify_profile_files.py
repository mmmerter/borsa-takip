"""
Simple verification script to check if all profile system files are in place
No external dependencies required
"""

import os
import sys

def check_file_exists(filepath, description):
    """Check if a file exists and print result"""
    exists = os.path.isfile(filepath)
    status = "✅" if exists else "❌"
    print(f"{status} {description}: {filepath}")
    return exists

def verify_profile_system():
    """Verify all profile system files are in place"""
    print("=" * 70)
    print("🔍 PROFILE SYSTEM FILE VERIFICATION")
    print("=" * 70)
    print()
    
    files_to_check = [
        ("profile_manager.py", "Profile management module"),
        ("data_loader_profiles.py", "Profile-aware data loader"),
        ("setup_profiles.py", "Profile setup script"),
        ("test_profile_system.py", "Profile system tests"),
        ("PROFILE_SISTEMI_KILAVUZU.md", "Profile system documentation"),
        ("portfoy.py", "Main application (updated)"),
        ("data_loader.py", "Original data loader"),
        ("utils.py", "Utility functions"),
        ("charts.py", "Chart rendering"),
    ]
    
    all_exist = True
    for filename, description in files_to_check:
        filepath = os.path.join("/workspace", filename)
        exists = check_file_exists(filepath, description)
        if not exists:
            all_exist = False
    
    print()
    print("=" * 70)
    
    if all_exist:
        print("✅ ALL FILES PRESENT - Profile system is ready!")
        print("=" * 70)
        print()
        print("📋 Next steps:")
        print()
        print("1. 🔧 Setup Google Sheets:")
        print("   streamlit run setup_profiles.py")
        print()
        print("2. 🚀 Start the application:")
        print("   streamlit run portfoy.py")
        print()
        print("3. 📖 Read the documentation:")
        print("   cat PROFILE_SISTEMI_KILAVUZU.md")
        print()
        print("4. 🎯 Test the system:")
        print("   - Switch between profiles using the selector")
        print("   - Add assets to different profiles")
        print("   - View TOTAL profile for combined view")
        print()
        return True
    else:
        print("❌ SOME FILES ARE MISSING - Please check installation")
        print("=" * 70)
        return False

if __name__ == "__main__":
    success = verify_profile_system()
    sys.exit(0 if success else 1)
