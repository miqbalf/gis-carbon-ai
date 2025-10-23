"""
Cache Management Module for FastAPI GEE Service

This module provides utilities for managing Redis cache operations,
including clearing cache entries and monitoring cache status.
"""

import redis
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class CacheManager:
    """
    Manages Redis cache operations for the GEE service.
    """
    
    def __init__(self, redis_url: str = "redis://redis:6379"):
        """
        Initialize the cache manager.
        
        Args:
            redis_url: Redis connection URL
        """
        self.redis_url = redis_url
        self.redis_client = redis.from_url(redis_url)
    
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
