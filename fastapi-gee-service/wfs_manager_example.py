#!/usr/bin/env python3
"""
WFS Manager Example - Simplified Vector Layer Management

This script demonstrates how to use the new WFSManager class to simplify
adding vector layers to WFS services, replacing the manual /fc/ endpoint approach.

Usage:
    python wfs_manager_example.py
"""

import sys
import os

# Add the fastapi-gee-service to the path
sys.path.append('/usr/src/app/fastapi-gee-service')

def main():
    print("🚀 WFS Manager Example")
    print("=" * 50)
    
    # Example code that would replace the manual approach
    example_code = '''
# OLD APPROACH (Manual):
# ======================
geojson_data = training_points_ee.getInfo()
name_aoi = 'training_points_dynamic'

link_fastapi = 'http://fastapi:8000/fc/'+name_aoi

response = requests.post(
    link_fastapi,
    json=geojson_data
)

# NEW APPROACH (Simple):
# ======================
from wfs_manager import WFSManager

# Create WFS manager
wfs = WFSManager(fastapi_url="http://fastapi:8000", wfs_base_url="http://localhost:8001")

# Add vector layers (similar to Map.addLayer())
wfs.addLayer(AOI, "AOI Boundary")
wfs.addLayer(training_points_ee, "Training Points")

# Publish all layers to WFS
result = wfs.publish()
'''
    
    print("📋 Code Comparison:")
    print(example_code)
    
    print("\n✅ Benefits of the New Approach:")
    print("   - Simpler: No manual GeoJSON conversion")
    print("   - Intuitive: Similar to Map.addLayer()")
    print("   - Flexible: Add/remove layers dynamically")
    print("   - Clean: Method chaining support")
    print("   - Integrated: Works with existing WFS infrastructure")
    
    print("\n🔧 Available Methods:")
    print("   - wfs.addLayer(vector_data, layer_name)")
    print("   - wfs.removeLayer(layer_name)")
    print("   - wfs.listLayers()")
    print("   - wfs.publish()")
    print("   - wfs.clear()")
    
    print("\n📚 Usage Patterns:")
    print("   1. Step-by-step: Create manager, add layers, publish")
    print("   2. Method chaining: WFSManager().addLayer().addLayer().publish()")
    print("   3. Quick publish: quick_publish_vector(vector_data, name)")
    print("   4. Dynamic: Add/remove layers as needed")
    
    print("\n🌐 Service URLs:")
    print("   - WFS GetCapabilities: http://localhost:8001/wfs?service=WFS&version=1.1.0&request=GetCapabilities")
    print("   - WFS GetFeature: http://localhost:8001/wfs?service=WFS&version=1.1.0&request=GetFeature&typename=layer_name")
    print("   - FeatureCollection API: http://fastapi:8000/fc/layer_name")

if __name__ == "__main__":
    main()
