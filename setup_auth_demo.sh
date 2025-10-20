#!/bin/bash

# GIS Carbon AI - Authentication Demo Setup Script
# This script sets up test layers in GeoServer for authentication testing

echo "🚀 Setting up Authentication Demo for GIS Carbon AI..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker first."
    exit 1
fi

# Check if containers are running
print_info "Checking if required containers are running..."

if ! docker ps | grep -q "gis_postgres_dev"; then
    print_error "PostgreSQL container is not running. Please start your services first:"
    echo "docker-compose -f docker-compose.dev.yml up -d"
    exit 1
fi

if ! docker ps | grep -q "gis_geoserver_dev"; then
    print_error "GeoServer container is not running. Please start your services first:"
    echo "docker-compose -f docker-compose.dev.yml up -d"
    exit 1
fi

print_status "All required containers are running"

# Step 1: Set up PostgreSQL data
print_info "Step 1: Setting up test data in PostgreSQL..."

if docker exec -i gis_postgres_dev psql -U gis_user -d gis_carbon_data < geoserver/setup_test_layers.sql; then
    print_status "PostgreSQL test data created successfully"
else
    print_error "Failed to create PostgreSQL test data"
    exit 1
fi

# Step 2: Install Python dependencies
print_info "Step 2: Installing Python dependencies..."

if pip install requests > /dev/null 2>&1; then
    print_status "Python dependencies installed"
else
    print_warning "Could not install Python dependencies. Please install manually: pip install requests"
fi

# Step 3: Set up GeoServer layers
print_info "Step 3: Setting up GeoServer layers..."

if python geoserver/setup_geoserver_layers.py; then
    print_status "GeoServer layers created successfully"
else
    print_error "Failed to create GeoServer layers"
    exit 1
fi

# Step 4: Update MapStore configuration
print_info "Step 4: Updating MapStore configuration..."

if cp mapstore/mapstore-auth-test-config.json mapstore/localConfig.json; then
    print_status "MapStore configuration updated"
else
    print_warning "Could not update MapStore configuration. Please copy manually:"
    echo "cp mapstore/mapstore-auth-test-config.json mapstore/localConfig.json"
fi

# Step 5: Restart MapStore
print_info "Step 5: Restarting MapStore..."

if docker-compose -f docker-compose.dev.yml restart mapstore > /dev/null 2>&1; then
    print_status "MapStore restarted successfully"
else
    print_warning "Could not restart MapStore. Please restart manually:"
    echo "docker-compose -f docker-compose.dev.yml restart mapstore"
fi

# Wait for MapStore to start
print_info "Waiting for MapStore to start..."
sleep 10

# Test if services are accessible
print_info "Testing service accessibility..."

# Test PostgreSQL
if docker exec gis_postgres_dev psql -U gis_user -d gis_carbon_data -c "SELECT COUNT(*) FROM auth_demo.public_sample_geometries;" > /dev/null 2>&1; then
    print_status "PostgreSQL test data accessible"
else
    print_error "PostgreSQL test data not accessible"
fi

# Test GeoServer
if curl -s -u admin:admin "http://localhost:8080/geoserver/rest/layers" | grep -q "auth_demo"; then
    print_status "GeoServer layers accessible"
else
    print_warning "GeoServer layers may not be accessible yet. Please check manually."
fi

# Test MapStore
if curl -s "http://localhost:8082/mapstore" | grep -q "MapStore"; then
    print_status "MapStore accessible"
else
    print_warning "MapStore may not be accessible yet. Please check manually."
fi

echo ""
echo "🎉 Authentication Demo Setup Complete!"
echo ""
echo "📋 Created Test Layers:"
echo "   🌍 Public Layer: auth_demo:public_sample_geometries (Green points)"
echo "   🔒 Private Layer: auth_demo:private_analysis_results (Red polygons)"
echo "   👑 Admin Layer: auth_demo:admin_system_config (Admin points)"
echo ""
echo "🧪 Test Users:"
echo "   👤 Public User: public/public123 (viewer role)"
echo "   👤 Analyst User: analyst/analyst123 (analyst role)"
echo "   👤 Admin User: admin/admin123 (admin role)"
echo ""
echo "🔗 Test URLs:"
echo "   📊 GeoServer Admin: http://localhost:8080/geoserver (admin:admin)"
echo "   🗺️  MapStore: http://localhost:8082/mapstore"
echo ""
echo "📖 Next Steps:"
echo "   1. Open MapStore: http://localhost:8082/mapstore"
echo "   2. Test without login (should see only green points)"
echo "   3. Login as analyst (should see green + red)"
echo "   4. Login as admin (should see all layers)"
echo ""
echo "📚 For detailed instructions, see: VISUAL_AUTH_SIMULATION_GUIDE.md"
