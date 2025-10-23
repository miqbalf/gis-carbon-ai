#!/usr/bin/env python3
"""
GEE Integration Library for FastAPI
This module provides a clean interface for integrating GEE analysis results
with FastAPI and MapStore services. Works in both notebook and non-notebook environments.
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

def _detect_environment():
    """
    Detect the current environment and return appropriate default URLs.
    
    Returns:
        tuple: (fastapi_url, mapstore_config_path)
    """
    # Check if we're in a Docker container (notebook environment)
    if os.path.exists('/usr/src/app'):
        # Docker/notebook environment (Jupyter container)
        fastapi_url = "http://fastapi:8000"
        mapstore_config_path = "/usr/src/app/mapstore/config/localConfig.json"
    elif os.path.exists('/app'):
        # Docker/FastAPI environment
        fastapi_url = "http://fastapi:8000"
        mapstore_config_path = "/app/mapstore/config/localConfig.json"
    else:
        # Local development environment
        fastapi_url = "http://localhost:8001"
        mapstore_config_path = "./mapstore/config/localConfig.json"
    
    return fastapi_url, mapstore_config_path

class GEEIntegrationManager:
    """
    Manages the complete integration of GEE analysis results with FastAPI and MapStore
    """
    
    def __init__(self, 
                 fastapi_url: Optional[str] = None,
                 mapstore_config_path: Optional[str] = None):
        """
        Initialize the GEE Integration Manager
        
        Args:
            fastapi_url: URL of the FastAPI service (auto-detected if None)
            mapstore_config_path: Path to MapStore localConfig.json (auto-detected if None)
        """
        # Auto-detect environment if not provided
        if fastapi_url is None or mapstore_config_path is None:
            detected_fastapi_url, detected_mapstore_path = _detect_environment()
            self.fastapi_url = fastapi_url or detected_fastapi_url
            self.mapstore_config_path = mapstore_config_path or detected_mapstore_path
        else:
            self.fastapi_url = fastapi_url
            self.mapstore_config_path = mapstore_config_path
        
        logger.info(f"GEE Integration Manager initialized:")
        logger.info(f"  FastAPI URL: {self.fastapi_url}")
        logger.info(f"  MapStore Config: {self.mapstore_config_path}")
        
    def process_gee_analysis(self, 
                           map_layers: Dict[str, Any],
                           project_name: str = "GEE Analysis",
                           aoi_info: Optional[Dict[str, Any]] = None,
                           clear_cache_first: bool = True) -> Dict[str, Any]:
        """
        Complete processing of GEE analysis results
        
        Args:
            map_layers: Dictionary of GEE map layers with tile URLs
            project_name: Human-readable project name
            aoi_info: Area of interest information
            clear_cache_first: Whether to clear cache before processing (default: True)
            
        Returns:
            Dictionary with processing results and service URLs
        """
        try:
            logger.info(f"Processing GEE analysis: {project_name}")
            
            # Step 0: Clear cache first to ensure fresh data
            if clear_cache_first:
                logger.info("🧹 Clearing duplicate projects before processing new analysis...")
                cache_result = self.clear_duplicate_projects(project_name, aoi_info)
                if cache_result.get("status") == "success":
                    cleared_count = cache_result.get('cleared_count', 0)
                    kept_count = len(cache_result.get('kept_projects', []))
                    logger.info(f"✅ Cache cleared: {cleared_count} duplicate entries, kept {kept_count} unique projects")
                else:
                    logger.warning(f"⚠️ Duplicate clearing failed: {cache_result.get('error', 'Unknown error')}")
            
            # Step 1: Generate project ID based on project name
            # Clean project name for use in ID (remove spaces, special chars, make lowercase)
            clean_project_name = project_name.lower().replace(' ', '_').replace('-', '_')
            # Remove any special characters except underscores
            import re
            clean_project_name = re.sub(r'[^a-z0-9_]', '', clean_project_name)
            project_id = f"{clean_project_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Step 2: Prepare analysis data
            analysis_data = self._prepare_analysis_data(
                project_id, project_name, map_layers, aoi_info
            )
            
            # Step 3: Register with FastAPI
            fastapi_result = self._register_with_fastapi(analysis_data)
            
            # Step 4: Create FastAPI proxy URLs for GEE tiles
            proxy_result = self._create_fastapi_proxy_urls(analysis_data)
            
            # Step 5: Update MapStore WMTS configuration
            wmts_result = self._update_mapstore_wmts(analysis_data)
            
            # Step 6: Return comprehensive results
            return {
                "status": "success",
                "project_id": project_id,
                "project_name": project_name,
                "fastapi_registration": fastapi_result,
                "proxy_urls_creation": proxy_result,
                "wmts_configuration": wmts_result,
                "service_urls": {
                    "fastapi_layers": f"{self.fastapi_url}/layers/{project_id}",
                    "fastapi_tiles": f"{self.fastapi_url}/tiles/{project_id}",
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
            
            # Add FastAPI proxy URL for each layer
            layers_data[layer_name]['fastapi_proxy_url'] = f"{self.fastapi_url}/tiles/{project_id}/{layer_name}/{{z}}/{{x}}/{{y}}"
        
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
    
    def _create_fastapi_proxy_urls(self, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create FastAPI proxy URLs for GEE tiles"""
        try:
            project_id = analysis_data['project_id']
            layers = analysis_data['layers']
            
            logger.info(f"Creating FastAPI proxy URLs for project: {project_id}")
            
            # Create proxy URLs for each layer
            proxy_urls = {}
            for layer_name, layer_info in layers.items():
                # Create the FastAPI proxy URL format
                proxy_url = f"{self.fastapi_url}/tiles/{project_id}/{layer_name}/{{z}}/{{x}}/{{y}}"
                proxy_urls[layer_name] = {
                    'proxy_url': proxy_url,
                    'original_url': layer_info.get('tile_url', ''),
                    'layer_name': layer_name,
                    'description': layer_info.get('description', '')
                }
            
            logger.info(f"✅ Created {len(proxy_urls)} FastAPI proxy URLs")
            
            return {
                "status": "success",
                "message": f"Created {len(proxy_urls)} proxy URLs",
                "proxy_urls": proxy_urls,
                "layers_count": len(proxy_urls)
            }
            
        except Exception as e:
            error_msg = f"Error creating FastAPI proxy URLs: {e}"
            logger.error(error_msg)
            return {
                "status": "error",
                "message": error_msg
            }
    
    def _update_mapstore_wmts(self, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update MapStore WMTS configuration"""
        try:
            logger.info(f"Updating MapStore WMTS: {analysis_data['project_id']}")
            
            # Use the organized WMTS utilities
            from gee_utils import GEEIntegrationUtils
            wmts_utils = GEEIntegrationUtils(self.fastapi_url)
            
            # Force a comprehensive refresh to clear old layers and update with new ones
            logger.info("🔄 Forcing comprehensive WMTS refresh...")
            wmts_result = wmts_utils.comprehensive_refresh()
            
            if wmts_result.get("overall_status") == "success":
                logger.info("✅ MapStore WMTS configuration updated")
                logger.info(f"   New layers found: {len(wmts_result.get('layers_found', []))}")
                return {
                    "status": "success",
                    "message": "WMTS configuration updated successfully",
                    "service_id": "GEE_analysis_WMTS_layers",
                    "layers_available": wmts_result.get("layers_found", []),
                    "layers_count": len(wmts_result.get("layers_found", []))
                }
            else:
                error_msg = f"Failed to update WMTS configuration: {wmts_result.get('error', 'Unknown error')}"
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
    
    def clear_cache(self, cache_type: str = "all") -> Dict[str, Any]:
        """
        Clear Redis cache entries.
        
        Args:
            cache_type: Type of cache to clear (all, tiles, catalogs, projects, layers)
        
        Returns:
            Dictionary with clearing results
        """
        try:
            # Try to import cache_manager, but don't fail if it's not available
            try:
                from cache_manager import CacheManager
                manager = CacheManager()
                result = manager.clear_cache(cache_type)
                
                if result["status"] == "success":
                    logger.info(f"✅ Cache cleared successfully: {result['cleared_count']} entries")
                else:
                    logger.error(f"❌ Cache clearing failed: {result.get('error')}")
                
                return result
            except ImportError as import_error:
                logger.warning(f"⚠️ Cache manager not available: {import_error}")
                return {
                    "status": "warning",
                    "message": "Cache manager not available - skipping cache clear",
                    "cleared_count": 0
                }
            
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def clear_duplicate_projects(self, project_name: str, aoi_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clear only duplicate projects based on project name and AOI analysis parameters.
        This prevents clearing all data and only removes true duplicates.
        
        Args:
            project_name: Name of the new project being processed
            aoi_info: AOI information for the new project
        
        Returns:
            Dictionary with clearing results
        """
        try:
            # Try to import cache_manager, but don't fail if it's not available
            try:
                from cache_manager import CacheManager
                manager = CacheManager()
                result = manager.clear_duplicate_projects(project_name, aoi_info)
                
                if result["status"] == "success":
                    cleared_count = result.get('cleared_count', 0)
                    kept_count = len(result.get('kept_projects', []))
                    logger.info(f"✅ Duplicate clearing successful: {cleared_count} duplicates cleared, {kept_count} unique projects kept")
                else:
                    logger.error(f"❌ Duplicate clearing failed: {result.get('error')}")
                
                return result
            except ImportError as import_error:
                logger.warning(f"⚠️ Cache manager not available: {import_error}")
                return {
                    "status": "error",
                    "error": str(import_error),
                    "message": "Cache manager not available - skipping duplicate clear",
                    "cleared_count": 0
                }
            
        except Exception as e:
            logger.error(f"Error clearing duplicate projects: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def get_cache_status(self) -> Dict[str, Any]:
        """
        Get current cache status and statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        try:
            try:
                from cache_manager import CacheManager
                manager = CacheManager()
                return manager.get_cache_status()
            except ImportError as import_error:
                logger.warning(f"⚠️ Cache manager not available: {import_error}")
                return {
                    "status": "warning",
                    "message": "Cache manager not available",
                    "cache_available": False
                }
            
        except Exception as e:
            logger.error(f"Error getting cache status: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get current status of all services"""
        try:
            # Get FastAPI status
            fastapi_status = self._get_fastapi_status()
            
            # Get WMTS status
            wmts_status = self._get_wmts_status()
            
            # Get cache status
            cache_status = self.get_cache_status()
            
            return {
                "fastapi": fastapi_status,
                "wmts": wmts_status,
                "cache": cache_status,
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
            from gee_utils import GEEIntegrationUtils
            wmts_utils = GEEIntegrationUtils(self.fastapi_url)
            
            # Get current WMTS layers
            layers = wmts_utils.get_wmts_layers()
            
            if layers:
                return {
                    "status": "active",
                    "service_id": "GEE_analysis_WMTS_layers",
                    "layers_count": len(layers),
                    "layers_available": layers
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
                          fastapi_url: Optional[str] = None,
                          clear_cache_first: bool = True) -> Dict[str, Any]:
    """
    Convenience function to process GEE analysis results to MapStore
    
    Args:
        map_layers: Dictionary of GEE map layers with tile URLs
        project_name: Human-readable project name
        aoi_info: Area of interest information
        fastapi_url: URL of the FastAPI service (auto-detected if None)
        clear_cache_first: Whether to clear cache before processing (default: True)
        
    Returns:
        Dictionary with processing results
    """
    manager = GEEIntegrationManager(fastapi_url=fastapi_url)
    return manager.process_gee_analysis(map_layers, project_name, aoi_info, clear_cache_first)

# Backward compatibility aliases
process_gee_to_mapstore_notebook = process_gee_to_mapstore
GEENotebookIntegrationManager = GEEIntegrationManager

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
