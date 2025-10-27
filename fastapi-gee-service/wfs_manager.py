"""
WFS Manager - Simplified Vector Layer Management for Existing WFS Infrastructure

This module provides a simple, Map.addLayer()-like interface for adding vector layers
to the existing WFS service without creating new WFS infrastructure.
"""

import ee
import requests
import logging
from typing import Dict, Any, Optional, Union
from datetime import datetime

logger = logging.getLogger(__name__)

class WFSManager:
    """
    Simplified WFS Manager that provides Map.addLayer()-like functionality
    for adding vector layers to the existing WFS service via /fc/ endpoints.
    
    Usage:
        wfs = WFSManager(fastapi_url="http://fastapi:8000")
        wfs.addLayer(AOI_geometry, "AOI Boundary")
        wfs.addLayer(training_points_ee, "Training Points")
        result = wfs.publish()  # Publishes all layers to WFS
    """
    
    def __init__(self, 
                 fastapi_url: str = "http://fastapi:8000",
                 wfs_base_url: str = "http://localhost:8001"):
        """
        Initialize WFS Manager
        
        Args:
            fastapi_url: Internal FastAPI URL for Docker communication
            wfs_base_url: Public WFS service URL for external access
        """
        self.fastapi_url = fastapi_url.rstrip('/')
        self.wfs_base_url = wfs_base_url.rstrip('/')
        
        # Internal storage for layers
        self._layers = {}  # {layer_name: {'vector': ee.FeatureCollection/Geometry, 'name': str}}
        
        logger.info(f"WFSManager initialized:")
        logger.info(f"  FastAPI URL: {self.fastapi_url}")
        logger.info(f"  WFS Base URL: {self.wfs_base_url}")
    
    def addLayer(self, 
                 vector_data: Union[ee.FeatureCollection, ee.Geometry], 
                 layer_name: str) -> 'WFSManager':
        """
        Add a vector layer to the WFS manager (similar to Map.addLayer())
        
        Args:
            vector_data: Earth Engine FeatureCollection or Geometry object
            layer_name: Name for the layer (will be used as /fc/{layer_name})
            
        Returns:
            Self for method chaining
        """
        if not isinstance(vector_data, (ee.FeatureCollection, ee.Geometry)):
            raise ValueError("vector_data must be an ee.FeatureCollection or ee.Geometry object")
        
        if not layer_name or not isinstance(layer_name, str):
            raise ValueError("layer_name must be a non-empty string")
        
        # Clean layer name for URL usage
        clean_layer_name = layer_name.lower().replace(' ', '_').replace('-', '_')
        
        # Store layer information
        self._layers[clean_layer_name] = {
            'vector_data': vector_data,
            'name': layer_name,
            'clean_name': clean_layer_name
        }
        
        logger.info(f"Added vector layer: {layer_name} -> {clean_layer_name}")
        return self
    
    def removeLayer(self, layer_name: str) -> 'WFSManager':
        """
        Remove a layer from the manager
        
        Args:
            layer_name: Name of the layer to remove
            
        Returns:
            Self for method chaining
        """
        clean_name = layer_name.lower().replace(' ', '_').replace('-', '_')
        
        if clean_name in self._layers:
            del self._layers[clean_name]
            logger.info(f"Removed vector layer: {layer_name}")
        else:
            logger.warning(f"Vector layer not found: {layer_name}")
        
        return self
    
    def listLayers(self) -> Dict[str, Any]:
        """
        List all layers in the manager
        
        Returns:
            Dictionary of layer information
        """
        return {
            name: {
                'name': info['name'],
                'clean_name': info['clean_name'],
                'type': 'FeatureCollection' if isinstance(info['vector_data'], ee.FeatureCollection) else 'Geometry',
                'fc_url': f"{self.fastapi_url}/fc/{name}",
                'wfs_url': f"{self.wfs_base_url}/wfs?service=WFS&version=1.1.0&request=GetFeature&typename={name}"
            }
            for name, info in self._layers.items()
        }
    
    def _convert_to_geojson(self, vector_data: Union[ee.FeatureCollection, ee.Geometry]) -> Dict[str, Any]:
        """
        Convert Earth Engine vector data to GeoJSON
        """
        try:
            if isinstance(vector_data, ee.Geometry):
                # Convert geometry to FeatureCollection for GeoJSON output
                fc = ee.FeatureCollection([ee.Feature(vector_data)])
            else:
                fc = vector_data
            
            geojson = fc.getInfo()
            return geojson
            
        except Exception as e:
            logger.error(f"Failed to convert vector data to GeoJSON: {e}")
            raise ValueError(f"Could not convert vector data to GeoJSON: {e}")
    
    def _publish_layer(self, layer_name: str, layer_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Publish a single layer to the WFS service
        """
        try:
            # Convert to GeoJSON
            geojson_data = self._convert_to_geojson(layer_info['vector_data'])
            
            # Push to FastAPI /fc/ endpoint
            fc_url = f"{self.fastapi_url}/fc/{layer_name}"
            
            response = requests.post(
                fc_url,
                json=geojson_data,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                result = response.json()
                logger.info(f"✅ Published layer '{layer_name}': {result.get('message', 'Success')}")
                
                return {
                    'status': 'success',
                    'layer_name': layer_name,
                    'fc_url': fc_url,
                    'wfs_url': f"{self.wfs_base_url}/wfs?service=WFS&version=1.1.0&request=GetFeature&typename={layer_name}",
                    'feature_count': result.get('count', 'Unknown'),
                    'response': result
                }
            else:
                error_msg = f"Failed to publish layer '{layer_name}': {response.status_code} - {response.text}"
                logger.error(error_msg)
                return {
                    'status': 'error',
                    'layer_name': layer_name,
                    'error': error_msg
                }
                
        except Exception as e:
            error_msg = f"Error publishing layer '{layer_name}': {e}"
            logger.error(error_msg)
            return {
                'status': 'error',
                'layer_name': layer_name,
                'error': error_msg
            }
    
    def publish(self) -> Dict[str, Any]:
        """
        Publish all layers to WFS service
        
        Returns:
            Dictionary with publishing results
        """
        if not self._layers:
            raise ValueError("No layers to publish. Use addLayer() to add layers first.")
        
        logger.info(f"Publishing {len(self._layers)} vector layers to WFS...")
        
        results = {
            'status': 'success',
            'total_layers': len(self._layers),
            'successful_layers': 0,
            'failed_layers': 0,
            'layers': {},
            'service_urls': {
                'wfs_capabilities': f"{self.wfs_base_url}/wfs?service=WFS&version=1.1.0&request=GetCapabilities",
                'wfs_base': f"{self.wfs_base_url}/wfs"
            }
        }
        
        # Publish each layer
        for layer_name, layer_info in self._layers.items():
            layer_result = self._publish_layer(layer_name, layer_info)
            results['layers'][layer_name] = layer_result
            
            if layer_result['status'] == 'success':
                results['successful_layers'] += 1
            else:
                results['failed_layers'] += 1
        
        # Update overall status
        if results['failed_layers'] > 0:
            results['status'] = 'partial_success' if results['successful_layers'] > 0 else 'error'
        
        logger.info(f"WFS publishing completed: {results['status']}")
        logger.info(f"  Successful: {results['successful_layers']}")
        logger.info(f"  Failed: {results['failed_layers']}")
        
        return results
    
    def clear(self) -> 'WFSManager':
        """
        Clear all layers from the manager
        
        Returns:
            Self for method chaining
        """
        self._layers.clear()
        logger.info("Cleared all vector layers from WFS manager")
        return self
    
    def __len__(self) -> int:
        """Return number of layers"""
        return len(self._layers)
    
    def __str__(self) -> str:
        """String representation"""
        return f"WFSManager(layers={len(self._layers)}, fastapi={self.fastapi_url})"
    
    def __repr__(self) -> str:
        """Detailed representation"""
        layers_info = [f"{name}: {info['name']}" for name, info in self._layers.items()]
        return f"WFSManager(layers=[{', '.join(layers_info)}], fastapi={self.fastapi_url})"


# Convenience functions for quick usage
def create_wfs_manager(fastapi_url: str = "http://fastapi:8000", 
                      wfs_base_url: str = "http://localhost:8001") -> WFSManager:
    """
    Create a new WFSManager instance
    
    Args:
        fastapi_url: Internal FastAPI URL for Docker communication
        wfs_base_url: Public WFS service URL for external access
        
    Returns:
        WFSManager instance
    """
    return WFSManager(fastapi_url=fastapi_url, wfs_base_url=wfs_base_url)


def quick_publish_vector(vector_data: Union[ee.FeatureCollection, ee.Geometry], 
                        layer_name: str,
                        fastapi_url: str = "http://fastapi:8000",
                        wfs_base_url: str = "http://localhost:8001") -> Dict[str, Any]:
    """
    Quick publish a single vector layer to WFS
    
    Args:
        vector_data: Earth Engine FeatureCollection or Geometry object
        layer_name: Name for the layer
        fastapi_url: Internal FastAPI URL for Docker communication
        wfs_base_url: Public WFS service URL for external access
        
    Returns:
        Publishing results
    """
    wfs = WFSManager(fastapi_url=fastapi_url, wfs_base_url=wfs_base_url)
    wfs.addLayer(vector_data, layer_name)
    return wfs.publish()
