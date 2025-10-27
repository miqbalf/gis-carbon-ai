#!/usr/bin/env python3
"""
WMTS Manager Example - Simplified GEE Layer Management

This script demonstrates how to use the new WMTSManager class to simplify
adding GEE layers to WMTS services, replacing the complex map_layers approach.

Usage:
    python wmts_manager_example.py
"""

import sys
import os

# Add the fastapi-gee-service to the path
sys.path.append('/usr/src/app/fastapi-gee-service')

def main():
    print("🚀 WMTS Manager Example")
    print("=" * 50)
    
    # Example code that would replace the complex approach
    example_code = '''
# OLD APPROACH (Complex):
# ======================
map_layers = generate_map_id(
    {layer_name: vis_param, fcd1_1_layer_name: fcd_visparams, fcd2_1_layer_name: fcd_visparams}, 
    {layer_name: image_mosaick, fcd1_1_layer_name: FCD1_1, fcd2_1_layer_name: FCD2_1}
)['map_layers']

result = list_layers_to_wmts(map_layers, AOI)

# NEW APPROACH (Simple):
# ======================
from wmts_manager import WMTSManager

# Create WMTS manager (similar to creating a Map object)
wmts = WMTSManager(project_name=project_name, aoi=AOI)

# Add layers one by one (similar to Map.addLayer())
wmts.addLayer(image_mosaick, vis_param, layer_name)
wmts.addLayer(FCD1_1, fcd_visparams, fcd1_1_layer_name)
wmts.addLayer(FCD2_1, fcd_visparams, fcd2_1_layer_name)

# Publish all layers to WMTS
result = wmts.publish()
'''
    
    print("📋 Code Comparison:")
    print(example_code)
    
    print("\n✅ Benefits of the New Approach:")
    print("   - Simpler: No dictionary management")
    print("   - Intuitive: Similar to Map.addLayer()")
    print("   - Flexible: Add/remove layers dynamically")
    print("   - Clean: Method chaining support")
    print("   - Maintainable: Easier to debug and modify")
    
    print("\n🔧 Available Methods:")
    print("   - wmts.addLayer(image, vis_params, name)")
    print("   - wmts.removeLayer(name)")
    print("   - wmts.listLayers()")
    print("   - wmts.publish()")
    print("   - wmts.clear()")
    
    print("\n📚 Usage Patterns:")
    print("   1. Step-by-step: Create manager, add layers, publish")
    print("   2. Method chaining: WMTSManager().addLayer().addLayer().publish()")
    print("   3. Quick publish: quick_publish(image, vis, name)")
    print("   4. Dynamic: Add/remove layers as needed")

if __name__ == "__main__":
    main()
