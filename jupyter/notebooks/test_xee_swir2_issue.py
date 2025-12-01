#!/usr/bin/env python3
"""
Test to reproduce and fix the swir2 error in xee inspection
"""

import sys
import os

sys.path.insert(0, '/usr/src/app/eemont-osi')
sys.path.insert(0, '/usr/src/app/forestry_carbon_arr')

import ee
import eemont
import xee
import xarray as xr

print("="*60)
print("Testing xee swir2 error")
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

# Create test scenario matching notebook
print("\n" + "="*60)
print("STEP 1: Create test collection")
print("="*60)

def create_test_image():
    osi_bands = ['blue', 'green', 'nir', 'red', 'redE1', 'redE2', 'redE3', 'redE4', 'swir1', 'swir2']
    img = ee.Image.constant(0.5).rename(['blue'])
    for band in osi_bands[1:]:
        img = img.addBands(ee.Image.constant(0.5).rename([band]))
    return img

test_img = create_test_image()
test_col = ee.ImageCollection([test_img.set('year', 2020).set('system:time_start', ee.Date.fromYMD(2020, 12, 31).millis())])

# Compute spectral indices
print("\n" + "="*60)
print("STEP 2: Compute spectral indices")
print("="*60)

ee_col_indices = test_col.spectralIndices(
    index=['EVI', 'GNDVI', 'NDVI', 'SAVI', 'NBR'],
    satellite_type='Sentinel',
    drop=False
)

print(f"📋 After spectralIndices: {ee_col_indices.first().bandNames().getInfo()}")

# Create FCD collection
fcd_img = ee.Image.constant(50).rename('FCD').set('year', 2020)
fcd_col = ee.ImageCollection([fcd_img])

# Test current merge function
print("\n" + "="*60)
print("STEP 3: Test current merge function (with copyProperties)")
print("="*60)

def merge_with_fcd_current(img):
    """Current merge function - uses copyProperties"""
    year = img.get('year')
    si_selected = img.select(['EVI', 'GNDVI', 'NDVI', 'SAVI', 'NBR'])
    fcd_img = fcd_col.filter(ee.Filter.eq('year', year)).first().select('FCD')
    merged = si_selected.addBands(fcd_img)
    return merged.copyProperties(img, img.propertyNames())

fcd_col_merged_current = ee_col_indices.map(merge_with_fcd_current)
print(f"📋 After merge (current): {fcd_col_merged_current.first().bandNames().getInfo()}")

# Check properties
first_img = ee.Image(fcd_col_merged_current.first())
props = first_img.propertyNames().getInfo()
print(f"📋 Properties: {props}")

# Try xee inspection
print("\n" + "="*60)
print("STEP 4: Try xee inspection with current merge")
print("="*60)

try:
    # This is what xee does internally - it tries to get info about the collection
    info = fcd_col_merged_current.size().getInfo()
    print(f"   Collection size: {info}")
    
    # Try to open as xarray (this will trigger xee inspection)
    print("   Attempting xr.open_dataset...")
    ds = xr.open_dataset(
        fcd_col_merged_current,
        engine='ee',
        crs='EPSG:4326',
        scale=1000
    )
    print("   ✅ SUCCESS: xee inspection passed!")
except Exception as e:
    print(f"   ❌ ERROR: {e}")
    error_str = str(e)
    if 'swir2' in error_str.lower():
        print(f"   ⚠️  Found 'swir2' in error - this is the issue!")
    
# Test fixed merge function
print("\n" + "="*60)
print("STEP 5: Test fixed merge function (without copyProperties)")
print("="*60)

def merge_with_fcd_fixed(img):
    """Fixed merge function - only copies essential properties"""
    year = img.get('year')
    si_selected = img.select(['EVI', 'GNDVI', 'NDVI', 'SAVI', 'NBR'])
    fcd_filtered = fcd_col.filter(ee.Filter.eq('year', year))
    fcd_img = ee.Algorithms.If(
        fcd_filtered.size().gt(0),
        fcd_filtered.first().select('FCD'),
        ee.Image.constant(0).rename('FCD')
    )
    merged = si_selected.addBands(ee.Image(fcd_img))
    # Only copy essential properties, not all properties
    result = merged.set('year', year).set('system:time_start', img.get('system:time_start'))
    return result

fcd_col_merged_fixed = ee_col_indices.map(merge_with_fcd_fixed)
print(f"📋 After merge (fixed): {fcd_col_merged_fixed.first().bandNames().getInfo()}")

# Check properties
first_img_fixed = ee.Image(fcd_col_merged_fixed.first())
props_fixed = first_img_fixed.propertyNames().getInfo()
print(f"📋 Properties: {props_fixed}")

# Try xee inspection with fixed merge
print("\n" + "="*60)
print("STEP 6: Try xee inspection with fixed merge")
print("="*60)

try:
    info = fcd_col_merged_fixed.size().getInfo()
    print(f"   Collection size: {info}")
    
    print("   Attempting xr.open_dataset...")
    ds = xr.open_dataset(
        fcd_col_merged_fixed,
        engine='ee',
        crs='EPSG:4326',
        scale=1000
    )
    print("   ✅ SUCCESS: xee inspection passed with fixed merge!")
except Exception as e:
    print(f"   ❌ ERROR: {e}")

print("\n" + "="*60)
print("TEST COMPLETE")
print("="*60)

