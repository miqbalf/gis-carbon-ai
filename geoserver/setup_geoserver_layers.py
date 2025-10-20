#!/usr/bin/env python3
"""
Script to automatically configure GeoServer layers for authentication testing
This script creates data stores and layers in GeoServer for our login vs non-login simulation
"""

import requests
import json
import base64
from requests.auth import HTTPBasicAuth

# GeoServer configuration
GEOSERVER_URL = "http://localhost:8080/geoserver"
GEOSERVER_USER = "admin"
GEOSERVER_PASSWORD = "admin"
WORKSPACE = "gis_carbon"

# Database configuration
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "gis_carbon_data"
DB_USER = "gis_user"
DB_PASSWORD = "gis_password"

def create_auth_demo_workspace():
    """Create a dedicated workspace for authentication demo"""
    workspace_data = {
        "workspace": {
            "name": "auth_demo",
            "href": f"{GEOSERVER_URL}/rest/workspaces/auth_demo.json"
        }
    }
    
    response = requests.post(
        f"{GEOSERVER_URL}/rest/workspaces",
        json=workspace_data,
        auth=HTTPBasicAuth(GEOSERVER_USER, GEOSERVER_PASSWORD),
        headers={'Content-Type': 'application/json'}
    )
    
    if response.status_code in [200, 201]:
        print("✅ Created auth_demo workspace")
    elif response.status_code == 409:
        print("ℹ️  auth_demo workspace already exists")
    else:
        print(f"❌ Failed to create workspace: {response.status_code} - {response.text}")

def create_postgres_datastore():
    """Create PostgreSQL data store for authentication demo"""
    datastore_data = {
        "dataStore": {
            "name": "auth_demo_postgres",
            "type": "PostGIS",
            "enabled": True,
            "connectionParameters": {
                "entry": [
                    {"@key": "host", "$": DB_HOST},
                    {"@key": "port", "$": DB_PORT},
                    {"@key": "database", "$": DB_NAME},
                    {"@key": "schema", "$": "auth_demo"},
                    {"@key": "user", "$": DB_USER},
                    {"@key": "passwd", "$": DB_PASSWORD},
                    {"@key": "dbtype", "$": "postgis"},
                    {"@key": "Expose primary keys", "$": "true"}
                ]
            }
        }
    }
    
    response = requests.post(
        f"{GEOSERVER_URL}/rest/workspaces/auth_demo/datastores",
        json=datastore_data,
        auth=HTTPBasicAuth(GEOSERVER_USER, GEOSERVER_PASSWORD),
        headers={'Content-Type': 'application/json'}
    )
    
    if response.status_code in [200, 201]:
        print("✅ Created PostgreSQL data store")
    else:
        print(f"❌ Failed to create data store: {response.status_code} - {response.text}")

def create_layer(layer_name, table_name, title, description, is_public=True):
    """Create a layer in GeoServer"""
    
    # Layer configuration
    layer_data = {
        "featureType": {
            "name": layer_name,
            "nativeName": table_name,
            "title": title,
            "description": description,
            "enabled": True,
            "advertised": True,
            "srs": "EPSG:4326",
            "nativeBoundingBox": {
                "minx": 106.8,
                "maxx": 106.9,
                "miny": -6.25,
                "maxy": -6.15,
                "crs": "EPSG:4326"
            },
            "latLonBoundingBox": {
                "minx": 106.8,
                "maxx": 106.9,
                "miny": -6.25,
                "maxy": -6.15,
                "crs": "EPSG:4326"
            },
            "attributes": {
                "attribute": [
                    {"name": "id", "binding": "java.lang.Integer"},
                    {"name": "name", "binding": "java.lang.String"},
                    {"name": "description", "binding": "java.lang.String"},
                    {"name": "geom", "binding": "com.vividsolutions.jts.geom.Point"}
                ]
            }
        }
    }
    
    response = requests.post(
        f"{GEOSERVER_URL}/rest/workspaces/auth_demo/datastores/auth_demo_postgres/featuretypes",
        json=layer_data,
        auth=HTTPBasicAuth(GEOSERVER_USER, GEOSERVER_PASSWORD),
        headers={'Content-Type': 'application/json'}
    )
    
    if response.status_code in [200, 201]:
        print(f"✅ Created layer: {layer_name}")
        
        # Set layer style based on access level
        if is_public:
            set_layer_style(layer_name, "public_style")
        else:
            set_layer_style(layer_name, "private_style")
            
    else:
        print(f"❌ Failed to create layer {layer_name}: {response.status_code} - {response.text}")

def set_layer_style(layer_name, style_name):
    """Set style for a layer"""
    style_data = {
        "layer": {
            "defaultStyle": {
                "name": style_name
            }
        }
    }
    
    response = requests.put(
        f"{GEOSERVER_URL}/rest/layers/auth_demo:{layer_name}",
        json=style_data,
        auth=HTTPBasicAuth(GEOSERVER_USER, GEOSERVER_PASSWORD),
        headers={'Content-Type': 'application/json'}
    )
    
    if response.status_code in [200, 201]:
        print(f"✅ Set style {style_name} for layer {layer_name}")
    else:
        print(f"⚠️  Could not set style for {layer_name}: {response.status_code}")

def create_styles():
    """Create SLD styles for public and private layers"""
    
    # Public style (green)
    public_style = """<?xml version="1.0" encoding="UTF-8"?>
<StyledLayerDescriptor version="1.0.0" xmlns="http://www.opengis.net/sld" xmlns:ogc="http://www.opengis.net/ogc" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <NamedLayer>
    <Name>public_style</Name>
    <UserStyle>
      <Title>Public Layer Style</Title>
      <Abstract>Green style for public layers</Abstract>
      <FeatureTypeStyle>
        <Rule>
          <PointSymbolizer>
            <Graphic>
              <Mark>
                <WellKnownName>circle</WellKnownName>
                <Fill>
                  <CssParameter name="fill">#00FF00</CssParameter>
                </Fill>
                <Stroke>
                  <CssParameter name="stroke">#006600</CssParameter>
                  <CssParameter name="stroke-width">2</CssParameter>
                </Stroke>
              </Mark>
              <Size>10</Size>
            </Graphic>
          </PointSymbolizer>
        </Rule>
      </FeatureTypeStyle>
    </UserStyle>
  </NamedLayer>
</StyledLayerDescriptor>"""
    
    # Private style (red)
    private_style = """<?xml version="1.0" encoding="UTF-8"?>
<StyledLayerDescriptor version="1.0.0" xmlns="http://www.opengis.net/sld" xmlns:ogc="http://www.opengis.net/ogc" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <NamedLayer>
    <Name>private_style</Name>
    <UserStyle>
      <Title>Private Layer Style</Title>
      <Abstract>Red style for private layers</Abstract>
      <FeatureTypeStyle>
        <Rule>
          <PolygonSymbolizer>
            <Fill>
              <CssParameter name="fill">#FF0000</CssParameter>
              <CssParameter name="fill-opacity">0.5</CssParameter>
            </Fill>
            <Stroke>
              <CssParameter name="stroke">#CC0000</CssParameter>
              <CssParameter name="stroke-width">2</CssParameter>
            </Stroke>
          </PolygonSymbolizer>
        </Rule>
      </FeatureTypeStyle>
    </UserStyle>
  </NamedLayer>
</StyledLayerDescriptor>"""
    
    # Create public style
    response = requests.post(
        f"{GEOSERVER_URL}/rest/styles",
        data=public_style,
        auth=HTTPBasicAuth(GEOSERVER_USER, GEOSERVER_PASSWORD),
        headers={'Content-Type': 'application/vnd.ogc.sld+xml'}
    )
    
    if response.status_code in [200, 201]:
        print("✅ Created public style")
    else:
        print(f"⚠️  Could not create public style: {response.status_code}")
    
    # Create private style
    response = requests.post(
        f"{GEOSERVER_URL}/rest/styles",
        data=private_style,
        auth=HTTPBasicAuth(GEOSERVER_USER, GEOSERVER_PASSWORD),
        headers={'Content-Type': 'application/vnd.ogc.sld+xml'}
    )
    
    if response.status_code in [200, 201]:
        print("✅ Created private style")
    else:
        print(f"⚠️  Could not create private style: {response.status_code}")

def main():
    """Main function to set up all layers"""
    print("🚀 Setting up GeoServer layers for authentication testing...")
    
    # Step 1: Create workspace
    create_auth_demo_workspace()
    
    # Step 2: Create data store
    create_postgres_datastore()
    
    # Step 3: Create styles
    create_styles()
    
    # Step 4: Create layers
    print("\n📊 Creating test layers...")
    
    # Public layers (no authentication required)
    create_layer(
        "public_sample_geometries",
        "public_sample_geometries",
        "Public Sample Geometries",
        "Public layer visible to everyone - Green points",
        is_public=True
    )
    
    # Private layers (authentication required)
    create_layer(
        "private_analysis_results",
        "private_analysis_results", 
        "Private Analysis Results",
        "Private layer requiring authentication - Red polygons",
        is_public=False
    )
    
    create_layer(
        "admin_system_config",
        "admin_system_config",
        "Admin System Configuration", 
        "Admin-only layer - System configuration points",
        is_public=False
    )
    
    print("\n✅ GeoServer layer setup complete!")
    print("\n📋 Created layers:")
    print("   🌍 Public layers (no auth required):")
    print("      - auth_demo:public_sample_geometries")
    print("   🔒 Private layers (auth required):")
    print("      - auth_demo:private_analysis_results")
    print("      - auth_demo:admin_system_config")
    
    print("\n🔗 Test URLs:")
    print(f"   WMS Capabilities: {GEOSERVER_URL}/auth_demo/wms?service=WMS&version=1.3.0&request=GetCapabilities")
    print(f"   Public Layer: {GEOSERVER_URL}/auth_demo/wms?service=WMS&version=1.3.0&request=GetMap&layers=auth_demo:public_sample_geometries&format=image/png&width=256&height=256&crs=EPSG:4326&bbox=106.8,-6.25,106.9,-6.15")
    print(f"   Private Layer: {GEOSERVER_URL}/auth_demo/wms?service=WMS&version=1.3.0&request=GetMap&layers=auth_demo:private_analysis_results&format=image/png&width=256&height=256&crs=EPSG:4326&bbox=106.8,-6.25,106.9,-6.15")

if __name__ == "__main__":
    main()
