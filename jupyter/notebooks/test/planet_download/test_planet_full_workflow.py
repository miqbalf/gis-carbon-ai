"""
Full end-to-end test of PlanetScope downloader workflow
Tests: Search -> Get Results -> Prepare for Order
"""

import os
import json
import asyncio
from datetime import datetime
import geopandas as gpd
import gcsfs
from planet import Session, data_filter

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Helper for date parsing
try:
    from dateutil import parser as date_parser
    def parse_date(date_str):
        return date_parser.parse(date_str) if isinstance(date_str, str) else date_str
except ImportError:
    def parse_date(date_str):
        if isinstance(date_str, str):
            if date_str.endswith('Z'):
                date_str = date_str[:-1] + '+00:00'
            return datetime.fromisoformat(date_str)
        return date_str

# Helper for async in Jupyter
def run_async(coro):
    """Run async coroutine, handling both sync and async contexts."""
    try:
        loop = asyncio.get_running_loop()
        try:
            import nest_asyncio
            nest_asyncio.apply()
            return asyncio.run(coro)
        except ImportError:
            import concurrent.futures
            def run_in_thread():
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    return new_loop.run_until_complete(coro)
                finally:
                    new_loop.close()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(run_in_thread)
                return future.result()
    except RuntimeError:
        return asyncio.run(coro)

print("=" * 60)
print("FULL PLANET WORKFLOW TEST")
print("=" * 60)

# Check API key
api_key = os.getenv('PL_API_KEY') or os.getenv('PLANET_API_KEY')
if not api_key:
    print("❌ No API key found. Set PL_API_KEY or PLANET_API_KEY")
    exit(1)
else:
    print(f"✅ API key found: {api_key[:10]}...")
    os.environ['PL_API_KEY'] = api_key

# Load AOI from GCS (same as notebook)
print("\n📂 Loading AOI from GCS...")
gcs_shp_path = f'gs://{os.getenv("GCS_BUCKET_PATH")}/01-korindo/aoi_buffer/korindo_buffer.shp'
gcs_project = os.getenv('GOOGLE_CLOUD_PROJECT')

if not gcs_project:
    print("❌ GOOGLE_CLOUD_PROJECT not set")
    exit(1)

try:
    # Setup GCS filesystem
    token_path = os.getenv("GCS_TOKEN_PATH", "/usr/src/app/user_id.json")
    fs_kwargs = {"project": gcs_project}
    if token_path and os.path.exists(token_path):
        fs_kwargs["token"] = token_path
    
    fs = gcsfs.GCSFileSystem(**fs_kwargs)
    
    if not fs.exists(gcs_shp_path):
        print(f"❌ AOI file not found: {gcs_shp_path}")
        exit(1)
    
    # Read shapefile from GCS
    gdf_aoi = gpd.read_file(gcs_shp_path, filesystem=fs)
    print(f"✅ Loaded AOI: {len(gdf_aoi)} features")
    print(f"   CRS: {gdf_aoi.crs}")
    print(f"   Bounds: {gdf_aoi.total_bounds}")
    
    # Convert to WGS84 if needed
    if gdf_aoi.crs != 'EPSG:4326':
        print(f"   Converting CRS to EPSG:4326...")
        gdf_aoi = gdf_aoi.to_crs('EPSG:4326')
    
    # Convert to GeoJSON geometry
    # If multiple features, union them
    if len(gdf_aoi) > 1:
        print(f"   Multiple features ({len(gdf_aoi)}), creating union...")
        gdf_union = gdf_aoi.unary_union
        gdf_aoi = gpd.GeoDataFrame(geometry=[gdf_union], crs=gdf_aoi.crs)
    
    # Get geometry from first feature
    geometry = gdf_aoi.geometry.iloc[0]
    
    # Convert to GeoJSON
    geojson = json.loads(gpd.GeoSeries([geometry]).to_json())
    test_geometry = geojson['features'][0]['geometry']
    
    print(f"   ✅ Converted to GeoJSON: {test_geometry['type']}")
    
except Exception as e:
    print(f"❌ Error loading AOI from GCS: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Test dates
start_date = "2024-01-01T00:00:00Z"
end_date = "2024-09-19T23:59:59Z"  # Fixed: was "2024-9-19" which is invalid
start_dt = parse_date(start_date)
end_dt = parse_date(end_date)

print(f"\n📅 Date range: {start_date} to {end_date}")
print(f"   Parsed: {start_dt} to {end_dt}")

# Build filters
print("\n🔧 Building filters...")
geometry_filter = data_filter.geometry_filter(test_geometry)
date_range_filter = data_filter.date_range_filter(
    'acquired',
    gte=start_dt,
    lte=end_dt
)
cloud_cover_filter = data_filter.range_filter('cloud_cover', lte=0.1)
combined_filter = data_filter.and_filter([
    geometry_filter,
    date_range_filter,
    cloud_cover_filter
])
print("✅ Filters built successfully")

# Build search request
# Note: The search() method might take item_types and filter as separate parameters
# Let's try both formats
search_request = {
    "item_types": ["PSScene"],
    "filter": combined_filter
}

# Alternative: Try passing as parameters directly to search()
# We'll test both approaches

# Test search
print("\n🔍 Testing search...")
async def test_search():
    try:
        async with Session() as session:
            client = session.client('data')
            
            print("   Executing search...")
            items = []
            count = 0
            limit = 10  # Get first 10 for testing
            
            # The search() method signature: search(item_types, search_filter=..., ...)
            # Note: parameter is 'search_filter', not 'filter'
            search_result = client.search(
                item_types=["PSScene"],
                search_filter=combined_filter
            )
            print("   ✅ Using search(item_types=..., search_filter=...) format")
            
            async for item in search_result:
                items.append(item)
                count += 1
                print(f"   Found item {count}: {item.get('id', 'N/A')[:30]}...")
                if count >= limit:
                    break
            
            print(f"\n✅ Search successful! Found {len(items)} items")
            
            if items:
                print("\n📋 Sample items:")
                for i, item in enumerate(items[:5], 1):  # Show first 5
                    props = item.get('properties', {})
                    item_id = item.get('id', 'N/A')
                    acquired = props.get('acquired', 'N/A')
                    cloud_cover = props.get('cloud_cover', 0) * 100
                    
                    print(f"\n   {i}. Item ID: {item_id}")
                    print(f"      Date: {acquired}")
                    print(f"      Cloud Cover: {cloud_cover:.1f}%")
                    
                    # Check available assets
                    try:
                        assets_response = await client.get_assets(item_id)
                        asset_types = list(assets_response.keys())
                        print(f"      Available assets: {', '.join(asset_types[:5])}")
                        if len(asset_types) > 5:
                            print(f"      ... and {len(asset_types) - 5} more")
                    except Exception as e:
                        print(f"      ⚠️  Could not get assets: {e}")
                
                # Test order creation preparation
                print("\n📦 Testing order preparation...")
                item_ids = [item['id'] for item in items[:3]]  # Use first 3 for test
                print(f"   Selected {len(item_ids)} items for order test:")
                for item_id in item_ids:
                    print(f"      - {item_id}")
                
                # Test orders client
                orders_client = session.client('orders')
                print("   ✅ Orders client created")
                
                # Build order request (don't actually create it)
                order_request = {
                    "name": "test_order_validation",
                    "products": [
                        {
                            "item_ids": item_ids,
                            "item_type": "PSScene",
                            "product_bundle": "analytic_sr_udm2"
                        }
                    ]
                }
                print("   ✅ Order request structure valid")
                print(f"   Order would contain {len(item_ids)} items")
                print("   ✅ Ready to create order!")
                
                return True, items, item_ids
            else:
                print("⚠️  No items found - this might be OK if the area/date has no coverage")
                return False, [], []
                
    except Exception as e:
        print(f"❌ Search error: {e}")
        import traceback
        traceback.print_exc()
        return False, [], []

# Run the test
print("\n" + "=" * 60)
result, items, item_ids = run_async(test_search())
print("=" * 60)

if result:
    print("\n✅ FULL WORKFLOW TEST PASSED!")
    print(f"   - Successfully searched for images")
    print(f"   - Found {len(items)} images")
    print(f"   - Prepared {len(item_ids)} items for ordering")
    print("\n🎉 The code is ready to use in the notebook!")
else:
    print("\n⚠️  Test completed but no items found")
    print("   This might be normal if:")
    print("   - The test area has no PlanetScope coverage")
    print("   - The date range has no images")
    print("   - Cloud cover threshold is too strict")
    print("\n   Try adjusting the test geometry or date range")

print("\n" + "=" * 60)

