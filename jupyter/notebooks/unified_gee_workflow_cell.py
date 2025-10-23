# Copy and paste this code into a new cell in your notebook to use the unified GEE interface

# Import the unified interface from the fastapi-gee-service
import sys
sys.path.append('/usr/src/app/fastapi-gee-service')

from unified_gee_interface import UnifiedGEEInterface, comprehensive_workflow_unified

print("🚀 Using Unified GEE Interface for comprehensive workflow...")

# Create the unified interface
interface = UnifiedGEEInterface(fastapi_url="http://fastapi:8000")

# Option 1: Use the comprehensive workflow (recommended)
print("\n🔄 Running comprehensive workflow...")

try:
    # This will handle everything: AOI processing, cache clearing, and GEE analysis
    result = comprehensive_workflow_unified(
        AOI_geom=AOI.geometry(),
        map_layers=map_layers,
        project_name=project_name,
        clear_cache_first=True,
        fastapi_url="http://fastapi:8000"
    )
    
    print(f"\n📊 Workflow Results:")
    print(f"   - Overall Status: {result.get('overall_status')}")
    print(f"   - AOI Center: {result.get('aoi_processing', {}).get('center')}")
    print(f"   - Cache Cleared: {result.get('cache_clearing', {}).get('status')}")
    print(f"   - GEE Analysis: {result.get('gee_analysis', {}).get('status')}")
    
    if result.get('gee_analysis', {}).get('status') == 'success':
        print(f"   - Project ID: {result.get('gee_analysis', {}).get('project_id')}")
        print(f"   - Available Layers: {result.get('gee_analysis', {}).get('available_layers', [])}")
    
except Exception as e:
    print(f"❌ Error in comprehensive workflow: {e}")

# Option 2: Step-by-step approach (if you need more control)
print("\n🔧 Alternative: Step-by-step approach...")

try:
    # Step 1: Process AOI geometry
    print("1️⃣ Processing AOI geometry...")
    aoi_info = interface.process_aoi_geometry(AOI.geometry())
    print(f"   ✅ AOI Center: {aoi_info.get('center')}")
    
    # Step 2: Clear cache
    print("2️⃣ Clearing cache...")
    cache_result = interface.clear_cache("all")
    print(f"   ✅ Cache Status: {cache_result.get('status')}")
    
    # Step 3: Process GEE analysis
    print("3️⃣ Processing GEE analysis...")
    gee_result = interface.process_gee_analysis(
        map_layers=map_layers,
        project_name=project_name,
        aoi_info=aoi_info,
        clear_cache_first=False  # Already cleared above
    )
    print(f"   ✅ GEE Analysis: {gee_result.get('status')}")
    
    if gee_result.get('status') == 'success':
        print(f"   - Project ID: {gee_result.get('project_id')}")
        print(f"   - Service URLs: {gee_result.get('service_urls', {})}")
    
except Exception as e:
    print(f"❌ Error in step-by-step approach: {e}")

# Option 3: Check service status
print("\n📋 Checking service status...")

try:
    status = interface.get_service_status()
    print(f"   - FastAPI: {status.get('fastapi', {}).get('status')}")
    print(f"   - WMTS: {status.get('wmts', {}).get('status')}")
    print(f"   - Cache: {status.get('cache', {}).get('total_keys', 0)} keys")
    
except Exception as e:
    print(f"❌ Error checking status: {e}")

print("\n🎉 Unified GEE workflow completed!")
print("\n📝 Summary:")
print("   - All EE calculations are handled by GEE_notebook_Forestry/osi/utils")
print("   - All cache/Redis/WMTS operations are handled by fastapi-gee-service")
print("   - The unified interface provides a clean API for all operations")
print("   - This approach is modular and can be used in any context (notebooks, web apps, etc.)")

print("\n🔄 Next steps:")
print("1. Check MapStore for updated WMTS layers")
print("2. Verify that the layers show the correct content")
print("3. The cache has been cleared, so you should see fresh data")
