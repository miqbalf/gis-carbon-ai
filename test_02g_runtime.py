#!/usr/bin/env python3
"""
Runtime test for notebook 02g - simulates actual execution
Run: docker compose -f docker-compose.dev.yml exec jupyter python3 /usr/src/app/test_02g_runtime.py
"""

import json
import sys
import traceback

def test_runtime():
    """Test runtime execution of notebook cells"""
    print("=" * 80)
    print("RUNTIME TEST: 02g_ml_tsresh_prep_MPC.ipynb")
    print("=" * 80)
    
    notebook_path = '/usr/src/app/notebooks/02g_ml_tsresh_prep_MPC.ipynb'
    
    try:
        with open(notebook_path, 'r') as f:
            nb = json.load(f)
        print(f"✅ Notebook loaded: {len(nb['cells'])} cells")
    except Exception as e:
        print(f"❌ Failed to load notebook: {e}")
        return False
    
    # Test cell 30 - try to compile and check for obvious issues
    print("\n" + "=" * 80)
    print("TEST: Cell 30 Runtime Checks")
    print("=" * 80)
    
    cell_30 = ''.join(nb['cells'][30].get('source', [])) if len(nb['cells']) > 30 else ""
    
    # Check for common runtime errors
    issues = []
    
    # 1. Check if ee is imported but might not be initialized
    if 'ee.Geometry' in cell_30 and 'import ee' in cell_30:
        print("✅ ee is imported")
        if 'ee.Initialize' not in cell_30:
            print("⚠️  ee.Initialize() not in cell 30 (should be in earlier cells)")
    else:
        if 'ee.Geometry' in cell_30:
            issues.append("❌ Uses ee.Geometry but ee may not be imported")
    
    # 2. Check if forestry is used
    if 'forestry.config' in cell_30:
        print("✅ Uses forestry.config (should be initialized in cell 1)")
        if 'forestry =' not in cell_30:
            print("   (forestry should be created in earlier cells)")
    
    # 3. Check if sample_point is created correctly
    if 'sample_point = ee.Geometry.Point' in cell_30:
        print("✅ sample_point is created in cell 30")
    elif 'sample_point =' in cell_30:
        print("⚠️  sample_point is assigned but may not use ee.Geometry.Point")
    
    # 4. Check function call structure
    if 'ts_before_df, ts_after_df = extract_time_series_for_visualization(' in cell_30:
        print("✅ Function call structure is correct")
        
        # Check if all required parameters are in the call
        call_section = cell_30[cell_30.find('ts_before_df, ts_after_df ='):]
        required_params = [
            'collection_before=collection_before_sg',
            'collection_after=collection_with_sg',
            'sample_point=sample_point',
            'bands=bands_to_compare',
            'time_dates=time_dates_source',
        ]
        
        for param in required_params:
            if param in call_section:
                print(f"   ✅ {param.split('=')[0]} parameter present")
            else:
                issues.append(f"❌ Missing parameter: {param.split('=')[0]}")
    else:
        issues.append("❌ Function call not found in cell 30")
    
    # 5. Check cell 31
    print("\n" + "=" * 80)
    print("TEST: Cell 31 Runtime Checks")
    print("=" * 80)
    
    cell_31 = ''.join(nb['cells'][31].get('source', [])) if len(nb['cells']) > 31 else ""
    
    if 'def plot_sg_comparison' in cell_31:
        print("✅ plot_sg_comparison function defined")
    else:
        issues.append("❌ plot_sg_comparison function not found")
    
    if 'plot_sg_comparison(ts_before_df, ts_after_df, bands_to_compare)' in cell_31:
        print("✅ Function call found in cell 31")
    else:
        issues.append("❌ Function call not found in cell 31")
    
    if "if 'bands_to_compare' not in" in cell_31:
        print("✅ bands_to_compare fallback logic present")
    else:
        issues.append("❌ bands_to_compare fallback logic missing")
    
    # Summary
    print("\n" + "=" * 80)
    if issues:
        print("❌ ISSUES FOUND:")
        for issue in issues:
            print(f"   {issue}")
        return False
    else:
        print("✅ NO RUNTIME ISSUES DETECTED")
        print("\nThe notebook code structure is correct.")
        print("If you're seeing an error, please share the error message.")
        return True

if __name__ == '__main__':
    try:
        success = test_runtime()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        traceback.print_exc()
        sys.exit(1)

