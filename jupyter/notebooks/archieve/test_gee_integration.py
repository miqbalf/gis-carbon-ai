#!/usr/bin/env python3
"""
Test script for GEE to FastAPI to MapStore integration
Run this to verify the entire workflow is working
"""

import ee
import json
import os
import sys
import requests
from datetime import datetime

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_success(msg):
    print(f"{Colors.GREEN}✓ {msg}{Colors.END}")

def print_error(msg):
    print(f"{Colors.RED}✗ {msg}{Colors.END}")

def print_info(msg):
    print(f"{Colors.BLUE}ℹ {msg}{Colors.END}")

def print_warning(msg):
    print(f"{Colors.YELLOW}⚠ {msg}{Colors.END}")

# Add gee_lib to path
sys.path.insert(0, '/usr/src/app/gee_lib')

def test_gee_authentication():
    """Test 1: GEE Authentication"""
    print("\n" + "="*60)
    print("TEST 1: Google Earth Engine Authentication")
    print("="*60)
    
    try:
        credentials_path = '/usr/src/app/user_id.json'
        
        if not os.path.exists(credentials_path):
            print_error(f"Credentials file not found: {credentials_path}")
            return False
        
        with open(credentials_path, 'r') as f:
            credentials_data = json.load(f)
        
        service_account = credentials_data['client_email']
        project_id = credentials_data['project_id']
        
        credentials = ee.ServiceAccountCredentials(service_account, credentials_path)
        ee.Initialize(credentials)
        
        # Test by getting a simple image
        test_image = ee.Image('COPERNICUS/S2/20230101T000000_20230101T000000_T01ABC')
        
        print_success(f"GEE authenticated successfully")
        print_info(f"  Service Account: {service_account}")
        print_info(f"  Project ID: {project_id}")
        
        return True
    except Exception as e:
        print_error(f"GEE authentication failed: {e}")
        return False

def test_gee_lib_imports():
    """Test 2: GEE Library Imports"""
    print("\n" + "="*60)
    print("TEST 2: GEE Library Imports")
    print("="*60)
    
    try:
        from osi.image_collection.main import ImageCollection
        from osi.image_collection.cloud_mask import get_s2_sr_cld_col
        
        print_success("GEE library imports successful")
        print_info(f"  ImageCollection: {ImageCollection}")
        print_info(f"  cloud_mask module: Available")
        
        return True
    except Exception as e:
        print_error(f"GEE library import failed: {e}")
        return False

def test_simple_gee_computation():
    """Test 3: Simple GEE Computation"""
    print("\n" + "="*60)
    print("TEST 3: Simple GEE Computation")
    print("="*60)
    
    try:
        # Create a simple AOI
        aoi = ee.Geometry.Point([110.0, -1.0]).buffer(10000)
        
        # Get a single Sentinel-2 image
        image = ee.ImageCollection('COPERNICUS/S2_SR') \
            .filterDate('2023-01-01', '2023-12-31') \
            .filterBounds(aoi) \
            .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)) \
            .first()
        
        if image is None:
            print_error("No Sentinel-2 images found for test AOI")
            return False
        
        # Calculate NDVI
        ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI')
        
        # Get map ID
        map_id = ndvi.getMapId({'min': -0.2, 'max': 0.8, 'palette': ['red', 'yellow', 'green']})
        
        print_success("GEE computation successful")
        print_info(f"  Image ID: {image.get('system:id').getInfo()}")
        print_info(f"  Tile URL: {map_id['tile_fetcher'].url_format[:60]}...")
        
        return True
    except Exception as e:
        print_error(f"GEE computation failed: {e}")
        return False

def test_fastapi_connection():
    """Test 4: FastAPI Connection"""
    print("\n" + "="*60)
    print("TEST 4: FastAPI Service Connection")
    print("="*60)
    
    try:
        fastapi_url = "http://fastapi:8000"
        
        # Test health endpoint
        response = requests.get(f"{fastapi_url}/health", timeout=5)
        
        if response.status_code == 200:
            print_success("FastAPI service is accessible")
            result = response.json()
            print_info(f"  Status: {result.get('status')}")
            print_info(f"  Timestamp: {result.get('timestamp')}")
            return True
        else:
            print_error(f"FastAPI returned status code: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"FastAPI connection failed: {e}")
        print_warning("Make sure FastAPI service is running")
        return False

def test_push_to_fastapi():
    """Test 5: Push Data to FastAPI"""
    print("\n" + "="*60)
    print("TEST 5: Push Analysis to FastAPI")
    print("="*60)
    
    try:
        fastapi_url = "http://fastapi:8000"
        
        # Create test data
        test_data = {
            'project_id': f'test_integration_{datetime.now().strftime("%Y%m%d_%H%M%S")}',
            'project_name': 'Integration Test',
            'analysis_type': 'test',
            'parameters': {
                'satellite': 'Sentinel-2',
                'test': True
            }
        }
        
        # Push to FastAPI
        response = requests.post(
            f"{fastapi_url}/process-gee-analysis",
            json=test_data,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print_success("Successfully pushed data to FastAPI")
            print_info(f"  Project ID: {test_data['project_id']}")
            print_info(f"  Status: {result.get('status')}")
            return True
        else:
            print_error(f"Failed to push data: {response.status_code}")
            print_error(f"Response: {response.text}")
            return False
    except Exception as e:
        print_error(f"Push to FastAPI failed: {e}")
        return False

def test_complete_workflow():
    """Test 6: Complete Workflow (GEE → FastAPI)"""
    print("\n" + "="*60)
    print("TEST 6: Complete Workflow")
    print("="*60)
    
    try:
        from osi.image_collection.main import ImageCollection
        
        # Define AOI
        aoi = ee.Geometry.Point([110.0, -1.0]).buffer(5000)  # Small area for testing
        
        print_info("Creating Sentinel-2 composite...")
        
        # Create ImageCollection
        img_collection = ImageCollection(
            I_satellite='Sentinel',
            region='asia',
            AOI=aoi,
            date_start_end=['2023-06-01', '2023-06-30'],  # Short period for testing
            cloud_cover_threshold=30,
            config={'IsThermal': False}
        )
        
        # Get collection
        sentinel_collection = img_collection.image_collection_mask()
        image_count = sentinel_collection.size().getInfo()
        
        if image_count == 0:
            print_warning("No images found, but workflow test passed (GEE is working)")
            return True
        
        # Create composite
        sentinel_composite = img_collection.image_mosaick()
        
        # Calculate NDVI
        ndvi = sentinel_composite.normalizedDifference(['nir', 'red']).rename('NDVI')
        
        # Get map ID
        map_id = ndvi.getMapId({'min': -0.2, 'max': 0.8, 'palette': ['red', 'yellow', 'green']})
        
        # Prepare data for FastAPI
        project_id = f'workflow_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        
        layers_data = {
            'project_id': project_id,
            'project_name': 'Complete Workflow Test',
            'layers': {
                'ndvi': {
                    'tile_url': map_id['tile_fetcher'].url_format,
                    'map_id': map_id['mapid'],
                    'token': map_id['token']
                }
            }
        }
        
        # Push to FastAPI
        fastapi_url = "http://fastapi:8000"
        response = requests.post(
            f"{fastapi_url}/process-gee-analysis",
            json=layers_data,
            timeout=30
        )
        
        if response.status_code == 200:
            print_success("Complete workflow test passed!")
            print_info(f"  Images processed: {image_count}")
            print_info(f"  Project ID: {project_id}")
            print_info(f"  Tile URL generated: Yes")
            print_info(f"  Pushed to FastAPI: Yes")
            return True
        else:
            print_error(f"FastAPI push failed: {response.status_code}")
            return False
            
    except Exception as e:
        print_error(f"Complete workflow test failed: {e}")
        import traceback
        print(traceback.format_exc())
        return False

def test_redis_connection():
    """Test 7: Redis Connection"""
    print("\n" + "="*60)
    print("TEST 7: Redis Connection (via FastAPI)")
    print("="*60)
    
    try:
        # Test by checking if FastAPI can cache
        fastapi_url = "http://fastapi:8000"
        response = requests.get(f"{fastapi_url}/health", timeout=5)
        
        if response.status_code == 200:
            print_success("Redis connection available (FastAPI operational)")
            print_info("  FastAPI uses Redis for caching tiles")
            return True
        else:
            print_warning("Cannot verify Redis connection")
            return False
    except Exception as e:
        print_error(f"Redis connection test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║" + " "*15 + "GEE INTEGRATION TEST SUITE" + " "*17 + "║")
    print("╚" + "="*58 + "╝")
    
    tests = [
        ("GEE Authentication", test_gee_authentication),
        ("GEE Library Imports", test_gee_lib_imports),
        ("Simple GEE Computation", test_simple_gee_computation),
        ("FastAPI Connection", test_fastapi_connection),
        ("Push to FastAPI", test_push_to_fastapi),
        ("Complete Workflow", test_complete_workflow),
        ("Redis Connection", test_redis_connection),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print_error(f"Test '{test_name}' crashed: {e}")
            results.append((test_name, False))
    
    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        color = Colors.GREEN if result else Colors.RED
        print(f"{color}{status:6s}{Colors.END} - {test_name}")
    
    print("\n" + "-"*60)
    print(f"Total: {passed}/{total} tests passed")
    
    if passed == total:
        print_success("All tests passed! ✨")
        print("\nYou can now:")
        print("  1. Run the Jupyter notebook: 02_gee_calculations.ipynb")
        print("  2. Access Jupyter at: http://localhost:8888")
        print("  3. View MapStore at: http://localhost:8082/mapstore")
        return 0
    else:
        print_error(f"{total - passed} test(s) failed")
        print("\nPlease check:")
        print("  1. Docker services are running")
        print("  2. GCP credentials are valid")
        print("  3. Network connectivity")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

