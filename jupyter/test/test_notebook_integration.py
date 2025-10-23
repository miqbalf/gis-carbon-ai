#!/usr/bin/env python3
"""
Test script for Jupyter Notebook Integration
This script tests the complete workflow from GEE analysis to MapStore integration
"""

import sys
import os
import json
import requests
from datetime import datetime

# Add the notebooks directory to path (for Docker environment)
sys.path.append('/usr/src/app/notebooks')

def test_imports():
    """Test that all required modules can be imported"""
    try:
        # Test core imports
        import ee
        print("✅ Google Earth Engine imported successfully")
        
        # Test integration modules
        from gee_integration import process_gee_to_mapstore
        print("✅ GEE integration module imported successfully")
        
        from wmts_config_updater import update_mapstore_wmts_config, get_current_wmts_status
        print("✅ WMTS config updater imported successfully")
        
        from gee_catalog_updater import update_mapstore_catalog, GEECatalogUpdater
        print("✅ GEE catalog updater imported successfully")
        
        # Test other required modules
        import folium
        print("✅ Folium imported successfully")
        
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_gee_initialization():
    """Test GEE initialization with service account"""
    try:
        import ee
        
        # Check if credentials file exists
        credentials_path = '/usr/src/app/user_id.json'
        if not os.path.exists(credentials_path):
            print(f"❌ Credentials file not found: {credentials_path}")
            return False
        
        # Load credentials
        with open(credentials_path, 'r') as f:
            credentials_data = json.load(f)
        
        service_account = credentials_data['client_email']
        print(f"✅ Service account found: {service_account}")
        
        # Initialize GEE
        credentials = ee.ServiceAccountCredentials(service_account, credentials_path)
        ee.Initialize(credentials)
        
        print("✅ GEE initialized successfully")
        return True
    except Exception as e:
        print(f"❌ GEE initialization failed: {e}")
        return False

def test_gee_lib_access():
    """Test access to GEE library"""
    try:
        # Add gee_lib to path
        gee_lib_path = '/usr/src/app/gee_lib'
        if gee_lib_path not in sys.path:
            sys.path.append(gee_lib_path)
        
        # Test importing from gee_lib
        from osi.image_collection.main import ImageCollection
        print("✅ GEE library (osi) imported successfully")
        
        return True
    except ImportError as e:
        print(f"❌ GEE library import failed: {e}")
        return False
    except Exception as e:
        print(f"❌ GEE library access failed: {e}")
        return False

def test_integration_library():
    """Test the GEE integration library"""
    try:
        from gee_integration import process_gee_to_mapstore
        
        # Test with mock data
        test_layers = {
            'true_color': 'https://earthengine.googleapis.com/v1/projects/earthengine-legacy/maps/test/tiles/{z}/{x}/{y}',
            'ndvi': 'https://earthengine.googleapis.com/v1/projects/earthengine-legacy/maps/test2/tiles/{z}/{x}/{y}'
        }
        
        result = process_gee_to_mapstore(test_layers, "Test Integration")
        
        if result['status'] == 'success':
            print("✅ GEE integration library working")
            print(f"   Project ID: {result['project_id']}")
            print(f"   Service ID: {result['wmts_configuration']['service_id']}")
            return True
        else:
            print(f"❌ GEE integration failed: {result.get('error')}")
            return False
    except Exception as e:
        print(f"❌ GEE integration test failed: {e}")
        return False

def test_wmts_config_updater():
    """Test WMTS configuration updater"""
    try:
        from wmts_config_updater import get_current_wmts_status, list_gee_services
        
        # Test getting current status
        status = get_current_wmts_status()
        if status:
            print("✅ WMTS config updater working")
            print(f"   Current service: {status['service_id']}")
            print(f"   Project: {status['project_name']}")
            return True
        else:
            print("⚠️  No active WMTS service found (this is normal for fresh install)")
            return True
    except Exception as e:
        print(f"❌ WMTS config updater test failed: {e}")
        return False

def test_catalog_updater():
    """Test catalog updater"""
    try:
        from gee_catalog_updater import GEECatalogUpdater
        
        # Initialize catalog manager
        catalog_manager = GEECatalogUpdater("http://fastapi:8000")
        
        # Test listing catalogs
        catalogs = catalog_manager.list_catalogs()
        print("✅ Catalog updater working")
        print(f"   Catalogs found: {len(catalogs.get('catalogs', []))}")
        
        return True
    except Exception as e:
        print(f"❌ Catalog updater test failed: {e}")
        return False

def test_mapstore_config_access():
    """Test MapStore configuration file access"""
    try:
        config_path = "/usr/src/app/mapstore/config/localConfig.json"
        
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            # Check if catalog services exist
            catalog_services = config.get('initialState', {}).get('defaultState', {}).get('catalog', {}).get('default', {}).get('services', {})
            
            print("✅ MapStore config file accessible")
            print(f"   Total services: {len(catalog_services)}")
            
            # Check for GEE services
            gee_services = [k for k in catalog_services.keys() if k.startswith('gee_analysis_')]
            if gee_services:
                print(f"   GEE services: {len(gee_services)}")
                for service in gee_services:
                    print(f"     • {service}")
            else:
                print("   No GEE services found (normal for fresh install)")
            
            return True
        else:
            print(f"❌ MapStore config file not found: {config_path}")
            return False
    except Exception as e:
        print(f"❌ MapStore config test failed: {e}")
        return False

def test_fastapi_connectivity():
    """Test connectivity to FastAPI service"""
    try:
        response = requests.get("http://fastapi:8000/health", timeout=5)
        if response.status_code == 200:
            print("✅ FastAPI service is accessible")
            return True
        else:
            print(f"❌ FastAPI health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to FastAPI: {e}")
        return False

def test_notebook_workflow_simulation():
    """Simulate the complete notebook workflow"""
    try:
        print("🧪 Simulating notebook workflow...")
        
        # Step 1: Test GEE initialization
        if not test_gee_initialization():
            return False
        
        # Step 2: Test GEE library access
        if not test_gee_lib_access():
            return False
        
        # Step 3: Test integration library
        if not test_integration_library():
            return False
        
        # Step 4: Test WMTS configuration
        if not test_wmts_config_updater():
            return False
        
        # Step 5: Test catalog management
        if not test_catalog_updater():
            return False
        
        print("✅ Complete notebook workflow simulation successful")
        return True
    except Exception as e:
        print(f"❌ Notebook workflow simulation failed: {e}")
        return False

def run_all_tests():
    """Run all notebook integration tests"""
    print("🧪 Running Jupyter Notebook Integration Tests")
    print("=" * 60)
    
    tests = [
        ("Module Imports", test_imports),
        ("GEE Initialization", test_gee_initialization),
        ("GEE Library Access", test_gee_lib_access),
        ("FastAPI Connectivity", test_fastapi_connectivity),
        ("Integration Library", test_integration_library),
        ("WMTS Config Updater", test_wmts_config_updater),
        ("Catalog Updater", test_catalog_updater),
        ("MapStore Config Access", test_mapstore_config_access),
        ("Complete Workflow Simulation", test_notebook_workflow_simulation)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n🔍 Testing {test_name}...")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Results Summary")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Notebook integration is working correctly.")
    elif passed >= total * 0.8:
        print("⚠️  Most tests passed. Check failed tests for issues.")
    else:
        print("❌ Multiple tests failed. Check service configuration.")
    
    return passed == total

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
