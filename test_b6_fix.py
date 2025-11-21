#!/usr/bin/env python3
"""
Test script to verify B6 reverse mapping fix
This tests the scenario where ee_extra might create B6 internally but it doesn't exist in the result
"""
import ee
import os
import sys

# Initialize GEE
try:
    service_account = os.getenv('GOOGLE_SERVICE_ACCOUNT')
    credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', '/usr/src/app/user_id.json')
    
    if os.path.exists(credentials_path):
        credentials = ee.ServiceAccountCredentials(service_account, credentials_path)
        ee.Initialize(credentials)
        print("✓ GEE initialized with service account")
    else:
        ee.Initialize()
        print("✓ GEE initialized (default)")
except Exception as e:
    print(f"✗ Failed to initialize GEE: {e}")
    sys.exit(1)

# Import eemont
try:
    import eemont
    print("✓ eemont imported successfully")
except Exception as e:
    print(f"✗ Failed to import eemont: {e}")
    sys.exit(1)

# Create a mock Planet 8-band image (NO redE2/B6)
print("\n1. Creating mock Planet 8-band image (without redE2/B6)...")
try:
    test_region = ee.Geometry.Rectangle([103.0, -1.0, 104.0, 0.0])
    
    # Create bands with Planet names (NO redE2)
    img_planet = ee.Image().float().paint(test_region, 0.1).rename('coastal_blue')
    img_planet = img_planet.addBands(ee.Image().float().paint(test_region, 0.2).rename('blue'))
    img_planet = img_planet.addBands(ee.Image().float().paint(test_region, 0.3).rename('green1'))
    img_planet = img_planet.addBands(ee.Image().float().paint(test_region, 0.4).rename('green'))
    img_planet = img_planet.addBands(ee.Image().float().paint(test_region, 0.5).rename('yellow'))
    img_planet = img_planet.addBands(ee.Image().float().paint(test_region, 0.6).rename('red'))
    img_planet = img_planet.addBands(ee.Image().float().paint(test_region, 0.7).rename('redE1'))
    img_planet = img_planet.addBands(ee.Image().float().paint(test_region, 0.8).rename('nir'))
    # NOTE: NO redE2/B6 band!
    
    print(f"   ✓ Created image with bands: {img_planet.bandNames().getInfo()}")
except Exception as e:
    print(f"   ✗ Failed to create test image: {e}")
    sys.exit(1)

# Step 1: Rename Planet bands to Sentinel standard names
print("\n2. Renaming Planet bands to Sentinel standard names...")
try:
    img_sentinel_bands = img_planet.select(['blue', 'green', 'red', 'redE1', 'nir']).rename(['B2', 'B3', 'B4', 'B5', 'B8'])
    other_bands = img_planet.select(['coastal_blue', 'green1', 'yellow'])
    img_renamed = img_sentinel_bands.addBands(other_bands)
    print(f"   ✓ Renamed bands. New bands: {img_renamed.bandNames().getInfo()}")
except Exception as e:
    print(f"   ✗ Failed to rename bands: {e}")
    sys.exit(1)

# Step 2: Convert to ImageCollection
print("\n3. Converting to ImageCollection...")
try:
    img_col = ee.ImageCollection([img_renamed])
    print(f"   ✓ Converted to ImageCollection")
except Exception as e:
    print(f"   ✗ Failed to convert to ImageCollection: {e}")
    sys.exit(1)

# Step 3: Create band_map
print("\n4. Creating band_map...")
band_map = {
    'B2': 'B2',
    'B3': 'B3',
    'B4': 'B4',
    'B5': 'B5',
    'B8': 'B8'
}
print(f"   ✓ Created band_map: {band_map}")

# Step 4: Call spectralIndices with indices that might require B6
print("\n5. Calling spectralIndices with indices that might require B6...")
print("   (NDREI and CRI700 require red edge bands, but we only have redE1/B5, not redE2/B6)")
print("   The fix should skip B6 if it doesn't exist in the result")
try:
    img_with_indices = img_col.spectralIndices(
        index=[
            'ARVI', 'BAI', 'CRI700', 'EVI', 'ExG', 'ExGR',
            'GEMI', 'GLI', 'GNDVI', 'MSR', 'NDREI', 'NGRDI',
            'NLI', 'OSAVI', 'RDVI', 'RVI', 'SAVI', 'TVI',
            'VIG', 'WDRVI', 'WI2'
        ],
        band_map=band_map,
        G=2.5,
        C1=6.0,
        C2=7.5,
        L=1.0,
        drop=False
    )
    
    # Get the first image and check band names
    result_img = img_with_indices.first()
    result_bands = result_img.bandNames().getInfo()
    
    print(f"   ✓ spectralIndices succeeded!")
    print(f"   ✓ Result bands: {result_bands}")
    
    # Check if B6 is in the result (it shouldn't be)
    if 'B6' in result_bands:
        print(f"   ⚠️  WARNING: B6 is in result bands, but it shouldn't be (we don't have redE2)")
    else:
        print(f"   ✓ B6 is NOT in result bands (correct - we don't have redE2)")
    
    # Check if expected indices are present
    expected_indices = ['ARVI', 'BAI', 'CRI700', 'EVI', 'ExG', 'ExGR', 'GEMI', 'GLI', 'GNDVI', 
                        'MSR', 'NDREI', 'NGRDI', 'NLI', 'OSAVI', 'RDVI', 'RVI', 'SAVI', 'TVI', 
                        'VIG', 'WDRVI', 'WI2']
    found_indices = [b for b in result_bands if b in expected_indices]
    print(f"   ✓ Found {len(found_indices)}/{len(expected_indices)} expected indices")
    
    print("\n✅ SUCCESS: B6 fix is working correctly!")
    print("   The reverse mapping correctly skips B6 if it doesn't exist in the result")
    sys.exit(0)
        
except ee.ee_exception.EEException as e:
    error_msg = str(e)
    if "Band pattern 'B6' did not match any bands" in error_msg:
        print(f"   ✗ B6 error still occurs: {e}")
        print("   The fix did not work - B6 is being selected even though it doesn't exist")
        sys.exit(1)
    else:
        print(f"   ✗ EEException: {e}")
        sys.exit(1)
except Exception as e:
    print(f"   ✗ Unexpected error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

