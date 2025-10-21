#!/bin/bash

# Fix MapStore Complete Configuration
# This script creates a complete MapStore configuration with both map and plugins

echo "🔧 Fixing MapStore complete configuration..."

# Check if MapStore container is running
if ! docker ps | grep -q gis_mapstore_dev; then
    echo "❌ MapStore container is not running. Starting it first..."
    docker-compose -f docker-compose.dev.yml up -d mapstore
    sleep 30
fi

# 1. Create a complete configuration that includes both map and plugins
echo "📋 Creating complete MapStore configuration..."

# Create the complete configuration by merging map config and plugins config
docker exec gis_mapstore_dev sh -c 'cat > /usr/local/tomcat/webapps/mapstore/configs/localConfig.json << "EOF"
{
  "version": 2,
  "map": {
    "projection": "EPSG:900913",
    "units": "m",
    "center": {
      "x": 1250000.0,
      "y": 5370000.0,
      "crs": "EPSG:900913"
    },
    "zoom": 5,
    "maxExtent": [-20037508.34, -20037508.34, 20037508.34, 20037508.34],
    "layers": [
      {
        "format": "image/jpeg",
        "group": "background",
        "name": "osm:osm",
        "opacity": 1,
        "title": "OSM Bright",
        "thumbURL": "product/assets/img/osm-bright.jpg",
        "type": "osm",
        "url": "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
        "visibility": true
      }
    ]
  },
  "plugins": {
    "desktop": [
      "Map",
      "Toolbar",
      "DrawerMenu",
      "TOC",
      "BackgroundSelector",
      "Search",
      "Measure",
      "Identify",
      "Locate",
      "Home",
      "ZoomIn",
      "ZoomOut",
      "ZoomAll",
      "FullScreen",
      "MousePosition",
      "ScaleBox",
      "CRSSelector",
      "GlobeViewSwitcher",
      "BurgerMenu",
      "Expander",
      "Undo",
      "Redo",
      "MapFooter",
      "Notifications",
      "FeedbackMask",
      "Cookie"
    ],
    "mobile": [
      "Map",
      "Toolbar",
      "DrawerMenu",
      "TOC",
      "BackgroundSelector",
      "Search",
      "Measure",
      "Identify",
      "Locate",
      "Home",
      "ZoomIn",
      "ZoomOut",
      "ZoomAll",
      "FullScreen",
      "MousePosition",
      "ScaleBox",
      "CRSSelector",
      "GlobeViewSwitcher",
      "BurgerMenu",
      "Expander",
      "Undo",
      "Redo",
      "MapFooter",
      "Notifications",
      "FeedbackMask",
      "Cookie"
    ]
  },
  "catalogServices": {
    "services": {
      "demo_workspace": {
        "title": "Demo Workspace",
        "authenticationMethod": "No Auth",
        "type": "csw",
        "url": "http://localhost:8080/geoserver/demo_workspace/ows?service=CSW&version=2.0.2&request=GetCapabilities"
      }
    }
  },
  "proxyUrl": "/mapstore/proxy/?url=",
  "geoStoreUrl": "/mapstore/rest/geostore/",
  "printUrl": "https://demo.geo-solutions.it/geoserver/pdf/info.json",
  "initialMapFilter": "MS2"
}
EOF'

# 2. Verify the configuration was created correctly
echo "📋 Verifying configuration..."
if docker exec gis_mapstore_dev grep -q "plugins" /usr/local/tomcat/webapps/mapstore/configs/localConfig.json; then
    echo "  ✅ Configuration includes plugins section"
else
    echo "  ❌ Configuration missing plugins section"
    exit 1
fi

if docker exec gis_mapstore_dev grep -q "catalogServices" /usr/local/tomcat/webapps/mapstore/configs/localConfig.json; then
    echo "  ✅ Configuration includes catalogServices section"
else
    echo "  ❌ Configuration missing catalogServices section"
    exit 1
fi

# 3. Restart MapStore to apply the new configuration
echo "🔄 Restarting MapStore with complete configuration..."
docker-compose -f docker-compose.dev.yml restart mapstore

# 4. Wait for MapStore to start
echo "⏳ Waiting for MapStore to start..."
sleep 30

# 5. Test MapStore
echo "🧪 Testing MapStore with complete configuration..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8082/mapstore)
if [ "$HTTP_CODE" = "302" ] || [ "$HTTP_CODE" = "200" ]; then
    echo "  ✅ MapStore is accessible (HTTP $HTTP_CODE)"
else
    echo "  ❌ MapStore is not accessible (HTTP $HTTP_CODE)"
    exit 1
fi

# 6. Test configuration endpoint
echo "🧪 Testing configuration endpoint..."
if curl -s http://localhost:8082/mapstore/configs/localConfig.json | grep -q "plugins"; then
    echo "  ✅ Configuration endpoint returns plugins section"
else
    echo "  ❌ Configuration endpoint missing plugins section"
    exit 1
fi

# 7. Test plugins endpoint
echo "🧪 Testing plugins endpoint..."
if curl -s http://localhost:8082/mapstore/configs/pluginsConfig.json | grep -q "Map"; then
    echo "  ✅ Plugins endpoint working"
else
    echo "  ❌ Plugins endpoint not working"
    exit 1
fi

echo ""
echo "✅ MapStore complete configuration fix complete!"
echo ""
echo "📋 What was fixed:"
echo "  - Added plugins section to localConfig.json"
echo "  - Added catalogServices section to localConfig.json"
echo "  - Ensured both desktop and mobile plugin configurations"
echo "  - Maintained original map configuration"
echo ""
echo "🌐 Next steps:"
echo "  1. Open MapStore: http://localhost:8082/mapstore"
echo "  2. MapStore should now load completely (no more white screen)"
echo "  3. You should see the full MapStore interface with toolbar, layers, etc."
echo ""
echo "🔧 If still having issues:"
echo "  - Clear browser cache and refresh"
echo "  - Try incognito/private mode"
echo "  - Check browser console for any remaining errors"
echo ""
echo "💡 The complete configuration now includes:"
echo "  - Map configuration (projection, center, zoom, layers)"
echo "  - Plugins configuration (desktop and mobile)"
echo "  - Catalog services configuration"
echo "  - Proxy and GeoStore URLs"
