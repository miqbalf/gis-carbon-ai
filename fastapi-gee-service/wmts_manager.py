"""
WMTS Manager - Simplified GEE Layer Management for MapStore Integration

This module provides a simple, Map.addLayer()-like interface for adding GEE layers
to WMTS services without the complexity of managing map_layers dictionaries.
"""

import ee
import logging
from typing import Dict, Any, Optional, Union
from datetime import datetime
from gee_lib.osi.utils import generate_map_id
from gee_integration import process_gee_to_mapstore
from gee_lib.osi.utils import process_aoi_geometry

logger = logging.getLogger(__name__)

class WMTSManager:
    """
    Simplified WMTS Manager that provides Map.addLayer()-like functionality
    for adding GEE layers to MapStore via WMTS services.
    
    Usage:
        wmts = WMTSManager(project_name="My Analysis", aoi=AOI_geometry)
        wmts.addLayer(image_mosaick, vis_params, "True Color")
        wmts.addLayer(FCD1_1, fcd_visparams, "Forest Cover Density")
        result = wmts.publish()  # Publishes all layers to WMTS
    """
    
    def __init__(self, 
                 project_name: str = "GEE Analysis",
                 aoi: Optional[ee.Geometry] = None,
                 fastapi_url: Optional[str] = None,
                 clear_cache_first: bool = True):
        """
        Initialize WMTS Manager
        
        Args:
            project_name: Human-readable project name
            aoi: Earth Engine Geometry object for AOI
            fastapi_url: FastAPI service URL (auto-detected if None)
            clear_cache_first: Whether to clear cache before publishing
        """
        self.project_name = project_name
        self.aoi = aoi
        self.fastapi_url = fastapi_url
        self.clear_cache_first = clear_cache_first
        
        # Internal storage for layers
        self._layers = {}  # {layer_name: {'image': ee.Image, 'vis': dict, 'name': str}}
        self._aoi_info = None
        
        logger.info(f"WMTSManager initialized for project: {project_name}")
    
    def addLayer(self, 
                 image: ee.Image, 
                 vis_params: Dict[str, Any], 
                 layer_name: str) -> 'WMTSManager':
        """
        Add a GEE layer to the WMTS manager (similar to Map.addLayer())
        
        Args:
            image: Earth Engine Image object
            vis_params: Visualization parameters (bands, min, max, palette, etc.)
            layer_name: Name for the layer
            
        Returns:
            Self for method chaining
        """
        if not isinstance(image, ee.Image):
            raise ValueError("image must be an ee.Image object")
        
        if not isinstance(vis_params, dict):
            raise ValueError("vis_params must be a dictionary")
        
        if not layer_name or not isinstance(layer_name, str):
            raise ValueError("layer_name must be a non-empty string")
        
        # Store layer information
        self._layers[layer_name] = {
            'image': image,
            'vis_params': vis_params,
            'name': layer_name
        }
        
        logger.info(f"Added layer: {layer_name}")
        return self
    
    def removeLayer(self, layer_name: str) -> 'WMTSManager':
        """
        Remove a layer from the manager
        
        Args:
            layer_name: Name of the layer to remove
            
        Returns:
            Self for method chaining
        """
        if layer_name in self._layers:
            del self._layers[layer_name]
            logger.info(f"Removed layer: {layer_name}")
        else:
            logger.warning(f"Layer not found: {layer_name}")
        
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
                'vis_params': info['vis_params'],
                'has_image': info['image'] is not None
            }
            for name, info in self._layers.items()
        }
    
    def _prepare_aoi_info(self) -> Dict[str, Any]:
        """
        Prepare AOI information from the geometry
        """
        if self._aoi_info is not None:
            return self._aoi_info
        
        if self.aoi is None:
            logger.warning("No AOI provided, using default bounds")
            return {
                'bbox': {'minx': -180, 'miny': -90, 'maxx': 180, 'maxy': 90},
                'center': [0, 0]
            }
        
        try:
            self._aoi_info = process_aoi_geometry(self.aoi)
            logger.info(f"AOI processed: {self._aoi_info['bbox']}")
            return self._aoi_info
        except Exception as e:
            logger.error(f"Failed to process AOI: {e}")
            return {
                'bbox': {'minx': -180, 'miny': -90, 'maxx': 180, 'maxy': 90},
                'center': [0, 0]
            }
    
    def _generate_map_layers(self) -> Dict[str, Any]:
        """
        Generate map layers from stored layer information
        """
        if not self._layers:
            raise ValueError("No layers added. Use addLayer() to add layers first.")
        
        # Prepare data for generate_map_id
        layername_visparam = {}
        layername_image = {}
        
        for layer_name, layer_info in self._layers.items():
            layername_visparam[layer_name] = layer_info['vis_params']
            layername_image[layer_name] = layer_info['image']
        
        # Generate map IDs
        logger.info(f"Generating map IDs for {len(self._layers)} layers...")
        result = generate_map_id(layername_visparam, layername_image)
        
        return result['map_layers']
    
    def publish(self) -> Dict[str, Any]:
        """
        Publish all layers to WMTS service
        
        Returns:
            Dictionary with publishing results
        """
        if not self._layers:
            raise ValueError("No layers to publish. Use addLayer() to add layers first.")
        
        try:
            # Generate map layers
            map_layers = self._generate_map_layers()
            
            # Prepare AOI info
            aoi_info = self._prepare_aoi_info()
            
            # Publish to WMTS
            logger.info(f"Publishing {len(map_layers)} layers to WMTS...")
            result = process_gee_to_mapstore(
                map_layers=map_layers,
                project_name=self.project_name,
                aoi_info=aoi_info,
                fastapi_url=self.fastapi_url,
                clear_cache_first=self.clear_cache_first
            )
            
            logger.info(f"WMTS publishing completed: {result['status']}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to publish layers: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'project_name': self.project_name,
                'layers_count': len(self._layers)
            }
    
    def clear(self) -> 'WMTSManager':
        """
        Clear all layers from the manager
        
        Returns:
            Self for method chaining
        """
        self._layers.clear()
        self._aoi_info = None
        logger.info("Cleared all layers from WMTS manager")
        return self
    
    def __len__(self) -> int:
        """Return number of layers"""
        return len(self._layers)
    
    def __str__(self) -> str:
        """String representation"""
        return f"WMTSManager(project='{self.project_name}', layers={len(self._layers)})"
    
    def __repr__(self) -> str:
        """Detailed representation"""
        layers_info = [f"{name}: {info['name']}" for name, info in self._layers.items()]
        return f"WMTSManager(project='{self.project_name}', layers=[{', '.join(layers_info)}])"


# Convenience functions for quick usage
def create_wmts_manager(project_name: str = "GEE Analysis", 
                       aoi: Optional[ee.Geometry] = None) -> WMTSManager:
    """
    Create a new WMTSManager instance
    
    Args:
        project_name: Human-readable project name
        aoi: Earth Engine Geometry object for AOI
        
    Returns:
        WMTSManager instance
    """
    return WMTSManager(project_name=project_name, aoi=aoi)


def quick_publish(image: ee.Image, 
                 vis_params: Dict[str, Any], 
                 layer_name: str,
                 project_name: str = "GEE Analysis",
                 aoi: Optional[ee.Geometry] = None) -> Dict[str, Any]:
    """
    Quick publish a single layer to WMTS
    
    Args:
        image: Earth Engine Image object
        vis_params: Visualization parameters
        layer_name: Name for the layer
        project_name: Project name
        aoi: AOI geometry
        
    Returns:
        Publishing results
    """
    wmts = WMTSManager(project_name=project_name, aoi=aoi)
    wmts.addLayer(image, vis_params, layer_name)
    return wmts.publish()
