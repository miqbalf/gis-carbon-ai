"""
Fixed merge function for 02p notebook - avoids swir2 references in xee inspection
"""

# Fixed merge function - use this in cell 9 of 02p_adding_si_tsfresh_annual_ndvi_evi.ipynb

def merge_with_fcd(img):
    """Merge spectral indices with FCD, creating clean images without problematic references"""
    # Get year for matching
    year = img.get('year')
    
    # Select only the spectral indices we need (this creates a new image and breaks computation graph)
    si_selected = img.select(['EVI', 'GNDVI', 'NDVI', 'SAVI', 'NBR'])
    
    # Get matching FCD image - handle case where FCD might not exist
    fcd_filtered = fcd_col.filter(ee.Filter.eq('year', year))
    fcd_img = ee.Algorithms.If(
        fcd_filtered.size().gt(0),
        fcd_filtered.first().select('FCD'),
        ee.Image.constant(0).rename('FCD')  # Fallback: create empty FCD band if missing
    )
    
    # Merge - this creates a completely new image
    merged = si_selected.addBands(ee.Image(fcd_img))
    
    # Copy only essential properties (avoid copying system:band_names or other problematic properties)
    # Only copy time and year properties, not band-related properties that might reference swir2
    result = merged.set('year', year).set('system:time_start', img.get('system:time_start'))
    
    return result

fcd_col_merged = ee_col_indices.map(merge_with_fcd)

