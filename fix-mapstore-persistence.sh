#!/bin/bash

# Fix MapStore Persistent Storage Issue
# This script handles the Docker volume mount issue where existing files in containers
# take precedence over mounted files

echo "🔧 Fixing MapStore persistent storage issue..."

# Check if MapStore container is running
if ! docker ps | grep -q gis_mapstore_dev; then
    echo "❌ MapStore container is not running. Starting it first..."
    docker-compose -f docker-compose.dev.yml up -d mapstore
    sleep 30
fi

# Ensure our configuration files exist
echo "📋 Ensuring configuration files exist..."
mkdir -p ./mapstore/config

if [ ! -f "./mapstore/config/localConfig.json" ]; then
    echo "  Creating localConfig.json..."
    cp ./mapstore/localConfig.json ./mapstore/config/localConfig.json 2>/dev/null || {
        echo "  Creating default localConfig.json..."
        cat > ./mapstore/config/localConfig.json << 'EOF'
{
  "map": {
    "center": {
      "x": 106.8,
      "y": -6.25,
      "crs": "EPSG:4326"
    },
    "zoom": 10,
    "maxZoom": 20,
    "minZoom": 1,
    "layers": [
      {
        "type": "osm",
        "title": "OpenStreetMap",
        "name": "osm",
        "visibility": true
      }
    ]
  },
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
  },
  "catalogServices": {
    "services": [
      {
        "type": "wms",
        "title": "GeoServer - Demo Workspace (Auth Required)",
        "url": "http://admin:admin@localhost:8080/geoserver/demo_workspace/wms",
        "format": "image/png",
        "version": "1.3.0",
        "authRequired": true,
        "authType": "basic"
      },
      {
        "type": "wms",
        "title": "GeoServer - Public Layers",
        "url": "http://localhost:8080/geoserver/gis_carbon/wms",
        "format": "image/png",
        "version": "1.3.0",
        "authRequired": false
      },
      {
        "type": "tile",
        "title": "GEE Analysis Layers",
        "description": "Google Earth Engine analysis layers from FastAPI service",
        "url": "http://localhost:8001/tiles/gee/{layer_name}/{z}/{x}/{y}",
        "format": "image/png",
        "transparent": true,
        "tileSize": 256,
        "authRequired": false
      }
    ]
  },
  "authentication": {
    "provider": "jwt",
    "loginUrl": "http://localhost:8000/api/auth/unified-login/",
    "logoutUrl": "http://localhost:8000/api/auth/unified-logout/",
    "userUrl": "http://localhost:8000/api/auth/unified-user/",
    "tokenKey": "unified_token",
    "userKey": "user",
    "rolesKey": "roles",
    "loginForm": {
      "enabled": true,
      "title": "GIS Carbon AI - Unified SSO",
      "subtitle": "Access your geospatial data and analysis tools"
    }
  },
  "security": {
    "roles": [
      "ROLE_ANONYMOUS",
      "ROLE_AUTHENTICATED",
      "ADMIN",
      "ANALYST",
      "VIEWER"
    ]
  }
}
EOF
    }
fi

# Copy configuration files directly into the container
echo "📁 Copying configuration files into MapStore container..."
docker cp ./mapstore/config/localConfig.json gis_mapstore_dev:/usr/local/tomcat/webapps/mapstore/configs/localConfig.json

# Copy other config files if they exist
if [ -f "./mapstore/config/gee-integration-config.json" ]; then
    docker cp ./mapstore/config/gee-integration-config.json gis_mapstore_dev:/usr/local/tomcat/webapps/mapstore/configs/gee-integration-config.json
fi

if [ -f "./mapstore/config/geoserver-integration-config.json" ]; then
    docker cp ./mapstore/config/geoserver-integration-config.json gis_mapstore_dev:/usr/local/tomcat/webapps/mapstore/configs/geoserver-integration-config.json
fi

# Verify the files were copied correctly
echo "🔍 Verifying configuration files..."
GEE_LAYERS_COUNT=$(docker exec gis_mapstore_dev grep -c "sentinel_analysis_" /usr/local/tomcat/webapps/mapstore/configs/localConfig.json 2>/dev/null || echo "0")

if [ "$GEE_LAYERS_COUNT" -gt 0 ]; then
    echo "  ✅ GEE layers found in MapStore config: $GEE_LAYERS_COUNT"
else
    echo "  ⚠️  No GEE layers found in MapStore config"
fi

# Restart MapStore to load the new configuration
echo "🔄 Restarting MapStore to load new configuration..."
docker-compose -f docker-compose.dev.yml restart mapstore

# Wait for MapStore to start
echo "⏳ Waiting for MapStore to start..."
sleep 30

# Test if MapStore is accessible
echo "🧪 Testing MapStore accessibility..."
if curl -s -o /dev/null -w "%{http_code}" http://localhost:8082/mapstore | grep -q "302\|200"; then
    echo "  ✅ MapStore is accessible"
else
    echo "  ❌ MapStore is not accessible"
    echo "  💡 Wait a bit longer and try: http://localhost:8082/mapstore"
fi

echo ""
echo "✅ MapStore persistent storage fix complete!"
echo ""
echo "📋 What was done:"
echo "  - Configuration files copied directly into MapStore container"
echo "  - MapStore restarted to load new configuration"
echo "  - GEE layers should now be available in MapStore Catalog"
echo ""
echo "🌐 Next steps:"
echo "  1. Open MapStore: http://localhost:8082/mapstore"
echo "  2. Click the Catalog button (📁) in the toolbar"
echo "  3. Look for 'GEE Analysis Layers' service"
echo "  4. Add layers to your map"
echo ""
echo "⚠️  Note: This fix needs to be run after each 'docker-compose up -d' or container restart"
echo "   To automate this, add this script to your startup workflow"
