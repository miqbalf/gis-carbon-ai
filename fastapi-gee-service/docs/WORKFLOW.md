# GEE-to-MapStore Workflow Documentation

## Overview
This document describes the complete workflow from GEE analysis to MapStore integration, based on the actual implementation in `02_gee_calculations.ipynb`.

## Workflow Steps

### 1. GEE Analysis (Steps 1-5 in Notebook)

#### Step 1: Initialize GEE
```python
def initialize_gee():
    credentials_path = '/usr/src/app/user_id.json'
    with open(credentials_path, 'r') as f:
        credentials_data = json.load(f)
    
    service_account = credentials_data['client_email']
    credentials = ee.ServiceAccountCredentials(service_account, credentials_path)
    ee.Initialize(credentials)
```

#### Step 2: Define AOI
```python
aoi_coords = [
    [109.5, -1.5],
    [110.5, -1.5], 
    [110.5, -0.5],
    [109.5, -0.5],
    [109.5, -1.5]
]
aoi = ee.Geometry.Polygon(aoi_coords)
```

#### Step 3: Create Sentinel-2 Composite
```python
from osi.image_collection.main import ImageCollection

img_collection = ImageCollection(
    I_satellite='Sentinel',
    region='asia',
    AOI=aoi,
    date_start_end=['2023-01-01', '2023-12-31'],
    cloud_cover_threshold=20,
    config={'IsThermal': False}
)

sentinel_collection = img_collection.image_collection_mask()
sentinel_composite = img_collection.image_mosaick()
```

#### Step 4: Generate Analysis Products
```python
# True Color RGB
true_color = sentinel_composite.select(['red', 'green', 'blue'])

# False Color (NIR, Red, Green)
false_color = sentinel_composite.select(['nir', 'red', 'green'])

# NDVI
ndvi = sentinel_composite.normalizedDifference(['nir', 'red']).rename('NDVI')

# EVI
evi = sentinel_composite.expression(
    '2.5 * ((NIR - RED) / (NIR + 6 * RED - 7.5 * BLUE + 1))', {
        'NIR': sentinel_composite.select('nir'),
        'RED': sentinel_composite.select('red'),
        'BLUE': sentinel_composite.select('blue')
    }
).rename('EVI')

# NDWI
ndwi = sentinel_composite.normalizedDifference(['green', 'nir']).rename('NDWI')
```

#### Step 5: Create GEE Map IDs
```python
vis_params = {
    'true_color': {'bands': ['red', 'green', 'blue'], 'min': 0, 'max': 0.3, 'gamma': 1.4},
    'false_color': {'bands': ['nir', 'red', 'green'], 'min': 0, 'max': 0.5, 'gamma': 1.4},
    'ndvi': {'min': -0.2, 'max': 0.8, 'palette': ['red', 'yellow', 'green', 'darkgreen']},
    'evi': {'min': -0.2, 'max': 0.8, 'palette': ['brown', 'yellow', 'lightgreen', 'darkgreen']},
    'ndwi': {'min': -0.3, 'max': 0.3, 'palette': ['white', 'lightblue', 'blue', 'darkblue']}
}

map_ids = {}
map_ids['true_color'] = true_color.getMapId(vis_params['true_color'])
map_ids['false_color'] = false_color.getMapId(vis_params['false_color'])
map_ids['ndvi'] = ndvi.getMapId(vis_params['ndvi'])
map_ids['evi'] = evi.getMapId(vis_params['evi'])
map_ids['ndwi'] = ndwi.getMapId(vis_params['ndwi'])
```

### 2. Integration (Step 8 - Ultra-Simple)

#### Import Integration Library
```python
import sys
sys.path.append('/usr/src/app/notebooks')
from gee_integration import process_gee_to_mapstore
```

#### Prepare Map Layers
```python
simple_map_layers = {
    'true_color': map_ids['true_color']['tile_fetcher'].url_format,
    'false_color': map_ids['false_color']['tile_fetcher'].url_format,
    'ndvi': map_ids['ndvi']['tile_fetcher'].url_format,
    'evi': map_ids['evi']['tile_fetcher'].url_format,
    'ndwi': map_ids['ndwi']['tile_fetcher'].url_format
}
```

#### One-Line Integration
```python
result = process_gee_to_mapstore(simple_map_layers, "My GEE Analysis")
```

### 3. What Happens Internally

#### 3.1 FastAPI Registration
The `process_gee_to_mapstore()` function calls:
```python
# POST /catalog/update
{
    "project_id": "sentinel_analysis_20251023_090335",
    "project_name": "My GEE Analysis",
    "analysis_info": {
        "aoi": {
            "bbox": {"minx": 109.5, "miny": -1.5, "maxx": 110.5, "maxy": -0.5},
            "center": [110.0, -1.0]
        },
        "generated_at": "2025-10-23T09:03:35.504275"
    },
    "layers": {
        "true_color": {
            "tile_url": "https://earthengine.googleapis.com/v1/projects/...",
            "name": "True Color",
            "description": "TRUE_COLOR visualization from GEE analysis"
        }
        // ... other layers
    }
}
```

#### 3.2 MapStore WMTS Configuration Update
The function updates `localConfig.json`:
```json
{
    "initialState": {
        "defaultState": {
            "catalog": {
                "default": {
                    "services": {
                        "gee_analysis_mygeeanalysis": {
                            "url": "http://localhost:8001/wmts",
                            "type": "wmts",
                            "title": "GEE Analysis WMTS - My GEE Analysis",
                            "autoload": false,
                            "params": {
                                "LAYERS": "sentinel_analysis_20251023_090335",
                                "TILEMATRIXSET": "GoogleMapsCompatible",
                                "FORMAT": "image/png"
                            },
                            "extent": [109.5, -1.5, 110.5, -0.5],
                            "metadata": {
                                "project_id": "sentinel_analysis_20251023_090335",
                                "project_name": "My GEE Analysis",
                                "service_type": "dynamic_gee_wmts",
                                "layers_available": [
                                    "sentinel_analysis_20251023_090335_true_color",
                                    "sentinel_analysis_20251023_090335_false_color",
                                    "sentinel_analysis_20251023_090335_ndvi",
                                    "sentinel_analysis_20251023_090335_evi",
                                    "sentinel_analysis_20251023_090335_ndwi"
                                ]
                            }
                        }
                    }
                }
            }
        }
    }
}
```

### 4. MapStore Usage

#### 4.1 Access MapStore
1. Go to: `http://localhost:8082/mapstore`
2. Open the Catalog panel
3. Look for: "GEE Analysis WMTS - My GEE Analysis"
4. Click on the service to see available layers
5. Add individual layers to your map

#### 4.2 Available Layers
- **True Color**: Natural RGB visualization
- **False Color**: NIR-Red-Green composite (highlights vegetation)
- **NDVI**: Normalized Difference Vegetation Index
- **EVI**: Enhanced Vegetation Index  
- **NDWI**: Normalized Difference Water Index

## File Structure

### Docker Environment Paths
Based on `docker-compose.dev.yml`:

```
# FastAPI Service
./fastapi-gee-service:/app

# Jupyter Notebook
./jupyter/notebooks:/usr/src/app/notebooks

# MapStore Config
./mapstore/config:/usr/src/app/mapstore/config

# GEE Library
./GEE_notebook_Forestry:/usr/src/app/gee_lib:ro

# Credentials
./backend/user_id.json:/usr/src/app/user_id.json
```

### Key Files
- **Notebook**: `/usr/src/app/notebooks/archieve/02_gee_calculations.ipynb`
- **Integration**: `/usr/src/app/notebooks/gee_integration.py`
- **WMTS Updater**: `/usr/src/app/notebooks/wmts_config_updater.py`
- **MapStore Config**: `/usr/src/app/mapstore/config/localConfig.json`
- **FastAPI Main**: `/app/main.py`
- **FastAPI Integration**: `/app/gee_integration.py`

## Network Configuration

### Docker Network
- **Network**: `gis_network_dev`
- **FastAPI**: `http://fastapi:8000` (internal)
- **MapStore**: `http://localhost:8082` (external)
- **Redis**: `redis:6379` (internal)

### Service URLs
- **FastAPI External**: `http://localhost:8001`
- **FastAPI Internal**: `http://fastapi:8000`
- **MapStore**: `http://localhost:8082/mapstore`
- **WMTS Service**: `http://localhost:8001/wmts`

## Error Handling

### Common Issues
1. **GEE Map ID Expiration**: Re-run notebook to generate fresh Map IDs
2. **Redis Connection**: Check Redis container is running
3. **File Permissions**: Ensure MapStore config is writable
4. **Network Issues**: Verify Docker network connectivity

### Debug Steps
1. Check container status: `docker ps | grep fastapi`
2. View FastAPI logs: `docker logs gis_fastapi_dev`
3. Test health endpoint: `curl http://localhost:8001/health`
4. Verify WMTS: `curl "http://localhost:8001/wmts?service=WMTS&request=GetCapabilities"`

## Benefits

### Dynamic Integration
- ✅ **One-Line Integration**: Simple function call
- ✅ **Automatic Management**: Old services replaced automatically
- ✅ **Dynamic Naming**: Service IDs based on project names
- ✅ **No Manual Config**: Everything handled programmatically

### Performance
- ✅ **Direct GEE Tiles**: No intermediate processing
- ✅ **Redis Caching**: Fast metadata access
- ✅ **Fallback Tiles**: Graceful degradation
- ✅ **CORS Support**: Proper browser compatibility

### MapStore Integration
- ✅ **WMTS Standard**: Full OGC compliance
- ✅ **Layer Discovery**: Automatic layer enumeration
- ✅ **Proper Styling**: Each layer correctly styled
- ✅ **No Conflicts**: Clean service management
