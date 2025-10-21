# GIS Carbon AI - Complete Docker Architecture

A comprehensive Docker-based platform for carbon analysis using Google Earth Engine (GEE), with Django backend, FastAPI tile service, GeoServer, PostgreSQL, and Jupyter Lab for interactive development and testing.

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   MapStore      │    │   Django        │    │   FastAPI       │
│   (Tomcat)      │◄──►│   Backend       │◄──►│   GEE Service   │
│   (React App)   │    │   (Admin/API)   │    │   (Tiles)       │
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
│   Reverse Proxy │    │   (Tomcat)      │    │   + ArcGIS API  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## ✨ Key Features

- **🌍 Google Earth Engine Integration**: Direct access to GEE datasets and processing
- **🗺️ ArcGIS Python API**: Full integration with ArcGIS services and data
- **📊 Interactive Development**: Jupyter Lab for testing and algorithm development
- **🗄️ Spatial Database**: PostgreSQL with PostGIS for spatial data storage
- **🌐 Web Services**: GeoServer for WMS/WFS services with CORS support
- **⚡ High Performance**: FastAPI for fast GEE tile processing
- **🔧 Admin Interface**: Django admin for project management
- **📱 Modern Frontend**: React-based MapStore interface served via Tomcat
- **🔒 Advanced Security**: GeoFence integration with PostgreSQL
- **🔐 Unified SSO**: JWT-based authentication across all services

## 🚀 Quick Start

### Prerequisites

- **Docker and Docker Compose** installed
- **GEE service account credentials** (`user_id.json`)
- **Minimum 8GB RAM** for optimal performance
- **Ports 3000, 8000, 8001, 8080, 8082, 8888, 5432, 6379** available

### 1. Setup

```bash
# Clone the repository
git clone <your-repo-url>
cd gis-carbon-ai

# Copy GEE credentials (IMPORTANT: Keep this file secure!)
cp /path/to/your/user_id.json ./backend/

# Start all services in development mode
docker-compose -f docker-compose.dev.yml up --build

# Or start specific services
docker-compose -f docker-compose.dev.yml up django fastapi postgres redis jupyter geoserver
```

### 2. Setup Unified SSO (Optional)

```bash
# Run the unified SSO setup script
./setup-unified-sso.sh
```

This will create test users and configure unified authentication across all services.

## 🌐 Service URLs

- **MapStore Frontend** (Tomcat): http://localhost:8082/mapstore
- **Django Admin**: http://localhost:8000/admin/
- **FastAPI Docs**: http://localhost:8001/docs
- **Jupyter Lab**: http://localhost:8888
- **GeoServer** (Tomcat): http://localhost:8080/geoserver/
- **Nginx (Production)**: http://localhost

## 🔑 Default Credentials

- **Django Admin**: admin@admin.com / admin
- **GeoServer**: admin / admin
- **PostgreSQL**: gis_user / gis_password
- **Jupyter Lab**: No authentication required (development mode)

### Test Users (After SSO Setup)

- **demo_user** (password: demo123) - Role: ROLE_AUTHENTICATED
- **analyst** (password: analyst123) - Role: ROLE_ANALYST
- **admin** (password: admin123) - Role: ADMIN

## 🗄️ Current Configuration

### GeoServer Setup
- **Workspaces**: `gis_carbon`, `demo_workspace`
- **Datastore**: `gis_carbon_postgis` (PostgreSQL)
- **Database**: `gis_carbon_data` (PostgreSQL with PostGIS)
- **Extensions**: GeoFence with PostgreSQL integration
- **CORS**: Fully configured with credentials support

### Database Configuration
- **Main Database**: `gis_carbon_data` (PostgreSQL + PostGIS)
- **Django Database**: `gis_carbon` (PostgreSQL)
- **GeoFence Database**: `gis_carbon_data` (shared)

## 📚 Documentation

Comprehensive documentation is organized in the `/docs/` directory:

- **[📁 Architecture](/docs/architecture/)** - System design and architecture
- **[⚙️ Setup](/docs/setup/)** - Installation and configuration guides
- **[🐛 Issues](/docs/issues/)** - Troubleshooting and known issues
- **[📖 Guides](/docs/guides/)** - How-to guides and workflows

### Quick Documentation Links

- **[Quick Start Guide](QUICK_START.md)** - Fast setup instructions
- **[Daily Workflow](docs/guides/daily-workflow.md)** - Development workflow
- **[GeoServer Setup](docs/setup/GEOSERVER_SETUP.md)** - GeoServer configuration
- **[GEE Integration](docs/guides/MAPSTORE_GEE_INTEGRATION_GUIDE.md)** - Google Earth Engine setup
- **[MapStore Integration](docs/guides/MAPSTORE_GEOSERVER_INTEGRATION.md)** - MapStore configuration

## 🔧 Development

### Interactive Development with Jupyter Lab

1. **Access Jupyter Lab**: http://localhost:8888
2. **Test Environment**: Run notebooks in `/jupyter/notebooks/`
3. **GEE Calculations**: Use GEE_notebook_Forestry library
4. **ArcGIS Integration**: Use ArcGIS Python API

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
```

### GeoServer Management

```bash
# Check GeoServer status
curl -u admin:admin http://localhost:8080/geoserver/rest/about/version.json

# List workspaces
curl -u admin:admin http://localhost:8080/geoserver/rest/workspaces

# Check GeoFence status
curl -u admin:admin http://localhost:8080/geoserver/rest/geofence/info
```

## 🔒 Security Features

- **CORS Configuration**: Properly configured for cross-origin requests
- **GeoFence Integration**: Advanced security and access control
- **Unified Authentication**: JWT-based SSO across all services
- **Environment Variables**: Secure configuration management
- **Docker Security**: Containerized services with proper isolation

## 🧪 Testing

```bash
# Test all services
curl http://localhost:8000/health/  # Django
curl http://localhost:8001/health   # FastAPI
curl http://localhost:8080/geoserver/  # GeoServer
curl http://localhost:8888/lab  # Jupyter Lab

# Test CORS
curl -H "Origin: http://localhost:3000" http://localhost:8080/geoserver/rest/about/version.json -u admin:admin

# Test GeoFence
curl -u admin:admin http://localhost:8080/geoserver/rest/geofence/info
```

## 🐛 Troubleshooting

Common issues and solutions are documented in `/docs/issues/`:

- **[CORS Issues](docs/issues/mapstore-cors-issue.md)**
- **[MapStore White Screen](docs/issues/mapstore-white-screen-issue.md)**
- **[Persistence Problems](docs/issues/mapstore-persistence-issue.md)**
- **[Extensions Issues](docs/issues/mapstore-extensions-issue.md)**

### Quick Health Checks

```bash
# Check service status
docker-compose ps

# View logs
docker-compose logs -f geoserver
docker-compose logs -f django
docker-compose logs -f fastapi

# Check GeoServer post-startup configuration
docker exec gis_geoserver_dev tail -20 /var/log/post-startup.log
```

## 📈 Performance

- **Memory**: 8GB+ RAM recommended
- **Storage**: SSD recommended for better I/O performance
- **Network**: Ensure all required ports are available
- **Docker**: Allocate sufficient resources to Docker

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with `docker-compose -f docker-compose.dev.yml up --build`
5. Update documentation if needed
6. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

- **Documentation**: Check `/docs/` directory for detailed guides
- **Issues**: Look in `/docs/issues/` for known problems
- **Logs**: Use `docker-compose logs -f <service>` for debugging
- **Health Checks**: Use the testing commands above to verify services