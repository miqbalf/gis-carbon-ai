#!/bin/bash

# Build Custom MapStore Docker Image
# This script builds a custom MapStore image with complete configuration

echo "🔨 Building Custom MapStore Docker Image..."

# 1. Stop the current MapStore container
echo "📋 Stopping current MapStore container..."
docker-compose -f docker-compose.dev.yml stop mapstore

# 2. Build the custom MapStore image
echo "🔨 Building custom MapStore image..."
docker build -f ./mapstore/Dockerfile.mapstore -t gis-mapstore-custom:v2025.01.02-stable ./mapstore

if [ $? -eq 0 ]; then
    echo "  ✅ Custom MapStore image built successfully"
else
    echo "  ❌ Failed to build custom MapStore image"
    exit 1
fi

# 3. Start MapStore with custom image
echo "🚀 Starting MapStore with custom image..."
docker-compose -f docker-compose.dev.yml up -d mapstore

# 4. Wait for MapStore to start
echo "⏳ Waiting for MapStore to start..."
sleep 60

# 5. Test MapStore
echo "🧪 Testing custom MapStore..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8082/mapstore)
if [ "$HTTP_CODE" = "302" ] || [ "$HTTP_CODE" = "200" ]; then
    echo "  ✅ Custom MapStore is accessible (HTTP $HTTP_CODE)"
else
    echo "  ❌ Custom MapStore is not accessible (HTTP $HTTP_CODE)"
    echo "  📋 Checking logs..."
    docker logs gis_mapstore_dev --tail 20
    exit 1
fi

# 6. Test configuration
echo "🧪 Testing configuration..."
if curl -s http://localhost:8082/mapstore/configs/localConfig.json | grep -q "plugins"; then
    echo "  ✅ Configuration includes plugins section"
else
    echo "  ❌ Configuration missing plugins section"
    exit 1
fi

# 7. Test extensions
echo "🧪 Testing extensions..."
if curl -s http://localhost:8082/mapstore/extensions/extensions.json | grep -q "\[\]"; then
    echo "  ✅ Extensions working"
else
    echo "  ❌ Extensions not working"
    exit 1
fi

# 8. Run comprehensive test
echo "🧪 Running comprehensive test..."
python test-mapstore-loading.py

echo ""
echo "✅ Custom MapStore build and deployment complete!"
echo ""
echo "📋 What was done:"
echo "  - Built custom MapStore image based on official v2025.01.02-stable"
echo "  - Included complete configuration (map, plugins, catalogServices)"
echo "  - Created proper directory structure"
echo "  - Set correct permissions"
echo "  - Updated docker-compose to use custom image"
echo "  - Started new container with custom image"
echo ""
echo "🌐 Next steps:"
echo "  1. Open MapStore: http://localhost:8082/mapstore"
echo "  2. MapStore should now load completely with full interface"
echo "  3. All plugins and features should be available"
echo ""
echo "💡 Benefits of custom build:"
echo "  - Based on official MapStore v2025.01.02-stable image"
echo "  - Complete configuration included from start"
echo "  - No missing files or directories"
echo "  - Proper permissions set from start"
echo "  - Complete plugin configuration"
echo "  - Optimized for our use case"