# GEE Analysis Notebooks - Index

Welcome to the GEE Analysis notebooks directory! This index will help you navigate all available resources.

## 📚 Documentation

| File | Description | When to Use |
|------|-------------|-------------|
| **INDEX.md** | This file - Overview of all resources | Start here |
| **README_GEE_WORKFLOW.md** | Complete documentation and guide | In-depth learning |
| **QUICK_REFERENCE.md** | Quick commands and snippets | Quick lookups |

## 📓 Notebooks

| Notebook | Description | Difficulty | Estimated Time |
|----------|-------------|------------|----------------|
| **02_gee_calculations.ipynb** | Complete GEE to MapStore workflow | Beginner | 10-15 min |

### What's in `02_gee_calculations.ipynb`:
- ✅ GEE authentication with service account
- ✅ Cloudless Sentinel-2 composite creation
- ✅ Multiple vegetation indices (NDVI, EVI, NDWI)
- ✅ Interactive Folium map visualization
- ✅ FastAPI integration
- ✅ MapStore catalog configuration
- ✅ Configuration export

## 🐍 Python Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| **test_gee_integration.py** | Test the entire integration | `python test_gee_integration.py` |
| **example_api_usage.py** | Programmatic API examples | Run directly or import functions |

### Test Script Features:
- Tests GEE authentication
- Tests library imports
- Tests GEE computations
- Tests FastAPI connection
- Tests complete workflow
- Provides detailed error messages

### Example Script Features:
- Example 1: Simple NDVI layer
- Example 2: Seasonal analysis
- Example 3: Multiple vegetation indices
- Reusable functions for custom workflows

## 🚀 Quick Start

### First Time Setup (5 minutes)

1. **Start Docker services**:
   ```bash
   cd /Users/miqbalf/gis-carbon-ai
   docker-compose -f docker-compose.dev.yml up -d
   ```

2. **Verify setup**:
   ```bash
   docker exec -it gis_jupyter_dev python /usr/src/app/notebooks/test_gee_integration.py
   ```

3. **Open Jupyter**:
   - Navigate to: http://localhost:8888
   - Open: `02_gee_calculations.ipynb`
   - Run all cells

### Running the Notebook

**Option 1: Interactive (Recommended)**
- Open Jupyter Lab: http://localhost:8888
- Open `02_gee_calculations.ipynb`
- Run cells one by one to understand each step

**Option 2: Run All**
- Open notebook
- Click: **Run** → **Run All Cells**
- Wait for completion (~5-10 minutes)

**Option 3: From Terminal**
```bash
docker exec -it gis_jupyter_dev \
  jupyter nbconvert --to notebook --execute \
  /usr/src/app/notebooks/02_gee_calculations.ipynb
```

### Testing the Integration

```bash
# Inside Jupyter container
docker exec -it gis_jupyter_dev bash
cd /usr/src/app/notebooks
python test_gee_integration.py
```

## 📖 Learning Path

### Beginner Path
1. Read **QUICK_REFERENCE.md** (5 min)
2. Run **test_gee_integration.py** (2 min)
3. Run **02_gee_calculations.ipynb** (15 min)
4. Try modifying the AOI or date range (5 min)

### Advanced Path
1. Read **README_GEE_WORKFLOW.md** (15 min)
2. Study **02_gee_calculations.ipynb** (20 min)
3. Use **example_api_usage.py** as template (30 min)
4. Create custom analysis workflows (variable)

## 🎯 Common Tasks

### Change Area of Interest
```python
# In notebook cell 3
aoi_coords = [
    [your_lon_min, your_lat_min],
    [your_lon_max, your_lat_min],
    [your_lon_max, your_lat_max],
    [your_lon_min, your_lat_max],
    [your_lon_min, your_lat_min]
]
```

### Change Date Range
```python
# In notebook cell 4
date_start_end = ['2023-01-01', '2023-12-31']
```

### Add New Index
```python
# Add to notebook cell 5
# Example: SAVI
savi = sentinel_composite.expression(
    '((NIR - RED) / (NIR + RED + 0.5)) * 1.5', {
        'NIR': sentinel_composite.select('nir'),
        'RED': sentinel_composite.select('red')
    }
).rename('SAVI')
```

### Export Configuration
```python
# Already included in notebook cell 13
# Output: /usr/src/app/data/{project_id}_config.json
```

## 🔧 Troubleshooting

### Common Issues

**Issue**: Can't access Jupyter
```bash
# Check if service is running
docker ps | grep jupyter

# Restart if needed
docker-compose -f docker-compose.dev.yml restart jupyter
```

**Issue**: GEE authentication fails
```bash
# Verify credentials file
docker exec -it gis_jupyter_dev cat /usr/src/app/user_id.json

# Check if it's valid JSON
docker exec -it gis_jupyter_dev python -c "import json; json.load(open('/usr/src/app/user_id.json'))"
```

**Issue**: FastAPI connection refused
```bash
# Check FastAPI service
docker logs gis_fastapi_dev

# Test connection
docker exec -it gis_jupyter_dev curl http://fastapi:8000/health
```

**Issue**: No Sentinel images found
- Increase cloud cover threshold
- Expand date range
- Check if AOI has data coverage

## 📊 Outputs

After running the notebook, you'll have:

### 1. Interactive Map
- Displays in notebook
- Multiple layers (True Color, NDVI, EVI, NDWI)
- Toggle layers on/off
- Zoom and pan

### 2. GEE Tile URLs
- Printed in notebook output
- Can be used directly in MapStore
- Format: `https://earthengine.googleapis.com/v1/...`

### 3. Configuration File
- Location: `/usr/src/app/data/{project_id}_config.json`
- Contains: All layer info, metadata, MapStore config
- Use for: Reproducibility, sharing, automation

### 4. FastAPI Integration
- Layers pushed to FastAPI
- Available at: `http://fastapi:8000/layers/{project_id}`
- Can be accessed by MapStore

## 🌐 Service URLs

| Service | URL | Credentials |
|---------|-----|-------------|
| Jupyter Lab | http://localhost:8888 | No password |
| FastAPI | http://localhost:8001 | None |
| FastAPI Docs | http://localhost:8001/docs | None |
| GeoServer | http://localhost:8080/geoserver | admin/admin |
| MapStore | http://localhost:8082/mapstore | Create account |
| PostgreSQL | localhost:5432 | gis_user/gis_password |
| Redis | localhost:6379 | No password |

## 🔗 Integration Flow

```
┌──────────────┐
│   Jupyter    │ 1. Authenticate with GEE
│   Notebook   │ 2. Process Sentinel-2 data
└──────┬───────┘ 3. Generate analysis products
       │
       ├─────────────────┐
       ▼                 ▼
┌────────────┐    ┌────────────┐
│    GEE     │    │  FastAPI   │ 4. Push results
│  (Google)  │    │  Service   │ 5. Cache in Redis
└────────────┘    └──────┬─────┘
                         │
                         ▼
                  ┌────────────┐
                  │ MapStore   │ 6. Add to catalog
                  │  Catalog   │ 7. View on map
                  └────────────┘
```

## 📦 Data Flow

1. **Input**: AOI coordinates, date range, parameters
2. **Processing**: GEE creates cloudless composite
3. **Analysis**: Calculate indices (NDVI, EVI, etc.)
4. **Visualization**: Generate GEE tile URLs
5. **Storage**: Push to FastAPI, cache in Redis
6. **Display**: Add to MapStore catalog
7. **Output**: Configuration file for reproducibility

## 🎓 Additional Resources

### GEE Resources
- [Earth Engine Code Editor](https://code.earthengine.google.com/)
- [Earth Engine Datasets](https://developers.google.com/earth-engine/datasets)
- [Sentinel-2 Documentation](https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S2_SR)

### Project Resources
- Main README: `/Users/miqbalf/gis-carbon-ai/README.md`
- Architecture: `/Users/miqbalf/gis-carbon-ai/ARCHITECTURE_DIAGRAM.md`
- Quick Start: `/Users/miqbalf/gis-carbon-ai/QUICK_START.md`

### API Documentation
- FastAPI: http://localhost:8001/docs
- GeoServer REST: http://localhost:8080/geoserver/rest/api

## 💡 Tips & Best Practices

1. **Start Small**: Test with small AOIs and short date ranges
2. **Monitor Quotas**: Keep track of GEE usage limits
3. **Use Caching**: FastAPI caches tiles for faster access
4. **Save Configs**: Keep configuration files for reproducibility
5. **Version Control**: Track analysis parameters
6. **Clean Data**: Remove old cache entries periodically
7. **Error Handling**: Wrap GEE operations in try-except
8. **Documentation**: Comment your custom analyses

## 🤝 Contributing

To add new notebooks or examples:
1. Follow the structure of `02_gee_calculations.ipynb`
2. Include clear documentation and comments
3. Test thoroughly before committing
4. Update this INDEX.md file

## 📝 Version History

- **v1.0** (Oct 2024): Initial release
  - Complete workflow notebook
  - Integration test script
  - Example API usage
  - Documentation

## 📧 Support

For questions or issues:
1. Check **README_GEE_WORKFLOW.md** → Troubleshooting section
2. Review **QUICK_REFERENCE.md** for common solutions
3. Run **test_gee_integration.py** to diagnose issues
4. Check Docker logs: `docker logs <container_name>`

---

**Last Updated**: October 2024  
**Maintained by**: GIS Carbon AI Team

