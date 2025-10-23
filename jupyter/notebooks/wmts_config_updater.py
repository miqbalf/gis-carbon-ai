#!/usr/bin/env python3
"""
Dynamic WMTS Configuration Updater for MapStore
This module manages WMTS service configuration in localConfig.json
"""

import json
import os
import requests
from datetime import datetime
from typing import Dict, Any, Optional, List
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WMTSConfigUpdater:
    """Manages dynamic WMTS configuration in MapStore localConfig.json"""
    
    def __init__(self, config_path: str = "/usr/src/app/mapstore/config/localConfig.json"):
        self.config_path = config_path
        self.fastapi_url = "http://fastapi:8000"
        
    def load_config(self) -> Dict[str, Any]:
        """Load the current MapStore configuration"""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            raise
    
    def save_config(self, config: Dict[str, Any]) -> bool:
        """Save the updated MapStore configuration"""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)
            logger.info(f"Configuration saved to {self.config_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving config: {e}")
            return False
    
    def remove_old_gee_wmts_services(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Remove all existing GEE WMTS services from configuration"""
        try:
            # Find and remove old GEE WMTS services from the correct catalog location
            services_to_remove = []
            
            # Check in the correct catalog location
            catalog_services = config.get('initialState', {}).get('defaultState', {}).get('catalog', {}).get('default', {}).get('services', {})
            
            for service_id, service_config in catalog_services.items():
                if (isinstance(service_config, dict) and 
                    service_config.get('type') == 'wmts' and
                    # Only remove dynamic GEE services, not static ones
                    (service_id.startswith('gee_analysis_') or 
                     service_config.get('metadata', {}).get('service_type') == 'dynamic_gee_wmts')):
                    services_to_remove.append(service_id)
                    logger.info(f"Marking for removal: {service_id}")
            
            # Remove the services
            for service_id in services_to_remove:
                if service_id in catalog_services:
                    del catalog_services[service_id]
                    logger.info(f"Removed old GEE WMTS service: {service_id}")
            
            return config
        except Exception as e:
            logger.error(f"Error removing old services: {e}")
            return config
    
    def add_dynamic_wmts_service(self, config: Dict[str, Any], project_id: str, 
                                project_name: str, aoi_info: Dict[str, Any]) -> Dict[str, Any]:
        """Add dynamic WMTS service for the latest GEE analysis"""
        try:
            # Ensure catalogServices exists
            if 'catalogServices' not in config:
                config['catalogServices'] = {}
            
            # Create the dynamic WMTS service configuration with project-based ID
            # Clean project name for use as service ID (remove spaces, special chars)
            clean_project_name = "".join(c for c in project_name if c.isalnum() or c in ('_', '-')).lower()
            wmts_service_id = f"gee_analysis_{clean_project_name}"
            
            wmts_service_config = {
                "url": "http://localhost:8001/wmts",
                "type": "wmts",
                "title": f"GEE Analysis WMTS - {project_name}",
                "autoload": False,
                "description": f"Dynamic WMTS service for GEE analysis: {project_name}",
                "params": {
                    "LAYERS": project_id,
                    "TILEMATRIXSET": "GoogleMapsCompatible",
                    "FORMAT": "image/png"
                },
                "extent": [
                    aoi_info.get('bbox', {}).get('minx', 109.5),
                    aoi_info.get('bbox', {}).get('miny', -1.5),
                    aoi_info.get('bbox', {}).get('maxx', 110.5),
                    aoi_info.get('bbox', {}).get('maxy', -0.5)
                ],
                "metadata": {
                    "project_id": project_id,
                    "project_name": project_name,
                    "generated_at": datetime.now().isoformat(),
                    "service_type": "dynamic_gee_wmts",
                    "layers_available": [
                        f"{project_id}_true_color",
                        f"{project_id}_false_color", 
                        f"{project_id}_ndvi",
                        f"{project_id}_evi",
                        f"{project_id}_ndwi"
                    ]
                }
            }
            
            # Add the service to the correct catalog location
            if 'initialState' not in config:
                config['initialState'] = {}
            if 'defaultState' not in config['initialState']:
                config['initialState']['defaultState'] = {}
            if 'catalog' not in config['initialState']['defaultState']:
                config['initialState']['defaultState']['catalog'] = {}
            if 'default' not in config['initialState']['defaultState']['catalog']:
                config['initialState']['defaultState']['catalog']['default'] = {}
            if 'services' not in config['initialState']['defaultState']['catalog']['default']:
                config['initialState']['defaultState']['catalog']['default']['services'] = {}
            
            config['initialState']['defaultState']['catalog']['default']['services'][wmts_service_id] = wmts_service_config
            
            logger.info(f"Added dynamic WMTS service: {wmts_service_id}")
            logger.info(f"  Project: {project_name} ({project_id})")
            logger.info(f"  Available layers: {len(wmts_service_config['metadata']['layers_available'])}")
            
            return config, wmts_service_id
        except Exception as e:
            logger.error(f"Error adding WMTS service: {e}")
            return config, None
    
    def update_wmts_configuration(self, project_id: str, project_name: str, 
                                 aoi_info: Dict[str, Any], 
                                 replace_existing: bool = True) -> bool:
        """Update WMTS configuration with latest GEE analysis"""
        try:
            logger.info(f"Updating WMTS configuration for project: {project_id}")
            
            # Load current configuration
            config = self.load_config()
            
            # Remove old GEE WMTS services if requested
            if replace_existing:
                config = self.remove_old_gee_wmts_services(config)
            
            # Add new dynamic WMTS service
            config, wmts_service_id = self.add_dynamic_wmts_service(config, project_id, project_name, aoi_info)
            
            if wmts_service_id is None:
                logger.error("❌ Failed to create WMTS service")
                return False
            
            # Save updated configuration
            success = self.save_config(config)
            
            if success:
                logger.info("✅ WMTS configuration updated successfully!")
                logger.info(f"   Service ID: {wmts_service_id}")
                logger.info(f"   Project: {project_name}")
                logger.info(f"   Layers: {project_id}_*")
            else:
                logger.error("❌ Failed to save WMTS configuration")
            
            return success
        except Exception as e:
            logger.error(f"Error updating WMTS configuration: {e}")
            return False
    
    def get_current_wmts_info(self) -> Optional[Dict[str, Any]]:
        """Get information about current WMTS service"""
        try:
            config = self.load_config()
            
            # Check in the correct catalog location
            catalog_services = config.get('initialState', {}).get('defaultState', {}).get('catalog', {}).get('default', {}).get('services', {})
            
            for service_id, service_config in catalog_services.items():
                if (isinstance(service_config, dict) and 
                    service_config.get('type') == 'wmts' and
                    service_id.startswith('gee_analysis_')):
                    return {
                        'service_id': service_id,
                        'project_id': service_config.get('metadata', {}).get('project_id'),
                        'project_name': service_config.get('metadata', {}).get('project_name'),
                        'generated_at': service_config.get('metadata', {}).get('generated_at'),
                        'layers_available': service_config.get('metadata', {}).get('layers_available', [])
                    }
            return None
        except Exception as e:
            logger.error(f"Error getting WMTS info: {e}")
            return None
    
    def list_all_gee_services(self) -> List[Dict[str, Any]]:
        """List all GEE-related services in the configuration"""
        try:
            config = self.load_config()
            gee_services = []
            
            # Check in the correct catalog location
            catalog_services = config.get('initialState', {}).get('defaultState', {}).get('catalog', {}).get('default', {}).get('services', {})
            
            for service_id, service_config in catalog_services.items():
                if (isinstance(service_config, dict) and 
                    # Only list dynamic GEE services, not static ones
                    (service_id.startswith('gee_analysis_') or 
                     (service_config.get('metadata', {}).get('service_type') == 'dynamic_gee_wmts'))):
                    gee_services.append({
                        'service_id': service_id,
                        'type': service_config.get('type'),
                        'title': service_config.get('title'),
                        'project_id': service_config.get('metadata', {}).get('project_id'),
                        'generated_at': service_config.get('metadata', {}).get('generated_at')
                    })
            
            return gee_services
        except Exception as e:
            logger.error(f"Error listing GEE services: {e}")
            return []

def update_mapstore_wmts_config(project_id: str, project_name: str, 
                               aoi_info: Dict[str, Any], 
                               replace_existing: bool = True) -> bool:
    """
    Convenience function to update MapStore WMTS configuration
    
    Args:
        project_id: GEE analysis project ID (e.g., 'sentinel_analysis_20251023_072452')
        project_name: Human-readable project name
        aoi_info: Area of interest information with bbox coordinates
        replace_existing: If True, replace existing GEE services. If False, add alongside existing.
    
    Returns:
        bool: True if successful, False otherwise
    """
    updater = WMTSConfigUpdater()
    return updater.update_wmts_configuration(project_id, project_name, aoi_info, replace_existing)

def get_current_wmts_status() -> Optional[Dict[str, Any]]:
    """Get current WMTS service status"""
    updater = WMTSConfigUpdater()
    return updater.get_current_wmts_info()

def list_gee_services() -> List[Dict[str, Any]]:
    """List all GEE services in MapStore configuration"""
    updater = WMTSConfigUpdater()
    return updater.list_all_gee_services()

# Example usage
if __name__ == "__main__":
    # Example: Update WMTS configuration
    aoi_info = {
        'bbox': {
            'minx': 109.5,
            'miny': -1.5,
            'maxx': 110.5,
            'maxy': -0.5
        },
        'center': [110.0, -1.0]
    }
    
    success = update_mapstore_wmts_config(
        project_id="sentinel_analysis_20251023_072452",
        project_name="Sentinel-2 Cloudless Composite Analysis",
        aoi_info=aoi_info
    )
    
    if success:
        print("✅ WMTS configuration updated successfully!")
        
        # Show current status
        status = get_current_wmts_status()
        if status:
            print(f"Current WMTS service: {status['service_id']}")
            print(f"Project: {status['project_name']}")
            print(f"Layers: {len(status['layers_available'])}")
    else:
        print("❌ Failed to update WMTS configuration")
