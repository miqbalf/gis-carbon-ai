#!/bin/bash

# Setup MapStore Persistent Storage
# This script ensures MapStore configuration and data persist across container restarts

echo "🔧 Setting up MapStore persistent storage..."

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p ./mapstore/data
mkdir -p ./mapstore/config
mkdir -p ./mapstore/backups

# Ensure configuration files exist
echo "📋 Ensuring configuration files exist..."

# Create localConfig.json if it doesn't exist
if [ ! -f "./mapstore/localConfig.json" ]; then
    echo "  Creating localConfig.json..."
    cat > ./mapstore/localConfig.json << 'EOF'
{
  "map": {
    "center": {
      "x": 106.8,
      "y": -6.25,
      "crs": "EPSG:4326"
    },
    "zoom": 10,
    "maxZoom": 20,
    "minZoom": 1,
    "layers": [
      {
        "type": "osm",
        "title": "OpenStreetMap",
        "name": "osm",
        "visibility": true
      }
    ]
  },
  "plugins": {
    "desktop": [
      "Map",
      "Toolbar",
      "DrawerMenu",
      "ZoomIn",
      "ZoomOut",
      "ZoomAll",
      "BackgroundSelector",
      "LayerTree",
      "TOC",
      "Search",
      "Catalog",
      "Measure",
      "Print",
      "Share",
      "Login"
    ]
  },
  "catalogServices": {
    "services": [
      {
        "type": "wms",
        "title": "GeoServer - Demo Workspace (Auth Required)",
        "url": "http://admin:admin@localhost:8080/geoserver/demo_workspace/wms",
        "format": "image/png",
        "version": "1.3.0",
        "authRequired": true,
        "authType": "basic"
      },
      {
        "type": "wms",
        "title": "GeoServer - Public Layers",
        "url": "http://localhost:8080/geoserver/gis_carbon/wms",
        "format": "image/png",
        "version": "1.3.0",
        "authRequired": false
      }
    ]
  },
  "authentication": {
    "provider": "jwt",
    "loginUrl": "http://localhost:8000/api/auth/unified-login/",
    "logoutUrl": "http://localhost:8000/api/auth/unified-logout/",
    "userUrl": "http://localhost:8000/api/auth/unified-user/",
    "tokenKey": "unified_token",
    "userKey": "user",
    "rolesKey": "roles",
    "loginForm": {
      "enabled": true,
      "title": "GIS Carbon AI - Unified SSO",
      "subtitle": "Access your geospatial data and analysis tools"
    }
  },
  "security": {
    "roles": [
      "ROLE_ANONYMOUS",
      "ROLE_AUTHENTICATED",
      "ADMIN",
      "ANALYST",
      "VIEWER"
    ]
  }
}
EOF
else
    echo "  localConfig.json already exists"
fi

# Create gee-integration-config.json if it doesn't exist
if [ ! -f "./mapstore/gee-integration-config.json" ]; then
    echo "  Creating gee-integration-config.json..."
    cat > ./mapstore/gee-integration-config.json << 'EOF'
{
  "mapstore_gee_integration": {
    "fastapi_connection": {
      "url": "http://localhost:8001",
      "endpoints": {
        "health": "/health",
        "register_layers": "/layers/register",
        "get_layers": "/layers/{project_id}",
        "process_analysis": "/process-gee-analysis"
      }
    },
    "gee_layer_types": {
      "tile": {
        "description": "Google Earth Engine tile layers",
        "format": "image/png",
        "transparent": true,
        "tileSize": 256
      }
    },
    "default_visualization_params": {
      "ndvi": {
        "min": -0.2,
        "max": 0.8,
        "palette": ["red", "yellow", "green", "darkgreen"]
      },
      "evi": {
        "min": -0.2,
        "max": 0.8,
        "palette": ["brown", "yellow", "lightgreen", "darkgreen"]
      },
      "ndwi": {
        "min": -0.3,
        "max": 0.3,
        "palette": ["white", "lightblue", "blue", "darkblue"]
      },
      "true_color": {
        "bands": ["red", "green", "blue"],
        "min": 0,
        "max": 0.3,
        "gamma": 1.4
      },
      "false_color": {
        "bands": ["nir", "red", "green"],
        "min": 0,
        "max": 0.5,
        "gamma": 1.4
      }
    },
    "mapstore_catalog_config": {
      "catalog_services": [
        {
          "type": "tile",
          "title": "GEE Analysis Layers",
          "description": "Google Earth Engine analysis layers from FastAPI service",
          "url": "http://localhost:8001/tiles/gee/{layer_name}/{z}/{x}/{y}",
          "format": "image/png",
          "transparent": true,
          "tileSize": 256,
          "layers": []
        }
      ]
    }
  }
}
EOF
else
    echo "  gee-integration-config.json already exists"
fi

# Set proper permissions
echo "🔐 Setting permissions..."
chmod 644 ./mapstore/localConfig.json
chmod 644 ./mapstore/gee-integration-config.json
chmod 755 ./mapstore/data

# Create backup of current config if it exists
if [ -f "./mapstore/localConfig.json" ]; then
    echo "💾 Creating backup of current configuration..."
    cp ./mapstore/localConfig.json ./mapstore/backups/localConfig.backup.$(date +%Y%m%d_%H%M%S).json
fi

echo "✅ MapStore persistent storage setup complete!"
echo ""
echo "📋 What was configured:"
echo "  - Configuration files: ./mapstore/localConfig.json"
echo "  - GEE integration config: ./mapstore/gee-integration-config.json"
echo "  - Data directory: ./mapstore/data"
echo "  - Backup directory: ./mapstore/backups"
echo ""
echo "🔧 Docker volumes configured:"
echo "  - ./mapstore/localConfig.json → /usr/local/tomcat/webapps/mapstore/localConfig.json"
echo "  - ./mapstore/gee-integration-config.json → /usr/local/tomcat/webapps/mapstore/gee-integration-config.json"
echo "  - mapstore_data_dev → /usr/local/tomcat/webapps/mapstore/data"
echo ""
echo "🚀 Next steps:"
echo "  1. Restart MapStore container:"
echo "     docker-compose -f docker-compose.dev.yml restart mapstore"
echo "  2. Run GEE analysis notebook to add layers"
echo "  3. Configuration changes will now persist across restarts"
echo ""
echo "🎯 Your GEE layers will now be permanently available in MapStore!"
