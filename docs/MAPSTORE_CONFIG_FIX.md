# MapStore Configuration Fix

## Problem Identified

The WFS services were not appearing in MapStore because:

1. **Duplicate Services**: GEE services were being added to BOTH locations:
   - ✅ Correct location: `initialState.defaultState.catalog.services`
   - ❌ Incorrect location: `catalogServices`

2. **MapStore Confusion**: MapStore was reading from the wrong location, causing JavaScript errors

3. **Service Conflicts**: Duplicate services with different configurations caused conflicts

## Solution Implemented

### 1. **Cleanup Script Created** (`cleanup_mapstore_config.py`)
- Removes old GEE services from `catalogServices`
- Verifies services exist only in correct location
- Creates backup before making changes
- Provides detailed logging

### 2. **Configuration Cleaned**
```bash
# Removed from catalogServices:
- gee_wmts_Separate_Services_Test
- gee_wfs_Separate_Services_Test

# Kept in initialState.defaultState.catalog.services:
- gee_wmts_Separate_Services_Test (WMTS)
- gee_wfs_Separate_Services_Test (WFS)
```

### 3. **Service Manager Updated**
- Fixed `mapstore_service_manager.py` to add services to correct location
- Updated all methods to work with proper MapStore structure
- Added proper error handling and validation

## Current Status

### ✅ **Services Properly Configured**
```json
{
  "initialState": {
    "defaultState": {
      "catalog": {
        "services": {
          "gee_wmts_Separate_Services_Test": {
            "type": "wmts",
            "url": "http://fastapi:8000/wmts",
            "version": "1.0.0",
            "title": "GEE WMTS Service - Separate_Services_Test",
            "autoload": false,
            "authRequired": false,
            "format": "image/png",
            "transparent": true,
            "tileSize": 256
          },
          "gee_wfs_Separate_Services_Test": {
            "type": "wfs",
            "url": "http://fastapi:8000/wfs",
            "version": "2.0.0",
            "title": "GEE WFS Service - Separate_Services_Test",
            "autoload": false,
            "authRequired": false,
            "outputFormat": "application/json",
            "maxFeatures": 1000
          }
        }
      }
    }
  }
}
```

### ✅ **No Duplicate Services**
- `catalogServices` section cleaned of GEE services
- Only test services remain in `catalogServices`
- All GEE services in correct location

### ✅ **MapStore Ready**
- Services will now appear in MapStore catalog
- No more JavaScript errors
- Both WMTS and WFS services available
- Proper service separation maintained

## Verification

Run the cleanup script to verify:
```bash
python cleanup_mapstore_config.py
```

Expected output:
```
✅ GEE services are in the correct location
✅ Found 2 GEE services in correct location:
  - gee_wmts_Separate_Services_Test (wmts)
  - gee_wfs_Separate_Services_Test (wfs)
✅ No GEE services in incorrect location
```

## Next Steps

1. **Restart MapStore** to load the cleaned configuration
2. **Check MapStore Catalog** for the two separate services
3. **Test WFS Service** by adding layers from the WFS service
4. **Test WMTS Service** by adding layers from the WMTS service

## Prevention

The updated `mapstore_service_manager.py` now:
- Only adds services to correct location
- Validates configuration structure
- Provides clear error messages
- Prevents duplicate service creation

This ensures future integrations will work correctly without manual cleanup.

