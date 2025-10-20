# 🗺️ GeoServer-MapStore Integration Guide

## Overview
This guide shows how to integrate your GeoServer data with MapStore and customize MapStore for your GIS Carbon AI project.

## 1. GeoServer Data Integration

### Current GeoServer Setup
- **URL**: `http://localhost:8080/geoserver`
- **Credentials**: `admin:admin`
- **Workspace**: `gis_carbon`
- **Data Store**: `gis_carbon_data`
- **Available Layer**: `sample_geometries`

### Adding GeoServer Layers to MapStore

#### Method 1: Through MapStore Web Interface
1. Open MapStore: `http://localhost:8082/mapstore`
2. Login with: `admin:admin`
3. Go to **Catalog** → **Add Service**
4. Add WMS Service:
   - **URL**: `http://localhost:8080/geoserver/gis_carbon/wms`
   - **Type**: WMS
   - **Version**: 1.3.0
5. Add WFS Service:
   - **URL**: `http://localhost:8080/geoserver/gis_carbon/wfs`
   - **Type**: WFS
   - **Version**: 1.1.0

#### Method 2: Direct Layer URLs
- **WMS Layer**: `http://localhost:8080/geoserver/gis_carbon/wms?service=WMS&version=1.3.0&request=GetMap&layers=gis_carbon:sample_geometries&styles=&format=image/png&transparent=true&width=256&height=256&crs=EPSG:4326&bbox=-180,-90,180,90`
- **WFS Layer**: `http://localhost:8080/geoserver/gis_carbon/wfs?service=WFS&version=1.1.0&request=GetFeature&typeName=gis_carbon:sample_geometries&outputFormat=application/json`

## 2. MapStore Customization Options

### A. Configuration Files (Customizable)
MapStore allows extensive customization through configuration files:

#### 1. `localConfig.json` - Main Configuration
```json
{
  "map": {
    "projection": "EPSG:4326",
    "center": [0, 0],
    "zoom": 2
  },
  "catalogServices": {
    "services": [
      {
        "type": "wms",
        "title": "GeoServer WMS",
        "url": "http://localhost:8080/geoserver/gis_carbon/wms",
        "format": "image/png",
        "version": "1.3.0"
      }
    ]
  }
}
```

#### 2. `plugins.json` - Plugin Configuration
```json
{
  "plugins": {
    "desktop": [
      "Map",
      "Toolbar",
      "DrawerMenu",
      "ZoomIn",
      "ZoomOut",
      "ZoomAll",
      "BackgroundSelector",
      "LayerTree",
      "TOC",
      "Search",
      "Catalog",
      "Measure",
      "Print",
      "Share",
      "Login"
    ]
  }
}
```

### B. Customizable Components

#### 1. **Themes & Styling**
- Custom CSS files
- Brand colors and logos
- UI layout modifications

#### 2. **Plugins & Extensions**
- Custom plugins for carbon analysis
- Integration with your Django/FastAPI services
- Custom tools and widgets

#### 3. **Data Sources**
- Multiple GeoServer instances
- External WMS/WFS services
- Custom data providers

#### 4. **User Interface**
- Custom toolbar buttons
- Modified menus
- Custom dialogs and forms

## 3. Integration with Your Carbon AI Services

### A. Django Integration
```javascript
// Custom plugin to connect with Django backend
const CarbonAnalysisPlugin = {
  name: 'CarbonAnalysis',
  component: CarbonAnalysisComponent,
  reducers: {
    carbonAnalysis: carbonAnalysisReducer
  }
};
```

### B. FastAPI Integration
```javascript
// Custom service for GEE tile integration
const GEETileService = {
  getTile: (x, y, z) => {
    return fetch(`http://localhost:8001/tiles/${z}/${x}/${y}`);
  }
};
```

## 4. Next Steps

1. **Test GeoServer Integration**: Add your layers to MapStore
2. **Customize UI**: Modify themes and add custom plugins
3. **Integrate Services**: Connect with Django/FastAPI backends
4. **Add Carbon Tools**: Create custom tools for carbon analysis

## 5. Useful URLs

- **MapStore**: `http://localhost:8082/mapstore`
- **GeoServer**: `http://localhost:8080/geoserver`
- **GeoServer Admin**: `http://localhost:8080/geoserver/web`
- **WMS Capabilities**: `http://localhost:8080/geoserver/gis_carbon/wms?service=WMS&version=1.3.0&request=GetCapabilities`
- **WFS Capabilities**: `http://localhost:8080/geoserver/gis_carbon/wfs?service=WFS&version=1.1.0&request=GetCapabilities`
