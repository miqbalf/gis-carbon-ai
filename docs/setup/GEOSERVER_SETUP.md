# GeoServer Setup Guide for GIS Carbon AI

## Default Credentials and Configuration

### GeoServer Access
- **URL**: http://localhost:8080/geoserver
- **Username**: `admin`
- **Password**: `admin`
- **Admin Panel**: http://localhost:8080/geoserver/web/

### PostGIS Database Connection
- **Host**: `postgres` (internal Docker network) or `localhost` (external access)
- **Port**: `5432`
- **Database**: `gis_carbon_data` (for spatial data)
- **Username**: `gis_user`
- **Password**: `gis_password`

## Creating a New Data Store in GeoServer

### Method 1: Using the Web Interface

1. **Access GeoServer Admin Panel**
   ```
   http://localhost:8080/geoserver/web/
   Username: admin
   Password: admin
   ```

2. **Create a New Workspace**
   - Go to `Data` → `Workspaces`
   - Click `Add new workspace`
   - Enter workspace name (e.g., `my_project`)
   - Click `Save`

3. **Create a New Data Store**
   - Go to `Data` → `Stores`
   - Click `Add new Store`
   - Select `PostGIS` from the vector data sources
   - Fill in the connection parameters:
     ```
     Workspace: my_project
     Data Source Name: my_datastore
     Host: postgres
     Port: 5432
     Database: gis_carbon_data
     Schema: public
     User: gis_user
     Password: gis_password
     ```
   - Click `Save`

4. **Publish a Layer**
   - After creating the data store, you'll see available tables
   - Click `Publish` next to the table you want to use
   - Configure the layer settings (CRS, bounding box, etc.)
   - Click `Save`

### Method 2: Using the Command Line Script

Use the provided script to automate the process:

```bash
# Create a new workspace
./geoserver/create-datastore.sh create-workspace my_project

# Create a new data store
./geoserver/create-datastore.sh create-datastore my_project my_datastore

# List available tables
./geoserver/create-datastore.sh list-tables my_project my_datastore

# Create a layer from a table
./geoserver/create-datastore.sh create-layer my_project my_datastore my_table

# Quick setup (creates workspace, datastore, and lists tables)
./geoserver/create-datastore.sh quick-setup my_project my_datastore
```

### Method 3: Using REST API Directly

```bash
# Create workspace
curl -u "admin:admin" \
  -X POST \
  -H "Content-type: text/xml" \
  -d "<workspace><name>my_project</name></workspace>" \
  "http://localhost:8080/geoserver/rest/workspaces"

# Create data store
curl -u "admin:admin" \
  -X POST \
  -H "Content-type: text/xml" \
  -d "<dataStore>
    <name>my_datastore</name>
    <type>PostGIS</type>
    <enabled>true</enabled>
    <workspace><name>my_project</name></workspace>
    <connectionParameters>
      <entry key=\"host\">postgres</entry>
      <entry key=\"port\">5432</entry>
      <entry key=\"database\">gis_carbon_data</entry>
      <entry key=\"user\">gis_user</entry>
      <entry key=\"passwd\">gis_password</entry>
      <entry key=\"dbtype\">postgis</entry>
      <entry key=\"schema\">public</entry>
    </connectionParameters>
  </dataStore>" \
  "http://localhost:8080/geoserver/rest/workspaces/my_project/datastores"
```

## Accessing Your Layers

### WMS (Web Map Service)
```
http://localhost:8080/geoserver/my_project/wms?service=WMS&version=1.1.0&request=GetMap&layers=my_project:my_layer&styles=&bbox=-180,-90,180,90&width=768&height=330&srs=EPSG:4326&format=image/png
```

### WFS (Web Feature Service)
```
http://localhost:8080/geoserver/my_project/wfs?service=WFS&version=1.0.0&request=GetFeature&typeName=my_project:my_layer&outputFormat=application/json
```

### WCS (Web Coverage Service)
```
http://localhost:8080/geoserver/my_project/wcs?service=WCS&version=1.0.0&request=GetCoverage&coverage=my_project:my_layer&format=GeoTIFF
```

## Creating Spatial Data in PostGIS

### Connect to the Database
```bash
# From host machine
docker exec -it gis_postgres_dev psql -U gis_user -d gis_carbon_data

# Or from within the network
psql -h postgres -U gis_user -d gis_carbon_data
```

### Create a New Spatial Table
```sql
-- Create a table with geometry column
CREATE TABLE my_spatial_data (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255),
    description TEXT,
    geom GEOMETRY(POINT, 4326),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create spatial index
CREATE INDEX idx_my_spatial_data_geom ON my_spatial_data USING GIST (geom);

-- Insert sample data
INSERT INTO my_spatial_data (name, description, geom) VALUES
('Point 1', 'First sample point', ST_GeomFromText('POINT(0 0)', 4326)),
('Point 2', 'Second sample point', ST_GeomFromText('POINT(1 1)', 4326));

-- Grant permissions
GRANT ALL PRIVILEGES ON TABLE my_spatial_data TO gis_user;
GRANT ALL PRIVILEGES ON SEQUENCE my_spatial_data_id_seq TO gis_user;
```

## Troubleshooting

### Common Issues

1. **Connection Refused**
   - Ensure PostgreSQL container is running: `docker ps`
   - Check if GeoServer can reach PostgreSQL: `docker exec gis_geoserver_dev ping postgres`

2. **Authentication Failed**
   - Verify credentials in docker-compose.dev.yml
   - Check PostgreSQL logs: `docker logs gis_postgres_dev`

3. **Layer Not Found**
   - Ensure the table exists in the database
   - Check if the data store is properly configured
   - Verify table has a geometry column

4. **CRS Issues**
   - Ensure your geometry data has proper SRID
   - Use `ST_SetSRID(geom, 4326)` when inserting data
   - Check GeoServer layer CRS settings

### Useful Commands

```bash
# Check GeoServer status
curl -u "admin:admin" "http://localhost:8080/geoserver/rest/about/status.json"

# List all workspaces
curl -u "admin:admin" "http://localhost:8080/geoserver/rest/workspaces.json"

# List all data stores
curl -u "admin:admin" "http://localhost:8080/geoserver/rest/datastores.json"

# Check database connection
docker exec gis_postgres_dev psql -U gis_user -d gis_carbon_data -c "\dt"

# View GeoServer logs
docker logs gis_geoserver_dev
```

## Integration with MapStore

MapStore can consume GeoServer layers through WMS/WFS services. The layers will be available in MapStore's layer catalog and can be added to maps.

### MapStore Configuration
- **GeoServer URL**: http://localhost:8080/geoserver
- **WMS Service**: http://localhost:8080/geoserver/wms
- **WFS Service**: http://localhost:8080/geoserver/wfs

## Security Considerations

1. **Change Default Passwords**: Update admin credentials in production
2. **Network Security**: Use proper firewall rules
3. **Database Access**: Limit database user permissions
4. **SSL/TLS**: Enable HTTPS for production deployments

## Performance Optimization

1. **Spatial Indexes**: Always create spatial indexes on geometry columns
2. **Connection Pooling**: Configure connection pooling in GeoServer
3. **Caching**: Enable GeoWebCache for better performance
4. **Memory**: Adjust JVM memory settings in docker-compose.yml
