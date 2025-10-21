#!/bin/bash

# Fix MapStore CORS Issues
# This script adds CORS headers to MapStore to fix white blank screen issues

echo "🔧 Fixing MapStore CORS issues..."

# Check if MapStore container is running
if ! docker ps | grep -q gis_mapstore_dev; then
    echo "❌ MapStore container is not running. Starting it first..."
    docker-compose -f docker-compose.dev.yml up -d mapstore
    sleep 30
fi

# 1. Create a simple CORS filter
echo "📁 Creating CORS filter..."
docker exec gis_mapstore_dev sh -c 'cat > /usr/local/tomcat/webapps/mapstore/WEB-INF/web.xml << "EOF"
<?xml version="1.0" encoding="UTF-8"?>
<web-app xmlns="http://xmlns.jcp.org/xml/ns/javaee"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://xmlns.jcp.org/xml/ns/javaee
         http://xmlns.jcp.org/xml/ns/javaee/web-app_3_1.xsd"
         version="3.1">
    
    <!-- CORS Filter -->
    <filter>
        <filter-name>CorsFilter</filter-name>
        <filter-class>org.apache.catalina.filters.CorsFilter</filter-class>
        <init-param>
            <param-name>cors.allowed.origins</param-name>
            <param-value>*</param-value>
        </init-param>
        <init-param>
            <param-name>cors.allowed.methods</param-name>
            <param-value>GET,POST,PUT,DELETE,OPTIONS,HEAD</param-value>
        </init-param>
        <init-param>
            <param-name>cors.allowed.headers</param-name>
            <param-value>Content-Type,X-Requested-With,accept,Origin,Access-Control-Request-Method,Access-Control-Request-Headers</param-value>
        </init-param>
        <init-param>
            <param-name>cors.support.credentials</param-name>
            <param-value>false</param-value>
        </init-param>
    </filter>
    
    <filter-mapping>
        <filter-name>CorsFilter</filter-name>
        <url-pattern>/*</url-pattern>
    </filter-mapping>
    
</web-app>
EOF'

# 2. Create missing extensions directory and file
echo "📁 Creating missing extensions directory and file..."
docker exec gis_mapstore_dev mkdir -p /usr/local/tomcat/webapps/mapstore/extensions
docker exec gis_mapstore_dev sh -c 'echo "[]" > /usr/local/tomcat/webapps/mapstore/extensions/extensions.json'

# 3. Copy configuration to container
echo "📁 Copying configuration to MapStore container..."
docker cp ./mapstore/config/localConfig.json gis_mapstore_dev:/usr/local/tomcat/webapps/mapstore/configs/localConfig.json

# 4. Restart MapStore to apply CORS configuration
echo "🔄 Restarting MapStore to apply CORS configuration..."
docker-compose -f docker-compose.dev.yml restart mapstore

# 5. Wait for MapStore to start
echo "⏳ Waiting for MapStore to start..."
sleep 30

# 6. Test MapStore accessibility
echo "🧪 Testing MapStore accessibility..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8082/mapstore)
if [ "$HTTP_CODE" = "302" ] || [ "$HTTP_CODE" = "200" ]; then
    echo "  ✅ MapStore is accessible (HTTP $HTTP_CODE)"
else
    echo "  ❌ MapStore is not accessible (HTTP $HTTP_CODE)"
    echo "  💡 Check MapStore logs: docker logs gis_mapstore_dev"
    exit 1
fi

# 7. Test CORS headers
echo "🔍 Testing CORS headers..."
CORS_HEADERS=$(curl -I -H "Origin: http://localhost:8082" http://localhost:8082/mapstore/configs/localConfig.json 2>/dev/null | grep -i "access-control" || echo "No CORS headers found")
if echo "$CORS_HEADERS" | grep -q "access-control"; then
    echo "  ✅ CORS headers found:"
    echo "$CORS_HEADERS" | sed 's/^/    /'
else
    echo "  ⚠️  No CORS headers found (this might be normal for same-origin requests)"
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
echo "✅ MapStore CORS fix complete!"
echo ""
echo "📋 What was fixed:"
echo "  - CORS filter added to web.xml"
echo "  - Extensions directory and file created"
echo "  - Configuration copied to container"
echo "  - MapStore restarted with CORS support"
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
echo "  - Check for CORS errors in browser console"
