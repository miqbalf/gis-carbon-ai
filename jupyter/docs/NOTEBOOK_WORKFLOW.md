# Notebook Workflow Documentation

## Overview
This document describes the complete workflow implemented in `02_gee_calculations.ipynb`, from GEE analysis to MapStore integration.

## Complete Workflow Steps

### **Step 1: Initialize GEE**
```python
def initialize_gee():
    """Initialize GEE using service account credentials"""
    credentials_path = '/usr/src/app/user_id.json'
    
    with open(credentials_path, 'r') as f:
        credentials_data = json.load(f)
    
    service_account = credentials_data['client_email']
    credentials = ee.ServiceAccountCredentials(service_account, credentials_path)
    ee.Initialize(credentials)
    
    print(f"✓ GEE Initialized successfully")
    print(f"  Service Account: {service_account}")
    print(f"  Project ID: {credentials_data['project_id']}")
    
    return True

# Initialize GEE
initialize_gee()
```

**What it does:**
- Loads GCP service account credentials
- Initializes Google Earth Engine
- Verifies authentication

### **Step 2: Define Area of Interest (AOI)**
```python
# Example: A region in Indonesia (Kalimantan)
aoi_coords = [
    [109.5, -1.5],
    [110.5, -1.5],
    [110.5, -0.5],
    [109.5, -0.5],
    [109.5, -1.5]
]

aoi = ee.Geometry.Polygon(aoi_coords)
aoi_center = aoi.centroid().coordinates().getInfo()

print("✓ AOI defined")
print(f"  Center coordinates: {aoi_center}")
print(f"  Area: {aoi.area().divide(1e6).getInfo():.2f} km²")
```

**What it does:**
- Defines polygon coordinates for analysis area
- Creates GEE geometry object
- Calculates center point and area

### **Step 3: Create Cloudless Sentinel-2 Composite**
```python
from osi.image_collection.main import ImageCollection

# Configuration
config = {
    'IsThermal': False,
}

date_start_end = ['2023-01-01', '2023-12-31']
cloud_cover_threshold = 20  # Maximum cloud cover percentage

print("Creating cloudless Sentinel-2 composite...")
print(f"  Date range: {date_start_end[0]} to {date_start_end[1]}")
print(f"  Cloud cover threshold: {cloud_cover_threshold}%")

# Create ImageCollection instance
img_collection = ImageCollection(
    I_satellite='Sentinel',
    region='asia',
    AOI=aoi,
    date_start_end=date_start_end,
    cloud_cover_threshold=cloud_cover_threshold,
    config=config
)

# Get cloud-masked image collection
sentinel_collection = img_collection.image_collection_mask()

# Create median composite (cloudless)
sentinel_composite = img_collection.image_mosaick()

print("✓ Sentinel-2 cloudless composite created")
print(f"  Number of images used: {sentinel_collection.size().getInfo()}")
```

**What it does:**
- Uses `gee_lib` for Sentinel-2 processing
- Applies cloud masking
- Creates median composite for cloudless imagery
- Processes images from specified date range

### **Step 4: Generate Analysis Products**
```python
# True Color RGB (Natural Color)
true_color = sentinel_composite.select(['red', 'green', 'blue'])

# False Color (NIR, Red, Green) - highlights vegetation
false_color = sentinel_composite.select(['nir', 'red', 'green'])

# Calculate NDVI
ndvi = sentinel_composite.normalizedDifference(['nir', 'red']).rename('NDVI')

# Calculate EVI (Enhanced Vegetation Index)
evi = sentinel_composite.expression(
    '2.5 * ((NIR - RED) / (NIR + 6 * RED - 7.5 * BLUE + 1))', {
        'NIR': sentinel_composite.select('nir'),
        'RED': sentinel_composite.select('red'),
        'BLUE': sentinel_composite.select('blue')
    }
).rename('EVI')

# Calculate NDWI (Normalized Difference Water Index)
ndwi = sentinel_composite.normalizedDifference(['green', 'nir']).rename('NDWI')

print("✓ Analysis products generated:")
print("  - True Color RGB")
print("  - False Color Composite")
print("  - NDVI (Normalized Difference Vegetation Index)")
print("  - EVI (Enhanced Vegetation Index)")
print("  - NDWI (Normalized Difference Water Index)")
```

**What it does:**
- Creates True Color RGB visualization
- Generates False Color composite (highlights vegetation)
- Calculates NDVI (vegetation health)
- Calculates EVI (enhanced vegetation index)
- Calculates NDWI (water content)

### **Step 5: Create GEE Map IDs**
```python
# Visualization parameters
vis_params = {
    'true_color': {
        'bands': ['red', 'green', 'blue'],
        'min': 0,
        'max': 0.3,
        'gamma': 1.4
    },
    'false_color': {
        'bands': ['nir', 'red', 'green'],
        'min': 0,
        'max': 0.5,
        'gamma': 1.4
    },
    'ndvi': {
        'min': -0.2,
        'max': 0.8,
        'palette': ['red', 'yellow', 'green', 'darkgreen']
    },
    'evi': {
        'min': -0.2,
        'max': 0.8,
        'palette': ['brown', 'yellow', 'lightgreen', 'darkgreen']
    },
    'ndwi': {
        'min': -0.3,
        'max': 0.3,
        'palette': ['white', 'lightblue', 'blue', 'darkblue']
    }
}

# Generate Map IDs
print("Generating GEE Map IDs...")

map_ids = {}
map_ids['true_color'] = true_color.getMapId(vis_params['true_color'])
map_ids['false_color'] = false_color.getMapId(vis_params['false_color'])
map_ids['ndvi'] = ndvi.getMapId(vis_params['ndvi'])
map_ids['evi'] = evi.getMapId(vis_params['evi'])
map_ids['ndwi'] = ndwi.getMapId(vis_params['ndwi'])

print("✓ Map IDs generated for all layers")

# Display tile URLs
for layer_name, map_id_dict in map_ids.items():
    tile_url = map_id_dict['tile_fetcher'].url_format
    print(f"\n{layer_name.upper()}:")
    print(f"  Tile URL: {tile_url}")
```

**What it does:**
- Defines visualization parameters for each layer
- Generates GEE Map IDs for tile serving
- Creates tile URLs for each analysis product
- Provides URLs for direct tile access

### **Step 6: Visualize on Interactive Map**
```python
import folium

# Create base map
center_lat, center_lon = aoi_center[1], aoi_center[0]
m = folium.Map(location=[center_lat, center_lon], zoom_start=10)

# Add GEE tile layers
for layer_name, map_id_dict in map_ids.items():
    tile_url = map_id_dict['tile_fetcher'].url_format
    folium.TileLayer(
        tiles=tile_url,
        attr='Google Earth Engine',
        name=layer_name.replace('_', ' ').title(),
        overlay=True,
        control=True
    ).add_to(m)

# Add layer control
folium.LayerControl().add_to(m)

print("✓ Interactive map created with all layers")
print(f"  Map centered at: ({center_lat:.4f}, {center_lon:.4f})")

# Display the map
m
```

**What it does:**
- Creates interactive Folium map
- Adds all GEE layers as tile layers
- Centers map on AOI
- Provides layer controls for toggling

### **Step 8: Ultra-Simple Integration**
```python
import sys
sys.path.append('/usr/src/app/notebooks')
from gee_integration import process_gee_to_mapstore

# Prepare map layers for integration
simple_map_layers = {
    'true_color': map_ids['true_color']['tile_fetcher'].url_format,
    'false_color': map_ids['false_color']['tile_fetcher'].url_format,
    'ndvi': map_ids['ndvi']['tile_fetcher'].url_format,
    'evi': map_ids['evi']['tile_fetcher'].url_format,
    'ndwi': map_ids['ndwi']['tile_fetcher'].url_format
}

# One-line integration
result = process_gee_to_mapstore(simple_map_layers, "My GEE Analysis")

print("🎯 Ultra-Simple Integration Result:")
print(f"   Status: {result['status']}")
if result['status'] == 'success':
    print(f"   Project: {result['project_id']}")
    print(f"   Layers: {result['available_layers']}")
    print(f"   MapStore: {result['service_urls']['mapstore_catalog']}")
else:
    print(f"   Error: {result.get('error')}")
```

**What it does:**
- Imports integration library
- Prepares map layers dictionary
- Calls one-line integration function
- Registers with FastAPI
- Updates MapStore configuration
- Creates dynamic WMTS service

### **Steps 11-12: Catalog Management**
```python
import sys
sys.path.append('/usr/src/app/notebooks')
from gee_catalog_updater import update_mapstore_catalog

# Prepare analysis information
analysis_params = {
    'satellite': 'Sentinel-2',
    'cloud_cover_threshold': cloud_cover_threshold,
    'image_count': sentinel_collection.size().getInfo(),
    'date_range': f"{date_start_end[0]} to {date_start_end[1]}"
}

aoi_info = {
    'center': aoi_center,
    'area_km2': aoi.area().divide(1e6).getInfo(),
    'coordinates': aoi_coords
}

print("🔄 Updating MapStore catalog with GEE results...")
print(f"  Project: {project_id}")
print(f"  Analysis: {analysis_params['satellite']} from {analysis_params['date_range']}")

# Update the catalog
catalog_result = update_mapstore_catalog(
    project_id=project_id,
    project_name=layers_data['project_name'],
    map_ids=map_ids,
    vis_params=vis_params,
    aoi_info=aoi_info,
    analysis_params=analysis_params,
    fastapi_url="http://fastapi:8000"
)

if catalog_result:
    print("\n✅ MapStore catalog updated successfully!")
    print("📋 Next steps:")
    print("   1. Go to MapStore: http://localhost:8082/mapstore")
    print("   2. Open the Catalog panel")
    print("   3. Look for 'GEE Dynamic Catalog' service")
    print("   4. Refresh the catalog to see your new layers")
    print("   5. Add layers to your map!")
    print(f"\n🔗 Catalog URL: {catalog_result.get('catalog_url')}")
else:
    print("\n❌ Failed to update MapStore catalog")
    print("   Check that FastAPI service is running")
```

**What it does:**
- Prepares analysis parameters and AOI information
- Updates MapStore catalog with GEE results
- Creates CSW service for layer discovery
- Provides next steps for MapStore usage

### **Steps 13-14: WMTS Configuration**
```python
import sys
sys.path.append('/usr/src/app/notebooks')
from wmts_config_updater import update_mapstore_wmts_config, get_current_wmts_status

# Prepare AOI information for WMTS configuration
aoi_bbox = {
    'minx': min([coord[0] for coord in aoi_coords]),
    'miny': min([coord[1] for coord in aoi_coords]),
    'maxx': max([coord[0] for coord in aoi_coords]),
    'maxy': max([coord[1] for coord in aoi_coords])
}

aoi_info_for_wmts = {
    'bbox': aoi_bbox,
    'center': aoi_center,
    'area_km2': aoi.area().divide(1e6).getInfo(),
    'coordinates': aoi_coords
}

print("🔄 Updating MapStore WMTS configuration...")
print(f"  Project: {project_id}")
print(f"  Analysis: {layers_data['project_name']}")
print(f"  AOI: {aoi_bbox}")

# Update WMTS configuration
wmts_success = update_mapstore_wmts_config(
    project_id=project_id,
    project_name=layers_data['project_name'],
    aoi_info=aoi_info_for_wmts
)

if wmts_success:
    print("\n✅ MapStore WMTS configuration updated successfully!")
    print("📋 WMTS Service Details:")
    print("   Service ID: GEE_analysis_WMTS_layers")
    print("   Type: WMTS (Web Map Tile Service)")
    print("   URL: http://localhost:8001/wmts")
    print("   Layers: Automatically discovered from WMTS GetCapabilities")
    print(f"   Project: {project_id}")
    
    # Show current status
    current_status = get_current_wmts_status()
    if current_status:
        print(f"\n🔍 Current WMTS Service Status:")
        print(f"   Service: {current_status['service_id']}")
        print(f"   Project: {current_status['project_name']}")
        print(f"   Generated: {current_status['generated_at']}")
        print(f"   Available Layers: {len(current_status['layers_available'])}")
        for layer in current_status['layers_available']:
            print(f"     • {layer}")
    
    print("\n📋 Next Steps:")
    print("   1. Go to MapStore: http://localhost:8082/mapstore")
    print("   2. Open the Catalog panel")
    print("   3. Look for 'GEE Analysis WMTS - [Project Name]' service")
    print("   4. Click on the service to see available layers")
    print("   5. Add individual layers to your map!")
    print("\n💡 Benefits of Dynamic WMTS:")
    print("   • Single WMTS service with multiple layers")
    print("   • Automatic layer discovery")
    print("   • No style mixing - each layer has proper styling")
    print("   • Easy to manage - old analyses are automatically replaced")
    
else:
    print("\n❌ Failed to update MapStore WMTS configuration")
    print("   Check that the MapStore config directory is accessible")
    print("   Verify Docker volume mount is working correctly")
```

**What it does:**
- Prepares AOI information for WMTS configuration
- Updates MapStore localConfig.json with WMTS service
- Creates dynamic service with project-specific naming
- Removes old GEE services to prevent conflicts
- Shows current service status and available layers

## What Happens Internally

### **FastAPI Registration**
The `process_gee_to_mapstore()` function:
1. Registers layers with FastAPI (`/catalog/update`)
2. Stores project metadata in Redis
3. Creates layer catalog entries

### **MapStore Configuration Update**
The WMTS updater:
1. Reads `localConfig.json`
2. Removes old GEE services
3. Adds new WMTS service with dynamic ID
4. Sets AOI-based extent
5. Saves updated configuration

### **Dynamic Service Creation**
- **Service ID**: `gee_analysis_{project_name}` (cleaned)
- **Title**: `GEE Analysis WMTS - {project_name}`
- **URL**: `http://localhost:8001/wmts`
- **Layers**: Automatically discovered from WMTS capabilities

## Output and Results

### **GEE Analysis Results**
- **Map IDs**: Generated for all analysis products
- **Tile URLs**: Direct access to GEE tiles
- **Visualization**: Interactive map with all layers

### **Integration Results**
- **FastAPI**: Layers registered and accessible
- **MapStore**: WMTS service created and configured
- **Service URLs**: All endpoints available

### **MapStore Usage**
1. Go to: `http://localhost:8082/mapstore`
2. Open Catalog panel
3. Look for: "GEE Analysis WMTS - [Project Name]"
4. Click service to see available layers
5. Add individual layers to map

## Benefits

### **Complete Workflow**
- ✅ **End-to-End**: From GEE analysis to MapStore integration
- ✅ **Automated**: One-line integration function
- ✅ **Dynamic**: Automatic service management
- ✅ **Persistent**: Survives container restarts

### **Production Ready**
- ✅ **Scalable**: Handles multiple analyses
- ✅ **Reliable**: Error handling and fallbacks
- ✅ **Maintainable**: Clean code organization
- ✅ **Documented**: Comprehensive documentation

### **User Friendly**
- ✅ **Simple**: Easy to use integration
- ✅ **Visual**: Interactive maps and results
- ✅ **Flexible**: Configurable parameters
- ✅ **Informative**: Detailed status and results
