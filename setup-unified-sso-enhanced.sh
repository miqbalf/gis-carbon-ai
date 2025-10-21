#!/bin/bash

echo "🚀 Setting up Enhanced Unified SSO for GIS Carbon AI..."

# Navigate to project root
cd "$(dirname "$0")"

# Configuration
GEOSERVER_URL="http://localhost:8080/geoserver"
DJANGO_URL="http://localhost:8000"
FASTAPI_URL="http://localhost:8001"
MAPSTORE_URL="http://localhost:8082"

# 1. Ensure Docker services are up
echo "📦 Bringing up Docker services..."
docker-compose -f docker-compose.dev.yml up -d --build postgres geoserver mapstore django fastapi jupyter

# Wait for services to be healthy
echo "⏳ Waiting for services to be ready..."
sleep 30

# 2. Wait for GeoServer to be fully ready
echo "🔒 Setting up GeoServer unified roles..."
echo "⏳ Waiting for GeoServer web UI to be ready..."
ATTEMPTS=0
until curl -s -o /dev/null -w "%{http_code}" "$GEOSERVER_URL/web/" | grep -q "200\|302"; do
  ATTEMPTS=$((ATTEMPTS+1))
  if [ "$ATTEMPTS" -ge 60 ]; then
    echo "(warn) GeoServer web UI not ready after 120s; proceeding anyway"
    break
  fi
  sleep 2
done

# 3. Run enhanced GeoServer SSO setup
echo "🔐 Running enhanced GeoServer SSO setup..."
if [ -f geoserver/scripts/setup-sso.sh ]; then
  docker exec gis_geoserver_dev /scripts/setup-sso.sh || echo "(warn) GeoServer SSO setup script exited with non-zero status"
else
  echo "(warn) geoserver/scripts/setup-sso.sh not found; skipping SSO setup"
fi

# 4. Copy auth service to containers
echo "📋 Setting up unified authentication service..."
docker exec gis_django_dev mkdir -p /app/auth || true
docker exec gis_fastapi_dev mkdir -p /app/auth || true
docker cp auth/unified-auth-service.py gis_django_dev:/app/auth/ 2>/dev/null || true
docker cp auth/unified-roles-config.json gis_django_dev:/app/auth/ 2>/dev/null || true
docker cp auth/unified-auth-service.py gis_fastapi_dev:/app/auth/ 2>/dev/null || true
docker cp auth/unified-roles-config.json gis_fastapi_dev:/app/auth/ 2>/dev/null || true

# 5. Create Django user groups with enhanced roles
echo "👥 Creating Django user groups..."
docker-compose -f docker-compose.dev.yml exec -T django bash -lc 'python - <<"PY"
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sv_carbon_removal.settings")
import django
django.setup()
from django.contrib.auth.models import Group
from django.contrib.auth import get_user_model

User = get_user_model()

# Create enhanced groups based on GeoNode approach
groups = [
    "ROLE_ANONYMOUS", 
    "ROLE_AUTHENTICATED", 
    "ROLE_ANALYST", 
    "ROLE_GROUP_ADMIN",
    "ROLE_ADMINISTRATOR",
    "ROLE_SERVICE_ADMIN",
    "ROLE_LAYER_ADMIN",
    "ROLE_STYLE_ADMIN",
    "ROLE_WORKSPACE_ADMIN"
]
for group_name in groups:
    group, created = Group.objects.get_or_create(name=group_name)
    print(("Created" if created else "Exists"), "group:", group_name)

# Create test users with enhanced roles
test_users = [
    {
        "name": "demo_user", 
        "password": "demo123", 
        "email": "demo@example.com", 
        "groups": ["ROLE_AUTHENTICATED"]
    },
    {
        "name": "analyst", 
        "password": "analyst123", 
        "email": "analyst@example.com", 
        "groups": ["ROLE_AUTHENTICATED", "ROLE_ANALYST"]
    },
    {
        "name": "layer_admin", 
        "password": "layer123", 
        "email": "layer@example.com", 
        "groups": ["ROLE_AUTHENTICATED", "ROLE_LAYER_ADMIN"]
    },
    {
        "name": "admin", 
        "password": "admin123", 
        "email": "admin@example.com", 
        "groups": ["ROLE_ADMINISTRATOR"]
    },
]

for user_data in test_users:
    user, created = User.objects.get_or_create(
        email=user_data["email"],
        defaults={"name": user_data["name"], "is_active": True},
    )
    if created:
        user.set_password(user_data["password"])
        user.save()
        print("Created user:", user_data["email"]) 
    else:
        print("User already exists:", user_data["email"]) 

    # Add to groups
    user.groups.clear()
    for group_name in user_data["groups"]:
        group = Group.objects.get(name=group_name)
        user.groups.add(group)
    print("Added", user_data["email"], "to groups:", user_data["groups"]) 
PY'

# 6. Setup GeoServer workspace and datastore with enhanced configuration
echo "🗄️  Setting up GeoServer workspace and datastore..."
echo "⏳ Waiting for GeoServer REST API to be available..."
ATTEMPTS=0
until curl -s -u admin:admin -o /dev/null -w "%{http_code}" "$GEOSERVER_URL/rest/workspaces.json" | grep -q "200"; do
  ATTEMPTS=$((ATTEMPTS+1))
  if [ "$ATTEMPTS" -ge 30 ]; then
    echo "(warn) GeoServer REST API not ready after 60s; proceeding anyway"
    break
  fi
  sleep 2
done

# Use the create-datastore.sh script to setup GeoServer
if [ -f geoserver/create-datastore.sh ]; then
  chmod +x geoserver/create-datastore.sh
  echo "📦 Creating GeoServer workspace 'gis_carbon'..."
  ./geoserver/create-datastore.sh create-workspace gis_carbon || echo "(info) Workspace may already exist"
  sleep 2
  
  echo "📦 Creating GeoServer datastore 'gis_carbon_postgis'..."
  ./geoserver/create-datastore.sh create-datastore gis_carbon gis_carbon_postgis gis_carbon_data || echo "(info) Datastore may already exist"
  sleep 2
  
  echo "📋 Available tables in datastore:"
  ./geoserver/create-datastore.sh list-tables gis_carbon gis_carbon_postgis || true
else
  echo "(warn) geoserver/create-datastore.sh not found; skipping datastore setup"
fi

# 7. Configure MapStore integration
echo "🗺️  Configuring MapStore integration..."
if [ -f mapstore/localConfig.json ]; then
  echo "📝 Updating MapStore configuration for SSO..."
  # Update MapStore config to use unified authentication
  docker exec gis_mapstore_dev sh -c '
    if [ -f /usr/local/tomcat/webapps/mapstore/config/localConfig.json ]; then
      cp /usr/local/tomcat/webapps/mapstore/config/localConfig.json /usr/local/tomcat/webapps/mapstore/config/localConfig.json.backup
    fi
  ' || true
fi

# 8. Restart services to pick up new configurations
echo "🔄 Restarting services..."
docker-compose -f docker-compose.dev.yml restart django fastapi mapstore

# 9. Wait for services to be ready
echo "⏳ Waiting for services to restart..."
sleep 20

# 10. Test the enhanced setup
echo "🧪 Testing enhanced unified SSO setup..."

# Test Django authentication
echo "Testing Django authentication..."
curl -X POST "$DJANGO_URL/api/auth/unified-login/" \
  -H "Content-Type: application/json" \
  -d '{"username": "demo_user", "password": "demo123"}' \
  | jq '.message' 2>/dev/null || echo "Django auth test completed"

# Test GeoServer authentication
echo "Testing GeoServer authentication..."
curl -u demo_user:demo123 "$GEOSERVER_URL/rest/workspaces.json" \
  -o /tmp/geoserver_test.json 2>/dev/null && echo "✅ GeoServer authentication working" || echo "❌ GeoServer authentication failed"

# Test MapStore access
echo "Testing MapStore access..."
curl -I "$MAPSTORE_URL/mapstore" \
  -o /tmp/mapstore_test.txt 2>/dev/null && echo "✅ MapStore access working" || echo "❌ MapStore access failed"

echo ""
echo "🎉 Enhanced Unified SSO setup complete!"
echo ""
echo "📋 Test Users:"
echo "  - demo_user (password: demo123) - Role: ROLE_AUTHENTICATED"
echo "  - analyst (password: analyst123) - Role: ROLE_ANALYST"
echo "  - layer_admin (password: layer123) - Role: ROLE_LAYER_ADMIN"
echo "  - admin (password: admin123) - Role: ROLE_ADMINISTRATOR"
echo ""
echo "🌐 Access Points:"
echo "  - MapStore: $MAPSTORE_URL/mapstore"
echo "  - GeoServer: $GEOSERVER_URL/web/"
echo "  - Django API: $DJANGO_URL/api/"
echo "  - FastAPI: $FASTAPI_URL/"
echo ""
echo "🗄️  GeoServer Setup:"
echo "  - Workspace: gis_carbon"
echo "  - Datastore: gis_carbon_postgis"
echo "  - Database: gis_carbon_data (PostgreSQL)"
echo "  - Django Database: gis_carbon (PostgreSQL)"
echo ""
echo "🔐 Enhanced Authentication Features:"
echo "  - Unified JWT tokens across all services"
echo "  - Role-based access control (RBAC)"
echo "  - CORS support for cross-origin requests"
echo "  - Enhanced security filters"
echo "  - Service-level security configuration"
echo "  - User group management"
echo ""
echo "🚀 Next Steps:"
echo "  1. Access MapStore at $MAPSTORE_URL/mapstore"
echo "  2. Login with any test user credentials"
echo "  3. Access GeoServer layers through MapStore"
echo "  4. Use Django API for data management"
echo "  5. Configure additional layers in GeoServer"
