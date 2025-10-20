# ArcGIS Python API Integration
# This script demonstrates how to use ArcGIS Python API with the GIS Carbon AI environment.

import sys
import os
import requests
from datetime import datetime

# Add libraries to path
sys.path.append('/app/gee_lib')
sys.path.append('/app/ex_ante')

print("="*60)
print("ARCGIS PYTHON API INTEGRATION TEST")
print("="*60)

# Test ArcGIS Python API imports
try:
    from arcgis.gis import GIS
    from arcgis.features import FeatureLayer
    from arcgis.geometry import Geometry
    from arcgis.raster import ImageryLayer
    from arcgis.mapping import WebMap
    print("✅ ArcGIS Python API imported successfully")
    print("Available modules:")
    print("- GIS: Main GIS connection class")
    print("- FeatureLayer: For working with feature services")
    print("- Geometry: For geometric operations")
    print("- ImageryLayer: For raster data")
    print("- WebMap: For web map operations")
    
except ImportError as e:
    print(f"❌ ArcGIS Python API import failed: {e}")
    print("Make sure arcgis package is installed")

# Test ArcGIS Online connection (anonymous)
try:
    print("\n" + "-"*40)
    print("Testing ArcGIS Online connection...")
    
    # Connect to ArcGIS Online (anonymous)
    gis = GIS()
    print("✅ Connected to ArcGIS Online successfully")
    print(f"GIS version: {gis.version}")
    print(f"Current user: {gis.users.me if gis.users.me else 'Anonymous'}")
    
    # Search for some public content
    print("\nSearching for forest-related content...")
    search_results = gis.content.search("forest carbon", max_items=3)
    print(f"Found {len(search_results)} forest carbon related items:")
    
    for item in search_results:
        print(f"  - {item.title} (Type: {item.type})")
        print(f"    ID: {item.id}")
        print(f"    Owner: {item.owner}")
        print()
    
except Exception as e:
    print(f"❌ ArcGIS Online connection failed: {e}")

# Test ArcGIS Enterprise connection (if configured)
try:
    print("\n" + "-"*40)
    print("Testing ArcGIS Enterprise connection...")
    
    # You can configure this with your ArcGIS Enterprise URL
    # enterprise_url = "https://your-enterprise-server.com/portal"
    # username = "your-username"
    # password = "your-password"
    # gis_enterprise = GIS(enterprise_url, username, password)
    
    print("ℹ️  ArcGIS Enterprise connection not configured")
    print("To configure, uncomment and set the following variables:")
    print("  - enterprise_url")
    print("  - username") 
    print("  - password")
    
except Exception as e:
    print(f"❌ ArcGIS Enterprise connection failed: {e}")

# Test working with feature layers
try:
    print("\n" + "-"*40)
    print("Testing feature layer operations...")
    
    # Example: Access a public feature layer
    # You can replace this with your own feature layer URL
    feature_layer_url = "https://services.arcgis.com/P3ePLMYs2RVChkJx/arcgis/rest/services/World_Countries_(Generalized)/FeatureServer/0"
    
    feature_layer = FeatureLayer(feature_layer_url)
    print(f"✅ Feature layer loaded: {feature_layer.properties.name}")
    print(f"Layer type: {feature_layer.properties.geometryType}")
    print(f"Feature count: {feature_layer.query(return_count_only=True)}")
    
    # Get some sample features
    features = feature_layer.query(where="1=1", out_fields="*", result_record_count=3)
    print(f"Sample features retrieved: {len(features.features)}")
    
    for feature in features.features:
        print(f"  - {feature.attributes.get('NAME', 'Unknown')}")
    
except Exception as e:
    print(f"❌ Feature layer operations failed: {e}")

# Test working with imagery layers
try:
    print("\n" + "-"*40)
    print("Testing imagery layer operations...")
    
    # Example: Access a public imagery layer
    # You can replace this with your own imagery layer URL
    imagery_layer_url = "https://services.arcgis.com/P3ePLMYs2RVChkJx/arcgis/rest/services/World_Imagery/MapServer"
    
    imagery_layer = ImageryLayer(imagery_layer_url)
    print(f"✅ Imagery layer loaded: {imagery_layer.properties.name}")
    print(f"Layer type: {imagery_layer.properties.type}")
    print(f"Extent: {imagery_layer.properties.extent}")
    
except Exception as e:
    print(f"❌ Imagery layer operations failed: {e}")

# Test integration with our local services
try:
    print("\n" + "-"*40)
    print("Testing integration with local services...")
    
    # Test GeoServer connection
    geoserver_url = "http://geoserver:8080/geoserver"
    response = requests.get(f"{geoserver_url}/rest/about/status.json")
    
    if response.status_code == 200:
        print("✅ GeoServer is accessible from Jupyter")
        print("You can integrate ArcGIS with GeoServer layers")
    else:
        print(f"❌ GeoServer connection failed: {response.status_code}")
    
    # Test FastAPI connection
    fastapi_url = "http://fastapi:8000"
    response = requests.get(f"{fastapi_url}/health")
    
    if response.status_code == 200:
        print("✅ FastAPI is accessible from Jupyter")
        print("You can call GEE processing endpoints from ArcGIS workflows")
    else:
        print(f"❌ FastAPI connection failed: {response.status_code}")
    
except Exception as e:
    print(f"❌ Local services integration test failed: {e}")

# Example: Create a simple web map
try:
    print("\n" + "-"*40)
    print("Testing web map creation...")
    
    # Create a new web map
    web_map = WebMap()
    print("✅ Web map created successfully")
    
    # Add a basemap
    web_map.basemap = "streets"
    print("✅ Basemap added to web map")
    
    # You can add layers, set extent, etc.
    print("Web map is ready for customization")
    
except Exception as e:
    print(f"❌ Web map creation failed: {e}")

print("\n" + "="*60)
print("ARCGIS INTEGRATION TEST COMPLETE")
print("="*60)
print("Next steps:")
print("1. Configure ArcGIS Enterprise connection if needed")
print("2. Add your own feature and imagery layers")
print("3. Integrate with GEE calculations")
print("4. Create custom web maps and applications")
print("5. Publish results to ArcGIS Online/Enterprise")
