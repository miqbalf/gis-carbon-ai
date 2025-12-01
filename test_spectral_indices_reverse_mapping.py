#!/usr/bin/env python3
"""
Test script to verify reverse mapping in eemont-osi spectralIndices method.

This script tests:
1. ImageCollection.spectralIndices with satellite_type='Sentinel' and drop=False
2. ee.Image.spectralIndices with satellite_type='Sentinel' and drop=False
3. Verifies that bands are reverse-mapped from Sentinel names (B2, B3, etc.) to OSI names (blue, green, etc.)

Usage:
    python test_spectral_indices_reverse_mapping.py
"""

import os
import sys
import ee
import eemont

# Add eemont-osi to path
sys.path.insert(0, '/usr/src/app/eemont-osi')

# Initialize Earth Engine
try:
    ee.Initialize()
    print("✅ Earth Engine initialized")
except Exception as e:
    print(f"❌ Failed to initialize Earth Engine: {e}")
    sys.exit(1)

def test_imagecollection_spectral_indices():
    """Test ImageCollection.spectralIndices with reverse mapping"""
    print("\n" + "="*60)
    print("TEST 1: ImageCollection.spectralIndices with satellite_type='Sentinel'")
    print("="*60)
    
    # Create a test image collection with OSI-style band names
    # Simulate the pattern from 02p notebook
    test_bands = ['blue', 'green', 'nir', 'red', 'redE1', 'redE2', 'redE3', 'redE4', 'swir1', 'swir2']
    
    # Create a simple test image with OSI-style bands
    def create_test_image():
        # Create dummy bands (using constant values for testing)
        img = ee.Image.constant(0.5).rename(['blue'])
        for band in test_bands[1:]:
            img = img.addBands(ee.Image.constant(0.5).rename([band]))
        return img
    
    test_img = create_test_image()
    test_col = ee.ImageCollection([test_img])
    
    print(f"📋 Original bands: {test_img.bandNames().getInfo()}")
    
    # Compute spectral indices with satellite_type='Sentinel' and drop=False
    try:
        result_col = test_col.spectralIndices(
            index=['EVI', 'GNDVI', 'NDVI', 'SAVI', 'NBR'],
            satellite_type='Sentinel',
            G=2.5,
            C1=6.0,
            C2=7.5,
            L=1.0,
            drop=False
        )
        
        # Check the result
        result_img = ee.Image(result_col.first())
        result_bands = result_img.bandNames().getInfo()
        
        print(f"\n📋 Result bands: {result_bands}")
        
        # Check if reverse mapping worked
        sentinel_bands = ['B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B8', 'B8A', 'B11', 'B12']
        osi_bands = ['blue', 'green', 'red', 'redE1', 'redE2', 'redE3', 'nir', 'redE4', 'swir1', 'swir2']
        
        sentinel_found = [b for b in result_bands if b in sentinel_bands]
        osi_found = [b for b in result_bands if b in osi_bands]
        
        print(f"\n🔍 Analysis:")
        print(f"   Sentinel bands found: {sentinel_found}")
        print(f"   OSI bands found: {osi_found}")
        print(f"   Spectral indices: {[b for b in result_bands if b not in sentinel_bands and b not in osi_bands]}")
        
        if sentinel_found:
            print(f"\n❌ FAILED: Found Sentinel bands that should have been reverse-mapped: {sentinel_found}")
            return False
        elif osi_found:
            print(f"\n✅ SUCCESS: Bands were reverse-mapped to OSI names!")
            print(f"   Expected OSI bands: {osi_bands}")
            print(f"   Found OSI bands: {osi_found}")
            return True
        else:
            print(f"\n⚠️  WARNING: No OSI bands found, but no Sentinel bands either. Check result.")
            return False
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_image_spectral_indices():
    """Test ee.Image.spectralIndices with reverse mapping"""
    print("\n" + "="*60)
    print("TEST 2: ee.Image.spectralIndices with satellite_type='Sentinel'")
    print("="*60)
    
    # Create a test image with OSI-style band names (like PlanetScope)
    test_bands = ['blue', 'green', 'nir', 'red', 'redE1', 'redE2', 'redE3', 'redE4', 'swir1', 'swir2']
    
    def create_test_image():
        img = ee.Image.constant(0.5).rename(['blue'])
        for band in test_bands[1:]:
            img = img.addBands(ee.Image.constant(0.5).rename([band]))
        return img
    
    test_img = create_test_image()
    
    print(f"📋 Original bands: {test_img.bandNames().getInfo()}")
    
    # Compute spectral indices with satellite_type='Sentinel' and drop=False
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
        
        result_bands = result_img.bandNames().getInfo()
        
        print(f"\n📋 Result bands: {result_bands}")
        
        # Check if reverse mapping worked
        sentinel_bands = ['B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B8', 'B8A', 'B11', 'B12']
        osi_bands = ['blue', 'green', 'red', 'redE1', 'redE2', 'redE3', 'nir', 'redE4', 'swir1', 'swir2']
        
        sentinel_found = [b for b in result_bands if b in sentinel_bands]
        osi_found = [b for b in result_bands if b in osi_bands]
        
        print(f"\n🔍 Analysis:")
        print(f"   Sentinel bands found: {sentinel_found}")
        print(f"   OSI bands found: {osi_found}")
        print(f"   Spectral indices: {[b for b in result_bands if b not in sentinel_bands and b not in osi_bands]}")
        
        if sentinel_found:
            print(f"\n❌ FAILED: Found Sentinel bands that should have been reverse-mapped: {sentinel_found}")
            return False
        elif osi_found:
            print(f"\n✅ SUCCESS: Bands were reverse-mapped to OSI names!")
            print(f"   Expected OSI bands: {osi_bands}")
            print(f"   Found OSI bands: {osi_found}")
            return True
        else:
            print(f"\n⚠️  WARNING: No OSI bands found, but no Sentinel bands either. Check result.")
            return False
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("🧪 Testing eemont-osi reverse mapping for spectralIndices")
    print("="*60)
    
    results = []
    
    # Test 1: ImageCollection
    results.append(("ImageCollection.spectralIndices", test_imagecollection_spectral_indices()))
    
    # Test 2: ee.Image
    results.append(("ee.Image.spectralIndices", test_image_spectral_indices()))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status}: {test_name}")
        if not passed:
            all_passed = False
    
    print("="*60)
    if all_passed:
        print("✅ All tests passed!")
        return 0
    else:
        print("❌ Some tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())

