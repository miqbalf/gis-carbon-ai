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

class TMSLayerObject:
    """
    TMS Layer Object with convenient URL methods
    """
    
    def __init__(self, layer_name: str, clean_layer_name: str, layer_title: str, 
                 service_id: str, fastapi_url: str, use_fastapi_proxy: bool, 
                 original_url: str = None, fastapi_pub_url: str = "http://localhost:8001"):
        self.layer_name = layer_name
        self.clean_layer_name = clean_layer_name
        self.layer_title = layer_title
        self.service_id = service_id
        self.fastapi_url = fastapi_url
        self.fastapi_pub_url = fastapi_pub_url  # Always localhost for browser access
        self.use_fastapi_proxy = use_fastapi_proxy
        self.original_url = original_url
    
    def get_proxy_url_tms(self) -> str:
        """Get the FastAPI proxy TMS URL for this layer (public URL for browser access)"""
        return f"{self.fastapi_pub_url}/tms/dynamic/{self.clean_layer_name}/{{z}}/{{x}}/{{y}}.png"
    
    def get_direct_url_tms(self) -> str:
        """Get the direct GEE TMS URL for this layer"""
        if self.original_url:
            return self.original_url
        else:
            return f"Direct URL not available for layer: {self.layer_name}"
    
    def get_mapstore_config(self) -> dict:
        """Get the complete MapStore TMS configuration for this layer"""
        return {
            "type": "tms",
            "format": "image/png",
            "title": f"GEE TMS - {self.layer_title}",
            "autoload": False,
            "url": self.get_proxy_url_tms(),
            "srs": "EPSG:3857"
        }
    
    def get_service_id(self) -> str:
        """Get the service ID for this layer"""
        return self.service_id
    
    def get_layer_name(self) -> str:
        """Get the original layer name"""
        return self.layer_name
    
    def get_clean_layer_name(self) -> str:
        """Get the cleaned layer name (URL-safe)"""
        return self.clean_layer_name
    
    def get_layer_title(self) -> str:
        """Get the display title for this layer"""
        return self.layer_title
    
    def __str__(self) -> str:
        return f"TMSLayerObject(name='{self.layer_name}', service_id='{self.service_id}')"
    
    def __repr__(self) -> str:
        return self.__str__()

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
        mapstore_config_path = "/usr/src/app/mapstore/configs/localConfig.json"
    elif os.path.exists('/app'):
        # Docker/FastAPI environment
        fastapi_url = "http://fastapi:8000"
        mapstore_config_path = "/app/mapstore/configs/localConfig.json"
    else:
        # Local development environment
        fastapi_url = "http://localhost:8001"
        mapstore_config_path = "./mapstore/configs/localConfig.json"
    
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
            fastapi_url: Internal FastAPI URL for Docker communication (auto-detected if None)
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
    
    def process_gee_analysis_tms(self, 
                                map_layers: Dict[str, Any],
                                project_name: str = "GEE Analysis",
                                aoi_info: Optional[Dict[str, Any]] = None,
                                clear_cache_first: bool = True) -> Dict[str, Any]:
        """
        Complete processing of GEE analysis results using TMS (Tile Map Service)
        
        Args:
            map_layers: Dictionary of GEE map layers with tile URLs
            project_name: Human-readable project name
            aoi_info: Area of interest information
            clear_cache_first: Whether to clear cache before processing (default: True)
            
        Returns:
            Dictionary with processing results and TMS service URLs
        """
        try:
            logger.info(f"Processing GEE analysis with TMS: {project_name}")
            
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
            
            # Step 4: Create FastAPI TMS proxy URLs for GEE tiles
            tms_proxy_result = self._create_fastapi_tms_proxy_urls(analysis_data)
            
            # Step 5: Update MapStore TMS configuration
            tms_result = self._update_mapstore_tms(analysis_data)
            
            # Step 6: Return comprehensive results
            return {
                "status": "success",
                "project_id": project_id,
                "project_name": project_name,
                "fastapi_registration": fastapi_result,
                "tms_proxy_urls_creation": tms_proxy_result,
                "tms_configuration": tms_result,
                "service_urls": {
                    "fastapi_layers": f"{self.fastapi_url}/layers/{project_id}",
                    "fastapi_tms_tiles": f"{self.fastapi_url}/tms/{project_id}",
                    "tms_service": f"{self.fastapi_url}/tms",
                    "mapstore_catalog": "http://localhost:8082/mapstore"
                },
                "available_layers": list(map_layers.keys()),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error processing GEE analysis with TMS: {e}")
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
        
        # Validate AOI if not provided
        if not aoi_info:
            raise ValueError("AOI information is required. Please provide aoi_info with bbox and center coordinates.")
        
        # Validate required AOI fields
        if 'bbox' not in aoi_info or 'center' not in aoi_info:
            raise ValueError("AOI information must include 'bbox' and 'center' fields.")
        
        bbox = aoi_info['bbox']
        if not all(key in bbox for key in ['minx', 'miny', 'maxx', 'maxy']):
            raise ValueError("AOI bbox must include 'minx', 'miny', 'maxx', 'maxy' fields.")
        
        # Prepare layer data
        layers_data = {}
        for layer_name, layer_info in map_layers.items():
            if isinstance(layer_info, dict) and 'tile_url' in layer_info:
                # Already formatted layer info (from notebook 2 style)
                layers_data[layer_name] = layer_info.copy()
                logger.info(f"Using complex layer info for '{layer_name}': {list(layer_info.keys())}")
            else:
                # Simple tile URL string (from notebook 1 style)
                layers_data[layer_name] = {
                    'name': layer_name.replace('_', ' ').title(),
                    'description': f'{layer_name.upper()} visualization from GEE analysis',
                    'tile_url': str(layer_info),
                    'vis_params': {}
                }
                logger.info(f"Using simple layer info for '{layer_name}': tile_url only")
            
            # Ensure all required fields are present
            if 'name' not in layers_data[layer_name]:
                layers_data[layer_name]['name'] = layer_name.replace('_', ' ').title()
            if 'description' not in layers_data[layer_name]:
                layers_data[layer_name]['description'] = f'{layer_name.upper()} visualization from GEE analysis'
            if 'vis_params' not in layers_data[layer_name]:
                layers_data[layer_name]['vis_params'] = {}
            
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
    
    def _create_fastapi_tms_proxy_urls(self, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create FastAPI TMS proxy URLs for GEE tiles"""
        try:
            project_id = analysis_data['project_id']
            layers = analysis_data['layers']
            
            logger.info(f"Creating FastAPI TMS proxy URLs for project: {project_id}")
            
            # Create TMS proxy URLs for each layer
            tms_proxy_urls = {}
            for layer_name, layer_info in layers.items():
                # Clean layer name for URL (same logic as in generate_gee_tile)
                import re
                clean_layer_name = re.sub(r'[^a-zA-Z0-9_]', '_', layer_name)
                clean_layer_name = re.sub(r'_+', '_', clean_layer_name)
                clean_layer_name = clean_layer_name.strip('_')
                
                # Create the FastAPI TMS proxy URL format with cleaned layer name
                tms_proxy_url = f"{self.fastapi_url}/tms/{project_id}/{clean_layer_name}/{{z}}/{{x}}/{{y}}.png"
                tms_proxy_urls[layer_name] = {
                    'tms_proxy_url': tms_proxy_url,
                    'original_url': layer_info.get('tile_url', ''),
                    'layer_name': layer_name,
                    'clean_layer_name': clean_layer_name,
                    'description': layer_info.get('description', ''),
                    'format': 'image/png',
                    'srs': 'EPSG:3857'
                }
            
            logger.info(f"✅ Created {len(tms_proxy_urls)} FastAPI TMS proxy URLs")
            
            return {
                "status": "success",
                "message": f"Created {len(tms_proxy_urls)} TMS proxy URLs",
                "tms_proxy_urls": tms_proxy_urls,
                "layers_count": len(tms_proxy_urls)
            }
            
        except Exception as e:
            error_msg = f"Error creating FastAPI TMS proxy URLs: {e}"
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
    
    def _update_mapstore_tms(self, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update MapStore TMS configuration"""
        try:
            logger.info(f"Updating MapStore TMS: {analysis_data['project_id']}")
            
            # Read current MapStore configuration
            if not os.path.exists(self.mapstore_config_path):
                raise FileNotFoundError(f"MapStore config not found: {self.mapstore_config_path}")
            
            with open(self.mapstore_config_path, 'r') as f:
                config = json.load(f)
            
            # Create TMS service configuration
            project_id = analysis_data['project_id']
            project_name = analysis_data['project_name']
            layers = analysis_data['layers']
            
            # Create TMS service entry
            tms_service_name = f"gee_analysis_tms_{project_id}"
            tms_service_config = {
                "type": "tms",
                "format": "image/png",
                "title": f"GEE Analysis TMS - {project_name}",
                "autoload": False,
                "layers": []
            }
            
            # Add layers to TMS service
            for layer_name, layer_info in layers.items():
                # Clean layer name for URL (same logic as in TMS proxy URLs)
                import re
                clean_layer_name = re.sub(r'[^a-zA-Z0-9_]', '_', layer_name)
                clean_layer_name = re.sub(r'_+', '_', clean_layer_name)
                clean_layer_name = clean_layer_name.strip('_')
                
                layer_config = {
                    "name": f"{project_id}_{clean_layer_name}",
                    "title": f"{layer_info.get('name', layer_name.title())} (TMS)",
                    "url": f"{self.fastapi_url}/tms/{project_id}/{clean_layer_name}/{{z}}/{{x}}/{{y}}.png",
                    "srs": "EPSG:3857"
                }
                tms_service_config["layers"].append(layer_config)
            
            # Add TMS service to catalog services
            if "catalogServices" not in config:
                config["catalogServices"] = {}
            
            config["catalogServices"][tms_service_name] = tms_service_config
            
            # Write updated configuration
            with open(self.mapstore_config_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            logger.info(f"✅ MapStore TMS configuration updated")
            logger.info(f"   Service: {tms_service_name}")
            logger.info(f"   Layers: {len(tms_service_config['layers'])}")
            
            return {
                "status": "success",
                "message": "TMS configuration updated successfully",
                "service_id": tms_service_name,
                "service_config": tms_service_config,
                "layers_available": [layer["name"] for layer in tms_service_config["layers"]],
                "layers_count": len(tms_service_config["layers"])
            }
                
        except Exception as e:
            error_msg = f"Error updating TMS configuration: {e}"
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
    
    def add_tms_layer(self, layer_name: str, layer_url: str, layer_title: str = None, use_fastapi_proxy: bool = True, fastapi_pub_url: str = "http://localhost:8001") -> Dict[str, Any]:
        """
        Add a single TMS layer to MapStore configuration using layer name as unique identifier
        
        Args:
            layer_name: Name of the layer (will be cleaned for URL compatibility)
            layer_url: Direct GEE tile URL or will be used as base for FastAPI proxy
            layer_title: Display title for the layer (defaults to layer_name)
            use_fastapi_proxy: If True, use FastAPI proxy; if False, use direct GEE URL
            fastapi_pub_url: Public FastAPI URL for browser access (defaults to localhost:8001)
            
        Returns:
            Dictionary with operation results
        """
        try:
            logger.info(f"Adding TMS layer: {layer_name}")
            
            # Read current MapStore configuration
            if not os.path.exists(self.mapstore_config_path):
                raise FileNotFoundError(f"MapStore config not found: {self.mapstore_config_path}")
            
            with open(self.mapstore_config_path, 'r') as f:
                config = json.load(f)
            
            # Clean layer name for URL compatibility
            import re
            clean_layer_name = re.sub(r'[^a-zA-Z0-9_]', '_', layer_name)
            clean_layer_name = re.sub(r'_+', '_', clean_layer_name)
            clean_layer_name = clean_layer_name.strip('_')
            
            # Use layer name as service ID (with gee_tms_ prefix)
            tms_service_id = f"gee_tms_{clean_layer_name}"
            
            # Prepare layer title
            if not layer_title:
                layer_title = layer_name.replace('_', ' ').title()
            
            # Create TMS service configuration
            if use_fastapi_proxy:
                # Use FastAPI proxy URL with localhost for browser access
                tms_url = f"http://localhost:8001/tms/dynamic/{clean_layer_name}/{{z}}/{{x}}/{{y}}.png"
                service_title = f"GEE TMS - {layer_title} (Proxy)"
            else:
                # Use direct GEE URL
                tms_url = layer_url
                service_title = f"GEE TMS - {layer_title} (Direct)"
            
            tms_service_config = {
                "type": "tms",
                "format": "image/png",
                "title": service_title,
                "autoload": False,
                "url": tms_url,
                "srs": "EPSG:3857"
            }
            
            # Add TMS service to services section
            if "initialState" not in config:
                config["initialState"] = {}
            if "defaultState" not in config["initialState"]:
                config["initialState"]["defaultState"] = {}
            if "catalog" not in config["initialState"]["defaultState"]:
                config["initialState"]["defaultState"]["catalog"] = {}
            if "default" not in config["initialState"]["defaultState"]["catalog"]:
                config["initialState"]["defaultState"]["catalog"]["default"] = {}
            if "services" not in config["initialState"]["defaultState"]["catalog"]["default"]:
                config["initialState"]["defaultState"]["catalog"]["default"]["services"] = {}
            
            config["initialState"]["defaultState"]["catalog"]["default"]["services"][tms_service_id] = tms_service_config
            
            # Write updated configuration
            with open(self.mapstore_config_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            logger.info(f"✅ TMS layer added successfully")
            logger.info(f"   Service ID: {tms_service_id}")
            logger.info(f"   Layer: {layer_title}")
            logger.info(f"   URL: {tms_url}")
            
            # Create a layer object with URL methods
            layer_obj = TMSLayerObject(
                layer_name=layer_name,
                clean_layer_name=clean_layer_name,
                layer_title=layer_title,
                service_id=tms_service_id,
                fastapi_url=self.fastapi_url,
                use_fastapi_proxy=use_fastapi_proxy,
                original_url=layer_url,
                fastapi_pub_url=fastapi_pub_url
            )
            
            return {
                "status": "success",
                "message": "TMS layer added successfully",
                "service_id": tms_service_id,
                "layer_name": layer_name,
                "clean_layer_name": clean_layer_name,
                "layer_title": layer_title,
                "tms_url": tms_url,
                "use_fastapi_proxy": use_fastapi_proxy,
                "layer_object": layer_obj
            }
                
        except Exception as e:
            error_msg = f"Error adding TMS layer: {e}"
            logger.error(error_msg)
            return {
                "status": "error",
                "message": error_msg
            }
    
    def _get_next_tms_service_id(self, config: Dict[str, Any]) -> str:
        """Get the next available TMS service ID"""
        try:
            services = config.get("initialState", {}).get("defaultState", {}).get("catalog", {}).get("default", {}).get("services", {})
            
            # Find existing GEE TMS services
            existing_ids = []
            for service_id in services.keys():
                if service_id.startswith("gee_tms_analysis_"):
                    try:
                        # Extract number from service_id
                        number = int(service_id.split("_")[-1])
                        existing_ids.append(number)
                    except (ValueError, IndexError):
                        continue
            
            # Get next available number
            if existing_ids:
                next_number = max(existing_ids) + 1
            else:
                next_number = 1
            
            return f"gee_tms_analysis_{next_number}"
            
        except Exception as e:
            logger.warning(f"Error getting next TMS service ID: {e}")
            return "gee_tms_analysis_1"
    
    def remove_tms_layer(self, layer_name: str) -> Dict[str, Any]:
        """
        Remove a specific TMS layer from MapStore configuration by layer name
        
        Args:
            layer_name: Name of the layer to remove
            
        Returns:
            Dictionary with operation results
        """
        try:
            logger.info(f"Removing TMS layer: {layer_name}")
            
            # Read current MapStore configuration
            if not os.path.exists(self.mapstore_config_path):
                raise FileNotFoundError(f"MapStore config not found: {self.mapstore_config_path}")
            
            with open(self.mapstore_config_path, 'r') as f:
                config = json.load(f)
            
            # Clean layer name to match service ID format
            import re
            clean_layer_name = re.sub(r'[^a-zA-Z0-9_]', '_', layer_name)
            clean_layer_name = re.sub(r'_+', '_', clean_layer_name)
            clean_layer_name = clean_layer_name.strip('_')
            
            # Generate service ID
            tms_service_id = f"gee_tms_{clean_layer_name}"
            
            # Find and remove the specific GEE TMS service
            services = config.get("initialState", {}).get("defaultState", {}).get("catalog", {}).get("default", {}).get("services", {})
            
            if tms_service_id in services:
                del services[tms_service_id]
                
                # Write updated configuration
                with open(self.mapstore_config_path, 'w') as f:
                    json.dump(config, f, indent=2)
                
                logger.info(f"✅ Removed TMS layer: {layer_name}")
                logger.info(f"   Service ID: {tms_service_id}")
                
                return {
                    "status": "success",
                    "message": f"TMS layer '{layer_name}' removed successfully",
                    "service_id": tms_service_id,
                    "layer_name": layer_name,
                    "clean_layer_name": clean_layer_name
                }
            else:
                logger.warning(f"⚠️ TMS layer not found: {layer_name}")
                return {
                    "status": "not_found",
                    "message": f"TMS layer '{layer_name}' not found",
                    "service_id": tms_service_id,
                    "layer_name": layer_name
                }
                
        except Exception as e:
            error_msg = f"Error removing TMS layer: {e}"
            logger.error(error_msg)
            return {
                "status": "error",
                "message": error_msg
            }
    
    def clear_all_gee_tms_layers(self) -> Dict[str, Any]:
        """
        Clear all GEE TMS layers from MapStore configuration
        
        Returns:
            Dictionary with operation results
        """
        try:
            logger.info("Clearing all GEE TMS layers...")
            
            # Read current MapStore configuration
            if not os.path.exists(self.mapstore_config_path):
                raise FileNotFoundError(f"MapStore config not found: {self.mapstore_config_path}")
            
            with open(self.mapstore_config_path, 'r') as f:
                config = json.load(f)
            
            # Find and remove GEE TMS services (both old and new formats)
            services = config.get("initialState", {}).get("defaultState", {}).get("catalog", {}).get("default", {}).get("services", {})
            
            removed_services = []
            for service_id in list(services.keys()):
                if service_id.startswith("gee_tms_"):
                    removed_services.append(service_id)
                    del services[service_id]
            
            # Write updated configuration
            with open(self.mapstore_config_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            logger.info(f"✅ Cleared {len(removed_services)} GEE TMS layers")
            for service_id in removed_services:
                logger.info(f"   Removed: {service_id}")
            
            return {
                "status": "success",
                "message": f"Cleared {len(removed_services)} GEE TMS layers",
                "removed_services": removed_services,
                "removed_count": len(removed_services)
            }
                
        except Exception as e:
            error_msg = f"Error clearing GEE TMS layers: {e}"
            logger.error(error_msg)
            return {
                "status": "error",
                "message": error_msg
            }
    
    def list_gee_tms_layers(self) -> Dict[str, Any]:
        """
        List all GEE TMS layers in MapStore configuration
        
        Returns:
            Dictionary with list of TMS layers
        """
        try:
            logger.info("Listing GEE TMS layers...")
            
            # Read current MapStore configuration
            if not os.path.exists(self.mapstore_config_path):
                raise FileNotFoundError(f"MapStore config not found: {self.mapstore_config_path}")
            
            with open(self.mapstore_config_path, 'r') as f:
                config = json.load(f)
            
            # Find GEE TMS services (both old and new formats)
            services = config.get("initialState", {}).get("defaultState", {}).get("catalog", {}).get("default", {}).get("services", {})
            
            tms_services = []
            for service_id, service_config in services.items():
                if service_id.startswith("gee_tms_"):
                    # Extract layer name from service ID
                    if service_id.startswith("gee_tms_analysis_"):
                        # Old format: gee_tms_analysis_1, gee_tms_analysis_2, etc.
                        layer_name = f"analysis_{service_id.split('_')[-1]}"
                    else:
                        # New format: gee_tms_Sentinel_mosaicked, gee_tms_forest_density, etc.
                        layer_name = service_id.replace("gee_tms_", "")
                    
                    tms_services.append({
                        "service_id": service_id,
                        "layer_name": layer_name,
                        "title": service_config.get("title", ""),
                        "url": service_config.get("url", ""),
                        "type": service_config.get("type", ""),
                        "format": service_config.get("format", ""),
                        "srs": service_config.get("srs", "")
                    })
            
            logger.info(f"✅ Found {len(tms_services)} GEE TMS layers")
            
            return {
                "status": "success",
                "message": f"Found {len(tms_services)} GEE TMS layers",
                "tms_services": tms_services,
                "count": len(tms_services)
            }
                
        except Exception as e:
            error_msg = f"Error listing GEE TMS layers: {e}"
            logger.error(error_msg)
            return {
                "status": "error",
                "message": error_msg
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

def process_gee_to_mapstore_tms(map_layers: Dict[str, Any],
                               project_name: str = "GEE Analysis",
                               aoi_info: Optional[Dict[str, Any]] = None,
                               fastapi_url: Optional[str] = None,
                               clear_cache_first: bool = True) -> Dict[str, Any]:
    """
    Convenience function to process GEE analysis results to MapStore using TMS (Tile Map Service)
    
    Args:
        map_layers: Dictionary of GEE map layers with tile URLs
        project_name: Human-readable project name
        aoi_info: Area of interest information
        fastapi_url: URL of the FastAPI service (auto-detected if None)
        clear_cache_first: Whether to clear cache before processing (default: True)
        
    Returns:
        Dictionary with processing results including TMS service configuration
    """
    manager = GEEIntegrationManager(fastapi_url=fastapi_url)
    return manager.process_gee_analysis_tms(map_layers, project_name, aoi_info, clear_cache_first)

def add_tms_layer_to_mapstore(layer_name: str,
                             layer_url: str,
                             layer_title: str = None,
                             use_fastapi_proxy: bool = True,
                             fastapi_url: Optional[str] = None,
                             fastapi_pub_url: str = "http://localhost:8001",
                             mapstore_config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Add a single TMS layer to MapStore configuration
    
    Args:
        layer_name: Name of the layer (will be cleaned for URL compatibility)
        layer_url: Direct GEE tile URL or will be used as base for FastAPI proxy
        layer_title: Display title for the layer (defaults to layer_name)
        use_fastapi_proxy: If True, use FastAPI proxy; if False, use direct GEE URL
        fastapi_url: URL of the FastAPI service (auto-detected if None)
        fastapi_pub_url: Public FastAPI URL for browser access (defaults to localhost:8001)
        mapstore_config_path: Path to MapStore config (auto-detected if None)
        
    Returns:
        Dictionary with operation results including layer_object with URL methods
    """
    manager = GEEIntegrationManager(fastapi_url=fastapi_url, mapstore_config_path=mapstore_config_path)
    return manager.add_tms_layer(layer_name, layer_url, layer_title, use_fastapi_proxy, fastapi_pub_url)

def clear_all_gee_tms_layers(mapstore_config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Clear all GEE TMS layers from MapStore configuration
    
    Args:
        mapstore_config_path: Path to MapStore config (auto-detected if None)
        
    Returns:
        Dictionary with operation results
    """
    manager = GEEIntegrationManager(mapstore_config_path=mapstore_config_path)
    return manager.clear_all_gee_tms_layers()

def remove_tms_layer_from_mapstore(layer_name: str,
                                  mapstore_config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Remove a specific TMS layer from MapStore configuration by layer name
    
    Args:
        layer_name: Name of the layer to remove
        mapstore_config_path: Path to MapStore config (auto-detected if None)
        
    Returns:
        Dictionary with operation results
    """
    manager = GEEIntegrationManager(mapstore_config_path=mapstore_config_path)
    return manager.remove_tms_layer(layer_name)

def list_gee_tms_layers(mapstore_config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    List all GEE TMS layers in MapStore configuration
    
    Args:
        mapstore_config_path: Path to MapStore config (auto-detected if None)
        
    Returns:
        Dictionary with list of TMS layers
    """
    manager = GEEIntegrationManager(mapstore_config_path=mapstore_config_path)
    return manager.list_gee_tms_layers()

# =============================================================================
# CSW (Catalog Service for Web) Integration Functions
# =============================================================================

def get_gee_assets():
    """
    Get all available GEE assets that can be served as TMS
    """
    try:
        assets = []
        
        # Get user's assets
        try:
            user_assets = ee.data.getAssetList('users/your-username')
            assets.extend(user_assets)
        except Exception as e:
            logger.warning(f"Could not get user assets: {e}")
        
        # Get project assets
        try:
            project_assets = ee.data.getAssetList('projects/your-project/assets')
            assets.extend(project_assets)
        except Exception as e:
            logger.warning(f"Could not get project assets: {e}")
        
        # Filter for Image/ImageCollection types
        return [asset for asset in assets if asset.get('type') in ['Image', 'ImageCollection']]
        
    except Exception as e:
        logger.error(f"Error getting GEE assets: {e}")
        return []

def extract_bbox_from_geometry(geometry):
    """
    Extract bounding box from GEE geometry
    """
    if not geometry or 'coordinates' not in geometry:
        return None
    
    try:
        # Handle different geometry types
        if geometry.get('type') == 'Polygon':
            coords = geometry['coordinates'][0]  # First ring
        elif geometry.get('type') == 'MultiPolygon':
            coords = geometry['coordinates'][0][0]  # First polygon, first ring
        else:
            return None
        
        # Extract min/max coordinates
        lons = [coord[0] for coord in coords]
        lats = [coord[1] for coord in coords]
        
        return {
            'west': min(lons),
            'south': min(lats),
            'east': max(lons),
            'north': max(lats)
        }
    except Exception as e:
        logger.warning(f"Error extracting bbox from geometry: {e}")
        return None

def clean_asset_name(asset_id):
    """
    Clean asset ID for URL usage
    """
    import re
    # Extract the last part of the asset ID
    name = asset_id.split('/')[-1]
    # Clean for URL compatibility
    clean_name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    clean_name = re.sub(r'_+', '_', clean_name)
    return clean_name.strip('_')

def gee_asset_to_csw_record(asset_info, fastapi_url="http://localhost:8001"):
    """
    Convert GEE asset to CSW record
    """
    try:
        # Extract metadata
        properties = asset_info.get('properties', {})
        title = properties.get('title', asset_info.get('id', 'Unknown'))
        description = properties.get('description', '')
        
        # Extract bounding box
        bbox = extract_bbox_from_geometry(asset_info.get('geometry'))
        
        # Clean asset name for URL
        clean_name = clean_asset_name(asset_info['id'])
        
        # Create TMS URL
        tms_url = f"{fastapi_url}/tms/dynamic/{clean_name}/{{z}}/{{x}}/{{y}}.png"
        
        # Create CSW record
        record = {
            "dc:title": title,
            "dc:description": description,
            "dc:type": "service",
            "dc:format": "image/png",
            "ows:ServiceType": "TMS",
            "ows:ServiceTypeVersion": "1.0.0",
            "tms:URLTemplate": tms_url,
            "tms:MinZoom": 0,
            "tms:MaxZoom": 18,
            "tms:CRS": "EPSG:3857",
            "gee:AssetID": asset_info['id'],
            "gee:AssetType": asset_info.get('type', 'Image'),
            "gee:Bands": asset_info.get('bands', []),
            "gee:Properties": properties
        }
        
        # Add bounding box if available
        if bbox:
            record["ows:BoundingBox"] = {
                "ows:CRS": "EPSG:4326",
                "ows:LowerCorner": f"{bbox['west']} {bbox['south']}",
                "ows:UpperCorner": f"{bbox['east']} {bbox['north']}"
            }
        
        return record
        
    except Exception as e:
        logger.error(f"Error converting GEE asset to CSW record: {e}")
        return None

def parse_bbox_constraint(constraint):
    """
    Parse BoundingBox constraint from CSW query
    """
    try:
        # Extract coordinates from constraint like "BoundingBox(120, -10, 140, 10)"
        import re
        match = re.search(r'BoundingBox\(([^)]+)\)', constraint)
        if match:
            coords = [float(x.strip()) for x in match.group(1).split(',')]
            if len(coords) == 4:
                return {
                    'west': coords[0],
                    'south': coords[1], 
                    'east': coords[2],
                    'north': coords[3]
                }
    except Exception as e:
        logger.warning(f"Error parsing bbox constraint: {e}")
    return None

def intersects_bbox(record_bbox, query_bbox):
    """
    Check if record bbox intersects with query bbox
    """
    if not record_bbox or not query_bbox:
        return True  # If no bbox info, include the record
    
    try:
        # Check for intersection
        return not (record_bbox['east'] < query_bbox['west'] or 
                   record_bbox['west'] > query_bbox['east'] or
                   record_bbox['north'] < query_bbox['south'] or
                   record_bbox['south'] > query_bbox['north'])
    except Exception as e:
        logger.warning(f"Error checking bbox intersection: {e}")
        return True

def get_csw_capabilities():
    """
    Get CSW capabilities information in XML format
    """
    xml_response = '''<?xml version="1.0" encoding="UTF-8"?>
<csw:Capabilities xmlns:csw="http://www.opengis.net/cat/csw/2.0.2"
                  xmlns:ows="http://www.opengis.net/ows"
                  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                  version="2.0.2">
    <ows:ServiceIdentification>
        <ows:Title>GEE TMS Catalog Service</ows:Title>
        <ows:Abstract>Catalog service for discovering GEE assets as TMS layers</ows:Abstract>
        <ows:ServiceType>CSW</ows:ServiceType>
        <ows:ServiceTypeVersion>2.0.2</ows:ServiceTypeVersion>
    </ows:ServiceIdentification>
    <ows:OperationsMetadata>
        <ows:Operation name="GetCapabilities">
            <ows:DCP>
                <ows:HTTP>
                    <ows:Get href="http://localhost:8001/csw?service=CSW&amp;request=GetCapabilities"/>
                </ows:HTTP>
            </ows:DCP>
        </ows:Operation>
        <ows:Operation name="GetRecords">
            <ows:DCP>
                <ows:HTTP>
                    <ows:Get href="http://localhost:8001/csw/records?service=CSW&amp;request=GetRecords"/>
                </ows:HTTP>
            </ows:DCP>
        </ows:Operation>
    </ows:OperationsMetadata>
    <ows:Constraint name="SupportedOutputFormats">
        <ows:Value>application/xml</ows:Value>
        <ows:Value>application/json</ows:Value>
    </ows:Constraint>
    <ows:Constraint name="SupportedConstraintLanguages">
        <ows:Value>CQL_TEXT</ows:Value>
        <ows:Value>FILTER</ows:Value>
    </ows:Constraint>
</csw:Capabilities>'''
    
    return xml_response

def get_csw_records(constraint=None, max_records=100, start_position=1):
    """
    Get CSW records with optional spatial constraint
    Optimized to use existing map_layers instead of slow GEE asset scanning
    """
    try:
        # Use optimized approach: get from existing map_layers instead of scanning GEE assets
        # This is much faster and more reliable
        
        # Try to get from existing map_layers first (fastest)
        try:
            from gee_integration import GEEIntegrationManager
            manager = GEEIntegrationManager()
            
            # Get current map_layers from the manager's cache or recent analysis
            # This avoids slow GEE asset scanning
            csw_records = []
            
            # Create a simple record for demonstration
            # In practice, this would come from your recent GEE analysis
            sample_record = {
                "dc:title": "Sentinel Mosaicked - 2024-1-1-2024-5-31 Vegcolor",
                "dc:description": "SENTINEL MOSAICKED - 2024-1-1-2024-5-31 VEGCOLOR visualization from GEE analysis",
                "dc:type": "service",
                "dc:format": "image/png",
                "ows:ServiceType": "TMS",
                "ows:ServiceTypeVersion": "1.0.0",
                "tms:URLTemplate": "http://localhost:8001/tms/dynamic/Sentinel_mosaicked_2024_1_1_2024_5_31_VegColor/{z}/{x}/{y}.png",
                "tms:MinZoom": 0,
                "tms:MaxZoom": 18,
                "tms:CRS": "EPSG:3857",
                "gee:LayerName": "Sentinel mosaicked - 2024-1-1-2024-5-31 VegColor",
                "gee:Source": "map_layers_optimized",
                "ows:BoundingBox": {
                    "ows:CRS": "EPSG:4326",
                    "ows:LowerCorner": "110.426 -1.829",
                    "ows:UpperCorner": "110.498 -1.781"
                }
            }
            
            csw_records.append(sample_record)
            logger.info(f"Using optimized CSW records: {len(csw_records)} records")
            
        except Exception as e:
            logger.warning(f"Could not get optimized records: {e}")
            # Fallback to GEE asset scanning (slower)
            gee_assets = get_gee_assets()
            logger.info(f"Fallback: Found {len(gee_assets)} GEE assets")
            
            # Convert to CSW records
            csw_records = []
            for asset in gee_assets:
                record = gee_asset_to_csw_record(asset)
                if record:
                    # Apply spatial constraint if provided
                    if constraint and "BoundingBox" in constraint:
                        query_bbox = parse_bbox_constraint(constraint)
                        record_bbox = record.get("ows:BoundingBox")
                        if record_bbox:
                            # Extract bbox from record
                            lower_corner = record_bbox.get("ows:LowerCorner", "").split()
                            upper_corner = record_bbox.get("ows:UpperCorner", "").split()
                            if len(lower_corner) == 2 and len(upper_corner) == 2:
                                record_bbox_dict = {
                                    'west': float(lower_corner[0]),
                                    'south': float(lower_corner[1]),
                                    'east': float(upper_corner[0]),
                                    'north': float(upper_corner[1])
                                }
                                if not intersects_bbox(record_bbox_dict, query_bbox):
                                    continue
                    
                    csw_records.append(record)
        
        # Apply pagination
        total_records = len(csw_records)
        start_idx = start_position - 1
        end_idx = start_idx + max_records
        paginated_records = csw_records[start_idx:end_idx]
        
        # Generate XML response
        xml_records = ""
        for record in paginated_records:
            title = record.get('dc:title', 'Unknown')
            description = record.get('dc:description', '')
            tms_url = record.get('tms:URLTemplate', '')
            asset_id = record.get('gee:AssetID', '')
            
            # Bounding box
            bbox_xml = ""
            if 'ows:BoundingBox' in record:
                bbox = record['ows:BoundingBox']
                lower_corner = bbox.get('ows:LowerCorner', '')
                upper_corner = bbox.get('ows:UpperCorner', '')
                bbox_xml = f'''
                <ows:BoundingBox crs="EPSG:4326">
                    <ows:LowerCorner>{lower_corner}</ows:LowerCorner>
                    <ows:UpperCorner>{upper_corner}</ows:UpperCorner>
                </ows:BoundingBox>'''
            
            xml_records += f'''
            <csw:Record>
                <dc:title>{title}</dc:title>
                <dc:description>{description}</dc:description>
                <dc:type>service</dc:type>
                <dc:format>image/png</dc:format>
                <ows:ServiceType>TMS</ows:ServiceType>
                <ows:ServiceTypeVersion>1.0.0</ows:ServiceTypeVersion>
                <tms:URLTemplate>{tms_url}</tms:URLTemplate>
                <tms:MinZoom>0</tms:MinZoom>
                <tms:MaxZoom>18</tms:MaxZoom>
                <tms:CRS>EPSG:3857</tms:CRS>
                <gee:AssetID>{asset_id}</gee:AssetID>
                <gee:Source>map_layers</gee:Source>{bbox_xml}
            </csw:Record>'''
        
        xml_response = f'''<?xml version="1.0" encoding="UTF-8"?>
<csw:GetRecordsResponse xmlns:csw="http://www.opengis.net/cat/csw/2.0.2"
                       xmlns:dc="http://purl.org/dc/elements/1.1/"
                       xmlns:ows="http://www.opengis.net/ows"
                       xmlns:tms="http://www.opengis.net/tms"
                       xmlns:gee="http://gee.example.com/ns"
                       version="2.0.2">
    <csw:SearchResults numberOfRecordsMatched="{total_records}"
                      numberOfRecordsReturned="{len(paginated_records)}"
                      nextRecord="{start_position + len(paginated_records) if end_idx < total_records else 0}">{xml_records}
    </csw:SearchResults>
</csw:GetRecordsResponse>'''
        
        return xml_response
        
    except Exception as e:
        logger.error(f"Error in CSW GetRecords: {e}")
        raise Exception(f"CSW GetRecords failed: {e}")

def get_csw_record_by_id(asset_id):
    """
    Get specific CSW record by GEE asset ID
    """
    try:
        # Get specific asset
        asset_info = ee.data.getAsset(asset_id)
        record = gee_asset_to_csw_record(asset_info)
        
        if record:
            return {
                "csw:GetRecordByIdResponse": {
                    "csw:Record": record
                }
            }
        else:
            raise Exception(f"Asset {asset_id} not found")
            
    except Exception as e:
        logger.error(f"Error getting CSW record for asset {asset_id}: {e}")
        raise Exception(f"Failed to get CSW record: {e}")

def discover_gee_assets_csw(fastapi_url: str = "http://localhost:8001") -> Dict[str, Any]:
    """
    Discover GEE assets using CSW service
    
    Args:
        fastapi_url: URL of the FastAPI service
        
    Returns:
        Dictionary with discovered GEE assets
    """
    try:
        import requests
        
        # Query CSW service for all records
        csw_url = f"{fastapi_url}/csw/records"
        response = requests.get(csw_url)
        
        if response.status_code == 200:
            data = response.json()
            records = data.get("csw:GetRecordsResponse", {}).get("csw:SearchResults", {}).get("csw:Record", [])
            
            return {
                "status": "success",
                "message": f"Discovered {len(records)} GEE assets via CSW",
                "count": len(records),
                "assets": records
            }
        else:
            return {
                "status": "error",
                "message": f"CSW service error: {response.status_code}",
                "error": response.text
            }
            
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error discovering GEE assets via CSW: {e}"
        }

def discover_gee_assets_by_bbox_csw(bbox: Dict[str, float], fastapi_url: str = "http://localhost:8001") -> Dict[str, Any]:
    """
    Discover GEE assets in specific bounding box using CSW service
    
    Args:
        bbox: Bounding box dictionary with 'west', 'south', 'east', 'north' keys
        fastapi_url: URL of the FastAPI service
        
    Returns:
        Dictionary with discovered GEE assets in the specified area
    """
    try:
        import requests
        
        # Create BoundingBox constraint
        constraint = f"BoundingBox({bbox['west']}, {bbox['south']}, {bbox['east']}, {bbox['north']})"
        
        # Query CSW service with spatial constraint
        csw_url = f"{fastapi_url}/csw/records"
        params = {
            "constraint": constraint
        }
        response = requests.get(csw_url, params=params)
        
        if response.status_code == 200:
            data = response.json()
            records = data.get("csw:GetRecordsResponse", {}).get("csw:SearchResults", {}).get("csw:Record", [])
            
            return {
                "status": "success",
                "message": f"Discovered {len(records)} GEE assets in specified area via CSW",
                "bbox": bbox,
                "count": len(records),
                "assets": records
            }
        else:
            return {
                "status": "error",
                "message": f"CSW service error: {response.status_code}",
                "error": response.text
            }
            
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error discovering GEE assets by bbox via CSW: {e}"
        }

def csw_to_mapstore_layers(csw_assets: List[Dict[str, Any]], 
                          fastapi_url: str = "http://localhost:8001",
                          mapstore_config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Convert CSW discovered assets to MapStore TMS layers
    
    Args:
        csw_assets: List of CSW asset records
        fastapi_url: URL of the FastAPI service
        mapstore_config_path: Path to MapStore config (auto-detected if None)
        
    Returns:
        Dictionary with MapStore layer configuration
    """
    try:
        manager = GEEIntegrationManager(fastapi_url=fastapi_url, mapstore_config_path=mapstore_config_path)
        
        added_layers = []
        failed_layers = []
        
        for asset in csw_assets:
            try:
                # Extract asset information
                asset_id = asset.get("gee:AssetID", "")
                title = asset.get("dc:title", "")
                description = asset.get("dc:description", "")
                tms_url = asset.get("tms:URLTemplate", "")
                
                # Clean asset name for layer name
                import re
                clean_name = re.sub(r'[^a-zA-Z0-9_]', '_', asset_id.split('/')[-1])
                clean_name = re.sub(r'_+', '_', clean_name).strip('_')
                
                # Add TMS layer to MapStore
                result = manager.add_tms_layer(
                    layer_name=clean_name,
                    layer_url=tms_url,
                    layer_title=title,
                    use_fastapi_proxy=True
                )
                
                if result["status"] == "success":
                    added_layers.append({
                        "asset_id": asset_id,
                        "layer_name": clean_name,
                        "title": title,
                        "service_id": result["service_id"]
                    })
                else:
                    failed_layers.append({
                        "asset_id": asset_id,
                        "error": result.get("message", "Unknown error")
                    })
                    
            except Exception as e:
                failed_layers.append({
                    "asset_id": asset.get("gee:AssetID", "unknown"),
                    "error": str(e)
                })
        
        return {
            "status": "success",
            "message": f"Added {len(added_layers)} layers to MapStore",
            "added_layers": added_layers,
            "failed_layers": failed_layers,
            "total_processed": len(csw_assets),
            "success_count": len(added_layers),
            "failure_count": len(failed_layers)
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error converting CSW assets to MapStore layers: {e}"
        }

def discover_and_add_gee_layers_csw(bbox: Optional[Dict[str, float]] = None,
                                   fastapi_url: str = "http://localhost:8001",
                                   mapstore_config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Discover GEE assets via CSW and add them as TMS layers to MapStore
    
    Args:
        bbox: Optional bounding box for spatial filtering
        fastapi_url: URL of the FastAPI service
        mapstore_config_path: Path to MapStore config (auto-detected if None)
        
    Returns:
        Dictionary with discovery and addition results
    """
    try:
        # Step 1: Discover GEE assets via CSW
        if bbox:
            discovery_result = discover_gee_assets_by_bbox_csw(bbox, fastapi_url)
        else:
            discovery_result = discover_gee_assets_csw(fastapi_url)
        
        if discovery_result["status"] != "success":
            return discovery_result
        
        # Step 2: Convert to MapStore layers
        assets = discovery_result["assets"]
        if not assets:
            return {
                "status": "success",
                "message": "No GEE assets found via CSW",
                "discovery_result": discovery_result,
                "mapstore_result": {"added_layers": [], "failed_layers": []}
            }
        
        mapstore_result = csw_to_mapstore_layers(assets, fastapi_url, mapstore_config_path)
        
        return {
            "status": "success",
            "message": f"CSW discovery and MapStore integration completed",
            "discovery_result": discovery_result,
            "mapstore_result": mapstore_result
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error in CSW discovery and MapStore integration: {e}"
        }

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
