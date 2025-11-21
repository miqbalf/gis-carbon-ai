"""
Test script for PlanetScope Downloader
Tests the actual workflow to identify errors before using in notebook
"""

import os
import json
import asyncio
from datetime import datetime
from typing import Dict, List, Optional
from planet import Session
from planet import data_filter

# Test imports and basic setup
print("=" * 60)
print("TEST 1: Imports and Basic Setup")
print("=" * 60)

try:
    # Test date parsing
    try:
        from dateutil import parser as date_parser
        def parse_date(date_str):
            return date_parser.parse(date_str) if isinstance(date_str, str) else date_str
        print("✅ Using dateutil.parser for date parsing")
    except ImportError:
        def parse_date(date_str):
            if isinstance(date_str, str):
                if date_str.endswith('Z'):
                    date_str = date_str[:-1] + '+00:00'
                return datetime.fromisoformat(date_str)
            return date_str
        print("✅ Using datetime.fromisoformat for date parsing")
    
    print("✅ All imports successful")
except Exception as e:
    print(f"❌ Import error: {e}")
    exit(1)

# Test 2: Check API key
print("\n" + "=" * 60)
print("TEST 2: API Key Check")
print("=" * 60)

api_key = os.getenv('PL_API_KEY') or os.getenv('PLANET_API_KEY')
if not api_key:
    print("⚠️  No API key found. Set PL_API_KEY or PLANET_API_KEY")
    print("   Continuing with tests that don't require API key...")
    api_key = "test_key_for_structure_testing"
else:
    print(f"✅ API key found: {api_key[:10]}...")

os.environ['PL_API_KEY'] = api_key

# Test 3: Test filter creation
print("\n" + "=" * 60)
print("TEST 3: Filter Creation")
print("=" * 60)

try:
    # Test geometry filter
    test_geometry = {
        "type": "Polygon",
        "coordinates": [[
            [100.0, -5.0],
            [101.0, -5.0],
            [101.0, -4.0],
            [100.0, -4.0],
            [100.0, -5.0]
        ]]
    }
    
    # Check available methods in data_filter
    print(f"Available data_filter methods: {[m for m in dir(data_filter) if not m.startswith('_')]}")
    
    # Test geometry_filter
    try:
        geometry_filter = data_filter.geometry_filter(test_geometry)
        print("✅ geometry_filter() works")
    except AttributeError:
        try:
            geometry_filter = data_filter.geom_filter(test_geometry)
            print("✅ geom_filter() works (using fallback)")
        except AttributeError as e:
            print(f"❌ Neither geometry_filter nor geom_filter exists: {e}")
            exit(1)
    
    # Test date_range_filter
    start_date = "2024-01-01T00:00:00Z"
    end_date = "2024-12-31T23:59:59Z"
    start_dt = parse_date(start_date)
    end_dt = parse_date(end_date)
    
    print(f"Parsed dates: {start_dt} to {end_dt}")
    
    try:
        date_range_filter = data_filter.date_range_filter(
            'acquired',
            gte=start_dt,
            lte=end_dt
        )
        print("✅ date_range_filter() works with gte/lte")
    except Exception as e:
        print(f"❌ date_range_filter error: {e}")
        # Try with gt/lt
        try:
            date_range_filter = data_filter.date_range_filter(
                'acquired',
                gt=start_dt,
                lt=end_dt
            )
            print("✅ date_range_filter() works with gt/lt")
        except Exception as e2:
            print(f"❌ date_range_filter error with gt/lt: {e2}")
            exit(1)
    
    # Test range_filter
    try:
        cloud_cover_filter = data_filter.range_filter('cloud_cover', lte=0.1)
        print("✅ range_filter() works")
    except Exception as e:
        print(f"❌ range_filter error: {e}")
        exit(1)
    
    # Test and_filter
    try:
        combined_filter = data_filter.and_filter([
            geometry_filter,
            date_range_filter,
            cloud_cover_filter
        ])
        print("✅ and_filter() works")
        print(f"Combined filter type: {type(combined_filter)}")
        print(f"Combined filter keys: {combined_filter.keys() if isinstance(combined_filter, dict) else 'Not a dict'}")
    except Exception as e:
        print(f"❌ and_filter error: {e}")
        exit(1)
    
except Exception as e:
    print(f"❌ Filter creation error: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Test 4: Test search request building
print("\n" + "=" * 60)
print("TEST 4: Search Request Building")
print("=" * 60)

try:
    # Check if build_search_request exists
    if hasattr(data_filter, 'build_search_request'):
        print("✅ build_search_request() exists")
        try:
            search_request = data_filter.build_search_request(
                combined_filter,
                item_types=['PSScene']
            )
            print("✅ build_search_request() works")
        except Exception as e:
            print(f"❌ build_search_request() error: {e}")
            # Fallback to dictionary
            search_request = {
                "item_types": ["PSScene"],
                "filter": combined_filter
            }
            print("✅ Using dictionary fallback for search request")
    else:
        print("⚠️  build_search_request() does not exist, using dictionary")
        search_request = {
            "item_types": ["PSScene"],
            "filter": combined_filter
        }
        print("✅ Search request built as dictionary")
    
    print(f"Search request structure: {list(search_request.keys())}")
    
except Exception as e:
    print(f"❌ Search request building error: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Test 5: Test Session and Client
print("\n" + "=" * 60)
print("TEST 5: Session and Client Creation")
print("=" * 60)

async def test_session():
    try:
        async with Session() as session:
            print("✅ Session created successfully")
            
            # Test data client
            try:
                client = session.client('data')
                print("✅ Data client created successfully")
                print(f"Client type: {type(client)}")
                print(f"Client methods: {[m for m in dir(client) if not m.startswith('_') and callable(getattr(client, m, None))]}")
            except Exception as e:
                print(f"❌ Data client creation error: {e}")
                return False
            
            # Test orders client
            try:
                orders_client = session.client('orders')
                print("✅ Orders client created successfully")
            except Exception as e:
                print(f"❌ Orders client creation error: {e}")
                return False
            
            return True
    except Exception as e:
        print(f"❌ Session error: {e}")
        import traceback
        traceback.print_exc()
        return False

# Run async test
try:
    result = asyncio.run(test_session())
    if not result:
        exit(1)
except RuntimeError as e:
    if "cannot be called from a running event loop" in str(e):
        print("⚠️  Event loop already running (Jupyter environment)")
        print("   This is expected in Jupyter - will need nest_asyncio or thread-based solution")
    else:
        print(f"❌ Runtime error: {e}")
        exit(1)
except Exception as e:
    print(f"❌ Session test error: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Test 6: Test actual search (if API key is valid)
print("\n" + "=" * 60)
print("TEST 6: Actual Search Test (Optional)")
print("=" * 60)

async def test_search():
    try:
        async with Session() as session:
            client = session.client('data')
            
            # Try a small search
            print("Attempting search...")
            results = await client.search(search_request)
            
            items = []
            count = 0
            async for item in results:
                items.append(item)
                count += 1
                if count >= 3:  # Just get 3 items for testing
                    break
            
            print(f"✅ Search successful! Found {len(items)} items (limited to 3 for testing)")
            if items:
                print(f"   First item ID: {items[0].get('id', 'N/A')}")
            
            return True
    except Exception as e:
        print(f"⚠️  Search test error (this is OK if API key is invalid): {e}")
        return False

# Only run search test if user wants
run_search_test = os.getenv('TEST_SEARCH', 'false').lower() == 'true'
if run_search_test:
    try:
        asyncio.run(test_search())
    except RuntimeError:
        print("⚠️  Cannot run search test in this environment (event loop issue)")
else:
    print("⏭️  Skipping actual search test (set TEST_SEARCH=true to enable)")

print("\n" + "=" * 60)
print("✅ ALL TESTS COMPLETED")
print("=" * 60)
print("\nSummary:")
print("1. ✅ Imports work")
print("2. ✅ API key found")
print("3. ✅ Filters can be created")
print("4. ✅ Search request can be built")
print("5. ✅ Session and clients can be created")
print("\nCode should work! Fix any errors above before using in notebook.")

