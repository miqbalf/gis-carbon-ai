#!/bin/bash

# Test Database Setup Script
# This script tests the database configuration for both Django and GeoServer

echo "Testing Database Setup for GIS Carbon AI..."
echo "============================================="

# Test PostgreSQL connection
echo "1. Testing PostgreSQL connection..."
docker exec gis_postgres_dev psql -U gis_user -d gis_carbon -c "SELECT version();" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✅ Django database (gis_carbon) connection successful"
else
    echo "❌ Django database (gis_carbon) connection failed"
fi

docker exec gis_postgres_dev psql -U gis_user -d gis_carbon_data -c "SELECT version();" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✅ GeoServer database (gis_carbon_data) connection successful"
else
    echo "❌ GeoServer database (gis_carbon_data) connection failed"
fi

# Test PostGIS extensions
echo ""
echo "2. Testing PostGIS extensions..."
docker exec gis_postgres_dev psql -U gis_user -d gis_carbon -c "SELECT PostGIS_version();" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✅ PostGIS extension enabled in Django database"
else
    echo "❌ PostGIS extension not found in Django database"
fi

docker exec gis_postgres_dev psql -U gis_user -d gis_carbon_data -c "SELECT PostGIS_version();" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✅ PostGIS extension enabled in GeoServer database"
else
    echo "❌ PostGIS extension not found in GeoServer database"
fi

# Test sample data
echo ""
echo "3. Testing sample spatial data..."
docker exec gis_postgres_dev psql -U gis_user -d gis_carbon_data -c "SELECT COUNT(*) FROM sample_geometries;" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✅ Sample spatial data found in GeoServer database"
else
    echo "❌ Sample spatial data not found in GeoServer database"
fi

# Test Django database migrations
echo ""
echo "4. Testing Django database setup..."
docker exec gis_django_dev python manage.py showmigrations 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✅ Django can connect to database and show migrations"
else
    echo "❌ Django database connection or migration check failed"
fi

# Test GeoServer connection
echo ""
echo "5. Testing GeoServer connection..."
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/geoserver/ 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✅ GeoServer is accessible"
else
    echo "❌ GeoServer is not accessible"
fi

echo ""
echo "Database setup test completed!"
echo "=============================="
echo ""
echo "Next steps:"
echo "1. Run Django migrations: docker exec gis_django_dev python manage.py migrate"
echo "2. Create Django superuser: docker exec -it gis_django_dev python manage.py createsuperuser"
echo "3. Configure GeoServer data store using the init script: ./geoserver/init-geoserver-db.sh"
echo "4. Access GeoServer at: http://localhost:8080/geoserver (admin/admin)"
echo "5. Access Django admin at: http://localhost:8000/admin"
