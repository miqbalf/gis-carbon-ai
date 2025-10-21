# QGIS to PostGIS Raster Import Guide

This guide explains how to import raster data from QGIS to your PostGIS database with raster support and configure it for GeoServer.

## Prerequisites

- QGIS installed on your system
- Access to your GIS Carbon AI PostgreSQL database
- PostGIS 3.4 with raster support (already configured)

## Database Connection Details

```
Host: localhost
Port: 5432
Database: gis_carbon_data (for GeoServer spatial data)
Username: gis_user
Password: gis_password
```

## Step 1: Connect QGIS to PostGIS Database

1. **Open QGIS** and go to **Browser Panel**
2. **Right-click** on **PostGIS** → **New Connection**
3. **Fill in the connection details:**
   - Name: `GIS Carbon AI Database`
   - Host: `localhost`
   - Port: `5432`
   - Database: `gis_carbon_data`
   - Username: `gis_user`
   - Password: `gis_password`
4. **Test Connection** and click **OK**

## Step 2: Import Raster Data to PostGIS

### Method 1: Using QGIS DB Manager (Recommended)

1. **Open DB Manager**: Go to **Database** → **DB Manager**
2. **Select your connection**: `GIS Carbon AI Database`
3. **Import Raster**: Right-click on **raster_data** schema → **Import Layer/File**
4. **Choose your raster file** (GeoTIFF, etc.)
5. **Configure import settings:**
   - **Table name**: Use descriptive name (e.g., `carbon_density_2024`)
   - **Schema**: `raster_data`
   - **SRID**: Set appropriate coordinate system (e.g., 4326 for WGS84)
   - **Tiling**: Enable for large rasters
   - **Tile size**: 256x256 (recommended)

### Method 2: Using QGIS Processing Toolbox

1. **Open Processing Toolbox**: Go to **Processing** → **Toolbox**
2. **Search for**: "Import raster into PostGIS"
3. **Use the tool**: "Import raster into PostGIS (raster)"
4. **Configure parameters:**
   - **Input raster**: Your raster file
   - **Database**: Select your connection
   - **Schema**: `raster_data`
   - **Table name**: Descriptive name
   - **SRID**: Appropriate coordinate system

### Method 3: Using Command Line (Advanced)

```bash
# Using raster2pgsql (if available)
raster2pgsql -s 4326 -I -C -M -t 256x256 your_raster.tif raster_data.your_table_name | psql -h localhost -U gis_user -d gis_carbon_data
```

## Step 3: Update Raster Metadata

After importing, update the `raster_layers` table with metadata:

```sql
-- Connect to your database and run:
INSERT INTO raster_data.raster_layers (
    name, 
    description, 
    source_file, 
    data_type, 
    resolution_meters, 
    srid, 
    bounds
) VALUES (
    'Carbon Density 2024',
    'Annual carbon density raster data',
    'carbon_density_2024.tif',
    'Carbon',
    30.0,  -- resolution in meters
    4326,  -- SRID
    (SELECT ST_Envelope(ST_Union(rast)) FROM raster_data.raster_data WHERE layer_id = 1)
);
```

## Step 4: Configure GeoServer Raster Store

### Option A: Using GeoServer Web Interface

1. **Access GeoServer**: Go to `http://localhost:8080/geoserver`
2. **Login**: admin/admin
3. **Create Workspace** (if not exists):
   - Go to **Data** → **Workspaces**
   - Click **Add new workspace**
   - Name: `gis_carbon`
   - URI: `http://gis-carbon-ai.local`

4. **Create PostGIS Raster Data Store**:
   - Go to **Data** → **Stores**
   - Click **Add new Store** → **PostGIS Raster**
   - **Workspace**: `gis_carbon`
   - **Data Source Name**: `raster_postgis`
   - **Connection Parameters**:
     - **host**: `postgres`
     - **port**: `5432`
     - **database**: `gis_carbon_data`
     - **schema**: `raster_data`
     - **user**: `gis_user`
     - **passwd**: `gis_password`
     - **dbtype**: `postgisraster`

5. **Publish Raster Layer**:
   - Select your data store
   - Choose your raster table
   - Configure layer settings
   - Set appropriate coordinate system

### Option B: Using REST API (Automated)

```bash
# Create workspace
curl -u admin:admin -X POST -H "Content-type: text/xml" \
  -d "<workspace><name>gis_carbon</name></workspace>" \
  http://localhost:8080/geoserver/rest/workspaces

# Create PostGIS raster data store
curl -u admin:admin -X POST -H "Content-type: text/xml" \
  -d @raster_store_config.xml \
  http://localhost:8080/geoserver/rest/workspaces/gis_carbon/datastores
```

## Step 5: Verify Raster Data

### Check in QGIS:
1. **Add PostGIS Layer**: Right-click your connection → **Add Layer**
2. **Select your raster table** from `raster_data` schema
3. **Verify display** and properties

### Check in GeoServer:
1. **Layer Preview**: Go to **Layer Preview**
2. **Select your raster layer**
3. **Test different formats** (PNG, JPEG, GeoTIFF)

## Step 6: Access in MapStore

Your raster data will be available in MapStore at:
- **WMS URL**: `http://localhost:8080/geoserver/gis_carbon/wms`
- **Layer Name**: Your raster layer name

## Best Practices

### 1. Raster Optimization
- **Use appropriate tile sizes** (256x256 or 512x512)
- **Compress large rasters** before import
- **Consider pyramid levels** for large datasets

### 2. Coordinate Systems
- **Use consistent SRID** across all rasters
- **Reproject if necessary** before import
- **Document coordinate system** in metadata

### 3. Data Management
- **Use descriptive table names**
- **Update metadata regularly**
- **Create indexes** for better performance

### 4. Performance Tips
- **Limit raster size** for web display
- **Use overviews** for large rasters
- **Consider data partitioning** for very large datasets

## Troubleshooting

### Common Issues:

1. **"Provider is not valid (provider: postgresraster)" Error**:
   - **Cause**: The raster table is empty or doesn't contain valid raster data
   - **Solution**: Ensure your raster table has actual raster data before connecting
   - **Test**: Create a sample raster first:
     ```sql
     INSERT INTO raster_data.raster_layers (name, description, data_type, resolution_meters, srid) 
     VALUES ('Test Layer', 'Test raster', 'Test', 30.0, 4326);
     
     INSERT INTO raster_data.raster_data (layer_id, tile_id, rast) 
     VALUES (1, 'test_tile', ST_MakeEmptyRaster(100, 100, 0, 0, 0.01, -0.01, 0, 0, 4326));
     ```

2. **Connection Refused**:
   - Check if PostgreSQL container is running
   - Verify port 5432 is accessible

3. **Permission Denied**:
   - Ensure `gis_user` has proper permissions
   - Check schema permissions

4. **Raster Import Fails**:
   - Verify PostGIS raster extension is installed
   - Check raster file format compatibility
   - Ensure sufficient disk space

5. **GeoServer Can't Access Raster**:
   - Verify data store configuration
   - Check network connectivity between containers
   - Review GeoServer logs

### Alternative Connection Methods:

If the `postgresraster` provider doesn't work, try these alternatives:

#### Method 1: Use Regular PostGIS Connection
1. Connect using standard PostGIS provider
2. Select the `raster_data` schema
3. Choose your raster table
4. QGIS will treat it as a vector layer showing raster bounds

#### Method 2: Import via Processing Toolbox
1. Go to **Processing** → **Toolbox**
2. Search for "Import raster into PostGIS"
3. Use the "Import raster into PostGIS (raster)" tool
4. This creates a properly formatted raster table

#### Method 3: Use DB Manager
1. Open **Database** → **DB Manager**
2. Connect to your PostGIS database
3. Use the **Import Layer/File** option
4. Select "Raster" as the layer type

### Useful SQL Queries:

```sql
-- Check installed PostGIS extensions
SELECT extname, extversion FROM pg_extension WHERE extname LIKE 'postgis%';

-- List raster tables
SELECT schemaname, tablename FROM pg_tables WHERE schemaname = 'raster_data';

-- Check raster metadata
SELECT name, data_type, resolution_meters, srid FROM raster_data.raster_layers;

-- Get raster bounds
SELECT ST_AsText(ST_Envelope(rast)) FROM raster_data.raster_data LIMIT 1;
```

## Next Steps

1. **Import your raster data** using the methods above
2. **Configure GeoServer** to serve the raster data
3. **Test in MapStore** to ensure proper display
4. **Set up automated workflows** for regular data updates

For more advanced configurations or issues, refer to the PostGIS and GeoServer documentation.
