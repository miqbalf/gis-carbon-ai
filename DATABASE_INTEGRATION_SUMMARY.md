# Database Integration Summary

## ✅ Completed Setup

### Database Architecture

```
PostgreSQL Container (gis_postgres_dev)
├── gis_carbon          → Django application database
│   ├── Django models (people, api, etc.)
│   └── MapStore GeoStore tables (automatically created by Hibernate)
│
└── gis_carbon_data     → GeoServer spatial data database
    ├── PostGIS extensions enabled
    ├── Sample spatial tables (sample_geometries)
    └── Connected to GeoServer datastore: gis_carbon_postgis
```

### Service Connections

| Service | Database | Schema | Purpose |
|---------|----------|--------|---------|
| **Django** | `gis_carbon` | `public` | Application data, user management |
| **MapStore** | `gis_carbon` | `public` | Maps, resources, user configs (GeoStore) |
| **GeoServer** | `gis_carbon_data` | `public` | Spatial layers, feature types |

### Automated Setup

The `setup-unified-sso.sh` script now automatically:

1. ✅ Creates PostgreSQL databases (`gis_carbon` + `gis_carbon_data`)
2. ✅ Enables PostGIS extensions on both databases
3. ✅ Creates GeoServer workspace: `gis_carbon`
4. ✅ Creates GeoServer datastore: `gis_carbon_postgis`
5. ✅ Connects datastore to `gis_carbon_data` database
6. ✅ Sets up unified authentication across all services

### Connection Details

#### Django (Port 8000)
```bash
DB_ENGINE=django.db.backends.postgresql
DB_DATABASE=gis_carbon
DB_USER=gis_user
DB_PASSWORD=gis_password
DB_HOST=postgres
DB_PORT=5432
```

#### GeoServer (Port 8080)
- **Workspace**: `gis_carbon`
- **Datastore**: `gis_carbon_postgis` (PostGIS)
- **Database**: `gis_carbon_data`
- **Access**: http://localhost:8080/geoserver
- **Credentials**: admin/admin

#### MapStore (Port 8082)
- **Database**: `gis_carbon` (shares with Django, separate tables)
- **Config**: `mapstore/geostore-datasource-ovr-postgres.properties`
- **Access**: http://localhost:8082/mapstore
- **Storage**: PostgreSQL (not H2)

### Working with GeoServer Data

#### Create a new layer from existing table:
```bash
# If you have a table in gis_carbon_data database:
./geoserver/create-datastore.sh create-layer gis_carbon gis_carbon_postgis your_table_name "Your Layer Title"
```

#### List available tables:
```bash
./geoserver/create-datastore.sh list-tables gis_carbon gis_carbon_postgis
```

#### Test sample layer:
```bash
# The sample_geometries table is already in gis_carbon_data
./geoserver/create-datastore.sh create-layer gis_carbon gis_carbon_postgis sample_geometries "Sample Points"

# View in browser:
# http://localhost:8080/geoserver/gis_carbon/wms?service=WMS&version=1.1.0&request=GetMap&layers=gis_carbon:sample_geometries&styles=&bbox=-180,-90,180,90&width=768&height=330&srs=EPSG:4326&format=image/png
```

### Database Initialization

The databases are automatically initialized on first run via:
- **File**: `postgres/init/01-init-databases.sql`
- **Triggered**: When PostgreSQL container starts for the first time
- **Creates**:
  - `gis_carbon` database with PostGIS
  - `gis_carbon_data` database with PostGIS
  - Sample spatial tables
  - Proper permissions for `gis_user`

### Verification Commands

```bash
# Check databases exist
docker exec gis_postgres_dev psql -U gis_user -l

# Check PostGIS is enabled in gis_carbon
docker exec gis_postgres_dev psql -U gis_user -d gis_carbon -c "SELECT PostGIS_version();"

# Check PostGIS is enabled in gis_carbon_data
docker exec gis_postgres_dev psql -U gis_user -d gis_carbon_data -c "SELECT PostGIS_version();"

# List tables in gis_carbon_data
docker exec gis_postgres_dev psql -U gis_user -d gis_carbon_data -c "\dt"

# Check GeoServer workspace
curl -s -u admin:admin "http://localhost:8080/geoserver/rest/workspaces/gis_carbon.json"

# Check GeoServer datastore
curl -s -u admin:admin "http://localhost:8080/geoserver/rest/workspaces/gis_carbon/datastores/gis_carbon_postgis.json"
```

### Fresh Setup

To set up everything from scratch:

```bash
# Stop and remove all containers and volumes
docker compose -f docker-compose.dev.yml down -v

# Remove GeoServer volume specifically (if needed)
docker volume rm gis-carbon-ai_geoserver_data_dev

# Run the unified setup script
bash ./setup-unified-sso.sh
```

This will:
1. Build and start all containers
2. Initialize databases automatically
3. Create GeoServer workspace and datastore
4. Set up unified authentication
5. Create test users

### Important Notes

- **MapStore** uses the same PostgreSQL server as Django but creates its own tables (GeoStore schema)
- **GeoServer** uses a separate database (`gis_carbon_data`) for spatial data isolation
- **Django** has full control over `gis_carbon` for application data
- All databases are in the same PostgreSQL container for development
- Production deployments should use separate PostgreSQL instances for better performance

### Troubleshooting

#### GeoServer can't connect to database:
```bash
# Check if gis_carbon_data exists
docker exec gis_postgres_dev psql -U gis_user -l

# Test connection from GeoServer container
docker exec gis_geoserver_dev ping -c 2 postgres

# Recreate datastore
./geoserver/create-datastore.sh create-datastore gis_carbon gis_carbon_postgis gis_carbon_data
```

#### MapStore shows H2 database error:
```bash
# Verify the geostore-datasource-ovr-postgres.properties is mounted
docker exec gis_mapstore_dev cat /usr/local/tomcat/conf/geostore-datasource-ovr.properties

# Check MapStore can connect to PostgreSQL
docker exec gis_mapstore_dev ping -c 2 postgres
```

#### Django migrations fail:
```bash
# Ensure gis_carbon database exists and PostGIS is enabled
docker exec gis_postgres_dev psql -U gis_user -d gis_carbon -c "CREATE EXTENSION IF NOT EXISTS postgis;"

# Run migrations
docker exec gis_django_dev python manage.py migrate
```

## Next Steps

1. Create your spatial tables in `gis_carbon_data`
2. Publish them as layers using the `create-datastore.sh` script
3. Configure layer security via unified roles
4. Add layers to MapStore for visualization
5. Access layers via WMS/WFS in your applications

