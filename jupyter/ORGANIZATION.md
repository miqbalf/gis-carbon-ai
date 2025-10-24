# Jupyter Notebooks - File Organization

## Overview
This document describes the organization of files in the `jupyter` directory, based on the actual workflow from `02_gee_calculations.ipynb`.

## Current File Structure

```
jupyter/
├── notebooks/                 # ✅ ACTIVE: Main notebooks directory
│   ├── gee_integration.py     # ✅ CORE: Integration library (used in notebook)
│   ├── wmts_config_updater.py # ✅ CORE: WMTS configuration management
│   ├── gee_catalog_updater.py # ✅ CORE: Catalog service management
│   ├── archieve/              # ✅ ACTIVE: Archived notebooks
│   │   ├── 02_gee_calculations.ipynb # ✅ CORE: Main workflow notebook
│   │   ├── 02_gee_calculations.py    # 📁 ARCHIVE: Python version
│   │   ├── 03_arcgis_integration.py  # 📁 ARCHIVE: Unused integration
│   │   ├── add_to_mapstore.py        # 📁 ARCHIVE: Old approach
│   │   ├── example_api_usage.py      # 📁 ARCHIVE: Example only
│   │   ├── test_gee_integration.py   # 📁 ARCHIVE: Old test
│   │   ├── 01_dynamic_baseline.ipynb # 📁 ARCHIVE: Not used in main workflow
│   │   └── mapstore_config_updater.py # 📁 ARCHIVE: Replaced by wmts_config_updater
│   ├── data/                  # ✅ ACTIVE: Data directory
│   └── shared/                # ✅ ACTIVE: Shared resources
├── data/                      # ✅ ACTIVE: Analysis data
│   ├── sentinel_analysis_*_config.json # Analysis configurations
│   └── sentinel_analysis_*_fastapi_wms_endpoints.py # FastAPI endpoints
├── shared/                    # ✅ ACTIVE: Shared files
├── docs/                      # 🆕 NEW: Documentation
│   ├── README.md              # Complete service documentation
│   ├── NOTEBOOK_WORKFLOW.md   # Detailed workflow documentation
│   ├── GEE_INTEGRATION_GUIDE.md # Integration guide
│   ├── INDEX.md               # Index documentation
│   ├── QUICK_REFERENCE.md     # Quick reference
│   ├── README_GEE_WORKFLOW.md # GEE workflow documentation
│   └── SETUP_COMPLETE.md      # Setup documentation
├── test/                      # 🆕 NEW: Test files
│   ├── test_notebook_integration.py # Comprehensive test suite
│   └── run_tests.sh           # Test runner script
├── Dockerfile                 # ✅ CORE: Container build file
├── requirements.txt           # ✅ CORE: Python dependencies
├── start.sh                   # ✅ CORE: Startup script
└── ORGANIZATION.md            # 📋 This organization guide
```

## File Categories

### ✅ CORE FILES (Essential for workflow)
These files are essential for the notebook workflow to function:

- **`notebooks/archieve/02_gee_calculations.ipynb`**: Main workflow notebook
- **`notebooks/gee_integration.py`**: Integration library used in Step 8
- **`notebooks/wmts_config_updater.py`**: WMTS configuration used in Steps 13-14
- **`notebooks/gee_catalog_updater.py`**: Catalog management used in Steps 11-12
- **`Dockerfile`**: Container build configuration
- **`requirements.txt`**: Python dependencies
- **`start.sh`**: Container startup script

### ✅ ACTIVE DIRECTORIES
These directories contain actively used code and data:

- **`notebooks/`**: Main notebooks and integration modules
- **`notebooks/archieve/`**: Archived notebooks (including main workflow)
- **`notebooks/data/`**: Notebook-specific data
- **`notebooks/shared/`**: Shared notebook resources
- **`data/`**: Analysis data and configurations
- **`shared/`**: Shared files across the system

### 🆕 NEW ORGANIZATIONAL DIRECTORIES

#### `docs/` - Documentation
- **`README.md`**: Complete service documentation with API reference
- **`NOTEBOOK_WORKFLOW.md`**: Detailed step-by-step workflow documentation
- **`GEE_INTEGRATION_GUIDE.md`**: Integration guide (moved from notebooks/)
- **`INDEX.md`**: Index documentation (moved from notebooks/)
- **`QUICK_REFERENCE.md`**: Quick reference (moved from notebooks/)
- **`README_GEE_WORKFLOW.md`**: GEE workflow documentation (moved from notebooks/)
- **`SETUP_COMPLETE.md`**: Setup documentation (moved from notebooks/)

#### `test/` - Test Files
- **`test_notebook_integration.py`**: Comprehensive test suite for all components
- **`run_tests.sh`**: Test runner script for Docker environment

#### `notebooks/archieve/` - Archived Files
- **`02_gee_calculations.py`**: Python version of main notebook
- **`03_arcgis_integration.py`**: Unused ArcGIS integration
- **`add_to_mapstore.py`**: Old MapStore integration approach
- **`example_api_usage.py`**: Example API usage
- **`test_gee_integration.py`**: Old test file
- **`01_dynamic_baseline.ipynb`**: Not used in main workflow
- **`mapstore_config_updater.py`**: Replaced by wmts_config_updater.py

## Workflow Integration

### From `02_gee_calculations.ipynb`

The notebook follows this workflow:

1. **GEE Analysis** (Steps 1-5):
   - Initialize GEE with service account
   - Define AOI (Area of Interest)
   - Create Sentinel-2 composite using `gee_lib`
   - Generate analysis products (True Color, False Color, NDVI, EVI, NDWI)
   - Create GEE Map IDs for tile serving

2. **Integration** (Step 8 - Ultra-Simple):
   ```python
   from gee_integration import process_gee_to_mapstore
   result = process_gee_to_mapstore(simple_map_layers, "My GEE Analysis")
   ```

3. **Catalog Management** (Steps 11-12):
   ```python
   from gee_catalog_updater import update_mapstore_catalog, GEECatalogUpdater
   catalog_result = update_mapstore_catalog(...)
   ```

4. **WMTS Configuration** (Steps 13-14):
   ```python
   from wmts_config_updater import update_mapstore_wmts_config, get_current_wmts_status
   wmts_success = update_mapstore_wmts_config(...)
   ```

### Docker Environment
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

## Key Files Used

### **Core Integration Files**

#### `notebooks/gee_integration.py`
- **Purpose**: Main integration library for GEE-to-MapStore workflow
- **Key Function**: `process_gee_to_mapstore(map_layers, project_name, aoi_info, fastapi_url)`
- **Usage**: Called from Step 8 in notebook
- **Features**:
  - Registers layers with FastAPI
  - Updates MapStore WMTS configuration
  - Handles dynamic service naming
  - Manages old service cleanup

#### `notebooks/wmts_config_updater.py`
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

#### `notebooks/gee_catalog_updater.py`
- **Purpose**: Catalog service management
- **Key Functions**:
  - `update_mapstore_catalog()` - Updates catalog services
  - `GEECatalogUpdater` - Catalog management class
- **Usage**: Called from Steps 11-12 in notebook
- **Features**:
  - CSW service management
  - Layer discovery
  - Catalog metadata

### **Main Workflow Notebook**

#### `notebooks/archieve/02_gee_calculations.ipynb`
- **Purpose**: Complete GEE analysis workflow
- **Steps**:
  1. Initialize GEE
  2. Define AOI
  3. Create Sentinel-2 composite
  4. Generate analysis products
  5. Create GEE Map IDs
  6. Visualize results
  8. Ultra-simple integration
  11-12. Catalog management
  13-14. WMTS configuration
- **Output**: Complete GEE-to-MapStore integration

## Testing

### **Test Suite Created**
- Tests module imports
- Tests GEE initialization
- Tests GEE library access
- Tests FastAPI connectivity
- Tests integration library
- Tests WMTS configuration updater
- Tests catalog updater
- Tests MapStore config access
- Tests complete workflow simulation

### **To Run Tests**
```bash
# From within Docker container
docker exec -it gis_jupyter_dev bash
cd /usr/src/app/jupyter/test
./run_tests.sh
```

## Documentation

### **`docs/README.md`**
- Complete service documentation
- API reference
- Configuration guide
- Usage examples
- Troubleshooting guide

### **`docs/NOTEBOOK_WORKFLOW.md`**
- Detailed step-by-step workflow documentation
- Code examples from actual notebook
- What happens internally
- Output and results
- Benefits

## Benefits of This Organization

### ✅ Clear Structure
- Core files easily identifiable
- Workflow files organized logically
- Archived files preserved but not cluttering
- Documentation comprehensive and accessible

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
- Essential files in logical locations
- Documentation for deployment
- Test suite for validation
- Clean, organized structure

## Maintenance

### **Adding New Notebooks**
- **Core functionality**: Add to `notebooks/` directory
- **Archived notebooks**: Move to `notebooks/archieve/`
- **Tests**: Add to `test/` directory
- **Documentation**: Add to `docs/` directory

### **Removing Files**
- **Never delete**: Core files in `notebooks/`
- **Archive instead**: Move obsolete files to `notebooks/archieve/`
- **Clean up**: Remove files from `archieve/` after confirming they're not needed

### **Updating Documentation**
- **API changes**: Update `docs/README.md`
- **Workflow changes**: Update `docs/NOTEBOOK_WORKFLOW.md`
- **New features**: Add to appropriate documentation file

## Next Steps

1. **Use the organized structure** for development
2. **Run tests** to validate everything works
3. **Update documentation** as you add features
4. **Archive obsolete files** as they become unused
5. **Keep core files** in `notebooks/` for easy access

The organization is complete and follows the actual workflow from your notebook! 🎉
