"""
Unified GEE Interface

This module provides a unified interface for all GEE-related operations,
combining geometry processing, cache management, and WMTS operations.
It can be used from notebooks, web applications, or any other context.
"""

import sys
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class UnifiedGEEInterface:
    """
    Unified interface for all GEE operations including geometry processing,
    cache management, and WMTS operations.
    """
    
    def __init__(self, fastapi_url: str = "http://localhost:8000"):
        """
        Initialize the unified GEE interface.
        
        Args:
            fastapi_url: FastAPI service URL
        """
        self.fastapi_url = fastapi_url
        
        # Import modules
        try:
            from cache_manager import CacheManager
            from gee_utils import GEEIntegrationUtils, process_gee_analysis_with_cache_management
            from gee_integration import GEEIntegrationManager
            from wmts_config_updater import WMTSConfigUpdater
            from gee_catalog_updater import GEECatalogUpdater
            
            self.cache_manager = CacheManager()
            self.wmts_utils = GEEIntegrationUtils(fastapi_url)
            self.gee_manager = GEEIntegrationManager(fastapi_url=fastapi_url)
            self.process_with_cache = process_gee_analysis_with_cache_management
            self.wmts_config_updater = WMTSConfigUpdater()
            self.catalog_updater = GEECatalogUpdater(fastapi_url)
            
        except ImportError as e:
            logger.warning(f"Some modules not available: {e}")
            self.cache_manager = None
            self.wmts_utils = None
            self.gee_manager = None
            self.process_with_cache = None
    
    def process_aoi_geometry(self, AOI_geom) -> Dict[str, Any]:
        """
        Process AOI geometry using the osi.utils module.
        
        Args:
            AOI_geom: Earth Engine Geometry object
        
        Returns:
            Dictionary containing AOI information
        """
        try:
            # Try to import from the organized osi.utils module
            sys.path.append('/usr/src/app/gee_lib')
            from osi.utils.main import process_aoi_geometry
            
            return process_aoi_geometry(AOI_geom)
            
        except ImportError:
            # Fallback method if osi.utils is not available
            logger.warning("osi.utils module not available, using fallback method")
            return self._fallback_aoi_processing(AOI_geom)
    
    def _fallback_aoi_processing(self, AOI_geom) -> Dict[str, Any]:
        """
        Fallback AOI processing method.
        
        Args:
            AOI_geom: Earth Engine Geometry object
        
        Returns:
            Dictionary containing AOI information
        """
        try:
            # Get coordinates
            coords = AOI_geom.coordinates().getInfo()
            
            # Get center with error handling
            try:
                center = AOI_geom.centroid(maxError=1).coordinates().getInfo()
            except:
                try:
                    bounds = AOI_geom.bounds().getInfo()
                    if bounds and 'coordinates' in bounds:
                        coords_bounds = bounds['coordinates'][0]
                        if len(coords_bounds) >= 4:
                            center = [
                                (coords_bounds[0][0] + coords_bounds[2][0]) / 2,
                                (coords_bounds[0][1] + coords_bounds[2][1]) / 2
                            ]
                        else:
                            center = coords[0] if coords else [0, 0]
                    else:
                        center = coords[0] if coords else [0, 0]
                except:
                    center = coords[0] if coords else [0, 0]
            
            # Calculate bounding box
            if coords:
                lons = [coord[0] for coord in coords]
                lats = [coord[1] for coord in coords]
                bbox = {
                    'minx': min(lons),
                    'miny': min(lats),
                    'maxx': max(lons),
                    'maxy': max(lats)
                }
            else:
                bbox = None
            
            # Calculate area
            try:
                area_km2 = AOI_geom.area().divide(1e6).getInfo()
            except:
                area_km2 = None
            
            return {
                'bbox': bbox,
                'center': center,
                'coordinates': coords,
                'area_km2': area_km2
            }
            
        except Exception as e:
            logger.error(f"Error in fallback AOI processing: {e}")
            return {
                'bbox': None,
                'center': [0, 0],
                'coordinates': None,
                'area_km2': None
            }
    
    def clear_cache(self, cache_type: str = "all") -> Dict[str, Any]:
        """
        Clear Redis cache entries.
        
        Args:
            cache_type: Type of cache to clear (all, tiles, catalogs, projects, layers)
        
        Returns:
            Dictionary with clearing results
        """
        if not self.cache_manager:
            return {"status": "error", "error": "Cache manager not available"}
        
        try:
            result = self.cache_manager.clear_cache(cache_type)
            if result["status"] == "success":
                logger.info(f"✅ Cache cleared successfully: {result['cleared_count']} entries")
            return result
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return {"status": "error", "error": str(e)}
    
    def get_cache_status(self) -> Dict[str, Any]:
        """
        Get current cache status and statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        if not self.cache_manager:
            return {"status": "error", "error": "Cache manager not available"}
        
        try:
            return self.cache_manager.get_cache_status()
        except Exception as e:
            logger.error(f"Error getting cache status: {e}")
            return {"status": "error", "error": str(e)}
    
    def refresh_wmts(self) -> Dict[str, Any]:
        """
        Force refresh WMTS capabilities.
        
        Returns:
            Dictionary with refresh results
        """
        if not self.wmts_utils:
            return {"status": "error", "error": "WMTS utils not available"}
        
        try:
            result = self.wmts_utils.force_wmts_refresh()
            if result["status"] == "success":
                logger.info("✅ WMTS capabilities refreshed successfully")
            return result
        except Exception as e:
            logger.error(f"Error refreshing WMTS: {e}")
            return {"status": "error", "error": str(e)}
    
    def get_wmts_layers(self) -> List[str]:
        """
        Get list of available WMTS layers.
        
        Returns:
            List of layer names
        """
        if not self.wmts_utils:
            return []
        
        try:
            layers = self.wmts_utils.get_wmts_layers()
            logger.info(f"Found {len(layers)} WMTS layers")
            return layers
        except Exception as e:
            logger.error(f"Error getting WMTS layers: {e}")
            return []
    
    def process_gee_analysis(self, map_layers: Dict[str, Any],
                           project_name: str = "GEE Analysis",
                           aoi_info: Optional[Dict[str, Any]] = None,
                           clear_cache_first: bool = True) -> Dict[str, Any]:
        """
        Process GEE analysis with comprehensive cache management.
        
        Args:
            map_layers: Dictionary of GEE map layers with tile URLs
            project_name: Human-readable project name
            aoi_info: Area of interest information
            clear_cache_first: Whether to clear cache before processing
        
        Returns:
            Dictionary with processing results
        """
        if not self.process_with_cache:
            return {"status": "error", "error": "GEE processing not available"}
        
        try:
            result = self.process_with_cache(
                map_layers=map_layers,
                project_name=project_name,
                aoi_info=aoi_info,
                fastapi_url=self.fastapi_url,
                clear_cache_first=clear_cache_first
            )
            
            if result.get("status") == "success":
                logger.info(f"✅ GEE analysis processed successfully: {result.get('project_id')}")
            return result
            
        except Exception as e:
            logger.error(f"Error processing GEE analysis: {e}")
            return {"status": "error", "error": str(e)}
    
    def get_service_status(self) -> Dict[str, Any]:
        """
        Get comprehensive status of all services.
        
        Returns:
            Dictionary with service status
        """
        if not self.gee_manager:
            return {"status": "error", "error": "GEE manager not available"}
        
        try:
            return self.gee_manager.get_service_status()
        except Exception as e:
            logger.error(f"Error getting service status: {e}")
            return {"status": "error", "error": str(e)}
    
    def update_wmts_configuration(self, project_id: str, project_name: str, 
                                 aoi_info: Dict[str, Any], 
                                 replace_existing: bool = True) -> Dict[str, Any]:
        """
        Update WMTS configuration for MapStore.
        
        Args:
            project_id: GEE analysis project ID
            project_name: Human-readable project name
            aoi_info: Area of interest information
            replace_existing: Whether to replace existing services
        
        Returns:
            Dictionary with update results
        """
        if not hasattr(self, 'wmts_config_updater') or not self.wmts_config_updater:
            return {"status": "error", "error": "WMTS config updater not available"}
        
        try:
            success = self.wmts_config_updater.update_wmts_configuration(
                project_id, project_name, aoi_info, replace_existing
            )
            
            if success:
                logger.info("✅ WMTS configuration updated successfully")
                return {
                    "status": "success",
                    "message": "WMTS configuration updated successfully",
                    "project_id": project_id,
                    "project_name": project_name
                }
            else:
                return {
                    "status": "error",
                    "message": "Failed to update WMTS configuration"
                }
                
        except Exception as e:
            logger.error(f"Error updating WMTS configuration: {e}")
            return {"status": "error", "error": str(e)}
    
    def get_wmts_configuration_status(self) -> Dict[str, Any]:
        """
        Get current WMTS configuration status.
        
        Returns:
            Dictionary with WMTS configuration status
        """
        if not hasattr(self, 'wmts_config_updater') or not self.wmts_config_updater:
            return {"status": "error", "error": "WMTS config updater not available"}
        
        try:
            wmts_info = self.wmts_config_updater.get_current_wmts_info()
            gee_services = self.wmts_config_updater.list_all_gee_services()
            
            return {
                "status": "success",
                "current_wmts": wmts_info,
                "all_gee_services": gee_services,
                "services_count": len(gee_services)
            }
            
        except Exception as e:
            logger.error(f"Error getting WMTS configuration status: {e}")
            return {"status": "error", "error": str(e)}
    
    def update_catalog(self, project_id: str, project_name: str, 
                      layers: Dict[str, Any], analysis_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Update MapStore catalog with GEE analysis results.
        
        Args:
            project_id: Unique project identifier
            project_name: Human-readable project name
            layers: Dictionary of layer information
            analysis_info: Additional analysis metadata
        
        Returns:
            Dictionary with catalog update results
        """
        if not hasattr(self, 'catalog_updater') or not self.catalog_updater:
            return {"status": "error", "error": "Catalog updater not available"}
        
        try:
            result = self.catalog_updater.push_gee_results(
                project_id=project_id,
                project_name=project_name,
                layers=layers,
                analysis_info=analysis_info
            )
            
            if result:
                logger.info("✅ Catalog updated successfully")
                return {
                    "status": "success",
                    "message": "Catalog updated successfully",
                    "result": result
                }
            else:
                return {
                    "status": "error",
                    "message": "Failed to update catalog"
                }
                
        except Exception as e:
            logger.error(f"Error updating catalog: {e}")
            return {"status": "error", "error": str(e)}
    
    def get_catalog_info(self, project_id: str) -> Dict[str, Any]:
        """
        Get catalog information for a specific project.
        
        Args:
            project_id: Project ID to get information for
        
        Returns:
            Dictionary with catalog information
        """
        if not hasattr(self, 'catalog_updater') or not self.catalog_updater:
            return {"status": "error", "error": "Catalog updater not available"}
        
        try:
            result = self.catalog_updater.get_catalog_info(project_id)
            if result:
                return {
                    "status": "success",
                    "catalog_info": result
                }
            else:
                return {
                    "status": "error",
                    "message": "No catalog information found"
                }
                
        except Exception as e:
            logger.error(f"Error getting catalog info: {e}")
            return {"status": "error", "error": str(e)}
    
    def list_catalogs(self) -> Dict[str, Any]:
        """
        List all available catalogs.
        
        Returns:
            Dictionary with catalog list
        """
        if not hasattr(self, 'catalog_updater') or not self.catalog_updater:
            return {"status": "error", "error": "Catalog updater not available"}
        
        try:
            result = self.catalog_updater.list_catalogs()
            if result:
                return {
                    "status": "success",
                    "catalogs": result
                }
            else:
                return {
                    "status": "error",
                    "message": "Failed to list catalogs"
                }
                
        except Exception as e:
            logger.error(f"Error listing catalogs: {e}")
            return {"status": "error", "error": str(e)}
    
    def comprehensive_workflow(self, AOI_geom, map_layers: Dict[str, Any],
                             project_name: str = "GEE Analysis",
                             clear_cache_first: bool = True) -> Dict[str, Any]:
        """
        Complete workflow: process AOI, clear cache, and process GEE analysis.
        
        Args:
            AOI_geom: Earth Engine Geometry object
            map_layers: Dictionary of GEE map layers with tile URLs
            project_name: Human-readable project name
            clear_cache_first: Whether to clear cache before processing
        
        Returns:
            Dictionary with complete workflow results
        """
        logger.info("🚀 Starting comprehensive GEE workflow...")
        
        results = {
            "aoi_processing": {},
            "cache_clearing": {},
            "gee_analysis": {},
            "wmts_configuration": {},
            "overall_status": "success"
        }
        
        try:
            # Step 1: Process AOI geometry
            logger.info("1️⃣ Processing AOI geometry...")
            results["aoi_processing"] = self.process_aoi_geometry(AOI_geom)
            
            # Step 2: Clear cache if requested
            if clear_cache_first:
                logger.info("2️⃣ Clearing cache...")
                results["cache_clearing"] = self.clear_cache("all")
            
            # Step 3: Process GEE analysis
            logger.info("3️⃣ Processing GEE analysis...")
            results["gee_analysis"] = self.process_gee_analysis(
                map_layers=map_layers,
                project_name=project_name,
                aoi_info=results["aoi_processing"],
                clear_cache_first=False  # Already cleared above
            )
            
            # Step 4: Update WMTS configuration
            if results["gee_analysis"].get("status") == "success":
                logger.info("4️⃣ Updating WMTS configuration...")
                project_id = results["gee_analysis"].get("project_id")
                if project_id:
                    results["wmts_configuration"] = self.update_wmts_configuration(
                        project_id=project_id,
                        project_name=project_name,
                        aoi_info=results["aoi_processing"],
                        replace_existing=True
                    )
                else:
                    results["wmts_configuration"] = {"status": "error", "error": "No project ID from GEE analysis"}
            else:
                results["wmts_configuration"] = {"status": "skipped", "reason": "GEE analysis failed"}
            
            # Check overall success
            if (results["aoi_processing"].get("center") != [0, 0] and
                results["gee_analysis"].get("status") == "success" and
                results["wmts_configuration"].get("status") == "success"):
                logger.info("✅ Comprehensive workflow completed successfully")
            else:
                results["overall_status"] = "partial_success"
                logger.warning("⚠️  Workflow completed with some issues")
            
            return results
            
        except Exception as e:
            logger.error(f"Error in comprehensive workflow: {e}")
            results["overall_status"] = "error"
            results["error"] = str(e)
            return results


# Convenience functions for direct use
def create_unified_interface(fastapi_url: str = "http://localhost:8000") -> UnifiedGEEInterface:
    """
    Create a unified GEE interface instance.
    
    Args:
        fastapi_url: FastAPI service URL
    
    Returns:
        UnifiedGEEInterface instance
    """
    return UnifiedGEEInterface(fastapi_url)


def process_aoi_geometry_unified(AOI_geom, fastapi_url: str = "http://localhost:8000") -> Dict[str, Any]:
    """
    Process AOI geometry using the unified interface.
    
    Args:
        AOI_geom: Earth Engine Geometry object
        fastapi_url: FastAPI service URL
    
    Returns:
        Dictionary containing AOI information
    """
    interface = UnifiedGEEInterface(fastapi_url)
    return interface.process_aoi_geometry(AOI_geom)


def clear_cache_unified(cache_type: str = "all", fastapi_url: str = "http://localhost:8000") -> Dict[str, Any]:
    """
    Clear cache using the unified interface.
    
    Args:
        cache_type: Type of cache to clear
        fastapi_url: FastAPI service URL
    
    Returns:
        Dictionary with clearing results
    """
    interface = UnifiedGEEInterface(fastapi_url)
    return interface.clear_cache(cache_type)


def process_gee_analysis_unified(map_layers: Dict[str, Any],
                                project_name: str = "GEE Analysis",
                                aoi_info: Optional[Dict[str, Any]] = None,
                                clear_cache_first: bool = True,
                                fastapi_url: str = "http://localhost:8000") -> Dict[str, Any]:
    """
    Process GEE analysis using the unified interface.
    
    Args:
        map_layers: Dictionary of GEE map layers with tile URLs
        project_name: Human-readable project name
        aoi_info: Area of interest information
        clear_cache_first: Whether to clear cache before processing
        fastapi_url: FastAPI service URL
    
    Returns:
        Dictionary with processing results
    """
    interface = UnifiedGEEInterface(fastapi_url)
    return interface.process_gee_analysis(map_layers, project_name, aoi_info, clear_cache_first)


def comprehensive_workflow_unified(AOI_geom, map_layers: Dict[str, Any],
                                 project_name: str = "GEE Analysis",
                                 clear_cache_first: bool = True,
                                 fastapi_url: str = "http://localhost:8000") -> Dict[str, Any]:
    """
    Complete workflow using the unified interface.
    
    Args:
        AOI_geom: Earth Engine Geometry object
        map_layers: Dictionary of GEE map layers with tile URLs
        project_name: Human-readable project name
        clear_cache_first: Whether to clear cache before processing
        fastapi_url: FastAPI service URL
    
    Returns:
        Dictionary with complete workflow results
    """
    interface = UnifiedGEEInterface(fastapi_url)
    return interface.comprehensive_workflow(AOI_geom, map_layers, project_name, clear_cache_first)
