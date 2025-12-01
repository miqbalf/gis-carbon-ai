#!/usr/bin/env python3
"""
Test the full workflow from the notebook to identify the root cause
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
print("Testing full notebook workflow")
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

# Simulate the notebook workflow
print("\n" + "="*60)
print("STEP 1: Load collection (simulate ee_col_year_median)")
print("="*60)

# Create a test collection similar to the notebook
def create_test_image(year):
    osi_bands = ['blue', 'green', 'nir', 'red', 'redE1', 'redE2', 'redE3', 'redE4', 'swir1', 'swir2']
    img = ee.Image.constant(0.5).rename(['blue'])
    for band in osi_bands[1:]:
        img = img.addBands(ee.Image.constant(0.5).rename([band]))
    return img.set('year', year).set('system:time_start', ee.Date.fromYMD(year, 12, 31).millis())

# Create collection with 11 years (like the notebook)
years = [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]
ee_col_year_median = ee.ImageCollection([create_test_image(y) for y in years])

print(f"📋 Collection size: {ee_col_year_median.size().getInfo()}")
print(f"📋 First image bands: {ee_col_year_median.first().bandNames().getInfo()}")

# Compute spectral indices
print("\n" + "="*60)
print("STEP 2: Compute spectral indices")
print("="*60)

ee_col_indices = ee_col_year_median.spectralIndices(
    index=['EVI', 'GNDVI', 'NDVI', 'SAVI', 'NBR'],
    satellite_type='Sentinel',
    drop=False
)

result_bands = ee_col_indices.first().bandNames().getInfo()
print(f"📋 After spectralIndices: {result_bands}")

# Clean collection - SIMPLER APPROACH
print("\n" + "="*60)
print("STEP 3: Clean collection (simple approach)")
print("="*60)

# Just select the bands we know exist from the first image
# This breaks the computation graph without complex filtering
bands_to_keep = result_bands  # Use the actual bands from first image
print(f"   Bands to keep: {bands_to_keep}")

# Simple select - this will work if all images have the same bands
ee_col_indices = ee_col_indices.map(lambda img: img.select(bands_to_keep))

print(f"   After cleaning: {ee_col_indices.first().bandNames().getInfo()}")

# Create FCD collection
print("\n" + "="*60)
print("STEP 4: Create FCD collection")
print("="*60)

fcd_col = ee.ImageCollection([
    ee.Image.constant(50).rename('FCD').set('year', y).set('system:time_start', ee.Date.fromYMD(y, 12, 31).millis())
    for y in years
])

print(f"📋 FCD collection size: {fcd_col.size().getInfo()}")

# Merge function
print("\n" + "="*60)
print("STEP 5: Merge with FCD")
print("="*60)

def merge_with_fcd(img):
    """Merge spectral indices with FCD"""
    year = img.get('year')
    
    # Select only spectral indices
    si_selected = img.select(['EVI', 'GNDVI', 'NDVI', 'SAVI', 'NBR'])
    
    # Get FCD
    fcd_filtered = fcd_col.filter(ee.Filter.eq('year', year))
    fcd_img = ee.Image(
        ee.Algorithms.If(
            fcd_filtered.size().gt(0),
            fcd_filtered.first().select('FCD'),
            ee.Image.constant(0).rename('FCD')
        )
    )
    
    # Merge
    merged = si_selected.addBands(fcd_img)
    
    # Final select to break computation graph
    final_bands = ['EVI', 'GNDVI', 'NDVI', 'SAVI', 'NBR', 'FCD']
    result = merged.select(final_bands)
    
    # Set properties
    result = result.set('year', year).set('system:time_start', img.get('system:time_start'))
    
    return result

fcd_col_merged = ee_col_indices.map(merge_with_fcd)

print(f"📋 After merge: {fcd_col_merged.first().bandNames().getInfo()}")

# Test xee inspection
print("\n" + "="*60)
print("STEP 6: Test xee inspection (simulate reduceColumns)")
print("="*60)

try:
    # This is what xee does - it uses reduceColumns to get properties
    def get_props(img):
        return ee.Feature(None, {
            'id': img.get('system:id'),
            'time': img.get('system:time_start'),
            'year': img.get('year')
        })
    
    props_collection = fcd_col_merged.map(get_props)
    props_list = props_collection.getInfo()
    print(f"   ✅ Successfully got properties from all images")
    print(f"   Number of images: {len(props_list.get('features', []))}")
    
except Exception as e:
    print(f"   ❌ ERROR during reduceColumns simulation: {e}")
    error_str = str(e)
    if 'swir' in error_str.lower():
        print(f"   ⚠️  Found 'swir' in error - this is the issue!")
    
    # Try to identify problematic image
    print("\n   🔍 Trying to identify problematic image...")
    try:
        size = fcd_col_merged.size().getInfo()
        for i in range(size):
            img = ee.Image(fcd_col_merged.toList(1, i).get(0))
            bands = img.bandNames().getInfo()
            print(f"      Image {i}: {len(bands)} bands - {bands}")
    except Exception as e2:
        print(f"      Error checking individual images: {e2}")

# Test xr.open_dataset
print("\n" + "="*60)
print("STEP 7: Test xr.open_dataset")
print("="*60)

try:
    ds = xr.open_dataset(
        fcd_col_merged,
        engine='ee',
        crs='EPSG:4326',
        scale=1000
    )
    print(f"   ✅ SUCCESS: xr.open_dataset worked!")
    print(f"   Dataset dimensions: {dict(ds.dims)}")
    print(f"   Data variables: {list(ds.data_vars.keys())}")
except Exception as e:
    print(f"   ❌ ERROR: {e}")
    error_str = str(e)
    if 'swir' in error_str.lower():
        print(f"   ⚠️  Found 'swir' in error - this is the issue!")

print("\n" + "="*60)
print("TEST COMPLETE")
print("="*60)

