#!/usr/bin/env python3
"""
Test to identify why xee is encountering swir2 reference
"""

import sys
import os

sys.path.insert(0, '/usr/src/app/eemont-osi')
sys.path.insert(0, '/usr/src/app/forestry_carbon_arr')

import ee
import eemont

print("="*60)
print("Testing xee inspection issue")
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

# Create test scenario - simulate the actual notebook scenario
print("\n" + "="*60)
print("STEP 1: Create test collection with OSI bands")
print("="*60)

def create_test_image(year):
    osi_bands = ['blue', 'green', 'nir', 'red', 'redE1', 'redE2', 'redE3', 'redE4', 'swir1', 'swir2']
    img = ee.Image.constant(0.5).rename(['blue'])
    for band in osi_bands[1:]:
        img = img.addBands(ee.Image.constant(0.5).rename([band]))
    return img.set('year', year).set('system:time_start', ee.Date.fromYMD(year, 12, 31).millis())

# Create collection with multiple years (like the notebook)
test_col = ee.ImageCollection([create_test_image(2020), create_test_image(2021), create_test_image(2022)])

print(f"📋 Original bands: {test_col.first().bandNames().getInfo()}")

# Compute spectral indices
print("\n" + "="*60)
print("STEP 2: Compute spectral indices")
print("="*60)

ee_col_indices = test_col.spectralIndices(
    index=['EVI', 'GNDVI', 'NDVI', 'SAVI', 'NBR'],
    satellite_type='Sentinel',
    drop=False
)

result_bands = ee_col_indices.first().bandNames().getInfo()
print(f"📋 After spectralIndices: {result_bands}")

# Create FCD collection
fcd_col = ee.ImageCollection([
    ee.Image.constant(50).rename('FCD').set('year', 2020).set('system:time_start', ee.Date.fromYMD(2020, 12, 31).millis()),
    ee.Image.constant(50).rename('FCD').set('year', 2021).set('system:time_start', ee.Date.fromYMD(2021, 12, 31).millis()),
    ee.Image.constant(50).rename('FCD').set('year', 2022).set('system:time_start', ee.Date.fromYMD(2022, 12, 31).millis()),
])

# Test merge function
print("\n" + "="*60)
print("STEP 3: Test merge function")
print("="*60)

def merge_with_fcd(img):
    """Merge spectral indices with FCD"""
    year = img.get('year')
    si_selected = img.select(['EVI', 'GNDVI', 'NDVI', 'SAVI', 'NBR'])
    fcd_filtered = fcd_col.filter(ee.Filter.eq('year', year))
    fcd_img = ee.Algorithms.If(
        fcd_filtered.size().gt(0),
        fcd_filtered.first().select('FCD'),
        ee.Image.constant(0).rename('FCD')
    )
    merged = si_selected.addBands(ee.Image(fcd_img))
    result = merged.set('year', year).set('system:time_start', img.get('system:time_start'))
    return result

fcd_col_merged = ee_col_indices.map(merge_with_fcd)

print(f"📋 After merge: {fcd_col_merged.first().bandNames().getInfo()}")

# Test what xee does - it uses reduceColumns to get metadata
print("\n" + "="*60)
print("STEP 4: Simulate xee inspection (reduceColumns)")
print("="*60)

try:
    # This is what xee does internally
    size = fcd_col_merged.size().getInfo()
    print(f"   Collection size: {size}")
    
    # xee uses reduceColumns to get properties from all images
    # Let's test this directly
    def get_props(img):
        return ee.Feature(None, {
            'id': img.get('system:id'),
            'time': img.get('system:time_start'),
            'year': img.get('year')
        })
    
    props_collection = fcd_col_merged.map(get_props)
    props_list = props_collection.getInfo()
    print(f"   ✅ Successfully got properties from all images")
    print(f"   Properties: {props_list}")
    
except Exception as e:
    print(f"   ❌ ERROR during reduceColumns simulation: {e}")
    error_str = str(e)
    if 'swir2' in error_str.lower():
        print(f"   ⚠️  Found 'swir2' in error - this is the issue!")
    
    # Try to identify which image is problematic
    print("\n   🔍 Trying to identify problematic image...")
    try:
        for i in range(size):
            img = ee.Image(fcd_col_merged.toList(1, i).get(0))
            bands = img.bandNames().getInfo()
            print(f"      Image {i}: {len(bands)} bands - {bands}")
    except Exception as e2:
        print(f"      Error checking individual images: {e2}")

# Test with explicit band selection before merge
print("\n" + "="*60)
print("STEP 5: Test with explicit band selection (force clean images)")
print("="*60)

def merge_with_fcd_clean(img):
    """Merge with explicit band selection to break computation graph"""
    year = img.get('year')
    
    # Force select only the bands we want - this breaks the computation graph
    si_bands = ['EVI', 'GNDVI', 'NDVI', 'SAVI', 'NBR']
    si_selected = img.select(si_bands)
    
    # Get FCD
    fcd_filtered = fcd_col.filter(ee.Filter.eq('year', year))
    fcd_img = fcd_filtered.size().gt(0).And(
        fcd_filtered.first().select('FCD')
    ).Or(
        ee.Image.constant(0).rename('FCD')
    )
    
    # Create completely new image with only the bands we want
    merged = si_selected.addBands(ee.Image(fcd_img))
    
    # Only set essential properties
    result = merged.set('year', year).set('system:time_start', img.get('system:time_start'))
    
    return result

fcd_col_merged_clean = ee_col_indices.map(merge_with_fcd_clean)

try:
    size = fcd_col_merged_clean.size().getInfo()
    print(f"   Collection size: {size}")
    
    # Test reduceColumns
    props_collection = fcd_col_merged_clean.map(get_props)
    props_list = props_collection.getInfo()
    print(f"   ✅ Successfully got properties with clean merge")
    
except Exception as e:
    print(f"   ❌ ERROR with clean merge: {e}")

print("\n" + "="*60)
print("TEST COMPLETE")
print("="*60)

