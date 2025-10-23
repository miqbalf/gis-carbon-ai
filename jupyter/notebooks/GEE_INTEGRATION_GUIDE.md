# GEE Integration Guide

## 🚀 Simplified GEE-to-MapStore Integration

This guide shows how to use the new **GEE Integration Library** to seamlessly connect your GEE analysis results with MapStore.

## 📋 Quick Start

### Option 1: Ultra-Simple (One Line)
```python
from gee_integration import process_gee_to_mapstore

# Just provide your map layers
map_layers = {
    'true_color': 'https://earthengine.googleapis.com/v1/projects/earthengine-legacy/maps/your_map_id/tiles/{z}/{x}/{y}',
    'ndvi': 'https://earthengine.googleapis.com/v1/projects/earthengine-legacy/maps/your_ndvi_id/tiles/{z}/{x}/{y}'
}

# One line integration!
result = process_gee_to_mapstore(map_layers, "My GEE Analysis")
```

### Option 2: Detailed Integration
```python
from gee_integration import process_gee_to_mapstore

# Prepare your map layers with metadata
map_layers = {
    'true_color': {
        'tile_url': 'https://earthengine.googleapis.com/v1/projects/earthengine-legacy/maps/your_map_id/tiles/{z}/{x}/{y}',
        'name': 'True Color',
        'description': 'True Color RGB visualization',
        'vis_params': {'bands': ['red', 'green', 'blue'], 'min': 0, 'max': 0.3}
    },
    'ndvi': {
        'tile_url': 'https://earthengine.googleapis.com/v1/projects/earthengine-legacy/maps/your_ndvi_id/tiles/{z}/{x}/{y}',
        'name': 'NDVI',
        'description': 'Normalized Difference Vegetation Index',
        'vis_params': {'min': -0.2, 'max': 0.8, 'palette': ['red', 'yellow', 'green']}
    }
}

# Optional: Provide AOI information
aoi_info = {
    'bbox': {'minx': 109.5, 'miny': -1.5, 'maxx': 110.5, 'maxy': -0.5},
    'center': [110.0, -1.0]
}

# Process integration
result = process_gee_to_mapstore(
    map_layers=map_layers,
    project_name="My GEE Analysis",
    aoi_info=aoi_info
)
```

## 🎯 What the Integration Library Does

The `process_gee_to_mapstore()` function automatically:

1. **Generates Project ID** - Creates unique project identifier
2. **Registers with FastAPI** - Stores layer information in Redis
3. **Updates MapStore WMTS** - Configures WMTS service in localConfig.json
4. **Removes Old Services** - Prevents conflicts with previous analyses
5. **Returns Status** - Provides comprehensive results and URLs

## 📊 Integration Results

```python
result = process_gee_to_mapstore(map_layers, "My Analysis")

if result['status'] == 'success':
    print(f"✅ Project ID: {result['project_id']}")
    print(f"📋 Available Layers: {result['available_layers']}")
    print(f"🔗 MapStore URL: {result['service_urls']['mapstore_catalog']}")
    print(f"📡 FastAPI Status: {result['fastapi_registration']['status']}")
    print(f"🗺️ WMTS Status: {result['wmts_configuration']['status']}")
```

## 🎮 Using in MapStore

After running the integration:

1. **Go to MapStore**: `http://localhost:8082/mapstore`
2. **Open Catalog Panel**
3. **Look for**: "GEE Analysis WMTS - [Your Project Name]"
4. **Click the Service** - See all available layers
5. **Add Layers** - Each layer has proper styling, no mixing!

## 🔧 Advanced Usage

### Custom FastAPI URL
```python
result = process_gee_to_mapstore(
    map_layers=map_layers,
    project_name="My Analysis",
    fastapi_url="http://custom-fastapi:8000"
)
```

### Check Service Status
```python
from gee_integration import GEEIntegrationManager

manager = GEEIntegrationManager()
status = manager.get_service_status()

print(f"FastAPI: {status['fastapi']['status']}")
print(f"WMTS: {status['wmts']['status']}")
```

## 🎯 Benefits

- ✅ **One-Line Integration** - Simple function call
- ✅ **Automatic Management** - Old analyses replaced automatically
- ✅ **No Style Mixing** - Each layer properly styled
- ✅ **Dynamic Discovery** - Layers discovered from WMTS capabilities
- ✅ **Error Handling** - Comprehensive error reporting
- ✅ **Status Monitoring** - Check service health

## 📝 Example Notebook Usage

```python
# In your GEE analysis notebook
import sys
sys.path.append('/usr/src/app/notebooks')
from gee_integration import process_gee_to_mapstore

# After generating your GEE map IDs
map_layers = {}
for layer_name, map_id_dict in map_ids.items():
    map_layers[layer_name] = map_id_dict['tile_fetcher'].url_format

# One line to integrate everything!
result = process_gee_to_mapstore(map_layers, "My GEE Analysis")

if result['status'] == 'success':
    print("🎉 Ready for MapStore!")
    print(f"Go to: {result['service_urls']['mapstore_catalog']}")
```

## 🚨 Troubleshooting

### Common Issues

1. **FastAPI Connection Error**
   - Check: `docker ps | grep fastapi`
   - Verify: FastAPI service is running

2. **WMTS Configuration Error**
   - Check: MapStore config directory is mounted
   - Verify: `localConfig.json` is writable

3. **Layer Not Showing**
   - Check: GEE Map IDs are valid
   - Verify: WMTS service is active in MapStore

### Debug Commands

```python
# Check service status
from gee_integration import GEEIntegrationManager
manager = GEEIntegrationManager()
status = manager.get_service_status()
print(status)
```

## 🎉 Success!

Your GEE analysis is now seamlessly integrated with MapStore! The integration library handles all the complex configuration automatically, giving you a clean, simple interface to connect your GEE results with MapStore.
