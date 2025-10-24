# Separate WMTS and WFS Services Guide

This guide explains how the enhanced GEE integration creates **separate** WMTS and WFS services in MapStore, ensuring proper service layer separation as requested.

## Overview

The enhanced integration now creates **two distinct services** in MapStore's localConfig.json:

1. **WMTS Service** - For raster data (tiles)
2. **WFS Service** - For vector data (features)

This separation ensures that each service type is properly configured and managed independently.

## Service Configuration Structure

### MapStore localConfig.json Structure

```json
{
  "catalogServices": {
    "gee_wmts_project_name": {
      "type": "wmts",
      "url": "http://fastapi:8000/wmts",
      "version": "1.0.0",
      "title": "GEE WMTS Service - project_name",
      "description": "Google Earth Engine Raster Tiles via WMTS for project_name",
      "authRequired": false,
      "format": "image/png",
      "transparent": true,
      "tileSize": 256
    },
    "gee_wfs_project_name": {
      "type": "wfs",
      "url": "http://fastapi:8000/wfs",
      "version": "2.0.0",
      "title": "GEE WFS Service - project_name",
      "description": "Google Earth Engine Feature Collections via WFS for project_name",
      "authRequired": false,
      "format": "application/json"
    }
  }
}
```

## Key Components

### 1. MapStore Service Manager (`mapstore_service_manager.py`)

**Purpose**: Manages separate WMTS and WFS services in MapStore configuration

**Key Methods**:
- `add_wmts_service()` - Add WMTS service
- `add_wfs_service()` - Add WFS service  
- `add_both_services()` - Add both services
- `remove_project_services()` - Remove project services
- `list_services()` - List all GEE services

### 2. Enhanced WFS Integration (`gee_wfs_integration.py`)

**Purpose**: Processes GEE data and creates separate services

**Key Features**:
- Separate WMTS and WFS service creation
- Independent service management
- Service validation and error handling

### 3. WFS Utilities (`gee_wfs_utils.py`)

**Purpose**: Handle GEE vector data processing for WFS

**Key Features**:
- Feature collection export to GeoJSON
- WFS capabilities generation
- Vector data processing

## Usage Examples

### Basic Usage (Separate Services)

```python
from gee_wfs_integration import process_gee_to_mapstore_with_wfs

# This creates TWO separate services in MapStore
result = process_gee_to_mapstore_with_wfs(
    map_layers=map_layers,           # Creates WMTS service
    vector_layers=vector_layers,    # Creates WFS service
    project_name="My_Project"
)

# Result contains separate service information
print(f"WMTS Updated: {result['mapstore_services']['wmts_updated']}")
print(f"WFS Updated: {result['mapstore_services']['wfs_updated']}")
```

### Service Management

```python
from mapstore_service_manager import MapStoreServiceManager

manager = MapStoreServiceManager()

# Add both services
result = manager.add_both_services("project_name", "http://fastapi:8000")

# List services
services = manager.list_services()
print(f"Services: {services['count']}")

# Remove services
removal = manager.remove_project_services("project_name")
```

## Service Separation Benefits

### 1. **Clear Service Boundaries**
- WMTS for raster tiles only
- WFS for vector features only
- No mixing of service types

### 2. **Independent Management**
- Each service can be configured separately
- Different authentication rules
- Different caching strategies

### 3. **OGC Compliance**
- Proper WMTS 1.0.0 implementation
- Proper WFS 2.0.0 implementation
- Standard service discovery

### 4. **MapStore Integration**
- Services appear separately in catalog
- Independent layer management
- Clear service identification

## Service Naming Convention

### WMTS Services
- **Name**: `gee_wmts_{project_name}`
- **Type**: `wmts`
- **URL**: `{fastapi_url}/wmts`

### WFS Services  
- **Name**: `gee_wfs_{project_name}`
- **Type**: `wfs`
- **URL**: `{fastapi_url}/wfs`

## Configuration Examples

### WMTS Service Configuration
```json
{
  "gee_wmts_forestry_analysis": {
    "type": "wmts",
    "url": "http://fastapi:8000/wmts",
    "version": "1.0.0",
    "title": "GEE WMTS Service - forestry_analysis",
    "description": "Google Earth Engine Raster Tiles via WMTS for forestry_analysis",
    "authRequired": false,
    "format": "image/png",
    "transparent": true,
    "tileSize": 256
  }
}
```

### WFS Service Configuration
```json
{
  "gee_wfs_forestry_analysis": {
    "type": "wfs",
    "url": "http://fastapi:8000/wfs",
    "version": "2.0.0",
    "title": "GEE WFS Service - forestry_analysis",
    "description": "Google Earth Engine Feature Collections via WFS for forestry_analysis",
    "authRequired": false,
    "format": "application/json"
  }
}
```

## Integration Workflow

### 1. **Data Processing**
```python
# Process raster data (creates WMTS service)
raster_result = process_gee_analysis(map_layers, project_name)

# Process vector data (creates WFS service)  
vector_result = process_vector_layers_for_wfs(vector_layers, project_name)
```

### 2. **Service Creation**
```python
# Create separate services in MapStore
service_manager = MapStoreServiceManager()
service_results = service_manager.add_both_services(project_name, fastapi_url)
```

### 3. **Service Validation**
```python
# Verify services were created
services = service_manager.list_services()
assert services['count'] >= 2  # At least WMTS and WFS
```

## Error Handling

### Service Creation Errors
- **WMTS Creation Failed**: Raster data processing continues
- **WFS Creation Failed**: Vector data processing continues
- **Both Failed**: Returns error with details

### Service Management Errors
- **Config File Missing**: Creates minimal configuration
- **Permission Errors**: Logs error and continues
- **Invalid JSON**: Backs up and recreates config

## Testing

### Service Creation Test
```python
# Test service creation
result = process_gee_to_mapstore_with_wfs(
    map_layers=map_layers,
    vector_layers=vector_layers,
    project_name="test_project"
)

# Verify separate services
assert result['separate_services'] == True
assert result['mapstore_services']['wmts_updated'] == True
assert result['mapstore_services']['wfs_updated'] == True
```

### Service Listing Test
```python
# Test service listing
services = list_gee_services_in_mapstore()
assert services['count'] >= 2

# Verify service types
service_types = [s['type'] for s in services['services']]
assert 'wmts' in service_types
assert 'wfs' in service_types
```

## Troubleshooting

### Common Issues

1. **Services Not Created**
   - Check MapStore config path
   - Verify FastAPI service is running
   - Check file permissions

2. **Services Not Visible in MapStore**
   - Restart MapStore application
   - Check service URLs
   - Verify service configuration

3. **WFS Service Not Working**
   - Check WFS endpoint: `http://fastapi:8000/wfs`
   - Verify feature collections
   - Check GeoJSON format

### Debug Commands

```python
# List all services
services = list_gee_services_in_mapstore()
print(f"Services: {services}")

# Test service manager
manager = MapStoreServiceManager()
config = manager.load_config()
print(f"Config: {config['catalogServices']}")
```

## Best Practices

### 1. **Service Naming**
- Use descriptive project names
- Avoid special characters
- Keep names consistent

### 2. **Service Management**
- Remove old services before adding new ones
- Validate service creation
- Monitor service status

### 3. **Error Handling**
- Always check service creation results
- Implement fallback strategies
- Log service operations

## Conclusion

The separate services approach ensures:

✅ **Clear Service Separation** - WMTS and WFS are distinct services  
✅ **Independent Management** - Each service can be managed separately  
✅ **OGC Compliance** - Proper implementation of both standards  
✅ **MapStore Integration** - Services appear correctly in catalog  
✅ **Scalability** - Easy to add/remove services per project  

This approach provides the clean separation you requested while maintaining full functionality for both raster and vector data access.

