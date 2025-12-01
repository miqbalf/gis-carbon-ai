#!/usr/bin/env python3
"""
More robust cleaning that handles images with missing bands
"""

# Copy this code into a NEW cell after cell 9 (after ee_col_indices.first().bandNames().getInfo())

# Clean ee_col_indices - handle images that might have missing bands
print("🧹 Cleaning ee_col_indices to remove problematic band references...")
print("   This step ensures all images have consistent bands and breaks computation graph")

# Get bands from first image as reference
first_img_bands = ee_col_indices.first().bandNames().getInfo()
print(f"   Reference bands from first image: {first_img_bands}")

# Define the bands we want to keep (spectral indices + OSI bands)
desired_bands = ['EVI', 'GNDVI', 'NDVI', 'SAVI', 'NBR', 'blue', 'green', 'red', 'redE1', 'redE2', 'redE3', 'nir', 'redE4', 'swir1', 'swir2']

# Filter to only bands that exist in the first image
bands_to_keep = [b for b in desired_bands if b in first_img_bands]
print(f"   Bands to keep (filtered): {bands_to_keep}")

# Clean each image - only select bands that exist in that specific image
# This prevents errors if some images have different band sets
def clean_image(img):
    """Clean a single image by selecting only existing bands"""
    img_bands = img.bandNames()
    # Create a mask for bands that exist
    existing_bands = bands_to_keep.filter(lambda b: img_bands.contains(b))
    # Select only the bands that exist
    return img.select(existing_bands)

ee_col_indices = ee_col_indices.map(clean_image)

print(f"   After cleaning: {ee_col_indices.first().bandNames().getInfo()}")
print("✅ Collection cleaned - computation graph broken")

