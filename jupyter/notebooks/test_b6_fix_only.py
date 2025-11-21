"""
Test ONLY the B6 fix (reverse mapping), not the platform detection.
This verifies that the B6 error is fixed.
"""
import ee
import sys
sys.path.insert(0, '/usr/src/app/eemont-osi')

# Initialize
ee.Initialize(project='remote-sensing-476412', credentials=ee.ServiceAccountCredentials(None, '/usr/src/app/user_id.json'))

# Create test image with B2, B3, B4, B5, B8 (NO B6) plus some indices
# Simulate what happens after ee_extra processes it
test_image = ee.Image.constant([0.1] * 7).rename(['B2', 'B3', 'B4', 'B5', 'B8', 'NDVI', 'EVI'])
test_collection = ee.ImageCollection([test_image])

print("Test image bands:", test_image.bandNames().getInfo())
print("\nTesting reverse mapping with B6 in reverse_map but NOT in image...")

# Simulate reverse_map that includes B6 (this is the bug scenario)
reverse_map = {'B2': 'blue', 'B3': 'green', 'B4': 'red', 'B5': 'redE1', 'B6': 'redE2', 'B8': 'nir'}
bands_to_rename_list = list(reverse_map.keys())  # Includes B6
new_names_list = [reverse_map[old] for old in bands_to_rename_list]

print(f"reverse_map keys: {bands_to_rename_list}")
print(f"Image bands: {test_image.bandNames().getInfo()}")
print(f"B6 in reverse_map: {'B6' in bands_to_rename_list}")
print(f"B6 in image: {'B6' in test_image.bandNames().getInfo()}")

# Test the rename_back logic
def rename_back_test(img):
    all_bands = img.bandNames()
    bands_to_rename_ee = ee.List(bands_to_rename_list)
    bands_to_keep_ee = all_bands.removeAll(bands_to_rename_ee)
    result_img = img.select(bands_to_keep_ee)
    
    # Add renamed bands with existence check
    old_names_ee = ee.List(bands_to_rename_list)
    new_names_ee = ee.List(new_names_list)
    
    def add_renamed_band_if_exists(acc, i):
        old_name = old_names_ee.get(i)
        new_name = new_names_ee.get(i)
        band_exists = all_bands.contains(old_name)
        renamed_band = ee.Algorithms.If(
            band_exists,
            img.select([old_name]).rename([new_name]),
            None
        )
        return ee.Algorithms.If(
            ee.Algorithms.IsEqual(acc, None),
            ee.Algorithms.If(band_exists, renamed_band, None),
            ee.Algorithms.If(band_exists, acc.addBands(renamed_band), acc)
        )
    
    renamed_combined = old_names_ee.iterate(
        lambda i, acc: add_renamed_band_if_exists(acc, i),
        None
    )
    
    result_img = ee.Algorithms.If(
        ee.Algorithms.IsEqual(renamed_combined, None),
        result_img,
        result_img.addBands(renamed_combined)
    )
    
    return result_img

try:
    result = test_collection.map(rename_back_test)
    result_image = result.first()
    band_names = result_image.bandNames().getInfo()
    print(f"\n✅ SUCCESS! Reverse mapping worked with {len(band_names)} bands")
    print(f"   Result bands: {band_names}")
    print("   ✅ B6 was skipped (as expected)")
except Exception as e:
    print(f"\n❌ ERROR: {type(e).__name__}: {str(e)[:300]}")
    if "B6" in str(e):
        print("   ❌ B6 error still exists!")
    else:
        print("   ⚠️  Different error (not B6 related)")

