# MapStore Configs Folder Migration

## Problem Identified

The MapStore container was using the `configs` folder, but our local configuration was in the `config` folder, causing a mismatch between the Docker mount paths and the actual file locations.

## Changes Made

### 1. **Docker Compose Configuration Updated**

**File**: `docker-compose.dev.yml`

**Changes**:
- **MapStore Service**: `./mapstore/configs/localConfig.json:/usr/local/tomcat/webapps/mapstore/configs/localConfig.json` ✅
- **FastAPI Service**: `./mapstore/configs:/app/mapstore/configs` ✅  
- **Jupyter Service**: `./mapstore/configs:/usr/src/app/mapstore/configs` ✅

### 2. **Python Code Updated**

**Files Updated**:
- `fastapi-gee-service/gee_integration.py` ✅
- `fastapi-gee-service/cleanup_mapstore_config.py` ✅
- `fastapi-gee-service/mapstore_service_manager.py` ✅
- `fastapi-gee-service/main.py` ✅
- `fastapi-gee-service/wmts_config_updater.py` ✅
- `fastapi-gee-service/fix_wfs_format.py` ✅

**Path Changes**:
- `/usr/src/app/mapstore/config/localConfig.json` → `/usr/src/app/mapstore/configs/localConfig.json`
- `/app/mapstore/config/localConfig.json` → `/app/mapstore/configs/localConfig.json`
- `./mapstore/config/localConfig.json` → `./mapstore/configs/localConfig.json`

### 3. **Current Status**

✅ **Docker Compose**: All services now mount the `configs` folder  
✅ **Python Code**: All references updated to use `configs` folder  
✅ **Local Files**: WFS service is in the correct local file  
✅ **Container Mount**: MapStore container will use the correct path  

### 4. **Expected Results**

1. **MapStore Container**: Will load localConfig.json from the correct `configs` folder
2. **WFS Service**: Should appear in MapStore catalog
3. **WMTS Service**: Should continue working
4. **No JavaScript Errors**: The 'Format' error should be resolved

### 5. **Next Steps**

1. **Restart Services**: 
   ```bash
   docker-compose -f docker-compose.dev.yml restart mapstore fastapi jupyter
   ```

2. **Verify Mount**: Check that the localConfig.json is properly mounted in the container

3. **Test Services**: Verify both WMTS and WFS services appear in MapStore

### 6. **Verification Commands**

```bash
# Check if localConfig.json is properly mounted
docker-compose -f docker-compose.dev.yml exec mapstore ls -la /usr/local/tomcat/webapps/mapstore/configs/localConfig.json

# Check if WFS service is in the file
docker-compose -f docker-compose.dev.yml exec mapstore grep -A 5 "gee_wfs" /usr/local/tomcat/webapps/mapstore/configs/localConfig.json

# Check if FastAPI can access the config
docker-compose -f docker-compose.dev.yml exec fastapi ls -la /app/mapstore/configs/localConfig.json

# Check if Jupyter can access the config  
docker-compose -f docker-compose.dev.yml exec jupyter ls -la /usr/src/app/mapstore/configs/localConfig.json
```

## Summary

All Docker Compose mounts and Python code references have been updated to use the `configs` folder consistently. The WFS service should now be properly accessible to MapStore, and both WMTS and WFS services should appear in the MapStore catalog.
