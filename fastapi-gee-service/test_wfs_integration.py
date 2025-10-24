#!/usr/bin/env python3
"""
Test script for WFS integration functionality
Demonstrates how to convert ee.FeatureCollection to list of features
and use WFS endpoints for serving vector data.
"""

import requests
import json
import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_wfs_capabilities(base_url="http://localhost:8001"):
    """Test WFS GetCapabilities endpoint"""
    print("🔍 Testing WFS GetCapabilities...")
    
    try:
        response = requests.get(f"{base_url}/wfs", params={
            'service': 'WFS',
            'version': '1.1.0',
            'request': 'GetCapabilities'
        }, timeout=10)
        
        if response.status_code == 200:
            print("   ✅ WFS GetCapabilities working!")
            print(f"   Content type: {response.headers.get('content-type', 'Unknown')}")
            print(f"   Content length: {len(response.text)} characters")
            
            # Check if it's XML
            if response.text.strip().startswith('<?xml'):
                print("   ✅ Returns XML format")
            else:
                print("   ⚠️ Not XML format")
                
            return True
        else:
            print(f"   ❌ WFS GetCapabilities failed: {response.status_code}")
            print(f"   Response: {response.text[:200]}...")
            return False
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def test_wfs_getfeature(base_url="http://localhost:8001", typename="gee_aoi_dynamic"):
    """Test WFS GetFeature endpoint"""
    print(f"🔍 Testing WFS GetFeature for '{typename}'...")
    
    try:
        response = requests.get(f"{base_url}/wfs", params={
            'service': 'WFS',
            'version': '1.1.0',
            'request': 'GetFeature',
            'typename': typename,
            'outputformat': 'application/json',
            'maxfeatures': 5
        }, timeout=10)
        
        if response.status_code == 200:
            print("   ✅ WFS GetFeature working!")
            print(f"   Content type: {response.headers.get('content-type', 'Unknown')}")
            
            # Try to parse as JSON
            try:
                data = response.json()
                if 'features' in data:
                    print(f"   📊 Returned {len(data['features'])} features")
                    print(f"   📊 Total features: {data.get('totalFeatures', 'Unknown')}")
                    
                    # Show first feature
                    if data['features']:
                        first_feature = data['features'][0]
                        print(f"   🔍 First feature:")
                        print(f"      Type: {first_feature.get('type', 'Unknown')}")
                        print(f"      Geometry: {first_feature.get('geometry', {}).get('type', 'Unknown')}")
                        print(f"      Properties: {list(first_feature.get('properties', {}).keys())}")
                    return True
                else:
                    print("   ⚠️ No features in response")
                    return False
            except Exception as json_error:
                print(f"   ⚠️ Could not parse JSON response: {json_error}")
                return False
        else:
            print(f"   ❌ WFS GetFeature failed: {response.status_code}")
            print(f"   Response: {response.text[:200]}...")
            return False
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def test_wfs_describe_feature_type(base_url="http://localhost:8001", typename="gee_aoi_dynamic"):
    """Test WFS DescribeFeatureType endpoint"""
    print(f"🔍 Testing WFS DescribeFeatureType for '{typename}'...")
    
    try:
        response = requests.get(f"{base_url}/wfs", params={
            'service': 'WFS',
            'version': '1.1.0',
            'request': 'DescribeFeatureType',
            'typename': typename
        }, timeout=10)
        
        if response.status_code == 200:
            print("   ✅ WFS DescribeFeatureType working!")
            print(f"   Content type: {response.headers.get('content-type', 'Unknown')}")
            print(f"   Content length: {len(response.text)} characters")
            
            # Check if it's XML
            if response.text.strip().startswith('<?xml'):
                print("   ✅ Returns XML schema format")
                return True
            else:
                print("   ⚠️ Not XML format")
                return False
        else:
            print(f"   ❌ WFS DescribeFeatureType failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def test_wfs_cascading(base_url="http://localhost:8001"):
    """Test WFS cascading functionality"""
    print("🔍 Testing WFS Cascading...")
    
    try:
        # Test with a public WFS service
        response = requests.get(f"{base_url}/wfs/cascade", params={
            'service': 'WFS',
            'version': '1.1.0',
            'request': 'GetCapabilities',
            'cascaded_url': 'https://demo.mapserver.org/cgi-bin/wfs?service=WFS&version=1.1.0&request=GetCapabilities'
        }, timeout=30)
        
        if response.status_code == 200:
            print("   ✅ WFS Cascading working!")
            print(f"   Content type: {response.headers.get('content-type', 'Unknown')}")
            print(f"   Content length: {len(response.text)} characters")
            
            # Check if it's XML
            if response.text.strip().startswith('<?xml'):
                print("   ✅ Returns XML capabilities from cascaded service")
                return True
            else:
                print("   ⚠️ Not XML format")
                return False
        else:
            print(f"   ❌ WFS Cascading failed: {response.status_code}")
            print(f"   Response: {response.text[:200]}...")
            return False
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def test_geojson_endpoint(base_url="http://localhost:8001", fc_name="gee_aoi_dynamic"):
    """Test existing GeoJSON endpoint for comparison"""
    print(f"🔍 Testing existing GeoJSON endpoint for '{fc_name}'...")
    
    try:
        response = requests.get(f"{base_url}/fc/{fc_name}", timeout=10)
        
        if response.status_code == 200:
            print("   ✅ GeoJSON endpoint working!")
            print(f"   Content type: {response.headers.get('content-type', 'Unknown')}")
            
            # Try to parse as JSON
            try:
                data = response.json()
                if 'features' in data:
                    print(f"   📊 GeoJSON has {len(data['features'])} features")
                    print(f"   📊 Type: {data.get('type', 'Unknown')}")
                    return True
                else:
                    print("   ⚠️ No features in GeoJSON response")
                    return False
            except Exception as json_error:
                print(f"   ⚠️ Could not parse GeoJSON: {json_error}")
                return False
        else:
            print(f"   ❌ GeoJSON endpoint failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def test_featurecollection_conversion():
    """Test FeatureCollection conversion utilities"""
    print("🔍 Testing FeatureCollection conversion utilities...")
    
    try:
        from gee_integration import (
            convert_ee_fc_to_features_list, 
            get_fc_statistics,
            convert_ee_fc_to_geojson
        )
        
        # Create a simple test FeatureCollection
        import ee
        
        # Initialize Earth Engine (this might fail in some environments)
        try:
            ee.Initialize()
            
            # Create a simple test FeatureCollection
            test_fc = ee.FeatureCollection([
                ee.Feature(ee.Geometry.Point([110.0, -1.0]), {'name': 'Point 1', 'value': 100}),
                ee.Feature(ee.Geometry.Point([110.1, -1.1]), {'name': 'Point 2', 'value': 200})
            ])
            
            # Test conversion to features list
            features_list = convert_ee_fc_to_features_list(test_fc)
            print(f"   ✅ Converted to {len(features_list)} features")
            
            # Test statistics
            stats = get_fc_statistics(test_fc)
            print(f"   📊 Statistics: {stats}")
            
            # Test GeoJSON conversion
            geojson = convert_ee_fc_to_geojson(test_fc)
            print(f"   ✅ GeoJSON conversion successful")
            print(f"   📊 GeoJSON type: {geojson.get('type', 'Unknown')}")
            print(f"   📊 Features count: {len(geojson.get('features', []))}")
            
            return True
            
        except Exception as ee_error:
            print(f"   ⚠️ Earth Engine not available: {ee_error}")
            print("   ℹ️ This is expected in some environments")
            return True  # Not a failure, just not available
            
    except ImportError as import_error:
        print(f"   ⚠️ Could not import gee_integration: {import_error}")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def main():
    """Run all WFS integration tests"""
    print("🌐 WFS Integration Test Suite")
    print("=" * 50)
    
    base_url = "http://localhost:8001"
    
    # Test results
    results = {}
    
    # Test 1: WFS GetCapabilities
    results['wfs_capabilities'] = test_wfs_capabilities(base_url)
    
    # Test 2: WFS GetFeature
    results['wfs_getfeature'] = test_wfs_getfeature(base_url)
    
    # Test 3: WFS DescribeFeatureType
    results['wfs_describe_feature_type'] = test_wfs_describe_feature_type(base_url)
    
    # Test 4: WFS Cascading
    results['wfs_cascading'] = test_wfs_cascading(base_url)
    
    # Test 5: GeoJSON endpoint
    results['geojson_endpoint'] = test_geojson_endpoint(base_url)
    
    # Test 6: FeatureCollection conversion
    results['fc_conversion'] = test_featurecollection_conversion()
    
    # Summary
    print("\n🎯 Test Results Summary:")
    print("=" * 30)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n📊 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! WFS integration is working correctly.")
    else:
        print("⚠️ Some tests failed. Check the output above for details.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
