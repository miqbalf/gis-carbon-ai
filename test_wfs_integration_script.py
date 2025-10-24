#!/usr/bin/env python3
"""
WFS Integration Test Script
Run this in the Jupyter container to test WFS integration
"""

import sys
import os
import requests
import json
from typing import Dict, Any

# Add the fastapi-gee-service to the path
sys.path.append('/usr/src/app/fastapi-gee-service')

def test_wfs_endpoints():
    """Test WFS endpoints"""
    print("🧪 Testing WFS Endpoints...")
    
    # Test GetCapabilities
    try:
        response = requests.get("http://fastapi:8000/wfs", params={
            "service": "WFS",
            "version": "2.0.0",
            "request": "GetCapabilities"
        })
        if response.status_code == 200:
            print("✅ WFS GetCapabilities working")
            print(f"   Response length: {len(response.text)} characters")
        else:
            print(f"❌ WFS GetCapabilities failed: {response.status_code}")
    except Exception as e:
        print(f"❌ WFS GetCapabilities error: {e}")
    
    # Test GetFeature
    try:
        response = requests.get("http://fastapi:8000/wfs", params={
            "service": "WFS",
            "version": "2.0.0",
            "request": "GetFeature",
            "typeName": "gee_sample_features",
            "outputFormat": "application/json"
        })
        if response.status_code == 200:
            data = response.json()
            print(f"✅ WFS GetFeature working - Found {len(data.get('features', []))} features")
        else:
            print(f"❌ WFS GetFeature failed: {response.status_code}")
    except Exception as e:
        print(f"❌ WFS GetFeature error: {e}")

def test_wfs_integration():
    """Test the WFS integration function"""
    print("🔧 Testing WFS Integration Function...")
    
    try:
        from gee_wfs_integration import process_gee_to_mapstore_with_wfs
        from gee_wfs_utils import create_sample_gee_feature_collection
        
        print("✅ WFS integration modules imported successfully")
        
        # Create sample data
        sample_map_layers = {
            "ndvi": "http://fastapi:8000/tiles/ndvi/{z}/{x}/{y}.png",
            "ndwi": "http://fastapi:8000/tiles/ndwi/{z}/{x}/{y}.png"
        }
        
        sample_vector_layers = {
            "sample_features": create_sample_gee_feature_collection()
        }
        
        print("✅ Sample data created")
        
        # Test the integration
        result = process_gee_to_mapstore_with_wfs(
            map_layers=sample_map_layers,
            vector_layers=sample_vector_layers,
            project_name="WFS_Test_Project",
            aoi_info={"bounds": [110, -2, 111, -1]}
        )
        
        print(f"✅ WFS integration completed")
        print(f"   Status: {result.get('status', 'unknown')}")
        print(f"   Has vector layers: {result.get('has_vector_layers', False)}")
        print(f"   Separate services: {result.get('separate_services', False)}")
        
    except Exception as e:
        print(f"❌ WFS integration error: {e}")
        import traceback
        traceback.print_exc()

def check_mapstore_config():
    """Check MapStore configuration"""
    print("🗺️ Checking MapStore Configuration...")
    
    try:
        # Check if we can access the config file
        config_path = "/usr/src/app/mapstore/configs/localConfig.json"
        
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            # Check for GEE services
            services = config.get('initialState', {}).get('defaultState', {}).get('catalog', {}).get('services', {})
            gee_services = {k: v for k, v in services.items() if 'gee' in k.lower()}
            
            print(f"✅ Found {len(gee_services)} GEE services in MapStore config:")
            for name, service in gee_services.items():
                print(f"   📋 {name}: {service.get('type', 'unknown')} - {service.get('title', 'no title')}")
                
            # Check if WFS service exists
            wfs_services = {k: v for k, v in gee_services.items() if v.get('type') == 'wfs'}
            if wfs_services:
                print(f"✅ Found {len(wfs_services)} WFS services")
            else:
                print("❌ No WFS services found in MapStore config")
                
        else:
            print(f"❌ MapStore config file not found at {config_path}")
            
    except Exception as e:
        print(f"❌ Error checking MapStore config: {e}")
        import traceback
        traceback.print_exc()

def test_mapstore_service_manager():
    """Test MapStore service manager"""
    print("🔧 Testing MapStore Service Manager...")
    
    try:
        from mapstore_service_manager import MapStoreServiceManager
        
        # Initialize service manager
        service_manager = MapStoreServiceManager()
        
        # List current services
        services = service_manager.list_services()
        print(f"✅ Found {len(services)} GEE services:")
        for service in services:
            print(f"   📋 {service['name']}: {service['type']} - {service['title']}")
        
        # Check if we can add a test service
        test_result = service_manager.add_both_services("Test_Project", "http://fastapi:8000")
        print(f"✅ Test service addition: WMTS={test_result.get('wmts', False)}, WFS={test_result.get('wfs', False)}")
        
    except Exception as e:
        print(f"❌ MapStore service manager error: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Main test function"""
    print("🚀 Starting WFS Integration Test...")
    print("=" * 50)
    
    # Test WFS endpoints
    test_wfs_endpoints()
    print()
    
    # Test WFS integration
    test_wfs_integration()
    print()
    
    # Check MapStore configuration
    check_mapstore_config()
    print()
    
    # Test MapStore service manager
    test_mapstore_service_manager()
    print()
    
    # Final verification
    print("🎯 Final Verification...")
    
    # Check if MapStore is accessible
    try:
        response = requests.get("http://mapstore:8080/mapstore/")
        if response.status_code == 200:
            print("✅ MapStore is accessible")
        else:
            print(f"❌ MapStore not accessible: {response.status_code}")
    except Exception as e:
        print(f"❌ MapStore accessibility error: {e}")
    
    print("\n🎉 WFS Integration Test Complete!")
    print("\nNext steps:")
    print("1. Open MapStore at http://localhost:8082/mapstore/")
    print("2. Check the Catalog for GEE services")
    print("3. Look for both WMTS and WFS services")
    print("4. Add layers from both services to test functionality")

if __name__ == "__main__":
    main()
