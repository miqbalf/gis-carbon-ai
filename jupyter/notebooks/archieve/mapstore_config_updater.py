#!/usr/bin/env python3
"""
MapStore Configuration Updater

This module provides functionality to programmatically update MapStore's localConfig.json
with TMS layers generated from GEE analysis results.
"""

import json
import os
import shutil
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MapStoreConfigUpdater:
    """
    A class to manage MapStore configuration updates with TMS layers
    """
    
    def __init__(self, config_path: str = "/usr/src/app/mapstore/config/localConfig.json"):
        """
        Initialize the MapStore config updater
        
        Args:
            config_path: Path to the localConfig.json file
        """
        self.config_path = config_path
        self.backup_path = f"{config_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
    def backup_config(self) -> bool:
        """
        Create a backup of the current configuration
        
        Returns:
            bool: True if backup was successful, False otherwise
        """
        try:
            if os.path.exists(self.config_path):
                shutil.copy2(self.config_path, self.backup_path)
                logger.info(f"Configuration backed up to: {self.backup_path}")
                return True
            else:
                logger.warning(f"Configuration file not found: {self.config_path}")
                return False
        except Exception as e:
            logger.error(f"Failed to backup configuration: {e}")
            return False
    
    def load_config(self) -> Optional[Dict[str, Any]]:
        """
        Load the current MapStore configuration
        
        Returns:
            Dict containing the configuration or None if failed
        """
        try:
            # Ensure the directory exists
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            
            # Check if file exists
            if not os.path.exists(self.config_path):
                logger.error(f"Configuration file does not exist: {self.config_path}")
                return None
                
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                logger.info("Configuration loaded successfully")
                return config
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            return None
    
    def save_config(self, config: Dict[str, Any]) -> bool:
        """
        Save the configuration to file
        
        Args:
            config: Configuration dictionary to save
            
        Returns:
            bool: True if save was successful, False otherwise
        """
        try:
            # Ensure the directory exists
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
                logger.info("Configuration saved successfully")
                return True
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            return False
    
    def remove_old_gee_layers(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove old GEE layers from the configuration
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Updated configuration dictionary
        """
        services = config.get("initialState", {}).get("defaultState", {}).get("catalog", {}).get("default", {}).get("services", {})
        
        # Remove old GEE layers (those starting with 'gee_' or 'fastapi_gee_')
        layers_to_remove = []
        for service_name in services.keys():
            if service_name.startswith(('gee_', 'fastapi_gee_')):
                layers_to_remove.append(service_name)
        
        for layer_name in layers_to_remove:
            del services[layer_name]
            logger.info(f"Removed old GEE layer: {layer_name}")
        
        return config
    
    def add_tms_layers(self, config: Dict[str, Any], project_id: str, layers_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add TMS layers to the configuration (standard MapStore format)
        
        Args:
            config: Configuration dictionary
            project_id: Project identifier
            layers_data: Dictionary containing layer information
            
        Returns:
            Updated configuration dictionary
        """
        services = config.get("initialState", {}).get("defaultState", {}).get("catalog", {}).get("default", {}).get("services", {})
        
        # Add new TMS layers
        for layer_name, layer_info in layers_data.get('layers', {}).items():
            service_name = f"gee_{project_id}_{layer_name}"
            
            # Create TMS service configuration (standard MapStore format)
            tms_service = {
                "url": f"http://localhost:8001/tms/{project_id}/{layer_name}/{{z}}/{{x}}/{{y}}.png",
                "type": "tms",
                "title": f"GEE {layer_info.get('name', layer_name).title()}",
                "autoload": False,
                "description": layer_info.get('description', f"GEE analysis layer: {layer_name}"),
                "metadata": {
                    "project_id": project_id,
                    "layer_name": layer_name,
                    "analysis_date": datetime.now().isoformat(),
                    "satellite": layers_data.get('analysis_params', {}).get('satellite', 'Unknown'),
                    "date_range": layers_data.get('analysis_params', {}).get('date_range', 'Unknown')
                }
            }
            
            services[service_name] = tms_service
            logger.info(f"Added TMS layer: {service_name}")
        
        return config
    
    def update_initial_map_state(self, config: Dict[str, Any], aoi_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update the initial map state with AOI information for better initial view
        
        Args:
            config: Configuration dictionary
            aoi_info: AOI information dictionary
            
        Returns:
            Updated configuration dictionary
        """
        # Find the Map plugin configuration
        plugins = config.get("plugins", {})
        desktop_plugins = plugins.get("desktop", [])
        
        for plugin in desktop_plugins:
            if isinstance(plugin, dict) and plugin.get("name") == "Map":
                plugin_cfg = plugin.get("cfg", {})
                
                # Always update the initial map state to center on the analysis area
                logger.info("Updating initial map state to center on analysis area")
                
                # Set center and zoom based on AOI
                center = aoi_info.get('center', [110.0, -1.0])
                if center:
                    plugin_cfg["initialMapState"] = {
                        "center": {
                            "x": center[0],
                            "y": center[1],
                            "crs": "EPSG:4326"
                        },
                        "zoom": 10
                    }
                    
                    # Set bbox
                    coordinates = aoi_info.get('coordinates', [])
                    if coordinates and len(coordinates) > 0:
                        lons = [coord[0] for coord in coordinates]
                        lats = [coord[1] for coord in coordinates]
                        
                        plugin_cfg["initialMapState"]["bbox"] = {
                            "bounds": {
                                "minx": min(lons),
                                "miny": min(lats),
                                "maxx": max(lons),
                                "maxy": max(lats),
                                "crs": "EPSG:4326"
                            }
                        }
                    
                    logger.info("Updated initial map state to center on analysis area")
                break
        
        return config
    
    def update_config_with_gee_results(self, project_id: str, layers_data: Dict[str, Any], 
                                     aoi_info: Dict[str, Any], analysis_params: Dict[str, Any]) -> bool:
        """
        Update MapStore configuration with GEE analysis results
        
        Args:
            project_id: Project identifier
            layers_data: Dictionary containing layer information
            aoi_info: AOI information dictionary
            analysis_params: Analysis parameters dictionary
            
        Returns:
            bool: True if update was successful, False otherwise
        """
        try:
            # Create backup
            if not self.backup_config():
                logger.warning("Failed to create backup, continuing anyway...")
            
            # Load current configuration
            config = self.load_config()
            if config is None:
                logger.error("Failed to load configuration")
                return False
            
            # Remove old GEE layers
            config = self.remove_old_gee_layers(config)
            
            # Add new TMS layers (without changing initial map state)
            config = self.add_tms_layers(config, project_id, layers_data)
            
            # Note: We don't update initial map state to avoid breaking existing configuration
            
            # Save updated configuration
            if self.save_config(config):
                logger.info(f"Successfully updated MapStore configuration with {len(layers_data.get('layers', {}))} TMS layers")
                return True
            else:
                logger.error("Failed to save updated configuration")
                return False
                
        except Exception as e:
            logger.error(f"Failed to update configuration: {e}")
            return False
    
    def list_current_gee_layers(self) -> List[str]:
        """
        List current GEE layers in the configuration
        
        Returns:
            List of GEE layer names
        """
        config = self.load_config()
        if config is None:
            return []
        
        services = config.get("initialState", {}).get("defaultState", {}).get("catalog", {}).get("default", {}).get("services", {})
        
        gee_layers = []
        for service_name in services.keys():
            if service_name.startswith(('gee_', 'fastapi_gee_')):
                gee_layers.append(service_name)
        
        return gee_layers
    
    def get_layer_info(self, service_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific layer
        
        Args:
            service_name: Name of the service
            
        Returns:
            Dictionary containing layer information or None if not found
        """
        config = self.load_config()
        if config is None:
            return None
        
        services = config.get("initialState", {}).get("defaultState", {}).get("catalog", {}).get("default", {}).get("services", {})
        
        return services.get(service_name)


def update_mapstore_config(project_id: str, layers_data: Dict[str, Any], 
                          aoi_info: Dict[str, Any], analysis_params: Dict[str, Any],
                          config_path: str = "/usr/src/app/mapstore/config/localConfig.json") -> bool:
    """
    Convenience function to update MapStore configuration
    
    Args:
        project_id: Project identifier
        layers_data: Dictionary containing layer information
        aoi_info: AOI information dictionary
        analysis_params: Analysis parameters dictionary
        config_path: Path to the localConfig.json file
        
    Returns:
        bool: True if update was successful, False otherwise
    """
    updater = MapStoreConfigUpdater(config_path)
    return updater.update_config_with_gee_results(project_id, layers_data, aoi_info, analysis_params)


def list_mapstore_gee_layers(config_path: str = "/usr/src/app/mapstore/config/localConfig.json") -> List[str]:
    """
    Convenience function to list current GEE layers
    
    Args:
        config_path: Path to the localConfig.json file
        
    Returns:
        List of GEE layer names
    """
    updater = MapStoreConfigUpdater(config_path)
    return updater.list_current_gee_layers()


if __name__ == "__main__":
    # Example usage
    print("MapStore Configuration Updater")
    print("This module provides functions to update MapStore's localConfig.json with TMS layers")
    print("\nAvailable functions:")
    print("- update_mapstore_config(): Update configuration with GEE results")
    print("- list_mapstore_gee_layers(): List current GEE layers")
    print("- MapStoreConfigUpdater: Class for advanced configuration management")
