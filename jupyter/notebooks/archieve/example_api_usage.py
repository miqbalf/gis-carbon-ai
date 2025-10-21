#!/usr/bin/env python3
"""
Example: Using the GEE-FastAPI integration programmatically
This demonstrates how to use the workflow from Python scripts
"""

import ee
import json
import requests
from datetime import datetime

def initialize_gee():
    """Initialize Google Earth Engine"""
    credentials_path = '/usr/src/app/user_id.json'
    
    with open(credentials_path, 'r') as f:
        credentials_data = json.load(f)
    
    service_account = credentials_data['client_email']
    credentials = ee.ServiceAccountCredentials(service_account, credentials_path)
    ee.Initialize(credentials)
    
    print(f"✓ Initialized GEE with {service_account}")

def create_sentinel_ndvi_layer(aoi_coords, date_start, date_end, layer_name="ndvi"):
    """
    Create a Sentinel-2 NDVI layer
    
    Args:
        aoi_coords: List of [lon, lat] coordinates defining polygon
        date_start: Start date string 'YYYY-MM-DD'
        date_end: End date string 'YYYY-MM-DD'
        layer_name: Name for the layer
    
    Returns:
        dict: Layer information including tile URL
    """
    # Create AOI
    aoi = ee.Geometry.Polygon([aoi_coords])
    
    # Get Sentinel-2 collection
    sentinel = ee.ImageCollection('COPERNICUS/S2_SR') \
        .filterDate(date_start, date_end) \
        .filterBounds(aoi) \
        .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
    
    # Create composite
    composite = sentinel.median().clip(aoi)
    
    # Calculate NDVI
    ndvi = composite.normalizedDifference(['B8', 'B4']).rename('NDVI')
    
    # Get map ID
    vis_params = {
        'min': -0.2,
        'max': 0.8,
        'palette': ['red', 'yellow', 'green', 'darkgreen']
    }
    
    map_id = ndvi.getMapId(vis_params)
    
    return {
        'name': layer_name,
        'tile_url': map_id['tile_fetcher'].url_format,
        'map_id': map_id['mapid'],
        'token': map_id['token'],
        'vis_params': vis_params,
        'metadata': {
            'satellite': 'Sentinel-2',
            'index': 'NDVI',
            'date_range': f'{date_start} to {date_end}',
            'image_count': sentinel.size().getInfo()
        }
    }

def push_to_mapstore_catalog(project_name, layers, aoi_coords, fastapi_url="http://fastapi:8000"):
    """
    Push layers to FastAPI service for MapStore catalog
    
    Args:
        project_name: Name for the project
        layers: List of layer dictionaries
        aoi_coords: AOI coordinates
        fastapi_url: FastAPI service URL
    
    Returns:
        dict: Response from FastAPI
    """
    project_id = f"project_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    payload = {
        'project_id': project_id,
        'project_name': project_name,
        'aoi': {
            'type': 'Polygon',
            'coordinates': [aoi_coords]
        },
        'layers': {}
    }
    
    # Add each layer
    for layer in layers:
        layer_name = layer['name']
        payload['layers'][layer_name] = layer
    
    # Send to FastAPI
    response = requests.post(
        f"{fastapi_url}/process-gee-analysis",
        json=payload,
        timeout=30
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✓ Pushed {len(layers)} layer(s) to FastAPI")
        print(f"  Project ID: {project_id}")
        return result
    else:
        print(f"✗ Error: {response.status_code}")
        print(f"  Response: {response.text}")
        return None

# ============================================================================
# EXAMPLE 1: Simple NDVI Layer
# ============================================================================

def example_1_simple_ndvi():
    """Example 1: Create and push a simple NDVI layer"""
    print("\n" + "="*60)
    print("EXAMPLE 1: Simple NDVI Layer")
    print("="*60 + "\n")
    
    # Initialize GEE
    initialize_gee()
    
    # Define AOI (Kalimantan, Indonesia)
    aoi_coords = [
        [109.5, -1.5],
        [110.5, -1.5],
        [110.5, -0.5],
        [109.5, -0.5],
        [109.5, -1.5]
    ]
    
    # Create NDVI layer
    print("Creating NDVI layer...")
    ndvi_layer = create_sentinel_ndvi_layer(
        aoi_coords=aoi_coords,
        date_start='2023-01-01',
        date_end='2023-12-31',
        layer_name='annual_ndvi'
    )
    
    print(f"✓ Layer created: {ndvi_layer['name']}")
    print(f"  Images used: {ndvi_layer['metadata']['image_count']}")
    print(f"  Tile URL: {ndvi_layer['tile_url'][:80]}...")
    
    # Push to FastAPI
    print("\nPushing to FastAPI...")
    result = push_to_mapstore_catalog(
        project_name="Simple NDVI Analysis",
        layers=[ndvi_layer],
        aoi_coords=aoi_coords
    )
    
    return result

# ============================================================================
# EXAMPLE 2: Multi-Season Analysis
# ============================================================================

def example_2_seasonal_analysis():
    """Example 2: Create seasonal NDVI layers"""
    print("\n" + "="*60)
    print("EXAMPLE 2: Seasonal Analysis")
    print("="*60 + "\n")
    
    # Initialize GEE
    initialize_gee()
    
    # Define AOI
    aoi_coords = [
        [109.5, -1.5],
        [110.5, -1.5],
        [110.5, -0.5],
        [109.5, -0.5],
        [109.5, -1.5]
    ]
    
    # Define seasons
    seasons = [
        ('dry_season', '2023-06-01', '2023-09-30'),
        ('wet_season', '2023-12-01', '2024-02-28'),
    ]
    
    layers = []
    
    for season_name, start_date, end_date in seasons:
        print(f"Creating {season_name} layer...")
        layer = create_sentinel_ndvi_layer(
            aoi_coords=aoi_coords,
            date_start=start_date,
            date_end=end_date,
            layer_name=f'ndvi_{season_name}'
        )
        layers.append(layer)
        print(f"✓ {season_name}: {layer['metadata']['image_count']} images")
    
    # Push all layers
    print(f"\nPushing {len(layers)} layers to FastAPI...")
    result = push_to_mapstore_catalog(
        project_name="Seasonal NDVI Analysis",
        layers=layers,
        aoi_coords=aoi_coords
    )
    
    return result

# ============================================================================
# EXAMPLE 3: Custom Analysis with Multiple Indices
# ============================================================================

def create_multi_index_layers(aoi_coords, date_start, date_end):
    """Create multiple vegetation indices"""
    aoi = ee.Geometry.Polygon([aoi_coords])
    
    # Get Sentinel-2 collection
    sentinel = ee.ImageCollection('COPERNICUS/S2_SR') \
        .filterDate(date_start, date_end) \
        .filterBounds(aoi) \
        .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
    
    composite = sentinel.median().clip(aoi)
    
    # Define indices
    indices = {
        'ndvi': {
            'bands': ['B8', 'B4'],
            'palette': ['red', 'yellow', 'green', 'darkgreen'],
            'min': -0.2,
            'max': 0.8
        },
        'evi': {
            'expression': '2.5 * ((NIR - RED) / (NIR + 6 * RED - 7.5 * BLUE + 1))',
            'bands': {'NIR': 'B8', 'RED': 'B4', 'BLUE': 'B2'},
            'palette': ['brown', 'yellow', 'lightgreen', 'darkgreen'],
            'min': -0.2,
            'max': 0.8
        },
        'ndwi': {
            'bands': ['B3', 'B8'],
            'palette': ['white', 'lightblue', 'blue', 'darkblue'],
            'min': -0.3,
            'max': 0.3
        }
    }
    
    layers = []
    
    for index_name, params in indices.items():
        print(f"  Calculating {index_name.upper()}...")
        
        if 'expression' in params:
            # Use expression for complex indices like EVI
            index_image = composite.expression(
                params['expression'],
                {k: composite.select(v) for k, v in params['bands'].items()}
            ).rename(index_name.upper())
        else:
            # Use normalized difference for simple indices
            index_image = composite.normalizedDifference(params['bands']).rename(index_name.upper())
        
        # Get map ID
        vis_params = {
            'min': params['min'],
            'max': params['max'],
            'palette': params['palette']
        }
        
        map_id = index_image.getMapId(vis_params)
        
        layers.append({
            'name': index_name,
            'tile_url': map_id['tile_fetcher'].url_format,
            'map_id': map_id['mapid'],
            'token': map_id['token'],
            'vis_params': vis_params,
            'metadata': {
                'satellite': 'Sentinel-2',
                'index': index_name.upper(),
                'date_range': f'{date_start} to {date_end}'
            }
        })
    
    return layers

def example_3_multi_index():
    """Example 3: Multiple vegetation indices"""
    print("\n" + "="*60)
    print("EXAMPLE 3: Multiple Vegetation Indices")
    print("="*60 + "\n")
    
    # Initialize GEE
    initialize_gee()
    
    # Define AOI
    aoi_coords = [
        [109.5, -1.5],
        [110.5, -1.5],
        [110.5, -0.5],
        [109.5, -0.5],
        [109.5, -1.5]
    ]
    
    print("Creating multiple index layers...")
    layers = create_multi_index_layers(
        aoi_coords=aoi_coords,
        date_start='2023-01-01',
        date_end='2023-12-31'
    )
    
    print(f"✓ Created {len(layers)} index layers")
    
    # Push all layers
    print("\nPushing to FastAPI...")
    result = push_to_mapstore_catalog(
        project_name="Multi-Index Analysis",
        layers=layers,
        aoi_coords=aoi_coords
    )
    
    return result

# ============================================================================
# MAIN
# ============================================================================

def main():
    """Run examples"""
    print("\n╔" + "="*58 + "╗")
    print("║" + " "*12 + "GEE-FastAPI Integration Examples" + " "*13 + "║")
    print("╚" + "="*58 + "╝")
    
    # Choose which example to run
    examples = {
        '1': ("Simple NDVI Layer", example_1_simple_ndvi),
        '2': ("Seasonal Analysis", example_2_seasonal_analysis),
        '3': ("Multiple Indices", example_3_multi_index),
    }
    
    print("\nAvailable examples:")
    for key, (name, _) in examples.items():
        print(f"  {key}. {name}")
    
    print("\nTo run an example, modify this script to call the desired function.")
    print("For example: example_1_simple_ndvi()")
    
    # Run example 1 by default
    print("\nRunning Example 1 by default...\n")
    example_1_simple_ndvi()

if __name__ == "__main__":
    main()

