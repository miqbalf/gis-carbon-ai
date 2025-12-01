# Reverse Mapping Fix for eemont-osi spectralIndices

## Problem
When using `spectralIndices()` with `satellite_type='Sentinel'` and `drop=False`, bands were not being reverse-mapped back to OSI names. Instead of getting `['blue', 'green', 'red', 'nir', 'swir1', 'swir2', 'EVI', 'NDVI', ...]`, users were getting `['B2', 'B3', 'B4', 'B8', 'B11', 'B12', 'EVI', 'NDVI', ...]`.

## Changes Made

### 1. Fixed `iterate` parameter order in `imagecollection.py`
**File**: `eemont-osi/eemont/imagecollection.py` (line ~1085)

**Issue**: The `iterate` function in Earth Engine takes `(accumulator, current)` as parameters, but the code was using `(current, accumulator)`.

**Fix**: Changed from:
```python
renamed_img = bands_to_rename_ee.iterate(
    lambda old_name, acc: add_renamed_band(acc, old_name),
    None
)
```

To:
```python
renamed_img = bands_to_rename_ee.iterate(
    lambda acc, old_name: add_renamed_band(acc, old_name),
    None
)
```

### 2. Added `satellite_type` and `band_map` support to `ee.Image.spectralIndices`
**File**: `eemont-osi/eemont/image.py` (lines ~784-973)

**Changes**:
- Added `satellite_type` and `band_map` parameters to `ee.Image.spectralIndices()`
- When `satellite_type` or `band_map` is provided, the method now:
  1. Wraps the single image in an `ee.ImageCollection`
  2. Calls `ImageCollection.spectralIndices()` (which has the reverse mapping logic)
  3. Extracts the first image from the result
  4. Copies properties from the original image

This ensures that single `ee.Image` objects (like custom PlanetScope images) also benefit from the OSI band mapping and reverse mapping.

## Testing

### Test Script
A test script has been created at: `test_spectral_indices_reverse_mapping.py`

### How to Test in Docker Jupyter

1. **Start the Jupyter container** (if not already running):
   ```bash
   docker-compose -f docker-compose.dev.yml up -d jupyter
   ```

2. **Open Jupyter Lab** and create a new notebook or use an existing one

3. **Reload the eemont-osi module** (important!):
   ```python
   import importlib
   import eemont
   importlib.reload(eemont)
   ```

4. **Test ImageCollection**:
   ```python
   import ee, eemont
   
   # Create test collection with OSI-style bands
   test_img = ee.Image.constant(0.5).rename(['blue'])
   for band in ['green', 'nir', 'red', 'swir1', 'swir2']:
       test_img = test_img.addBands(ee.Image.constant(0.5).rename([band]))
   
   test_col = ee.ImageCollection([test_img])
   
   # Compute spectral indices
   result_col = test_col.spectralIndices(
       index=['EVI', 'GNDVI', 'NDVI', 'SAVI', 'NBR'],
       satellite_type='Sentinel',
       drop=False
   )
   
   # Check result
   result_bands = result_col.first().bandNames().getInfo()
   print(f"Result bands: {result_bands}")
   
   # Should see OSI names (blue, green, red, nir, swir1, swir2) not Sentinel names (B2, B3, etc.)
   ```

5. **Test ee.Image** (for custom images like PlanetScope):
   ```python
   # Create test image with OSI-style bands
   test_img = ee.Image.constant(0.5).rename(['blue'])
   for band in ['green', 'nir', 'red', 'swir1', 'swir2']:
       test_img = test_img.addBands(ee.Image.constant(0.5).rename([band]))
   
   # Compute spectral indices
   result_img = test_img.spectralIndices(
       index=['EVI', 'GNDVI', 'NDVI', 'SAVI', 'NBR'],
       satellite_type='Sentinel',
       drop=False
   )
   
   # Check result
   result_bands = result_img.bandNames().getInfo()
   print(f"Result bands: {result_bands}")
   
   # Should see OSI names (blue, green, red, nir, swir1, swir2) not Sentinel names (B2, B3, etc.)
   ```

### Testing with Real Notebooks

1. **Test `02p_adding_si_tsfresh_annual_ndvi_evi.ipynb`**:
   - Run the cell that computes `ee_col_indices`
   - Check: `ee_col_indices.first().bandNames().getInfo()`
   - Expected: Should see OSI names like `['blue', 'green', 'red', 'nir', 'swir1', 'swir2', 'EVI', 'GNDVI', 'NDVI', 'SAVI', 'NBR']`
   - Not: `['B2', 'B3', 'B4', 'B8', 'B11', 'B12', 'EVI', 'GNDVI', 'NDVI', 'SAVI', 'NBR']`

2. **Test `02l_pl_landcover.ipynb`**:
   - Run the cell that uses `img.spectralIndices()` or `img.spectra_indices()` with a custom PlanetScope image
   - Check: `result_img.bandNames().getInfo()`
   - Expected: Should see OSI names preserved or correctly mapped

## Expected Behavior

### Before Fix
- `spectralIndices(satellite_type='Sentinel', drop=False)` returned bands with Sentinel names: `['B2', 'B3', 'B4', 'B8', 'B11', 'B12', 'EVI', 'NDVI', ...]`

### After Fix
- `spectralIndices(satellite_type='Sentinel', drop=False)` returns bands with OSI names: `['blue', 'green', 'red', 'nir', 'swir1', 'swir2', 'EVI', 'NDVI', ...]`

## Files Modified

1. `eemont-osi/eemont/imagecollection.py` - Fixed `iterate` parameter order
2. `eemont-osi/eemont/image.py` - Added `satellite_type` and `band_map` support to `ee.Image.spectralIndices()`

## Notes

- The reverse mapping only applies when `satellite_type` or `band_map` is provided
- If `drop=True`, only spectral indices are returned (no original bands to reverse-map)
- The fix ensures that both `ee.ImageCollection` and `ee.Image` work correctly with OSI-style band names

