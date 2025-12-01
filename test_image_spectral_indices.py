#!/usr/bin/env python3
"""
Test ee.Image.spectralIndices with reverse mapping (for custom images like PlanetScope)
"""

import sys
import os

sys.path.insert(0, '/usr/src/app/eemont-osi')
sys.path.insert(0, '/usr/src/app/forestry_carbon_arr')

import ee
import eemont

print("="*60)
print("Testing ee.Image.spectralIndices with reverse mapping")
print("="*60)

# Initialize Earth Engine
try:
    from forestry_carbon_arr.core import ForestryCarbonARR
    forestry = ForestryCarbonARR(config_path='/usr/src/app/notebooks/00_input/korindo.json')
    forestry.initialize_gee()
    print("✅ Earth Engine initialized")
except Exception as e:
    print(f"⚠️  Could not initialize via ForestryCarbonARR: {e}")
    try:
        credentials_path = '/usr/src/app/user_id.json'
        if os.path.exists(credentials_path):
            credentials = ee.ServiceAccountCredentials(None, credentials_path)
            ee.Initialize(credentials)
            print(f"✅ Earth Engine initialized with service account")
        else:
            ee.Initialize()
            print("✅ Earth Engine initialized (default)")
    except Exception as e2:
        print(f"❌ Failed to initialize: {e2}")
        sys.exit(1)

# Reload eemont
import importlib
importlib.reload(eemont)
print("✅ eemont-osi module reloaded")

def test_image_spectral_indices():
    """Test function"""
    # Create test image with OSI-style bands (like PlanetScope)
    print("\n" + "="*60)
    print("STEP 1: Create test image with OSI-style bands")
    print("="*60)

    def create_test_image():
        osi_bands = ['blue', 'green', 'nir', 'red', 'redE1', 'redE2', 'redE3', 'redE4', 'swir1', 'swir2']
        img = ee.Image.constant(0.5).rename(['blue'])
        for band in osi_bands[1:]:
            img = img.addBands(ee.Image.constant(0.5).rename([band]))
        return img

    test_img = create_test_image()
    print(f"📋 Original bands: {test_img.bandNames().getInfo()}")

    # Test ee.Image.spectralIndices
    print("\n" + "="*60)
    print("STEP 2: Compute spectral indices on ee.Image with satellite_type='Sentinel'")
    print("="*60)

    try:
        result_img = test_img.spectralIndices(
            index=['EVI', 'GNDVI', 'NDVI', 'SAVI', 'NBR'],
            satellite_type='Sentinel',
            G=2.5,
            C1=6.0,
            C2=7.5,
            L=1.0,
            drop=False
        )
        
        print("✅ spectralIndices computation completed")
        
        # Check result
        print("\n" + "="*60)
        print("STEP 3: Check result bands")
        print("="*60)
        
        # Ensure result_img is an ee.Image
        if not isinstance(result_img, ee.Image):
            result_img = ee.Image(result_img)
        result_bands = result_img.bandNames().getInfo()
        print(f"📋 Result bands: {result_bands}")
        
        # Analyze
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
        
        print("\n" + "="*60)
        print("RESULT")
        print("="*60)
        
        if sentinel_found:
            print(f"❌ FAILED: Found Sentinel bands: {sentinel_found}")
            return False
        elif osi_found:
            print(f"✅ SUCCESS: Bands reverse-mapped to OSI names!")
            print(f"   OSI bands: {osi_found}")
            print(f"   Spectral indices: {indices_found}")
            return True
        else:
            print(f"⚠️  WARNING: No OSI bands found")
            return False
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_image_spectral_indices()
    sys.exit(0 if success else 1)
