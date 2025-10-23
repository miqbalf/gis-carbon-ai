"""
Enhanced FastAPI GEE Service with Authentication Layers
Integrates with MapStore and handles login vs non-login layers
"""

from fastapi import FastAPI, HTTPException, Depends, Query, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse
import ee
import redis
import json
import os
import sys
from typing import Optional, Dict, Any, List
import asyncio
from datetime import datetime, timedelta
import logging
import httpx

# Import authentication modules
from auth_layers import (
    get_current_user, require_auth, check_layer_permission,
    layer_access_controller, jwt_auth_manager, layer_auth_manager
)

# Add GEE_notebook_Forestry to Python path
GEE_LIB_PATH = '/app/gee_lib'
if GEE_LIB_PATH not in sys.path:
    sys.path.append(GEE_LIB_PATH)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Enhanced GEE Tile Service with Authentication",
    description="FastAPI service for Google Earth Engine tile processing with MapStore integration",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Redis connection
redis_client = redis.Redis(host='redis', port=6379, db=1, decode_responses=True)

# Initialize Earth Engine
def initialize_ee():
    try:
        service_account = os.getenv('GEE_SERVICE_ACCOUNT', 'iqbalpythonapi@bukit30project.iam.gserviceaccount.com')
        credentials_path = '/app/user_id.json'
        
        if os.path.exists(credentials_path):
            credentials = ee.ServiceAccountCredentials(service_account, credentials_path)
            ee.Initialize(credentials)
            logger.info("Earth Engine initialized successfully")
        else:
            logger.error(f"Credentials file not found at {credentials_path}")
            raise FileNotFoundError("GEE credentials file not found")
    except Exception as e:
        logger.error(f"Failed to initialize Earth Engine: {e}")
        raise

# Initialize EE on startup
initialize_ee()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Enhanced GEE Tile Service API", 
        "version": "2.0.0",
        "features": ["authentication", "layer_access_control", "mapstore_integration"]
    }

# Authentication endpoints
@app.post("/auth/login")
async def login(username: str, password: str):
    """Login endpoint (integrate with Django authentication)"""
    try:
        # Call Django authentication service
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://django:8000/api/auth/login/",
                json={"username": username, "password": password}
            )
            
            if response.status_code == 200:
                user_data = response.json()
                user_id = user_data.get('user_id')
                
                # Create JWT token
                token = jwt_auth_manager.create_token(
                    user_id=user_id,
                    username=username,
                    expires_delta=timedelta(hours=24)
                )
                
                # Store user session
                session_key = f"session:{user_id}"
                redis_client.setex(session_key, 86400, json.dumps(user_data))
                
                return {
                    "access_token": token,
                    "token_type": "bearer",
                    "user": user_data,
                    "expires_in": 86400
                }
            else:
                raise HTTPException(status_code=401, detail="Invalid credentials")
                
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail="Login failed")

@app.post("/auth/logout")
async def logout(user: Dict[str, Any] = Depends(require_auth)):
    """Logout endpoint"""
    user_id = user['user_id']
    session_key = f"session:{user_id}"
    redis_client.delete(session_key)
    
    return {"message": "Logged out successfully"}

# Layer management endpoints
@app.get("/layers/geoserver")
async def get_geoserver_layers(user: Optional[Dict[str, Any]] = Depends(get_current_user)):
    """Get accessible GeoServer layers"""
    try:
        # Get layers from GeoServer
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "http://geoserver:8080/geoserver/rest/workspaces/gis_carbon/layers",
                auth=("admin", "admin")
            )
            
            if response.status_code == 200:
                layers_data = response.json()
                all_layers = [layer['name'] for layer in layers_data.get('layers', {}).get('layer', [])]
                
                # Filter based on user access
                accessible_layers = await layer_access_controller.get_accessible_layers('geoserver', user)
                filtered_layers = [layer for layer in all_layers if layer in accessible_layers]
                
                return {
                    "layers": filtered_layers,
                    "total": len(filtered_layers),
                    "user_authenticated": user is not None
                }
            else:
                raise HTTPException(status_code=500, detail="Failed to fetch GeoServer layers")
                
    except Exception as e:
        logger.error(f"Error fetching GeoServer layers: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/layers/gee")
async def get_gee_layers(user: Optional[Dict[str, Any]] = Depends(get_current_user)):
    """Get accessible GEE layers"""
    try:
        # Get available GEE layers
        available_layers = [
            "FCD1_1", "FCD2_1", "FCD1_2", "FCD2_2",
            "image_mosaick", "avi_image", "bsi_image", "si_image",
            "public_ndvi", "public_landcover"
        ]
        
        # Filter based on user access
        accessible_layers = await layer_access_controller.get_accessible_layers('gee', user)
        filtered_layers = [layer for layer in available_layers if layer in accessible_layers]
        
        return {
            "layers": filtered_layers,
            "total": len(filtered_layers),
            "user_authenticated": user is not None
        }
        
    except Exception as e:
        logger.error(f"Error fetching GEE layers: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Enhanced tile serving with authentication
@app.get("/tiles/{layer_type}/{layer_name}/{z}/{x}/{y}")
async def get_authenticated_tile(
    layer_type: str,
    layer_name: str,
    z: int,
    x: int,
    y: int,
    user: Optional[Dict[str, Any]] = Depends(get_current_user)
):
    """
    Get a tile with authentication check
    layer_type: 'geoserver' or 'gee'
    layer_name: name of the layer
    """
    try:
        # Check layer access permission
        await check_layer_permission(layer_type, layer_name, user)
        
        # Create cache key
        cache_key = f"tile:{layer_type}:{layer_name}:{z}:{x}:{y}"
        
        # Check cache first
        cached_tile = redis_client.get(cache_key)
        if cached_tile:
            logger.info(f"Cache hit for {cache_key}")
            return Response(content=cached_tile, media_type="image/png")
        
        # Generate tile based on layer type
        if layer_type == "geoserver":
            tile_data = await generate_geoserver_tile(layer_name, z, x, y)
        elif layer_type == "gee":
            tile_data = await generate_gee_tile(layer_name, z, x, y)
        else:
            raise HTTPException(status_code=400, detail="Invalid layer type")
        
        # Cache the tile for 1 hour
        redis_client.setex(cache_key, 3600, tile_data)
        
        return Response(content=tile_data, media_type="image/png")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating tile: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# GEE analysis endpoint with authentication
@app.post("/analysis/fcd")
async def run_fcd_analysis(
    analysis_config: Dict[str, Any],
    user: Dict[str, Any] = Depends(require_auth)
):
    """Run FCD analysis (requires authentication)"""
    try:
        # Import GEE_notebook_Forestry modules
        try:
            from gee_lib.osi.fcd.main_fcd import FCDCalc
            from gee_lib.osi.hansen.historical_loss import HansenHistorical
            from gee_lib.osi.classifying.assign_zone import AssignClassZone
        except ImportError as e:
            logger.error(f"Failed to import GEE_notebook_Forestry modules: {e}")
            raise HTTPException(status_code=500, detail="GEE library not available")
        
        # Run FCD analysis
        fcd_calc = FCDCalc(analysis_config)
        result = fcd_calc.fcd_calc()
        
        # Generate tile URLs for MapStore
        tile_urls = {}
        for layer_name, image in result.items():
            if isinstance(image, ee.Image):
                map_id = image.getMapId({
                    'min': 0,
                    'max': 80,
                    'palette': ['ff4c16', 'ffd96c', '39a71d']
                })
                tile_urls[layer_name] = map_id['tile_fetcher'].url_format
        
        # Store result for user
        result_key = f"analysis_result:{user['user_id']}:{datetime.now().isoformat()}"
        redis_client.setex(result_key, 7200, json.dumps({
            'result': result,
            'tile_urls': tile_urls,
            'user_id': user['user_id'],
            'timestamp': datetime.now().isoformat()
        }))
        
        # Add layers to user's accessible layers
        for layer_name in tile_urls.keys():
            layer_auth_manager.add_user_layer(user['user_id'], 'gee', layer_name)
        
        return {
            "status": "success",
            "analysis_id": result_key,
            "tile_urls": tile_urls,
            "mapstore_integration": {
                "layer_type": "gee",
                "base_url": f"http://localhost:8001/tiles/gee/{{layer_name}}/{{z}}/{{x}}/{{y}}",
                "available_layers": list(tile_urls.keys())
            }
        }
        
    except Exception as e:
        logger.error(f"Error in FCD analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# MapStore integration endpoint
@app.get("/mapstore/config")
async def get_mapstore_config(user: Optional[Dict[str, Any]] = Depends(get_current_user)):
    """Get MapStore configuration with user-specific layers"""
    try:
        # Get accessible layers
        geoserver_layers = await layer_access_controller.get_accessible_layers('geoserver', user)
        gee_layers = await layer_access_controller.get_accessible_layers('gee', user)
        
        # Build MapStore configuration
        config = {
            "catalogServices": {
                "services": []
            },
            "layers": []
        }
        
        # Add GeoServer services
        if geoserver_layers:
            config["catalogServices"]["services"].append({
                "type": "wms",
                "title": "GeoServer WMS",
                "url": "http://localhost:8080/geoserver/gis_carbon/wms",
                "format": "image/png",
                "version": "1.3.0",
                "layers": geoserver_layers
            })
        
        # Add GEE services
        if gee_layers:
            config["catalogServices"]["services"].append({
                "type": "tile",
                "title": "GEE Tiles",
                "url": "http://localhost:8001/tiles/gee/{layer_name}/{z}/{x}/{y}",
                "format": "image/png",
                "layers": gee_layers
            })
        
        # Add individual layers
        for layer in geoserver_layers:
            config["layers"].append({
                "type": "wms",
                "name": layer,
                "title": f"GeoServer {layer}",
                "url": "http://localhost:8080/geoserver/gis_carbon/wms",
                "layers": layer,
                "format": "image/png",
                "transparent": True
            })
        
        for layer in gee_layers:
            config["layers"].append({
                "type": "tile",
                "name": layer,
                "title": f"GEE {layer}",
                "url": f"http://localhost:8001/tiles/gee/{layer}/{{z}}/{{x}}/{{y}}",
                "format": "image/png"
            })
        
        return {
            "config": config,
            "user_authenticated": user is not None,
            "user_id": user['user_id'] if user else None
        }
        
    except Exception as e:
        logger.error(f"Error generating MapStore config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Helper functions
async def generate_geoserver_tile(layer_name: str, z: int, x: int, y: int) -> bytes:
    """Generate tile from GeoServer"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"http://geoserver:8080/geoserver/gis_carbon/wms",
                params={
                    "service": "WMS",
                    "version": "1.3.0",
                    "request": "GetMap",
                    "layers": f"gis_carbon:{layer_name}",
                    "format": "image/png",
                    "transparent": "true",
                    "width": "256",
                    "height": "256",
                    "crs": "EPSG:3857",
                    "bbox": f"{x},{y},{x+1},{y+1}"
                }
            )
            
            if response.status_code == 200:
                return response.content
            else:
                raise HTTPException(status_code=500, detail="Failed to generate GeoServer tile")
                
    except Exception as e:
        logger.error(f"Error generating GeoServer tile: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def generate_gee_tile(layer_name: str, z: int, x: int, y: int) -> bytes:
    """Generate tile from GEE"""
    try:
        # This would integrate with your existing GEE processing logic
        # For now, return a placeholder tile
        return b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x01\x00\x00\x00\x01\x00\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xdb\x00\x00\x00\x00IEND\xaeB`\x82'
        
    except Exception as e:
        logger.error(f"Error generating GEE tile: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
