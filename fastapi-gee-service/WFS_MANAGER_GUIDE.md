# 🚀 WFSManager - Simplified Vector Layer Management

## Overview

The `WFSManager` class provides a simple, `Map.addLayer()`-like interface for adding vector layers to your existing WFS service, replacing the manual `/fc/` endpoint approach.

## Quick Start

### Old Approach (Manual)
```python
# Old way - manual GeoJSON conversion and API calls
geojson_data = training_points_ee.getInfo()
name_aoi = 'training_points_dynamic'

link_fastapi = 'http://fastapi:8000/fc/'+name_aoi

response = requests.post(
    link_fastapi,
    json=geojson_data
)
```

### New Approach (Simple)
```python
# New way - simple and intuitive
from wfs_manager import WFSManager

# Create WFS manager
wfs = WFSManager(fastapi_url="http://fastapi:8000", wfs_base_url="http://localhost:8001")

# Add vector layers (similar to Map.addLayer())
wfs.addLayer(AOI, "AOI Boundary")
wfs.addLayer(training_points_ee, "Training Points")

# Publish all layers to WFS
result = wfs.publish()
```

## Key Benefits

- ✅ **Simpler**: No manual GeoJSON conversion
- ✅ **Intuitive**: Similar to `Map.addLayer()` from GEE
- ✅ **Flexible**: Add/remove layers dynamically
- ✅ **Clean**: Method chaining support
- ✅ **Integrated**: Works with existing WFS infrastructure
- ✅ **Auto-conversion**: Handles ee.FeatureCollection → GeoJSON automatically

## Usage Patterns

### 1. Step-by-Step (Recommended)
```python
from wfs_manager import WFSManager

wfs = WFSManager(fastapi_url="http://fastapi:8000", wfs_base_url="http://localhost:8001")
wfs.addLayer(AOI, "AOI Boundary")
wfs.addLayer(training_points_ee, "Training Points")
result = wfs.publish()
```

### 2. Method Chaining (Fluent Interface)
```python
result = (WFSManager(fastapi_url="http://fastapi:8000", wfs_base_url="http://localhost:8001")
          .addLayer(AOI, "AOI Boundary")
          .addLayer(training_points_ee, "Training Points")
          .publish())
```

### 3. Quick Publish (Single Layer)
```python
from wfs_manager import quick_publish_vector

result = quick_publish_vector(
    vector_data=training_points_ee,
    layer_name="Training Points",
    fastapi_url="http://fastapi:8000",
    wfs_base_url="http://localhost:8001"
)
```

### 4. Dynamic Layer Management
```python
wfs = WFSManager()

# Add layers
wfs.addLayer(AOI, "AOI Boundary")
wfs.addLayer(training_points_ee, "Training Points")

# Check what we have
print(f"Layers: {list(wfs.listLayers().keys())}")

# Remove a layer
wfs.removeLayer("Training Points")

# Clear all
wfs.clear()
```

## API Reference

### WFSManager Class

#### Constructor
```python
WFSManager(fastapi_url="http://fastapi:8000", wfs_base_url="http://localhost:8001")
```

#### Methods
- `addLayer(vector_data, layer_name)` - Add a vector layer (ee.FeatureCollection or ee.Geometry)
- `removeLayer(layer_name)` - Remove a layer
- `listLayers()` - List all layers with URLs
- `publish()` - Publish all layers to WFS
- `clear()` - Clear all layers

### Convenience Functions
- `create_wfs_manager(fastapi_url, wfs_base_url)` - Create a new manager
- `quick_publish_vector(vector_data, layer_name, fastapi_url, wfs_base_url)` - Quick single layer publish

## Integration with Existing WFS Infrastructure

The WFSManager works seamlessly with your existing system:

### 1. **FeatureCollection Registry** (`/fc/` endpoints)
- **POST** `/fc/{layer_name}` - Registers vector data
- **GET** `/fc/{layer_name}` - Retrieves GeoJSON
- **DELETE** `/fc/{layer_name}` - Removes layer

### 2. **WFS Service** (`/wfs` endpoints)
- **GetCapabilities**: `http://localhost:8001/wfs?service=WFS&version=1.1.0&request=GetCapabilities`
- **GetFeature**: `http://localhost:8001/wfs?service=WFS&version=1.1.0&request=GetFeature&typename={layer_name}`
- **DescribeFeatureType**: `http://localhost:8001/wfs?service=WFS&version=1.1.0&request=DescribeFeatureType&typename={layer_name}`

### 3. **Service URLs**
- **Internal**: `http://fastapi:8000` (Docker network)
- **External**: `http://localhost:8001` (Public access)

## Example: Replacing Your Current Code

### Current Notebook Code:
```python
# Example GeoJSON data, adding again above (points, not only AOI polygon)
geojson_data = training_points_ee.getInfo() # important this ee.FeatureCollection should convert to geojson first
name_aoi = 'training_points_dynamic'

link_fastapi = 'http://fastapi:8000/fc/'+name_aoi #only from container, not from localhost

# Push to API
response = requests.post(
    link_fastapi, # running in the notebook for now
    json=geojson_data
)
```

### New Simplified Code:
```python
from wfs_manager import WFSManager

# Create WFS manager
wfs = WFSManager(fastapi_url="http://fastapi:8000", wfs_base_url="http://localhost:8001")

# Add layers (auto-converts ee.FeatureCollection to GeoJSON)
wfs.addLayer(training_points_ee, "Training Points Dynamic")
wfs.addLayer(AOI, "AOI Boundary")

# Publish all layers
result = wfs.publish()

# Check results
if result['status'] == 'success':
    print(f"✅ Published {result['successful_layers']} layers")
    for layer_name, layer_result in result['layers'].items():
        print(f"   - {layer_name}: {layer_result['wfs_url']}")
```

## Response Format

The `publish()` method returns:
```python
{
    'status': 'success',  # 'success', 'partial_success', or 'error'
    'total_layers': 2,
    'successful_layers': 2,
    'failed_layers': 0,
    'layers': {
        'training_points_dynamic': {
            'status': 'success',
            'layer_name': 'training_points_dynamic',
            'fc_url': 'http://fastapi:8000/fc/training_points_dynamic',
            'wfs_url': 'http://localhost:8001/wfs?service=WFS&version=1.1.0&request=GetFeature&typename=training_points_dynamic',
            'feature_count': 200,
            'response': {...}
        }
    },
    'service_urls': {
        'wfs_capabilities': 'http://localhost:8001/wfs?service=WFS&version=1.1.0&request=GetCapabilities',
        'wfs_base': 'http://localhost:8001/wfs'
    }
}
```

## Migration Guide

To migrate from the old approach:

1. **Replace** manual GeoJSON conversion + requests.post() calls
2. **With** WFSManager + addLayer() + publish()
3. **Keep** all your existing ee.FeatureCollection and ee.Geometry objects
4. **Use** the same layer names and URLs

The new approach is fully compatible with your existing WFS infrastructure and provides the same functionality with much simpler code.
