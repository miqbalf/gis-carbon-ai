# FastAPI GEE Service - File Organization

## Overview
This document describes the organization of files in the `fastapi-gee-service` directory, based on the actual workflow from `02_gee_calculations.ipynb`.

## Current File Structure

```
fastapi-gee-service/
├── main.py                    # ✅ CORE: Main FastAPI application
├── gee_integration.py         # ✅ CORE: Integration library (used in notebook)
├── requirements.txt           # ✅ CORE: Python dependencies
├── Dockerfile                 # ✅ CORE: Container build file
├── user_id.json              # ✅ CORE: GEE credentials (mounted from backend)
├── auth/                     # ✅ ACTIVE: Authentication modules
│   ├── unified-auth-service.py
│   └── unified-roles-config.json
├── cache/                    # ✅ ACTIVE: Cache directory (Docker volume)
├── gee_lib/                  # ✅ ACTIVE: GEE library (mounted from GEE_notebook_Forestry)
├── test/                     # 🆕 NEW: Test files
│   ├── test_integration.py   # Integration test suite
│   └── run_tests.sh          # Test runner script
├── docs/                     # 🆕 NEW: Documentation
│   ├── README.md             # Complete service documentation
│   └── WORKFLOW.md           # Workflow documentation
├── archive/                  # 🆕 NEW: Obsolete files
│   ├── enhanced_main.py      # Old version of main.py
│   ├── auth_layers.py        # Unused authentication module
│   ├── mapstore_auth_middleware.py  # Unused middleware
│   └── unified_auth_middleware.py   # Unused middleware
└── __pycache__/              # Python cache (auto-generated)
```

## File Categories

### ✅ CORE FILES (Keep in root)
These files are essential for the service to function:

- **`main.py`**: Main FastAPI application with all endpoints
- **`gee_integration.py`**: Integration library used by the notebook
- **`requirements.txt`**: Python dependencies
- **`Dockerfile`**: Container build configuration
- **`user_id.json`**: GEE service account credentials

### ✅ ACTIVE DIRECTORIES
These directories contain actively used code:

- **`auth/`**: Authentication and authorization modules
- **`cache/`**: Tile cache storage (Docker volume)
- **`gee_lib/`**: GEE library (mounted from external directory)

### 🆕 NEW ORGANIZATIONAL DIRECTORIES

#### `test/` - Test Files
- **`test_integration.py`**: Comprehensive integration test suite
- **`run_tests.sh`**: Test runner script for Docker environment

#### `docs/` - Documentation
- **`README.md`**: Complete service documentation with API reference
- **`WORKFLOW.md`**: Step-by-step workflow documentation

#### `archive/` - Obsolete Files
- **`enhanced_main.py`**: Older version of main.py (replaced)
- **`auth_layers.py`**: Unused authentication module
- **`mapstore_auth_middleware.py`**: Unused middleware
- **`unified_auth_middleware.py`**: Unused middleware

## Workflow Integration

### From Jupyter Notebook
The notebook (`02_gee_calculations.ipynb`) uses these files:

1. **GEE Analysis** (Steps 1-5):
   - Uses `gee_lib/` for Sentinel-2 processing
   - Generates Map IDs for tile serving

2. **Integration** (Step 8):
   ```python
   from gee_integration import process_gee_to_mapstore
   result = process_gee_to_mapstore(simple_map_layers, "My GEE Analysis")
   ```

3. **What happens**:
   - Calls FastAPI endpoints in `main.py`
   - Updates MapStore configuration
   - Creates dynamic WMTS service

### Docker Environment
Based on `docker-compose.dev.yml`:

```yaml
fastapi:
  build:
    context: ./fastapi-gee-service
    dockerfile: Dockerfile
  volumes:
    - ./fastapi-gee-service:/app
    - ./backend/user_id.json:/app/user_id.json
    - gee_tiles_cache_dev:/app/cache
    - ./GEE_notebook_Forestry:/app/gee_lib:ro
```

## Key Endpoints Used

### From `main.py`:
- `POST /catalog/update` - Register GEE layers
- `GET /wmts` - WMTS GetCapabilities and GetTile
- `GET /health` - Health check
- `GET /layers/{project_id}` - Get project layers

### From `gee_integration.py`:
- `process_gee_to_mapstore()` - Main integration function
- `GEEIntegrationManager` - Complete integration management

## Testing

### Run Integration Tests
```bash
# From within Docker container
docker exec -it gis_jupyter_dev bash
cd /usr/src/app/fastapi-gee-service/test
./run_tests.sh
```

### Test Coverage
- ✅ FastAPI service health
- ✅ WMTS capabilities
- ✅ GEE integration library
- ✅ WMTS configuration updater
- ✅ MapStore config access
- ✅ Redis connection

## Maintenance

### Adding New Files
- **Core functionality**: Add to root directory
- **Tests**: Add to `test/` directory
- **Documentation**: Add to `docs/` directory
- **Obsolete code**: Move to `archive/` directory

### Removing Files
- **Never delete**: Core files in root
- **Archive instead**: Move obsolete files to `archive/`
- **Clean up**: Remove files from `archive/` after confirming they're not needed

### Updating Documentation
- **API changes**: Update `docs/README.md`
- **Workflow changes**: Update `docs/WORKFLOW.md`
- **New features**: Add to appropriate documentation file

## Benefits of This Organization

### ✅ Clear Separation
- Core files easily identifiable
- Test files organized and runnable
- Documentation comprehensive and accessible
- Obsolete files preserved but not cluttering

### ✅ Easy Maintenance
- Clear file purposes
- Logical directory structure
- Easy to find and update files
- Test suite for validation

### ✅ Development Friendly
- Quick access to core files
- Comprehensive documentation
- Working test suite
- Clean workspace

### ✅ Production Ready
- Essential files in root
- Documentation for deployment
- Test suite for validation
- Clean, organized structure
