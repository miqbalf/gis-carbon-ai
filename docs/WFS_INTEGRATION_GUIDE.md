# GEE WFS Integration Guide

This guide explains how to use the enhanced GEE integration that now supports both WMTS (Web Map Tile Service) for raster data and WFS (Web Feature Service) for vector data.

## Overview

The enhanced GEE integration provides:

- **WMTS Support**: Existing functionality for raster data visualization
- **WFS Support**: New functionality for vector data access
- **Backward Compatibility**: Original functions still work
- **OGC Standards**: Full WFS 2.0.0 compliance
- **Geemap Integration**: Uses geemap for vector data processing

## Key Components

### 1. WFS Utilities (`gee_wfs_utils.py`)
- `GEEWFSManager`: Main class for WFS operations
- `export_gee_feature_collection_to_geojson()`: Export GEE FeatureCollections to GeoJSON
- `create_wfs_feature_type_info()`: Create WFS feature type information
- `process_gee_vector_to_wfs()`: Process GEE vectors for WFS integration

### 2. Enhanced Integration (`gee_wfs_integration.py`)
- `GEEWFSIntegrationManager`: Enhanced integration manager
- `process_gee_to_mapstore_with_wfs()`: Main function for combined WMTS+WFS processing
- `process_gee_to_mapstore_enhanced()`: Backward-compatible enhanced version

### 3. FastAPI WFS Endpoints (`main.py`)
- `GET /wfs`: WFS service endpoint
- `GetCapabilities`: WFS capabilities response
- `GetFeature`: Feature data retrieval
- `DescribeFeatureType`: Feature type schema

## Usage Examples

### Basic Usage (Raster Only - Existing Functionality)

```python
from gee_integration import process_gee_to_mapstore

# Prepare raster layers
map_layers = {
    'sentinel_mosaicked': 'https://earthengine.googleapis.com/v1/projects/ee-iwansetiawan/maps/.../tiles/{z}/{x}/{y}'
}

# Process with original function
result = process_gee_to_mapstore(
    map_layers=map_layers,
    project_name="My Project",
    aoi_info=aoi_info
)
```

### Enhanced Usage (Raster + Vector)

```python
from gee_wfs_integration import process_gee_to_mapstore_with_wfs
import ee

# Prepare raster layers
map_layers = {
    'sentinel_mosaicked': 'https://earthengine.googleapis.com/v1/projects/ee-iwansetiawan/maps/.../tiles/{z}/{x}/{y}'
}

# Prepare vector layers
sample_points = ee.FeatureCollection([
    ee.Feature(ee.Geometry.Point([110.463, -1.804]), {'id': 1, 'name': 'Point 1', 'value': 100}),
    ee.Feature(ee.Geometry.Point([110.470, -1.810]), {'id': 2, 'name': 'Point 2', 'value': 200})
])

vector_layers = {
    'sample_points': {
        'feature_collection': sample_points,
        'name': 'Sample Points',
        'description': 'Sample point features'
    }
}

# Process with enhanced function
result = process_gee_to_mapstore_with_wfs(
    map_layers=map_layers,
    vector_layers=vector_layers,
    project_name="Enhanced Project",
    aoi_info=aoi_info
)
```

### Vector Only (WFS Only)

```python
# Process only vector layers
result = process_gee_to_mapstore_with_wfs(
    map_layers={},  # Empty for raster-only
    vector_layers=vector_layers,
    project_name="Vector Only Project",
    aoi_info=aoi_info
)
```

## WFS Service Endpoints

### GetCapabilities
```
GET http://fastapi:8000/wfs?service=WFS&version=2.0.0&request=GetCapabilities
```

### GetFeature
```
GET http://fastapi:8000/wfs?service=WFS&version=2.0.0&request=GetFeature&typename=gee:project_name_layer_name&outputformat=application/json
```

### DescribeFeatureType
```
GET http://fastapi:8000/wfs?service=WFS&version=2.0.0&request=DescribeFeatureType&typename=gee:project_name_layer_name
```

## Response Format

The enhanced integration returns:

```python
{
    "status": "success",
    "project_id": "project_name_timestamp",
    "wmts_services": {
        "wmts_service_url": "http://fastapi:8000/wmts",
        "total_raster_layers": 1,
        "raster_endpoints": [...]
    },
    "wfs_services": {
        "wfs_service_url": "http://fastapi:8000/wfs",
        "total_vector_layers": 1,
        "wfs_endpoints": [
            {
                "layer_name": "sample_points",
                "endpoint": "http://fastapi:8000/wfs?service=WFS&version=2.0.0&request=GetFeature&typename=gee:project_name_sample_points",
                "feature_count": 2
            }
        ]
    },
    "has_vector_layers": True,
    "vector_layer_count": 1
}
```

## Integration with MapStore

The enhanced integration automatically:

1. **Registers WMTS services** with MapStore for raster visualization
2. **Registers WFS services** with MapStore for vector data access
3. **Updates MapStore configuration** to include both service types
4. **Provides OGC-compliant endpoints** for standard GIS clients

## Advanced Usage

### Custom WFS Processing

```python
from gee_wfs_utils import GEEWFSManager

wfs_manager = GEEWFSManager()

# Export feature collection to GeoJSON
geojson_data = wfs_manager.export_gee_feature_collection_to_geojson(
    feature_collection=my_feature_collection,
    aoi=my_aoi_geometry,
    max_features=1000
)

# Create WFS feature type info
feature_type_info = wfs_manager.create_wfs_feature_type_info(
    feature_collection=my_feature_collection,
    layer_name="my_layer",
    project_name="my_project"
)
```

### Direct WFS Manager Usage

```python
from gee_wfs_integration import GEEWFSIntegrationManager

manager = GEEWFSIntegrationManager(fastapi_url="http://fastapi:8000")

# Process with custom settings
result = manager.process_gee_analysis_with_wfs(
    map_layers=map_layers,
    vector_layers=vector_layers,
    project_name="Custom Project",
    aoi_info=aoi_info,
    clear_cache_first=True
)
```

## Testing

Use the provided test notebook (`test_wfs_integration.ipynb`) to:

1. Test WFS utilities
2. Test enhanced integration
3. Test WFS endpoints
4. Compare with original integration

## Dependencies

The WFS integration requires:

- `earthengine-api`: GEE Python API
- `geemap`: Geospatial analysis and visualization
- `geopandas`: Geospatial data processing
- `shapely`: Geometric operations
- `pandas`: Data manipulation

## Error Handling

The integration includes comprehensive error handling:

- **GEE Authentication**: Automatic credential management
- **Feature Collection Processing**: Graceful handling of invalid geometries
- **WFS Service Errors**: Proper HTTP status codes and error messages
- **Cache Management**: Automatic cleanup and error recovery

## Performance Considerations

- **Feature Limits**: Default max 1000 features per request
- **Caching**: Redis-based caching for improved performance
- **Pagination**: WFS supports paging for large datasets
- **Bbox Filtering**: Spatial filtering for reduced data transfer

## Future Enhancements

Planned improvements include:

- **Transaction Support**: WFS-T for feature editing
- **Advanced Filtering**: CQL and OGC filters
- **Multiple Formats**: Support for GML, KML, Shapefile
- **Real-time Updates**: Live feature collection updates
- **Authentication**: Secure WFS endpoints

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all dependencies are installed
2. **GEE Authentication**: Check service account credentials
3. **Feature Collection**: Verify GEE FeatureCollection is valid
4. **WFS Endpoints**: Ensure FastAPI service is running

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Support

For issues and questions:

1. Check the test notebook for examples
2. Review the FastAPI service logs
3. Verify GEE authentication
4. Test with sample data first

## Conclusion

The enhanced GEE integration provides a complete solution for both raster and vector data visualization through standard OGC services. It maintains backward compatibility while adding powerful new WFS capabilities for vector data access and analysis.

