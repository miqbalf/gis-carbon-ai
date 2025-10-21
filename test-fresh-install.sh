#!/bin/bash

# Test script to verify MapStore works from a fresh git clone
# Run this after: git clone <repo> && cd gis-carbon-ai

echo "🧪 Testing fresh install setup..."

# Check if required files exist
echo "📁 Checking required files..."
required_files=(
    "mapstore/Dockerfile"
    "mapstore/geostore-datasource-ovr-postgres.properties"
    "mapstore/auto-configure-services.js"
    "mapstore/default-localConfig.json"
    "docker-compose.dev.yml"
)

for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✅ $file exists"
    else
        echo "  ❌ $file missing"
        exit 1
    fi
done

# Check database configuration
echo "🔍 Checking database configuration..."
if grep -q "jdbc:postgresql://postgres:5432/gis_carbon" mapstore/geostore-datasource-ovr-postgres.properties; then
    echo "  ✅ Database URL is correct"
else
    echo "  ❌ Database URL is incorrect"
    exit 1
fi

if grep -q "hibernate.hbm2ddl.auto]=update" mapstore/geostore-datasource-ovr-postgres.properties; then
    echo "  ✅ Database schema mode is set to 'update' (preserves data)"
else
    echo "  ❌ Database schema mode is not set to 'update'"
    exit 1
fi

# Check docker-compose configuration
echo "🐳 Checking docker-compose configuration..."
if grep -q "Ddatadir.location=/usr/local/tomcat/datadir" docker-compose.dev.yml; then
    echo "  ✅ Datadir location is configured"
else
    echo "  ❌ Datadir location is not configured"
    exit 1
fi

if grep -q "geostore-datasource-ovr-postgres.properties" docker-compose.dev.yml; then
    echo "  ✅ Database configuration file is mounted"
else
    echo "  ❌ Database configuration file is not mounted"
    exit 1
fi

echo ""
echo "🎉 All checks passed! Fresh install should work correctly."
echo ""
echo "To start the services:"
echo "  docker-compose -f docker-compose.dev.yml up -d"
echo ""
echo "To test MapStore:"
echo "  curl -I http://localhost:8082/mapstore/"
echo ""
echo "Expected result: HTTP/1.1 200"
