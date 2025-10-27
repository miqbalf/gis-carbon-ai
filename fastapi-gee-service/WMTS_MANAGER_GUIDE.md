# 🚀 WMTSManager - Simplified GEE Layer Management

## Overview

The `WMTSManager` class provides a simple, `Map.addLayer()`-like interface for adding GEE layers to WMTS services, replacing the complex `map_layers` dictionary approach.

## Quick Start

### Old Approach (Complex)
```python
# Old way - managing dictionaries
map_layers = generate_map_id(
    {layer_name: vis_param, fcd1_1_layer_name: fcd_visparams, fcd2_1_layer_name: fcd_visparams}, 
    {layer_name: image_mosaick, fcd1_1_layer_name: FCD1_1, fcd2_1_layer_name: FCD2_1}
)['map_layers']

result = list_layers_to_wmts(map_layers, AOI)
```

### New Approach (Simple)
```python
# New way - simple and intuitive
from wmts_manager import WMTSManager

# Create WMTS manager (similar to creating a Map object)
wmts = WMTSManager(project_name=project_name, aoi=AOI)

# Add layers one by one (similar to Map.addLayer())
wmts.addLayer(image_mosaick, vis_param, layer_name)
wmts.addLayer(FCD1_1, fcd_visparams, fcd1_1_layer_name)
wmts.addLayer(FCD2_1, fcd_visparams, fcd2_1_layer_name)

# Publish all layers to WMTS
result = wmts.publish()
```

## Key Benefits

- ✅ **Simpler**: No dictionary management
- ✅ **Intuitive**: Similar to `Map.addLayer()` from GEE
- ✅ **Flexible**: Add/remove layers dynamically
- ✅ **Clean**: Method chaining support
- ✅ **Maintainable**: Easier to debug and modify

## Usage Patterns

### 1. Step-by-Step (Recommended)
```python
from wmts_manager import WMTSManager

wmts = WMTSManager(project_name="My Analysis", aoi=AOI)
wmts.addLayer(image_mosaick, vis_param, "True Color")
wmts.addLayer(FCD1_1, fcd_visparams, "Forest Cover Density")
result = wmts.publish()
```

### 2. Method Chaining (Fluent Interface)
```python
result = (WMTSManager(project_name="My Analysis", aoi=AOI)
          .addLayer(image_mosaick, vis_param, "True Color")
          .addLayer(FCD1_1, fcd_visparams, "Forest Cover Density")
          .publish())
```

### 3. Quick Publish (Single Layer)
```python
from wmts_manager import quick_publish

result = quick_publish(
    image=FCD1_1,
    vis_params=fcd_visparams,
    layer_name="Forest Cover Density",
    project_name="Quick Analysis",
    aoi=AOI
)
```

### 4. Dynamic Layer Management
```python
wmts = WMTSManager(project_name="Dynamic Analysis")

# Add layers
wmts.addLayer(image_mosaick, vis_param, "Base Image")
wmts.addLayer(FCD1_1, fcd_visparams, "Forest Cover")

# Check what we have
print(f"Layers: {list(wmts.listLayers().keys())}")

# Remove a layer
wmts.removeLayer("Forest Cover")

# Clear all
wmts.clear()
```

## API Reference

### WMTSManager Class

#### Constructor
```python
WMTSManager(project_name="GEE Analysis", aoi=None, fastapi_url=None, clear_cache_first=True)
```

#### Methods
- `addLayer(image, vis_params, layer_name)` - Add a GEE layer
- `removeLayer(layer_name)` - Remove a layer
- `listLayers()` - List all layers
- `publish()` - Publish all layers to WMTS
- `clear()` - Clear all layers

### Convenience Functions
- `create_wmts_manager(project_name, aoi)` - Create a new manager
- `quick_publish(image, vis_params, layer_name, project_name, aoi)` - Quick single layer publish

## Integration with Existing Code

To migrate from the old approach:

1. **Replace** `generate_map_id()` + `list_layers_to_wmts()` calls
2. **With** `WMTSManager` + `addLayer()` + `publish()`
3. **Keep** all your existing GEE images and visualization parameters
4. **Use** the same AOI and project names

The new approach is fully compatible with your existing GEE analysis pipeline and provides the same WMTS integration results with much simpler code.
