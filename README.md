# GIS Carbon AI - Docker Architecture

This project provides a complete Docker-based architecture for serving Google Earth Engine (GEE) data through MapStore, with Django backend, FastAPI tile service, GeoServer, and PostgreSQL.

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
│   Nginx         │    │   PostgreSQL    │    │   Redis         │
│   Reverse Proxy │    │   + PostGIS     │    │   Cache         │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │
         ▼
┌─────────────────┐
│   GeoServer     │
│   (WMS/WFS)     │
└─────────────────┘
```

## Services

- **MapStore Frontend** (Port 3000): React-based map interface
- **Django Backend** (Port 8000): Project management, user authentication, admin interface
- **FastAPI GEE Service** (Port 8001): High-performance GEE tile processing
- **GeoServer** (Port 8080): WMS/WFS services for spatial data
- **PostgreSQL + PostGIS** (Port 5432): Spatial database
- **Redis** (Port 6379): Caching layer
- **Nginx** (Port 80): Reverse proxy and load balancer

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- GEE service account credentials (`user_id.json`)

### 1. Setup

```bash
# Clone the repository
git clone <your-repo-url>
cd gis-carbon-ai

# Copy GEE credentials (IMPORTANT: Keep this file secure!)
cp /path/to/your/user_id.json ./backend/

# Create environment files from examples
cp ./backend/.env.example ./backend/.env
cp ./fastapi-gee-service/.env.example ./fastapi-gee-service/.env

# Edit the .env files with your actual configuration
nano ./backend/.env
nano ./fastapi-gee-service/.env
```

### 2. Security Setup

**IMPORTANT**: The following files contain sensitive information and are automatically ignored by git:

- `backend/user_id.json` - Your GCP service account credentials
- `backend/.env` - Django environment variables
- `fastapi-gee-service/.env` - FastAPI environment variables

**Never commit these files to version control!**

Make sure to:
1. Copy your GCP service account JSON file to `backend/user_id.json`
2. Update the `.env` files with your actual configuration
3. Keep your service account credentials secure

### 3. Development Mode

```bash
# Start all services in development mode
docker-compose -f docker-compose.dev.yml up --build

# Or start specific services
docker-compose -f docker-compose.dev.yml up django fastapi postgres redis
```

### 4. Production Mode

```bash
# Start all services in production mode
docker-compose up --build -d

# Check service status
docker-compose ps
```

## Service URLs

- **MapStore Frontend**: http://localhost:3000
- **Django Admin**: http://localhost:8000/admin/
- **FastAPI Docs**: http://localhost:8001/docs
- **GeoServer**: http://localhost:8080/geoserver/
- **Nginx (Production)**: http://localhost

## API Endpoints

### Django Backend (Port 8000)
- `GET /api/projects/` - List projects
- `POST /api/projects/` - Create project
- `GET /api/projects_sv_conf/` - Satellite verification configs
- `POST /api/run-sv/` - Process GEE analysis

### FastAPI GEE Service (Port 8001)
- `GET /tiles/{project_id}/{z}/{x}/{y}` - Get GEE tile
- `GET /layers/{project_id}` - Get project layers
- `POST /process/{project_id}` - Process project
- `GET /health` - Health check

### GeoServer (Port 8080)
- `GET /geoserver/wms` - WMS services
- `GET /geoserver/wfs` - WFS services
- `GET /geoserver/rest` - REST API

## Development

### Adding New GEE Layers

1. Update the FastAPI service in `fastapi-gee-service/main.py`
2. Add layer configuration in the `generate_gee_tile` function
3. Update the MapStore frontend to display new layers

### Database Management

```bash
# Access PostgreSQL
docker-compose exec postgres psql -U gis_user -d gis_carbon_db

# Run Django migrations
docker-compose exec django python manage.py migrate

# Create superuser
docker-compose exec django python manage.py createsuperuser
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
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with `docker-compose -f docker-compose.dev.yml up --build`
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.