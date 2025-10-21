#!/usr/bin/env python3
"""
Add GEE Layers to MapStore Configuration
This script can be run from the Jupyter notebook to automatically add layers to MapStore
"""

import json
import requests
import os
from datetime import datetime

class MapStoreGEEIntegrator:
    def __init__(self, fastapi_url="http://fastapi:8000", mapstore_config_path="/usr/src/app/mapstore/localConfig.json"):
        self.fastapi_url = fastapi_url
        self.mapstore_config_path = mapstore_config_path
        self.backup_path = mapstore_config_path.replace('.json', '.backup.json')
        
    def get_registered_projects(self):
        """Get all registered projects from FastAPI"""
        try:
            # Try common project IDs that might exist
            common_project_ids = [
                'test_project_001',
                'sentinel_analysis_20241020_171516'
            ]
            
            projects = []
            
            for project_id in common_project_ids:
                try:
                    response = requests.get(f"{self.fastapi_url}/layers/{project_id}", timeout=5)
                    if response.status_code == 200:
                        project_data = response.json()
                        if project_data.get('status') == 'success' and project_data.get('layers'):
                            projects.append({
                                'project_id': project_id,
                                **project_data
                            })
                            print(f"✅ Found project: {project_id} ({len(project_data['layers'])} layers)")
                except Exception as e:
                    print(f"⚠️  Project {project_id} not found: {e}")
                    
            return projects
            
        except Exception as e:
            print(f"❌ Error fetching projects: {e}")
            return []
    
    def convert_gee_layer_to_mapstore(self, project_id, layer_name, layer_data):
        """Convert GEE layer data to MapStore layer configuration"""
        base_url = f"{self.fastapi_url}/tiles/gee/{layer_name}"
        
        return {
            "type": "tile",
            "name": f"{project_id}_{layer_name}",
            "title": layer_data.get('name', layer_name.upper()),
            "description": layer_data.get('description', f'{layer_name} from GEE analysis'),
            "url": f"{base_url}/{{z}}/{{x}}/{{y}}",
            "format": "image/png",
            "transparent": True,
            "tileSize": 256,
            "visibility": False,
            "opacity": 1.0,
            "metadata": {
                "source": "Google Earth Engine",
                "project_id": project_id,
                "layer_name": layer_name,
                "analysis_date": layer_data.get('metadata', {}).get('analysis_date', datetime.now().isoformat()),
                "satellite": layer_data.get('metadata', {}).get('satellite', 'Sentinel-2'),
                **layer_data.get('metadata', {})
            }
        }
    
    def add_gee_layers_to_config(self, config, projects):
        """Add GEE layers to MapStore configuration"""
        # Ensure catalogServices exists
        if 'catalogServices' not in config:
            config['catalogServices'] = {'services': []}
        
        if 'services' not in config['catalogServices']:
            config['catalogServices']['services'] = []
        
        # Add GEE tile service
        gee_service = {
            "type": "tile",
            "title": "GEE Analysis Layers",
            "description": "Google Earth Engine analysis layers from FastAPI service",
            "url": f"{self.fastapi_url}/tiles/gee/{{layer_name}}/{{z}}/{{x}}/{{y}}",
            "format": "image/png",
            "transparent": True,
            "tileSize": 256,
            "authRequired": False
        }
        
        # Check if GEE service already exists
        existing_gee_service = None
        for i, service in enumerate(config['catalogServices']['services']):
            if service.get('title') == 'GEE Analysis Layers':
                existing_gee_service = i
                break
        
        if existing_gee_service is not None:
            print("  🔄 Updating existing GEE service...")
            config['catalogServices']['services'][existing_gee_service] = gee_service
        else:
            print("  ➕ Adding new GEE service...")
            config['catalogServices']['services'].append(gee_service)
        
        # Ensure map.layers exists
        if 'map' not in config:
            config['map'] = {}
        if 'layers' not in config['map']:
            config['map']['layers'] = []
        
        # Remove existing GEE layers
        config['map']['layers'] = [
            layer for layer in config['map']['layers'] 
            if not (layer.get('name', '').startswith('sentinel_analysis_') or 
                   layer.get('name', '').startswith('test_project_'))
        ]
        
        # Add new GEE layers
        layer_count = 0
        for project in projects:
            print(f"  📁 Processing project: {project['project_id']}")
            
            for layer_name, layer_data in project['layers'].items():
                mapstore_layer = self.convert_gee_layer_to_mapstore(
                    project['project_id'], layer_name, layer_data
                )
                config['map']['layers'].append(mapstore_layer)
                layer_count += 1
                print(f"    ➕ Added layer: {mapstore_layer['name']}")
        
        print(f"  ✅ Added {layer_count} GEE layers to MapStore configuration")
        return config
    
    def integrate_layers(self):
        """Main function to integrate GEE layers with MapStore"""
        print("🚀 Starting GEE Layers Integration with MapStore...\n")
        
        try:
            # 1. Load current MapStore configuration
            print("📖 Loading MapStore configuration...")
            if not os.path.exists(self.mapstore_config_path):
                raise FileNotFoundError(f"MapStore config not found: {self.mapstore_config_path}")
            
            with open(self.mapstore_config_path, 'r') as f:
                config = json.load(f)
            print("  ✅ Configuration loaded")
            
            # 2. Create backup
            print("💾 Creating backup...")
            with open(self.backup_path, 'w') as f:
                json.dump(config, f, indent=2)
            print(f"  ✅ Backup created: {self.backup_path}")
            
            # 3. Get GEE layers from FastAPI
            projects = self.get_registered_projects()
            
            if not projects:
                print("⚠️  No GEE projects found. Make sure to run the Jupyter notebook first.")
                print("   Run: jupyter/notebooks/02_gee_calculations.ipynb")
                return False
            
            # 4. Add GEE layers to configuration
            print("\n🔧 Adding GEE layers to MapStore configuration...")
            updated_config = self.add_gee_layers_to_config(config, projects)
            
            # 5. Save updated configuration
            print("💾 Saving updated configuration...")
            with open(self.mapstore_config_path, 'w') as f:
                json.dump(updated_config, f, indent=2)
            print(f"  ✅ Updated config saved: {self.mapstore_config_path}")
            
            # 6. Show summary
            print("\n📊 Summary:")
            print(f"  Projects processed: {len(projects)}")
            total_layers = sum(len(p['layers']) for p in projects)
            print(f"  Total layers added: {total_layers}")
            print(f"  MapStore layers: {len(updated_config['map']['layers'])}")
            print(f"  Catalog services: {len(updated_config['catalogServices']['services'])}")
            
            print("\n🎉 Integration complete!")
            print("\nNext steps:")
            print("  1. Restart MapStore container:")
            print("     docker-compose -f docker-compose.dev.yml restart mapstore")
            print("  2. Open MapStore:")
            print("     http://localhost:8082/mapstore")
            print("  3. Check the Catalog for GEE layers")
            print("  4. Add layers to your map from the Catalog")
            
            return True
            
        except Exception as error:
            print(f"\n❌ Error: {error}")
            return False

def add_gee_layers_to_mapstore(fastapi_url="http://fastapi:8000"):
    """
    Convenience function to add GEE layers to MapStore
    Call this from your Jupyter notebook
    """
    integrator = MapStoreGEEIntegrator(fastapi_url)
    return integrator.integrate_layers()

# Example usage
if __name__ == "__main__":
    success = add_gee_layers_to_mapstore()
    if success:
        print("\n✅ Successfully added GEE layers to MapStore!")
    else:
        print("\n❌ Failed to add GEE layers to MapStore")
