# Docker Setup and Volume Management

## Overview
This document describes the Docker setup for the GIS Carbon AI project, ensuring that the repository can be replicated from scratch with `git clone` without relying on persistent volumes or manual `docker cp` operations.

## Docker Architecture

### Services
- **PostgreSQL**: Database service
- **Redis**: Cache service
- **GeoServer**: Geospatial data server
- **MapStore**: Web mapping application
- **Django**: Backend API service
- **FastAPI**: GEE tile service
- **Jupyter**: Development notebooks
- **Nginx**: Reverse proxy

### Build Contexts and Dockerfiles

#### FastAPI Service
- **Dockerfile**: `./fastapi-gee-service/Dockerfile`
- **Build Context**: `.` (project root)
- **Reason**: Allows access to `./auth/` directory for unified authentication

#### Django Service
- **Dockerfile**: `./backend/Dockerfile-dev`
- **Build Context**: `./backend`
- **Standard**: Uses local build context

#### Jupyter Service
- **Dockerfile**: `./jupyter/Dockerfile`
- **Build Context**: `./jupyter`
- **Standard**: Uses local build context

## Volume Management

### Named Volumes (Persistent Data)
```yaml
volumes:
  postgres_data_dev:           # Database data
  redis_data_dev:              # Cache data
  django_static_dev:           # Django static files
  django_media_dev:            # Django media files
  geoserver_data_dev:          # GeoServer data directory
  gee_tiles_cache_dev:         # GEE tile cache
  mapstore_data_dev:           # MapStore data
  mapstore_webapps_dev:        # MapStore webapps
  mapstore_logs_dev:           # MapStore logs
  mapstore_temp_dev:           # MapStore temp files
  mapstore_work_dev:           # MapStore work directory
  mapstore_config_dev:         # MapStore configuration
  mapstore_auth_dev:           # MapStore authentication
  mapstore_plugins_dev:        # MapStore plugins
  mapstore_uploads_dev:        # MapStore uploads
  mapstore_custom_dev:         # MapStore custom files
```

### Bind Mounts (Source Code and Configuration)
```yaml
# Django Service
volumes:
  - ./backend/sv_carbon_removal/:/usr/src/app
  - ./backend/user_id.json:/usr/src/app/user_id.json
  - ./auth:/usr/src/app/auth
  - ./GEE_notebook_Forestry:/usr/src/app/gee_lib:ro

# FastAPI Service
volumes:
  - ./backend/user_id.json:/app/user_id.json
  - ./fastapi-gee-service:/app
  - ./auth:/app/auth
  - ./GEE_notebook_Forestry:/app/gee_lib:ro

# Jupyter Service
volumes:
  - ./jupyter/notebooks:/usr/src/app/notebooks
  - ./jupyter/data:/usr/src/app/data
  - ./jupyter/shared:/usr/src/app/shared
  - ./backend/user_id.json:/usr/src/app/user_id.json
  - ./auth:/usr/src/app/auth
  - ./GEE_notebook_Forestry:/usr/src/app/gee_lib:ro
  - ./ex_ante:/usr/src/app/ex_ante_lib:ro
  - ./mapstore/config:/usr/src/app/mapstore/config
```

## Directory Structure in Containers

### FastAPI Container (`/app/`)
```
/app/
├── main.py                    # Main FastAPI application
├── gee_integration.py         # Integration library
├── requirements.txt           # Dependencies
├── user_id.json              # GEE credentials (mounted)
├── auth/                     # Auth files (mounted)
│   ├── unified-auth-service.py
│   └── unified-roles-config.json
├── cache/                    # Cache directory (named volume)
├── test/                     # Test files (created in Dockerfile)
├── docs/                     # Documentation (created in Dockerfile)
├── archive/                  # Archived files (created in Dockerfile)
└── gee_lib/                  # GEE library (mounted, read-only)
```

### Jupyter Container (`/usr/src/app/`)
```
/usr/src/app/
├── notebooks/                # Notebooks (mounted)
│   ├── gee_integration.py    # Integration library
│   ├── wmts_config_updater.py # WMTS configuration
│   ├── gee_catalog_updater.py # Catalog management
│   ├── archieve/             # Archived notebooks
│   ├── data/                 # Data directory
│   └── shared/               # Shared resources
├── data/                     # Analysis data (mounted)
├── shared/                   # Shared files (mounted)
├── test/                     # Test files (created in Dockerfile)
├── docs/                     # Documentation (created in Dockerfile)
├── archive/                  # Archived files (created in Dockerfile)
├── user_id.json             # GEE credentials (mounted)
├── auth/                    # Auth files (mounted)
├── gee_lib/                 # GEE library (mounted, read-only)
├── ex_ante_lib/             # Ex-ante library (mounted, read-only)
└── mapstore/                # MapStore configuration (mounted)
    └── config/
        └── localConfig.json
```

### Django Container (`/usr/src/app/`)
```
/usr/src/app/
├── sv_carbon_removal/        # Django application (mounted)
├── user_id.json             # GEE credentials (mounted)
├── auth/                    # Auth files (mounted)
├── gee_lib/                 # GEE library (mounted, read-only)
├── mapstore/                # MapStore configuration (mounted)
│   └── config/
└── media/                   # Media files (named volume)
```

## Eliminated Manual `docker cp` Operations

### Previously Required Manual Operations
```bash
# These are now handled automatically by Dockerfiles and volumes
docker cp auth/unified-auth-service.py gis_django_dev:/app/auth/
docker cp auth/unified-roles-config.json gis_django_dev:/app/auth/
docker cp auth/unified-auth-service.py gis_fastapi_dev:/app/auth/
docker cp auth/unified-roles-config.json gis_fastapi_dev:/app/auth/
```

### Current Automated Setup
1. **Dockerfiles**: Create necessary directories
2. **Volume Mounts**: Mount auth files dynamically
3. **Build Context**: Include auth files in build context
4. **No Manual Operations**: Everything is automated

## Fresh Installation Process

### 1. Clone Repository
```bash
git clone <repository-url>
cd gis-carbon-ai
```

### 2. Set Up Environment
```bash
# Copy environment template
cp .env.example .env

# Edit environment variables
nano .env
```

### 3. Build and Start Services
```bash
# Build and start all services
docker-compose -f docker-compose.dev.yml up -d --build

# Or start specific services
docker-compose -f docker-compose.dev.yml up -d --build postgres redis
docker-compose -f docker-compose.dev.yml up -d --build django fastapi jupyter
docker-compose -f docker-compose.dev.yml up -d --build geoserver mapstore
```

### 4. Initialize Services
```bash
# Run setup script (optional - for unified SSO)
./setup-unified-sso.sh

# Or run individual setup commands
docker-compose -f docker-compose.dev.yml exec django python manage.py migrate
docker-compose -f docker-compose.dev.yml exec django python manage.py createsuperuser
```

## Directory Creation in Dockerfiles

### FastAPI Dockerfile
```dockerfile
# Create necessary directories
RUN mkdir -p /app/cache /app/test /app/docs /app/archive /app/auth
```

### Jupyter Dockerfile
```dockerfile
# Create directories for notebooks, data, and organizational folders
RUN mkdir -p /app/notebooks /app/data /app/shared /app/test /app/docs /app/archive
```

### Backend Dockerfile-dev
```dockerfile
# Create MapStore config directory for configuration updates
RUN mkdir -p /usr/src/app/mapstore/config /usr/src/app/auth
```

## Volume Persistence

### What Persists (Named Volumes)
- ✅ Database data (PostgreSQL)
- ✅ Cache data (Redis)
- ✅ Static files (Django)
- ✅ Media files (Django)
- ✅ GeoServer data
- ✅ MapStore data and configuration
- ✅ GEE tile cache

### What Persists (Bind Mounts)
- ✅ Source code changes
- ✅ Configuration files
- ✅ Notebook files
- ✅ Analysis data
- ✅ Auth files
- ✅ GEE library
- ✅ MapStore configuration

### What Doesn't Persist
- ❌ Container state (memory, processes)
- ❌ Network connections (recreated)
- ❌ Running processes (restarted)
- ❌ Temporary files (in container filesystem)

## Development Workflow

### Code Changes
1. **Edit files** in host filesystem
2. **Changes are immediately available** in containers (bind mounts)
3. **No rebuild required** for most changes
4. **Restart services** only for configuration changes

### Data Persistence
1. **Database changes** persist across restarts
2. **File uploads** persist in named volumes
3. **Cache data** persists in Redis
4. **Configuration changes** persist in bind mounts

### Testing
1. **Run tests** in containers
2. **Test files** are available in containers
3. **Results persist** in bind mounts
4. **No manual setup** required

## Production Considerations

### Security
- Use proper authentication
- Secure volume mounts
- Validate input parameters
- Implement access controls

### Performance
- Use named volumes for data
- Implement caching strategies
- Monitor disk usage
- Optimize build contexts

### Maintenance
- Regular cleanup of old data
- Monitor volume usage
- Update configurations
- Backup important data

## Troubleshooting

### Common Issues
1. **Build failures**: Check Dockerfile syntax and build context
2. **Volume mount issues**: Verify paths and permissions
3. **Service startup failures**: Check logs and dependencies
4. **File access issues**: Verify volume mounts and permissions

### Debug Commands
```bash
# Check container status
docker ps

# View logs
docker logs <container_name>

# Check volume mounts
docker inspect <container_name>

# Access container shell
docker exec -it <container_name> bash

# Check file permissions
docker exec <container_name> ls -la /path/to/directory
```

## Benefits

### ✅ Fresh Installation Ready
- No manual `docker cp` operations
- All files included in build context
- Automatic directory creation
- Complete automation

### ✅ Development Friendly
- Immediate code changes
- Persistent data
- Easy testing
- Clean workspace

### ✅ Production Ready
- Proper volume management
- Data persistence
- Security considerations
- Performance optimization

### ✅ Maintainable
- Clear structure
- Automated setup
- Easy debugging
- Comprehensive documentation
