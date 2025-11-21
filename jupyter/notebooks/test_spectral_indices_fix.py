"""
Test script to verify the spectral indices fix for missing bands (B6).
This tests the eemont-osi spectralIndices function with a Planet image
that doesn't have B6 (redE2) band.

Run this in the Jupyter container:
docker exec -it gis_jupyter_dev python /usr/src/app/test_spectral_indices_fix.py
"""
import ee
import eemont
import os
import sys

# Add paths
sys.path.insert(0, '/usr/src/app')
sys.path.insert(0, '/usr/src/app/eemont-osi')

print("="*60)
print("Testing Spectral Indices Fix for Missing B6 Band")
print("="*60)

# Initialize GEE
try:
    # Try to initialize with service account
    credential_path = '/usr/src/app/user_id.json'
    if os.path.exists(credential_path):
        credentials = ee.ServiceAccountCredentials(None, credential_path)
        ee.Initialize(credentials, project='remote-sensing-476412')
        print("✅ GEE Initialized with service account")
    else:
        ee.Initialize(project='remote-sensing-476412')
        print("✅ GEE Initialized")
except Exception as e:
    # If already initialized, that's fine
    if "already initialized" in str(e).lower():
        print("✅ GEE already initialized")
    else:
        print(f"⚠️  GEE initialization error: {e}")
        # Try to continue anyway
        try:
            ee.Initialize(project='remote-sensing-476412')
        except:
            pass

# Create a test image similar to the user's setup
# Planet 8-band image with bands: coastal_blue, blue, green1, green, yellow, red, redE1, nir
# But NO redE2 (B6)
test_bands = ['coastal_blue', 'blue', 'green1', 'green', 'yellow', 'red', 'redE1', 'nir']
test_image = ee.Image.constant([0.1] * len(test_bands)).rename(test_bands)

print(f"\n✅ Test image created with bands: {test_bands}")
print(f"   Note: NO 'redE2' or 'B6' band (this is the issue)")

# Convert to ImageCollection (required for eemont-osi)
test_collection = ee.ImageCollection([test_image])

print("\n🧪 Testing spectralIndices with indices that might require B6...")

# Test with the same indices the user is trying
test_indices = [
    'ARVI', 'BAI', 'CRI700', 'EVI', 'ExG', 'ExGR',
    'GEMI', 'GLI', 'GNDVI', 'MSR', 'NDREI', 'NGRDI',
    'NLI', 'OSAVI', 'RDVI', 'RVI', 'SAVI', 'TVI',
    'VIG', 'WDRVI', 'WI2'
]

print(f"   Requested indices: {len(test_indices)} indices")
print(f"   Some indices (like NDREI, CRI700) may require B6 (redE2)")

try:
    print("\n⏳ Calling spectralIndices (this may take a moment)...")
    
    # This should work now with our fix
    result = test_collection.spectralIndices(
        index=test_indices,
        satellite_type='Sentinel',  # This will map redE1 -> B5, but B6 doesn't exist
        G=2.5,
        C1=6.0,
        C2=7.5,
        L=1.0,
        drop=False
    )
    
    print("✅ spectralIndices call completed without error")
    print("⏳ Getting result band names (this is where the error usually occurs)...")
    
    # Try to get the first image and its band names
    result_image = result.first()
    band_names = result_image.bandNames().getInfo()
    
    print(f"\n✅ SUCCESS! Result has {len(band_names)} bands:")
    print(f"   Original bands: {test_bands}")
    print(f"   New indices added: {len(band_names) - len(test_bands)}")
    
    # Show first 15 bands
    if len(band_names) > 15:
        print(f"   First 15 bands: {band_names[:15]}")
        print(f"   ... and {len(band_names) - 15} more")
    else:
        print(f"   All bands: {band_names}")
    
    # Check if B6 is in the result (it shouldn't be)
    if 'B6' in band_names:
        print("⚠️  WARNING: B6 is in the result (unexpected)")
    else:
        print("✅ B6 is NOT in the result (expected - it doesn't exist)")
    
    # Check if the requested indices are present
    found_indices = [idx for idx in test_indices if idx in band_names]
    print(f"\n✅ Found {len(found_indices)}/{len(test_indices)} requested indices")
    
    if len(found_indices) < len(test_indices):
        missing = set(test_indices) - set(found_indices)
        print(f"   Missing indices (may require B6): {missing}")
    
    print("\n" + "="*60)
    print("✅ TEST PASSED - Fix is working correctly!")
    print("="*60)
    
except Exception as e:
    error_msg = str(e)
    print(f"\n❌ ERROR: {type(e).__name__}")
    print(f"   {error_msg}")
    
    if "B6" in error_msg or "Band pattern" in error_msg:
        print("\n🔍 The error is still happening with B6.")
        print("   The issue is that ee_extra is trying to select B6 internally.")
        print("   We need to prevent ee_extra from trying to use B6.")
    elif "Collection.first" in error_msg:
        print("\n🔍 Error in Collection.first - likely in reverse mapping.")
        print("   The reverse mapping is trying to rename B6 back, but B6 doesn't exist.")
    else:
        print(f"\n⚠️  Different error occurred: {type(e).__name__}")
    
    print("\n" + "="*60)
    print("❌ TEST FAILED")
    print("="*60)
    sys.exit(1)
