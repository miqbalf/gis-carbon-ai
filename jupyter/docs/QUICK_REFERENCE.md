# Quick Reference: GEE Analysis to MapStore

## 🚀 Quick Start (5 minutes)

### 1. Start Services
```bash
cd /Users/miqbalf/gis-carbon-ai
docker-compose -f docker-compose.dev.yml up -d
```

### 2. Open Jupyter
- URL: http://localhost:8888
- Open: `notebooks/02_gee_calculations.ipynb`
- Click: **Run** → **Run All Cells**

### 3. View Results
- Interactive map displays in notebook
- Tile URLs printed in output
- Configuration saved to `/data/` folder

---

## 📋 Key Code Snippets

### Initialize GEE
```python
import ee
import json

credentials_path = '/usr/src/app/user_id.json'
with open(credentials_path, 'r') as f:
    credentials_data = json.load(f)

service_account = credentials_data['client_email']
credentials = ee.ServiceAccountCredentials(service_account, credentials_path)
ee.Initialize(credentials)
```

### Create Cloudless Sentinel Composite
```python
from osi.image_collection.main import ImageCollection

img_collection = ImageCollection(
    I_satellite='Sentinel',
    region='asia',
    AOI=your_aoi,
    date_start_end=['2023-01-01', '2023-12-31'],
    cloud_cover_threshold=20,
    config={'IsThermal': False}
)

sentinel_composite = img_collection.image_mosaick()
```

### Calculate NDVI
```python
ndvi = sentinel_composite.normalizedDifference(['nir', 'red']).rename('NDVI')

map_id = ndvi.getMapId({
    'min': -0.2,
    'max': 0.8,
    'palette': ['red', 'yellow', 'green', 'darkgreen']
})

tile_url = map_id['tile_fetcher'].url_format
```

### Push to FastAPI
```python
import requests

layers_data = {
    'project_id': 'my_analysis_001',
    'layers': {
        'ndvi': {
            'tile_url': tile_url,
            'name': 'NDVI',
            'description': 'Vegetation health index'
        }
    }
}

response = requests.post(
    'http://fastapi:8000/process-gee-analysis',
    json=layers_data
)
```

---

## 🗺️ Adding to MapStore

### Method 1: Direct Tile URL (Easiest)

1. Copy tile URL from notebook output
2. Open MapStore: http://localhost:8082/mapstore
3. Click **Catalog** → **Add Service**
4. Choose **Tile** service
5. Paste URL: `https://earthengine.googleapis.com/v1/...`
6. Add layer to map

### Method 2: Via FastAPI Proxy

Use FastAPI as a proxy (with caching):
```
http://localhost:8001/tiles/gee/{layer_name}/{z}/{x}/{y}
```

In MapStore:
1. Add Tile service
2. URL: `http://localhost:8001/tiles/gee/ndvi/{z}/{x}/{y}`
3. Add to map

### Method 3: WMS (Future Implementation)

Convert GEE tiles to WMS via GeoServer:
```
http://localhost:8080/geoserver/gis_carbon/wms?
  service=WMS&
  layers=gis_carbon:sentinel_ndvi
```

---

## 🎯 Common Use Cases

### 1. Forest Cover Analysis
```python
# NDVI for vegetation
ndvi = composite.normalizedDifference(['nir', 'red'])

# Threshold for forest
forest_mask = ndvi.gt(0.6)

# Calculate forest area
forest_area = forest_mask.multiply(ee.Image.pixelArea()) \
    .reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=aoi,
        scale=10
    )
```

### 2. Water Detection
```python
# NDWI for water bodies
ndwi = composite.normalizedDifference(['green', 'nir'])

# Threshold for water
water_mask = ndwi.gt(0.3)
```

### 3. Change Detection
```python
# Compare two time periods
composite_before = create_composite('2022-01-01', '2022-12-31')
composite_after = create_composite('2023-01-01', '2023-12-31')

ndvi_before = composite_before.normalizedDifference(['nir', 'red'])
ndvi_after = composite_after.normalizedDifference(['nir', 'red'])

# Calculate change
ndvi_change = ndvi_after.subtract(ndvi_before)

# Detect significant changes
change_mask = ndvi_change.abs().gt(0.2)
```

### 4. Multi-temporal Analysis
```python
# Monthly composites
months = range(1, 13)
monthly_ndvi = []

for month in months:
    start = f'2023-{month:02d}-01'
    end = f'2023-{month:02d}-28'
    
    composite = create_composite(start, end)
    ndvi = composite.normalizedDifference(['nir', 'red'])
    monthly_ndvi.append(ndvi)

# Create time series
ndvi_collection = ee.ImageCollection(monthly_ndvi)
```

---

## 🔧 Troubleshooting

### Issue: "No images found"
**Fix**: Increase cloud cover threshold or expand date range
```python
cloud_cover_threshold = 50  # Instead of 20
date_start_end = ['2023-01-01', '2024-12-31']  # Longer period
```

### Issue: "Authentication failed"
**Fix**: Check credentials file
```bash
docker exec -it gis_jupyter_dev cat /usr/src/app/user_id.json
```

### Issue: "FastAPI connection refused"
**Fix**: Check service is running
```bash
docker ps | grep fastapi
docker logs gis_fastapi_dev
```

### Issue: "Computation timeout"
**Fix**: Reduce AOI size or use coarser scale
```python
# Reduce area
aoi_small = aoi.buffer(-1000)  # Remove 1km border

# Or use coarser resolution
scale = 100  # Instead of 10
```

---

## 📊 Output Files

After running the notebook, you'll have:

```
/usr/src/app/data/
└── sentinel_analysis_20241020_143022_config.json
    ├── project_info
    │   ├── project_id
    │   ├── aoi
    │   ├── date_range
    │   └── layers
    │       ├── true_color (tile_url, map_id, token)
    │       ├── false_color
    │       ├── ndvi
    │       ├── evi
    │       └── ndwi
    └── mapstore_config
        └── layers (ready for MapStore import)
```

---

## 🌐 Service URLs

| Service | URL | Purpose |
|---------|-----|---------|
| Jupyter | http://localhost:8888 | Run notebooks |
| FastAPI | http://localhost:8001 | GEE tile service |
| GeoServer | http://localhost:8080 | WMS/WFS service |
| MapStore | http://localhost:8082/mapstore | Map viewer |
| Redis | localhost:6379 | Caching |
| PostgreSQL | localhost:5432 | Database |

---

## 💡 Pro Tips

1. **Cache Everything**: FastAPI caches tiles in Redis for 1 hour
2. **Use Specific Dates**: Narrow date ranges = faster processing
3. **Start Small**: Test with small AOIs first
4. **Export Important Results**: Use GEE Export API for permanent storage
5. **Monitor Quotas**: Check GEE usage at https://code.earthengine.google.com/
6. **Save Configurations**: Keep JSON files for reproducibility
7. **Layer Groups**: Organize related layers in MapStore
8. **Version Control**: Track analysis parameters in git

---

## 📚 Documentation Links

- **Full Guide**: `README_GEE_WORKFLOW.md`
- **GEE Docs**: https://developers.google.com/earth-engine
- **Sentinel-2**: https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S2_SR
- **FastAPI**: https://fastapi.tiangolo.com/
- **MapStore**: https://mapstore.readthedocs.io/

---

## 🔄 Typical Workflow

```
1. Define AOI → 2. Set Parameters → 3. Run Analysis → 4. Generate Tiles
                                                              ↓
                                   6. View in MapStore ← 5. Push to FastAPI
```

**Time**: ~5-10 minutes for typical analysis

---

## ✅ Checklist

Before running analysis:
- [ ] Docker services running
- [ ] Jupyter accessible at :8888
- [ ] FastAPI accessible at :8001
- [ ] GCP credentials file exists
- [ ] AOI coordinates defined
- [ ] Date range selected
- [ ] Cloud cover threshold set

After running analysis:
- [ ] Interactive map displays
- [ ] Tile URLs generated
- [ ] Configuration file saved
- [ ] Layers accessible in FastAPI
- [ ] MapStore catalog updated

---

## 🆘 Getting Help

1. Check logs:
   ```bash
   docker logs gis_jupyter_dev
   docker logs gis_fastapi_dev
   ```

2. Verify services:
   ```bash
   docker-compose -f docker-compose.dev.yml ps
   ```

3. Test connectivity:
   ```bash
   curl http://localhost:8001/health
   ```

4. Review notebook outputs for detailed error messages

---

**Last Updated**: October 2024
**Version**: 1.0

