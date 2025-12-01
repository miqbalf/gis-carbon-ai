#!/usr/bin/env python3
"""
Diagnostic script to identify root cause of swir2 error in xee inspection
"""

import sys
import os

sys.path.insert(0, '/usr/src/app/eemont-osi')
sys.path.insert(0, '/usr/src/app/forestry_carbon_arr')

import ee
import eemont

print("="*60)
print("Diagnosing swir2 error in xee inspection")
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

# Simulate the notebook scenario
print("\n" + "="*60)
print("STEP 1: Create test collection with OSI bands")
print("="*60)

def create_test_image():
    osi_bands = ['blue', 'green', 'nir', 'red', 'redE1', 'redE2', 'redE3', 'redE4', 'swir1', 'swir2']
    img = ee.Image.constant(0.5).rename(['blue'])
    for band in osi_bands[1:]:
        img = img.addBands(ee.Image.constant(0.5).rename([band]))
    return img

test_img = create_test_image()
test_col = ee.ImageCollection([test_img])

print(f"📋 Original bands: {test_img.bandNames().getInfo()}")

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

# Simulate merge with FCD
print("\n" + "="*60)
print("STEP 3: Simulate merge with FCD (using current merge function)")
print("="*60)

# Create a dummy FCD collection
fcd_img = ee.Image.constant(50).rename('FCD').set('year', 2020)
fcd_col = ee.ImageCollection([fcd_img])

def merge_with_fcd_current(img):
    """Current merge function from notebook"""
    year = img.get('year')
    si_selected = img.select(['EVI', 'GNDVI', 'NDVI', 'SAVI', 'NBR'])
    fcd_img = fcd_col.filter(ee.Filter.eq('year', year)).first().select('FCD')
    merged = si_selected.addBands(fcd_img)
    return merged.copyProperties(img, img.propertyNames())

# Set year property
ee_col_indices = ee_col_indices.map(lambda img: img.set('year', 2020))
fcd_col_merged = ee_col_indices.map(merge_with_fcd_current)

print(f"📋 After merge: {fcd_col_merged.first().bandNames().getInfo()}")

# Check properties
print("\n" + "="*60)
print("STEP 4: Check properties that might reference swir2")
print("="*60)

try:
    first_img = ee.Image(fcd_col_merged.first())
    props = first_img.propertyNames().getInfo()
    print(f"📋 Properties: {props}")
    
    # Check for problematic properties
    problematic_props = ['system:band_names', 'band_names', 'original_bands']
    for prop in problematic_props:
        if prop in props:
            prop_value = first_img.get(prop).getInfo()
            print(f"   ⚠️  Found property '{prop}': {prop_value}")
            if isinstance(prop_value, (list, str)) and 'swir2' in str(prop_value):
                print(f"      ⚠️  WARNING: Property '{prop}' contains 'swir2' reference!")
except Exception as e:
    print(f"   Error checking properties: {e}")

# Test xee inspection simulation
print("\n" + "="*60)
print("STEP 5: Simulate xee inspection (check all images)")
print("="*60)

try:
    # Try to get info about all images (similar to what xee does)
    size = fcd_col_merged.size().getInfo()
    print(f"   Collection size: {size}")
    
    # Try to get band names from all images
    def get_bands(img):
        return img.bandNames()
    
    all_bands = fcd_col_merged.map(get_bands).aggregate_array('bandNames').getInfo()
    print(f"   ✅ Successfully got band names from all images")
    print(f"   Band names: {all_bands}")
    
except Exception as e:
    print(f"   ❌ ERROR during inspection: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
print("DIAGNOSIS COMPLETE")
print("="*60)

