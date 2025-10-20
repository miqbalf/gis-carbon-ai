# GIS Carbon AI - Complete Docker Architecture

This project provides a comprehensive Docker-based architecture for carbon analysis using Google Earth Engine (GEE), with Django backend, FastAPI tile service, GeoServer, PostgreSQL, and Jupyter Lab for interactive development and testing.

## Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   MapStore      │    │   Django        │    │   FastAPI       │
│   Frontend      │◄──►│   Backend       │◄──►│   GEE Service   │
│   (React)       │    │   (Admin/API)   │    │   (Tiles)       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Jupyter Lab   │    │   PostgreSQL    │    │   Redis         │
│   (Testing)     │    │   + PostGIS     │    │   Cache         │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Nginx         │    │   GeoServer     │    │   GEE Libraries │
│   Reverse Proxy │    │   (WMS/WFS)     │    │   + ArcGIS API  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Key Features

- **🌍 Google Earth Engine Integration**: Direct access to GEE datasets and processing
- **🗺️ ArcGIS Python API**: Full integration with ArcGIS services and data
- **📊 Interactive Development**: Jupyter Lab for testing and algorithm development
- **🗄️ Spatial Database**: PostgreSQL with PostGIS for spatial data storage
- **🌐 Web Services**: GeoServer for WMS/WFS services
- **⚡ High Performance**: FastAPI for fast GEE tile processing
- **🔧 Admin Interface**: Django admin for project management
- **📱 Modern Frontend**: React-based MapStore interface

## Services

- **MapStore Frontend** (Port 3000): React-based map interface
- **Django Backend** (Port 8000): Project management, user authentication, admin interface
- **FastAPI GEE Service** (Port 8001): High-performance GEE tile processing
- **Jupyter Lab** (Port 8888): Interactive development and testing environment
- **GeoServer** (Port 8080): WMS/WFS services for spatial data
- **PostgreSQL + PostGIS** (Port 5432): Spatial database
- **Redis** (Port 6379): Caching layer
- **Nginx** (Port 80): Reverse proxy and load balancer

## Libraries and APIs

- **GEE_notebook_Forestry**: Carbon calculation algorithms and GEE processing
- **ex_ante**: Additional carbon analysis tools
- **ArcGIS Python API**: Integration with ArcGIS services and data
- **Google Earth Engine API**: Direct access to GEE datasets
- **PostGIS**: Spatial database extensions
- **GeoPandas**: Geospatial data manipulation

## Quick Start

### Prerequisites

- **Docker and Docker Compose** installed
- **GEE service account credentials** (`user_id.json`)
- **GEE_notebook_Forestry library** (mounted as volume)
- **ex_ante library** (mounted as volume)
- **Minimum 8GB RAM** for optimal performance
- **Ports 3000, 8000, 8001, 8080, 8082, 8888, 5432, 6379** available

### 1. Setup

```bash
# Clone the repository
git clone <your-repo-url>
cd gis-carbon-ai

# Copy GEE credentials (IMPORTANT: Keep this file secure!)
cp /path/to/your/user_id.json ./backend/

# Ensure GEE libraries are available
# GEE_notebook_Forestry should be at: /path/to/GEE_notebook_Forestry
# ex_ante should be at: /path/to/ex_ante

# Create environment files from examples (if they exist)
cp ./backend/.env.example ./backend/.env 2>/dev/null || echo "No .env.example found"
cp ./fastapi-gee-service/.env.example ./fastapi-gee-service/.env 2>/dev/null || echo "No .env.example found"

# Edit the .env files with your actual configuration
nano ./backend/.env
nano ./fastapi-gee-service/.env
```

### 2. Library Setup

Ensure your GEE libraries are properly mounted:

```bash
# Update the volume paths in docker-compose.dev.yml and docker-compose.yml
# Replace these paths with your actual library locations:
# - /Users/miqbalf/gis-carbon-ai/GEE_notebook_Forestry:/app/gee_lib:ro
# - /Users/miqbalf/gis-carbon-ai/ex_ante:/app/ex_ante:ro
```

### 3. Security Setup

**IMPORTANT**: The following files contain sensitive information and are automatically ignored by git:

- `backend/user_id.json` - Your GCP service account credentials
- `backend/.env` - Django environment variables
- `fastapi-gee-service/.env` - FastAPI environment variables

**Never commit these files to version control!**

Make sure to:
1. Copy your GCP service account JSON file to `backend/user_id.json`
2. Update the `.env` files with your actual configuration
3. Keep your service account credentials secure

### 4. Development Mode

```bash
# Start all services in development mode
docker-compose -f docker-compose.dev.yml up --build

# Or start specific services
docker-compose -f docker-compose.dev.yml up django fastapi postgres redis jupyter

# Start with Jupyter Lab for testing
docker-compose -f docker-compose.dev.yml up --build jupyter
```

### 5. Production Mode

```bash
# Start all services in production mode
docker-compose up --build -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f
```

### 6. Testing and Development

```bash
# Test database setup
./test-database-setup.sh

# Access Jupyter Lab for interactive development
# Open: http://localhost:8888

# Create GeoServer data stores
./geoserver/create-datastore.sh quick-setup my_project my_datastore
```

## Service URLs

- **MapStore Frontend**: http://localhost:3000
- **Django Admin**: http://localhost:8000/admin/
- **FastAPI Docs**: http://localhost:8001/docs
- **Jupyter Lab**: http://localhost:8888
- **GeoServer**: http://localhost:8080/geoserver/
- **Nginx (Production)**: http://localhost

## Default Credentials

- **Django Admin**: admin@admin.com / admin
- **GeoServer**: admin / admin
- **PostgreSQL**: gis_user / gis_password
- **Jupyter Lab**: No authentication required (development mode)

## API Endpoints

### Django Backend (Port 8000)
- `GET /api/projects/` - List projects
- `POST /api/projects/` - Create project
- `GET /api/projects_sv_conf/` - Satellite verification configs
- `POST /api/run-sv/` - Process GEE analysis

### FastAPI GEE Service (Port 8001)
- `GET /tiles/{project_id}/{z}/{x}/{y}` - Get GEE tile
- `GET /layers/{project_id}` - Get project layers
- `POST /process-gee-analysis` - Process GEE analysis using GEE_notebook_Forestry
- `GET /health` - Health check

### GeoServer (Port 8080)
- `GET /geoserver/wms` - WMS services
- `GET /geoserver/wfs` - WFS services
- `GET /geoserver/rest` - REST API

### Jupyter Lab (Port 8888)
- Interactive Python environment with access to all libraries
- Pre-configured notebooks for testing GEE calculations
- ArcGIS Python API integration
- Direct access to GEE_notebook_Forestry and ex_ante libraries

## Development

### Interactive Development with Jupyter Lab

1. **Access Jupyter Lab**: http://localhost:8888
2. **Test Environment**: Run `01_environment_test.ipynb` to verify all components
3. **GEE Calculations**: Use `02_gee_calculations.py` for testing GEE algorithms
4. **ArcGIS Integration**: Use `03_arcgis_integration.py` for ArcGIS workflows

### Adding New GEE Layers

1. **Test in Jupyter**: Develop and test algorithms in Jupyter Lab
2. **Update FastAPI**: Add new endpoints in `fastapi-gee-service/main.py`
3. **Update Django**: Add new models and views in Django backend
4. **Update Frontend**: Add new layers to MapStore interface

### Database Management

```bash
# Access PostgreSQL
docker-compose exec postgres psql -U gis_user -d gis_carbon_data

# Run Django migrations
docker-compose exec django python manage.py migrate

# Create superuser
docker-compose exec django python manage.py createsuperuser

# Test database setup
./test-database-setup.sh
```

### GeoServer Management

```bash
# Create new data stores
./geoserver/create-datastore.sh quick-setup my_project my_datastore

# List available tables
./geoserver/create-datastore.sh list-tables my_project my_datastore

# Create layers from tables
./geoserver/create-datastore.sh create-layer my_project my_datastore my_table
```

### Logs and Debugging

```bash
# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f django
docker-compose logs -f fastapi
docker-compose logs -f geoserver

# Access service shell
docker-compose exec django bash
docker-compose exec fastapi bash
```

## Configuration

### Environment Variables

Create `.env` files in each service directory:

**Django Backend** (`backend/.env`):
```
DEBUG=1
SECRET_KEY=your-secret-key
DB_ENGINE=django.db.backends.postgresql
DB_DATABASE=gis_carbon_db
DB_USER=gis_user
DB_PASSWORD=gis_password
DB_HOST=postgres
DB_PORT=5432
```

**FastAPI Service** (`fastapi-gee-service/.env`):
```
REDIS_URL=redis://redis:6379/1
POSTGRES_URL=postgresql://gis_user:gis_password@postgres:5432/gis_carbon_db
GEE_SERVICE_ACCOUNT=your-service-account@project.iam.gserviceaccount.com
```

### GeoServer Configuration

GeoServer configuration is stored in `geoserver/config/` and mounted to the container.

## Security Checklist

Before deploying to production, ensure:

- [ ] All `.env` files are properly configured and not committed to git
- [ ] GCP service account credentials (`user_id.json`) are secure
- [ ] Database passwords are strong and unique
- [ ] Django `SECRET_KEY` is changed from default
- [ ] CORS settings are properly configured for production
- [ ] SSL certificates are configured for HTTPS
- [ ] Firewall rules are properly set up
- [ ] Regular security updates are applied
- [ ] Logs are monitored for suspicious activity

## Troubleshooting

### Common Issues

1. **GEE Authentication Error**
   - Ensure `user_id.json` is in the correct location
   - Check service account permissions

2. **Database Connection Error**
   - Wait for PostgreSQL to fully start
   - Check database credentials in `.env` files

3. **Port Conflicts**
   - Stop other services using the same ports
   - Modify port mappings in `docker-compose.yml`

4. **Memory Issues**
   - Increase Docker memory allocation
   - Adjust GeoServer heap size in environment variables

### Health Checks

```bash
# Check service health
curl http://localhost:8000/health/  # Django
curl http://localhost:8001/health   # FastAPI
curl http://localhost:8080/geoserver/  # GeoServer
curl http://localhost:8888/lab  # Jupyter Lab

# Test database connections
./test-database-setup.sh

# Check all services status
docker-compose ps
```

### Jupyter Lab Issues

If Jupyter Lab fails to start:

1. **Network Issues**: Check Docker network connectivity
2. **Memory Issues**: Ensure sufficient RAM (8GB+ recommended)
3. **Library Mounts**: Verify GEE_notebook_Forestry and ex_ante paths
4. **Port Conflicts**: Ensure port 8888 is available

```bash
# Alternative: Run Jupyter in existing container
docker-compose exec django bash
pip install jupyterlab
jupyter lab --ip=0.0.0.0 --port=8888 --allow-root
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with `docker-compose -f docker-compose.dev.yml up --build`
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.