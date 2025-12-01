#!/usr/bin/env python3
"""
Test script to verify reverse mapping in Docker Jupyter environment.
This mimics the exact pattern from 02p_adding_si_tsfresh_annual_ndvi_evi.ipynb
"""

import sys
import os

# Add paths (matching Docker environment)
sys.path.insert(0, '/usr/src/app/eemont-osi')
sys.path.insert(0, '/usr/src/app/forestry_carbon_arr')

import ee
import eemont

print("="*60)
print("Testing Reverse Mapping in Docker Environment")
print("="*60)

# Initialize Earth Engine (using forestry_carbon_arr method if available)
try:
    from forestry_carbon_arr.core import ForestryCarbonARR
    # Try to use forestry initialization
    forestry = ForestryCarbonARR(config_path='/usr/src/app/notebooks/00_input/korindo.json')
    forestry.initialize_gee()
    print("✅ Earth Engine initialized via ForestryCarbonARR")
except Exception as e:
    print(f"⚠️  Could not initialize via ForestryCarbonARR: {e}")
    print("   Trying direct initialization...")
    try:
        credentials_path = '/usr/src/app/user_id.json'
        if os.path.exists(credentials_path):
            # Use service account credentials
            credentials = ee.ServiceAccountCredentials(None, credentials_path)
            ee.Initialize(credentials)
            print(f"✅ Earth Engine initialized with service account: {credentials_path}")
        else:
            ee.Initialize()
            print("✅ Earth Engine initialized (default)")
    except Exception as e2:
        print(f"❌ Failed to initialize Earth Engine: {e2}")
        print("   Please ensure GEE is initialized in your notebook first")
        sys.exit(1)

# Reload eemont to ensure latest changes are loaded
import importlib
importlib.reload(eemont)
print("✅ eemont-osi module reloaded")

def test_reverse_mapping():
    """Main test function"""
    # Create test image collection with OSI-style bands (matching 02p notebook)
    print("\n" + "="*60)
    print("STEP 1: Create test image collection with OSI-style bands")
    print("="*60)

    def create_test_image():
        """Create a test image with OSI-style band names"""
        # Create bands matching the pattern from 02p notebook
        osi_bands = ['blue', 'green', 'nir', 'red', 'redE1', 'redE2', 'redE3', 'redE4', 'swir1', 'swir2']
        
        # Start with first band
        img = ee.Image.constant(0.5).rename(['blue'])
        
        # Add remaining bands
        for band in osi_bands[1:]:
            img = img.addBands(ee.Image.constant(0.5).rename([band]))
        
        return img

    test_img = create_test_image()
    test_col = ee.ImageCollection([test_img])

    print(f"📋 Original bands: {test_img.bandNames().getInfo()}")

    # Test spectralIndices with satellite_type='Sentinel' and drop=False
    print("\n" + "="*60)
    print("STEP 2: Compute spectral indices with satellite_type='Sentinel', drop=False")
    print("="*60)

    try:
        ee_col_indices = test_col.spectralIndices(
            index=['EVI', 'GNDVI', 'NDVI', 'SAVI', 'NBR'],
            satellite_type='Sentinel',  # Maps OSI-style names to standard Sentinel names
            G=2.5,
            C1=6.0,
            C2=7.5,
            L=1.0,
            drop=False  # Keep original bands
        )
        
        print("✅ spectralIndices computation completed")
        
        # Check the result
        print("\n" + "="*60)
        print("STEP 3: Check result bands")
        print("="*60)
        
        result_bands = ee_col_indices.first().bandNames().getInfo()
        print(f"📋 Result bands: {result_bands}")
        
        # Analyze the result
        sentinel_bands = ['B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B8', 'B8A', 'B11', 'B12']
        osi_bands = ['blue', 'green', 'red', 'redE1', 'redE2', 'redE3', 'nir', 'redE4', 'swir1', 'swir2']
        spectral_indices = ['EVI', 'GNDVI', 'NDVI', 'SAVI', 'NBR']
        
        sentinel_found = [b for b in result_bands if b in sentinel_bands]
        osi_found = [b for b in result_bands if b in osi_bands]
        indices_found = [b for b in result_bands if b in spectral_indices]
        
        print(f"\n🔍 Analysis:")
        print(f"   Sentinel bands found: {sentinel_found}")
        print(f"   OSI bands found: {osi_found}")
        print(f"   Spectral indices found: {indices_found}")
        
        # Determine success/failure
        print("\n" + "="*60)
        print("RESULT")
        print("="*60)
        
        if sentinel_found:
            print(f"❌ FAILED: Found Sentinel bands that should have been reverse-mapped:")
            print(f"   {sentinel_found}")
            print(f"\n   Expected: OSI names (blue, green, red, nir, swir1, swir2)")
            print(f"   Got: Sentinel names (B2, B3, B4, etc.)")
            return False
        elif osi_found:
            print(f"✅ SUCCESS: Bands were reverse-mapped to OSI names!")
            print(f"   Found OSI bands: {osi_found}")
            print(f"   Found spectral indices: {indices_found}")
            
            # Check if we have the expected bands
            expected_osi = ['blue', 'green', 'red', 'nir', 'swir1', 'swir2']
            missing_osi = [b for b in expected_osi if b not in osi_found]
            if missing_osi:
                print(f"   ⚠️  WARNING: Some expected OSI bands missing: {missing_osi}")
            else:
                print(f"   ✅ All expected OSI bands present!")
            
            return True
        else:
            print(f"⚠️  WARNING: No OSI bands found, but no Sentinel bands either.")
            print(f"   This might indicate an issue with the mapping logic.")
            return False
            
    except Exception as e:
        print(f"\n❌ ERROR during computation: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_reverse_mapping()
    sys.exit(0 if success else 1)
