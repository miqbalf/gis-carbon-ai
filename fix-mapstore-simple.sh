#!/bin/bash

# Simple MapStore Fix - Use Official Image with Proper Configuration
# This script reverts to the official MapStore image and fixes configuration

echo "🔧 Simple MapStore Fix - Using Official Image..."

# 1. Stop current MapStore
echo "📋 Stopping current MapStore..."
docker-compose -f docker-compose.dev.yml stop mapstore

# 2. Revert to original docker-compose
echo "📋 Reverting to original docker-compose..."
if [ -f docker-compose.dev.yml.backup ]; then
    cp docker-compose.dev.yml.backup docker-compose.dev.yml
    echo "  ✅ Restored original docker-compose"
else
    echo "  ⚠️  No backup found, will use current docker-compose"
fi

# 3. Update docker-compose to use official MapStore image
echo "📋 Updating docker-compose to use official MapStore image..."
sed -i.bak 's|image: gis-carbon-ai-mapstore-custom:latest|image: geosolutionsit/mapstore2:v2025.01.02-stable|g' docker-compose.dev.yml
sed -i.bak 's|build:|# build:|g' docker-compose.dev.yml
sed -i.bak 's|context: ./mapstore|# context: ./mapstore|g' docker-compose.dev.yml
sed -i.bak 's|dockerfile: Dockerfile|# dockerfile: Dockerfile|g' docker-compose.dev.yml

# 4. Start MapStore with official image
echo "🚀 Starting MapStore with official image..."
docker-compose -f docker-compose.dev.yml up -d mapstore

# 5. Wait for MapStore to start
echo "⏳ Waiting for MapStore to start..."
sleep 60

# 6. Create proper configuration
echo "📋 Creating proper configuration..."
docker exec gis_mapstore_dev mkdir -p /usr/local/tomcat/webapps/mapstore/configs
docker exec gis_mapstore_dev mkdir -p /usr/local/tomcat/webapps/mapstore/extensions

# Create a simple, working configuration
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

# Create extensions.json
docker exec gis_mapstore_dev sh -c 'echo "[]" > /usr/local/tomcat/webapps/mapstore/extensions/extensions.json'

# 7. Restart MapStore to apply configuration
echo "🔄 Restarting MapStore to apply configuration..."
docker-compose -f docker-compose.dev.yml restart mapstore

# 8. Wait for restart
echo "⏳ Waiting for MapStore to restart..."
sleep 60

# 9. Test MapStore
echo "🧪 Testing MapStore..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8082/mapstore)
if [ "$HTTP_CODE" = "302" ] || [ "$HTTP_CODE" = "200" ]; then
    echo "  ✅ MapStore is accessible (HTTP $HTTP_CODE)"
else
    echo "  ❌ MapStore is not accessible (HTTP $HTTP_CODE)"
    echo "  📋 Checking logs..."
    docker logs gis_mapstore_dev --tail 10
    exit 1
fi

# 10. Test configuration
echo "🧪 Testing configuration..."
if curl -s http://localhost:8082/mapstore/configs/localConfig.json | grep -q "plugins"; then
    echo "  ✅ Configuration includes plugins section"
else
    echo "  ❌ Configuration missing plugins section"
    exit 1
fi

# 11. Test extensions
echo "🧪 Testing extensions..."
if curl -s http://localhost:8082/mapstore/extensions/extensions.json | grep -q "\[\]"; then
    echo "  ✅ Extensions working"
else
    echo "  ❌ Extensions not working"
    exit 1
fi

echo ""
echo "✅ Simple MapStore fix complete!"
echo ""
echo "📋 What was done:"
echo "  - Reverted to official MapStore image (geosolutionsit/mapstore2:v2025.01.02-stable)"
echo "  - Created proper configuration with all required sections"
echo "  - Created extensions directory and file"
echo "  - Restarted MapStore with new configuration"
echo ""
echo "🌐 Next steps:"
echo "  1. Open MapStore: http://localhost:8082/mapstore"
echo "  2. MapStore should now load completely"
echo "  3. All plugins and features should be available"
echo ""
echo "💡 Benefits of using official image:"
echo "  - Tested and stable"
echo "  - No custom build issues"
echo "  - Proper dependencies"
echo "  - Official support"
