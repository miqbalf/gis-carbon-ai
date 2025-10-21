#!/bin/bash

# Setup MapStore Persistent Configuration
# Following MapStore Docker documentation: https://training.mapstore.geosolutionsgroup.com/administration/docker.html

echo "🔧 Setting up MapStore persistent configuration following official documentation..."

# Create necessary directories
echo "📁 Creating MapStore directory structure..."
mkdir -p ./mapstore/config
mkdir -p ./mapstore/data
mkdir -p ./mapstore/backups
mkdir -p ./mapstore/logs

# Create MapStore configuration following the documentation pattern
echo "📋 Creating MapStore configuration files..."

# Create localConfig.json in the config directory
cat > ./mapstore/config/localConfig.json << 'EOF'
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
      },
      {
        "type": "tile",
        "title": "GEE Analysis Layers",
        "description": "Google Earth Engine analysis layers from FastAPI service",
        "url": "http://localhost:8001/tiles/gee/{layer_name}/{z}/{x}/{y}",
        "format": "image/png",
        "transparent": true,
        "tileSize": 256,
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

# Create gee-integration-config.json
cat > ./mapstore/config/gee-integration-config.json << 'EOF'
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
    }
  }
}
EOF

# Create geoserver-integration-config.json
cat > ./mapstore/config/geoserver-integration-config.json << 'EOF'
{
  "geoserver_integration": {
    "base_url": "http://localhost:8080/geoserver",
    "workspaces": {
      "demo_workspace": {
        "name": "demo_workspace",
        "description": "Demo workspace for testing",
        "auth_required": true,
        "auth_type": "basic",
        "username": "admin",
        "password": "admin"
      },
      "gis_carbon": {
        "name": "gis_carbon",
        "description": "GIS Carbon AI workspace",
        "auth_required": false
      }
    },
    "wms_settings": {
      "version": "1.3.0",
      "format": "image/png",
      "transparent": true,
      "tiled": true,
      "tileSize": 256
    }
  }
}
EOF

# Set proper permissions
echo "🔐 Setting proper permissions..."
chmod 644 ./mapstore/config/*.json
chmod 755 ./mapstore/data
chmod 755 ./mapstore/logs

# Create backup of existing config if it exists
if [ -f "./mapstore/localConfig.json" ]; then
    echo "💾 Creating backup of existing configuration..."
    cp ./mapstore/localConfig.json ./mapstore/backups/localConfig.backup.$(date +%Y%m%d_%H%M%S).json
fi

echo "✅ MapStore persistent configuration setup complete!"
echo ""
echo "📋 What was configured:"
echo "  - Configuration directory: ./mapstore/config/"
echo "  - Data directory: ./mapstore/data/"
echo "  - Logs directory: ./mapstore/logs/"
echo "  - Backup directory: ./mapstore/backups/"
echo ""
echo "🔧 Docker volumes configured (following MapStore documentation):"
echo "  - ./mapstore/config/ → /usr/local/tomcat/webapps/mapstore/config"
echo "  - ./mapstore/geostore-datasource-ovr-postgres.properties → /usr/local/tomcat/conf/geostore-datasource-ovr.properties"
echo "  - mapstore_data_dev → /usr/local/tomcat/webapps/mapstore/data"
echo "  - mapstore_extensions_dev → /usr/local/tomcat/webapps/mapstore/dist/extensions"
echo "  - mapstore_logs_dev → /usr/local/tomcat/logs"
echo ""
echo "🚀 Next steps:"
echo "  1. Restart MapStore container:"
echo "     docker-compose -f docker-compose.dev.yml restart mapstore"
echo "  2. Run GEE analysis notebook to add layers"
echo "  3. Configuration changes will now persist across restarts"
echo ""
echo "📚 Reference: https://training.mapstore.geosolutionsgroup.com/administration/docker.html"
echo "🎯 Your GEE layers will now be permanently available in MapStore!"
