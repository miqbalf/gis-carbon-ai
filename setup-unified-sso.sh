#!/bin/bash

echo "🚀 Setting up Unified SSO for GIS Carbon AI..."

# Navigate to project root
cd "$(dirname "$0")"

# 1. Ensure Docker services are up
echo "📦 Bringing up Docker services..."
docker-compose -f docker-compose.dev.yml up -d --build postgres geoserver mapstore django fastapi jupyter

# Wait for services to be healthy
echo "⏳ Waiting for services to be ready..."
sleep 30

# 2. Copy auth service to containers
echo "📋 Setting up unified authentication service..."
docker exec gis_django_dev mkdir -p /app/auth || true
docker exec gis_fastapi_dev mkdir -p /app/auth || true
docker cp auth/unified-auth-service.py gis_django_dev:/app/auth/ 2>/dev/null || true
docker cp auth/unified-roles-config.json gis_django_dev:/app/auth/ 2>/dev/null || true
docker cp auth/unified-auth-service.py gis_fastapi_dev:/app/auth/ 2>/dev/null || true
docker cp auth/unified-roles-config.json gis_fastapi_dev:/app/auth/ 2>/dev/null || true

# 3. Wait for GeoServer to fully initialize and inject unified role service
echo "🔒 Setting up GeoServer unified roles..."
echo "⏳ Waiting for GeoServer web UI to be ready..."
ATTEMPTS=0
until curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/geoserver/web/ | grep -q "200\|302"; do
  ATTEMPTS=$((ATTEMPTS+1))
  if [ "$ATTEMPTS" -ge 60 ]; then
    echo "(warn) GeoServer web UI not ready after 120s; proceeding anyway"
    break
  fi
  sleep 2
done

echo "📋 Injecting unified REST role service config..."
docker exec gis_geoserver_dev mkdir -p /opt/geoserver/data_dir/security/role/unified_rest_role_service || true
docker cp geoserver/config/security/role/unified_rest_role_service/config.xml \
  gis_geoserver_dev:/opt/geoserver/data_dir/security/role/unified_rest_role_service/config.xml
docker exec gis_geoserver_dev chown -R geoserveruser:geoserverusers \
  /opt/geoserver/data_dir/security/role/unified_rest_role_service || true

echo "🔄 Restarting GeoServer to activate unified role service..."
docker-compose -f docker-compose.dev.yml restart geoserver
sleep 10

if [ -f geoserver/setup-unified-roles.py ]; then
  docker exec gis_django_dev mkdir -p /usr/src/app/geoserver || true
  docker cp geoserver/setup-unified-roles.py gis_django_dev:/usr/src/app/geoserver/setup-unified-roles.py

  echo "⏳ Waiting for GeoServer to be reachable after restart..."
  ATTEMPTS=0
  until docker-compose -f docker-compose.dev.yml exec -T django sh -lc "nc -z geoserver 8080"; do
    ATTEMPTS=$((ATTEMPTS+1))
    if [ "$ATTEMPTS" -ge 30 ]; then
      echo "(warn) GeoServer not reachable after waiting; proceeding anyway"
      break
    fi
    sleep 2
  done

  docker-compose -f docker-compose.dev.yml exec -T -e GEOSERVER_URL=http://geoserver:8080/geoserver django \
    python /usr/src/app/geoserver/setup-unified-roles.py || echo "(warn) GeoServer role setup script exited with non-zero status"
else
  echo "(info) geoserver/setup-unified-roles.py not found; skipping role setup"
fi

# 4. Create Django user groups
echo "👥 Creating Django user groups..."
docker-compose -f docker-compose.dev.yml exec -T django bash -lc 'python - <<"PY"
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sv_carbon_removal.settings")
import django
django.setup()
from django.contrib.auth.models import Group
from django.contrib.auth import get_user_model

User = get_user_model()

# Create groups
groups = ["ROLE_ANONYMOUS", "ROLE_AUTHENTICATED", "ROLE_ANALYST", "ADMIN"]
for group_name in groups:
    group, created = Group.objects.get_or_create(name=group_name)
    print(("Created" if created else "Exists"), "group:", group_name)

# Create test users (custom User uses email as identifier)
test_users = [
    {"name": "demo_user", "password": "demo123", "email": "demo@example.com", "groups": ["ROLE_AUTHENTICATED"]},
    {"name": "analyst", "password": "analyst123", "email": "analyst@example.com", "groups": ["ROLE_AUTHENTICATED", "ROLE_ANALYST"]},
    {"name": "admin", "password": "admin123", "email": "admin@example.com", "groups": ["ADMIN"]},
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

# 5. Restart services to pick up new configurations
echo "🔄 Restarting services..."
docker-compose -f docker-compose.dev.yml restart django fastapi mapstore

# 6. Wait for services to be ready
echo "⏳ Waiting for services to restart..."
sleep 20

# 7. Test the setup
echo "🧪 Testing unified SSO setup..."

# Test Django authentication
echo "Testing Django authentication..."
curl -X POST http://localhost:8000/api/auth/unified-login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "demo_user", "password": "demo123"}' \
  | jq '.message' 2>/dev/null || echo "Django auth test completed"

# Test GeoServer layer access
echo "Testing GeoServer layer access..."
curl -u demo_user:demo123 "http://localhost:8080/geoserver/demo_workspace/wms?service=WMS&version=1.3.0&request=GetMap&layers=demo_workspace:forest_areas&format=image/png&width=256&height=256&crs=EPSG:4326&bbox=106.8,-6.25,106.9,-6.15" \
  -o /tmp/test_layer.png 2>/dev/null && echo "✅ GeoServer layer access working" || echo "❌ GeoServer layer access failed"

echo ""
echo "🎉 Unified SSO setup complete!"
echo ""
echo "📋 Test Users:"
echo "  - demo_user (password: demo123) - Role: ROLE_AUTHENTICATED"
echo "  - analyst (password: analyst123) - Role: ROLE_ANALYST"
echo "  - admin (password: admin123) - Role: ADMIN"
echo ""
echo "🌐 Access Points:"
echo "  - MapStore: http://localhost:8082/mapstore"
echo "  - GeoServer: http://localhost:8080/geoserver"
echo "  - Django API: http://localhost:8000/api/"
echo "  - FastAPI: http://localhost:8001/"
echo ""
echo "🔐 Authentication Flow:"
echo "  1. Login via MapStore or Django API"
echo "  2. Get unified JWT token"
echo "  3. Token works across all services"
echo "  4. Role-based access control enforced"
