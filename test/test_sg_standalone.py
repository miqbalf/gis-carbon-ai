#!/usr/bin/env python3
"""
Standalone test script for Savitzky-Golay comparison.
This script can be run directly in the Jupyter container to test the SG filtering.
"""

import sys
import os

# Add the project to path
sys.path.insert(0, '/usr/src/app')

import ee
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import json

print("=" * 70)
print("Savitzky-Golay Filtering Test Script")
print("=" * 70)

# Initialize Earth Engine
try:
    ee.Initialize()
    print("✅ Earth Engine initialized")
except Exception as e:
    print(f"⚠️  Earth Engine initialization: {e}")

# Load notebook to extract variable definitions
print("\n📖 Loading notebook to extract collections...")
NOTEBOOK_PATH = '/usr/src/app/jupyter/notebooks/02b_forestry_arr_eligibility_stac_LAZY_OPTIMIZE.ipynb'

def extract_time_series_manual(collection, sample_point, collection_name="unknown"):
    """Extract time series manually to avoid collection structure issues."""
    print(f"\n   Extracting time series from {collection_name}...")
    
    def extract_pixel_value(img):
        """Extract mean value at sample point for NDVI and EVI."""
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
    
    # Convert to pandas DataFrame
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
        print(f"   ✅ Converted {collection_name}: {len(df)} time steps")
        return df
    except Exception as e:
        print(f"   ❌ Error converting {collection_name}: {e}")
        import traceback
        traceback.print_exc()
        raise

def create_comparison_chart(ts_before_df, ts_after_df, output_path='/tmp/sg_comparison.png'):
    """Create before/after comparison chart."""
    print("\n📊 Creating comparison chart...")
    
    fig, axes = plt.subplots(2, 1, figsize=(14, 10))
    fig.suptitle('Savitzky-Golay Filtering: Before vs After Comparison', fontsize=16, fontweight='bold')
    
    # Plot NDVI
    ax1 = axes[0]
    if 'NDVI' in ts_before_df.columns and 'NDVI' in ts_after_df.columns:
        ax1.plot(ts_before_df['date'], ts_before_df['NDVI'], 
                'o-', color='lightblue', alpha=0.6, linewidth=1.5, markersize=4,
                label='Before SG (Original)', zorder=1)
        ax1.plot(ts_after_df['date'], ts_after_df['NDVI'], 
                '-', color='darkblue', linewidth=2.5,
                label='After SG (Smoothed)', zorder=2)
    
    ax1.set_xlabel('Date', fontsize=12)
    ax1.set_ylabel('NDVI', fontsize=12)
    ax1.set_title('NDVI Time Series', fontsize=14, fontweight='bold')
    ax1.legend(loc='best', fontsize=11)
    ax1.grid(True, alpha=0.3, linestyle='--')
    ax1.tick_params(axis='x', rotation=45)
    
    # Plot EVI
    ax2 = axes[1]
    if 'EVI' in ts_before_df.columns and 'EVI' in ts_after_df.columns:
        ax2.plot(ts_before_df['date'], ts_before_df['EVI'], 
                'o-', color='lightcoral', alpha=0.6, linewidth=1.5, markersize=4,
                label='Before SG (Original)', zorder=1)
        ax2.plot(ts_after_df['date'], ts_after_df['EVI'], 
                '-', color='darkred', linewidth=2.5,
                label='After SG (Smoothed)', zorder=2)
    
    ax2.set_xlabel('Date', fontsize=12)
    ax2.set_ylabel('EVI', fontsize=12)
    ax2.set_title('EVI Time Series', fontsize=14, fontweight='bold')
    ax2.legend(loc='best', fontsize=11)
    ax2.grid(True, alpha=0.3, linestyle='--')
    ax2.tick_params(axis='x', rotation=45)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"   ✅ Chart saved to: {output_path}")
    plt.close()
    
    # Print summary statistics
    print("\n📊 Summary Statistics:")
    print("=" * 60)
    
    if 'NDVI' in ts_before_df.columns and 'NDVI' in ts_after_df.columns:
        before_ndvi_mean = ts_before_df['NDVI'].mean()
        before_ndvi_std = ts_before_df['NDVI'].std()
        after_ndvi_mean = ts_after_df['NDVI'].mean()
        after_ndvi_std = ts_after_df['NDVI'].std()
        
        print("NDVI Statistics:")
        print(f"  Before SG - Mean: {before_ndvi_mean:.4f}, Std: {before_ndvi_std:.4f}")
        print(f"  After SG  - Mean: {after_ndvi_mean:.4f}, Std: {after_ndvi_std:.4f}")
        if before_ndvi_std > 0:
            noise_reduction_ndvi = (1 - after_ndvi_std/before_ndvi_std) * 100
            print(f"  Noise Reduction: {noise_reduction_ndvi:.1f}%")
    
    if 'EVI' in ts_before_df.columns and 'EVI' in ts_after_df.columns:
        before_evi_mean = ts_before_df['EVI'].mean()
        before_evi_std = ts_before_df['EVI'].std()
        after_evi_mean = ts_after_df['EVI'].mean()
        after_evi_std = ts_after_df['EVI'].std()
        
        print("\nEVI Statistics:")
        print(f"  Before SG - Mean: {before_evi_mean:.4f}, Std: {before_evi_std:.4f}")
        print(f"  After SG  - Mean: {after_evi_mean:.4f}, Std: {after_evi_std:.4f}")
        if before_evi_std > 0:
            noise_reduction_evi = (1 - after_evi_std/before_evi_std) * 100
            print(f"  Noise Reduction: {noise_reduction_evi:.1f}%")

# Main execution
print("\n⚠️  This script requires collections to exist in the GEE session.")
print("   Collections must be loaded from the notebook first.")
print("\n   To use:")
print("   1. Run notebook cells to create: collection_with_eemont_indices, collection_with_sg, aoi_ee")
print("   2. Then run this script")
print("\n   OR use this script interactively in Jupyter to test the extraction functions.")

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("Functions available:")
    print("  - extract_time_series_manual(collection, sample_point, collection_name)")
    print("  - create_comparison_chart(ts_before_df, ts_after_df, output_path)")
    print("=" * 70)
    print("\n✅ Test script loaded. Ready to use functions interactively.")

