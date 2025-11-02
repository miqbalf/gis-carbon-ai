#!/usr/bin/env python3
"""
Complete test script for Savitzky-Golay comparison.
Tests the extraction and visualization workflow.
"""

import sys
sys.path.insert(0, '/usr/src/app')

import ee
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

print("=" * 70)
print("Testing Savitzky-Golay Extraction and Comparison")
print("=" * 70)

# Initialize GEE
try:
    ee.Initialize()
    print("✅ GEE initialized")
except:
    print("⚠️  GEE initialization skipped (may already be initialized)")

# Manual extraction function (same as in notebook)
def extract_time_series_manual(collection, sample_point, collection_name="unknown"):
    """Extract time series manually to avoid collection structure issues."""
    print(f"\n   Extracting from {collection_name}...")
    
    def extract_pixel_value(img):
        img_selected = img.select(['NDVI', 'EVI'])
        stats = img_selected.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=sample_point,
            scale=10,
            bestEffort=True,
            maxPixels=1e9
        )
        date_str = img.date().format('YYYY-MM-dd')
        return ee.Feature(
            sample_point,
            {
                'date': date_str,
                'NDVI': stats.get('NDVI'),
                'EVI': stats.get('EVI')
            }
        )
    
    ts_features = collection.map(extract_pixel_value)
    ts_fc = ee.FeatureCollection(ts_features)
    
    print(f"   Converting {collection_name} to DataFrame...")
    try:
        ts_list = ts_fc.getInfo()['features']
        ts_data = []
        for feat in ts_list:
            props = feat['properties']
            ts_data.append({
                'date': props.get('date'),
                'NDVI': props.get('NDVI'),
                'EVI': props.get('EVI')
            })
        df = pd.DataFrame(ts_data)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True)
        df = df.replace([None, -9999], np.nan)
        print(f"   ✅ {collection_name}: {len(df)} time steps")
        return df
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

def create_chart(ts_before_df, ts_after_df, output_path='/tmp/sg_test.png'):
    """Create comparison chart."""
    print("\n📊 Creating chart...")
    
    fig, axes = plt.subplots(2, 1, figsize=(14, 10))
    fig.suptitle('SG Filtering: Before vs After', fontsize=16, fontweight='bold')
    
    # NDVI
    ax1 = axes[0]
    if 'NDVI' in ts_before_df.columns and 'NDVI' in ts_after_df.columns:
        ax1.plot(ts_before_df['date'], ts_before_df['NDVI'], 
                'o-', color='lightblue', alpha=0.6, linewidth=1.5, markersize=4,
                label='Before SG', zorder=1)
        ax1.plot(ts_after_df['date'], ts_after_df['NDVI'], 
                '-', color='darkblue', linewidth=2.5, label='After SG', zorder=2)
    ax1.set_xlabel('Date', fontsize=12)
    ax1.set_ylabel('NDVI', fontsize=12)
    ax1.set_title('NDVI Time Series', fontsize=14, fontweight='bold')
    ax1.legend(loc='best')
    ax1.grid(True, alpha=0.3)
    
    # EVI
    ax2 = axes[1]
    if 'EVI' in ts_before_df.columns and 'EVI' in ts_after_df.columns:
        ax2.plot(ts_before_df['date'], ts_before_df['EVI'], 
                'o-', color='lightcoral', alpha=0.6, linewidth=1.5, markersize=4,
                label='Before SG', zorder=1)
        ax2.plot(ts_after_df['date'], ts_after_df['EVI'], 
                '-', color='darkred', linewidth=2.5, label='After SG', zorder=2)
    ax2.set_xlabel('Date', fontsize=12)
    ax2.set_ylabel('EVI', fontsize=12)
    ax2.set_title('EVI Time Series', fontsize=14, fontweight='bold')
    ax2.legend(loc='best')
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"   ✅ Chart saved: {output_path}")
    plt.close()
    
    # Stats
    print("\n📊 Statistics:")
    if 'NDVI' in ts_before_df.columns:
        before_std = ts_before_df['NDVI'].std()
        after_std = ts_after_df['NDVI'].std()
        if before_std > 0:
            reduction = (1 - after_std/before_std) * 100
            print(f"  NDVI noise reduction: {reduction:.1f}%")
    if 'EVI' in ts_before_df.columns:
        before_std = ts_before_df['EVI'].std()
        after_std = ts_after_df['EVI'].std()
        if before_std > 0:
            reduction = (1 - after_std/before_std) * 100
            print(f"  EVI noise reduction: {reduction:.1f}%")

print("\n⚠️  NOTE: This script assumes collections exist from the notebook.")
print("   Variables needed: collection_with_eemont_indices, collection_with_sg, aoi_ee")
print("\n   To use in Jupyter:")
print("   1. Run notebook cells to create collections")
print("   2. exec(open('/usr/src/app/test_sg_complete.py').read())")
print("   3. Then call: test_extraction_and_chart()")

def test_extraction_and_chart():
    """Test function - call this after collections are loaded."""
    try:
        # Get sample point
        sample_point = aoi_ee.geometry().centroid(1)
        print(f"✅ Sample point created: {sample_point.getInfo()}")
        
        # Extract BEFORE
        ts_before_df = extract_time_series_manual(
            collection_with_eemont_indices, 
            sample_point, 
            "BEFORE (original)"
        )
        
        if ts_before_df is None:
            print("❌ Failed to extract BEFORE data")
            return
        
        # Extract AFTER
        ts_after_df = extract_time_series_manual(
            collection_with_sg, 
            sample_point, 
            "AFTER (smoothed)"
        )
        
        if ts_after_df is None:
            print("❌ Failed to extract AFTER data")
            return
        
        # Create chart
        create_chart(ts_before_df, ts_after_df)
        
        print("\n✅ Test completed successfully!")
        return ts_before_df, ts_after_df
        
    except NameError as e:
        print(f"\n❌ Error: Variable not defined - {e}")
        print("   Make sure you've run the notebook cells first to create collections.")
    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        import traceback
        traceback.print_exc()

print("\n✅ Script loaded. Call test_extraction_and_chart() after loading collections.")

