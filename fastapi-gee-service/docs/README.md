# FastAPI GEE Service Documentation

## Overview
This FastAPI service provides Google Earth Engine (GEE) tile processing and serves as a bridge between GEE analysis results and MapStore. It handles tile serving, WMTS/WMS capabilities, and dynamic catalog management.

## Architecture

### Core Components
- **Main Application**: `main.py` - FastAPI application with all endpoints
- **Integration Library**: `gee_integration.py` - Simplified interface for GEE-to-MapStore integration
- **Authentication**: Uses GCP service account credentials
- **Caching**: Redis for tile caching and project metadata
- **Tile Serving**: Direct GEE tile proxying with fallback mechanisms

### Docker Integration
- **Container**: `gis_fastapi_dev`
- **Port**: 8001 (external) → 8000 (internal)
- **Network**: `gis_network_dev`
- **Volumes**: 
  - `./fastapi-gee-service:/app` (code)
  - `./backend/user_id.json:/app/user_id.json` (credentials)
  - `gee_tiles_cache_dev:/app/cache` (tile cache)

## Workflow Integration

### From Jupyter Notebook (`02_gee_calculations.ipynb`)

The notebook follows this workflow:

1. **GEE Analysis** (Steps 1-5):
   - Initialize GEE with service account
   - Define AOI (Area of Interest)
   - Create Sentinel-2 cloudless composite
   - Generate analysis products (True Color, False Color, NDVI, EVI, NDWI)
   - Create GEE Map IDs for tile serving

2. **Integration** (Step 8 - Ultra-Simple):
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

3. **What happens internally**:
   - Registers layers with FastAPI (`/catalog/update`)
   - Updates MapStore WMTS configuration (`localConfig.json`)
   - Creates dynamic service: `gee_analysis_mygeeanalysis`
   - Removes old GEE services to prevent conflicts

## API Endpoints

### Core Endpoints
- `GET /health` - Health check
- `GET /` - Root endpoint with service info

### Tile Serving
- `GET /tiles/{project_id}/{z}/{x}/{y}` - Direct tile access
- `GET /tms/{project_id}/{layer}/{z}/{x}/{y}.png` - TMS tile format
- `GET /direct-tile/{project_id}/{layer}/{z}/{x}/{y}` - Bypass WMTS complexity

### OGC Services
- `GET /wmts` - WMTS GetCapabilities and GetTile
- `GET /wms` - WMS GetCapabilities and GetMap
- `GET /csw` - CSW GetCapabilities and GetRecords
- `GET /gwc/service/wmts` - GeoWebCache WMTS compatibility

### Layer Management
- `POST /layers/register` - Register GEE layers
- `GET /layers/{project_id}` - Get project layers
- `POST /catalog/update` - Update MapStore catalog
- `GET /catalog` - List all catalogs

### Search and Discovery
- `GET /search` - Search layers by query
- `GET /catalog/{project_id}` - Get specific catalog info

## Configuration

### Environment Variables
- `REDIS_URL`: Redis connection string
- `POSTGRES_URL`: PostgreSQL connection string  
- `GEE_SERVICE_ACCOUNT`: GCP service account email

### File Structure
```
fastapi-gee-service/
├── main.py                 # Main FastAPI application
├── gee_integration.py      # Integration library
├── requirements.txt        # Python dependencies
├── Dockerfile             # Container build file
├── user_id.json           # GEE credentials (mounted)
├── auth/                  # Authentication modules
├── cache/                 # Cache directory
├── gee_lib/               # GEE library (mounted)
├── test/                  # Test files
├── docs/                  # Documentation
└── archive/               # Obsolete files
```

## Usage Examples

### 1. Direct Tile Access
```bash
curl "http://localhost:8001/tiles/sentinel_analysis_20251023_090335/true_color/10/512/256"
```

### 2. WMTS GetCapabilities
```bash
curl "http://localhost:8001/wmts?service=WMTS&request=GetCapabilities&version=1.0.0"
```

### 3. Register Layers
```bash
curl -X POST "http://localhost:8001/layers/register" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "my_analysis_20250101",
    "project_name": "My GEE Analysis",
    "layers": {
      "true_color": {
        "tile_url": "https://earthengine.googleapis.com/v1/projects/...",
        "name": "True Color",
        "description": "True Color RGB visualization"
      }
    }
  }'
```

## MapStore Integration

### Dynamic WMTS Service
The service creates a dynamic WMTS service in MapStore with:
- **Service ID**: `gee_analysis_{project_name}` (cleaned)
- **URL**: `http://localhost:8001/wmts`
- **Layers**: Automatically discovered from WMTS capabilities
- **Extent**: Based on AOI from GEE analysis

### Configuration Location
- **File**: `/usr/src/app/mapstore/configs/localConfig.json`
- **Path**: `initialState.defaultState.catalog.default.services`
- **Auto-updated**: Each time `process_gee_to_mapstore()` is called

## Error Handling

### Fallback Mechanisms
1. **GEE Tile Failure**: Returns styled fallback tiles
2. **Redis Unavailable**: Continues without caching
3. **Invalid Map IDs**: Creates gradient tiles with layer info
4. **CORS Issues**: Comprehensive CORS headers

### Logging
- **Level**: INFO
- **Format**: Structured logging with timestamps
- **Key Events**: Layer registration, tile requests, errors

## Performance

### Caching Strategy
- **Redis**: Project metadata and layer information
- **Tile Cache**: Persistent volume for frequently accessed tiles
- **Headers**: Cache-busting for development, proper caching for production

### Optimization
- **Async Operations**: All endpoints are async
- **Connection Pooling**: Redis and HTTP connections
- **Lazy Loading**: GEE initialization only when needed

## Development

### Running Locally
```bash
cd fastapi-gee-service
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Docker Development
```bash
docker-compose -f docker-compose.dev.yml up fastapi
```

### Testing
```bash
# Health check
curl http://localhost:8001/health

# Test tile
curl http://localhost:8001/test-tile

# WMTS capabilities
curl "http://localhost:8001/wmts?service=WMTS&request=GetCapabilities"
```

## Troubleshooting

### Common Issues
1. **GEE Authentication**: Check `user_id.json` and service account
2. **Redis Connection**: Verify Redis container is running
3. **Tile Loading**: Check GEE Map IDs are valid and not expired
4. **CORS Errors**: Verify CORS middleware configuration

### Debug Commands
```bash
# Check container status
docker ps | grep fastapi

# View logs
docker logs gis_fastapi_dev

# Test connectivity
docker exec gis_fastapi_dev curl http://localhost:8000/health
```

## Production Considerations

### Security
- Configure CORS origins properly
- Use environment variables for secrets
- Implement authentication/authorization
- Validate input parameters

### Scaling
- Use Redis cluster for caching
- Implement load balancing
- Monitor tile generation performance
- Set up proper logging and monitoring

### Maintenance
- Regular cleanup of expired Map IDs
- Monitor Redis memory usage
- Update GEE service account credentials
- Backup configuration files
