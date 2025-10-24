"""
GEE Integration Utilities for FastAPI Service

This module provides utilities for GEE integration, including
WMTS capabilities management and layer processing.
"""

import requests
import json
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class GEEIntegrationUtils:
    """
    Utilities for GEE integration and WMTS management.
    """
    
    def __init__(self, fastapi_url: str = "http://localhost:8000"):
        """
        Initialize GEE integration utilities.
        
        Args:
            fastapi_url: FastAPI service URL
        """
        self.fastapi_url = fastapi_url
    
    def get_wmts_capabilities(self) -> Optional[str]:
        """
        Get WMTS capabilities XML.
        
        Returns:
            WMTS capabilities XML or None if failed
        """
        try:
            response = requests.get(f"{self.fastapi_url}/wmts?service=WMTS&request=GetCapabilities")
            
            if response.status_code == 200:
                return response.text
            else:
                logger.error(f"Failed to get WMTS capabilities: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting WMTS capabilities: {e}")
            return None
    
    def get_wmts_layers(self) -> List[str]:
        """
        Get list of available WMTS layers.
        
        Returns:
            List of layer names
        """
        try:
            capabilities_xml = self.get_wmts_capabilities()
            if not capabilities_xml:
                return []
            
            # Parse the XML response to find layers
            root = ET.fromstring(capabilities_xml)
            
            # Find all Layer elements
            layers = []
            for layer in root.findall(".//{http://www.opengis.net/wmts/1.0}Layer"):
                identifier = layer.find("{http://www.opengis.net/ows/1.1}Identifier")
                if identifier is not None:
                    layers.append(identifier.text)
            
            return layers
            
        except Exception as e:
            logger.error(f"Error parsing WMTS layers: {e}")
            return []
    
    def force_wmts_refresh(self) -> Dict[str, Any]:
        """
        Force refresh WMTS capabilities to get latest layers.
        
        Returns:
            Refresh results
        """
        try:
            # Get WMTS capabilities
            response = requests.get(f"{self.fastapi_url}/wmts?service=WMTS&request=GetCapabilities")
            
            if response.status_code == 200:
                logger.info("WMTS capabilities refreshed successfully")
                return {
                    "status": "success",
                    "capabilities_updated": True,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                logger.error(f"Failed to refresh WMTS capabilities: {response.status_code}")
                return {
                    "status": "error",
                    "error": f"Capabilities refresh failed: {response.status_code}",
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error refreshing WMTS capabilities: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def get_mapstore_config(self) -> Dict[str, Any]:
        """
        Get current MapStore configuration.
        
        Returns:
            Current MapStore configuration
        """
        try:
            response = requests.get(f"{self.fastapi_url}/mapstore/configs")
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Could not get MapStore config: {response.status_code}")
                return {}
        except Exception as e:
            logger.error(f"Error getting MapStore config: {e}")
            return {}
    
    def clear_old_wmts_services(self) -> Dict[str, Any]:
        """
        Clear old WMTS services from MapStore configuration.
        For single layer scenarios, this will completely replace the WMTS service.
        
        Returns:
            Clearing results
        """
        try:
            # Get current config
            config = self.get_mapstore_config()
            
            if not config:
                return {"error": "No config found"}
            
            # Find GEE-related WMTS services (not all WMTS services)
            gee_wmts_services = []
            if "catalogServices" in config:
                for service_name, service_config in config["catalogServices"].items():
                    if (service_config.get("type") == "wmts" and 
                        ("GEE Analysis" in service_config.get("title", "") or 
                         service_name.startswith("gee_analysis_"))):
                        gee_wmts_services.append(service_name)
            
            logger.info(f"Found {len(gee_wmts_services)} GEE WMTS services")
            
            # Remove ALL GEE WMTS services to ensure clean replacement
            if gee_wmts_services:
                for service_name in gee_wmts_services:
                    if service_name in config["catalogServices"]:
                        del config["catalogServices"][service_name]
                        logger.info(f"Removed GEE WMTS service: {service_name}")
                
                # Update the configuration
                response = requests.post(f"{self.fastapi_url}/mapstore/configs", json=config)
                if response.status_code == 200:
                    logger.info("Updated MapStore configuration - cleared all GEE WMTS services")
                    return {
                        "status": "success",
                        "removed_services": gee_wmts_services,
                        "message": f"Cleared {len(gee_wmts_services)} GEE WMTS services for clean replacement",
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    logger.error(f"Failed to update MapStore config: {response.status_code}")
                    return {
                        "status": "error",
                        "error": f"Update failed: {response.status_code}",
                        "timestamp": datetime.now().isoformat()
                    }
            else:
                logger.info("No GEE WMTS services to remove")
                return {
                    "status": "success",
                    "message": "No GEE WMTS services found",
                    "timestamp": datetime.now().isoformat()
                }
            
        except Exception as e:
            logger.error(f"Error clearing WMTS services: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def update_mapstore_wmts_service(self) -> Dict[str, Any]:
        """
        Update MapStore configuration with new WMTS service.
        
        Returns:
            Update results
        """
        try:
            # Get current WMTS layers from FastAPI
            layers = self.get_wmts_layers()
            
            if not layers:
                logger.warning("No WMTS layers found")
                return {
                    "status": "warning",
                    "message": "No layers found",
                    "layers_found": []
                }
            
            # Get the latest catalog data from Redis
            import requests
            try:
                response = requests.get(f"{self.fastapi_url}/catalog")
                if response.status_code == 200:
                    catalog_response = response.json()
                    catalogs = catalog_response.get('catalogs', [])
                    if catalogs:
                        # Get the most recent catalog
                        latest_catalog = max(catalogs, key=lambda x: x.get('timestamp', ''))
                        project_id = latest_catalog.get('project_id', 'unknown')
                        project_name = latest_catalog.get('project_name', 'GEE Analysis')
                        
                        # Calculate actual AOI extent for MapStore
                        aoi_info = latest_catalog.get('analysis_info', {}).get('aoi', {})
                        if aoi_info and aoi_info.get('bbox'):
                            bbox = aoi_info['bbox']
                            # Handle the bbox format where each coordinate is stored as [x, y] array
                            if isinstance(bbox.get('minx'), list) and len(bbox['minx']) >= 2:
                                # Format: minx: [x, y], miny: [x, y], etc.
                                extent = [
                                    bbox['minx'][0], bbox['miny'][1],  # minx, miny
                                    bbox['maxx'][0], bbox['maxy'][1]   # maxx, maxy
                                ]
                            else:
                                # Fallback to center-based extent if bbox format is unexpected
                                center = aoi_info.get('center', [110.0, -1.0])
                                buffer = 0.1
                                extent = [center[0] - buffer, center[1] - buffer, center[0] + buffer, center[1] + buffer]
                        else:
                            # Fallback to center-based extent if bbox not available
                            center = aoi_info.get('center', [110.0, -1.0])
                            buffer = 0.1
                            extent = [center[0] - buffer, center[1] - buffer, center[0] + buffer, center[1] + buffer]

                        # Create WMTS service configuration that requests capabilities dynamically
                        # Use external URL (localhost:8001) for client access, not internal Docker URL
                        external_fastapi_url = "http://localhost:8001"
                        wmts_service_config = {
                            "url": f"{external_fastapi_url}/wmts",
                            "type": "wmts",
                            "title": "GEE Analysis WMTS",
                            "autoload": False,
                            "description": f"Dynamic WMTS service for GEE analysis - Latest: {project_name}",
                            "params": {
                                "SERVICE": "WMTS",
                                "VERSION": "1.0.0",
                                "REQUEST": "GetCapabilities"
                            }
                        }

                        # Update MapStore configuration with consistent service name
                        update_response = requests.post(
                            f"{self.fastapi_url}/mapstore/wmts/update",
                            json={
                                "service_name": "gee_analysis_wmts",  # Consistent service name
                                "service_config": wmts_service_config
                            }
                        )
                        
                        if update_response.status_code == 200:
                            logger.info(f"Successfully updated MapStore WMTS service: gee_analysis_wmts")
                            return {
                                "status": "success",
                                "service_name": "gee_analysis_wmts",
                                "project_name": project_name,
                                "layers_found": layers,
                                "layers_count": len(layers)
                            }
                        else:
                            logger.error(f"Failed to update MapStore WMTS service: {update_response.status_code}")
                            return {
                                "status": "error",
                                "error": f"MapStore update failed: {update_response.status_code}",
                                "layers_found": layers
                            }
                    else:
                        logger.warning("No catalogs found")
                        return {
                            "status": "warning",
                            "message": "No catalogs found",
                            "layers_found": layers
                        }
                else:
                    logger.error(f"Failed to get catalogs: {response.status_code}")
                    return {
                        "status": "error",
                        "error": f"Failed to get catalogs: {response.status_code}",
                        "layers_found": layers
                    }
            except Exception as e:
                logger.error(f"Error updating MapStore WMTS service: {e}")
                return {
                    "status": "error",
                    "error": str(e),
                    "layers_found": layers
                }
                
        except Exception as e:
            logger.error(f"Error in update_mapstore_wmts_service: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def comprehensive_refresh(self) -> Dict[str, Any]:
        """
        Perform comprehensive WMTS refresh and cleanup.
        This method ensures clean replacement of WMTS services, especially for single layer scenarios.
        
        Returns:
            Comprehensive results
        """
        logger.info("Starting comprehensive WMTS refresh...")
        
        results = {
            "wmts_clear": {},
            "capabilities_refresh": {},
            "mapstore_update": {},
            "layers_found": [],
            "overall_status": "success"
        }
        
        try:
            # Step 1: Clear old WMTS services (complete replacement for single layer)
            logger.info("Clearing old WMTS services...")
            results["wmts_clear"] = self.clear_old_wmts_services()
            
            if results["wmts_clear"].get("status") != "success":
                logger.warning(f"WMTS clear had issues: {results['wmts_clear']}")
            
            # Step 2: Refresh WMTS capabilities
            logger.info("Refreshing WMTS capabilities...")
            results["capabilities_refresh"] = self.force_wmts_refresh()
            
            if results["capabilities_refresh"].get("status") != "success":
                logger.warning(f"Capabilities refresh had issues: {results['capabilities_refresh']}")
            
            # Step 3: Update MapStore with new WMTS service
            logger.info("Updating MapStore WMTS service...")
            results["mapstore_update"] = self.update_mapstore_wmts_service()
            
            if results["mapstore_update"].get("status") != "success":
                logger.error(f"MapStore update failed: {results['mapstore_update']}")
                results["overall_status"] = "error"
                return results
            
            # Step 4: Get current layers
            logger.info("Getting current WMTS layers...")
            results["layers_found"] = self.get_wmts_layers()
            
            logger.info(f"Comprehensive WMTS refresh completed successfully - Found {len(results['layers_found'])} layers")
            return results
            
        except Exception as e:
            logger.error(f"Error during comprehensive refresh: {e}")
            results["overall_status"] = "error"
            results["error"] = str(e)
            return results


# Convenience functions for direct use
def get_wmts_layers(fastapi_url: str = "http://localhost:8000") -> List[str]:
    """
    Get list of available WMTS layers.
    
    Args:
        fastapi_url: FastAPI service URL
    
    Returns:
        List of layer names
    """
    utils = GEEIntegrationUtils(fastapi_url)
    return utils.get_wmts_layers()


def force_wmts_refresh(fastapi_url: str = "http://localhost:8000") -> Dict[str, Any]:
    """
    Force refresh WMTS capabilities.
    
    Args:
        fastapi_url: FastAPI service URL
    
    Returns:
        Refresh results
    """
    utils = GEEIntegrationUtils(fastapi_url)
    return utils.force_wmts_refresh()


def comprehensive_wmts_refresh(fastapi_url: str = "http://localhost:8000") -> Dict[str, Any]:
    """
    Perform comprehensive WMTS refresh and cleanup.
    
    Args:
        fastapi_url: FastAPI service URL
    
    Returns:
        Comprehensive results
    """
    utils = GEEIntegrationUtils(fastapi_url)
    return utils.comprehensive_refresh()


def process_gee_analysis_with_cache_management(map_layers: Dict[str, Any],
                                             project_name: str = "GEE Analysis",
                                             aoi_info: Optional[Dict[str, Any]] = None,
                                             fastapi_url: str = "http://localhost:8000",
                                             clear_cache_first: bool = True) -> Dict[str, Any]:
    """
    Process GEE analysis with comprehensive cache management.
    
    Args:
        map_layers: Dictionary of GEE map layers with tile URLs
        project_name: Human-readable project name
        aoi_info: Area of interest information
        fastapi_url: FastAPI service URL
        clear_cache_first: Whether to clear cache before processing
    
    Returns:
        Dictionary with processing results
    """
    try:
        from cache_manager import CacheManager
        from gee_integration import GEEIntegrationManager
        
        # Clear cache first if requested
        if clear_cache_first:
            print("🧹 Clearing cache before processing...")
            cache_manager = CacheManager()
            cache_result = cache_manager.clear_cache("all")
            if cache_result.get("status") != "success":
                print("⚠️  Cache clearing failed, but continuing with analysis...")
        
        # Process the analysis
        manager = GEEIntegrationManager(fastapi_url=fastapi_url)
        result = manager.process_gee_analysis(map_layers, project_name, aoi_info)
        
        return result
        
    except Exception as e:
        print(f"❌ Error processing GEE analysis: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


def get_comprehensive_service_status(fastapi_url: str = "http://localhost:8000") -> Dict[str, Any]:
    """
    Get comprehensive status of all services including cache, WMTS, and FastAPI.
    
    Args:
        fastapi_url: FastAPI service URL
    
    Returns:
        Dictionary with comprehensive service status
    """
    try:
        from cache_manager import CacheManager
        from gee_integration import GEEIntegrationManager
        
        # Get cache status
        cache_manager = CacheManager()
        cache_status = cache_manager.get_cache_status()
        
        # Get WMTS status
        wmts_utils = GEEIntegrationUtils(fastapi_url)
        wmts_layers = wmts_utils.get_wmts_layers()
        
        # Get FastAPI status
        manager = GEEIntegrationManager(fastapi_url=fastapi_url)
        service_status = manager.get_service_status()
        
        return {
            "cache": cache_status,
            "wmts": {
                "status": "active" if wmts_layers else "inactive",
                "layers_count": len(wmts_layers),
                "layers_available": wmts_layers
            },
            "fastapi": service_status.get("fastapi", {}),
            "overall_status": "healthy" if cache_status.get("total_keys", 0) >= 0 else "unknown",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
