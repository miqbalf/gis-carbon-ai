#!/bin/bash

# GeoServer Database Configuration Script
# This script configures GeoServer to connect to the gis_carbon_data database

echo "Configuring GeoServer database connection..."

# Wait for GeoServer to be ready
echo "Waiting for GeoServer to start..."
sleep 30

# GeoServer REST API endpoint
GEOSERVER_URL="http://localhost:8080/geoserver"
ADMIN_USER="admin"
ADMIN_PASSWORD="admin"

# Database connection parameters
DB_HOST="postgres"
DB_PORT="5432"
DB_NAME="gis_carbon_data"
DB_USER="gis_user"
DB_PASSWORD="gis_password"

# Create workspace
echo "Creating workspace..."
curl -u "${ADMIN_USER}:${ADMIN_PASSWORD}" \
  -X POST \
  -H "Content-type: text/xml" \
  -d "<workspace><name>gis_carbon</name></workspace>" \
  "${GEOSERVER_URL}/rest/workspaces"

# Create data store
echo "Creating PostGIS data store..."
curl -u "${ADMIN_USER}:${ADMIN_PASSWORD}" \
  -X POST \
  -H "Content-type: text/xml" \
  -d "<dataStore>
    <name>gis_carbon_data</name>
    <type>PostGIS</type>
    <enabled>true</enabled>
    <workspace>
      <name>gis_carbon</name>
    </workspace>
    <connectionParameters>
      <entry key=\"host\">${DB_HOST}</entry>
      <entry key=\"port\">${DB_PORT}</entry>
      <entry key=\"database\">${DB_NAME}</entry>
      <entry key=\"user\">${DB_USER}</entry>
      <entry key=\"passwd\">${DB_PASSWORD}</entry>
      <entry key=\"dbtype\">postgis</entry>
      <entry key=\"schema\">public</entry>
      <entry key=\"Expose primary keys\">true</entry>
    </connectionParameters>
  </dataStore>" \
  "${GEOSERVER_URL}/rest/workspaces/gis_carbon/datastores"

# Create layer from sample_geometries table
echo "Creating layer from sample_geometries table..."
curl -u "${ADMIN_USER}:${ADMIN_PASSWORD}" \
  -X POST \
  -H "Content-type: text/xml" \
  -d "<featureType>
    <name>sample_geometries</name>
    <nativeName>sample_geometries</nativeName>
    <title>Sample Geometries</title>
    <abstract>Sample spatial data for testing</abstract>
    <enabled>true</enabled>
    <srs>EPSG:4326</srs>
    <nativeBoundingBox>
      <minx>-180</minx>
      <maxx>180</maxx>
      <miny>-90</miny>
      <maxy>90</maxy>
      <crs>EPSG:4326</crs>
    </nativeBoundingBox>
    <latLonBoundingBox>
      <minx>-180</minx>
      <maxx>180</maxx>
      <miny>-90</miny>
      <maxy>90</maxy>
      <crs>EPSG:4326</crs>
    </latLonBoundingBox>
  </featureType>" \
  "${GEOSERVER_URL}/rest/workspaces/gis_carbon/datastores/gis_carbon_data/featuretypes"

echo "GeoServer database configuration completed!"
echo "You can now access GeoServer at: http://localhost:8080/geoserver"
echo "Username: admin, Password: admin"
echo "Sample layer available at: http://localhost:8080/geoserver/gis_carbon/wms?service=WMS&version=1.1.0&request=GetMap&layers=gis_carbon:sample_geometries&styles=&bbox=-180,-90,180,90&width=768&height=330&srs=EPSG:4326&format=image/png"
