# MapStore Persistence Guide

## Understanding MapStore Data Storage

### Current Setup (WORKING ✅)

MapStore now uses **PostgreSQL for ALL persistent data**:

```
MapStore Data Storage:
├── PostgreSQL (gis_carbon database)
│   ├── gs_user              → User accounts
│   ├── gs_resource          → Maps, contexts, dashboards
│   ├── gs_attribute         → User attributes
│   ├── gs_category          → Resource categories
│   ├── gs_security          → Permissions
│   └── gs_stored_data       → Saved data
│
└── Container filesystem (temporary)
    ├── /webapps/mapstore    → Extracted WAR (recreated on restart)
    └── /data                → Temp files (lost on restart, OK)
```

### Why Volumes Were Disabled

**Problem:** When you mount Docker volumes to `/usr/local/tomcat/webapps/mapstore/data` or `/configs` **before** the WAR file extracts, it prevents Tomcat from extracting the WAR properly, causing 404 errors.

**Solution:** Let the WAR extract naturally on first startup, then all your data persists in PostgreSQL automatically.

## Data Persistence Strategy

### What IS Persistent ✅

All important MapStore data is stored in PostgreSQL and survives:
- ✅ Container restarts (`docker compose restart mapstore`)
- ✅ Container recreation (`docker compose up -d`)
- ✅ System reboots
- ✅ Docker Compose down/up (if you don't use `-v` flag)

**Data persisted in PostgreSQL:**
- User accounts and permissions
- Maps and map configurations
- Dashboards and GeoStories
- Saved contexts
- Layer configurations
- All GeoStore data

### What is NOT Persistent ❌

These are recreated automatically and don't need persistence:
- ❌ Extracted WAR files (automatically re-extracted on restart)
- ❌ Tomcat temporary files
- ❌ Session data (stored in memory, expected to reset)

### Optional: Uploaded Files Persistence

If you upload custom plugins or extensions, you can enable volume mounts **AFTER first run**:

```yaml
volumes:
  - ./mapstore/geostore-datasource-ovr-postgres.properties:/usr/local/tomcat/conf/geostore-datasource-ovr.properties
  # Enable AFTER first successful startup:
  - mapstore_extensions_dev:/usr/local/tomcat/webapps/mapstore/dist/extensions
```

## Testing Persistence

### 1. Create a Map in MapStore

```bash
# Open MapStore
http://localhost:8082/mapstore

# Login or create an account
# Create a new map
# Save it
```

### 2. Restart Container

```bash
# Restart MapStore
docker compose -f docker-compose.dev.yml restart mapstore

# Wait 30 seconds for it to come back up
sleep 30

# Your map should still be there!
http://localhost:8082/mapstore
```

### 3. Full Recreation Test

```bash
# Stop and remove container (but keep PostgreSQL data!)
docker compose -f docker-compose.dev.yml stop mapstore
docker compose -f docker-compose.dev.yml rm -f mapstore

# Start again
docker compose -f docker-compose.dev.yml up -d mapstore

# Wait for WAR extraction
sleep 45

# Your data is still there!
http://localhost:8082/mapstore
```

## Checking MapStore Tables in PostgreSQL

```bash
# List MapStore tables
docker exec gis_postgres_dev psql -U gis_user -d gis_carbon -c "\dt" | grep gs_

# Check user accounts
docker exec gis_postgres_dev psql -U gis_user -d gis_carbon -c "SELECT * FROM gs_user;"

# Check saved maps
docker exec gis_postgres_dev psql -U gis_user -d gis_carbon -c "SELECT name, description FROM gs_resource WHERE category_id IN (SELECT id FROM gs_category WHERE name='MAP');"
```

**Note:** Tables are created automatically when you first use MapStore (create user, save map, etc.)

## GeoServer Roles Question

### When Were Roles Created?

You asked: "I can see that now roles is created in geoserver, when did this happen?"

**Answer:** The roles were created during `bash ./setup-unified-sso.sh` by the Python script `geoserver/setup-unified-roles.py`.

Even though the REST Role Service extension isn't installed, the script successfully created:

**Roles:**
- `ADMIN`
- `GROUP_ADMIN`
- `ROLE_ANALYST`
- `ROLE_ANONYMOUS`
- `ROLE_AUTHENTICATED`

**Users:**
- `admin` (password: admin123 or admin)
- `analyst` (password: analyst123)
- `demo_user` (password: demo123)

These were created via GeoServer's REST API which works independently of the REST Role Service.

### Verify Roles

```bash
# List all roles
curl -s -u admin:admin "http://localhost:8080/geoserver/rest/security/roles.xml"

# List all users
curl -s -u admin:admin "http://localhost:8080/geoserver/rest/security/usergroup/users.xml"

# Check specific user's roles
curl -s -u admin:admin "http://localhost:8080/geoserver/rest/security/roles/user/demo_user.xml"
```

## Complete Reset (If Needed)

If you ever need to completely reset everything:

```bash
# WARNING: This deletes ALL data including PostgreSQL!

# Stop all containers
docker compose -f docker-compose.dev.yml down -v

# This removes:
# - All containers
# - All volumes (PostgreSQL data, GeoServer data, etc.)
# - All networks

# Start fresh
bash ./setup-unified-sso.sh
```

## Backup Strategy

### Backup PostgreSQL Data

```bash
# Backup all MapStore data
docker exec gis_postgres_dev pg_dump -U gis_user gis_carbon > mapstore_backup_$(date +%Y%m%d).sql

# Restore if needed
cat mapstore_backup_20241020.sql | docker exec -i gis_postgres_dev psql -U gis_user gis_carbon
```

### Backup GeoServer Config

```bash
# Backup GeoServer data directory
docker cp gis_geoserver_dev:/opt/geoserver/data_dir ./geoserver_backup_$(date +%Y%m%d)

# Restore if needed
docker cp ./geoserver_backup_20241020 gis_geoserver_dev:/opt/geoserver/data_dir
docker compose -f docker-compose.dev.yml restart geoserver
```

## Best Practices

1. **Don't use `-v` flag** when doing `docker compose down` unless you want to delete data:
   ```bash
   # GOOD: Keeps data
   docker compose -f docker-compose.dev.yml down
   
   # BAD: Deletes ALL data
   docker compose -f docker-compose.dev.yml down -v
   ```

2. **Regular backups** for production:
   ```bash
   # Daily backup
   docker exec gis_postgres_dev pg_dump -U gis_user gis_carbon > backup_$(date +%Y%m%d).sql
   ```

3. **Test restores** periodically to ensure backups work

4. **Monitor PostgreSQL** for disk space:
   ```bash
   docker exec gis_postgres_dev df -h /var/lib/postgresql/data
   ```

## Troubleshooting

### MapStore shows 404 after restart

**Cause:** WAR file hasn't extracted yet

**Solution:** Wait longer (up to 60 seconds) or check logs:
```bash
docker logs -f gis_mapstore_dev
# Look for: "Deployment of web application directory /usr/local/tomcat/webapps/mapstore has finished"
```

### MapStore tables not appearing

**Cause:** Tables are created on first use

**Solution:** Just use MapStore (create user, save map) and tables will appear automatically

### Lost data after restart

**Cause:** Used `docker compose down -v` which deletes volumes

**Solution:** 
- Restore from backup
- Or: Use `docker compose down` without `-v` flag

### WAR won't extract

**Cause:** Volume mounts blocking extraction

**Solution:** Remove volume mounts from docker-compose.dev.yml (already done)

## Summary

✅ **MapStore persistence IS working correctly!**

- All data stored in PostgreSQL
- Survives container restarts
- No volume mounts needed for data persistence
- WAR extracts properly on each startup
- GeoServer roles created via setup script

Your data is safe and will persist across restarts. The PostgreSQL database is your single source of truth for all MapStore data.

