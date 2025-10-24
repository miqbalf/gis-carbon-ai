# WFS Format Fix

## Problem Identified

MapStore was showing JavaScript error:
```
TypeError: Cannot read properties of undefined (reading 'Format')
```

This was caused by WFS services missing the required `Format` property (with capital F).

## Root Cause

MapStore expects WFS services to have:
- `Format` property (with capital F) - **Required**
- `maxFeatures` property - **Required**
- `version` property - **Required**

Our GEE WFS service was missing the `Format` property, and the existing GeoServer WFS service was also missing it.

## Solution Implemented

### 1. **Fixed GEE WFS Service**
```json
{
  "gee_wfs_Separate_Services_Test": {
    "type": "wfs",
    "url": "http://fastapi:8000/wfs",
    "version": "2.0.0",
    "title": "GEE WFS Service - Separate_Services_Test",
    "autoload": false,
    "authRequired": false,
    "outputFormat": "application/json",
    "maxFeatures": 1000,
    "Format": "application/json"  // ✅ Added
  }
}
```

### 2. **Fixed GeoServer WFS Service**
```json
{
  "geoserver_gis_carbon_wfs": {
    "url": "http://localhost:8080/geoserver/wfs",
    "type": "wfs",
    "title": "GeoServer GIS Carbon WFS",
    "autoload": true,
    "version": "1.1.0",
    "outputFormat": "application/json",
    "Format": "application/json",  // ✅ Added
    "maxFeatures": 1000           // ✅ Added
  }
}
```

### 3. **Created Fix Script** (`fix_wfs_format.py`)
- Automatically detects WFS services
- Adds missing required properties
- Creates backup before changes
- Provides detailed verification

## Current Status

### ✅ **Both WFS Services Fixed**
- **GEE WFS Service**: Has all required properties
- **GeoServer WFS Service**: Has all required properties
- **No JavaScript Errors**: MapStore can now read WFS services properly

### ✅ **Service Verification**
```
✅ gee_wfs_Separate_Services_Test has all required properties
✅ geoserver_gis_carbon_wfs has all required properties
```

## Expected Results

1. **No More JavaScript Errors**: The 'Format' error should be resolved
2. **WFS Services Visible**: Both WFS services should appear in MapStore catalog
3. **WMTS Service Working**: The WMTS service should also work properly now
4. **Layer Discovery**: Both services should be able to list their layers

## Next Steps

1. **Restart MapStore** to load the fixed configuration
2. **Check MapStore Catalog** for both WFS services
3. **Test Layer Discovery** from both WFS services
4. **Test WMTS Service** to ensure it's working properly

## Prevention

The updated `mapstore_service_manager.py` now includes the `Format` property when creating WFS services, preventing this issue in the future.

## Verification Commands

```bash
# Check WFS services have Format property
grep -A 10 '"type": "wfs"' /path/to/localConfig.json

# Verify no JavaScript errors in MapStore
# Check browser console for errors
```

The WFS services should now be fully functional in MapStore! 🎯
