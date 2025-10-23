"""
GEE Catalog Updater for MapStore Integration
This module provides functions to push GEE analysis results to MapStore catalog
"""

import requests
import json
from datetime import datetime
from typing import Dict, Any, Optional

class GEECatalogUpdater:
    """
    A class to update MapStore catalog with GEE analysis results
    """
    
    def __init__(self, fastapi_url: str = "http://fastapi:8000"):
        """
        Initialize the catalog updater
        
        Args:
            fastapi_url: URL of the FastAPI service
        """
        self.fastapi_url = fastapi_url
        self.catalog_endpoint = f"{fastapi_url}/catalog/update"
        self.catalog_list_endpoint = f"{fastapi_url}/catalog"
        
    def push_gee_results(self, 
                        project_id: str,
                        project_name: str,
                        layers: Dict[str, Any],
                        analysis_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Push GEE analysis results to MapStore catalog
        
        Args:
            project_id: Unique identifier for the project
            project_name: Human-readable name for the project
            layers: Dictionary of layer information with tile URLs
            analysis_info: Additional analysis metadata
            
        Returns:
            Response from the catalog update service
        """
        try:
            # Prepare the catalog data
            catalog_data = {
                "project_id": project_id,
                "project_name": project_name,
                "layers": layers,
                "analysis_info": analysis_info or {}
            }
            
            print(f"Pushing GEE results to MapStore catalog...")
            print(f"  Project: {project_name} ({project_id})")
            print(f"  Layers: {len(layers)}")
            print(f"  Endpoint: {self.catalog_endpoint}")
            
            # Send the request
            response = requests.post(
                self.catalog_endpoint,
                json=catalog_data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                print("✅ Successfully updated MapStore catalog!")
                print(f"  Status: {result.get('status')}")
                print(f"  Layers Count: {result.get('layers_count')}")
                print(f"  Message: {result.get('message')}")
                print(f"  Catalog URL: {result.get('catalog_url')}")
                return result
            else:
                print(f"❌ Error updating catalog: {response.status_code}")
                try:
                    error_detail = response.json()
                    print(f"  Detail: {error_detail.get('detail', response.text)}")
                except:
                    print(f"  Response: {response.text}")
                return None
                
        except requests.exceptions.ConnectionError as e:
            print(f"❌ Connection Error: Cannot reach FastAPI service")
            print(f"  Make sure FastAPI container is running")
            print(f"  Check: docker ps | grep fastapi")
            return None
        except Exception as e:
            print(f"❌ Error pushing to catalog: {e}")
            import traceback
            print(f"  Traceback: {traceback.format_exc()}")
            return None
    
    def list_catalogs(self) -> Dict[str, Any]:
        """
        List all available catalogs
        
        Returns:
            Dictionary with catalog information
        """
        try:
            response = requests.get(self.catalog_list_endpoint, timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Error listing catalogs: {response.status_code}")
                return None
        except Exception as e:
            print(f"Error listing catalogs: {e}")
            return None
    
    def get_catalog_info(self, project_id: str) -> Dict[str, Any]:
        """
        Get information about a specific catalog
        
        Args:
            project_id: Project ID to get information for
            
        Returns:
            Catalog information
        """
        try:
            url = f"{self.fastapi_url}/catalog/{project_id}"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Error getting catalog info: {response.status_code}")
                return None
        except Exception as e:
            print(f"Error getting catalog info: {e}")
            return None

def create_gee_catalog_data(project_id: str,
                           project_name: str,
                           map_ids: Dict[str, Any],
                           vis_params: Dict[str, Any],
                           aoi_info: Optional[Dict[str, Any]] = None,
                           analysis_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Create catalog data from GEE analysis results
    
    Args:
        project_id: Unique project identifier
        project_name: Human-readable project name
        map_ids: Dictionary of GEE map IDs from getMapId()
        vis_params: Visualization parameters for each layer
        aoi_info: Area of Interest information
        analysis_params: Analysis parameters
        
    Returns:
        Formatted catalog data ready for MapStore
    """
    
    layers = {}
    
    for layer_name, map_id_dict in map_ids.items():
        # Extract tile URL from map ID
        tile_url = map_id_dict['tile_fetcher'].url_format
        
        # Create layer information
        layers[layer_name] = {
            'name': layer_name.replace('_', ' ').title(),
            'description': f'{layer_name.upper()} visualization from GEE analysis',
            'tile_url': tile_url,
            'map_id': map_id_dict['mapid'],
            'token': map_id_dict['token'],
            'vis_params': vis_params.get(layer_name, {}),
            'layer_type': 'gee_tms'
        }
    
    # Create analysis info
    analysis_info = {
        'aoi': aoi_info or {},
        'analysis_params': analysis_params or {},
        'generated_at': datetime.now().isoformat(),
        'total_layers': len(layers)
    }
    
    return {
        'project_id': project_id,
        'project_name': project_name,
        'layers': layers,
        'analysis_info': analysis_info
    }

# Convenience function for quick updates
def update_mapstore_catalog(project_id: str,
                           project_name: str,
                           map_ids: Dict[str, Any],
                           vis_params: Dict[str, Any],
                           aoi_info: Optional[Dict[str, Any]] = None,
                           analysis_params: Optional[Dict[str, Any]] = None,
                           fastapi_url: str = "http://fastapi:8000") -> Dict[str, Any]:
    """
    Quick function to update MapStore catalog with GEE results
    
    Args:
        project_id: Unique project identifier
        project_name: Human-readable project name
        map_ids: Dictionary of GEE map IDs from getMapId()
        vis_params: Visualization parameters for each layer
        aoi_info: Area of Interest information
        analysis_params: Analysis parameters
        fastapi_url: FastAPI service URL
        
    Returns:
        Response from catalog update
    """
    
    # Create catalog data
    catalog_data = create_gee_catalog_data(
        project_id=project_id,
        project_name=project_name,
        map_ids=map_ids,
        vis_params=vis_params,
        aoi_info=aoi_info,
        analysis_params=analysis_params
    )
    
    # Update catalog
    updater = GEECatalogUpdater(fastapi_url)
    return updater.push_gee_results(
        project_id=catalog_data['project_id'],
        project_name=catalog_data['project_name'],
        layers=catalog_data['layers'],
        analysis_info=catalog_data['analysis_info']
    )

# Example usage function
def example_usage():
    """
    Example of how to use the catalog updater
    """
    print("=== GEE Catalog Updater Example ===")
    
    # Example map IDs (replace with your actual GEE results)
    example_map_ids = {
        'ndvi': {
            'mapid': 'example_map_id',
            'token': 'example_token',
            'tile_fetcher': type('obj', (object,), {
                'url_format': 'https://earthengine.googleapis.com/v1/projects/earthengine-legacy/maps/example_map_id/tiles/{z}/{x}/{y}'
            })()
        }
    }
    
    # Example visualization parameters
    example_vis_params = {
        'ndvi': {
            'min': -0.2,
            'max': 0.8,
            'palette': ['red', 'yellow', 'green', 'darkgreen']
        }
    }
    
    # Update catalog
    result = update_mapstore_catalog(
        project_id="example_analysis_20250101",
        project_name="Example GEE Analysis",
        map_ids=example_map_ids,
        vis_params=example_vis_params,
        aoi_info={'center': [110.0, -1.0], 'area_km2': 1000},
        analysis_params={'satellite': 'Sentinel-2', 'date_range': '2023-01-01 to 2023-12-31'}
    )
    
    if result:
        print("\n🎉 Catalog updated successfully!")
        print("   Refresh MapStore to see the new layers")
    else:
        print("\n❌ Failed to update catalog")

if __name__ == "__main__":
    example_usage()
