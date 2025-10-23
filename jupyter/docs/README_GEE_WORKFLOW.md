# GEE Analysis Workflow with FastAPI Integration

This directory contains Jupyter notebooks for performing Google Earth Engine (GEE) analysis and integrating the results with the FastAPI service for MapStore visualization.

## Overview

The workflow demonstrates:
1. **Authentication**: Using GCP service account credentials for GEE
2. **Analysis**: Creating cloudless Sentinel-2 composites and derived indices
3. **Integration**: Pushing results to FastAPI service
4. **Visualization**: Making layers available in MapStore catalog

## Notebooks

### `02_gee_calculations.ipynb`
Complete example of GEE analysis workflow including:
- GEE authentication with service account
- Cloudless Sentinel-2 composite creation
- Multiple vegetation indices (NDVI, EVI, NDWI)
- Interactive map visualization
- FastAPI integration
- MapStore catalog configuration

## Getting Started

### Prerequisites

1. **Docker services running**:
   ```bash
   cd /Users/miqbalf/gis-carbon-ai
   docker-compose -f docker-compose.dev.yml up -d
   ```

2. **Access Jupyter Lab**:
   - Open browser: http://localhost:8888
   - Navigate to `notebooks/02_gee_calculations.ipynb`

3. **Required credentials**:
   - GCP service account credentials in `backend/user_id.json`
   - FastAPI service running at `http://fastapi:8000`

### Running the Notebook

1. **Open Jupyter Lab** at http://localhost:8888

2. **Run all cells** in order (or run individual cells):
   - Cell 1: Import libraries
   - Cell 2: Initialize GEE authentication
   - Cell 3: Define Area of Interest (AOI)
   - Cell 4: Create cloudless Sentinel-2 composite
   - Cell 5: Generate analysis products
   - Cell 6: Create GEE Map IDs
   - Cell 7: Visualize on interactive map
   - Cell 8: Prepare data for FastAPI
   - Cell 9: Push to FastAPI service
   - Cell 10: Generate MapStore configuration
   - Cell 11: Test layer access
   - Cell 12: Save configuration to file

3. **Expected outputs**:
   - Interactive Folium map with multiple layers
   - GEE tile URLs for each analysis product
   - MapStore configuration JSON
   - Saved configuration file in `/usr/src/app/data/`

## Architecture

```
┌─────────────┐
│  Jupyter    │
│  Notebook   │
└─────┬───────┘
      │
      │ 1. GEE Authentication
      │    (user_id.json)
      ▼
┌─────────────────┐
│ Google Earth    │
│ Engine API      │
└─────┬───────────┘
      │
      │ 2. Create Analysis
      │    (Sentinel-2 + Indices)
      │
      │ 3. Generate Map IDs
      │
      ▼
┌─────────────┐      ┌─────────────┐
│  FastAPI    │◄────►│   Redis     │
│  Service    │      │   Cache     │
└─────┬───────┘      └─────────────┘
      │
      │ 4. Serve Tiles
      │
      ▼
┌─────────────┐
│  MapStore   │
│  Catalog    │
└─────────────┘
```

## Customization

### Change Area of Interest

Edit cell 3 in the notebook:
```python
aoi_coords = [
    [your_lon_min, your_lat_min],
    [your_lon_max, your_lat_min],
    [your_lon_max, your_lat_max],
    [your_lon_min, your_lat_max],
    [your_lon_min, your_lat_min]
]
```

### Change Date Range

Edit cell 4:
```python
date_start_end = ['YYYY-MM-DD', 'YYYY-MM-DD']
```

### Change Cloud Cover Threshold

Edit cell 4:
```python
cloud_cover_threshold = 30  # Percentage (0-100)
```

### Add More Indices

Add to cell 5:
```python
# Example: SAVI (Soil Adjusted Vegetation Index)
savi = sentinel_composite.expression(
    '((NIR - RED) / (NIR + RED + L)) * (1 + L)', {
        'NIR': sentinel_composite.select('nir'),
        'RED': sentinel_composite.select('red'),
        'L': 0.5
    }
).rename('SAVI')
```

## Output Files

The notebook generates configuration files in `/usr/src/app/data/`:

```
sentinel_analysis_YYYYMMDD_HHMMSS_config.json
```

This file contains:
- Project metadata
- AOI coordinates
- Date ranges
- Layer tile URLs
- MapStore configuration
- Visualization parameters

## Integration with MapStore

### Option 1: Manual Layer Addition

1. Open MapStore: http://localhost:8082/mapstore
2. Create/Open a map
3. Click **Catalog** button
4. Click **Add Service**
5. Select **Tile** service type
6. Paste the tile URL from notebook output
7. Add layer to map

### Option 2: Using Configuration File

The generated JSON configuration can be used to programmatically add layers:

```python
import requests
import json

# Load configuration
with open('config_file.json', 'r') as f:
    config = json.load(f)

# Add to MapStore via API
response = requests.post(
    'http://localhost:8001/mapstore/add-layers',
    json=config['mapstore_config']
)
```

### Option 3: Direct GEE Tile URLs

Use the tile URLs directly in MapStore layer configuration:

```json
{
  "type": "tile",
  "name": "sentinel_ndvi",
  "title": "Sentinel-2 NDVI",
  "url": "<GEE_TILE_URL_FROM_NOTEBOOK>",
  "format": "image/png",
  "transparent": true
}
```

## Troubleshooting

### GEE Authentication Fails

**Problem**: `Error initializing GEE: Could not find credentials`

**Solution**: 
- Ensure `user_id.json` exists in `/usr/src/app/`
- Check that the service account has Earth Engine permissions
- Verify the JSON file format is correct

### FastAPI Connection Error

**Problem**: `Connection refused to http://fastapi:8000`

**Solution**:
- Ensure FastAPI service is running: `docker ps | grep fastapi`
- Check Docker network: `docker network inspect gis_network_dev`
- Restart services: `docker-compose -f docker-compose.dev.yml restart fastapi`

### No Images Found

**Problem**: `Number of images used: 0`

**Solution**:
- Check date range is valid
- Increase cloud cover threshold
- Verify AOI coordinates are correct
- Check if Sentinel-2 data is available for that region/date

### Import Errors

**Problem**: `ModuleNotFoundError: No module named 'osi'`

**Solution**:
- Ensure gee_lib is mounted: Check `docker-compose.dev.yml`
- Verify path in notebook: `/usr/src/app/gee_lib`
- Restart Jupyter container

## Advanced Usage

### Batch Processing Multiple AOIs

```python
aoi_list = [
    {'name': 'Region 1', 'coords': [...]},
    {'name': 'Region 2', 'coords': [...]},
]

for aoi_data in aoi_list:
    aoi = ee.Geometry.Polygon(aoi_data['coords'])
    # Process each AOI...
```

### Export to GeoTIFF

```python
# Export analysis result to Google Drive
task = ee.batch.Export.image.toDrive(
    image=ndvi,
    description='NDVI_Export',
    scale=10,
    region=aoi,
    fileFormat='GeoTIFF'
)
task.start()
```

### Time Series Analysis

```python
# Analyze NDVI over time
dates = ee.List.sequence(0, 11, 1)

def create_monthly_composite(month):
    start = ee.Date(date_start_end[0]).advance(month, 'month')
    end = start.advance(1, 'month')
    
    collection = ee.ImageCollection('COPERNICUS/S2_SR') \
        .filterDate(start, end) \
        .filterBounds(aoi) \
        .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
    
    return collection.median().set('month', month)

monthly_composites = ee.ImageCollection(dates.map(create_monthly_composite))
```

## API Reference

### FastAPI Endpoints Used

- `POST /process-gee-analysis`: Submit analysis results
- `GET /layers/{project_id}`: Get layer information
- `GET /tiles/gee/{layer_name}/{z}/{x}/{y}`: Get tile data

### GEE Library Modules

- `osi.image_collection.main.ImageCollection`: Image collection handling
- `osi.image_collection.cloud_mask`: Cloud masking functions
- `osi.spectral_indices.spectral_analysis`: Spectral index calculations
- `osi.fcd.main_fcd`: Forest Canopy Density analysis

## Best Practices

1. **Start with small AOIs**: Test with small areas before processing large regions
2. **Monitor GEE quotas**: Be aware of GEE API usage limits
3. **Cache results**: Use Redis caching for frequently accessed tiles
4. **Version control**: Save configuration files for reproducibility
5. **Error handling**: Wrap GEE operations in try-except blocks
6. **Optimize date ranges**: Use specific date ranges to reduce computation
7. **Clean up**: Remove old analysis results from cache periodically

## Resources

- [Google Earth Engine Documentation](https://developers.google.com/earth-engine)
- [Sentinel-2 Data](https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S2_SR)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [MapStore Documentation](https://mapstore.readthedocs.io/)

## Support

For issues or questions:
1. Check container logs: `docker logs gis_jupyter_dev`
2. Verify services are running: `docker-compose -f docker-compose.dev.yml ps`
3. Review notebook outputs for error messages
4. Check GEE authentication status in cell 2

## License

This workflow is part of the GIS Carbon AI project.

