# Jupyter Notebooks - GEE Integration Documentation

## Overview
This directory contains Jupyter notebooks and Python modules for Google Earth Engine (GEE) analysis and MapStore integration. The main workflow is implemented in `02_gee_calculations.ipynb` which demonstrates the complete process from GEE analysis to MapStore integration.

## Architecture

### Core Components
- **Main Notebook**: `archieve/02_gee_calculations.ipynb` - Complete GEE analysis workflow
- **Integration Library**: `gee_integration.py` - Simplified GEE-to-MapStore integration
- **WMTS Updater**: `wmts_config_updater.py` - Dynamic WMTS configuration management
- **Catalog Updater**: `gee_catalog_updater.py` - Catalog service management

### Docker Integration
- **Container**: `gis_jupyter_dev`
- **Port**: 8888 (external) → 8888 (internal)
- **Network**: `gis_network_dev`
- **Volumes**: 
  - `./jupyter/notebooks:/usr/src/app/notebooks` (notebooks)
  - `./jupyter/data:/usr/src/app/data` (data)
  - `./jupyter/shared:/usr/src/app/shared` (shared files)
  - `./backend/user_id.json:/usr/src/app/user_id.json` (credentials)
  - `./GEE_notebook_Forestry:/usr/src/app/gee_lib:ro` (GEE library)
  - `./mapstore/configs:/usr/src/app/mapstore/configs` (MapStore config)

## Main Workflow

### `02_gee_calculations.ipynb` - Complete GEE Analysis

This notebook demonstrates the complete workflow from GEE analysis to MapStore integration:

#### **Steps 1-5: GEE Analysis**
1. **Initialize GEE** - Authenticate with GCP service account
2. **Define AOI** - Set Area of Interest (Polygon geometry)
3. **Create Sentinel-2 Composite** - Generate cloudless composite using `gee_lib`
4. **Generate Analysis Products** - Create True Color, False Color, NDVI, EVI, NDWI
5. **Create GEE Map IDs** - Generate tile URLs for serving

#### **Step 6: Visualization**
- Create interactive map with Folium
- Display all analysis layers
- Show layer controls

#### **Step 8: Ultra-Simple Integration**
```python
from gee_integration import process_gee_to_mapstore

# Prepare map layers
simple_map_layers = {
    'true_color': map_ids['true_color']['tile_fetcher'].url_format,
    'ndvi': map_ids['ndvi']['tile_fetcher'].url_format,
    # ... other layers
}

# One-line integration
result = process_gee_to_mapstore(simple_map_layers, "My GEE Analysis")
```

#### **Steps 11-12: Catalog Management**
```python
from gee_catalog_updater import update_mapstore_catalog, GEECatalogUpdater

# Update catalog
catalog_result = update_mapstore_catalog(
    project_id=project_id,
    project_name=layers_data['project_name'],
    map_ids=map_ids,
    vis_params=vis_params,
    aoi_info=aoi_info,
    analysis_params=analysis_params
)

# Manage catalogs
catalog_manager = GEECatalogUpdater("http://fastapi:8000")
catalogs = catalog_manager.list_catalogs()
```

#### **Steps 13-14: WMTS Configuration**
```python
from wmts_config_updater import update_mapstore_wmts_config, get_current_wmts_status

# Update WMTS configuration
wmts_success = update_mapstore_wmts_config(
    project_id=project_id,
    project_name=layers_data['project_name'],
    aoi_info=aoi_info_for_wmts
)

# Check status
current_status = get_current_wmts_status()
```

## Key Files

### **Core Integration Files**

#### `gee_integration.py`
- **Purpose**: Main integration library for GEE-to-MapStore workflow
- **Key Function**: `process_gee_to_mapstore(map_layers, project_name, aoi_info, fastapi_url)`
- **Usage**: Called from Step 8 in notebook
- **Features**:
  - Registers layers with FastAPI
  - Updates MapStore WMTS configuration
  - Handles dynamic service naming
  - Manages old service cleanup

#### `wmts_config_updater.py`
- **Purpose**: Dynamic WMTS configuration management
- **Key Functions**:
  - `update_mapstore_wmts_config()` - Updates localConfig.json
  - `get_current_wmts_status()` - Gets current service status
  - `list_gee_services()` - Lists all GEE services
- **Usage**: Called from Steps 13-14 in notebook
- **Features**:
  - Dynamic service ID generation
  - Automatic old service removal
  - AOI-based extent calculation
  - Service metadata management

#### `gee_catalog_updater.py`
- **Purpose**: Catalog service management
- **Key Functions**:
  - `update_mapstore_catalog()` - Updates catalog services
  - `GEECatalogUpdater` - Catalog management class
- **Usage**: Called from Steps 11-12 in notebook
- **Features**:
  - CSW service management
  - Layer discovery
  - Catalog metadata

### **Supporting Files**

#### `data/` Directory
- Contains analysis configuration files
- Stores project-specific data
- Includes deployment configurations

#### `shared/` Directory
- Shared resources across notebooks
- Common utilities and data

## Workflow Integration

### **From Notebook to MapStore**

1. **GEE Analysis** (Steps 1-5):
   - Uses `gee_lib/` for Sentinel-2 processing
   - Generates Map IDs for tile serving
   - Creates analysis products

2. **Integration** (Step 8):
   - Uses `gee_integration.py`
   - Registers with FastAPI
   - Updates MapStore configuration

3. **Catalog Management** (Steps 11-12):
   - Uses `gee_catalog_updater.py`
   - Manages catalog services
   - Handles layer discovery

4. **WMTS Configuration** (Steps 13-14):
   - Uses `wmts_config_updater.py`
   - Updates localConfig.json
   - Creates dynamic services

### **Docker Environment Paths**

Based on `docker-compose.dev.yml`:

```yaml
jupyter:
  volumes:
    - ./jupyter/notebooks:/usr/src/app/notebooks
    - ./jupyter/data:/usr/src/app/data
    - ./jupyter/shared:/usr/src/app/shared
    - ./backend/user_id.json:/usr/src/app/user_id.json
    - ./GEE_notebook_Forestry:/usr/src/app/gee_lib:ro
    - ./mapstore/configs:/usr/src/app/mapstore/configs
```

## Usage Examples

### **1. Run Complete Workflow**
```bash
# Start Jupyter
docker exec -it gis_jupyter_dev jupyter lab --ip=0.0.0.0 --port=8888 --no-browser --allow-root

# Access at: http://localhost:8888
# Open: notebooks/archieve/02_gee_calculations.ipynb
# Run all cells
```

### **2. Test Integration Library**
```python
import sys
sys.path.append('/usr/src/app/notebooks')
from gee_integration import process_gee_to_mapstore

# Test with sample data
test_layers = {
    'true_color': 'https://earthengine.googleapis.com/v1/projects/.../tiles/{z}/{x}/{y}',
    'ndvi': 'https://earthengine.googleapis.com/v1/projects/.../tiles/{z}/{x}/{y}'
}

result = process_gee_to_mapstore(test_layers, "Test Analysis")
print(f"Status: {result['status']}")
```

### **3. Check WMTS Status**
```python
from wmts_config_updater import get_current_wmts_status, list_gee_services

# Get current status
status = get_current_wmts_status()
if status:
    print(f"Current service: {status['service_id']}")
    print(f"Project: {status['project_name']}")
    print(f"Layers: {len(status['layers_available'])}")

# List all services
services = list_gee_services()
for service in services:
    print(f"Service: {service['service_id']} - {service['title']}")
```

## Configuration

### **Environment Variables**
- `PYTHONPATH`: Includes notebooks, gee_lib, ex_ante_lib
- `JUPYTER_ENABLE_LAB`: Enables JupyterLab
- `JUPYTER_TOKEN`: Authentication token
- `JUPYTER_ALLOW_ROOT`: Allows root access

### **File Structure**
```
jupyter/
├── notebooks/                 # Main notebooks directory
│   ├── gee_integration.py     # Integration library
│   ├── wmts_config_updater.py # WMTS configuration
│   ├── gee_catalog_updater.py # Catalog management
│   ├── archieve/              # Archived notebooks
│   │   └── 02_gee_calculations.ipynb # Main workflow
│   ├── data/                  # Data directory
│   └── shared/                # Shared resources
├── data/                      # Analysis data
├── shared/                    # Shared files
├── docs/                      # Documentation
├── test/                      # Test files
├── archive/                   # Obsolete files
├── Dockerfile                 # Container build
├── requirements.txt           # Dependencies
└── start.sh                   # Startup script
```

## Error Handling

### **Common Issues**
1. **GEE Authentication**: Check `user_id.json` and service account
2. **Import Errors**: Verify Python path includes notebooks directory
3. **File Access**: Check Docker volume mounts
4. **Network Issues**: Verify Docker network connectivity

### **Debug Commands**
```bash
# Check container status
docker ps | grep jupyter

# View logs
docker logs gis_jupyter_dev

# Test imports
docker exec gis_jupyter_dev python3 -c "
import sys
sys.path.append('/usr/src/app/notebooks')
from gee_integration import process_gee_to_mapstore
print('Import successful')
"
```

## Development

### **Adding New Notebooks**
1. Create notebook in `notebooks/` directory
2. Add necessary imports and path setup
3. Use existing integration libraries
4. Test with sample data

### **Extending Integration**
1. Modify `gee_integration.py` for new features
2. Update `wmts_config_updater.py` for configuration changes
3. Test with notebook workflow
4. Update documentation

### **Testing**
```bash
# Run integration tests
docker exec gis_jupyter_dev python3 /usr/src/app/notebooks/test/test_integration.py

# Test specific modules
docker exec gis_jupyter_dev python3 -c "
import sys
sys.path.append('/usr/src/app/notebooks')
from wmts_config_updater import get_current_wmts_status
print(get_current_wmts_status())
"
```

## Production Considerations

### **Security**
- Use proper Jupyter authentication
- Secure GEE credentials
- Validate input parameters
- Implement access controls

### **Performance**
- Monitor memory usage during GEE analysis
- Implement caching for repeated analyses
- Optimize tile generation
- Use appropriate AOI sizes

### **Maintenance**
- Regular cleanup of old analyses
- Monitor disk usage
- Update GEE service account credentials
- Backup important configurations

## Troubleshooting

### **Workflow Issues**
1. **Notebook won't start**: Check Docker container status
2. **Import errors**: Verify Python path configuration
3. **GEE errors**: Check authentication and service account
4. **MapStore integration fails**: Verify FastAPI service is running

### **Integration Issues**
1. **WMTS not updating**: Check file permissions on localConfig.json
2. **Services not appearing**: Verify FastAPI registration
3. **Tiles not loading**: Check GEE Map ID validity
4. **Configuration errors**: Validate JSON syntax

### **Performance Issues**
1. **Slow analysis**: Reduce AOI size or date range
2. **Memory issues**: Process smaller areas or fewer layers
3. **Network timeouts**: Check GEE service status
4. **Cache issues**: Clear Redis cache if needed
