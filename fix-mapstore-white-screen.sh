#!/bin/bash

# Fix MapStore White Blank Screen Issue
# This script addresses common causes of white blank screens in MapStore

echo "🔧 Fixing MapStore white blank screen issue..."

# Check if MapStore container is running
if ! docker ps | grep -q gis_mapstore_dev; then
    echo "❌ MapStore container is not running. Starting it first..."
    docker-compose -f docker-compose.dev.yml up -d mapstore
    sleep 30
fi

# 1. Check for JSON syntax errors in configuration
echo "📋 Checking configuration file syntax..."
if python3 -m json.tool ./mapstore/config/localConfig.json > /dev/null 2>&1; then
    echo "  ✅ Local configuration JSON is valid"
else
    echo "  ❌ Local configuration JSON has syntax errors"
    echo "  🔧 Creating a clean configuration..."
    
    # Create a clean, minimal configuration
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
      "Share"
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
  }
}
EOF
    echo "  ✅ Clean configuration created"
fi

# 2. Create missing extensions directory and file
echo "📁 Creating missing extensions directory and file..."
docker exec gis_mapstore_dev mkdir -p /usr/local/tomcat/webapps/mapstore/extensions
docker exec gis_mapstore_dev sh -c 'echo "[]" > /usr/local/tomcat/webapps/mapstore/extensions/extensions.json'

# 3. Copy configuration to container
echo "📁 Copying configuration to MapStore container..."
docker cp ./mapstore/config/localConfig.json gis_mapstore_dev:/usr/local/tomcat/webapps/mapstore/configs/localConfig.json

# 4. Check if the file was copied correctly
echo "🔍 Verifying configuration in container..."
if docker exec gis_mapstore_dev cat /usr/local/tomcat/webapps/mapstore/configs/localConfig.json | grep -q "catalogServices"; then
    echo "  ✅ Configuration copied successfully"
else
    echo "  ❌ Configuration copy failed"
    exit 1
fi

# 5. Restart MapStore to load the configuration
echo "🔄 Restarting MapStore..."
docker-compose -f docker-compose.dev.yml restart mapstore

# 6. Wait for MapStore to start
echo "⏳ Waiting for MapStore to start..."
sleep 30

# 7. Test MapStore accessibility
echo "🧪 Testing MapStore accessibility..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8082/mapstore)
if [ "$HTTP_CODE" = "302" ] || [ "$HTTP_CODE" = "200" ]; then
    echo "  ✅ MapStore is accessible (HTTP $HTTP_CODE)"
else
    echo "  ❌ MapStore is not accessible (HTTP $HTTP_CODE)"
    echo "  💡 Check MapStore logs: docker logs gis_mapstore_dev"
    exit 1
fi

# 8. Test configuration endpoint
echo "🔍 Testing configuration endpoint..."
if curl -s http://localhost:8082/mapstore/configs/localConfig.json | grep -q "catalogServices"; then
    echo "  ✅ Configuration endpoint is working"
else
    echo "  ❌ Configuration endpoint is not working"
    exit 1
fi

# 9. Test extensions endpoint
echo "🔍 Testing extensions endpoint..."
if curl -s http://localhost:8082/mapstore/extensions/extensions.json | grep -q "\[\]"; then
    echo "  ✅ Extensions endpoint is working"
else
    echo "  ❌ Extensions endpoint is not working"
    exit 1
fi

# 10. Add GEE layers if they're not present
echo "🔍 Checking for GEE layers..."
GEE_LAYERS_COUNT=$(docker exec gis_mapstore_dev grep -c "sentinel_analysis_" /usr/local/tomcat/webapps/mapstore/configs/localConfig.json 2>/dev/null || echo "0")

if [ "$GEE_LAYERS_COUNT" -eq 0 ]; then
    echo "  ⚠️  No GEE layers found. Adding them..."
    cd ./mapstore && python add-gee-layers-manual.py
    cd ..
    docker cp ./mapstore/config/localConfig.json gis_mapstore_dev:/usr/local/tomcat/webapps/mapstore/configs/localConfig.json
    docker-compose -f docker-compose.dev.yml restart mapstore
    sleep 30
    echo "  ✅ GEE layers added"
else
    echo "  ✅ GEE layers found: $GEE_LAYERS_COUNT"
fi

echo ""
echo "✅ MapStore white blank screen fix complete!"
echo ""
echo "📋 What was fixed:"
echo "  - Configuration JSON syntax validated"
echo "  - Configuration copied to container"
echo "  - MapStore restarted with clean configuration"
echo "  - GEE layers added if missing"
echo ""
echo "🌐 Next steps:"
echo "  1. Open MapStore: http://localhost:8082/mapstore"
echo "  2. If still white, clear browser cache and refresh"
echo "  3. Check browser console for JavaScript errors"
echo "  4. Try incognito/private browsing mode"
echo ""
echo "🔧 If still having issues:"
echo "  - Check browser console: F12 → Console tab"
echo "  - Check MapStore logs: docker logs gis_mapstore_dev"
echo "  - Try different browser or incognito mode"
