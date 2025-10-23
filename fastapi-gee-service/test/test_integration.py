#!/usr/bin/env python3
"""
Test script for GEE Integration with FastAPI and MapStore
This script demonstrates the complete workflow from GEE analysis to MapStore integration
"""

import sys
import os
import requests
import json
from datetime import datetime

# Add the notebooks directory to path (for Docker environment)
sys.path.append('/usr/src/app/notebooks')

def test_fastapi_health():
    """Test FastAPI service health"""
    try:
        response = requests.get("http://fastapi:8000/health", timeout=5)
        if response.status_code == 200:
            print("✅ FastAPI service is healthy")
            return True
        else:
            print(f"❌ FastAPI health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to FastAPI: {e}")
        return False

def test_wmts_capabilities():
    """Test WMTS GetCapabilities"""
    try:
        url = "http://fastapi:8000/wmts"
        params = {
            "service": "WMTS",
            "request": "GetCapabilities",
            "version": "1.0.0"
        }
        
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            content = response.text
            if "Capabilities" in content and "Layer" in content:
                print("✅ WMTS GetCapabilities working")
                return True
            else:
                print("❌ WMTS GetCapabilities returned invalid XML")
                return False
        else:
            print(f"❌ WMTS GetCapabilities failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ WMTS test failed: {e}")
        return False

def test_gee_integration():
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
    except ImportError as e:
        print(f"❌ Cannot import gee_integration: {e}")
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
    except ImportError as e:
        print(f"❌ Cannot import wmts_config_updater: {e}")
        return False
    except Exception as e:
        print(f"❌ WMTS config updater test failed: {e}")
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

def test_redis_connection():
    """Test Redis connection"""
    try:
        import redis
        
        # Try to connect to Redis
        r = redis.Redis(host='redis', port=6379, db=1, decode_responses=False)
        r.ping()
        
        print("✅ Redis connection working")
        
        # Test basic operations
        r.set('test_key', 'test_value', ex=10)
        value = r.get('test_key')
        if value == b'test_value':
            print("✅ Redis read/write working")
            r.delete('test_key')
            return True
        else:
            print("❌ Redis read/write test failed")
            return False
    except ImportError:
        print("❌ Redis module not available")
        return False
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        return False

def run_all_tests():
    """Run all integration tests"""
    print("🧪 Running GEE Integration Tests")
    print("=" * 50)
    
    tests = [
        ("FastAPI Health", test_fastapi_health),
        ("WMTS Capabilities", test_wmts_capabilities),
        ("GEE Integration Library", test_gee_integration),
        ("WMTS Config Updater", test_wmts_config_updater),
        ("MapStore Config Access", test_mapstore_config_access),
        ("Redis Connection", test_redis_connection)
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
    print("\n" + "=" * 50)
    print("📊 Test Results Summary")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Integration is working correctly.")
    elif passed >= total * 0.8:
        print("⚠️  Most tests passed. Check failed tests for issues.")
    else:
        print("❌ Multiple tests failed. Check service configuration.")
    
    return passed == total

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
