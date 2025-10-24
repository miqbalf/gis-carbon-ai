#!/usr/bin/env python3
"""
Test WFS Integration - Verify that WFS service is working properly
"""

import requests
import json
import sys

def test_wfs_endpoints():
    """Test WFS endpoints"""
    print("🧪 Testing WFS Endpoints...")
    
    base_url = "http://localhost:8001"
    
    # Test GetCapabilities
    print("  📋 Testing GetCapabilities...")
    try:
        response = requests.get(f"{base_url}/wfs", params={
            "service": "WFS",
            "version": "2.0.0",
            "request": "GetCapabilities"
        })
        if response.status_code == 200:
            print("    ✅ GetCapabilities working")
            # Check if it contains our service info
            if "GEE Feature Service" in response.text:
                print("    ✅ Service title found")
            else:
                print("    ⚠️ Service title not found")
        else:
            print(f"    ❌ GetCapabilities failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"    ❌ GetCapabilities error: {e}")
        return False
    
    # Test GetFeature
    print("  🔍 Testing GetFeature...")
    try:
        response = requests.get(f"{base_url}/wfs", params={
            "service": "WFS",
            "version": "2.0.0",
            "request": "GetFeature",
            "typeName": "gee_sample_features",
            "outputFormat": "application/json"
        })
        if response.status_code == 200:
            data = response.json()
            if data.get("type") == "FeatureCollection":
                print("    ✅ GetFeature working")
                print(f"    📊 Found {len(data.get('features', []))} features")
            else:
                print("    ⚠️ Unexpected response format")
        else:
            print(f"    ❌ GetFeature failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"    ❌ GetFeature error: {e}")
        return False
    
    # Test DescribeFeatureType
    print("  📝 Testing DescribeFeatureType...")
    try:
        response = requests.get(f"{base_url}/wfs", params={
            "service": "WFS",
            "version": "2.0.0",
            "request": "DescribeFeatureType",
            "typeName": "gee_sample_features"
        })
        if response.status_code == 200:
            print("    ✅ DescribeFeatureType working")
        else:
            print(f"    ❌ DescribeFeatureType failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"    ❌ DescribeFeatureType error: {e}")
        return False
    
    return True

def test_mapstore_config():
    """Test MapStore configuration"""
    print("🗺️ Testing MapStore Configuration...")
    
    # Check if MapStore is accessible
    print("  🌐 Testing MapStore accessibility...")
    try:
        response = requests.get("http://localhost:8082/mapstore/")
        if response.status_code == 200:
            print("    ✅ MapStore is accessible")
        else:
            print(f"    ❌ MapStore not accessible: {response.status_code}")
            return False
    except Exception as e:
        print(f"    ❌ MapStore error: {e}")
        return False
    
    # Check if we can access the config through FastAPI
    print("  ⚙️ Testing MapStore config access...")
    try:
        response = requests.get("http://localhost:8001/mapstore/configs")
        if response.status_code == 200:
            config = response.json()
            services = config.get('initialState', {}).get('defaultState', {}).get('catalog', {}).get('services', {})
            gee_services = {k: v for k, v in services.items() if 'gee' in k.lower()}
            print(f"    ✅ Found {len(gee_services)} GEE services in config")
            for name, service in gee_services.items():
                print(f"      📋 {name}: {service.get('type', 'unknown')} - {service.get('title', 'no title')}")
        else:
            print(f"    ❌ Config access failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"    ❌ Config access error: {e}")
        return False
    
    return True

def main():
    """Main test function"""
    print("🚀 Starting WFS Integration Test...")
    print("=" * 50)
    
    # Test WFS endpoints
    wfs_success = test_wfs_endpoints()
    print()
    
    # Test MapStore configuration
    mapstore_success = test_mapstore_config()
    print()
    
    # Summary
    print("=" * 50)
    print("📊 Test Results:")
    print(f"  WFS Endpoints: {'✅ PASS' if wfs_success else '❌ FAIL'}")
    print(f"  MapStore Config: {'✅ PASS' if mapstore_success else '❌ FAIL'}")
    
    if wfs_success and mapstore_success:
        print("\n🎉 All tests passed! WFS integration is working!")
        return True
    else:
        print("\n❌ Some tests failed. Check the output above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
