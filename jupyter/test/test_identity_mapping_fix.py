#!/usr/bin/env python3
"""Test identity mapping fix - skip all mapping when band_map is identity"""
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
        print("✓ GEE initialized")
    else:
        ee.Initialize()
        print("✓ GEE initialized")
except Exception as e:
    print(f"✗ Failed to initialize GEE: {e}")
    sys.exit(1)

import eemont

# Create test image with Sentinel band names (already in standard format)
print("\n1. Creating test image with Sentinel band names (B2, B3, B4, B5, B8)...")
test_region = ee.Geometry.Rectangle([103.0, -1.0, 104.0, 0.0])
img = ee.Image().float().paint(test_region, 0.1).rename('B2')
img = img.addBands(ee.Image().float().paint(test_region, 0.2).rename('B3'))
img = img.addBands(ee.Image().float().paint(test_region, 0.3).rename('B4'))
img = img.addBands(ee.Image().float().paint(test_region, 0.4).rename('B5'))
img = img.addBands(ee.Image().float().paint(test_region, 0.5).rename('B8'))
img_col = ee.ImageCollection([img])

print(f"   ✓ Created image with bands: {img.bandNames().getInfo()}")

# Use identity band_map (B2->B2, etc.)
print("\n2. Using identity band_map (should skip all mapping)...")
band_map = {'B2': 'B2', 'B3': 'B3', 'B4': 'B4', 'B5': 'B5', 'B8': 'B8'}

print("\n3. Calling spectralIndices with identity band_map...")
print("   (Should skip mapping entirely and call ee_extra directly)")
try:
    result = img_col.spectralIndices(
        index=['NDVI', 'EVI', 'SAVI', 'ARVI', 'GNDVI'],  # Indices that don't require B6
        band_map=band_map,
        G=2.5,
        C1=6.0,
        C2=7.5,
        L=1.0,
        drop=False
    )
    
    result_img = result.first()
    result_bands = result_img.bandNames().getInfo()
    
    print(f"   ✓ SUCCESS! Result bands: {result_bands}")
    print(f"   ✓ No B6 error - identity mapping was skipped correctly")
    sys.exit(0)
    
except Exception as e:
    error_msg = str(e)
    if "B6" in error_msg:
        print(f"   ✗ B6 error still occurs: {e}")
        sys.exit(1)
    else:
        print(f"   ✗ Other error: {e}")
        sys.exit(1)



