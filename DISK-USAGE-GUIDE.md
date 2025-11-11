# New Disk Usage Guide

## Overview

A new 200GB disk has been mounted to `/mnt/docker-data` on the host VM and is available to all containers at `/mnt/data`.

## Disk Information

- **Host Mount Point**: `/mnt/docker-data`
- **Container Mount Point**: `/mnt/data`
- **Size**: 200 GB
- **Filesystem**: ext4

## Container-Specific Directories

Each container has its own dedicated directory on the new disk:

| Container | Host Path | Container Path | Purpose |
|-----------|-----------|----------------|---------|
| **PostgreSQL** | `/mnt/docker-data/postgres` | `/mnt/data` | Large database exports, backups |
| **Redis** | `/mnt/docker-data/redis` | `/mnt/data` | Persistent cache, snapshots |
| **Django** | `/mnt/docker-data/django` | `/mnt/data` | User uploads, large files |
| **FastAPI** | `/mnt/docker-data/fastapi` | `/mnt/data` | GEE tiles cache, large responses |
| **GeoServer** | `/mnt/docker-data/geoserver` | `/mnt/data` | GeoWebCache tiles, raster data |
| **MapStore** | `/mnt/docker-data/mapstore` | `/mnt/data` | User maps, large contexts |
| **Jupyter** | `/mnt/docker-data/jupyter` | `/mnt/data` | Large datasets, processing outputs |

## Usage Examples

### 1. In Jupyter Notebooks

Save large datasets to the new disk:

```python
import pandas as pd
import geopandas as gpd

# Save processed data to the large disk
output_path = "/mnt/data/datasets/my_large_dataset.parquet"
df.to_parquet(output_path)

# Load data from the large disk
gdf = gpd.read_file("/mnt/data/datasets/shapes.geojson")
```

### 2. In Django (Python)

```python
from django.conf import settings
import os

# Define path for large file storage
LARGE_DATA_PATH = "/mnt/data"

# Save uploaded file to large disk
def save_large_file(uploaded_file):
    file_path = os.path.join(LARGE_DATA_PATH, uploaded_file.name)
    with open(file_path, 'wb+') as destination:
        for chunk in uploaded_file.chunks():
            destination.write(chunk)
    return file_path
```

### 3. In FastAPI (GEE Tile Caching)

```python
import os
from pathlib import Path

# Cache GEE tiles on the large disk
TILE_CACHE_DIR = Path("/mnt/data/tiles")
TILE_CACHE_DIR.mkdir(parents=True, exist_ok=True)

def cache_tile(tile_id: str, tile_data: bytes):
    cache_path = TILE_CACHE_DIR / f"{tile_id}.png"
    with open(cache_path, 'wb') as f:
        f.write(tile_data)
```

### 4. GeoServer Configuration

The GeoWebCache directory is already configured to use the new disk:

```
GEOWEBCACHE_CACHE_DIR=/mnt/data/gwc
```

Store large GeoTIFF files:
- Upload via GeoServer UI
- Or place files directly in: `/mnt/docker-data/geoserver/` (from host)
- Access in container at: `/mnt/data/`

### 5. PostgreSQL Backups

```bash
# From inside the postgres container
pg_dump -U gis_user gis_carbon > /mnt/data/backup_$(date +%Y%m%d).sql

# From host
docker exec gis_postgres_dev pg_dump -U gis_user gis_carbon > /mnt/docker-data/postgres/backup_$(date +%Y%m%d).sql
```

## Monitoring Disk Usage

### From Host

```bash
# Check overall disk usage
df -h /mnt/docker-data

# Check usage per container
du -sh /mnt/docker-data/*
```

### From Container

```bash
# From inside any container
df -h /mnt/data
du -sh /mnt/data
```

## Best Practices

1. **Use for Large Files Only**: Keep application code and small files in Docker volumes
2. **Regular Cleanup**: Implement cleanup routines for old cache files and temporary data
3. **Monitor Space**: Set up alerts when disk usage exceeds 80%
4. **Backup Important Data**: The disk is not automatically backed up
5. **Organize by Purpose**: Create subdirectories for different data types

## Directory Structure Recommendations

```
/mnt/data/
├── datasets/          # Raw and processed datasets
├── cache/             # Temporary cache files
├── tiles/             # Map tiles
├── uploads/           # User uploads
├── exports/           # Data exports
├── backups/           # Database/file backups
└── temp/              # Temporary processing files
```

## Troubleshooting

### Disk Not Visible in Container

1. Check if disk is mounted on host:
   ```bash
   df -h | grep docker-data
   ```

2. Verify docker-compose.dev.yml has the volume mount:
   ```yaml
   volumes:
     - /mnt/docker-data/[service]:/mnt/data
   ```

3. Restart the container:
   ```bash
   docker-compose -f docker-compose.dev.yml restart [service_name]
   ```

### Permission Denied Errors

```bash
# From host, fix permissions
sudo chown -R 999:999 /mnt/docker-data/postgres  # PostgreSQL uses UID 999
sudo chown -R 1000:1000 /mnt/docker-data/django  # Django user
sudo chmod -R 755 /mnt/docker-data
```

### Disk Full

```bash
# Find largest directories
du -sh /mnt/docker-data/*/* | sort -h

# Clean up cache files (example)
find /mnt/docker-data/fastapi/cache -type f -mtime +7 -delete
find /mnt/docker-data/geoserver/gwc -type f -mtime +30 -delete
```

## Migration from Old Storage (Optional)

If you have existing data to migrate:

```bash
# Stop containers
docker-compose -f docker-compose.dev.yml down

# Copy data to new disk (example for PostgreSQL)
sudo rsync -av /var/lib/docker/volumes/postgres_data/_data/ /mnt/docker-data/postgres/old_data/

# Restart containers
docker-compose -f docker-compose.dev.yml up -d
```

## Setup Instructions

To set up the disk for the first time, run:

```bash
./setup-disk.sh
```

This script will:
1. Format the disk
2. Mount it to `/mnt/docker-data`
3. Configure auto-mount
4. Create directory structure
5. Set appropriate permissions

