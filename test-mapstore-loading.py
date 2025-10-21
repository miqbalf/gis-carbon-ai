#!/usr/bin/env python3
"""
Test script to diagnose MapStore loading issues
"""

import requests
import json
import time

def test_mapstore_loading():
    """Test MapStore loading and diagnose issues"""
    
    print("🧪 Testing MapStore Loading Issues")
    print("=" * 50)
    
    # Test 1: Check if MapStore HTML loads
    print("\n1️⃣ Testing MapStore HTML loading...")
    try:
        response = requests.get('http://localhost:8082/mapstore/', timeout=10)
        if response.status_code == 200:
            html_content = response.text
            print("   ✅ MapStore HTML loaded successfully")
            
            # Check if it's stuck on loading
            if "Loading MapStore" in html_content:
                print("   ⚠️  Page shows 'Loading MapStore' - might be stuck")
            else:
                print("   ✅ Page loaded beyond loading screen")
                
            # Check for JavaScript file
            if "mapstore2.js" in html_content:
                print("   ✅ JavaScript file referenced in HTML")
            else:
                print("   ❌ JavaScript file not found in HTML")
                
        else:
            print(f"   ❌ MapStore HTML failed to load: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Error loading MapStore HTML: {e}")
        return False
    
    # Test 2: Check if JavaScript file loads
    print("\n2️⃣ Testing JavaScript file loading...")
    try:
        response = requests.get('http://localhost:8082/mapstore/dist/mapstore2.js', timeout=10)
        if response.status_code == 200:
            print(f"   ✅ JavaScript file loaded successfully ({len(response.content)} bytes)")
        else:
            print(f"   ❌ JavaScript file failed to load: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Error loading JavaScript file: {e}")
        return False
    
    # Test 3: Check configuration loading
    print("\n3️⃣ Testing configuration loading...")
    try:
        response = requests.get('http://localhost:8082/mapstore/configs/localConfig.json', timeout=10)
        if response.status_code == 200:
            config = response.json()
            print("   ✅ Configuration loaded successfully")
            
            # Check configuration structure
            if 'map' in config:
                print("   ✅ Configuration has 'map' section")
            else:
                print("   ❌ Configuration missing 'map' section")
                
            if 'plugins' in config:
                print("   ✅ Configuration has 'plugins' section")
            else:
                print("   ❌ Configuration missing 'plugins' section")
                
            if 'catalogServices' in config:
                print("   ✅ Configuration has 'catalogServices' section")
            else:
                print("   ❌ Configuration missing 'catalogServices' section")
                
        else:
            print(f"   ❌ Configuration failed to load: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Error loading configuration: {e}")
        return False
    
    # Test 4: Check extensions loading
    print("\n4️⃣ Testing extensions loading...")
    try:
        response = requests.get('http://localhost:8082/mapstore/extensions/extensions.json', timeout=10)
        if response.status_code == 200:
            extensions = response.json()
            print(f"   ✅ Extensions loaded successfully: {extensions}")
        else:
            print(f"   ❌ Extensions failed to load: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Error loading extensions: {e}")
        return False
    
    # Test 5: Check for any 404 errors
    print("\n5️⃣ Testing for 404 errors...")
    test_urls = [
        'http://localhost:8082/mapstore/dist/mapstore2.js',
        'http://localhost:8082/mapstore/configs/localConfig.json',
        'http://localhost:8082/mapstore/extensions/extensions.json',
        'http://localhost:8082/mapstore/configs/pluginsConfig.json'
    ]
    
    for url in test_urls:
        try:
            response = requests.head(url, timeout=5)
            if response.status_code == 200:
                print(f"   ✅ {url.split('/')[-1]} - OK")
            else:
                print(f"   ❌ {url.split('/')[-1]} - {response.status_code}")
        except Exception as e:
            print(f"   ❌ {url.split('/')[-1]} - Error: {e}")
    
    print("\n" + "=" * 50)
    print("🎯 Diagnosis Summary:")
    print("   If all tests pass but MapStore still shows white screen:")
    print("   1. Check browser console for JavaScript errors")
    print("   2. Try different browser or incognito mode")
    print("   3. Clear browser cache")
    print("   4. Check if there are network issues")
    print("   5. The issue might be in the MapStore JavaScript code itself")
    
    return True

if __name__ == "__main__":
    test_mapstore_loading()
