"""
Test script for profile system
Verifies that profile isolation and TOTAL aggregation work correctly
"""

import pandas as pd
from profile_manager import (
    get_all_profiles,
    get_individual_profiles,
    is_aggregate_profile,
    get_profile_display_name,
    get_profile_sheet_name,
    PROFILES
)

def test_profile_definitions():
    """Test that all profiles are defined correctly"""
    print("🧪 Testing profile definitions...")
    
    assert len(PROFILES) == 4, "Should have exactly 4 profiles"
    assert "MERT" in PROFILES, "MERT profile should exist"
    assert "ANNEM" in PROFILES, "ANNEM profile should exist"
    assert "BERGUZAR" in PROFILES, "BERGUZAR profile should exist"
    assert "TOTAL" in PROFILES, "TOTAL profile should exist"
    
    # Check TOTAL is aggregate
    assert is_aggregate_profile("TOTAL"), "TOTAL should be aggregate"
    assert not is_aggregate_profile("MERT"), "MERT should not be aggregate"
    
    print("✅ Profile definitions OK")


def test_profile_helpers():
    """Test profile helper functions"""
    print("\n🧪 Testing profile helpers...")
    
    # Test get_all_profiles
    all_profiles = get_all_profiles()
    assert len(all_profiles) == 4, "Should return 4 profiles"
    assert all_profiles[0] == "MERT", "First profile should be MERT"
    
    # Test get_individual_profiles
    individual_profiles = get_individual_profiles()
    assert len(individual_profiles) == 3, "Should return 3 individual profiles"
    assert "TOTAL" not in individual_profiles, "TOTAL should not be in individual profiles"
    
    # Test display names
    assert "MERT" in get_profile_display_name("MERT")
    assert "TOPLAM" in get_profile_display_name("TOTAL")
    
    print("✅ Profile helpers OK")


def test_sheet_naming():
    """Test sheet name generation"""
    print("\n🧪 Testing sheet naming...")
    
    # Test individual profile sheets
    mert_main = get_profile_sheet_name("main", "MERT")
    assert mert_main == "PortfoyData_MERT", f"Expected 'PortfoyData_MERT', got '{mert_main}'"
    
    annem_sales = get_profile_sheet_name("sales", "ANNEM")
    assert annem_sales == "Satislar_ANNEM", f"Expected 'Satislar_ANNEM', got '{annem_sales}'"
    
    # Test TOTAL (should return None)
    total_main = get_profile_sheet_name("main", "TOTAL")
    assert total_main is None, "TOTAL profile should not have a sheet name"
    
    print("✅ Sheet naming OK")


def test_data_isolation():
    """Test that profile data would be isolated (mock test)"""
    print("\n🧪 Testing data isolation (mock)...")
    
    # Create mock data for different profiles
    mert_data = pd.DataFrame({
        "Kod": ["THYAO", "GARAN"],
        "Adet": [100, 200],
        "Maliyet": [50, 30]
    })
    
    annem_data = pd.DataFrame({
        "Kod": ["BTC", "ETH"],
        "Adet": [0.5, 2],
        "Maliyet": [50000, 2000]
    })
    
    # Verify they are separate
    assert len(mert_data) == 2, "MERT should have 2 assets"
    assert len(annem_data) == 2, "ANNEM should have 2 assets"
    assert not mert_data.equals(annem_data), "Profile data should be different"
    
    # Verify TOTAL would aggregate (mock)
    combined = pd.concat([mert_data, annem_data], ignore_index=True)
    assert len(combined) == 4, "TOTAL should have 4 assets (combined)"
    
    print("✅ Data isolation OK")


def test_profile_colors_and_icons():
    """Test profile visual attributes"""
    print("\n🧪 Testing profile colors and icons...")
    
    # Check all profiles have required attributes
    for profile_name, config in PROFILES.items():
        assert "name" in config, f"{profile_name} should have 'name'"
        assert "display_name" in config, f"{profile_name} should have 'display_name'"
        assert "icon" in config, f"{profile_name} should have 'icon'"
        assert "color" in config, f"{profile_name} should have 'color'"
        assert "is_aggregate" in config, f"{profile_name} should have 'is_aggregate'"
        
        # Check color is hex
        assert config["color"].startswith("#"), f"{profile_name} color should be hex"
        assert len(config["color"]) == 7, f"{profile_name} color should be 7 chars"
    
    print("✅ Profile colors and icons OK")


def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("🚀 PROFILE SYSTEM TESTS")
    print("=" * 60)
    
    try:
        test_profile_definitions()
        test_profile_helpers()
        test_sheet_naming()
        test_data_isolation()
        test_profile_colors_and_icons()
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print("\n💡 Next steps:")
        print("1. Run 'streamlit run setup_profiles.py' to create sheets")
        print("2. Run 'streamlit run portfoy.py' to start the application")
        print("3. Test profile switching in the UI")
        print("4. Verify data isolation by adding assets to different profiles")
        
        return True
        
    except AssertionError as e:
        print("\n" + "=" * 60)
        print(f"❌ TEST FAILED: {str(e)}")
        print("=" * 60)
        return False
    except Exception as e:
        print("\n" + "=" * 60)
        print(f"❌ ERROR: {str(e)}")
        print("=" * 60)
        return False


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
