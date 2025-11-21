# How to Use Custom Image with run_eligibility

## Quick Copy-Paste Code for Your Notebook

After you have created `input_image_fix` in your notebook, simply add this code:

```python
# Set I_satellite to 'Custom' in your config
forestry.config['I_satellite'] = 'Custom'

# Run eligibility with your custom image
el = forestry.run_eligibility(
    config=forestry.config,
    use_gee=True,
    custom_image=input_image_fix  # Your pre-processed image
)

# Access results as usual
final_zone = el['final_zone']
intermediate_results = el['intermediate_results']
visualization_params = el['visualization_params']
```

## What Changed

The `run_eligibility` function now supports:
- `I_satellite='Custom'` in config
- `custom_image` parameter in kwargs

When you provide `custom_image`, the function will:
1. Skip ImageCollection creation
2. Use your `input_image_fix` directly
3. Continue with FCD calculation, spectral indices, OBIA, ML classification, Hansen analysis, and zone assignment

## Requirements

Your `input_image_fix` should have these bands:
- `red`
- `green` 
- `blue`
- `nir`
- (optionally `swir1`, `swir2` for Planet)

The image should already be:
- Cloud-masked
- Reprojected to appropriate CRS
- Clipped to AOI (or will be clipped automatically)

## Example from Your Notebook

```python
# After creating input_image_fix (from cell 6)
input_image_fix = input_image.select(['B0', 'B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7']). \
                                rename(['coastal_blue','blue','green1','green','yellow','red','redEdge','nir'])

# Set config for custom image
forestry.config['I_satellite'] = 'Custom'

# Make sure you have input_training and label_column in config
# forestry.config['input_training'] = 'path/to/training_points.shp'
# forestry.config['label_column'] = 'type'  # or 'code_lu' or any other column name

# Run eligibility
el = forestry.run_eligibility(
    config=forestry.config,
    use_gee=True,
    custom_image=input_image_fix
)

print("✅ Eligibility analysis completed!")
print(f"Algorithm used: {el['intermediate_results']['algo_ml_selected']}")
```

