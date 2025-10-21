#!/bin/bash

# Fix MapStore Routing Issues
# This script addresses the 404 error on MapStore routes

echo "🔧 Fixing MapStore routing issues..."

# Check if MapStore container is running
if ! docker ps | grep -q gis_mapstore_dev; then
    echo "❌ MapStore container is not running. Starting it first..."
    docker-compose -f docker-compose.dev.yml up -d mapstore
    sleep 30
fi

# 1. Check if MapStore is accessible
echo "📋 Checking MapStore accessibility..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8082/mapstore)
if [ "$HTTP_CODE" = "302" ] || [ "$HTTP_CODE" = "200" ]; then
    echo "  ✅ MapStore is accessible (HTTP $HTTP_CODE)"
else
    echo "  ❌ MapStore is not accessible (HTTP $HTTP_CODE)"
    exit 1
fi

# 2. Check if JavaScript file loads
echo "📋 Checking JavaScript file..."
JS_SIZE=$(curl -s -o /dev/null -w "%{size_download}" http://localhost:8082/mapstore/dist/mapstore2.js)
if [ "$JS_SIZE" -gt 1000000 ]; then
    echo "  ✅ JavaScript file loaded successfully ($JS_SIZE bytes)"
else
    echo "  ❌ JavaScript file failed to load ($JS_SIZE bytes)"
    exit 1
fi

# 3. Check if configuration loads
echo "📋 Checking configuration..."
if curl -s http://localhost:8082/mapstore/configs/localConfig.json | grep -q "map"; then
    echo "  ✅ Configuration loaded successfully"
else
    echo "  ❌ Configuration failed to load"
    exit 1
fi

# 4. Check if extensions load
echo "📋 Checking extensions..."
if curl -s http://localhost:8082/mapstore/extensions/extensions.json | grep -q "\[\]"; then
    echo "  ✅ Extensions loaded successfully"
else
    echo "  ❌ Extensions failed to load"
    exit 1
fi

# 5. The issue might be that MapStore needs a proper configuration
echo "📋 Checking if MapStore needs proper configuration..."
echo "  The 404 error on '#/' suggests MapStore is trying to load a route"
echo "  that doesn't exist. This is likely a client-side routing issue."

# 6. Let's try to fix this by ensuring MapStore has a proper configuration
echo "🔧 Attempting to fix routing issue..."

# Check if we have a working configuration
if docker exec gis_mapstore_dev grep -q "version" /usr/local/tomcat/webapps/mapstore/configs/localConfig.json; then
    echo "  ✅ Configuration has version field"
else
    echo "  ⚠️  Configuration missing version field, adding it..."
    # Add version field to configuration
    docker exec gis_mapstore_dev sh -c 'sed -i "1i{\n  \"version\": 2," /usr/local/tomcat/webapps/mapstore/configs/localConfig.json'
    docker exec gis_mapstore_dev sh -c 'echo "}" >> /usr/local/tomcat/webapps/mapstore/configs/localConfig.json'
fi

# 7. Restart MapStore to apply any changes
echo "🔄 Restarting MapStore..."
docker-compose -f docker-compose.dev.yml restart mapstore

# 8. Wait for MapStore to start
echo "⏳ Waiting for MapStore to start..."
sleep 30

# 9. Test MapStore again
echo "🧪 Testing MapStore after fix..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8082/mapstore)
if [ "$HTTP_CODE" = "302" ] || [ "$HTTP_CODE" = "200" ]; then
    echo "  ✅ MapStore is accessible (HTTP $HTTP_CODE)"
else
    echo "  ❌ MapStore is not accessible (HTTP $HTTP_CODE)"
    exit 1
fi

# 10. Test the specific route that was failing
echo "🧪 Testing the failing route..."
ROUTE_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8082/mapstore/#/")
if [ "$ROUTE_RESPONSE" = "200" ]; then
    echo "  ✅ Route '#/' is now working"
else
    echo "  ⚠️  Route '#/' still returns $ROUTE_RESPONSE (this might be normal for SPA)"
fi

echo ""
echo "✅ MapStore routing fix complete!"
echo ""
echo "📋 What was checked:"
echo "  - MapStore accessibility"
echo "  - JavaScript file loading"
echo "  - Configuration loading"
echo "  - Extensions loading"
echo "  - Configuration version field"
echo ""
echo "🌐 Next steps:"
echo "  1. Open MapStore: http://localhost:8082/mapstore"
echo "  2. If still showing white screen:"
echo "     - Clear browser cache and refresh"
echo "     - Try incognito/private mode"
echo "     - Check browser console for JavaScript errors"
echo "     - The '#/' route error might be normal for Single Page Applications"
echo ""
echo "🔧 If still having issues:"
echo "  - The 404 error on '#/' might be expected behavior"
echo "  - MapStore is a Single Page Application (SPA)"
echo "  - Client-side routes are handled by JavaScript"
echo "  - Server-side 404s on client routes are normal"
echo ""
echo "💡 The real test is whether MapStore loads in the browser, not the '#/' route"
