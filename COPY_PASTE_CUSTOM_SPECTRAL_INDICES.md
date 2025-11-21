# Custom Spectral Indices for Custom Images

This guide shows how to use the new `spectra_indices()` method for custom images with non-standard band names.

## Problem
When using `eemont.spectralIndices()` with custom images (loaded from GeoTIFF), you may encounter errors like:
- `Band pattern 'B6' did not match any bands`
- Platform detection issues
- Band mapping problems

## Solution
Use the new `spectra_indices()` method (or `computeSpectralIndices()` alias) that computes indices directly from formulas, bypassing `ee_extra`'s internal band mapping.

## Usage

### Basic Example

```python
import ee, eemont

# Your custom image (e.g., Planet 8-band)
img = ee.Image.loadGeoTIFF('gs://bucket/image.tif')

# Map standard band names to your actual band names
band_map = {
    'nir': 'B8',      # or 'nir', 'near_infrared', etc.
    'red': 'B4',      # or 'red', 'r', etc.
    'green': 'B3',    # or 'green', 'g', etc.
    'blue': 'B2',     # or 'blue', 'b', etc.
    'redE1': 'B5',    # Red Edge 1 (if available)
    # 'swir1': 'B11', # SWIR1 (if available)
    # 'swir2': 'B12', # SWIR2 (if available)
}

# Compute indices directly from formulas
img_with_indices = img.spectra_indices(
    index=['NDVI', 'EVI', 'SAVI', 'GNDVI', 'ARVI', 'BAI', 'ExG', 'ExGR'],
    band_map=band_map,
    G=2.5,      # Gain for EVI
    C1=6.0,     # Coefficient 1 for EVI
    C2=7.5,     # Coefficient 2 for EVI
    L=1.0,      # Canopy background adjustment for EVI/SAVI
    drop=False  # Keep original bands
)

# Check results
img_with_indices.bandNames().getInfo()
```

### Your Specific Case (Planet 8-band)

```python
# Your image with Planet band names
input_image_fix = input_image.select(['B0', 'B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7']). \
                                rename(['coastal_blue','blue','green1','green','yellow','red','redE1','nir'])

# Map standard names to your Planet band names
band_map = {
    'nir': 'nir',           # Already named correctly
    'red': 'red',           # Already named correctly
    'green': 'green',       # Already named correctly
    'blue': 'blue',         # Already named correctly
    'redE1': 'redE1',       # Already named correctly
    # Note: You don't have redE2 (B6), swir1, or swir2
}

# Compute indices (excluding those that require B6/redE2)
indices_list = [
    'ARVI', 'BAI', 'EVI', 'ExG', 'ExGR',
    'GEMI', 'GLI', 'GNDVI', 'MSR', 'NGRDI',
    'NLI', 'OSAVI', 'RDVI', 'RVI', 'SAVI', 'TVI',
    'VIG', 'WDRVI', 'WI2'
    # Excluded: 'CRI700', 'NDREI' (require redE2/B6)
]

img_with_indices = input_image_fix.spectra_indices(
    index=indices_list,
    band_map=band_map,
    G=2.5,
    C1=6.0,
    C2=7.5,
    L=1.0,
    drop=True  # Keep only indices
)

# Check results
img_with_indices.bandNames().getInfo()
```

### Auto-Detection (No band_map needed)

If your band names match common patterns, the method will auto-detect them:

```python
# If your bands are named: 'nir', 'red', 'green', 'blue', 'redE1'
img_with_indices = img.spectra_indices(
    index=['NDVI', 'EVI', 'SAVI'],
    # band_map=None  # Will auto-detect
)
```

### Available Parameters

All standard `eemont` parameters are supported:
- `G=2.5` - Gain factor for EVI
- `C1=6.0` - Coefficient 1 for EVI
- `C2=7.5` - Coefficient 2 for EVI
- `L=1.0` - Canopy background adjustment
- `alpha=0.1` - Weighting for WDRVI
- `gamma=1.0` - Weighting for ARVI
- And more...

### Advantages

1. **No B6 errors**: Computes indices directly from formulas, avoiding `ee_extra`'s internal band mapping
2. **Works with custom images**: No need for `system:id` or platform detection
3. **Flexible band mapping**: Map any band names to standard names
4. **All 253 indices**: Supports all indices from the awesome list
5. **Safe evaluation**: Uses `ee.Image.expression()` for safe formula evaluation

### Limitations

- Some indices require bands you don't have (e.g., `CRI700`, `NDREI` require `redE2`/`B6`)
- Complex formulas may not parse correctly (most common indices work fine)
- Parameters must be provided if the formula uses them

### Finding Which Indices Require Which Bands

```python
import ee_extra.Spectral.core as spec_core

indices_dict = spec_core.indices(online=False)

# Check what bands an index requires
ndvi_info = indices_dict['NDVI']
print(f"NDVI bands: {ndvi_info['bands']}")  # ['N', 'R']
print(f"NDVI formula: {ndvi_info['formula']}")  # '(N - R)/(N + R)'

# Check if an index requires redE2/B6
cri700_info = indices_dict['CRI700']
print(f"CRI700 bands: {cri700_info['bands']}")  # ['RE1', 'RE2'] - requires redE2!
```

### Complete Example for Your Notebook

```python
# After you have input_image_fix ready
band_map = {
    'nir': 'nir',
    'red': 'red',
    'green': 'green',
    'blue': 'blue',
    'redE1': 'redE1',
}

# List of indices that don't require redE2/B6
indices_safe = [
    'ARVI', 'BAI', 'EVI', 'ExG', 'ExGR',
    'GEMI', 'GLI', 'GNDVI', 'MSR', 'NGRDI',
    'NLI', 'OSAVI', 'RDVI', 'RVI', 'SAVI', 'TVI',
    'VIG', 'WDRVI', 'WI2'
]

img_with_indices = input_image_fix.spectra_indices(
    index=indices_safe,
    band_map=band_map,
    G=2.5, C1=6.0, C2=7.5, L=1.0,
    drop=True
)

# Now combine with your normalized bands
img_to_export = input_image_fix.addBands(image_norm_with_fcd_renamed).addBands(img_with_indices)
```

