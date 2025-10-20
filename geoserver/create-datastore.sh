#!/bin/bash

# GeoServer Data Store Creation Script
# This script helps you create new PostGIS data stores in GeoServer

# Default GeoServer configuration
GEOSERVER_URL="http://localhost:8080/geoserver"
ADMIN_USER="admin"
ADMIN_PASSWORD="admin"

# Default PostGIS connection parameters
DB_HOST="postgres"
DB_PORT="5432"
DB_NAME="gis_carbon_data"
DB_USER="gis_user"
DB_PASSWORD="gis_password"

# Function to create a new workspace
create_workspace() {
    local workspace_name=$1
    echo "Creating workspace: $workspace_name"
    
    curl -u "${ADMIN_USER}:${ADMIN_PASSWORD}" \
        -X POST \
        -H "Content-type: text/xml" \
        -d "<workspace><name>${workspace_name}</name></workspace>" \
        "${GEOSERVER_URL}/rest/workspaces"
    
    if [ $? -eq 0 ]; then
        echo "✅ Workspace '$workspace_name' created successfully"
    else
        echo "❌ Failed to create workspace '$workspace_name'"
    fi
}

# Function to create a new PostGIS data store
create_datastore() {
    local workspace_name=$1
    local datastore_name=$2
    local database_name=${3:-$DB_NAME}
    
    echo "Creating PostGIS data store: $datastore_name in workspace: $workspace_name"
    
    curl -u "${ADMIN_USER}:${ADMIN_PASSWORD}" \
        -X POST \
        -H "Content-type: text/xml" \
        -d "<dataStore>
            <name>${datastore_name}</name>
            <type>PostGIS</type>
            <enabled>true</enabled>
            <workspace>
                <name>${workspace_name}</name>
            </workspace>
            <connectionParameters>
                <entry key=\"host\">${DB_HOST}</entry>
                <entry key=\"port\">${DB_PORT}</entry>
                <entry key=\"database\">${database_name}</entry>
                <entry key=\"user\">${DB_USER}</entry>
                <entry key=\"passwd\">${DB_PASSWORD}</entry>
                <entry key=\"dbtype\">postgis</entry>
                <entry key=\"schema\">public</entry>
                <entry key=\"Expose primary keys\">true</entry>
                <entry key=\"validate connections\">true</entry>
                <entry key=\"Support on the fly geometry simplification\">true</entry>
                <entry key=\"create database\">false</entry>
                <entry key=\"preparedStatements\">false</entry>
            </connectionParameters>
        </dataStore>" \
        "${GEOSERVER_URL}/rest/workspaces/${workspace_name}/datastores"
    
    if [ $? -eq 0 ]; then
        echo "✅ Data store '$datastore_name' created successfully"
    else
        echo "❌ Failed to create data store '$datastore_name'"
    fi
}

# Function to list available tables in a data store
list_tables() {
    local workspace_name=$1
    local datastore_name=$2
    
    echo "Listing tables in data store: $datastore_name"
    
    curl -u "${ADMIN_USER}:${ADMIN_PASSWORD}" \
        -X GET \
        "${GEOSERVER_URL}/rest/workspaces/${workspace_name}/datastores/${datastore_name}/featuretypes.json" \
        | python3 -m json.tool 2>/dev/null || echo "No tables found or data store doesn't exist"
}

# Function to create a layer from a table
create_layer() {
    local workspace_name=$1
    local datastore_name=$2
    local table_name=$3
    local layer_title=${4:-$table_name}
    
    echo "Creating layer from table: $table_name"
    
    curl -u "${ADMIN_USER}:${ADMIN_PASSWORD}" \
        -X POST \
        -H "Content-type: text/xml" \
        -d "<featureType>
            <name>${table_name}</name>
            <nativeName>${table_name}</nativeName>
            <title>${layer_title}</title>
            <abstract>Layer created from ${table_name} table</abstract>
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
        "${GEOSERVER_URL}/rest/workspaces/${workspace_name}/datastores/${datastore_name}/featuretypes"
    
    if [ $? -eq 0 ]; then
        echo "✅ Layer '$table_name' created successfully"
        echo "   WMS URL: ${GEOSERVER_URL}/${workspace_name}/wms?service=WMS&version=1.1.0&request=GetMap&layers=${workspace_name}:${table_name}&styles=&bbox=-180,-90,180,90&width=768&height=330&srs=EPSG:4326&format=image/png"
    else
        echo "❌ Failed to create layer '$table_name'"
    fi
}

# Main menu
echo "GeoServer PostGIS Data Store Manager"
echo "===================================="
echo ""
echo "Default GeoServer Configuration:"
echo "  URL: $GEOSERVER_URL"
echo "  Username: $ADMIN_USER"
echo "  Password: $ADMIN_PASSWORD"
echo ""
echo "Default PostGIS Configuration:"
echo "  Host: $DB_HOST"
echo "  Port: $DB_PORT"
echo "  Database: $DB_NAME"
echo "  Username: $DB_USER"
echo "  Password: $DB_PASSWORD"
echo ""
echo "Available commands:"
echo "1. Create workspace: $0 create-workspace <workspace_name>"
echo "2. Create data store: $0 create-datastore <workspace_name> <datastore_name> [database_name]"
echo "3. List tables: $0 list-tables <workspace_name> <datastore_name>"
echo "4. Create layer: $0 create-layer <workspace_name> <datastore_name> <table_name> [layer_title]"
echo "5. Quick setup: $0 quick-setup <workspace_name> <datastore_name>"
echo ""

# Handle command line arguments
case "$1" in
    "create-workspace")
        if [ -z "$2" ]; then
            echo "Usage: $0 create-workspace <workspace_name>"
            exit 1
        fi
        create_workspace "$2"
        ;;
    "create-datastore")
        if [ -z "$3" ]; then
            echo "Usage: $0 create-datastore <workspace_name> <datastore_name> [database_name]"
            exit 1
        fi
        create_datastore "$2" "$3" "$4"
        ;;
    "list-tables")
        if [ -z "$3" ]; then
            echo "Usage: $0 list-tables <workspace_name> <datastore_name>"
            exit 1
        fi
        list_tables "$2" "$3"
        ;;
    "create-layer")
        if [ -z "$4" ]; then
            echo "Usage: $0 create-layer <workspace_name> <datastore_name> <table_name> [layer_title]"
            exit 1
        fi
        create_layer "$2" "$3" "$4" "$5"
        ;;
    "quick-setup")
        if [ -z "$3" ]; then
            echo "Usage: $0 quick-setup <workspace_name> <datastore_name>"
            exit 1
        fi
        echo "Quick setup for workspace: $2, datastore: $3"
        create_workspace "$2"
        sleep 2
        create_datastore "$2" "$3"
        sleep 2
        list_tables "$2" "$3"
        ;;
    *)
        echo "Invalid command. Use one of the commands listed above."
        exit 1
        ;;
esac
