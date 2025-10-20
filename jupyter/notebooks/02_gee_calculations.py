# GEE Calculations Testing
# This script demonstrates how to use the GEE_notebook_Forestry library for carbon calculations.

import ee
import sys
import os
from datetime import datetime

# Add libraries to path
sys.path.append('/app/gee_lib')
sys.path.append('/app/ex_ante')

print(f"Python path: {sys.path}")
print(f"Current working directory: {os.getcwd()}")

# Initialize Google Earth Engine
try:
    # Use service account authentication
    service_account = 'iqbalpythonapi@bukit30project.iam.gserviceaccount.com'
    credentials = ee.ServiceAccountCredentials(service_account, '/app/user_id.json')
    ee.Initialize(credentials)
    print("✅ Google Earth Engine initialized successfully")
    print(f"EE version: {ee.__version__}")
except Exception as e:
    print(f"❌ GEE initialization failed: {e}")
    print("Make sure user_id.json is properly mounted")

# Test GEE_notebook_Forestry imports
try:
    from gee_lib.osi.fcd.main_fcd import FCDCalc
    from gee_lib.osi.hansen.historical_loss import HansenHistorical
    from gee_lib.osi.classifying.assign_zone import AssignClassZone
    from gee_lib.osi.area_calc.main import CalcAreaClass
    
    print("✅ All GEE_notebook_Forestry modules imported successfully")
    print("Available classes:")
    print("- FCDCalc: Forest Canopy Density calculations")
    print("- HansenHistorical: Historical loss analysis")
    print("- AssignClassZone: Land use classification")
    print("- CalcAreaClass: Area calculations")
    
except ImportError as e:
    print(f"❌ Import failed: {e}")
    print("Available files in gee_lib:")
    for root, dirs, files in os.walk('/app/gee_lib'):
        level = root.replace('/app/gee_lib', '').count(os.sep)
        indent = ' ' * 2 * level
        print(f"{indent}{os.path.basename(root)}/")
        subindent = ' ' * 2 * (level + 1)
        for file in files[:5]:  # Show first 5 files
            print(f"{subindent}{file}")
        if len(files) > 5:
            print(f"{subindent}... and {len(files) - 5} more files")

# Test ex_ante library imports
try:
    import ex_ante
    print("✅ ex_ante library imported successfully")
    print(f"ex_ante location: {ex_ante.__file__}")
    
    # List available modules in ex_ante
    if hasattr(ex_ante, '__all__'):
        print(f"Available modules: {ex_ante.__all__}")
    
except ImportError as e:
    print(f"❌ ex_ante import failed: {e}")
    print("Note: ex_ante library may not be mounted yet")
    
    # Check if ex_ante directory exists
    if os.path.exists('/app/ex_ante'):
        print("ex_ante directory exists, listing contents:")
        for item in os.listdir('/app/ex_ante'):
            print(f"  - {item}")
    else:
        print("ex_ante directory does not exist")

# Test database connection for storing results
try:
    import psycopg2
    
    # Connect to the spatial database
    conn = psycopg2.connect(
        host="postgres",
        database="gis_carbon_data",
        user="gis_user",
        password="gis_password"
    )
    
    cursor = conn.cursor()
    cursor.execute("SELECT version();")
    db_version = cursor.fetchone()
    
    print("✅ Database connection successful")
    print(f"Database version: {db_version[0]}")
    
    # Test PostGIS extension
    cursor.execute("SELECT PostGIS_version();")
    postgis_version = cursor.fetchone()
    print(f"PostGIS version: {postgis_version[0]}")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"❌ Database connection failed: {e}")

# Test GeoServer connection
try:
    import requests
    
    # Test GeoServer REST API
    response = requests.get("http://geoserver:8080/geoserver/rest/about/status.json")
    
    if response.status_code == 200:
        status = response.json()
        print("✅ GeoServer connection successful")
        print(f"GeoServer status: {status.get('status', 'Unknown')}")
        print(f"GeoServer version: {status.get('version', 'Unknown')}")
    else:
        print(f"❌ GeoServer connection failed: HTTP {response.status_code}")
        
except Exception as e:
    print(f"❌ GeoServer connection failed: {e}")

# Test FastAPI service connection
try:
    import requests
    
    # Test FastAPI health endpoint
    response = requests.get("http://fastapi:8000/health")
    
    if response.status_code == 200:
        health_data = response.json()
        print("✅ FastAPI service connection successful")
        print(f"FastAPI status: {health_data}")
    else:
        print(f"❌ FastAPI connection failed: HTTP {response.status_code}")
        
except Exception as e:
    print(f"❌ FastAPI connection failed: {e}")

print("\n" + "="*50)
print("ENVIRONMENT TEST COMPLETE")
print("="*50)
print("Next steps:")
print("1. Authenticate with GEE using your user_id.json")
print("2. Test calculations with your data")
print("3. Store results in the database")
print("4. Publish layers to GeoServer")
print("5. Integrate with FastAPI endpoints")
