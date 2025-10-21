# Quick Start Guide - GIS Carbon AI

## 🚀 First Time Setup (Run Once)

```bash
bash ./setup-unified-sso.sh
```

This single command will:
- ✅ Start all Docker containers
- ✅ Create databases (`gis_carbon` + `gis_carbon_data`)
- ✅ Set up GeoServer workspace & datastore
- ✅ Configure unified authentication
- ✅ Create test users

**Important:** Run this **ONLY ONCE** or after `docker compose down -v`. All data persists automatically!

## 📅 Daily Usage (After First Setup)

```bash
# Start services
docker compose -f docker-compose.dev.yml up -d

# Stop services (optional, keeps data)
docker compose -f docker-compose.dev.yml down
```

**No need to run setup script again!** See `DAILY_WORKFLOW.md` for details.

## 📊 Database Layout

```
┌─────────────────────────────────────────────┐
│         PostgreSQL (postgres:5432)          │
├─────────────────────────────────────────────┤
│  gis_carbon          │  gis_carbon_data     │
│  (Django + MapStore) │  (GeoServer)         │
│  ├─ Django tables    │  ├─ Spatial layers   │
│  └─ MapStore tables  │  └─ Feature types    │
└─────────────────────────────────────────────┘
```

## 🌐 Access Points

| Service | URL | Credentials |
|---------|-----|-------------|
| **GeoServer** | http://localhost:8080/geoserver | admin / admin |
| **MapStore** | http://localhost:8082/mapstore | (login with test users) |
| **Django API** | http://localhost:8000/api/ | demo@example.com / demo123 |
| **FastAPI** | http://localhost:8001/ | - |
| **Jupyter** | http://localhost:8888/ | (no password) |

## 👥 Test Users

| Email | Password | Roles |
|-------|----------|-------|
| demo@example.com | demo123 | ROLE_AUTHENTICATED |
| analyst@example.com | analyst123 | ROLE_AUTHENTICATED, ROLE_ANALYST |
| admin@example.com | admin123 | ADMIN |

## 🗺️ Create a GeoServer Layer

```bash
# 1. Create a table in gis_carbon_data (example via psql)
docker exec -it gis_postgres_dev psql -U gis_user -d gis_carbon_data

# 2. In psql, create a spatial table:
CREATE TABLE my_points (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255),
    geom GEOMETRY(POINT, 4326)
);

# 3. Insert some data
INSERT INTO my_points (name, geom) VALUES
    ('Location A', ST_GeomFromText('POINT(106.8 -6.2)', 4326)),
    ('Location B', ST_GeomFromText('POINT(106.9 -6.3)', 4326));

# 4. Exit psql and create the layer
\q

# 5. Publish as GeoServer layer
./geoserver/create-datastore.sh create-layer gis_carbon gis_carbon_postgis my_points "My Points Layer"
```

## 🔄 Restart Everything

```bash
# Stop all services
docker compose -f docker-compose.dev.yml down

# Start fresh (keeps data)
docker compose -f docker-compose.dev.yml up -d

# Complete reset (deletes all data)
docker compose -f docker-compose.dev.yml down -v
bash ./setup-unified-sso.sh
```

## 🛠️ Useful Commands

```bash
# View logs
docker logs gis_geoserver_dev
docker logs gis_mapstore_dev
docker logs gis_django_dev

# Access database
docker exec -it gis_postgres_dev psql -U gis_user -d gis_carbon_data

# List GeoServer layers
curl -s -u admin:admin "http://localhost:8080/geoserver/rest/layers.json" | python3 -m json.tool

# Check service status
docker compose -f docker-compose.dev.yml ps
```

## 📚 Documentation

- **Database Integration**: `DATABASE_INTEGRATION_SUMMARY.md`
- **Unified Auth**: `UNIFIED_AUTH_IMPLEMENTATION.md`
- **GeoServer Setup**: `GEOSERVER_SETUP.md`
- **MapStore Config**: `MAPSTORE_CENTRALIZED_AUTH.md`

## 🐛 Troubleshooting

### GeoServer returns 404
```bash
# Check if container is running
docker ps | grep geoserver

# View startup logs
docker logs --tail=100 gis_geoserver_dev

# Restart GeoServer
docker compose -f docker-compose.dev.yml restart geoserver
```

### MapStore returns 404
```bash
# MapStore might still be extracting war file
docker logs gis_mapstore_dev

# Wait 30 seconds and try again
sleep 30 && curl http://localhost:8082/mapstore/
```

### Database connection errors
```bash
# Check if PostgreSQL is running
docker ps | grep postgres

# Test connection
docker exec gis_postgres_dev psql -U gis_user -l

# Restart PostgreSQL
docker compose -f docker-compose.dev.yml restart postgres
```

## 🎯 Next Steps

1. ✅ Verify all services are running
2. ✅ Login to GeoServer and MapStore
3. ✅ Create your spatial tables in `gis_carbon_data`
4. ✅ Publish layers via create-datastore.sh
5. ✅ Add layers to MapStore
6. ✅ Integrate with your Django/FastAPI app

---

**Need help?** Check the detailed documentation files or run:
```bash
./geoserver/create-datastore.sh
```

