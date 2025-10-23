"""
Cache Management Module for FastAPI GEE Service

This module provides utilities for managing Redis cache operations,
including clearing cache entries and monitoring cache status.
"""

import redis
import json
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class CacheManager:
    """
    Manages Redis cache operations for the GEE service.
    """
    
    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialize the cache manager.
        
        Args:
            redis_url: Redis connection URL (defaults to REDIS_URL env var or redis://redis:6379)
        """
        self.redis_url = redis_url or os.getenv('REDIS_URL', 'redis://redis:6379')
        self.redis_client = redis.from_url(self.redis_url)
    
    def clear_cache(self, cache_type: str = "all") -> Dict[str, Any]:
        """
        Clear Redis cache entries by type.
        
        Args:
            cache_type: Type of cache to clear (all, tiles, catalogs, projects, layers)
        
        Returns:
            Dictionary with clearing results
        """
        try:
            cleared_keys = []
            
            if cache_type in ["all", "tiles"]:
                # Clear tile cache
                tile_keys = self.redis_client.keys("tile:*")
                if tile_keys:
                    self.redis_client.delete(*tile_keys)
                    cleared_keys.extend([k.decode() for k in tile_keys])
                    logger.info(f"Cleared {len(tile_keys)} tile cache entries")
            
            if cache_type in ["all", "catalogs"]:
                # Clear catalog cache
                catalog_keys = self.redis_client.keys("catalog:*")
                if catalog_keys:
                    self.redis_client.delete(*catalog_keys)
                    cleared_keys.extend([k.decode() for k in catalog_keys])
                    logger.info(f"Cleared {len(catalog_keys)} catalog cache entries")
            
            if cache_type in ["all", "projects"]:
                # Clear project cache
                project_keys = self.redis_client.keys("project:*")
                if project_keys:
                    self.redis_client.delete(*project_keys)
                    cleared_keys.extend([k.decode() for k in project_keys])
                    logger.info(f"Cleared {len(project_keys)} project cache entries")
            
            if cache_type in ["all", "layers"]:
                # Clear layer cache
                layer_keys = self.redis_client.keys("catalog_layer:*")
                if layer_keys:
                    self.redis_client.delete(*layer_keys)
                    cleared_keys.extend([k.decode() for k in layer_keys])
                    logger.info(f"Cleared {len(layer_keys)} layer cache entries")
            
            return {
                "status": "success",
                "cache_type": cache_type,
                "cleared_count": len(cleared_keys),
                "cleared_keys": cleared_keys,
                "timestamp": datetime.now().isoformat(),
                "message": f"Successfully cleared {cache_type} cache"
            }
            
        except Exception as e:
            logger.error(f"Error clearing cache: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def clear_duplicate_projects(self, new_project_name: str, new_aoi_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clear only duplicate projects based on project name and AOI analysis parameters.
        This prevents clearing all data and only removes true duplicates.
        
        Args:
            new_project_name: Name of the new project being processed
            new_aoi_info: AOI information for the new project
        
        Returns:
            Dictionary with clearing results
        """
        try:
            cleared_keys = []
            kept_projects = []
            
            # Get all catalog entries
            catalog_keys = self.redis_client.keys("catalog:*")
            
            if not catalog_keys:
                logger.info("No existing catalog entries to check for duplicates")
                return {
                    "status": "success",
                    "cache_type": "duplicates",
                    "cleared_count": 0,
                    "cleared_keys": [],
                    "kept_projects": [],
                    "timestamp": datetime.now().isoformat(),
                    "message": "No existing projects to check for duplicates"
                }
            
            # Extract AOI signature for comparison
            new_aoi_signature = self._get_aoi_signature(new_aoi_info)
            
            for catalog_key in catalog_keys:
                try:
                    catalog_data = self.redis_client.get(catalog_key)
                    if catalog_data:
                        catalog_info = json.loads(catalog_data)
                        existing_project_name = catalog_info.get('project_name', '')
                        existing_aoi_info = catalog_info.get('analysis_info', {}).get('aoi', {})
                        existing_aoi_signature = self._get_aoi_signature(existing_aoi_info)
                        
                        # Check if this is a duplicate based on project name and AOI
                        is_duplicate = (
                            existing_project_name.lower() == new_project_name.lower() and
                            existing_aoi_signature == new_aoi_signature
                        )
                        
                        if is_duplicate:
                            # This is a duplicate - clear it
                            catalog_key_str = catalog_key.decode()
                            self.redis_client.delete(catalog_key)
                            cleared_keys.append(catalog_key_str)
                            
                            # Also clear related layer entries
                            project_id = catalog_info.get('project_id', '')
                            if project_id:
                                layer_keys = self.redis_client.keys(f"catalog_layer:{project_id}:*")
                                if layer_keys:
                                    self.redis_client.delete(*layer_keys)
                                    cleared_keys.extend([k.decode() for k in layer_keys])
                            
                            logger.info(f"Cleared duplicate project: {existing_project_name} (AOI: {existing_aoi_signature})")
                        else:
                            # Keep this project - it's not a duplicate
                            kept_projects.append({
                                'project_name': existing_project_name,
                                'project_id': catalog_info.get('project_id', ''),
                                'aoi_signature': existing_aoi_signature
                            })
                            
                except Exception as e:
                    logger.warning(f"Error processing catalog key {catalog_key}: {e}")
                    continue
            
            logger.info(f"Cleared {len(cleared_keys)} duplicate entries, kept {len(kept_projects)} unique projects")
            
            return {
                "status": "success",
                "cache_type": "duplicates",
                "cleared_count": len(cleared_keys),
                "cleared_keys": cleared_keys,
                "kept_projects": kept_projects,
                "timestamp": datetime.now().isoformat(),
                "message": f"Cleared {len(cleared_keys)} duplicate projects, kept {len(kept_projects)} unique projects"
            }
            
        except Exception as e:
            logger.error(f"Error clearing duplicate projects: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _get_aoi_signature(self, aoi_info: Dict[str, Any]) -> str:
        """
        Generate a signature for AOI information to identify duplicates.
        
        Args:
            aoi_info: AOI information dictionary
        
        Returns:
            String signature for the AOI
        """
        try:
            if not aoi_info:
                return "no_aoi"
            
            # Extract key AOI parameters for comparison
            bbox = aoi_info.get('bbox', {})
            center = aoi_info.get('center', [])
            coordinates = aoi_info.get('coordinates', [])
            
            # Create signature from bbox (most reliable for duplicate detection)
            if bbox and isinstance(bbox, dict):
                bbox_values = [
                    round(float(bbox.get('minx', 0)), 6),
                    round(float(bbox.get('miny', 0)), 6),
                    round(float(bbox.get('maxx', 0)), 6),
                    round(float(bbox.get('maxy', 0)), 6)
                ]
                return f"bbox_{'_'.join(map(str, bbox_values))}"
            
            # Fallback to center coordinates
            elif center and len(center) >= 2:
                center_values = [
                    round(float(center[0]), 6),
                    round(float(center[1]), 6)
                ]
                return f"center_{'_'.join(map(str, center_values))}"
            
            # Last fallback
            else:
                return "unknown_aoi"
                
        except Exception as e:
            logger.warning(f"Error generating AOI signature: {e}")
            return "error_aoi"
    
    def get_cache_status(self) -> Dict[str, Any]:
        """
        Get current cache status and statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        try:
            # Get all keys
            all_keys = self.redis_client.keys("*")
            
            # Count different types
            tile_keys = self.redis_client.keys("tile:*")
            catalog_keys = self.redis_client.keys("catalog:*")
            project_keys = self.redis_client.keys("project:*")
            layer_keys = self.redis_client.keys("catalog_layer:*")
            
            return {
                "total_keys": len(all_keys),
                "tile_keys": len(tile_keys),
                "catalog_keys": len(catalog_keys),
                "project_keys": len(project_keys),
                "layer_keys": len(layer_keys),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting cache status: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def clear_project_cache(self, project_id: str) -> Dict[str, Any]:
        """
        Clear cache for a specific project.
        
        Args:
            project_id: Project ID to clear cache for
        
        Returns:
            Dictionary with clearing results
        """
        try:
            cleared_keys = []
            
            # Clear project-specific cache
            project_keys = self.redis_client.keys(f"*{project_id}*")
            if project_keys:
                self.redis_client.delete(*project_keys)
                cleared_keys.extend([k.decode() for k in project_keys])
                logger.info(f"Cleared {len(project_keys)} cache entries for project {project_id}")
            
            return {
                "status": "success",
                "project_id": project_id,
                "cleared_count": len(cleared_keys),
                "cleared_keys": cleared_keys,
                "timestamp": datetime.now().isoformat(),
                "message": f"Successfully cleared cache for project {project_id}"
            }
            
        except Exception as e:
            logger.error(f"Error clearing project cache: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def get_catalog_info(self, project_id: str) -> Optional[Dict[str, Any]]:
        """
        Get catalog information for a specific project.
        
        Args:
            project_id: Project ID
        
        Returns:
            Catalog information or None if not found
        """
        try:
            catalog_key = f"catalog:{project_id}"
            catalog_data = self.redis_client.get(catalog_key)
            
            if catalog_data:
                return json.loads(catalog_data)
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error getting catalog info: {str(e)}")
            return None
    
    def list_all_catalogs(self) -> List[Dict[str, Any]]:
        """
        List all available catalogs.
        
        Returns:
            List of catalog information
        """
        try:
            catalog_keys = self.redis_client.keys("catalog:*")
            catalogs = []
            
            for key in catalog_keys:
                catalog_data = self.redis_client.get(key)
                if catalog_data:
                    catalog_info = json.loads(catalog_data)
                    catalogs.append({
                        "project_id": catalog_info.get("project_id"),
                        "project_name": catalog_info.get("project_name"),
                        "layers_count": len(catalog_info.get("layers", {})),
                        "timestamp": catalog_info.get("timestamp"),
                        "status": catalog_info.get("status")
                    })
            
            return catalogs
            
        except Exception as e:
            logger.error(f"Error listing catalogs: {str(e)}")
            return []


# Convenience functions for direct use
def clear_redis_cache(cache_type: str = "all", redis_url: str = "redis://redis:6379") -> Dict[str, Any]:
    """
    Clear Redis cache entries.
    
    Args:
        cache_type: Type of cache to clear
        redis_url: Redis connection URL
    
    Returns:
        Clearing results
    """
    manager = CacheManager(redis_url)
    return manager.clear_cache(cache_type)


def get_cache_status(redis_url: str = "redis://redis:6379") -> Dict[str, Any]:
    """
    Get cache status.
    
    Args:
        redis_url: Redis connection URL
    
    Returns:
        Cache status
    """
    manager = CacheManager(redis_url)
    return manager.get_cache_status()


def clear_project_cache(project_id: str, redis_url: str = "redis://redis:6379") -> Dict[str, Any]:
    """
    Clear cache for a specific project.
    
    Args:
        project_id: Project ID
        redis_url: Redis connection URL
    
    Returns:
        Clearing results
    """
    manager = CacheManager(redis_url)
    return manager.clear_project_cache(project_id)
