# 🗺️ How to Add GEE Layers to MapStore UI

## 🎯 Complete Step-by-Step Guide

### Method 1: Using the Jupyter Notebook (Recommended)

#### Step 1: Run the Complete Notebook
1. **Open Jupyter Lab**: http://localhost:8888
2. **Open the notebook**: `notebooks/02_gee_calculations.ipynb`
3. **Run all cells**: Click **Run** → **Run All Cells**
4. **Wait for completion**: The notebook will automatically:
   - Create GEE analysis
   - Register layers with FastAPI
   - Add layers to MapStore configuration
   - Restart MapStore container

#### Step 2: Access Your Layers in MapStore
1. **Open MapStore**: http://localhost:8082/mapstore
2. **Click Catalog**: Look for the 📁 (Catalog) button in the toolbar
3. **Find GEE Service**: Look for **"GEE Analysis Layers"** service
4. **Add Layers**: Click on any layer name to add it to your map

---

### Method 2: Manual Integration

#### Step 1: Run the Manual Script
```bash
cd /Users/miqbalf/gis-carbon-ai/mapstore
python add-gee-layers-manual.py
```

#### Step 2: Restart MapStore
```bash
docker-compose -f docker-compose.dev.yml restart mapstore
```

#### Step 3: Access in MapStore
1. Open: http://localhost:8082/mapstore
2. Click Catalog (📁)
3. Find "GEE Analysis Layers"
4. Add layers to your map

---

## 🎨 Detailed MapStore UI Instructions

### Step 1: Open MapStore
```
http://localhost:8082/mapstore
```

### Step 2: Access the Catalog
1. **Look for the Catalog button** in the toolbar (usually looks like 📁 or a folder icon)
2. **Click on it** to open the catalog panel
3. **The catalog will appear** on the right side of the screen

### Step 3: Find Your GEE Layers
1. **Look for "GEE Analysis Layers"** in the services list
2. **Click to expand** the service
3. **You'll see all your layers**:
   - `sentinel_analysis_YYYYMMDD_HHMMSS_true_color`
   - `sentinel_analysis_YYYYMMDD_HHMMSS_false_color`
   - `sentinel_analysis_YYYYMMDD_HHMMSS_ndvi`
   - `sentinel_analysis_YYYYMMDD_HHMMSS_evi`
   - `sentinel_analysis_YYYYMMDD_HHMMSS_ndwi`

### Step 4: Add Layers to Your Map
1. **Click on any layer name** in the catalog
2. **The layer will be added** to your map automatically
3. **Repeat for other layers** you want to display

### Step 5: Control Your Layers
1. **Toggle visibility**: Use the eye icon next to each layer
2. **Adjust opacity**: Use the slider to make layers more/less transparent
3. **Reorder layers**: Drag layers up/down in the layer list
4. **Remove layers**: Click the X button to remove a layer

---

## 🔍 What You'll See in MapStore

### Available Layers
Based on your analysis, you'll have these layers:

| Layer Name | Description | What It Shows |
|------------|-------------|---------------|
| **True Color** | Natural color RGB | How the area looks to human eyes |
| **False Color** | NIR-Red-Green | Highlights vegetation in red |
| **NDVI** | Vegetation Index | Green = healthy vegetation, red = no vegetation |
| **EVI** | Enhanced Vegetation Index | Similar to NDVI but better for dense vegetation |
| **NDWI** | Water Index | Blue = water bodies, white = dry areas |

### Layer Controls
- **Visibility Toggle**: Eye icon to show/hide layers
- **Opacity Slider**: Adjust transparency (0-100%)
- **Layer Order**: Drag to change stacking order
- **Layer Info**: Right-click for properties and metadata

---

## 🎯 Quick Start (5 Minutes)

### Option A: Run Notebook
```bash
# 1. Open Jupyter Lab
open http://localhost:8888

# 2. Open notebook
notebooks/02_gee_calculations.ipynb

# 3. Run all cells
# (Click Run → Run All Cells)

# 4. Open MapStore
open http://localhost:8082/mapstore
```

### Option B: Manual Integration
```bash
# 1. Run integration script
cd /Users/miqbalf/gis-carbon-ai/mapstore
python add-gee-layers-manual.py

# 2. Restart MapStore
docker-compose -f docker-compose.dev.yml restart mapstore

# 3. Open MapStore
open http://localhost:8082/mapstore
```

---

## 🔧 Troubleshooting

### Issue: "No GEE layers in Catalog"
**Solution**:
1. Check if layers were registered with FastAPI:
   ```bash
   curl http://localhost:8001/layers/sentinel_analysis_20251020_172658
   ```

2. Re-run the integration:
   ```bash
   cd /Users/miqbalf/gis-carbon-ai/mapstore
   python add-gee-layers-manual.py
   docker-compose -f docker-compose.dev.yml restart mapstore
   ```

### Issue: "MapStore not loading"
**Solution**:
1. Check if MapStore is running:
   ```bash
   docker ps | grep mapstore
   ```

2. Check MapStore logs:
   ```bash
   docker logs gis_mapstore_dev
   ```

3. Restart MapStore:
   ```bash
   docker-compose -f docker-compose.dev.yml restart mapstore
   ```

### Issue: "Layers not displaying"
**Solution**:
1. Check if GEE tile URLs are valid
2. Verify internet connection
3. Check GEE quotas
4. Try refreshing the map

### Issue: "Catalog button not visible"
**Solution**:
1. Look for a folder icon (📁) in the toolbar
2. Try different browser zoom levels
3. Check if MapStore loaded completely
4. Refresh the page

---

## 📊 Expected Results

### After Running the Notebook
You should see:
- ✅ **5 GEE layers** registered with FastAPI
- ✅ **MapStore configuration** updated
- ✅ **MapStore restarted** automatically
- ✅ **Layers available** in Catalog

### In MapStore UI
You should see:
- ✅ **"GEE Analysis Layers"** service in Catalog
- ✅ **5 layer names** under the service
- ✅ **Layers can be added** to map by clicking
- ✅ **Layer controls** work (visibility, opacity, order)

---

## 🎨 Using Layers in MapStore

### Layer Combinations
Try these combinations for different analyses:

#### Forest Monitoring
- **NDVI** + **EVI** (both vegetation indices)
- **True Color** as base layer

#### Water Body Detection
- **NDWI** (water index)
- **False Color** to see context

#### Land Cover Analysis
- **True Color** + **False Color** + **NDVI**
- Compare different visualizations

#### Change Detection
- Run analysis for different time periods
- Compare NDVI layers from different dates

### Layer Styling
- **Adjust opacity**: Make layers semi-transparent to see underlying data
- **Change order**: Put most important layers on top
- **Toggle visibility**: Turn layers on/off to focus on specific data

---

## 🚀 Advanced Usage

### Creating Maps
1. **Add multiple layers** to your map
2. **Adjust styling** and opacity
3. **Save the map** for later use
4. **Share the map** with your team

### Exporting Results
1. **Print the map** as PDF or image
2. **Export layer data** (if supported)
3. **Share map URLs** with stakeholders

### Custom Analysis
1. **Modify the notebook** for different AOIs
2. **Change date ranges** for time series analysis
3. **Add custom indices** for specific needs
4. **Automate the workflow** for regular updates

---

## 📚 Additional Resources

### Documentation
- **Complete Guide**: `README_GEE_WORKFLOW.md`
- **Quick Reference**: `QUICK_REFERENCE.md`
- **Integration Guide**: `MAPSTORE_GEE_INTEGRATION_GUIDE.md`

### Service URLs
- **Jupyter Lab**: http://localhost:8888
- **MapStore**: http://localhost:8082/mapstore
- **FastAPI**: http://localhost:8001
- **FastAPI Docs**: http://localhost:8001/docs

### Scripts
- **Notebook Integration**: `add_to_mapstore.py`
- **Manual Integration**: `add-gee-layers-manual.py`
- **Test Script**: `test_gee_integration.py`

---

## ✅ Success Checklist

- [ ] Jupyter notebook runs without errors
- [ ] GEE analysis creates 5 layers
- [ ] Layers registered with FastAPI
- [ ] MapStore configuration updated
- [ ] MapStore container restarted
- [ ] MapStore accessible at :8082
- [ ] "GEE Analysis Layers" visible in Catalog
- [ ] Layers can be added to map
- [ ] Layer controls work (visibility, opacity)
- [ ] Tiles load and display correctly

---

## 🎉 You're Ready!

Once you complete these steps, you'll have:
- ✅ **GEE analysis** running in Jupyter
- ✅ **Layers automatically** added to MapStore
- ✅ **Interactive visualization** in MapStore UI
- ✅ **Full control** over layer display
- ✅ **Professional maps** ready for sharing

**Start analyzing your geospatial data now!** 🌍📊

---

**Last Updated**: October 20, 2024  
**Status**: ✅ Production Ready  
**Version**: 1.0
