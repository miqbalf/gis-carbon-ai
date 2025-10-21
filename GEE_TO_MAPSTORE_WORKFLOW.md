# 🔄 GEE to MapStore Complete Workflow

## 📊 Visual Workflow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           COMPLETE WORKFLOW                                    │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   JUPYTER       │    │   GEE API       │    │   FASTAPI       │    │   MAPSTORE      │
│   NOTEBOOK      │    │   (Google)      │    │   SERVICE       │    │   UI            │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │                      │
          │ 1. Define AOI        │                      │                      │
          │ 2. Set Parameters    │                      │                      │
          │ 3. Run Analysis      │                      │                      │
          │                      │                      │                      │
          ▼                      ▼                      │                      │
┌─────────────────┐    ┌─────────────────┐              │                      │
│ • AOI Coords    │    │ • Sentinel-2    │              │                      │
│ • Date Range    │───▶│ • Cloud Masking │              │                      │
│ • Cloud %       │    │ • Composite     │              │                      │
│ • Indices       │    │ • NDVI, EVI,    │              │                      │
│                 │    │   NDWI, RGB     │              │                      │
└─────────────────┘    └─────────┬───────┘              │                      │
                                │                      │                      │
                                ▼                      │                      │
                    ┌─────────────────┐              │                      │
                    │ • Map IDs       │              │                      │
                    │ • Tile URLs     │──────────────▶│                      │
                    │ • Visualization │              │                      │
                    │   Parameters    │              │                      │
                    └─────────────────┘              │                      │
                                                     │                      │
                                                     ▼                      │
                                        ┌─────────────────┐              │
                                        │ • Register      │              │
                                        │   Layers        │              │
                                        │ • Store in      │              │
                                        │   Redis Cache   │              │
                                        │ • Return        │              │
                                        │   Confirmation  │              │
                                        └─────────────────┘              │
                                                                         │
                                                                         ▼
                                                             ┌─────────────────┐
                                                             │ • Update        │
                                                             │   localConfig   │
                                                             │ • Add GEE       │
                                                             │   Service       │
                                                             │ • Add Layers    │
                                                             │ • Restart       │
                                                             │   Container     │
                                                             └─────────────────┘
```

## 🎯 Step-by-Step Process

### Phase 1: GEE Analysis (Jupyter Notebook)
```
1. Initialize GEE with service account
   ↓
2. Define Area of Interest (AOI)
   ↓
3. Create cloudless Sentinel-2 composite
   ↓
4. Calculate vegetation indices (NDVI, EVI, NDWI)
   ↓
5. Generate RGB visualizations (True Color, False Color)
   ↓
6. Create GEE Map IDs for tile serving
```

### Phase 2: FastAPI Integration
```
7. Prepare layer data with metadata
   ↓
8. Register layers with FastAPI (/layers/register)
   ↓
9. Store in Redis cache (2-hour TTL)
   ↓
10. Return registration confirmation
```

### Phase 3: MapStore Integration
```
11. Load MapStore configuration (localConfig.json)
    ↓
12. Add GEE tile service to catalog
    ↓
13. Add individual layers to map layers
    ↓
14. Save updated configuration
    ↓
15. Restart MapStore container
```

### Phase 4: User Access (MapStore UI)
```
16. Open MapStore (http://localhost:8082/mapstore)
    ↓
17. Click Catalog button (📁)
    ↓
18. Find "GEE Analysis Layers" service
    ↓
19. Click layer names to add to map
    ↓
20. Use layer controls (visibility, opacity, order)
```

## 🔧 Technical Details

### Data Flow
```
Jupyter Notebook
    ↓ (GEE Analysis)
Google Earth Engine
    ↓ (Tile URLs)
FastAPI Service
    ↓ (Layer Registration)
Redis Cache
    ↓ (Configuration Update)
MapStore localConfig.json
    ↓ (Container Restart)
MapStore UI
    ↓ (User Interaction)
Interactive Map
```

### Service Communication
```
┌─────────────┐    HTTP POST    ┌─────────────┐
│   Jupyter   │ ──────────────▶ │   FastAPI   │
│   Notebook  │                 │   Service   │
└─────────────┘                 │ (localhost: │
                                │    8001)    │
                                └─────────────┘
                                       │
                                       │ HTTP GET
                                       ▼
                                ┌─────────────┐
                                │   MapStore  │
                                │   UI        │
                                │ (localhost: │
                                │    8082)    │
                                └─────────────┘
```

### File Locations
```
/Users/miqbalf/gis-carbon-ai/
├── jupyter/notebooks/
│   └── 02_gee_calculations.ipynb    # Main analysis notebook
├── mapstore/
│   └── localConfig.json             # MapStore configuration
├── fastapi-gee-service/
│   └── main.py                      # FastAPI service
└── backend/
    └── user_id.json                 # GEE credentials
```

## 🎨 Layer Information

### Generated Layers
| Layer | Type | Description | Use Case |
|-------|------|-------------|----------|
| **True Color** | RGB | Natural color visualization | Base map, visual reference |
| **False Color** | NIR-Red-Green | Highlights vegetation | Vegetation analysis |
| **NDVI** | Index | Vegetation health (-1 to +1) | Forest monitoring |
| **EVI** | Index | Enhanced vegetation index | Dense vegetation areas |
| **NDWI** | Index | Water detection (-1 to +1) | Water body mapping |

### Layer URLs
- **Direct GEE**: `https://earthengine.googleapis.com/v1/projects/...`
- **FastAPI Proxy**: `http://localhost:8001/tiles/gee/{layer_name}/{z}/{x}/{y}`
- **MapStore Integration**: Automatic via localConfig.json

## 🚀 Quick Commands

### Run Complete Workflow
```bash
# 1. Start services
docker-compose -f docker-compose.dev.yml up -d

# 2. Open Jupyter Lab
open http://localhost:8888

# 3. Run notebook
# (Open notebooks/02_gee_calculations.ipynb and run all cells)

# 4. Access MapStore
open http://localhost:8082/mapstore
```

### Manual Integration
```bash
# 1. Run integration script
cd /Users/miqbalf/gis-carbon-ai/mapstore
python add-gee-layers-manual.py

# 2. Restart MapStore
docker-compose -f docker-compose.dev.yml restart mapstore

# 3. Access MapStore
open http://localhost:8082/mapstore
```

### Test Integration
```bash
# Test FastAPI
curl http://localhost:8001/health

# Test layer registration
curl http://localhost:8001/layers/sentinel_analysis_20251020_172658

# Test MapStore
curl http://localhost:8082/mapstore
```

## 📊 Expected Outputs

### Console Output (Jupyter)
```
✓ Imports loaded successfully
✓ GEE Initialized successfully
✓ AOI defined
✓ Sentinel-2 cloudless composite created
✓ Analysis products generated
✓ Map IDs generated for all layers
✓ Interactive map created with all layers
✓ Data prepared for FastAPI
✓ Successfully pushed to FastAPI
✓ MapStore catalog configuration generated
✓ Successfully added GEE layers to MapStore!
✓ MapStore container restarted successfully
🎉 MapStore is ready with your GEE layers!
```

### MapStore UI
- **Catalog**: Shows "GEE Analysis Layers" service
- **Layers**: 5 layers available for adding to map
- **Controls**: Visibility, opacity, order controls work
- **Tiles**: Load and display correctly

## 🔍 Troubleshooting

### Common Issues
1. **"No GEE layers in Catalog"**
   - Check FastAPI: `curl http://localhost:8001/health`
   - Re-run integration script
   - Restart MapStore

2. **"MapStore not loading"**
   - Check container: `docker ps | grep mapstore`
   - Check logs: `docker logs gis_mapstore_dev`
   - Restart: `docker-compose -f docker-compose.dev.yml restart mapstore`

3. **"Layers not displaying"**
   - Check GEE tile URLs
   - Verify internet connection
   - Check GEE quotas

## ✅ Success Metrics

### Technical Success
- [x] GEE analysis completes without errors
- [x] 5 layers generated and registered
- [x] FastAPI returns success status
- [x] MapStore configuration updated
- [x] MapStore container restarted
- [x] Layers visible in Catalog
- [x] Layers can be added to map
- [x] Tiles load and display

### User Experience
- [x] Simple one-click workflow
- [x] Clear progress indicators
- [x] Automatic integration
- [x] Interactive visualization
- [x] Professional results

---

**🎯 This workflow transforms raw satellite data into interactive maps in just a few clicks!**

**Ready to start? Run the notebook and see your data come to life!** 🌍✨
