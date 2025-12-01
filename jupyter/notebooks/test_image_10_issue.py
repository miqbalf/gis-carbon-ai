#!/usr/bin/env python3
"""
Test specifically image 10 to identify the root cause
"""

import sys
import os

sys.path.insert(0, '/usr/src/app/eemont-osi')
sys.path.insert(0, '/usr/src/app/forestry_carbon_arr')

import ee
import eemont

print("="*60)
print("Testing image 10 specifically")
print("="*60)

# Initialize Earth Engine
try:
    from forestry_carbon_arr.core import ForestryCarbonARR
    forestry = ForestryCarbonARR(config_path='/usr/src/app/notebooks/00_input/korindo.json')
    forestry.initialize_gee()
    print("✅ Earth Engine initialized")
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
year_list_c = year_list.getInfo()

print(f"📋 Years: {year_list_c}")
print(f"📋 Collection size: {ee_col_year_median.size().getInfo()}")

# Check each image before spectralIndices
print("\n" + "="*60)
print("Checking images BEFORE spectralIndices:")
print("="*60)
for i, year in enumerate(year_list_c):
    try:
        img = ee.Image(ee_col_year_median.toList(1, i).get(0))
        bands = img.bandNames().getInfo()
        print(f"   Image {i} (year {year}): {len(bands)} bands")
    except Exception as e:
        print(f"   Image {i} (year {year}): ERROR - {e}")

# Compute spectral indices
print("\n" + "="*60)
print("Computing spectral indices...")
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

# Check each image AFTER spectralIndices
print("\n" + "="*60)
print("Checking images AFTER spectralIndices:")
print("="*60)
for i, year in enumerate(year_list_c):
    try:
        img = ee.Image(ee_col_indices.toList(1, i).get(0))
        bands = img.bandNames().getInfo()
        print(f"   Image {i} (year {year}): {len(bands)} bands - {bands[:5]}...")
    except Exception as e:
        print(f"   Image {i} (year {year}): ERROR - {e}")
        error_str = str(e)
        if 'swir' in error_str.lower():
            print(f"      ⚠️  Found 'swir' in error!")

# Try cleaning and check again
print("\n" + "="*60)
print("Cleaning collection and checking again:")
print("="*60)

first_img_bands = ee_col_indices.first().bandNames().getInfo()
print(f"   Bands to keep: {first_img_bands}")

# Clean with error handling
def clean_image_safe(img):
    """Clean image, handling empty images"""
    bands = img.bandNames()
    has_bands = bands.size().gt(0)
    return ee.Image(
        ee.Algorithms.If(
            has_bands,
            img.select(first_img_bands),
            ee.Image.constant(0).select([]).rename('empty')  # Empty image
        )
    )

ee_col_indices_cleaned = ee_col_indices.map(clean_image_safe)

for i, year in enumerate(year_list_c):
    try:
        img = ee.Image(ee_col_indices_cleaned.toList(1, i).get(0))
        bands = img.bandNames().getInfo()
        print(f"   Image {i} (year {year}): {len(bands)} bands")
    except Exception as e:
        print(f"   Image {i} (year {year}): ERROR - {e}")

print("\n" + "="*60)
print("TEST COMPLETE")
print("="*60)

