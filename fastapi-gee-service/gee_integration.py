#!/usr/bin/env python3
"""
GEE Integration Library for FastAPI
This module provides a clean interface for integrating GEE analysis results
with FastAPI and MapStore services.
"""

import json
import requests
import os
import sys
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GEEIntegrationManager:
    """
    Manages the complete integration of GEE analysis results with FastAPI and MapStore
    """
    
    def __init__(self, 
                 fastapi_url: str = "http://localhost:8001",
                 mapstore_config_path: str = "/usr/src/app/mapstore/config/localConfig.json"):
        """
        Initialize the GEE Integration Manager
        
        Args:
            fastapi_url: URL of the FastAPI service
            mapstore_config_path: Path to MapStore localConfig.json
        """
        self.fastapi_url = fastapi_url
        self.mapstore_config_path = mapstore_config_path
        
    def process_gee_analysis(self, 
                           map_layers: Dict[str, Any],
                           project_name: str = "GEE Analysis",
                           aoi_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Complete processing of GEE analysis results
        
        Args:
            map_layers: Dictionary of GEE map layers with tile URLs
            project_name: Human-readable project name
            aoi_info: Area of interest information
            
        Returns:
            Dictionary with processing results and service URLs
        """
        try:
            logger.info(f"Processing GEE analysis: {project_name}")
            
            # Step 1: Generate project ID
            project_id = f"sentinel_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Step 2: Prepare analysis data
            analysis_data = self._prepare_analysis_data(
                project_id, project_name, map_layers, aoi_info
            )
            
            # Step 3: Register with FastAPI
            fastapi_result = self._register_with_fastapi(analysis_data)
            
            # Step 4: Update MapStore WMTS configuration
            wmts_result = self._update_mapstore_wmts(analysis_data)
            
            # Step 5: Return comprehensive results
            return {
                "status": "success",
                "project_id": project_id,
                "project_name": project_name,
                "fastapi_registration": fastapi_result,
                "wmts_configuration": wmts_result,
                "service_urls": {
                    "fastapi_layers": f"{self.fastapi_url}/layers/{project_id}",
                    "wmts_service": f"{self.fastapi_url}/wmts",
                    "mapstore_catalog": "http://localhost:8082/mapstore"
                },
                "available_layers": list(map_layers.keys()),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error processing GEE analysis: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _prepare_analysis_data(self, 
                              project_id: str, 
                              project_name: str,
                              map_layers: Dict[str, Any],
                              aoi_info: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Prepare analysis data for FastAPI registration"""
        
        # Default AOI if not provided
        if not aoi_info:
            aoi_info = {
                'bbox': {'minx': 109.5, 'miny': -1.5, 'maxx': 110.5, 'maxy': -0.5},
                'center': [110.0, -1.0],
                'coordinates': [[109.5, -1.5], [110.5, -1.5], [110.5, -0.5], [109.5, -0.5], [109.5, -1.5]]
            }
        
        # Prepare layer data
        layers_data = {}
        for layer_name, layer_info in map_layers.items():
            if isinstance(layer_info, dict) and 'tile_url' in layer_info:
                # Already formatted layer info
                layers_data[layer_name] = layer_info
            else:
                # Simple tile URL string - create basic layer info
                layers_data[layer_name] = {
                    'name': layer_name.replace('_', ' ').title(),
                    'description': f'{layer_name.upper()} visualization from GEE analysis',
                    'tile_url': str(layer_info),
                    'vis_params': {}
                }
        
        return {
            'project_id': project_id,
            'project_name': project_name,
            'analysis_info': {
                'aoi': aoi_info,
                'generated_at': datetime.now().isoformat()
            },
            'layers': layers_data
        }
    
    def _register_with_fastapi(self, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """Register analysis data with FastAPI service"""
        try:
            logger.info(f"Registering with FastAPI: {analysis_data['project_id']}")
            
            response = requests.post(
                f"{self.fastapi_url}/catalog/update",
                json=analysis_data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"✅ FastAPI registration successful: {result.get('message')}")
                return {
                    "status": "success",
                    "message": result.get('message'),
                    "layers_count": result.get('layers_count')
                }
            else:
                error_msg = f"FastAPI registration failed: {response.status_code}"
                logger.error(error_msg)
                return {
                    "status": "error",
                    "message": error_msg,
                    "response": response.text
                }
                
        except Exception as e:
            error_msg = f"Error registering with FastAPI: {e}"
            logger.error(error_msg)
            return {
                "status": "error",
                "message": error_msg
            }
    
    def _update_mapstore_wmts(self, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update MapStore WMTS configuration"""
        try:
            logger.info(f"Updating MapStore WMTS: {analysis_data['project_id']}")
            
            # Import WMTS config updater
            sys.path.append('/usr/src/app/notebooks')
            from wmts_config_updater import update_mapstore_wmts_config
            
            # Update WMTS configuration
            success = update_mapstore_wmts_config(
                project_id=analysis_data['project_id'],
                project_name=analysis_data['project_name'],
                aoi_info=analysis_data['analysis_info']['aoi']
            )
            
            if success:
                logger.info("✅ MapStore WMTS configuration updated")
                return {
                    "status": "success",
                    "message": "WMTS configuration updated successfully",
                    "service_id": "GEE_analysis_WMTS_layers"
                }
            else:
                error_msg = "Failed to update WMTS configuration"
                logger.error(error_msg)
                return {
                    "status": "error",
                    "message": error_msg
                }
                
        except Exception as e:
            error_msg = f"Error updating WMTS configuration: {e}"
            logger.error(error_msg)
            return {
                "status": "error",
                "message": error_msg
            }
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get current status of all services"""
        try:
            # Get FastAPI status
            fastapi_status = self._get_fastapi_status()
            
            # Get WMTS status
            wmts_status = self._get_wmts_status()
            
            return {
                "fastapi": fastapi_status,
                "wmts": wmts_status,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting service status: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _get_fastapi_status(self) -> Dict[str, Any]:
        """Get FastAPI service status"""
        try:
            response = requests.get(f"{self.fastapi_url}/health", timeout=5)
            if response.status_code == 200:
                return {
                    "status": "healthy",
                    "url": self.fastapi_url
                }
            else:
                return {
                    "status": "unhealthy",
                    "url": self.fastapi_url,
                    "error": f"HTTP {response.status_code}"
                }
        except Exception as e:
            return {
                "status": "unreachable",
                "url": self.fastapi_url,
                "error": str(e)
            }
    
    def _get_wmts_status(self) -> Dict[str, Any]:
        """Get WMTS service status"""
        try:
            sys.path.append('/usr/src/app/notebooks')
            from wmts_config_updater import get_current_wmts_status
            
            status = get_current_wmts_status()
            if status:
                return {
                    "status": "active",
                    "service_id": status['service_id'],
                    "project_name": status['project_name'],
                    "layers_count": len(status['layers_available'])
                }
            else:
                return {
                    "status": "inactive",
                    "message": "No active WMTS service"
                }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }

def process_gee_to_mapstore(map_layers: Dict[str, Any],
                          project_name: str = "GEE Analysis",
                          aoi_info: Optional[Dict[str, Any]] = None,
                          fastapi_url: str = "http://localhost:8001") -> Dict[str, Any]:
    """
    Convenience function to process GEE analysis results to MapStore
    
    Args:
        map_layers: Dictionary of GEE map layers with tile URLs
        project_name: Human-readable project name
        aoi_info: Area of interest information
        fastapi_url: URL of the FastAPI service
        
    Returns:
        Dictionary with processing results
    """
    manager = GEEIntegrationManager(fastapi_url=fastapi_url)
    return manager.process_gee_analysis(map_layers, project_name, aoi_info)

# Example usage
if __name__ == "__main__":
    # Example map layers from GEE analysis
    example_map_layers = {
        'true_color': {
            'tile_url': 'https://earthengine.googleapis.com/v1/projects/earthengine-legacy/maps/example/tiles/{z}/{x}/{y}',
            'name': 'True Color',
            'description': 'True Color RGB visualization',
            'vis_params': {'bands': ['red', 'green', 'blue'], 'min': 0, 'max': 0.3}
        },
        'ndvi': {
            'tile_url': 'https://earthengine.googleapis.com/v1/projects/earthengine-legacy/maps/example2/tiles/{z}/{x}/{y}',
            'name': 'NDVI',
            'description': 'Normalized Difference Vegetation Index',
            'vis_params': {'min': -0.2, 'max': 0.8, 'palette': ['red', 'yellow', 'green']}
        }
    }
    
    # Process the analysis
    result = process_gee_to_mapstore(
        map_layers=example_map_layers,
        project_name="Example GEE Analysis",
        aoi_info={
            'bbox': {'minx': 109.5, 'miny': -1.5, 'maxx': 110.5, 'maxy': -0.5},
            'center': [110.0, -1.0]
        }
    )
    
    print(f"Processing result: {result['status']}")
    if result['status'] == 'success':
        print(f"Project ID: {result['project_id']}")
        print(f"Available layers: {result['available_layers']}")
