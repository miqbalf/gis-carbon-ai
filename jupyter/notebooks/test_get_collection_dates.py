#!/usr/bin/env python3
"""
Examples of how to get date range and list all dates from an ImageCollection
"""

import sys
import os

sys.path.insert(0, '/usr/src/app/eemont-osi')
sys.path.insert(0, '/usr/src/app/forestry_carbon_arr')

import ee
from datetime import datetime

print("="*60)
print("Getting date information from ImageCollection")
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

# Load a sample collection (using the same pattern as the notebook)
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

# Filter empty images
def add_band_count(img):
    band_count = img.bandNames().size()
    return img.set('has_bands', band_count.gt(0))

ee_col_with_flag = ee_col_year_median.map(add_band_count)
ee_col_year_median = ee_col_with_flag.filter(ee.Filter.eq('has_bands', 1))

# Simulate ee_col_indices (without actually computing spectral indices for speed)
ee_col_indices = ee_col_year_median  # For demo purposes

print("\n" + "="*60)
print("METHOD 1: Get date range (min and max)")
print("="*60)

# Get min and max timestamps
min_time = ee_col_indices.aggregate_min('system:time_start').getInfo()
max_time = ee_col_indices.aggregate_max('system:time_start').getInfo()

# Convert to readable dates
min_date = datetime.fromtimestamp(min_time / 1000)
max_date = datetime.fromtimestamp(max_time / 1000)

print(f"   Date range: {min_date.strftime('%Y-%m-%d')} to {max_date.strftime('%Y-%m-%d')}")
print(f"   Min timestamp: {min_time}")
print(f"   Max timestamp: {max_time}")

print("\n" + "="*60)
print("METHOD 2: Get all timestamps as array")
print("="*60)

# Get all timestamps
all_timestamps = ee_col_indices.aggregate_array('system:time_start').getInfo()
all_dates = [datetime.fromtimestamp(ts / 1000) for ts in all_timestamps]

print(f"   Total images: {len(all_dates)}")
print(f"   Dates:")
for date in all_dates:
    print(f"      {date.strftime('%Y-%m-%d %H:%M:%S')}")

print("\n" + "="*60)
print("METHOD 3: Get dates with year property (if available)")
print("="*60)

# Get years if the property exists
years = ee_col_indices.aggregate_array('year').getInfo()
print(f"   Years: {years}")

print("\n" + "="*60)
print("METHOD 4: Get detailed info for each image (date + properties)")
print("="*60)

# Map over collection to get date and other properties for each image
def get_image_info(img):
    """Extract date and other info from each image"""
    time_start = img.get('system:time_start')
    year = img.get('year')
    return ee.Feature(None, {
        'time_start': time_start,
        'date': ee.Date(time_start).format('YYYY-MM-dd'),
        'year': year,
        'timestamp': time_start
    })

info_collection = ee_col_indices.map(get_image_info)
info_list = info_collection.getInfo()

print(f"   Total images: {len(info_list.get('features', []))}")
for i, feature in enumerate(info_list.get('features', [])):
    props = feature.get('properties', {})
    print(f"   Image {i}: {props.get('date')} (year: {props.get('year')}, timestamp: {props.get('timestamp')})")

print("\n" + "="*60)
print("METHOD 5: Get sorted list of dates")
print("="*60)

# Get sorted dates
all_timestamps_sorted = sorted(all_timestamps)
all_dates_sorted = [datetime.fromtimestamp(ts / 1000) for ts in all_timestamps_sorted]

print(f"   Sorted dates:")
for date in all_dates_sorted:
    print(f"      {date.strftime('%Y-%m-%d')}")

print("\n" + "="*60)
print("QUICK ONE-LINERS for notebook use:")
print("="*60)
print("""
# Get date range:
min_date = datetime.fromtimestamp(ee_col_indices.aggregate_min('system:time_start').getInfo() / 1000)
max_date = datetime.fromtimestamp(ee_col_indices.aggregate_max('system:time_start').getInfo() / 1000)
print(f"Date range: {min_date.strftime('%Y-%m-%d')} to {max_date.strftime('%Y-%m-%d')}")

# Get all dates:
all_dates = [datetime.fromtimestamp(ts/1000) for ts in ee_col_indices.aggregate_array('system:time_start').getInfo()]
for date in all_dates:
    print(date.strftime('%Y-%m-%d'))

# Get years (if year property exists):
years = ee_col_indices.aggregate_array('year').getInfo()
print(f"Years: {years}")
""")

print("\n" + "="*60)
print("TEST COMPLETE")
print("="*60)

