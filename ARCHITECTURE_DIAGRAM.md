# System Architecture Diagram

## Complete Integration Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Docker Network (gis_network_dev)                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                    PostgreSQL + PostGIS                          │   │
│  │                    Container: gis_postgres_dev                   │   │
│  │                    Port: 5432                                    │   │
│  ├──────────────────────────────────────────────────────────────────┤   │
│  │  Database: gis_carbon                                            │   │
│  │  ├─ Django tables (people, api, auth, etc.)                     │   │
│  │  └─ MapStore tables (gs_*, created by Hibernate)                │   │
│  ├──────────────────────────────────────────────────────────────────┤   │
│  │  Database: gis_carbon_data                                       │   │
│  │  ├─ Spatial tables (user-created)                                │   │
│  │  ├─ sample_geometries (demo table)                               │   │
│  │  └─ PostGIS extensions                                           │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                           │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐     │
│  │   Django API    │    │   FastAPI GEE   │    │      Redis      │     │
│  │   Port: 8000    │    │   Port: 8001    │    │   Port: 6379    │     │
│  ├─────────────────┤    ├─────────────────┤    ├─────────────────┤     │
│  │ • REST API      │    │ • GEE Tiles     │    │ • Cache         │     │
│  │ • Auth Service  │    │ • Calculations  │    │ • Sessions      │     │
│  │ • User Mgmt     │    │ • JWT Verify    │    └─────────────────┘     │
│  │ • Role Service  │    │ • GIS Data      │                             │
│  └────────┬────────┘    └────────┬────────┘                             │
│           │                      │                                       │
│           │                      │                                       │
│           └──────────┬───────────┘                                       │
│                      │                                                   │
│                      ↓                                                   │
│  ┌───────────────────────────────────────────────────────────────┐     │
│  │                        GeoServer                               │     │
│  │                   Container: gis_geoserver_dev                 │     │
│  │                   Port: 8080                                   │     │
│  ├───────────────────────────────────────────────────────────────┤     │
│  │  Workspace: gis_carbon                                         │     │
│  │  Datastore: gis_carbon_postgis                                 │     │
│  │             └─> PostgreSQL: gis_carbon_data                    │     │
│  │                                                                 │     │
│  │  Security:                                                      │     │
│  │  • REST Role Service                                            │     │
│  │    └─> Django API: /api/auth/geoserver/roles/{username}       │     │
│  │  • Shared Secret: X-Role-Secret                                 │     │
│  └───────────────────────────────────────────────────────────────┘     │
│                                                                           │
│  ┌───────────────────────────────────────────────────────────────┐     │
│  │                         MapStore                               │     │
│  │                   Container: gis_mapstore_dev                  │     │
│  │                   Port: 8082                                   │     │
│  ├───────────────────────────────────────────────────────────────┤     │
│  │  GeoStore Backend:                                             │     │
│  │  └─> PostgreSQL: gis_carbon (separate tables)                 │     │
│  │                                                                 │     │
│  │  Integrations:                                                  │     │
│  │  • GeoServer WMS/WFS layers                                     │     │
│  │  • Django Auth API                                              │     │
│  │  • Unified JWT tokens                                           │     │
│  └───────────────────────────────────────────────────────────────┘     │
│                                                                           │
│  ┌───────────────────────────────────────────────────────────────┐     │
│  │                      Jupyter Lab                               │     │
│  │                   Port: 8888                                   │     │
│  │  • Development & Testing                                       │     │
│  │  • Access to all GEE libraries                                 │     │
│  └───────────────────────────────────────────────────────────────┘     │
│                                                                           │
└─────────────────────────────────────────────────────────────────────────┘
```

## Authentication Flow

```
┌──────────┐                                          ┌──────────┐
│  User    │                                          │ External │
│ Browser  │                                          │   App    │
└────┬─────┘                                          └────┬─────┘
     │                                                      │
     │ 1. Login Request                                     │
     ├────────────────────────────┐                         │
     │                            ↓                         │
     │                    ┌──────────────┐                  │
     │                    │   MapStore   │                  │
     │                    │  or Django   │                  │
     │                    └──────┬───────┘                  │
     │                           │                          │
     │                           │ 2. Validate Credentials  │
     │                           ↓                          │
     │                    ┌──────────────┐                  │
     │                    │  Django API  │                  │
     │                    │  /api/auth/  │                  │
     │                    └──────┬───────┘                  │
     │                           │                          │
     │ 3. Return JWT             │                          │
     │ ←─────────────────────────┤                          │
     │                           │                          │
     │ 4. Access GeoServer       │                          │
     │    with JWT or Basic      │                          │
     ├───────────────────────────┼──────────────────────────┤
     │                           ↓                          │
     │                    ┌──────────────┐                  │
     │                    │  GeoServer   │                  │
     │                    └──────┬───────┘                  │
     │                           │                          │
     │                           │ 5. Fetch user roles      │
     │                           ↓                          │
     │                    ┌──────────────┐                  │
     │                    │  Django API  │                  │
     │                    │  Role Service│                  │
     │                    │  + Secret    │                  │
     │                    └──────────────┘                  │
     │                           │                          │
     │ 6. Return Layer Data      │                          │
     │ ←─────────────────────────┘                          │
     │                                                      │
     │ 7. Access FastAPI with JWT                           │
     ├──────────────────────────────────────────────────────┤
     │                                                      ↓
     │                                              ┌──────────────┐
     │                                              │   FastAPI    │
     │                                              │ Validates JWT│
     │                                              └──────────────┘
     │                                                      │
     │ 8. Return GEE Tiles                                  │
     │ ←────────────────────────────────────────────────────┘
     │
```

## Data Flow - Creating and Viewing a Layer

```
1. Create Spatial Table
   ┌─────────────────┐
   │   Developer     │
   │   (psql/pgAdmin)│
   └────────┬────────┘
            │ CREATE TABLE my_layer...
            ↓
   ┌─────────────────┐
   │   PostgreSQL    │
   │ gis_carbon_data │
   └────────┬────────┘
            │

2. Publish to GeoServer
   ┌─────────────────┐
   │  create-        │
   │  datastore.sh   │
   └────────┬────────┘
            │ REST API
            ↓
   ┌─────────────────┐
   │   GeoServer     │
   │ • Creates layer │
   │ • Sets metadata │
   └────────┬────────┘
            │

3. Add to MapStore
   ┌─────────────────┐
   │  MapStore UI    │
   │ • Catalog       │
   │ • Add WMS       │
   └────────┬────────┘
            │ GetCapabilities
            ↓
   ┌─────────────────┐
   │   GeoServer     │
   │   WMS Endpoint  │
   └────────┬────────┘
            │

4. User Views Map
   ┌─────────────────┐
   │  Web Browser    │
   │ • MapStore UI   │
   │ • Custom App    │
   └────────┬────────┘
            │ GetMap Request
            ↓
   ┌─────────────────┐
   │   GeoServer     │
   │ • Auth Check    │
   │ • Query PostGIS │
   │ • Render Image  │
   └─────────────────┘
```

## Database Tables Overview

### gis_carbon (Django + MapStore)

```
Django Tables:
├── people_person (custom user model)
├── people_group
├── api_* (API models)
├── django_session
└── auth_* (standard Django auth)

MapStore Tables (auto-created):
├── gs_attribute
├── gs_category
├── gs_resource
├── gs_security
├── gs_stored_data
├── gs_user
└── gs_user_attribute
```

### gis_carbon_data (GeoServer)

```
User-Created Tables:
├── sample_geometries (demo)
├── forest_areas (your data)
├── land_parcels (your data)
└── ... (your spatial data)

PostGIS System Tables:
├── spatial_ref_sys
└── geometry_columns
```

## Port Mapping

| Internal Port | External Port | Service | URL |
|--------------|---------------|---------|-----|
| 5432 | 5432 | PostgreSQL | postgresql://localhost:5432 |
| 6379 | 6379 | Redis | redis://localhost:6379 |
| 8000 | 8000 | Django | http://localhost:8000 |
| 8000 | 8001 | FastAPI | http://localhost:8001 |
| 8080 | 8080 | GeoServer | http://localhost:8080/geoserver |
| 8080 | 8082 | MapStore | http://localhost:8082/mapstore |
| 8888 | 8888 | Jupyter | http://localhost:8888 |

## Setup Flow (setup-unified-sso.sh)

```
1. Start Docker Services
   ├─> Build images (if needed)
   ├─> Start containers
   └─> Wait for health checks

2. Initialize Databases (automatic)
   ├─> Create gis_carbon
   ├─> Create gis_carbon_data
   ├─> Enable PostGIS
   └─> Create sample tables

3. Configure Authentication
   ├─> Copy auth services to Django
   ├─> Copy auth services to FastAPI
   └─> Set shared secrets

4. Setup GeoServer
   ├─> Wait for GeoServer ready
   ├─> Inject unified role service
   ├─> Restart GeoServer
   ├─> Create workspace: gis_carbon
   └─> Create datastore: gis_carbon_postgis

5. Create Test Users
   ├─> Django groups (ROLE_AUTHENTICATED, ROLE_ANALYST, ADMIN)
   ├─> Django users (demo, analyst, admin)
   └─> GeoServer users (via REST API)

6. Verify Setup
   ├─> Test authentication
   ├─> Test GeoServer access
   └─> Test layer access
```

## File Structure

```
gis-carbon-ai/
├── docker-compose.dev.yml          # Service orchestration
├── setup-unified-sso.sh            # Automated setup script
│
├── backend/                        # Django application
│   └── sv_carbon_removal/
│       ├── api/auth/              # Authentication endpoints
│       └── geoserver/             # GeoServer integration scripts
│
├── fastapi-gee-service/           # FastAPI GEE service
│   └── auth/                      # Auth middleware
│
├── geoserver/
│   ├── create-datastore.sh        # Datastore management script
│   └── config/security/           # Security configuration
│       └── role/
│           └── unified_rest_role_service/
│               └── config.xml     # REST role service config
│
├── mapstore/
│   ├── geostore-datasource-ovr-postgres.properties  # DB config
│   └── localConfig.json           # MapStore configuration
│
└── postgres/
    └── init/
        └── 01-init-databases.sql  # Database initialization
```

## Security Model

```
┌───────────────────────────────────────────────────┐
│              Unified Role System                   │
├───────────────────────────────────────────────────┤
│                                                    │
│  Django Groups (Source of Truth)                  │
│  ├── ROLE_ANONYMOUS                               │
│  ├── ROLE_AUTHENTICATED                           │
│  ├── ROLE_ANALYST                                 │
│  └── ADMIN                                         │
│       ↓                                            │
│  GeoServer (via REST Role Service)                │
│  ├── Calls: /api/auth/geoserver/roles/{username} │
│  ├── Secret: X-Role-Secret header                 │
│  └── Returns: XML <roles>                         │
│       ↓                                            │
│  MapStore (via Django Auth API)                   │
│  ├── JWT token authentication                     │
│  └── Role-based resource access                   │
│       ↓                                            │
│  FastAPI (via JWT middleware)                     │
│  ├── Validates JWT signature                      │
│  └── Extracts user roles                          │
│                                                    │
└───────────────────────────────────────────────────┘
```

## Next Steps

1. ✅ **System is Running** - All services operational
2. 🗺️ **Create Spatial Data** - Add tables to `gis_carbon_data`
3. 📢 **Publish Layers** - Use `create-datastore.sh`
4. 🎨 **Style Layers** - Configure in GeoServer
5. 🌐 **Add to MapStore** - Create maps and share
6. 🔌 **Integrate Apps** - Use WMS/WFS/REST APIs

For detailed commands, see:
- `QUICK_START.md`
- `DATABASE_INTEGRATION_SUMMARY.md`

