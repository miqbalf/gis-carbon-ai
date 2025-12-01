#!/usr/bin/env python3
"""
Test the ACTUAL notebook workflow using the real collection from the notebook
This simulates exactly what happens in the notebook
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
print("Testing ACTUAL notebook workflow")
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

# Load the ACTUAL collection from the notebook
print("\n" + "="*60)
print("STEP 1: Load ACTUAL collection from notebook")
print("="*60)

asset_monthly_interpolated = 'projects/remote-sensing-476412/assets/korindo_smooth_monthly'
monthly_agg = ee.ImageCollection(asset_monthly_interpolated)

# Server-side list of unique years
year_list = (
    monthly_agg
        .aggregate_array('system:time_start')
        .map(lambda ts: ee.Date(ts).get('year'))
        .distinct()
        .sort()
)

def annual_col_median(img_col, years):
    def per_year(year):
        start = ee.Date.fromYMD(year, 12, 31)
        end = start.advance(1, 'year')
        return (
            img_col
            .filterDate(start, end)
            .median()
            .set('year', year)
            .set('system:time_start', start.millis())
        )
    return ee.ImageCollection(years.map(per_year))

ee_col_year_median = annual_col_median(monthly_agg, year_list)
year_list_c = year_list.getInfo()

print(f"📋 Collection size: {ee_col_year_median.size().getInfo()}")
print(f"📋 Years: {year_list_c}")
print(f"📋 First image bands: {ee_col_year_median.first().bandNames().getInfo()}")

# Compute spectral indices (EXACTLY as in notebook)
print("\n" + "="*60)
print("STEP 2: Compute spectral indices (notebook method)")
print("="*60)

ee_col_indices = ee_col_year_median.spectralIndices(
    index=['EVI', 'GNDVI', 'NDVI', 'SAVI', 'NBR'],
    satellite_type='Sentinel',
    G=2.5,
    C1=6.0,
    C2=7.5,
    L=1.0,
    drop=False
)

result_bands = ee_col_indices.first().bandNames().getInfo()
print(f"📋 After spectralIndices: {result_bands}")

# Clean collection (FIXED VERSION - no lambda in filter)
print("\n" + "="*60)
print("STEP 3: Clean collection (fixed version)")
print("="*60)

first_img_bands = ee_col_indices.first().bandNames().getInfo()
print(f"   Before cleaning: {first_img_bands}")

# Use the actual bands from the first image
bands_to_keep = first_img_bands
print(f"   Bands to keep: {bands_to_keep}")

# Simple select - breaks computation graph
ee_col_indices = ee_col_indices.map(lambda img: img.select(bands_to_keep))

print(f"   After cleaning: {ee_col_indices.first().bandNames().getInfo()}")

# Load FCD collection (EXACTLY as in notebook)
print("\n" + "="*60)
print("STEP 4: Load FCD collection (notebook method)")
print("="*60)

def load_yearly_images_from_gcs(years, gcs_bucket='remote_sensing_saas', base_path='01-korindo/yearly_mosaic_gee'):
    images = []
    for year in years:
        gcs_path = f'gs://{gcs_bucket}/{base_path}/fcd_{year}.tif'
        img = ee.Image.loadGeoTIFF(gcs_path)
        img = img.set('year', year)
        img = img.set('system:time_start', ee.Date.fromYMD(year, 12, 31).millis())
        images.append(img)
    return ee.ImageCollection(images)

fcd_col = load_yearly_images_from_gcs(year_list_c)
print(f"📋 FCD collection size: {fcd_col.size().getInfo()}")
print(f"📋 FCD bands: {fcd_col.first().bandNames().getInfo()}")

# Merge function (FIXED VERSION)
print("\n" + "="*60)
print("STEP 5: Merge with FCD (fixed version)")
print("="*60)

def merge_with_fcd(img):
    """Merge spectral indices with FCD"""
    year = img.get('year')
    si_selected = img.select(['EVI', 'GNDVI', 'NDVI', 'SAVI', 'NBR'])
    
    fcd_filtered = fcd_col.filter(ee.Filter.eq('year', year))
    fcd_exists = fcd_filtered.size()
    fcd_img = ee.Image(
        ee.Algorithms.If(
            fcd_exists.gt(0),
            fcd_filtered.first().select('FCD'),
            ee.Image.constant(0).rename('FCD')
        )
    )
    
    merged = si_selected.addBands(fcd_img)
    final_bands = ['EVI', 'GNDVI', 'NDVI', 'SAVI', 'NBR', 'FCD']
    result = merged.select(final_bands)
    result = result.set('year', year).set('system:time_start', img.get('system:time_start'))
    return result

fcd_col_merged = ee_col_indices.map(merge_with_fcd)

print(f"📋 After merge: {fcd_col_merged.first().bandNames().getInfo()}")

# Test xee inspection
print("\n" + "="*60)
print("STEP 6: Test xee inspection (reduceColumns simulation)")
print("="*60)

try:
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
        print(f"   Collection size: {size}")
        for i in range(min(size, 15)):  # Check first 15 images
            try:
                img = ee.Image(fcd_col_merged.toList(1, i).get(0))
                bands = img.bandNames().getInfo()
                year = img.get('year').getInfo()
                print(f"      Image {i} (year {year}): {len(bands)} bands - {bands[:5]}...")
            except Exception as e2:
                print(f"      Image {i}: ERROR - {e2}")
    except Exception as e2:
        print(f"      Error checking individual images: {e2}")

# Test xr.open_dataset (with actual geometry)
print("\n" + "="*60)
print("STEP 7: Test xr.open_dataset (actual notebook parameters)")
print("="*60)

try:
    # Use simple geometry for testing
    test_geometry = ee.Geometry.Rectangle([111.7, -0.46, 112.11, -0.17])
    
    ds = xr.open_dataset(
        fcd_col_merged,
        engine='ee',
        crs='EPSG:32749',
        scale=10,
        geometry=test_geometry.transform('EPSG:32749', maxError=1)
    )
    print(f"   ✅ SUCCESS: xr.open_dataset worked!")
    print(f"   Dataset dimensions: {dict(ds.sizes)}")
    print(f"   Data variables: {list(ds.data_vars.keys())}")
except Exception as e:
    print(f"   ❌ ERROR: {e}")
    error_str = str(e)
    if 'swir' in error_str.lower():
        print(f"   ⚠️  Found 'swir' in error - this is the issue!")

print("\n" + "="*60)
print("TEST COMPLETE")
print("="*60)

