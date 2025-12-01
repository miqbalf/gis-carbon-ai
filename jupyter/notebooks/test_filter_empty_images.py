#!/usr/bin/env python3
"""
Test filtering empty images before spectralIndices
"""

import sys
import os

sys.path.insert(0, '/usr/src/app/eemont-osi')
sys.path.insert(0, '/usr/src/app/forestry_carbon_arr')

import ee
import eemont

print("="*60)
print("Testing filter empty images solution")
print("="*60)

# Initialize Earth Engine
try:
    from forestry_carbon_arr.core import ForestryCarbonARR
    forestry = ForestryCarbonARR(config_path='/usr/src/app/notebooks/00_input/korindo.json')
    forestry.initialize_gee()
except Exception as e:
    credentials_path = '/usr/src/app/user_id.json'
    if os.path.exists(credentials_path):
        credentials = ee.ServiceAccountCredentials(None, credentials_path)
        ee.Initialize(credentials)
    else:
        ee.Initialize()

import importlib
importlib.reload(eemont)

# Load collection
asset_monthly_interpolated = 'projects/remote-sensing-476412/assets/korindo_smooth_monthly'
monthly_agg = ee.ImageCollection(asset_monthly_interpolated)

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
print(f"📋 Original collection size: {ee_col_year_median.size().getInfo()}")

# Filter out empty images
print("\n🔍 Filtering out empty images...")
def has_bands(img):
    """Check if image has bands"""
    band_count = img.bandNames().size()
    return band_count.gt(0)

ee_col_year_median_filtered = ee_col_year_median.filter(has_bands)
print(f"✅ Filtered collection size: {ee_col_year_median_filtered.size().getInfo()}")

# Compute spectral indices
print("\n🔄 Computing spectral indices...")
ee_col_indices = ee_col_year_median_filtered.spectralIndices(
    index=['EVI', 'GNDVI', 'NDVI', 'SAVI', 'NBR'],
    satellite_type='Sentinel',
    G=2.5,
    C1=6.0,
    C2=7.5,
    L=1.0,
    drop=False
)

# Check all images
print("\n📋 Checking all images after spectralIndices:")
size = ee_col_indices.size().getInfo()
for i in range(size):
    try:
        img = ee.Image(ee_col_indices.toList(1, i).get(0))
        bands = img.bandNames().getInfo()
        year = img.get('year').getInfo()
        print(f"   Image {i} (year {year}): {len(bands)} bands ✅")
    except Exception as e:
        print(f"   Image {i}: ERROR - {e} ❌")

# Test xee inspection
print("\n🧪 Testing xee inspection (reduceColumns simulation)...")
try:
    def get_props(img):
        return ee.Feature(None, {
            'id': img.get('system:id'),
            'time': img.get('system:time_start'),
            'year': img.get('year')
        })
    
    props_collection = ee_col_indices.map(get_props)
    props_list = props_collection.getInfo()
    print(f"   ✅ SUCCESS: Got properties from all {len(props_list.get('features', []))} images")
except Exception as e:
    print(f"   ❌ ERROR: {e}")

print("\n" + "="*60)
print("TEST COMPLETE")
print("="*60)

