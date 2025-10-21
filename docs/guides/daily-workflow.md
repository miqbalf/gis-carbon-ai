# Daily Workflow Guide

## Quick Answer

**Run `setup-unified-sso.sh` ONLY ONCE** (first time setup or after complete reset).

For daily work, just use standard Docker Compose commands.

---

## 📅 Your Daily Workflow

### Morning / Starting Work

```bash
# Option 1: If Docker Desktop is running (containers auto-start)
# Just open your browser - services are already running!
http://localhost:8080/geoserver
http://localhost:8082/mapstore
http://localhost:8000/api/

# Option 2: If containers stopped
docker compose -f docker-compose.dev.yml up -d

# Wait ~10 seconds for services to be ready
# That's it! All your data is already there.
```

### During Development

```bash
# View logs
docker compose -f docker-compose.dev.yml logs -f django

# Restart a specific service after code changes
docker compose -f docker-compose.dev.yml restart django

# Run Django migrations
docker exec gis_django_dev python manage.py migrate

# Access Django shell
docker exec -it gis_django_dev python manage.py shell

# Access PostgreSQL
docker exec -it gis_postgres_dev psql -U gis_user -d gis_carbon
```

### End of Day / Stopping Work

```bash
# Option 1: Keep containers running (recommended)
# Just close your IDE and browser - services keep running in background

# Option 2: Stop containers (saves RAM)
docker compose -f docker-compose.dev.yml stop

# Option 3: Stop and remove containers (still keeps data!)
docker compose -f docker-compose.dev.yml down
# Note: Without -v flag, all data is preserved
```

### Next Day

```bash
# Just start them again
docker compose -f docker-compose.dev.yml up -d

# All your data is still there:
# ✅ GeoServer workspace and layers
# ✅ MapStore maps and users  
# ✅ Django users and data
# ✅ PostgreSQL databases intact
```

---

## 🔄 When Data Persists (No Setup Needed)

### These Operations Keep Your Data:

| Command | Effect | Data Preserved? |
|---------|--------|----------------|
| `docker compose restart` | Restart services | ✅ Yes |
| `docker compose stop` then `up -d` | Stop/start | ✅ Yes |
| `docker compose down` (no -v) | Remove containers | ✅ Yes |
| System reboot | Computer restart | ✅ Yes |
| Code changes + restart | Update code | ✅ Yes |

**Why?** Because data is stored in:
- PostgreSQL volumes (`postgres_data_dev`)
- GeoServer volume (`geoserver_data_dev`)  
- Redis volume (`redis_data_dev`)

These volumes persist even when containers are removed!

---

## 🗑️ When You Need setup-unified-sso.sh Again

### Scenario 1: Complete Reset (Start Fresh)

```bash
# Delete EVERYTHING including volumes
docker compose -f docker-compose.dev.yml down -v

# Now you need to recreate everything
bash ./setup-unified-sso.sh
```

**When to do this:**
- Major problems with database
- Want to start completely fresh
- Testing the initial setup process

### Scenario 2: First Time on New Machine

```bash
# Clone the repo
git clone <your-repo>
cd gis-carbon-ai

# Run the setup script ONCE
bash ./setup-unified-sso.sh

# After this, use normal docker compose commands
```

### Scenario 3: After Pulling Major Changes

```bash
# If docker-compose.dev.yml changed significantly
docker compose -f docker-compose.dev.yml down -v
bash ./setup-unified-sso.sh

# Otherwise, just rebuild:
docker compose -f docker-compose.dev.yml up -d --build
```

---

## 🔍 How to Check If Setup is Needed

```bash
# Check if volumes exist
docker volume ls | grep gis-carbon-ai

# If you see these, data exists (no setup needed):
# gis-carbon-ai_postgres_data_dev
# gis-carbon-ai_geoserver_data_dev
# gis-carbon-ai_redis_data_dev

# Check if services are configured
curl -s http://localhost:8080/geoserver/rest/workspaces.json -u admin:admin | grep gis_carbon

# If "gis_carbon" appears, workspace exists (no setup needed)
```

---

## 💡 Common Scenarios

### Scenario: "I want to work on my project"

```bash
# Just start Docker (if not running)
docker compose -f docker-compose.dev.yml up -d

# Open your browser
http://localhost:8080/geoserver  # admin/admin
http://localhost:8082/mapstore
http://localhost:8000/admin

# Start coding!
```

**No setup script needed!** ✅

### Scenario: "I updated Django models"

```bash
# Make migrations
docker exec gis_django_dev python manage.py makemigrations

# Apply migrations
docker exec gis_django_dev python manage.py migrate

# Restart Django
docker compose -f docker-compose.dev.yml restart django
```

**No setup script needed!** ✅

### Scenario: "I want to add a new GeoServer layer"

```bash
# Option 1: Use the script
./geoserver/create-datastore.sh create-layer \
  gis_carbon gis_carbon_postgis my_table "My Layer"

# Option 2: Use GeoServer UI
# http://localhost:8080/geoserver → Layers → Add new layer
```

**No setup script needed!** ✅

### Scenario: "GeoServer is acting weird"

```bash
# Try restarting first
docker compose -f docker-compose.dev.yml restart geoserver

# Still broken? Check logs
docker logs gis_geoserver_dev

# Last resort: Complete reset
docker compose -f docker-compose.dev.yml down -v
bash ./setup-unified-sso.sh
```

**Setup script only needed for complete reset!** ⚠️

### Scenario: "MapStore lost my maps"

```bash
# This shouldn't happen! Check PostgreSQL
docker exec gis_postgres_dev psql -U gis_user -d gis_carbon -c "SELECT * FROM gs_resource;"

# If data is there, just restart MapStore
docker compose -f docker-compose.dev.yml restart mapstore

# Wait 45 seconds for WAR extraction
sleep 45
```

**No setup script needed!** ✅

---

## 📊 What setup-unified-sso.sh Actually Does

```bash
# Step 1: Start all services (docker compose up -d)
# Step 2: Create GeoServer workspace "gis_carbon"
# Step 3: Create GeoServer datastore "gis_carbon_postgis"  
# Step 4: Create GeoServer roles and users
# Step 5: Create Django user groups and test users
# Step 6: Restart services
# Step 7: Test everything works
```

**All of this happens ONCE and data persists in volumes!**

---

## 🎯 TL;DR

```bash
# ONCE (first time):
bash ./setup-unified-sso.sh

# EVERY DAY (normal work):
docker compose -f docker-compose.dev.yml up -d

# END OF DAY (optional):
docker compose -f docker-compose.dev.yml down

# ONLY RESET WHEN BROKEN:
docker compose -f docker-compose.dev.yml down -v
bash ./setup-unified-sso.sh
```

---

## 🚨 Warning Signs You're Running It Too Much

If you see these messages frequently, you're running the script unnecessarily:

```
(info) Workspace may already exist
(info) Datastore may already exist  
User already exists: demo@example.com
Exists group: ROLE_AUTHENTICATED
```

**These are normal the first time, but if you see them every day, you're running setup-unified-sso.sh when you don't need to!**

---

## ✅ Best Practices

1. **Run setup once** when you first set up the project
2. **Use docker compose** commands for daily start/stop
3. **Keep containers running** for best development experience
4. **Only reset** when you have serious problems
5. **Back up PostgreSQL** before major changes

```bash
# Backup before major changes
docker exec gis_postgres_dev pg_dump -U gis_user gis_carbon > backup_$(date +%Y%m%d).sql
docker exec gis_postgres_dev pg_dump -U gis_user gis_carbon_data >> backup_$(date +%Y%m%d).sql
```

---

## 🎓 Remember

**The whole point of Docker volumes and PostgreSQL persistence is that you DON'T need to run setup scripts every time!**

Your data lives in:
- 📦 Docker volumes (survive container removal)
- 🗄️ PostgreSQL database (persistent storage)  
- 💾 GeoServer data directory (volume-mounted)

Only run `setup-unified-sso.sh` when volumes are deleted or on first setup!

