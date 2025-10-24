from fastapi import FastAPI, HTTPException, Depends, Query
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
import xml.etree.ElementTree as ET

# Add GEE_notebook_Forestry to Python path
GEE_LIB_PATH = '/app/gee_lib'
if GEE_LIB_PATH not in sys.path:
    sys.path.append(GEE_LIB_PATH)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="GEE Tile Service",
    description="FastAPI service for Google Earth Engine tile processing",
    version="1.0.0"
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
redis_client = redis.Redis(host='redis', port=6379, db=1, decode_responses=False)

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
@app.head("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/test-tile")
async def test_tile():
    """Test endpoint to return a simple colored tile"""
    try:
        # Create a simple green tile
        tile_data = create_colored_tile(0, 255, 0, 255)  # Green tile
        
        return Response(
            content=tile_data,
            media_type="image/png",
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, HEAD, OPTIONS",
                "Access-Control-Allow-Headers": "*",
                "Cache-Control": "public, max-age=3600",
                "Cross-Origin-Resource-Policy": "cross-origin"
            }
        )
    except Exception as e:
        logger.error(f"Error creating test tile: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/direct-tile/{project_id}/{layer}/{z}/{x}/{y}")
async def direct_tile(project_id: str, layer: str, z: int, x: int, y: int):
    """Direct tile endpoint that bypasses WMTS complexity"""
    try:
        # Generate tile directly
        tile_result = await generate_gee_tile(project_id, layer, z, x, y)
        
        if isinstance(tile_result, tuple):
            tile_data, content_type = tile_result
        else:
            tile_data, content_type = tile_result, "image/png"
        
        return Response(
            content=tile_data,
            media_type=content_type,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, HEAD, OPTIONS",
                "Access-Control-Allow-Headers": "*",
                "Cache-Control": "public, max-age=3600",
                "Cross-Origin-Resource-Policy": "cross-origin"
            }
        )
    except Exception as e:
        logger.error(f"Error generating direct tile: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tms/{project_id}/{layer}/{z}/{x}/{y}.png")
@app.head("/tms/{project_id}/{layer}/{z}/{x}/{y}.png")
async def tms_tile(project_id: str, layer: str, z: int, x: int, y: int):
    """TMS tile endpoint for MapStore compatibility"""
    try:
        # Generate tile directly
        tile_result = await generate_gee_tile(project_id, layer, z, x, y)

        if isinstance(tile_result, tuple):
            tile_data, content_type = tile_result
        else:
            tile_data, content_type = tile_result, "image/png"

        return Response(
            content=tile_data,
            media_type=content_type,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, HEAD, OPTIONS",
                "Access-Control-Allow-Headers": "*",
                "Cache-Control": "public, max-age=3600",
                "Cross-Origin-Resource-Policy": "cross-origin"
            }
        )
    except Exception as e:
        logger.error(f"Error generating TMS tile: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Session-based TMS endpoints for dynamic layer management
@app.get("/tms/session/{session_id}/{layer_name}/{z}/{x}/{y}.png")
@app.head("/tms/session/{session_id}/{layer_name}/{z}/{x}/{y}.png")
async def tms_session_tile(session_id: str, layer_name: str, z: int, x: int, y: int):
    """TMS tile endpoint for session-based layer management"""
    try:
        from gee_integration import SessionBasedTMSManager
        
        # Get layer info from session
        tms_manager = SessionBasedTMSManager()
        layers_result = tms_manager.get_session_layers(session_id)
        
        if layers_result['status'] != 'success':
            raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
        
        # Find the requested layer
        layer_info = None
        for layer in layers_result['layers']:
            if layer['layer_name'] == layer_name:
                layer_info = layer
                break
        
        if not layer_info:
            raise HTTPException(status_code=404, detail=f"Layer '{layer_name}' not found in session '{session_id}'")
        
        # Generate tile based on layer configuration
        if layer_info['use_proxy']:
            # Use the original GEE URL for tile generation
            # Extract project_id and layer from the stored URL
            import re
            url_match = re.search(r'/tiles/([^/]+)/([^/]+)/', layer_info['layer_url'])
            if url_match:
                project_id = url_match.group(1)
                original_layer = url_match.group(2)
                tile_result = await generate_gee_tile(project_id, original_layer, z, x, y)
            else:
                raise HTTPException(status_code=500, detail="Invalid layer URL format")
        else:
            # Use direct GEE URL
            import requests
            response = requests.get(layer_info['layer_url'].format(z=z, x=x, y=y))
            if response.status_code == 200:
                tile_data = response.content
                content_type = response.headers.get('content-type', 'image/png')
            else:
                raise HTTPException(status_code=500, detail="Failed to fetch tile from GEE")
            return Response(
                content=tile_data,
                media_type=content_type,
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, HEAD, OPTIONS",
                    "Access-Control-Allow-Headers": "*",
                    "Cache-Control": "public, max-age=3600",
                    "Cross-Origin-Resource-Policy": "cross-origin"
                }
            )

        if isinstance(tile_result, tuple):
            tile_data, content_type = tile_result
        else:
            tile_data, content_type = tile_result, "image/png"

        return Response(
            content=tile_data,
            media_type=content_type,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, HEAD, OPTIONS",
                "Access-Control-Allow-Headers": "*",
                "Cache-Control": "public, max-age=3600",
                "Cross-Origin-Resource-Policy": "cross-origin"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating session TMS tile: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tms/dynamic/{layer_name}/{z}/{x}/{y}.png")
@app.head("/tms/dynamic/{layer_name}/{z}/{x}/{y}.png")
async def tms_dynamic_tile(layer_name: str, z: int, x: int, y: int):
    """TMS tile endpoint for dynamic layer management (global registry)"""
    try:
        from gee_integration import DynamicTMSManager
        
        # Get layer info from dynamic registry
        tms_manager = DynamicTMSManager()
        layer_config = tms_manager.get_layer_config(layer_name)
        
        if layer_config['status'] != 'success':
            raise HTTPException(status_code=404, detail=f"Layer '{layer_name}' not found in dynamic registry")
        
        # Generate tile based on layer configuration
        layer_info = tms_manager.active_layers[layer_name]
        
        if layer_info['use_proxy']:
            # Use the original GEE URL for tile generation
            import re
            url_match = re.search(r'/tiles/([^/]+)/([^/]+)/', layer_info['url'])
            if url_match:
                project_id = url_match.group(1)
                original_layer = url_match.group(2)
                tile_result = await generate_gee_tile(project_id, original_layer, z, x, y)
            else:
                raise HTTPException(status_code=500, detail="Invalid layer URL format")
        else:
            # Use direct GEE URL
            import requests
            response = requests.get(layer_info['url'].format(z=z, x=x, y=y))
            if response.status_code == 200:
                tile_data = response.content
                content_type = response.headers.get('content-type', 'image/png')
            else:
                raise HTTPException(status_code=500, detail="Failed to fetch tile from GEE")
            return Response(
                content=tile_data,
                media_type=content_type,
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, HEAD, OPTIONS",
                    "Access-Control-Allow-Headers": "*",
                    "Cache-Control": "public, max-age=3600",
                    "Cross-Origin-Resource-Policy": "cross-origin"
                }
            )

        if isinstance(tile_result, tuple):
            tile_data, content_type = tile_result
        else:
            tile_data, content_type = tile_result, "image/png"

        return Response(
            content=tile_data,
            media_type=content_type,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, HEAD, OPTIONS",
                "Access-Control-Allow-Headers": "*",
                "Cache-Control": "public, max-age=3600",
                "Cross-Origin-Resource-Policy": "cross-origin"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating dynamic TMS tile: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Session Management API endpoints
@app.post("/api/sessions/{session_id}")
async def create_session(session_id: str, user_id: str = None):
    """Create or update a session"""
    try:
        from gee_integration import SessionBasedTMSManager
        
        tms_manager = SessionBasedTMSManager()
        result = tms_manager.create_session(session_id, user_id)
        
        return result
    except Exception as e:
        logger.error(f"Error creating session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/sessions/{session_id}/layers")
async def add_layer_to_session(
    session_id: str, 
    layer_name: str, 
    layer_url: str, 
    layer_title: str = None, 
    use_proxy: bool = True
):
    """Add a TMS layer to a session"""
    try:
        from gee_integration import SessionBasedTMSManager
        
        tms_manager = SessionBasedTMSManager()
        result = tms_manager.add_layer_to_session(
            session_id, layer_name, layer_url, layer_title, use_proxy
        )
        
        return result
    except Exception as e:
        logger.error(f"Error adding layer to session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sessions/{session_id}/layers")
async def get_session_layers(session_id: str):
    """Get all layers for a session"""
    try:
        from gee_integration import SessionBasedTMSManager
        
        tms_manager = SessionBasedTMSManager()
        result = tms_manager.get_session_layers(session_id)
        
        return result
    except Exception as e:
        logger.error(f"Error getting session layers: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/sessions/{session_id}/layers/{layer_name}")
async def remove_layer_from_session(session_id: str, layer_name: str):
    """Remove a layer from a session"""
    try:
        from gee_integration import SessionBasedTMSManager
        
        tms_manager = SessionBasedTMSManager()
        result = tms_manager.remove_layer_from_session(session_id, layer_name)
        
        return result
    except Exception as e:
        logger.error(f"Error removing layer from session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/sessions/{session_id}/layers")
async def clear_session_layers(session_id: str):
    """Clear all layers from a session"""
    try:
        from gee_integration import SessionBasedTMSManager
        
        tms_manager = SessionBasedTMSManager()
        result = tms_manager.clear_session_layers(session_id)
        
        return result
    except Exception as e:
        logger.error(f"Error clearing session layers: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Dynamic TMS Management API endpoints
@app.post("/api/dynamic/layers")
async def register_dynamic_layer(
    layer_name: str, 
    layer_url: str, 
    layer_title: str = None, 
    use_proxy: bool = True
):
    """Register a layer in the dynamic TMS registry"""
    try:
        from gee_integration import DynamicTMSManager
        
        tms_manager = DynamicTMSManager()
        result = tms_manager.register_layer(layer_name, layer_url, layer_title, use_proxy)
        
        return result
    except Exception as e:
        logger.error(f"Error registering dynamic layer: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/dynamic/layers")
async def list_dynamic_layers():
    """List all layers in the dynamic TMS registry"""
    try:
        from gee_integration import DynamicTMSManager
        
        tms_manager = DynamicTMSManager()
        result = tms_manager.list_active_layers()
        
        return result
    except Exception as e:
        logger.error(f"Error listing dynamic layers: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/dynamic/layers/{layer_name}")
async def unregister_dynamic_layer(layer_name: str):
    """Unregister a layer from the dynamic TMS registry"""
    try:
        from gee_integration import DynamicTMSManager
        
        tms_manager = DynamicTMSManager()
        result = tms_manager.unregister_layer(layer_name)
        
        return result
    except Exception as e:
        logger.error(f"Error unregistering dynamic layer: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Improved WMTS endpoint with Y-coordinate flipping fix
@app.get("/wmts")
@app.post("/wmts")
@app.head("/wmts")
async def wmts_service_improved(
    service: str = Query("WMTS"),
    version: str = Query("1.0.0"),
    request: str = Query("GetCapabilities"),
    layer: str = Query(""),
    tilematrixset: str = Query("GoogleMapsCompatible"),
    tilematrix: str = Query(""),
    tilerow: str = Query(""),
    tilecol: str = Query(""),
    format: str = Query("image/png"),
    # Aliases for mixed-case parameters from MapStore
    Service: str = Query(None, alias="Service"),
    REQUEST: str = Query(None, alias="Request"),
    Layer: str = Query(None, alias="Layer"),
    TileMatrixSet: str = Query(None, alias="TileMatrixSet"),
    TileMatrix: str = Query(None, alias="TileMatrix"),
    TileRow: str = Query(None, alias="TileRow"),
    TileCol: str = Query(None, alias="TileCol"),
    Format: str = Query(None, alias="Format"),
    Style: str = Query(None, alias="Style")
):
    """Improved WMTS service endpoint with Y-coordinate flipping fix"""
    try:
        # Use aliased parameters if provided, otherwise use lowercase ones
        req_type = REQUEST or request
        layer_name = Layer or layer
        tms_set = TileMatrixSet or tilematrixset
        tm = TileMatrix or tilematrix
        tr = TileRow or tilerow
        tc = TileCol or tilecol
        fmt = Format or format
        
        if req_type == "GetCapabilities":
            capabilities_xml = generate_wmts_capabilities_improved()
            return Response(
                content=capabilities_xml,
                media_type="application/xml",
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, HEAD, OPTIONS",
                    "Access-Control-Allow-Headers": "*"
                }
            )
        elif req_type == "GetTile":
            return await wmts_get_tile_improved(layer_name, tms_set, tm, tr, tc, fmt)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported request: {req_type}")
    except Exception as e:
        logger.error(f"Error in improved WMTS service: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "GEE Tile Service API", "version": "1.0.0"}

@app.get("/tiles/{project_id}/{z}/{x}/{y}")
async def get_tile(
    project_id: str,
    z: int,
    x: int,
    y: int,
    layer: str = Query("FCD1_1", description="Layer name to render"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)")
):
    """
    Get a single tile for a specific project and layer
    """
    try:
        # Create cache key
        cache_key = f"tile:{project_id}:{layer}:{z}:{x}:{y}"
        
        # Check cache first
        cached_tile = redis_client.get(cache_key)
        if cached_tile:
            logger.info(f"Cache hit for {cache_key}")
            return Response(content=cached_tile, media_type="image/png")
        
        # Generate tile
        tile_data = await generate_gee_tile(project_id, layer, z, x, y, start_date, end_date)
        
        # Cache the tile for 1 hour
        redis_client.setex(cache_key, 3600, tile_data)
        
        return Response(content=tile_data, media_type="image/png")
        
    except Exception as e:
        logger.error(f"Error generating tile: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tiles/gee/{z}/{x}/{y}")
@app.head("/tiles/gee/{z}/{x}/{y}")
async def get_gee_tile(
    z: int,
    x: int,
    y: int,
    layer: str = Query("ndvi", description="Layer name to render")
):
    """
    Get a GEE tile for MapStore compatibility (TMS format)
    This endpoint serves tiles from registered projects
    """
    try:
        # Create cache key
        cache_key = f"tile:gee:{layer}:{z}:{x}:{y}"
        
        # Check cache first
        cached_tile = redis_client.get(cache_key)
        if cached_tile:
            logger.info(f"Cache hit for {cache_key}")
            return Response(content=cached_tile, media_type="image/png")
        
        # Try to find the layer in registered projects
        project_keys = redis_client.keys("project:*")
        layer_found = False
        
        for project_key in project_keys:
            project_data = redis_client.get(project_key)
            if project_data:
                project_info = json.loads(project_data)
                layers_info = project_info.get('layers', {})
                
                if layer in layers_info:
                    # Generate tile using the found layer
                    tile_data = await generate_gee_tile("gee", layer, z, x, y)
                    layer_found = True
                    break
        
        if not layer_found:
            # Fallback: try to generate tile anyway
            tile_data = await generate_gee_tile("gee", layer, z, x, y)
        
        # Cache the tile for 1 hour
        redis_client.setex(cache_key, 3600, tile_data)
        
        return Response(content=tile_data, media_type="image/png")
        
    except Exception as e:
        logger.error(f"Error generating GEE tile: {e}")
        # Return a placeholder tile instead of error
        return Response(content=create_colored_tile(128, 128, 128, 255), media_type="image/png")




@app.get("/tiles/{project_id}/{layer_name}/{z}/{x}/{y}")
@app.head("/tiles/{project_id}/{layer_name}/{z}/{x}/{y}")
async def get_project_tile(
    project_id: str,
    layer_name: str,
    z: int,
    x: int,
    y: int
):
    """
    Get a tile from a registered project (TMS format)
    This is the main endpoint for MapStore to consume GEE layers
    """
    try:
        # Check cache first
        cache_key = f"tile:project:{project_id}:{layer_name}:{z}:{x}:{y}"
        cached_tile = redis_client.get(cache_key)
        if cached_tile:
            logger.info(f"Cache hit for {cache_key}")
            return Response(content=cached_tile, media_type="image/png")
        
        # Try to get layer info from registered projects
        project_key = f"project:{project_id}"
        project_data = redis_client.get(project_key)
        
        if project_data:
            project_info = json.loads(project_data)
            layers_info = project_info.get('layers', {})
            
            if layer_name in layers_info:
                # Use the existing generate_gee_tile function
                tile_data = await generate_gee_tile("gee", layer_name, z, x, y)
                
                # Cache the tile
                redis_client.setex(cache_key, 3600, tile_data)
                
                return Response(content=tile_data, media_type="image/png")
        
        # Fallback: try to generate tile anyway
        tile_data = await generate_gee_tile("gee", layer_name, z, x, y)
        redis_client.setex(cache_key, 3600, tile_data)
        
        return Response(content=tile_data, media_type="image/png")
        
    except Exception as e:
        logger.error(f"Error generating project tile: {e}")
        # Return a placeholder tile instead of error
        return Response(content=create_colored_tile(128, 128, 128, 255), media_type="image/png")

@app.get("/search")
async def search_layers(
    q: str = Query("", description="Search query"),
    type: str = Query("", description="Layer type filter"),
    limit: int = Query(10, description="Maximum number of results")
):
    """
    Search for layers - MapStore compatibility endpoint
    Dynamically searches through registered GEE catalogs
    """
    try:
        # Get layers from registered catalogs
        search_layers = []
        
        # Try to get layers from registered catalogs
        try:
            # Get all catalog keys from Redis
            catalog_keys = redis_client.keys("catalog:*")
            
            for catalog_key in catalog_keys:
                catalog_data = redis_client.get(catalog_key)
                if catalog_data:
                    catalog_info = json.loads(catalog_data)
                    project_id = catalog_info.get('project_id', 'unknown')
                    project_name = catalog_info.get('project_name', 'GEE Analysis')
                    layers = catalog_info.get('layers', {})
                    
                    for layer_name, layer_info in layers.items():
                        # Create layer entry for search
                        full_layer_name = f"{project_id}_{layer_name}"
                        layer_entry = {
                            "name": full_layer_name,
                            "title": layer_info.get('name', layer_name),
                            "description": layer_info.get('description', f'{layer_name} from {project_name}'),
                            "type": "tms",
                            "url": layer_info.get('tile_url', ''),
                            "project_id": project_id,
                            "project_name": project_name,
                            "layer_name": layer_name
                        }
                        search_layers.append(layer_entry)
        except Exception as e:
            logger.warning(f"Could not load catalog layers: {e}")
        
        # If no catalog layers found, use default fallback layers
        if not search_layers:
            search_layers = [
                {
                    "name": "sentinel_true_color",
                    "title": "Sentinel-2 True Color",
                    "description": "True Color RGB visualization from Sentinel-2",
                    "type": "tms",
                    "url": "https://earthengine.googleapis.com/v1/projects/earthengine-legacy/maps/1b749899d57475b8da0c62721b07c0ba-18f438d0290e925a528c6bb116c38dfe/tiles/{z}/{x}/{y}"
                },
                {
                    "name": "sentinel_ndvi", 
                    "title": "Sentinel-2 NDVI",
                    "description": "Normalized Difference Vegetation Index from Sentinel-2",
                    "type": "tms",
                    "url": "https://earthengine.googleapis.com/v1/projects/earthengine-legacy/maps/34e1b4bfca361fdbd734d4638ad507ee-228c3523ed27dda41377d61fbff5cbd1/tiles/{z}/{x}/{y}"
                },
                {
                    "name": "sentinel_evi",
                    "title": "Sentinel-2 EVI",
                    "description": "Enhanced Vegetation Index from Sentinel-2",
                    "type": "tms", 
                    "url": "https://earthengine.googleapis.com/v1/projects/earthengine-legacy/maps/087609fc3b3c354bad9f3bcef540a392-6afa9b25fcd660a2dccb246b5b33d035/tiles/{z}/{x}/{y}"
                },
                {
                    "name": "sentinel_ndwi",
                    "title": "Sentinel-2 NDWI", 
                    "description": "Normalized Difference Water Index from Sentinel-2",
                    "type": "tms",
                    "url": "https://earthengine.googleapis.com/v1/projects/earthengine-legacy/maps/d53bd437b713e1e2f1a2d96cdc97b07f-33170c3c03889940f2ef8b6be6be7f51/tiles/{z}/{x}/{y}"
                }
            ]
        
        # Filter layers based on search query
        if q:
            filtered_layers = [
                layer for layer in search_layers 
                if q.lower() in layer["name"].lower() or 
                   q.lower() in layer["title"].lower() or
                   q.lower() in layer["description"].lower()
            ]
        else:
            filtered_layers = search_layers
            
        # Apply type filter
        if type:
            filtered_layers = [layer for layer in filtered_layers if layer["type"] == type]
            
        # Limit results
        filtered_layers = filtered_layers[:limit]
        
        # MapStore expects a specific format for search results
        return {
            "results": {
                "records": filtered_layers,
                "numberOfRecordsMatched": len(filtered_layers),
                "numberOfRecordsReturned": len(filtered_layers)
            }
        }
        
    except Exception as e:
        logger.error(f"Error searching layers: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/csw")
@app.post("/csw")
async def csw_service(
    service: str = Query("CSW", description="Service type"),
    version: str = Query("2.0.2", description="CSW version"),
    request: str = Query("GetCapabilities", description="Request type"),
    outputformat: str = Query("application/xml", description="Output format"),
    request_body: str = None
):
    """
    CSW (Catalog Service for Web) endpoint for MapStore compatibility
    Dynamically serves GEE analysis results as CSW records
    """
    try:
        # Check if this is a GetRecords request (POST with XML body)
        if request == "GetRecords" or (request_body and "GetRecords" in request_body):
            # Build dynamic records from registered catalogs
            records_xml = ""
            total_records = 0
            
            try:
                # Get all catalog keys from Redis
                catalog_keys = redis_client.keys("catalog:*")
                
                for catalog_key in catalog_keys:
                    catalog_data = redis_client.get(catalog_key)
                    if catalog_data:
                        catalog_info = json.loads(catalog_data)
                        project_id = catalog_info.get('project_id', 'unknown')
                        project_name = catalog_info.get('project_name', 'GEE Analysis')
                        layers = catalog_info.get('layers', {})
                        
                        for layer_name, layer_info in layers.items():
                            full_layer_id = f"{project_id}_{layer_name}"
                            layer_title = layer_info.get('name', layer_name)
                            layer_description = layer_info.get('description', f'{layer_name} from {project_name}')
                            tile_url = layer_info.get('tile_url', '')
                            
                            # Create CSW record for TMS layer
                            records_xml += f"""
        <csw:Record>
            <dc:identifier>{full_layer_id}</dc:identifier>
            <dc:title>{layer_title}</dc:title>
            <dc:type>dataset</dc:type>
            <dc:description>{layer_description}</dc:description>
            <dc:subject>GEE, Analysis, {layer_name.upper()}</dc:subject>
            <dc:creator>Google Earth Engine</dc:creator>
            <dc:source>{project_name}</dc:source>
            <dct:references scheme="OGC:TMS">{tile_url}</dct:references>
            <dct:references scheme="OGC:WMS">http://localhost:8001/wms?service=WMS&amp;version=1.3.0&amp;request=GetMap&amp;layers={full_layer_id}&amp;styles=&amp;crs=EPSG:3857&amp;bbox=-20037508.34,-20037508.34,20037508.34,20037508.34&amp;width=256&amp;height=256</dct:references>
        </csw:Record>"""
                            total_records += 1
                            
            except Exception as e:
                logger.warning(f"Could not load catalog layers for CSW: {e}")
                # Fallback to default records
                records_xml = """
        <csw:Record>
            <dc:identifier>sentinel_true_color</dc:identifier>
            <dc:title>Sentinel-2 True Color</dc:title>
            <dc:type>dataset</dc:type>
            <dc:description>True Color RGB visualization from Sentinel-2</dc:description>
            <dc:subject>GEE, Sentinel-2, True Color</dc:subject>
            <dct:references scheme="OGC:TMS">https://earthengine.googleapis.com/v1/projects/earthengine-legacy/maps/1b749899d57475b8da0c62721b07c0ba-18f438d0290e925a528c6bb116c38dfe/tiles/{z}/{x}/{y}</dct:references>
        </csw:Record>
        <csw:Record>
            <dc:identifier>sentinel_ndvi</dc:identifier>
            <dc:title>Sentinel-2 NDVI</dc:title>
            <dc:type>dataset</dc:type>
            <dc:description>Normalized Difference Vegetation Index from Sentinel-2</dc:description>
            <dc:subject>GEE, Sentinel-2, NDVI</dc:subject>
            <dct:references scheme="OGC:TMS">https://earthengine.googleapis.com/v1/projects/earthengine-legacy/maps/34e1b4bfca361fdbd734d4638ad507ee-228c3523ed27dda41377d61fbff5cbd1/tiles/{z}/{x}/{y}</dct:references>
        </csw:Record>"""
                total_records = 2
            
            # Return GetRecords response with dynamic records
            getrecords_response = f"""<?xml version="1.0" encoding="UTF-8"?>
<csw:GetRecordsResponse xmlns:csw="http://www.opengis.net/cat/csw/2.0.2" 
                        xmlns:dc="http://purl.org/dc/elements/1.1/" 
                        xmlns:dct="http://purl.org/dc/terms/"
                        xmlns:ows="http://www.opengis.net/ows"
                        version="2.0.2">
    <csw:SearchStatus timestamp="{datetime.now().isoformat()}Z" status="complete"/>
    <csw:SearchResults numberOfRecordsMatched="{total_records}" numberOfRecordsReturned="{total_records}" nextRecord="0" recordSchema="http://www.opengis.net/cat/csw/2.0.2">{records_xml}
    </csw:SearchResults>
</csw:GetRecordsResponse>"""
            return Response(content=getrecords_response, media_type="application/xml")
        
        else:
            # Return GetCapabilities response
            capabilities_response = """<?xml version="1.0" encoding="UTF-8"?>
<csw:Capabilities xmlns:csw="http://www.opengis.net/cat/csw/2.0.2" 
                  xmlns:ows="http://www.opengis.net/ows" 
                  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                  version="2.0.2">
    <ows:ServiceIdentification>
        <ows:Title>GEE Dynamic Analysis Service</ows:Title>
        <ows:Abstract>Google Earth Engine Analysis Layers - Dynamically Updated</ows:Abstract>
        <ows:ServiceType>CSW</ows:ServiceType>
        <ows:ServiceTypeVersion>2.0.2</ows:ServiceTypeVersion>
    </ows:ServiceIdentification>
    <ows:OperationsMetadata>
        <ows:Operation name="GetCapabilities">
            <ows:DCP>
                <ows:HTTP>
                    <ows:Get xlink:href="http://localhost:8001/csw"/>
                    <ows:Post xlink:href="http://localhost:8001/csw"/>
                </ows:HTTP>
            </ows:DCP>
        </ows:Operation>
        <ows:Operation name="GetRecords">
            <ows:DCP>
                <ows:HTTP>
                    <ows:Get xlink:href="http://localhost:8001/csw"/>
                    <ows:Post xlink:href="http://localhost:8001/csw"/>
                </ows:HTTP>
            </ows:DCP>
        </ows:Operation>
    </ows:OperationsMetadata>
</csw:Capabilities>"""
            return Response(content=capabilities_response, media_type="application/xml")
        
    except Exception as e:
        logger.error(f"Error in CSW service: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/wms")
@app.post("/wms")
async def wms_service(
    service: str = Query("WMS", description="Service type"),
    version: str = Query("1.3.0", description="WMS version"),
    request: str = Query("GetCapabilities", description="Request type"),
    layers: str = Query("", description="Layer names"),
    styles: str = Query("", description="Style names"),
    crs: str = Query("EPSG:3857", description="Coordinate reference system"),
    bbox: str = Query("", description="Bounding box"),
    width: int = Query(256, description="Image width"),
    height: int = Query(256, description="Image height"),
    format: str = Query("image/png", description="Output format")
):
    """
    WMS (Web Map Service) endpoint for MapStore compatibility
    Following OGC WMS 1.3.0 standard
    """
    try:
        # Validate service type
        if service.upper() != "WMS":
            raise HTTPException(status_code=400, detail="Invalid service type. Must be WMS.")
        
        if request == "GetCapabilities":
            return await wms_get_capabilities()
        elif request == "GetMap":
            return await wms_get_map(layers, bbox, width, height, crs, format)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported request: {request}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in WMS service: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def wms_get_capabilities():
    """
    WMS GetCapabilities response
    """
    try:
        # Build dynamic layers from registered catalogs
        layers_xml = ""
        
        try:
            # Get all catalog keys from Redis
            catalog_keys = redis_client.keys("catalog:*")
            
            for catalog_key in catalog_keys:
                catalog_data = redis_client.get(catalog_key)
                if catalog_data:
                    catalog_info = json.loads(catalog_data)
                    project_id = catalog_info.get('project_id', 'unknown')
                    project_name = catalog_info.get('project_name', 'GEE Analysis')
                    layers = catalog_info.get('layers', {})
                    
                    for layer_name, layer_info in layers.items():
                        full_layer_name = f"{project_id}_{layer_name}"
                        layer_title = layer_info.get('name', layer_name)
                        layer_description = layer_info.get('description', f'{layer_name} from {project_name}')
                        
                        layers_xml += f"""
            <Layer queryable="1">
                <Name>{full_layer_name}</Name>
                <Title>{layer_title}</Title>
                <Abstract>{layer_description}</Abstract>
                <CRS>EPSG:3857</CRS>
                <CRS>EPSG:4326</CRS>
                <BoundingBox CRS="EPSG:3857" minx="-20037508.34" miny="-20037508.34" maxx="20037508.34" maxy="20037508.34"/>
            </Layer>"""
        except Exception as e:
            logger.warning(f"Could not load catalog layers for WMS: {e}")
            # Fallback to default layers
            layers_xml = """
            <Layer queryable="1">
                <Name>sentinel_true_color</Name>
                <Title>Sentinel-2 True Color</Title>
                <Abstract>True Color RGB visualization from Sentinel-2</Abstract>
                <CRS>EPSG:3857</CRS>
                <CRS>EPSG:4326</CRS>
                <BoundingBox CRS="EPSG:3857" minx="-20037508.34" miny="-20037508.34" maxx="20037508.34" maxy="20037508.34"/>
            </Layer>
            <Layer queryable="1">
                <Name>sentinel_ndvi</Name>
                <Title>Sentinel-2 NDVI</Title>
                <Abstract>Normalized Difference Vegetation Index from Sentinel-2</Abstract>
                <CRS>EPSG:3857</CRS>
                <CRS>EPSG:4326</CRS>
                <BoundingBox CRS="EPSG:3857" minx="-20037508.34" miny="-20037508.34" maxx="20037508.34" maxy="20037508.34"/>
            </Layer>
            <Layer queryable="1">
                <Name>sentinel_evi</Name>
                <Title>Sentinel-2 EVI</Title>
                <Abstract>Enhanced Vegetation Index from Sentinel-2</Abstract>
                <CRS>EPSG:3857</CRS>
                <CRS>EPSG:4326</CRS>
                <BoundingBox CRS="EPSG:3857" minx="-20037508.34" miny="-20037508.34" maxx="20037508.34" maxy="20037508.34"/>
            </Layer>
            <Layer queryable="1">
                <Name>sentinel_ndwi</Name>
                <Title>Sentinel-2 NDWI</Title>
                <Abstract>Normalized Difference Water Index from Sentinel-2</Abstract>
                <CRS>EPSG:3857</CRS>
                <CRS>EPSG:4326</CRS>
                <BoundingBox CRS="EPSG:3857" minx="-20037508.34" miny="-20037508.34" maxx="20037508.34" maxy="20037508.34"/>
            </Layer>"""
            
            # Build complete WMS capabilities
            wms_capabilities = f"""<?xml version="1.0" encoding="UTF-8"?>
<WMS_Capabilities version="1.3.0" xmlns="http://www.opengis.net/wms" xmlns:xlink="http://www.w3.org/1999/xlink">
    <Service>
        <Name>WMS</Name>
        <Title>GEE Dynamic Analysis WMS Service</Title>
        <Abstract>Google Earth Engine Analysis Layers via WMS - Dynamically Updated</Abstract>
        <OnlineResource xlink:href="http://localhost:8001/wms"/>
    </Service>
    <Capability>
        <Request>
            <GetCapabilities>
                <Format>text/xml</Format>
                <DCPType>
                    <HTTP>
                        <Get>
                            <OnlineResource xlink:href="http://localhost:8001/wms"/>
                        </Get>
                    </HTTP>
                </DCPType>
            </GetCapabilities>
            <GetMap>
                <Format>image/png</Format>
                <DCPType>
                    <HTTP>
                        <Get>
                            <OnlineResource xlink:href="http://localhost:8001/wms"/>
                        </Get>
                    </HTTP>
                </DCPType>
            </GetMap>
        </Request>
        <Layer>
            <Title>GEE Analysis Layers</Title>{layers_xml}
        </Layer>
    </Capability>
</WMS_Capabilities>"""
            return Response(content=wms_capabilities, media_type="application/xml")
        
    except Exception as e:
        logger.error(f"Error generating WMS capabilities: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def wms_get_map(layers: str, bbox: str, width: int, height: int, crs: str, format: str):
    """
    WMS GetMap response - renders GEE tiles as WMS image
    """
    try:
        # Validate parameters
        if not layers:
            raise HTTPException(status_code=400, detail="layers parameter is required")
        
        if not bbox:
            raise HTTPException(status_code=400, detail="bbox parameter is required")
        
        # Parse bounding box
        try:
            bbox_parts = bbox.split(',')
            if len(bbox_parts) != 4:
                raise ValueError("Invalid bbox format")
            minx, miny, maxx, maxy = map(float, bbox_parts)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid bbox format. Use: minx,miny,maxx,maxy")
        
        # Get first layer
        layer_name = layers.split(',')[0]
        
        # Try to find layer in registered catalogs
        layer_found = False
        tile_data = None
        
        try:
            # Get all catalog keys from Redis
            catalog_keys = redis_client.keys("catalog:*")
            
            for catalog_key in catalog_keys:
                catalog_data = redis_client.get(catalog_key)
                if catalog_data:
                    catalog_info = json.loads(catalog_data)
                    project_id = catalog_info.get('project_id', 'unknown')
                    layers_info = catalog_info.get('layers', {})
                    
                    # Check if this layer belongs to this project
                    if layer_name.startswith(f"{project_id}_"):
                        base_layer_name = layer_name.replace(f"{project_id}_", "")
                        if base_layer_name in layers_info:
                            layer_info = layers_info[base_layer_name]
                            
                            # Calculate zoom level and tile coordinates from bbox
                            import math
                            zoom = max(0, min(18, int(math.log2(20037508.34 * 2 / (maxx - minx)))))
                            
                            # Calculate tile coordinates
                            n = 2.0 ** zoom
                            tile_x = int((minx + 20037508.34) / (40075016.68 / n))
                            tile_y = int((20037508.34 - maxy) / (40075016.68 / n))
                            
                            # Generate tile using existing function
                            tile_data = await generate_gee_tile(project_id, base_layer_name, zoom, tile_x, tile_y)
                            layer_found = True
                            break
        except Exception as e:
            logger.warning(f"Error processing catalog layer {layer_name}: {e}")
        
        # Fallback to default layers
        if not layer_found:
            default_layers = {
                'sentinel_true_color': 'true_color',
                'sentinel_ndvi': 'ndvi',
                'sentinel_evi': 'evi',
                'sentinel_ndwi': 'ndwi',
                'sentinel_false_color': 'false_color'
            }
            
            if layer_name in default_layers:
                base_layer_name = default_layers[layer_name]
                
                # Calculate zoom level and tile coordinates
                import math
                zoom = max(0, min(18, int(math.log2(20037508.34 * 2 / (maxx - minx)))))
                n = 2.0 ** zoom
                tile_x = int((minx + 20037508.34) / (40075016.68 / n))
                tile_y = int((20037508.34 - maxy) / (40075016.68 / n))
                
                try:
                    tile_data = await generate_gee_tile("gee", base_layer_name, zoom, tile_x, tile_y)
                    layer_found = True
                except Exception as e:
                    logger.warning(f"Error generating default tile for {base_layer_name}: {e}")
        
        # Return tile data or fallback
        if tile_data:
            return Response(content=tile_data, media_type="image/png")
        else:
            # Return a placeholder tile
            placeholder = create_colored_tile(128, 128, 128, 255)
            return Response(content=placeholder, media_type="image/png")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in WMS GetMap: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/gwc/service/wmts")
@app.post("/gwc/service/wmts")
@app.head("/gwc/service/wmts")
@app.options("/gwc/service/wmts")
async def wmts_service(
    service: str = Query("WMTS", description="Service type"),
    version: str = Query("1.0.0", description="WMTS version"),
    REQUEST: str = Query("GetCapabilities", description="Request type"),
    layer: str = Query("", description="Layer name"),
    tileMatrixSet: str = Query("", description="Tile matrix set"),
    tilematrixset: str = Query("", description="Tile matrix set (lowercase)"),
    expandLimit: int = Query(10, description="Expand limit"),
    TileMatrix: int = Query(0, description="Tile matrix level"),
    TileCol: int = Query(0, description="Tile column"),
    TileRow: int = Query(0, description="Tile row")
):
    """
    WMTS (Web Map Tile Service) endpoint for MapStore compatibility
    Following OGC WMTS 1.0.0 standard
    """
    try:
        # Validate service type
        if service.upper() != "WMTS":
            raise HTTPException(status_code=400, detail="Invalid service type. Must be WMTS.")
        
        if REQUEST == "GetCapabilities":
            return await wmts_get_capabilities()
        elif REQUEST == "GetTile":
            # Use the correct parameter (MapStore uses lowercase)
            matrix_set = tilematrixset or tileMatrixSet
            return await wmts_get_tile(layer, matrix_set, TileMatrix, TileCol, TileRow)
        elif REQUEST == "DescribeDomains":
            return await wmts_describe_domains(layer, tileMatrixSet, expandLimit)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported request: {REQUEST}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in WMTS service: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def wmts_get_capabilities():
    """
    WMTS GetCapabilities response
    """
    try:
        # Build dynamic layers from registered catalogs
        layers_xml = ""
        
        try:
            # Get all catalog keys from Redis
            catalog_keys = redis_client.keys("catalog:*")
            
            for catalog_key in catalog_keys:
                catalog_data = redis_client.get(catalog_key)
                if catalog_data:
                    catalog_info = json.loads(catalog_data)
                    project_id = catalog_info.get('project_id', 'unknown')
                    project_name = catalog_info.get('project_name', 'GEE Analysis')
                    layers = catalog_info.get('layers', {})
                    
                    # Extract bbox information from analysis_info
                    aoi_info = catalog_info.get('analysis_info', {}).get('aoi', {})
                    bbox_coords = aoi_info.get('coordinates', [])
                    center = aoi_info.get('center', [0, 0])
                    
                    # Calculate bbox bounds
                    if bbox_coords and len(bbox_coords) > 0:
                        # bbox_coords is [[109.5, -1.5], [110.5, -1.5], [110.5, -0.5], [109.5, -0.5], [109.5, -1.5]]
                        lons = [coord[0] for coord in bbox_coords]
                        lats = [coord[1] for coord in bbox_coords]
                        bbox_minx, bbox_maxx = min(lons), max(lons)
                        bbox_miny, bbox_maxy = min(lats), max(lats)
                        bbox_wkt = f"POLYGON(({bbox_minx} {bbox_miny}, {bbox_maxx} {bbox_miny}, {bbox_maxx} {bbox_maxy}, {bbox_minx} {bbox_maxy}, {bbox_minx} {bbox_miny}))"
                    else:
                        # Default bbox if not available
                        bbox_minx, bbox_maxx = center[0] - 0.5, center[0] + 0.5
                        bbox_miny, bbox_maxy = center[1] - 0.5, center[1] + 0.5
                        bbox_wkt = f"POLYGON(({bbox_minx} {bbox_miny}, {bbox_maxx} {bbox_miny}, {bbox_maxx} {bbox_maxy}, {bbox_minx} {bbox_maxy}, {bbox_minx} {bbox_miny}))"
                    
                    for layer_name, layer_info in layers.items():
                        full_layer_name = f"{project_id}_{layer_name}"
                        layer_title = layer_info.get('name', layer_name)
                        layer_description = layer_info.get('description', f'{layer_name} from {project_name}')
                        tile_url = layer_info.get('tile_url', '')
                        
                        layers_xml += f"""
                <Layer>
                    <ows:Title>{layer_title}</ows:Title>
                    <ows:Identifier>{full_layer_name}</ows:Identifier>
                    <ows:Abstract>{layer_description}</ows:Abstract>
                    <ows:WGS84BoundingBox>
                        <ows:LowerCorner>{bbox_minx} {bbox_miny}</ows:LowerCorner>
                        <ows:UpperCorner>{bbox_maxx} {bbox_maxy}</ows:UpperCorner>
                    </ows:WGS84BoundingBox>
                    <ResourceURL format="image/png"
                        template="http://localhost:8001/gwc/service/wmts?service=WMTS&amp;version=1.0.0&amp;REQUEST=GetTile&amp;layer={full_layer_name}&amp;tilematrixset=GoogleMapsCompatible&amp;TileMatrix={{TileMatrix}}&amp;TileCol={{TileCol}}&amp;TileRow={{TileRow}}"/>
                    <TileMatrixSetLink>
                        <TileMatrixSet>GoogleMapsCompatible</TileMatrixSet>
                    </TileMatrixSetLink>
                </Layer>"""
        except Exception as e:
            logger.warning(f"Could not load catalog layers for WMTS: {e}")
            # Fallback to default layers
            layers_xml = """
                <Layer>
                    <ows:Title>Sentinel-2 True Color</ows:Title>
                    <ows:Identifier>sentinel_true_color</ows:Identifier>
                    <ows:Abstract>True Color RGB visualization from Sentinel-2</ows:Abstract>
                    <ResourceURL format="image/png"
                        template="http://localhost:8001/gwc/service/wmts?service=WMTS&amp;version=1.0.0&amp;REQUEST=GetTile&amp;layer=sentinel_true_color&amp;tilematrixset=GoogleMapsCompatible&amp;TileMatrix={TileMatrix}&amp;TileCol={TileCol}&amp;TileRow={TileRow}"/>
                    <TileMatrixSetLink>
                        <TileMatrixSet>GoogleMapsCompatible</TileMatrixSet>
                    </TileMatrixSetLink>
                </Layer>
                <Layer>
                    <ows:Title>Sentinel-2 NDVI</ows:Title>
                    <ows:Identifier>sentinel_ndvi</ows:Identifier>
                    <ows:Abstract>Normalized Difference Vegetation Index from Sentinel-2</ows:Abstract>
                    <ResourceURL format="image/png"
                        template="http://localhost:8001/gwc/service/wmts?service=WMTS&amp;version=1.0.0&amp;REQUEST=GetTile&amp;layer=sentinel_ndvi&amp;tilematrixset=GoogleMapsCompatible&amp;TileMatrix={TileMatrix}&amp;TileCol={TileCol}&amp;TileRow={TileRow}"/>
                    <TileMatrixSetLink>
                        <TileMatrixSet>GoogleMapsCompatible</TileMatrixSet>
                    </TileMatrixSetLink>
                </Layer>
                <Layer>
                    <ows:Title>Sentinel-2 EVI</ows:Title>
                    <ows:Identifier>sentinel_evi</ows:Identifier>
                    <ows:Abstract>Enhanced Vegetation Index from Sentinel-2</ows:Abstract>
                    <ResourceURL format="image/png"
                        template="http://localhost:8001/gwc/service/wmts?service=WMTS&amp;version=1.0.0&amp;REQUEST=GetTile&amp;layer=sentinel_evi&amp;tilematrixset=GoogleMapsCompatible&amp;TileMatrix={TileMatrix}&amp;TileCol={TileCol}&amp;TileRow={TileRow}"/>
                    <TileMatrixSetLink>
                        <TileMatrixSet>GoogleMapsCompatible</TileMatrixSet>
                    </TileMatrixSetLink>
                </Layer>
                <Layer>
                    <ows:Title>Sentinel-2 NDWI</ows:Title>
                    <ows:Identifier>sentinel_ndwi</ows:Identifier>
                    <ows:Abstract>Normalized Difference Water Index from Sentinel-2</ows:Abstract>
                    <ResourceURL format="image/png"
                        template="http://localhost:8001/gwc/service/wmts?service=WMTS&amp;version=1.0.0&amp;REQUEST=GetTile&amp;layer=sentinel_ndwi&amp;tilematrixset=GoogleMapsCompatible&amp;TileMatrix={TileMatrix}&amp;TileCol={TileCol}&amp;TileRow={TileRow}"/>
                    <TileMatrixSetLink>
                        <TileMatrixSet>GoogleMapsCompatible</TileMatrixSet>
                    </TileMatrixSetLink>
                </Layer>"""
        
        # Build complete WMTS capabilities
        wmts_capabilities = f"""<?xml version="1.0" encoding="UTF-8"?>
<Capabilities xmlns="http://www.opengis.net/wmts/1.0"
    xmlns:ows="http://www.opengis.net/ows/1.1"
    xmlns:xlink="http://www.w3.org/1999/xlink"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xmlns:gml="http://www.opengis.net/gml"
    xsi:schemaLocation="http://www.opengis.net/wmts/1.0
    http://schemas.opengis.net/wmts/1.0/wmtsGetCapabilities_response.xsd"
    version="1.0.0">
    <ows:ServiceIdentification>
        <ows:Title>GEE Dynamic Analysis WMTS Service</ows:Title>
        <ows:Abstract>Google Earth Engine Analysis Layers via WMTS - Dynamically Updated</ows:Abstract>
        <ows:ServiceType>OGC WMTS</ows:ServiceType>
        <ows:ServiceTypeVersion>1.0.0</ows:ServiceTypeVersion>
        <ows:Fees>NONE</ows:Fees>
        <ows:AccessConstraints>NONE</ows:AccessConstraints>
    </ows:ServiceIdentification>
    <ows:ServiceProvider>
        <ows:ProviderName>GEE Analysis Service</ows:ProviderName>
        <ows:ProviderSite xlink:href="http://localhost:8001"/>
        <ows:ServiceContact>
            <ows:IndividualName>GEE Analysis Administrator</ows:IndividualName>
            <ows:PositionName>System Administrator</ows:PositionName>
        </ows:ServiceContact>
    </ows:ServiceProvider>
    <ows:OperationsMetadata>
        <ows:Operation name="GetCapabilities">
            <ows:DCP>
                <ows:HTTP>
                    <ows:Get xlink:href="http://localhost:8001/gwc/service/wmts"/>
                </ows:HTTP>
            </ows:DCP>
        </ows:Operation>
        <ows:Operation name="GetTile">
            <ows:DCP>
                <ows:HTTP>
                    <ows:Get xlink:href="http://localhost:8001/gwc/service/wmts"/>
                </ows:HTTP>
            </ows:DCP>
        </ows:Operation>
        <ows:Operation name="DescribeDomains">
            <ows:DCP>
                <ows:HTTP>
                    <ows:Get xlink:href="http://localhost:8001/gwc/service/wmts"/>
                </ows:HTTP>
            </ows:DCP>
        </ows:Operation>
    </ows:OperationsMetadata>
    <Contents>{layers_xml}
        <TileMatrixSet>
            <ows:Identifier>GoogleMapsCompatible</ows:Identifier>
            <ows:SupportedCRS>EPSG:3857</ows:SupportedCRS>
            <TileMatrix>
                <ows:Identifier>0</ows:Identifier>
                <ScaleDenominator>559082264.029</ScaleDenominator>
                <TopLeftCorner>-20037508.3427892 20037508.3427892</TopLeftCorner>
                <TileWidth>256</TileWidth>
                <TileHeight>256</TileHeight>
                <MatrixWidth>1</MatrixWidth>
                <MatrixHeight>1</MatrixHeight>
            </TileMatrix>
            <TileMatrix>
                <ows:Identifier>1</ows:Identifier>
                <ScaleDenominator>279541132.014</ScaleDenominator>
                <TopLeftCorner>-20037508.3427892 20037508.3427892</TopLeftCorner>
                <TileWidth>256</TileWidth>
                <TileHeight>256</TileHeight>
                <MatrixWidth>2</MatrixWidth>
                <MatrixHeight>2</MatrixHeight>
            </TileMatrix>
            <TileMatrix>
                <ows:Identifier>2</ows:Identifier>
                <ScaleDenominator>139770566.007</ScaleDenominator>
                <TopLeftCorner>-20037508.3427892 20037508.3427892</TopLeftCorner>
                <TileWidth>256</TileWidth>
                <TileHeight>256</TileHeight>
                <MatrixWidth>4</MatrixWidth>
                <MatrixHeight>4</MatrixHeight>
            </TileMatrix>
            <TileMatrix>
                <ows:Identifier>3</ows:Identifier>
                <ScaleDenominator>69885283.003</ScaleDenominator>
                <TopLeftCorner>-20037508.3427892 20037508.3427892</TopLeftCorner>
                <TileWidth>256</TileWidth>
                <TileHeight>256</TileHeight>
                <MatrixWidth>8</MatrixWidth>
                <MatrixHeight>8</MatrixHeight>
            </TileMatrix>
            <TileMatrix>
                <ows:Identifier>4</ows:Identifier>
                <ScaleDenominator>34942641.502</ScaleDenominator>
                <TopLeftCorner>-20037508.3427892 20037508.3427892</TopLeftCorner>
                <TileWidth>256</TileWidth>
                <TileHeight>256</TileHeight>
                <MatrixWidth>16</MatrixWidth>
                <MatrixHeight>16</MatrixHeight>
            </TileMatrix>
            <TileMatrix>
                <ows:Identifier>5</ows:Identifier>
                <ScaleDenominator>17471320.751</ScaleDenominator>
                <TopLeftCorner>-20037508.3427892 20037508.3427892</TopLeftCorner>
                <TileWidth>256</TileWidth>
                <TileHeight>256</TileHeight>
                <MatrixWidth>32</MatrixWidth>
                <MatrixHeight>32</MatrixHeight>
            </TileMatrix>
            <TileMatrix>
                <ows:Identifier>6</ows:Identifier>
                <ScaleDenominator>8735660.375</ScaleDenominator>
                <TopLeftCorner>-20037508.3427892 20037508.3427892</TopLeftCorner>
                <TileWidth>256</TileWidth>
                <TileHeight>256</TileHeight>
                <MatrixWidth>64</MatrixWidth>
                <MatrixHeight>64</MatrixHeight>
            </TileMatrix>
            <TileMatrix>
                <ows:Identifier>7</ows:Identifier>
                <ScaleDenominator>4367830.188</ScaleDenominator>
                <TopLeftCorner>-20037508.3427892 20037508.3427892</TopLeftCorner>
                <TileWidth>256</TileWidth>
                <TileHeight>256</TileHeight>
                <MatrixWidth>128</MatrixWidth>
                <MatrixHeight>128</MatrixHeight>
            </TileMatrix>
            <TileMatrix>
                <ows:Identifier>8</ows:Identifier>
                <ScaleDenominator>2183915.094</ScaleDenominator>
                <TopLeftCorner>-20037508.3427892 20037508.3427892</TopLeftCorner>
                <TileWidth>256</TileWidth>
                <TileHeight>256</TileHeight>
                <MatrixWidth>256</MatrixWidth>
                <MatrixHeight>256</MatrixHeight>
            </TileMatrix>
            <TileMatrix>
                <ows:Identifier>9</ows:Identifier>
                <ScaleDenominator>1091957.547</ScaleDenominator>
                <TopLeftCorner>-20037508.3427892 20037508.3427892</TopLeftCorner>
                <TileWidth>256</TileWidth>
                <TileHeight>256</TileHeight>
                <MatrixWidth>512</MatrixWidth>
                <MatrixHeight>512</MatrixHeight>
            </TileMatrix>
            <TileMatrix>
                <ows:Identifier>10</ows:Identifier>
                <ScaleDenominator>545978.773</ScaleDenominator>
                <TopLeftCorner>-20037508.3427892 20037508.3427892</TopLeftCorner>
                <TileWidth>256</TileWidth>
                <TileHeight>256</TileHeight>
                <MatrixWidth>1024</MatrixWidth>
                <MatrixHeight>1024</MatrixHeight>
            </TileMatrix>
        </TileMatrixSet>
    </Contents>
</Capabilities>"""
        return Response(content=wmts_capabilities, media_type="application/xml")
        
    except Exception as e:
        logger.error(f"Error generating WMTS capabilities: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def wmts_get_tile(layer: str, tileMatrixSet: str, TileMatrix: int, TileCol: int, TileRow: int):
    """
    WMTS GetTile response - proxies requests to GEE
    """
    try:
        # Validate parameters
        if not layer:
            raise HTTPException(status_code=400, detail="layer parameter is required")
        
        if tileMatrixSet.upper() != "GOOGLEMAPSCOMPATIBLE":
            raise HTTPException(status_code=400, detail=f"Only GoogleMapsCompatible tile matrix set is supported, got: '{tileMatrixSet}'")
        
        # Try to find layer in registered catalogs
        layer_found = False
        tile_data = None
        content_type = "image/png"  # Default content type
        
        try:
            # Get all catalog keys from Redis
            catalog_keys = redis_client.keys("catalog:*")
            
            for catalog_key in catalog_keys:
                catalog_data = redis_client.get(catalog_key)
                if catalog_data:
                    catalog_info = json.loads(catalog_data)
                    catalog_project_id = catalog_info.get('project_id', 'unknown')
                    layers_info = catalog_info.get('layers', {})
                    
                    # Check if this layer belongs to this project
                    if layer.startswith(f"{catalog_project_id}_"):
                        base_layer_name = layer.replace(f"{catalog_project_id}_", "")
                        if base_layer_name in layers_info:
                            # Generate tile using existing function with the catalog project_id
                            tile_result = await generate_gee_tile(catalog_project_id, base_layer_name, TileMatrix, TileCol, TileRow)
                            if isinstance(tile_result, tuple):
                                tile_data, content_type = tile_result
                            else:
                                tile_data, content_type = tile_result, "image/png"
                            layer_found = True
                            break
        except Exception as e:
            logger.warning(f"Error processing catalog layer {layer}: {e}")
        
        # Fallback to default layers
        if not layer_found:
            default_layers = {
                'sentinel_true_color': 'true_color',
                'sentinel_ndvi': 'ndvi',
                'sentinel_evi': 'evi',
                'sentinel_ndwi': 'ndwi',
                'sentinel_false_color': 'false_color'
            }
            
            if layer in default_layers:
                base_layer_name = default_layers[layer]
                
                try:
                    tile_result = await generate_gee_tile("default", base_layer_name, TileMatrix, TileCol, TileRow)
                    if isinstance(tile_result, tuple):
                        tile_data, content_type = tile_result
                    else:
                        tile_data, content_type = tile_result, "image/png"
                    layer_found = True
                except Exception as e:
                    logger.warning(f"Error generating default tile for {base_layer_name}: {e}")
        
        # Return tile data or fallback with proper CORS headers
        if tile_data:
            return Response(
                content=tile_data, 
                media_type=content_type,
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, HEAD, OPTIONS",
                    "Access-Control-Allow-Headers": "*",
                    "Cache-Control": "public, max-age=3600",
                    "Cross-Origin-Resource-Policy": "cross-origin"
                }
            )
        else:
            # Return a placeholder tile
            placeholder = create_colored_tile(128, 128, 128, 255)
            return Response(
                content=placeholder, 
                media_type="image/png",
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, HEAD, OPTIONS",
                    "Access-Control-Allow-Headers": "*",
                    "Cache-Control": "public, max-age=3600",
                    "Cross-Origin-Resource-Policy": "cross-origin"
                }
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in WMTS GetTile: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def wmts_describe_domains(layer: str, tileMatrixSet: str, expandLimit: int):
    """
    WMTS DescribeDomains response
    """
    try:
        # Return empty domains response for compatibility
        domains_response = """<?xml version="1.0" encoding="UTF-8"?>
<Domains xmlns="http://www.opengis.net/wmts/1.0"
         xmlns:ows="http://www.opengis.net/ows/1.1">
    <ows:ServiceIdentification>
        <ows:Title>GEE Dynamic Analysis WMTS Service</ows:Title>
        <ows:ServiceType>OGC WMTS</ows:ServiceType>
    </ows:ServiceIdentification>
    <Domains>
        <Domain>
            <ows:Identifier>default</ows:Identifier>
        </Domain>
    </Domains>
</Domains>"""
        return Response(content=domains_response, media_type="application/xml")
        
    except Exception as e:
        logger.error(f"Error in WMTS DescribeDomains: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/layers/{project_id}")
async def get_project_layers(project_id: str):
    """
    Get registered layers for a project
    """
    try:
        # Try to get from Redis first
        cache_key = f"catalog:{project_id}"
        cached_data = redis_client.get(cache_key)
        
        if cached_data:
            project_data = json.loads(cached_data)
            return {
                "status": "success",
                "project_id": project_id,
                "project_name": project_data.get("project_name", "Unknown"),
                "layers": project_data.get("layers", {}),
                "aoi": project_data.get("aoi"),
                "date_range": project_data.get("date_range"),
                "cached": True
            }
        
        # If not in cache, return default layers for backwards compatibility
        logger.warning(f"Project {project_id} not found in cache, returning defaults")
        layers = {
            "FCD1_1": {"name": "Forest Cover Density 1-1", "description": "Primary FCD layer"},
            "FCD2_1": {"name": "Forest Cover Density 2-1", "description": "Secondary FCD layer"},
            "image_mosaick": {"name": "Image Mosaic", "description": "Satellite image mosaic"},
            "avi_image": {"name": "AVI Image", "description": "Advanced Vegetation Index"},
        }
        
        return {
            "status": "success",
            "project_id": project_id,
            "layers": layers,
            "cached": False,
            "message": "Using default layers, project not found in cache"
        }
        
    except Exception as e:
        logger.error(f"Error getting project layers: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/process/{project_id}")
async def process_project(project_id: str, config: Dict[str, Any]):
    """
    Process a project and return tile URLs
    """
    try:
        # This would integrate with your existing GEE processing logic
        # For now, return a mock response
        result = {
            "project_id": project_id,
            "status": "processing",
            "tile_urls": {
                "FCD1_1": f"http://localhost:8001/tiles/{project_id}/{{z}}/{{x}}/{{y}}?layer=FCD1_1",
                "FCD2_1": f"http://localhost:8001/tiles/{project_id}/{{z}}/{{x}}/{{y}}?layer=FCD2_1",
            },
            "timestamp": datetime.now().isoformat()
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Error processing project: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/layers/register")
async def register_layers(request_data: dict):
    """
    Register GEE layers with metadata (for Jupyter notebook workflow)
    This endpoint stores layer information without running analysis
    """
    try:
        project_id = request_data.get("project_id")
        project_name = request_data.get("project_name", "Unnamed Project")
        layers = request_data.get("layers", {})
        
        logger.info(f"Registering layers for project {project_id}: {len(layers)} layers")
        
        # Validate required fields
        if not project_id:
            raise HTTPException(status_code=400, detail="project_id is required")
        
        if not layers:
            raise HTTPException(status_code=400, detail="At least one layer is required")
        
        # Store in Redis with catalog key format (for compatibility with generate_gee_tile)
        cache_key = f"catalog:{project_id}"
        redis_client.setex(cache_key, 7200, json.dumps(request_data))  # Cache for 2 hours
        
        logger.info(f"Successfully registered project {project_id}")
        
        return {
            "status": "success",
            "project_id": project_id,
            "project_name": project_name,
            "layers_count": len(layers),
            "timestamp": datetime.now().isoformat(),
            "message": "Layers registered successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error registering layers: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

@app.post("/catalog/update")
async def update_mapstore_catalog(request_data: dict):
    """
    Update MapStore catalog with new GEE analysis results
    This endpoint receives GEE analysis results from Jupyter and updates the catalog
    """
    try:
        project_id = request_data.get("project_id")
        project_name = request_data.get("project_name", "GEE Analysis")
        layers = request_data.get("layers", {})
        analysis_info = request_data.get("analysis_info", {})
        
        logger.info(f"Updating MapStore catalog for project {project_id}: {len(layers)} layers")
        
        # Validate required fields
        if not project_id:
            raise HTTPException(status_code=400, detail="project_id is required")
        
        if not layers:
            raise HTTPException(status_code=400, detail="At least one layer is required")
        
        # Store the analysis results in Redis for the catalog service
        catalog_data = {
            "project_id": project_id,
            "project_name": project_name,
            "analysis_info": analysis_info,
            "layers": layers,
            "timestamp": datetime.now().isoformat(),
            "status": "active"
        }
        
        # Store in Redis with a catalog-specific key
        catalog_key = f"catalog:{project_id}"
        redis_client.setex(catalog_key, 86400, json.dumps(catalog_data))  # Cache for 24 hours
        
        # Also store individual layer entries for easy access
        for layer_name, layer_info in layers.items():
            layer_key = f"catalog_layer:{project_id}:{layer_name}"
            layer_data = {
                "project_id": project_id,
                "layer_name": layer_name,
                "layer_info": layer_info,
                "tms_url": layer_info.get('tile_url', ''),
                "timestamp": datetime.now().isoformat()
            }
            redis_client.setex(layer_key, 86400, json.dumps(layer_data))
        
        logger.info(f"Successfully updated catalog for project {project_id}")
        
        return {
            "status": "success",
            "project_id": project_id,
            "project_name": project_name,
            "layers_count": len(layers),
            "timestamp": datetime.now().isoformat(),
            "message": "MapStore catalog updated successfully",
            "catalog_url": f"http://localhost:8001/catalog/{project_id}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating MapStore catalog: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Catalog update failed: {str(e)}")

@app.get("/catalog/{project_id}")
async def get_catalog_info(project_id: str):
    """
    Get catalog information for a specific project
    """
    try:
        catalog_key = f"catalog:{project_id}"
        catalog_data = redis_client.get(catalog_key)
        
        if catalog_data:
            return json.loads(catalog_data)
        else:
            raise HTTPException(status_code=404, detail=f"Project {project_id} not found in catalog")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting catalog info: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/catalog")
async def list_all_catalogs():
    """
    List all available catalogs
    """
    try:
        catalog_keys = redis_client.keys("catalog:*")
        catalogs = []
        
        for key in catalog_keys:
            catalog_data = redis_client.get(key)
            if catalog_data:
                catalog_info = json.loads(catalog_data)
                catalogs.append({
                    "project_id": catalog_info.get("project_id"),
                    "project_name": catalog_info.get("project_name"),
                    "layers_count": len(catalog_info.get("layers", {})),
                    "timestamp": catalog_info.get("timestamp"),
                    "status": catalog_info.get("status")
                })
        
        return {
            "status": "success",
            "catalogs": catalogs,
            "total": len(catalogs)
        }
        
    except Exception as e:
        logger.error(f"Error listing catalogs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/mapstore/wmts/update")
async def update_mapstore_wmts_service(request_data: dict):
    """
    Update MapStore WMTS service configuration
    """
    try:
        service_name = request_data.get("service_name")
        service_config = request_data.get("service_config")
        
        if not service_name or not service_config:
            raise HTTPException(status_code=400, detail="service_name and service_config are required")
        
        # Load current MapStore configuration (auto-detect path)
        import os
        if os.path.exists('/usr/src/app/mapstore/configs/localConfig.json'):
            config_path = "/usr/src/app/mapstore/configs/localConfig.json"
        elif os.path.exists('/app/mapstore/configs/localConfig.json'):
            config_path = "/app/mapstore/configs/localConfig.json"
        else:
            # Fallback to FastAPI container path
            config_path = "/app/mapstore/configs/localConfig.json"
        
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
        except Exception as e:
            logger.error(f"Error loading MapStore config: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to load MapStore config: {e}")
        
        # Update or add GEE WMTS service in the correct location (initialState.defaultState.catalog.services)
        # Navigate to the services section
        if "initialState" not in config:
            config["initialState"] = {}
        if "defaultState" not in config["initialState"]:
            config["initialState"]["defaultState"] = {}
        if "catalog" not in config["initialState"]["defaultState"]:
            config["initialState"]["defaultState"]["catalog"] = {}
        if "default" not in config["initialState"]["defaultState"]["catalog"]:
            config["initialState"]["defaultState"]["catalog"]["default"] = {}
        if "services" not in config["initialState"]["defaultState"]["catalog"]["default"]:
            config["initialState"]["defaultState"]["catalog"]["default"]["services"] = {}

        # Update existing service or add new one in the correct location
        config["initialState"]["defaultState"]["catalog"]["default"]["services"][service_name] = service_config
        logger.info(f"Updated MapStore WMTS service: {service_name}")
        
        # Save updated configuration
        try:
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
            logger.info(f"Successfully updated MapStore configuration with service: {service_name}")
        except Exception as e:
            logger.error(f"Error saving MapStore config: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to save MapStore config: {e}")
        
        return {
            "status": "success",
            "service_name": service_name,
            "message": f"MapStore WMTS service '{service_name}' updated successfully",
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating MapStore WMTS service: {str(e)}")
        raise HTTPException(status_code=500, detail=f"WMTS service update failed: {str(e)}")

@app.get("/mapstore/configs")
async def get_mapstore_config():
    """
    Get current MapStore configuration
    """
    try:
        config_path = "/app/mapstore/configs/localConfig.json"
        
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            return config
        except FileNotFoundError:
            logger.warning(f"MapStore config file not found: {config_path}")
            return {"error": "Config file not found"}
        except Exception as e:
            logger.error(f"Error loading MapStore config: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to load MapStore config: {e}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting MapStore config: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get MapStore config: {str(e)}")

@app.post("/mapstore/configs")
async def update_mapstore_config(config_data: dict):
    """
    Update MapStore configuration
    """
    try:
        # Auto-detect MapStore config path
        import os
        if os.path.exists('/usr/src/app/mapstore/configs/localConfig.json'):
            config_path = "/usr/src/app/mapstore/configs/localConfig.json"
        elif os.path.exists('/app/mapstore/configs/localConfig.json'):
            config_path = "/app/mapstore/configs/localConfig.json"
        else:
            # Fallback to FastAPI container path
            config_path = "/app/mapstore/configs/localConfig.json"

        # Handle dynamic extent calculation if needed
        if isinstance(config_data, dict) and "catalogServices" in config_data:
            for service_name, service_config in config_data["catalogServices"].items():
                if (service_config.get("type") == "wmts" and
                    service_name == "gee_analysis_wmts" and
                    service_config.get('params', {}).get('LAYERS')):

                    layers_param = service_config['params']['LAYERS']
                    if layers_param:
                        # Extract project_id from LAYERS parameter
                        project_id = layers_param
                        try:
                            # Get catalog data for this project
                            catalog_keys = redis_client.keys("catalog:*")
                            for key in catalog_keys:
                                catalog_data = redis_client.get(key)
                                if catalog_data:
                                    catalog_info = json.loads(catalog_data)
                                    if catalog_info.get('project_id') == project_id:
                                        aoi_info = catalog_info.get('analysis_info', {}).get('aoi', {})
                                        if aoi_info and aoi_info.get('bbox'):
                                            bbox = aoi_info['bbox']
                                            # Handle both old format (with lists) and new format (individual numbers)
                                            if isinstance(bbox.get('minx'), list):
                                                # Old format with lists - extract first element
                                                extent = [
                                                    bbox['minx'][0], bbox['miny'][0],
                                                    bbox['maxx'][0], bbox['maxy'][0]
                                                ]
                                            else:
                                                # New format with individual numbers
                                                extent = [bbox['minx'], bbox['miny'], bbox['maxx'], bbox['maxy']]

                                            # Update the service config with the calculated extent
                                            service_config['extent'] = extent
                                            logger.info(f"Updated extent for project {project_id}: {extent}")
                                            break
                        except Exception as e:
                            logger.warning(f"Could not get AOI data for project {project_id}: {e}")

        # Save updated configuration
        try:
            with open(config_path, 'w') as f:
                json.dump(config_data, f, indent=2)
            logger.info("Successfully updated MapStore configuration")
        except Exception as e:
            logger.error(f"Error saving MapStore config: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to save MapStore config: {e}")
        
        return {
            "status": "success",
            "message": "MapStore configuration updated successfully",
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating MapStore config: {str(e)}")
        raise HTTPException(status_code=500, detail=f"MapStore config update failed: {str(e)}")

@app.get("/catalog/mapstore")
async def get_mapstore_catalog():
    """
    Get catalog in MapStore-compatible format
    This endpoint provides all GEE layers as TMS services for MapStore
    """
    try:
        catalog_keys = redis_client.keys("catalog:*")
        tms_services = {}
        
        for key in catalog_keys:
            catalog_data = redis_client.get(key)
            if catalog_data:
                catalog_info = json.loads(catalog_data)
                project_id = catalog_info.get("project_id")
                project_name = catalog_info.get("project_name", "GEE Analysis")
                layers = catalog_info.get("layers", {})
                
                # Create TMS services for each layer
                for layer_name, layer_info in layers.items():
                    service_key = f"gee_{project_id}_{layer_name}"
                    tms_services[service_key] = {
                        "url": layer_info.get('tile_url', ''),
                        "type": "tms",
                        "title": f"{project_name} - {layer_info.get('name', layer_name)}",
                        "autoload": False,
                        "description": layer_info.get('description', ''),
                        "project_id": project_id,
                        "layer_name": layer_name,
                        "timestamp": catalog_info.get("timestamp")
                    }
        
        return {
            "status": "success",
            "services": tms_services,
            "total_services": len(tms_services),
            "message": "MapStore-compatible TMS services"
        }
        
    except Exception as e:
        logger.error(f"Error generating MapStore catalog: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/layers/register-sentinel")
async def register_sentinel_layers():
    """
    Register the Sentinel-2 GEE layers from the notebook analysis
    This creates a predefined set of layers for immediate use
    """
    try:
        # Define the Sentinel-2 layers from the notebook
        sentinel_layers = {
            "project_id": "sentinel_analysis_default",
            "project_name": "Sentinel-2 Cloudless Composite Analysis",
            "aoi": {
                "type": "Polygon",
                "coordinates": [[[109.5, -1.5], [110.5, -1.5], [110.5, -0.5], [109.5, -0.5], [109.5, -1.5]]],
                "center": [109.99999999999977, -1.000012676912049]
            },
            "date_range": {
                "start": "2023-01-01",
                "end": "2023-12-31"
            },
            "analysis_params": {
                "satellite": "Sentinel-2",
                "cloud_cover_threshold": 20,
                "image_count": 25
            },
            "layers": {
                "true_color": {
                    "name": "True Color",
                    "description": "True Color RGB visualization from Sentinel-2",
                    "tile_url": "https://earthengine.googleapis.com/v1/projects/earthengine-legacy/maps/1b749899d57475b8da0c62721b07c0ba-18f438d0290e925a528c6bb116c38dfe/tiles/{z}/{x}/{y}",
                    "map_id": "1b749899d57475b8da0c62721b07c0ba-18f438d0290e925a528c6bb116c38dfe",
                    "token": "18f438d0290e925a528c6bb116c38dfe",
                    "vis_params": {
                        "bands": ["red", "green", "blue"],
                        "min": 0,
                        "max": 0.3,
                        "gamma": 1.4
                    }
                },
                "false_color": {
                    "name": "False Color",
                    "description": "False Color Composite visualization from Sentinel-2",
                    "tile_url": "https://earthengine.googleapis.com/v1/projects/earthengine-legacy/maps/e4e73542a8e911f24707fc4c1027c0f9-6233ec3a871abb50d799098d5c9a00b8/tiles/{z}/{x}/{y}",
                    "map_id": "e4e73542a8e911f24707fc4c1027c0f9-6233ec3a871abb50d799098d5c9a00b8",
                    "token": "6233ec3a871abb50d799098d5c9a00b8",
                    "vis_params": {
                        "bands": ["nir", "red", "green"],
                        "min": 0,
                        "max": 0.5,
                        "gamma": 1.4
                    }
                },
                "ndvi": {
                    "name": "NDVI",
                    "description": "Normalized Difference Vegetation Index from Sentinel-2",
                    "tile_url": "https://earthengine.googleapis.com/v1/projects/earthengine-legacy/maps/34e1b4bfca361fdbd734d4638ad507ee-228c3523ed27dda41377d61fbff5cbd1/tiles/{z}/{x}/{y}",
                    "map_id": "34e1b4bfca361fdbd734d4638ad507ee-228c3523ed27dda41377d61fbff5cbd1",
                    "token": "228c3523ed27dda41377d61fbff5cbd1",
                    "vis_params": {
                        "min": -0.2,
                        "max": 0.8,
                        "palette": ["red", "yellow", "green", "darkgreen"]
                    }
                },
                "evi": {
                    "name": "EVI",
                    "description": "Enhanced Vegetation Index from Sentinel-2",
                    "tile_url": "https://earthengine.googleapis.com/v1/projects/earthengine-legacy/maps/087609fc3b3c354bad9f3bcef540a392-6afa9b25fcd660a2dccb246b5b33d035/tiles/{z}/{x}/{y}",
                    "map_id": "087609fc3b3c354bad9f3bcef540a392-6afa9b25fcd660a2dccb246b5b33d035",
                    "token": "6afa9b25fcd660a2dccb246b5b33d035",
                    "vis_params": {
                        "min": -0.2,
                        "max": 0.8,
                        "palette": ["brown", "yellow", "lightgreen", "darkgreen"]
                    }
                },
                "ndwi": {
                    "name": "NDWI",
                    "description": "Normalized Difference Water Index from Sentinel-2",
                    "tile_url": "https://earthengine.googleapis.com/v1/projects/earthengine-legacy/maps/d53bd437b713e1e2f1a2d96cdc97b07f-33170c3c03889940f2ef8b6be6be7f51/tiles/{z}/{x}/{y}",
                    "map_id": "d53bd437b713e1e2f1a2d96cdc97b07f-33170c3c03889940f2ef8b6be6be7f51",
                    "token": "33170c3c03889940f2ef8b6be6be7f51",
                    "vis_params": {
                        "min": -0.3,
                        "max": 0.3,
                        "palette": ["white", "lightblue", "blue", "darkblue"]
                    }
                }
            }
        }
        
        # Store in Redis
        cache_key = f"project:sentinel_analysis_default"
        redis_client.setex(cache_key, 7200, json.dumps(sentinel_layers))  # Cache for 2 hours
        
        logger.info(f"Successfully registered Sentinel-2 layers")
        
        return {
            "status": "success",
            "project_id": "sentinel_analysis_default",
            "project_name": "Sentinel-2 Cloudless Composite Analysis",
            "layers_count": 5,
            "timestamp": datetime.now().isoformat(),
            "message": "Sentinel-2 layers registered successfully",
            "tms_urls": {
                "true_color": "http://localhost:8001/tiles/gee/{z}/{x}/{y}?layer=true_color",
                "false_color": "http://localhost:8001/tiles/gee/{z}/{x}/{y}?layer=false_color",
                "ndvi": "http://localhost:8001/tiles/gee/{z}/{x}/{y}?layer=ndvi",
                "evi": "http://localhost:8001/tiles/gee/{z}/{x}/{y}?layer=evi",
                "ndwi": "http://localhost:8001/tiles/gee/{z}/{x}/{y}?layer=ndwi"
            }
        }
        
    except Exception as e:
        logger.error(f"Error registering Sentinel-2 layers: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

@app.post("/process-gee-analysis")
async def process_gee_analysis(request_data: dict):
    """
    Process GEE analysis using GEE_notebook_Forestry library
    This endpoint receives requests from Django
    """
    try:
        project_id = request_data.get("project_id")
        analysis_type = request_data.get("analysis_type")  # e.g., "fcd", "hansen", "classification"
        parameters = request_data.get("parameters", {})
        
        logger.info(f"Processing GEE analysis for project {project_id}, type: {analysis_type}")
        
        # If no analysis_type provided, treat as layer registration
        if not analysis_type:
            logger.info("No analysis_type provided, registering layers instead")
            return await register_layers(request_data)
        
        # Import GEE_notebook_Forestry modules
        try:
            from gee_lib.osi.fcd.main_fcd import FCDCalc
            from gee_lib.osi.hansen.historical_loss import HansenHistorical
            from gee_lib.osi.classifying.assign_zone import AssignClassZone
            from gee_lib.osi.area_calc.main import CalcAreaClass
        except ImportError as e:
            logger.error(f"Failed to import GEE_notebook_Forestry modules: {e}")
            raise HTTPException(status_code=500, detail="GEE library not available")
        
        # Process based on analysis type
        if analysis_type == "fcd":
            # Forest Canopy Density analysis
            fcd_calc = FCDCalc(parameters)
            result = fcd_calc.fcd_calc()
            
        elif analysis_type == "hansen":
            # Hansen historical loss analysis
            hansen = HansenHistorical(parameters)
            result = hansen.get_historical_loss()
            
        elif analysis_type == "classification":
            # Land use classification
            classifier = AssignClassZone(parameters)
            result = classifier.classify_land_use()
            
        elif analysis_type == "area_calc":
            # Area calculation
            area_calc = CalcAreaClass(parameters)
            result = area_calc.calculate_areas()
            
        else:
            raise HTTPException(status_code=400, detail=f"Unknown analysis type: {analysis_type}")
        
        # Cache results
        cache_key = f"analysis:{project_id}:{analysis_type}"
        redis_client.setex(cache_key, 7200, json.dumps(result))  # Cache for 2 hours
        
        return {
            "status": "success",
            "project_id": project_id,
            "analysis_type": analysis_type,
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing GEE analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

def is_tile_in_bbox(x: int, y: int, z: int, bbox: Dict[str, float]) -> bool:
    """
    Check if a tile intersects with the given bbox
    Simple geographic bounds check - works well for most cases
    """
    try:
        import math
        
        # Convert tile coordinates to geographic bounds (simple approach)
        n = 2.0 ** z
        lon_min = x / n * 360.0 - 180.0
        lon_max = (x + 1) / n * 360.0 - 180.0
        lat_max = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n))))
        lat_min = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (y + 1) / n))))
        
        # Check if tile bounds intersect with bbox
        intersects = not (lon_max < bbox['minx'] or lon_min > bbox['maxx'] or 
                         lat_max < bbox['miny'] or lat_min > bbox['maxy'])
        
        logger.info(f"Bbox check: tile({x},{y},{z}) -> geo({lon_min:.4f},{lat_min:.4f},{lon_max:.4f},{lat_max:.4f}) vs bbox({bbox['minx']:.4f},{bbox['miny']:.4f},{bbox['maxx']:.4f},{bbox['maxy']:.4f}) -> intersects={intersects}")
        
        return intersects
    except Exception as e:
        logger.warning(f"Error checking tile bbox: {e}")
        return True  # Default to allowing the tile

async def generate_gee_tile(project_id: str, layer: str, z: int, x: int, y: int, 
                          start_date: Optional[str] = None, end_date: Optional[str] = None) -> bytes:
    """
    Generate a GEE tile for the given parameters with caching and bbox validation
    """
    try:
        # Create cache key for this tile
        cache_key = f"tile_cache:{project_id}:{layer}:{z}:{x}:{y}"
        
        # Check if tile is already cached
        cached_tile = redis_client.get(cache_key)
        if cached_tile:
            logger.info(f"Returning cached tile for {project_id}:{layer}:{z}:{x}:{y}")
            return cached_tile
        
        logger.info(f"Generating tile for project={project_id}, layer={layer}, z={z}, x={x}, y={y}")
        
        # Try to get from registered catalogs first (for dynamic layers with fresh Map IDs)
        catalog_keys = redis_client.keys("catalog:*")
        
        for catalog_key in catalog_keys:
            catalog_data = redis_client.get(catalog_key)
            if catalog_data:
                catalog_info = json.loads(catalog_data)
                project_id = catalog_info.get('project_id', 'unknown')
                layers_info = catalog_info.get('layers', {})
                
                # Check if this layer belongs to this project
                # Clean the layer name for comparison (same cleaning as in WMTS capabilities)
                import re
                clean_layer_name = re.sub(r'[^a-zA-Z0-9_]', '_', layer)
                clean_layer_name = re.sub(r'_+', '_', clean_layer_name)
                clean_layer_name = clean_layer_name.strip('_')
                
                # Find matching layer by comparing cleaned names
                matching_layer_name = None
                for stored_layer_name in layers_info.keys():
                    stored_clean_name = re.sub(r'[^a-zA-Z0-9_]', '_', stored_layer_name)
                    stored_clean_name = re.sub(r'_+', '_', stored_clean_name)
                    stored_clean_name = stored_clean_name.strip('_')
                    
                    # Multiple matching strategies for robustness
                    if (clean_layer_name == stored_clean_name or 
                        clean_layer_name in stored_clean_name or 
                        stored_clean_name in clean_layer_name or
                        layer == stored_layer_name):
                        matching_layer_name = stored_layer_name
                        logger.info(f"Found layer match: '{layer}' -> '{stored_layer_name}' (cleaned: '{clean_layer_name}' -> '{stored_clean_name}')")
                        break
                
                if matching_layer_name:
                    layer_info = layers_info[matching_layer_name]
                    tile_url = layer_info.get('tile_url', '')
                    
                    if tile_url:
                        # Replace placeholders in the GEE tile URL
                        gee_tile_url = tile_url.replace('{z}', str(z)).replace('{x}', str(x)).replace('{y}', str(y))
                        
                        try:
                            # Fetch the actual GEE tile
                            import httpx
                            async with httpx.AsyncClient() as client:
                                response = await client.get(gee_tile_url, timeout=30.0)
                                if response.status_code == 200:
                                    logger.info(f"Successfully fetched GEE tile from: {gee_tile_url}")
                                    tile_content = response.content
                                    
                                    # Detect image format from content
                                    if tile_content.startswith(b'\xff\xd8\xff'):
                                        content_type = "image/jpeg"
                                    elif tile_content.startswith(b'\x89PNG'):
                                        content_type = "image/png"
                                    elif tile_content.startswith(b'GIF'):
                                        content_type = "image/gif"
                                    else:
                                        content_type = "image/png"  # Default fallback
                                    
                                    # Cache the tile for 1 hour (3600 seconds)
                                    redis_client.setex(cache_key, 3600, tile_content)
                                    logger.info(f"Cached tile: {cache_key} (format: {content_type})")
                                    
                                    return tile_content, content_type
                                else:
                                    logger.warning(f"GEE tile request failed: {response.status_code}")
                        except Exception as e:
                            logger.warning(f"Error fetching GEE tile: {e}")
        
        # Fallback: return a styled tile based on layer type
        logger.warning(f"No GEE tile found for layer: {layer}, using intelligent fallback")
        
        # Intelligent fallback based on layer name patterns
        layer_lower = layer.lower()
        
        if any(keyword in layer_lower for keyword in ['ndvi', 'vegetation', 'green']):
            # Vegetation indices: Green gradient
            return create_gradient_tile("ndvi"), "image/png"
        elif any(keyword in layer_lower for keyword in ['evi', 'enhanced']):
            # Enhanced vegetation: Dark green gradient
            return create_gradient_tile("evi"), "image/png"
        elif any(keyword in layer_lower for keyword in ['ndwi', 'water', 'moisture']):
            # Water indices: Blue gradient
            return create_gradient_tile("ndwi"), "image/png"
        elif any(keyword in layer_lower for keyword in ['false', 'nir', 'infrared']):
            # False color/NIR: NIR-Red-Green gradient
            return create_gradient_tile("false_color"), "image/png"
        elif any(keyword in layer_lower for keyword in ['true', 'rgb', 'natural', 'color']):
            # True color/natural: Natural RGB gradient
            return create_gradient_tile("true_color"), "image/png"
        elif any(keyword in layer_lower for keyword in ['forest', 'fcd', 'tree']):
            # Forest/vegetation: Green gradient
            return create_gradient_tile("ndvi"), "image/png"
        elif any(keyword in layer_lower for keyword in ['mosaic', 'composite', 'sentinel', 'landsat']):
            # Satellite imagery: Natural colors
            return create_gradient_tile("true_color"), "image/png"
        else:
            # Default: Natural looking tile for unknown types
            logger.info(f"Using default natural color fallback for layer: {layer}")
            return create_gradient_tile("true_color"), "image/png"
        
    except Exception as e:
        logger.error(f"Error in generate_gee_tile: {e}")
        # Return a gray tile on error (not transparent to avoid ORB blocking)
        return create_colored_tile(128, 128, 128, 255), "image/png"  # Gray

def create_gradient_tile(layer_type: str) -> bytes:
    """
    Create a realistic-looking gradient tile that mimics satellite imagery
    """
    try:
        from PIL import Image
        import io
        import random
        import math
        
        # Create a 256x256 image
        img = Image.new('RGBA', (256, 256), (0, 0, 0, 0))
        pixels = img.load()
        
        # Set random seed based on layer type for consistency
        random.seed(hash(layer_type) % 2**32)
        
        if layer_type == "ndvi":
            # NDVI: Green gradient with vegetation patterns
            for y in range(256):
                for x in range(256):
                    # Create a gradient with some noise
                    base_green = int(50 + (y / 256) * 150 + random.randint(-20, 20))
                    base_green = max(0, min(255, base_green))
                    pixels[x, y] = (0, base_green, 0, 255)
                    
        elif layer_type == "evi":
            # EVI: Darker green gradient
            for y in range(256):
                for x in range(256):
                    base_green = int(30 + (y / 256) * 120 + random.randint(-15, 15))
                    base_green = max(0, min(255, base_green))
                    pixels[x, y] = (0, base_green, 0, 255)
                    
        elif layer_type == "ndwi":
            # NDWI: Blue gradient for water
            for y in range(256):
                for x in range(256):
                    base_blue = int(50 + (x / 256) * 150 + random.randint(-20, 20))
                    base_blue = max(0, min(255, base_blue))
                    pixels[x, y] = (0, 0, base_blue, 255)
                    
        elif layer_type == "true_color":
            # True Color: Natural RGB gradient
            for y in range(256):
                for x in range(256):
                    # Create natural-looking colors
                    r = int(80 + (x / 256) * 100 + random.randint(-30, 30))
                    g = int(100 + (y / 256) * 80 + random.randint(-25, 25))
                    b = int(60 + ((x + y) / 512) * 60 + random.randint(-20, 20))
                    r = max(0, min(255, r))
                    g = max(0, min(255, g))
                    b = max(0, min(255, b))
                    pixels[x, y] = (r, g, b, 255)
                    
        elif layer_type == "false_color":
            # False Color: NIR-Red-Green (vegetation appears red)
            for y in range(256):
                for x in range(256):
                    # Vegetation appears red in false color
                    r = int(100 + (y / 256) * 120 + random.randint(-25, 25))
                    g = int(60 + (x / 256) * 80 + random.randint(-20, 20))
                    b = int(40 + ((x + y) / 512) * 40 + random.randint(-15, 15))
                    r = max(0, min(255, r))
                    g = max(0, min(255, g))
                    b = max(0, min(255, b))
                    pixels[x, y] = (r, g, b, 255)
        
        # Save to bytes
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        return img_bytes.getvalue()
        
    except ImportError:
        # Fallback to simple colored tile if PIL not available
        if layer_type == "ndvi":
            return create_colored_tile(0, 150, 0, 255)
        elif layer_type == "evi":
            return create_colored_tile(0, 100, 0, 255)
        elif layer_type == "ndwi":
            return create_colored_tile(0, 0, 150, 255)
        elif layer_type == "true_color":
            return create_colored_tile(100, 120, 80, 255)
        elif layer_type == "false_color":
            return create_colored_tile(150, 100, 50, 255)
        else:
            return create_colored_tile(128, 128, 128, 255)

def create_colored_tile(r: int, g: int, b: int, a: int) -> bytes:
    """
    Create a simple colored PNG tile using PIL
    """
    try:
        from PIL import Image
        import io
        
        # Create a 256x256 image with the specified color
        img = Image.new('RGBA', (256, 256), (r, g, b, a))
        
        # Save to bytes
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        return img_bytes.getvalue()
        
    except ImportError:
        # Fallback: create a simple colored tile without PIL
        import struct
        
        # PNG signature
        png_signature = b'\x89PNG\r\n\x1a\n'
        
        # IHDR chunk (256x256, 8-bit RGBA)
        ihdr_data = struct.pack('>IIBBBBB', 256, 256, 8, 6, 0, 0, 0)
        ihdr_crc = struct.pack('>I', 0x0a1a0a0d)
        ihdr_chunk = b'IHDR' + ihdr_data + ihdr_crc
        
        # Create a simple solid color tile
        # This is a minimal implementation - for production use PIL
        color_data = bytes([r, g, b, a] * (256 * 256))
        
        # Compress the data (simplified)
        import zlib
        compressed_data = zlib.compress(color_data)
        
        # IDAT chunk
        idat_crc = struct.pack('>I', zlib.crc32(b'IDAT' + compressed_data) & 0xffffffff)
        idat_chunk = b'IDAT' + compressed_data + idat_crc
        
        # IEND chunk
        iend_chunk = b'IEND\xaeB`\x82'
        
        return png_signature + ihdr_chunk + idat_chunk + iend_chunk

# Improved WMTS functions with Y-coordinate flipping fix
async def wmts_get_tile_improved(layer: str, tilematrixset: str, tilematrix: str, tilerow: str, tilecol: str, format: str):
    """Improved WMTS GetTile endpoint with conditional Y flipping"""
    try:
        z = int(tilematrix)
        y = int(tilerow)
        x = int(tilecol)

        # Decide whether to flip Y based on TileMatrixSet
        # GoogleMapsCompatible uses XYZ addressing → DO NOT FLIP
        # Flip only for classic TMS-style sets (not used here)
        if (tilematrixset or "").lower() == "googlemapscompatible":
            y_for_backend = y
        else:
            y_for_backend = (2 ** z - 1) - y

        # Extract project_id and layer_name from layer identifier
        # Layer format: project_id_YYYYMMDD_HHMMSS_layer_name
        # We need to find the project ID by checking against stored projects
        project_id = None
        layer_name = None
        
        # Try to find matching project by checking if layer starts with any known project ID
        catalog_keys = redis_client.keys("catalog:*")
        for catalog_key in catalog_keys:
            catalog_data = redis_client.get(catalog_key)
            if catalog_data:
                catalog_info = json.loads(catalog_data)
                catalog_project_id = catalog_info.get('project_id', '')
                if layer.startswith(f"{catalog_project_id}_"):
                    project_id = catalog_project_id
                    layer_name = layer.replace(f"{catalog_project_id}_", "")
                    break
        
        # Fallback: if no project found, try old logic
        if not project_id and "_" in layer:
            parts = layer.split("_")
            if len(parts) >= 3 and f"{parts[-2]}_{parts[-1]}" in ["true_color", "false_color"]:
                layer_name = f"{parts[-2]}_{parts[-1]}"
                project_id = "_".join(parts[:-2])
            elif len(parts) >= 2 and parts[-1] in ["ndvi", "evi", "ndwi"]:
                layer_name = parts[-1]
                project_id = "_".join(parts[:-1])
            else:
                layer_name = parts[-1]
                project_id = "_".join(parts[:-1])
        elif not project_id:
            project_id = "gee"
            layer_name = layer

        # Generate tile using chosen Y
        tile_result = await generate_gee_tile(project_id, layer_name, z, x, y_for_backend)

        if isinstance(tile_result, tuple):
            tile_data, content_type = tile_result
        else:
            tile_data, content_type = tile_result, "image/png"

        return Response(
            content=tile_data,
            media_type=content_type,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, HEAD, OPTIONS",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Allow-Credentials": "true",
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
                "Cross-Origin-Resource-Policy": "cross-origin"
            }
        )
    except Exception as e:
        logger.error(f"Error generating improved WMTS tile: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def calculate_tile_matrix_limits(bbox, zoom_level):
    """
    Calculate TileMatrixSetLimits for a given bounding box and zoom level.

    Args:
        bbox: Dictionary with minx, miny, maxx, maxy in WGS84
        zoom_level: Integer zoom level (0-15)

    Returns:
        Dictionary with MinTileRow, MaxTileRow, MinTileCol, MaxTileCol
    """
    import math

    # Web Mercator constants
    EARTH_RADIUS = 6378137
    TILE_SIZE = 256
    ORIGIN_SHIFT = 2 * math.pi * EARTH_RADIUS / 2

    def lat_lon_to_meters(lat, lon):
        """Convert lat/lon to Web Mercator meters"""
        # Clamp latitude to valid range to prevent math domain errors
        lat = max(-85.0511, min(85.0511, lat))
        mx = lon * ORIGIN_SHIFT / 180.0
        my = math.log(math.tan((90 + lat) * math.pi / 360.0)) / (math.pi / 180.0)
        my = my * ORIGIN_SHIFT / 180.0
        return mx, my

    def meters_to_tile(mx, my, zoom):
        """Convert meters to tile coordinates"""
        tile_x = int(math.floor((mx + ORIGIN_SHIFT) / (TILE_SIZE * 2 ** (15 - zoom))))
        tile_y = int(math.floor((ORIGIN_SHIFT - my) / (TILE_SIZE * 2 ** (15 - zoom))))
        return tile_x, tile_y

    # Convert bbox corners to Web Mercator meters
    min_mx, min_my = lat_lon_to_meters(bbox['miny'], bbox['minx'])
    max_mx, max_my = lat_lon_to_meters(bbox['maxy'], bbox['maxx'])

    # Convert to tile coordinates
    min_tile_x, min_tile_y = meters_to_tile(min_mx, min_my, zoom_level)
    max_tile_x, max_tile_y = meters_to_tile(max_mx, max_my, zoom_level)

    return {
        'MinTileRow': min_tile_y,
        'MaxTileRow': max_tile_y,
        'MinTileCol': min_tile_x,
        'MaxTileCol': max_tile_x
    }

def generate_wmts_capabilities_improved():
    """Generate dynamic WMTS Capabilities XML based on latest project in Redis"""
    import re
    try:
        # Get the latest project from Redis
        catalog_keys = redis_client.keys("catalog:*")
        if not catalog_keys:
            return generate_wmts_capabilities_empty()

        # Get the most recent catalog
        latest_catalog = None
        latest_timestamp = ""

        for key in catalog_keys:
            catalog_data = redis_client.get(key)
            if catalog_data:
                catalog_info = json.loads(catalog_data)
                timestamp = catalog_info.get('timestamp', '')
                if timestamp > latest_timestamp:
                    latest_timestamp = timestamp
                    latest_catalog = catalog_info

        if not latest_catalog:
            return generate_wmts_capabilities_empty()

        project_id = latest_catalog.get('project_id', 'unknown')
        project_name = latest_catalog.get('project_name', 'GEE Analysis')
        layers = latest_catalog.get('layers', {})

        logger.info(f"Generating WMTS capabilities for project: {project_id} with {len(layers)} layers")

        # Get AOI info for dynamic TileMatrixSetLimits calculation
        aoi_info = latest_catalog.get('analysis_info', {}).get('aoi', {})
        bbox = aoi_info.get('bbox', None)

        # Generate dynamic layers XML
        layers_xml = ""
        for layer_name, layer_info in layers.items():
            layer_title = layer_info.get('name', layer_name.replace('_', ' ').title())

            # Clean layer name for identifier (remove spaces, hyphens, special chars)
            clean_layer_name = re.sub(r'[^a-zA-Z0-9_]', '_', layer_name)
            clean_layer_name = re.sub(r'_+', '_', clean_layer_name)  # Remove multiple underscores
            clean_layer_name = clean_layer_name.strip('_')  # Remove leading/trailing underscores

            layer_identifier = f"{project_id}_{clean_layer_name}"

            # Get AOI info for bounding box
            aoi_info = latest_catalog.get('analysis_info', {}).get('aoi', {})
            layer_bbox = aoi_info.get('bbox', None)

            # Check if bbox is valid
            if not layer_bbox:
                logger.error("No bbox data available - skipping layer")
                continue

            # Calculate Web Mercator bounding box
            import math
            EARTH_RADIUS = 6378137
            ORIGIN_SHIFT = 2 * math.pi * EARTH_RADIUS / 2

            def lat_lon_to_meters(lat, lon):
                # Clamp latitude to valid range to prevent math domain errors
                lat = max(-85.0511, min(85.0511, lat))
                mx = lon * ORIGIN_SHIFT / 180.0
                my = math.log(math.tan((90 + lat) * math.pi / 360.0)) / (math.pi / 180.0)
                my = my * ORIGIN_SHIFT / 180.0
                return mx, my

            min_mx, min_my = lat_lon_to_meters(layer_bbox['miny'], layer_bbox['minx'])
            max_mx, max_my = lat_lon_to_meters(layer_bbox['maxy'], layer_bbox['maxx'])

            # Generate dynamic TileMatrixSetLimits for this AOI
            tile_limits_xml = ""
            for zoom in range(16):  # 0 to 15
                limits = calculate_tile_matrix_limits(layer_bbox, zoom)
                tile_limits_xml += f"""
                    <TileMatrixLimits>
                        <TileMatrix>{zoom}</TileMatrix>
                        <MinTileRow>{limits['MinTileRow']}</MinTileRow>
                        <MaxTileRow>{limits['MaxTileRow']}</MaxTileRow>
                        <MinTileCol>{limits['MinTileCol']}</MinTileCol>
                        <MaxTileCol>{limits['MaxTileCol']}</MaxTileCol>
                    </TileMatrixLimits>"""

            # Generate dynamic layer XML for each layer
            layers_xml += f"""
        <Layer>
            <ows:Title>GEE - {layer_title}</ows:Title>
            <ows:Identifier>{layer_identifier}</ows:Identifier>
            <ows:WGS84BoundingBox>
                <ows:LowerCorner>{layer_bbox['minx']} {layer_bbox['miny']}</ows:LowerCorner>
                <ows:UpperCorner>{layer_bbox['maxx']} {layer_bbox['maxy']}</ows:UpperCorner>
            </ows:WGS84BoundingBox>
            <BoundingBox crs="EPSG:3857">
                <ows:LowerCorner>{min_mx} {min_my}</ows:LowerCorner>
                <ows:UpperCorner>{max_mx} {max_my}</ows:UpperCorner>
            </BoundingBox>
            <Style isDefault="true">
                <ows:Identifier>default</ows:Identifier>
            </Style>
            <Format>image/png</Format>
            <TileMatrixSetLink>
                <TileMatrixSet>GoogleMapsCompatible</TileMatrixSet>
                <TileMatrixSetLimits>{tile_limits_xml}
                </TileMatrixSetLimits>
            </TileMatrixSetLink>
            <ResourceURL format="image/png" 
                resourceType="tile" 
                template="http://localhost:8001/wmts?service=WMTS&amp;request=GetTile&amp;version=1.0.0&amp;layer={layer_identifier}&amp;tilematrixset=GoogleMapsCompatible&amp;TileMatrix={{TileMatrix}}&amp;TileRow={{TileRow}}&amp;TileCol={{TileCol}}&amp;format=image/png"/>
        </Layer>"""

        # Close the layers loop
        logger.info(f"Generated WMTS capabilities for {len(layers)} layers from project: {project_id}")
        
        # Create the complete capabilities XML
        capabilities_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Capabilities version="1.0.0"
              xmlns="http://www.opengis.net/wmts/1.0"
              xmlns:ows="http://www.opengis.net/ows/1.1"
              xmlns:xlink="http://www.w3.org/1999/xlink"
              xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
              xsi:schemaLocation="http://www.opengis.net/wmts/1.0 http://schemas.opengis.net/wmts/1.0/wmtsGetCapabilities_response.xsd">
    <ows:ServiceIdentification>
        <ows:Title>GEE Dynamic WMTS Service</ows:Title>
        <ows:ServiceType>OGC WMTS</ows:ServiceType>
        <ows:ServiceTypeVersion>1.0.0</ows:ServiceTypeVersion>
    </ows:ServiceIdentification>
    <ows:OperationsMetadata>
        <ows:Operation name="GetCapabilities">
            <ows:DCP>
                <ows:HTTP>
                    <ows:Get xlink:href="http://localhost:8001/wmts"/>
                </ows:HTTP>
            </ows:DCP>
        </ows:Operation>
        <ows:Operation name="GetTile">
            <ows:DCP>
                <ows:HTTP>
                    <ows:Get xlink:href="http://localhost:8001/wmts"/>
                </ows:HTTP>
            </ows:DCP>
        </ows:Operation>
    </ows:OperationsMetadata>
    <Contents>
        {layers_xml}
        <TileMatrixSet>
            <ows:Identifier>GoogleMapsCompatible</ows:Identifier>
            <ows:SupportedCRS>EPSG:3857</ows:SupportedCRS>
            <TileMatrix>
                <ows:Identifier>0</ows:Identifier>
                <ScaleDenominator>559082264.0287178</ScaleDenominator>
                <TopLeftCorner>-20037508.342789244 20037508.342789244</TopLeftCorner>
                <TileWidth>256</TileWidth>
                <TileHeight>256</TileHeight>
                <MatrixWidth>1</MatrixWidth>
                <MatrixHeight>1</MatrixHeight>
            </TileMatrix>
            <TileMatrix>
                <ows:Identifier>1</ows:Identifier>
                <ScaleDenominator>279541132.0143589</ScaleDenominator>
                <TopLeftCorner>-20037508.342789244 20037508.342789244</TopLeftCorner>
                <TileWidth>256</TileWidth>
                <TileHeight>256</TileHeight>
                <MatrixWidth>2</MatrixWidth>
                <MatrixHeight>2</MatrixHeight>
            </TileMatrix>
            <TileMatrix>
                <ows:Identifier>2</ows:Identifier>
                <ScaleDenominator>139770566.00717944</ScaleDenominator>
                <TopLeftCorner>-20037508.342789244 20037508.342789244</TopLeftCorner>
                <TileWidth>256</TileWidth>
                <TileHeight>256</TileHeight>
                <MatrixWidth>4</MatrixWidth>
                <MatrixHeight>4</MatrixHeight>
            </TileMatrix>
            <TileMatrix>
                <ows:Identifier>3</ows:Identifier>
                <ScaleDenominator>69885283.00358972</ScaleDenominator>
                <TopLeftCorner>-20037508.342789244 20037508.342789244</TopLeftCorner>
                <TileWidth>256</TileWidth>
                <TileHeight>256</TileHeight>
                <MatrixWidth>8</MatrixWidth>
                <MatrixHeight>8</MatrixHeight>
            </TileMatrix>
            <TileMatrix>
                <ows:Identifier>4</ows:Identifier>
                <ScaleDenominator>34942641.50179486</ScaleDenominator>
                <TopLeftCorner>-20037508.342789244 20037508.342789244</TopLeftCorner>
                <TileWidth>256</TileWidth>
                <TileHeight>256</TileHeight>
                <MatrixWidth>16</MatrixWidth>
                <MatrixHeight>16</MatrixHeight>
            </TileMatrix>
            <TileMatrix>
                <ows:Identifier>5</ows:Identifier>
                <ScaleDenominator>17471320.75089743</ScaleDenominator>
                <TopLeftCorner>-20037508.342789244 20037508.342789244</TopLeftCorner>
                <TileWidth>256</TileWidth>
                <TileHeight>256</TileHeight>
                <MatrixWidth>32</MatrixWidth>
                <MatrixHeight>32</MatrixHeight>
            </TileMatrix>
            <TileMatrix>
                <ows:Identifier>6</ows:Identifier>
                <ScaleDenominator>8735660.375448715</ScaleDenominator>
                <TopLeftCorner>-20037508.342789244 20037508.342789244</TopLeftCorner>
                <TileWidth>256</TileWidth>
                <TileHeight>256</TileHeight>
                <MatrixWidth>64</MatrixWidth>
                <MatrixHeight>64</MatrixHeight>
            </TileMatrix>
            <TileMatrix>
                <ows:Identifier>7</ows:Identifier>
                <ScaleDenominator>4367830.1877243575</ScaleDenominator>
                <TopLeftCorner>-20037508.342789244 20037508.342789244</TopLeftCorner>
                <TileWidth>256</TileWidth>
                <TileHeight>256</TileHeight>
                <MatrixWidth>128</MatrixWidth>
                <MatrixHeight>128</MatrixHeight>
            </TileMatrix>
            <TileMatrix>
                <ows:Identifier>8</ows:Identifier>
                <ScaleDenominator>2183915.0938621787</ScaleDenominator>
                <TopLeftCorner>-20037508.342789244 20037508.342789244</TopLeftCorner>
                <TileWidth>256</TileWidth>
                <TileHeight>256</TileHeight>
                <MatrixWidth>256</MatrixWidth>
                <MatrixHeight>256</MatrixHeight>
            </TileMatrix>
            <TileMatrix>
                <ows:Identifier>9</ows:Identifier>
                <ScaleDenominator>1091957.5469310894</ScaleDenominator>
                <TopLeftCorner>-20037508.342789244 20037508.342789244</TopLeftCorner>
                <TileWidth>256</TileWidth>
                <TileHeight>256</TileHeight>
                <MatrixWidth>512</MatrixWidth>
                <MatrixHeight>512</MatrixHeight>
            </TileMatrix>
            <TileMatrix>
                <ows:Identifier>10</ows:Identifier>
                <ScaleDenominator>545978.7734655447</ScaleDenominator>
                <TopLeftCorner>-20037508.342789244 20037508.342789244</TopLeftCorner>
                <TileWidth>256</TileWidth>
                <TileHeight>256</TileHeight>
                <MatrixWidth>1024</MatrixWidth>
                <MatrixHeight>1024</MatrixHeight>
            </TileMatrix>
        </TileMatrixSet>
    </Contents>
</Capabilities>"""

        capabilities_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Capabilities version="1.0.0"
              xmlns="http://www.opengis.net/wmts/1.0"
              xmlns:ows="http://www.opengis.net/ows/1.1"
              xmlns:xlink="http://www.w3.org/1999/xlink"
              xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
              xsi:schemaLocation="http://www.opengis.net/wmts/1.0 http://schemas.opengis.net/wmts/1.0/wmtsGetCapabilities_response.xsd">
    <ows:ServiceIdentification>
        <ows:Title>GEE Dynamic WMTS Service</ows:Title>
        <ows:ServiceType>OGC WMTS</ows:ServiceType>
        <ows:ServiceTypeVersion>1.0.0</ows:ServiceTypeVersion>
    </ows:ServiceIdentification>
    <ows:OperationsMetadata>
        <ows:Operation name="GetCapabilities">
            <ows:DCP>
                <ows:HTTP>
                    <ows:Get xlink:href="http://localhost:8001/wmts"/>
                </ows:HTTP>
            </ows:DCP>
        </ows:Operation>
        <ows:Operation name="GetTile">
            <ows:DCP>
                <ows:HTTP>
                    <ows:Get xlink:href="http://localhost:8001/wmts"/>
                </ows:HTTP>
            </ows:DCP>
        </ows:Operation>
    </ows:OperationsMetadata>
    <Contents>
        {layers_xml}
        <TileMatrixSet>
            <ows:Identifier>GoogleMapsCompatible</ows:Identifier>
            <ows:SupportedCRS>EPSG:3857</ows:SupportedCRS>
            <TileMatrix>
                <ows:Identifier>0</ows:Identifier>
                <ScaleDenominator>559082264.0287178</ScaleDenominator>
                <TopLeftCorner>-20037508.342789244 20037508.342789244</TopLeftCorner>
                <TileWidth>256</TileWidth>
                <TileHeight>256</TileHeight>
                <MatrixWidth>1</MatrixWidth>
                <MatrixHeight>1</MatrixHeight>
            </TileMatrix>
            <TileMatrix>
                <ows:Identifier>1</ows:Identifier>
                <ScaleDenominator>279541132.0143589</ScaleDenominator>
                <TopLeftCorner>-20037508.342789244 20037508.342789244</TopLeftCorner>
                <TileWidth>256</TileWidth>
                <TileHeight>256</TileHeight>
                <MatrixWidth>2</MatrixWidth>
                <MatrixHeight>2</MatrixHeight>
            </TileMatrix>
            <TileMatrix>
                <ows:Identifier>2</ows:Identifier>
                <ScaleDenominator>139770566.00717944</ScaleDenominator>
                <TopLeftCorner>-20037508.342789244 20037508.342789244</TopLeftCorner>
                <TileWidth>256</TileWidth>
                <TileHeight>256</TileHeight>
                <MatrixWidth>4</MatrixWidth>
                <MatrixHeight>4</MatrixHeight>
            </TileMatrix>
            <TileMatrix>
                <ows:Identifier>3</ows:Identifier>
                <ScaleDenominator>69885283.00358972</ScaleDenominator>
                <TopLeftCorner>-20037508.342789244 20037508.342789244</TopLeftCorner>
                <TileWidth>256</TileWidth>
                <TileHeight>256</TileHeight>
                <MatrixWidth>8</MatrixWidth>
                <MatrixHeight>8</MatrixHeight>
            </TileMatrix>
            <TileMatrix>
                <ows:Identifier>4</ows:Identifier>
                <ScaleDenominator>34942641.50179486</ScaleDenominator>
                <TopLeftCorner>-20037508.342789244 20037508.342789244</TopLeftCorner>
                <TileWidth>256</TileWidth>
                <TileHeight>256</TileHeight>
                <MatrixWidth>16</MatrixWidth>
                <MatrixHeight>16</MatrixHeight>
            </TileMatrix>
            <TileMatrix>
                <ows:Identifier>5</ows:Identifier>
                <ScaleDenominator>17471320.75089743</ScaleDenominator>
                <TopLeftCorner>-20037508.342789244 20037508.342789244</TopLeftCorner>
                <TileWidth>256</TileWidth>
                <TileHeight>256</TileHeight>
                <MatrixWidth>32</MatrixWidth>
                <MatrixHeight>32</MatrixHeight>
            </TileMatrix>
            <TileMatrix>
                <ows:Identifier>6</ows:Identifier>
                <ScaleDenominator>8735660.375448715</ScaleDenominator>
                <TopLeftCorner>-20037508.342789244 20037508.342789244</TopLeftCorner>
                <TileWidth>256</TileWidth>
                <TileHeight>256</TileHeight>
                <MatrixWidth>64</MatrixWidth>
                <MatrixHeight>64</MatrixHeight>
            </TileMatrix>
            <TileMatrix>
                <ows:Identifier>7</ows:Identifier>
                <ScaleDenominator>4367830.1877243575</ScaleDenominator>
                <TopLeftCorner>-20037508.342789244 20037508.342789244</TopLeftCorner>
                <TileWidth>256</TileWidth>
                <TileHeight>256</TileHeight>
                <MatrixWidth>128</MatrixWidth>
                <MatrixHeight>128</MatrixHeight>
            </TileMatrix>
            <TileMatrix>
                <ows:Identifier>8</ows:Identifier>
                <ScaleDenominator>2183915.0938621787</ScaleDenominator>
                <TopLeftCorner>-20037508.342789244 20037508.342789244</TopLeftCorner>
                <TileWidth>256</TileWidth>
                <TileHeight>256</TileHeight>
                <MatrixWidth>256</MatrixWidth>
                <MatrixHeight>256</MatrixHeight>
            </TileMatrix>
            <TileMatrix>
                <ows:Identifier>9</ows:Identifier>
                <ScaleDenominator>1091957.5469310894</ScaleDenominator>
                <TopLeftCorner>-20037508.342789244 20037508.342789244</TopLeftCorner>
                <TileWidth>256</TileWidth>
                <TileHeight>256</TileHeight>
                <MatrixWidth>512</MatrixWidth>
                <MatrixHeight>512</MatrixHeight>
            </TileMatrix>
            <TileMatrix>
                <ows:Identifier>10</ows:Identifier>
                <ScaleDenominator>545978.7734655447</ScaleDenominator>
                <TopLeftCorner>-20037508.342789244 20037508.342789244</TopLeftCorner>
                <TileWidth>256</TileWidth>
                <TileHeight>256</TileHeight>
                <MatrixWidth>1024</MatrixWidth>
                <MatrixHeight>1024</MatrixHeight>
            </TileMatrix>
            <TileMatrix>
                <ows:Identifier>11</ows:Identifier>
                <ScaleDenominator>272989.38673277235</ScaleDenominator>
                <TopLeftCorner>-20037508.342789244 20037508.342789244</TopLeftCorner>
                <TileWidth>256</TileWidth>
                <TileHeight>256</TileHeight>
                <MatrixWidth>2048</MatrixWidth>
                <MatrixHeight>2048</MatrixHeight>
            </TileMatrix>
            <TileMatrix>
                <ows:Identifier>12</ows:Identifier>
                <ScaleDenominator>136494.69336638618</ScaleDenominator>
                <TopLeftCorner>-20037508.342789244 20037508.342789244</TopLeftCorner>
                <TileWidth>256</TileWidth>
                <TileHeight>256</TileHeight>
                <MatrixWidth>4096</MatrixWidth>
                <MatrixHeight>4096</MatrixHeight>
            </TileMatrix>
            <TileMatrix>
                <ows:Identifier>13</ows:Identifier>
                <ScaleDenominator>68247.34668319309</ScaleDenominator>
                <TopLeftCorner>-20037508.342789244 20037508.342789244</TopLeftCorner>
                <TileWidth>256</TileWidth>
                <TileHeight>256</TileHeight>
                <MatrixWidth>8192</MatrixWidth>
                <MatrixHeight>8192</MatrixHeight>
            </TileMatrix>
            <TileMatrix>
                <ows:Identifier>14</ows:Identifier>
                <ScaleDenominator>34123.67334159654</ScaleDenominator>
                <TopLeftCorner>-20037508.342789244 20037508.342789244</TopLeftCorner>
                <TileWidth>256</TileWidth>
                <TileHeight>256</TileHeight>
                <MatrixWidth>16384</MatrixWidth>
                <MatrixHeight>16384</MatrixHeight>
            </TileMatrix>
            <TileMatrix>
                <ows:Identifier>15</ows:Identifier>
                <ScaleDenominator>17061.83667079827</ScaleDenominator>
                <TopLeftCorner>-20037508.342789244 20037508.342789244</TopLeftCorner>
                <TileWidth>256</TileWidth>
                <TileHeight>256</TileHeight>
                <MatrixWidth>32768</MatrixWidth>
                <MatrixHeight>32768</MatrixHeight>
            </TileMatrix>
        </TileMatrixSet>
    </Contents>
</Capabilities>"""

        return capabilities_xml
    except Exception as e:
        logger.error(f"Error generating improved WMTS capabilities: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def generate_wmts_capabilities_empty():
    """Generate empty WMTS Capabilities XML when no layers are available"""
    return """<?xml version="1.0" encoding="UTF-8"?>
<Capabilities version="1.0.0"
              xmlns="http://www.opengis.net/wmts/1.0"
              xmlns:ows="http://www.opengis.net/ows/1.1"
              xmlns:xlink="http://www.w3.org/1999/xlink"
              xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
              xsi:schemaLocation="http://www.opengis.net/wmts/1.0 http://schemas.opengis.net/wmts/1.0/wmtsGetCapabilities_response.xsd">
    <ows:ServiceIdentification>
        <ows:Title>GEE Dynamic WMTS Service</ows:Title>
        <ows:ServiceType>OGC WMTS</ows:ServiceType>
        <ows:ServiceTypeVersion>1.0.0</ows:ServiceTypeVersion>
    </ows:ServiceIdentification>
    <ows:OperationsMetadata>
        <ows:Operation name="GetCapabilities">
            <ows:DCP>
                <ows:HTTP>
                    <ows:Get xlink:href="http://localhost:8001/wmts"/>
                </ows:HTTP>
            </ows:DCP>
        </ows:Operation>
        <ows:Operation name="GetTile">
            <ows:DCP>
                <ows:HTTP>
                    <ows:Get xlink:href="http://localhost:8001/wmts"/>
                </ows:HTTP>
            </ows:DCP>
        </ows:Operation>
    </ows:OperationsMetadata>
    <Contents>
        <TileMatrixSet>
            <ows:Identifier>GoogleMapsCompatible</ows:Identifier>
            <ows:SupportedCRS>EPSG:3857</ows:SupportedCRS>
        </TileMatrixSet>
    </Contents>
</Capabilities>"""

@app.post("/cache/clear")
async def clear_cache(cache_type: str = Query("all", description="Type of cache to clear: all, tiles, catalogs, projects")):
    """
    Clear Redis cache entries
    
    Args:
        cache_type: Type of cache to clear (all, tiles, catalogs, projects)
    """
    try:
        from cache_manager import CacheManager
        manager = CacheManager()
        result = manager.clear_cache(cache_type)
        
        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=result["error"])
        
        return result
        
    except Exception as e:
        logger.error(f"Error clearing cache: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Cache clearing failed: {str(e)}")

@app.get("/cache/status")
async def get_cache_status():
    """
    Get current cache status and statistics
    """
    try:
        from cache_manager import CacheManager
        manager = CacheManager()
        result = manager.get_cache_status()
        
        if result.get("status") == "error":
            raise HTTPException(status_code=500, detail=result["error"])
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting cache status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get cache status: {str(e)}")

@app.post("/cache/clear/{project_id}")
async def clear_project_cache(project_id: str):
    """
    Clear cache for a specific project
    
    Args:
        project_id: Project ID to clear cache for
    """
    try:
        from cache_manager import CacheManager
        manager = CacheManager()
        result = manager.clear_project_cache(project_id)
        
        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=result["error"])
        
        return result
        
    except Exception as e:
        logger.error(f"Error clearing project cache: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Project cache clearing failed: {str(e)}")

@app.post("/gee/process-with-cache-clear")
async def process_gee_with_cache_clear(request_data: dict):
    """
    Process GEE analysis with automatic cache clearing
    
    Args:
        request_data: Dictionary containing map_layers, project_name, aoi_info, clear_cache_first
    """
    try:
        from gee_utils import process_gee_analysis_with_cache_management
        
        map_layers = request_data.get("map_layers", {})
        project_name = request_data.get("project_name", "GEE Analysis")
        aoi_info = request_data.get("aoi_info")
        clear_cache_first = request_data.get("clear_cache_first", True)
        
        if not map_layers:
            raise HTTPException(status_code=400, detail="map_layers is required")
        
        result = process_gee_analysis_with_cache_management(
            map_layers=map_layers,
            project_name=project_name,
            aoi_info=aoi_info,
            fastapi_url=f"http://localhost:8000",
            clear_cache_first=clear_cache_first
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error processing GEE with cache clear: {str(e)}")
        raise HTTPException(status_code=500, detail=f"GEE processing failed: {str(e)}")

@app.get("/gee/comprehensive-status")
async def get_comprehensive_status():
    """
    Get comprehensive status of all services
    """
    try:
        from gee_utils import get_comprehensive_service_status
        
        result = get_comprehensive_service_status()
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting comprehensive status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")

@app.post("/gee/aoi/process")
async def process_aoi_geometry(request_data: dict):
    """
    Process AOI geometry and return comprehensive information
    
    Args:
        request_data: Dictionary containing geometry coordinates
    """
    try:
        # This endpoint would need to be implemented to work with EE geometry
        # For now, return a placeholder response
        return {
            "status": "success",
            "message": "AOI processing endpoint - requires EE geometry implementation",
            "note": "Use the osi.utils module directly for geometry processing"
        }
        
    except Exception as e:
        logger.error(f"Error processing AOI: {str(e)}")
        raise HTTPException(status_code=500, detail=f"AOI processing failed: {str(e)}")

@app.post("/wmts/update-configuration")
async def update_wmts_configuration(request_data: dict):
    """
    Update WMTS configuration for MapStore
    
    Args:
        request_data: Dictionary containing project_id, project_name, aoi_info, replace_existing
    """
    try:
        from unified_gee_interface import UnifiedGEEInterface
        
        project_id = request_data.get("project_id")
        project_name = request_data.get("project_name", "GEE Analysis")
        aoi_info = request_data.get("aoi_info")
        replace_existing = request_data.get("replace_existing", True)
        
        if not project_id:
            raise HTTPException(status_code=400, detail="project_id is required")
        
        if not aoi_info:
            raise HTTPException(status_code=400, detail="aoi_info is required")
        
        interface = UnifiedGEEInterface()
        result = interface.update_wmts_configuration(
            project_id=project_id,
            project_name=project_name,
            aoi_info=aoi_info,
            replace_existing=replace_existing
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error updating WMTS configuration: {str(e)}")
        raise HTTPException(status_code=500, detail=f"WMTS configuration update failed: {str(e)}")

@app.get("/wmts/configuration-status")
async def get_wmts_configuration_status():
    """
    Get current WMTS configuration status
    """
    try:
        from unified_gee_interface import UnifiedGEEInterface
        
        interface = UnifiedGEEInterface()
        result = interface.get_wmts_configuration_status()
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting WMTS configuration status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get WMTS configuration status: {str(e)}")

# =============================================================================
# WFS (Web Feature Service) Endpoints
# =============================================================================

@app.get("/wfs")
@app.post("/wfs")
async def wfs_service(
    service: str = Query("WFS", description="Service type"),
    version: str = Query("1.1.0", description="WFS version"),
    request: str = Query("GetCapabilities", description="Request type"),
    typename: str = Query("", description="Feature type name"),
    typeName: str = Query("", description="Feature type name (alternative parameter)"),
    featureid: str = Query("", description="Feature ID"),
    bbox: str = Query("", description="Bounding box"),
    srsname: str = Query("EPSG:4326", description="Spatial reference system"),
    outputformat: str = Query("application/json", description="Output format"),
    outputFormat: str = Query("", description="Output format (alternative parameter)"),
    maxfeatures: int = Query(1000, description="Maximum features to return"),
    startindex: int = Query(0, description="Start index for pagination"),
    request_data: dict = None
):
    """
    WFS (Web Feature Service) endpoint for serving vector data
    Following OGC WFS 1.1.0 standard
    """
    try:
        # Normalize parameter names (handle both typename/typeName and outputformat/outputFormat)
        actual_typename = typename if typename else typeName
        actual_outputformat = outputformat if outputformat else outputFormat
        
        # Validate service type
        if service.upper() != "WFS":
            raise HTTPException(status_code=400, detail="Invalid service type. Must be WFS.")
        
        if request == "GetCapabilities":
            return await wfs_get_capabilities()
        elif request == "GetFeature":
            sld = request_data.get('sld') if request_data and hasattr(request_data, 'get') else None
            return await wfs_get_feature(actual_typename, featureid, bbox, srsname, actual_outputformat, maxfeatures, startindex, sld)
        elif request == "DescribeFeatureType":
            return await wfs_describe_feature_type(actual_typename)
        elif request == "GetStyles":
            return await wfs_get_styles(actual_typename)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported request: {request}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in WFS service: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def wfs_get_capabilities():
    """
    WFS GetCapabilities response - Dynamic based on registered FeatureCollections
    """
    try:
        # Get available feature collections from GeoJSON API registry
        available_fcs = list(FC_REGISTRY.keys())
        
        if not available_fcs:
            # Return empty capabilities if no FeatureCollections are registered
            capabilities_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<wfs:WFS_Capabilities xmlns:wfs="http://www.opengis.net/wfs"
                      xmlns:ows="http://www.opengis.net/ows"
                      xmlns:gml="http://www.opengis.net/gml"
                      xmlns:xlink="http://www.w3.org/1999/xlink"
                      xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                      version="1.1.0"
                      xsi:schemaLocation="http://www.opengis.net/wfs http://schemas.opengis.net/wfs/1.1.0/wfs.xsd">
    <ows:ServiceIdentification>
        <ows:Title>GEE Feature Service</ows:Title>
        <ows:Abstract>Web Feature Service for GEE FeatureCollections</ows:Abstract>
        <ows:ServiceType>WFS</ows:ServiceType>
        <ows:ServiceTypeVersion>1.1.0</ows:ServiceTypeVersion>
    </ows:ServiceIdentification>
    <ows:OperationsMetadata>
        <ows:Operation name="GetCapabilities">
            <ows:DCP>
                <ows:HTTP>
                    <ows:Get href="http://localhost:8001/wfs?service=WFS&amp;request=GetCapabilities"/>
                </ows:HTTP>
            </ows:DCP>
        </ows:Operation>
        <ows:Operation name="GetFeature">
            <ows:DCP>
                <ows:HTTP>
                    <ows:Get href="http://localhost:8001/wfs?service=WFS&amp;request=GetFeature"/>
                </ows:HTTP>
            </ows:DCP>
        </ows:Operation>
        <ows:Operation name="DescribeFeatureType">
            <ows:DCP>
                <ows:HTTP>
                    <ows:Get href="http://localhost:8001/wfs?service=WFS&amp;request=DescribeFeatureType"/>
                </ows:HTTP>
            </ows:DCP>
        </ows:Operation>
        <ows:Operation name="GetStyles">
            <ows:DCP>
                <ows:HTTP>
                    <ows:Get href="http://localhost:8001/wfs?service=WFS&amp;request=GetStyles"/>
                </ows:HTTP>
            </ows:DCP>
        </ows:Operation>
    </ows:OperationsMetadata>
    <FeatureTypeList>
        <Operations>
            <Operation>Query</Operation>
        </Operations>
    </FeatureTypeList>
</wfs:WFS_Capabilities>'''
            
            return Response(
                content=capabilities_xml,
                media_type="application/xml",
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                    "Access-Control-Allow-Headers": "*"
                }
            )
        
        # Generate WFS capabilities XML
        capabilities_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<wfs:WFS_Capabilities xmlns:wfs="http://www.opengis.net/wfs"
                      xmlns:ows="http://www.opengis.net/ows"
                      xmlns:gml="http://www.opengis.net/gml"
                      xmlns:xlink="http://www.w3.org/1999/xlink"
                      xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                      version="1.1.0"
                      xsi:schemaLocation="http://www.opengis.net/wfs http://schemas.opengis.net/wfs/1.1.0/wfs.xsd">
    <ows:ServiceIdentification>
        <ows:Title>GEE Feature Service</ows:Title>
        <ows:Abstract>Web Feature Service for GEE FeatureCollections</ows:Abstract>
        <ows:ServiceType>WFS</ows:ServiceType>
        <ows:ServiceTypeVersion>1.1.0</ows:ServiceTypeVersion>
    </ows:ServiceIdentification>
    <ows:OperationsMetadata>
        <ows:Operation name="GetCapabilities">
            <ows:DCP>
                <ows:HTTP>
                    <ows:Get href="http://localhost:8001/wfs?service=WFS&amp;request=GetCapabilities"/>
                </ows:HTTP>
            </ows:DCP>
        </ows:Operation>
        <ows:Operation name="GetFeature">
            <ows:DCP>
                <ows:HTTP>
                    <ows:Get href="http://localhost:8001/wfs?service=WFS&amp;request=GetFeature"/>
                </ows:HTTP>
            </ows:DCP>
        </ows:Operation>
        <ows:Operation name="DescribeFeatureType">
            <ows:DCP>
                <ows:HTTP>
                    <ows:Get href="http://localhost:8001/wfs?service=WFS&amp;request=DescribeFeatureType"/>
                </ows:HTTP>
            </ows:DCP>
        </ows:Operation>
    </ows:OperationsMetadata>
    <FeatureTypeList>
        <Operations>
            <Operation>Query</Operation>
        </Operations>'''
        
        # Add feature types for each registered FeatureCollection
        for fc_name in available_fcs:
            # Get bounding box information for this FeatureCollection
            try:
                fc = FC_REGISTRY[fc_name]
                from gee_integration import get_fc_statistics
                stats = get_fc_statistics(fc)
                bbox = stats.get('bbox', None)
                
                # Generate bounding box XML if available
                bbox_xml = ""
                if bbox and all(key in bbox for key in ['minx', 'miny', 'maxx', 'maxy']):
                    bbox_xml = f'''
            <ows:WGS84BoundingBox>
                <ows:LowerCorner>{bbox['minx']} {bbox['miny']}</ows:LowerCorner>
                <ows:UpperCorner>{bbox['maxx']} {bbox['maxy']}</ows:UpperCorner>
            </ows:WGS84BoundingBox>
            <ows:BoundingBox crs="EPSG:4326">
                <ows:LowerCorner>{bbox['minx']} {bbox['miny']}</ows:LowerCorner>
                <ows:UpperCorner>{bbox['maxx']} {bbox['maxy']}</ows:UpperCorner>
            </ows:BoundingBox>'''
                else:
                    # Provide default global bounding box if no bbox available
                    bbox_xml = '''
            <ows:WGS84BoundingBox>
                <ows:LowerCorner>-180 -90</ows:LowerCorner>
                <ows:UpperCorner>180 90</ows:UpperCorner>
            </ows:WGS84BoundingBox>
            <ows:BoundingBox crs="EPSG:4326">
                <ows:LowerCorner>-180 -90</ows:LowerCorner>
                <ows:UpperCorner>180 90</ows:UpperCorner>
            </ows:BoundingBox>'''
                    
            except Exception as e:
                logger.warning(f"Could not get bbox for {fc_name}: {e}")
                # Provide default global bounding box
                bbox_xml = '''
            <ows:WGS84BoundingBox>
                <ows:LowerCorner>-180 -90</ows:LowerCorner>
                <ows:UpperCorner>180 90</ows:UpperCorner>
            </ows:WGS84BoundingBox>
            <ows:BoundingBox crs="EPSG:4326">
                <ows:LowerCorner>-180 -90</ows:LowerCorner>
                <ows:UpperCorner>180 90</ows:UpperCorner>
            </ows:BoundingBox>'''
            
            # Get additional metadata for better OGC compliance
            try:
                fc = FC_REGISTRY[fc_name]
                fc_info = fc.getInfo()
                feature_count = len(fc_info.get('features', [])) if fc_info.get('type') == 'FeatureCollection' else 1
                
                # Generate proper title and abstract
                title = fc_name.replace('_', ' ').title()
                abstract = f"FeatureCollection containing {feature_count} features from GEE analysis"
                
                # Add keywords for better discovery
                keywords = f"GEE, Earth Engine, {fc_name}, Vector, Features"
                
                # Detect CRS from actual data coordinates
                from gee_integration import detect_crs_from_data
                detected_crs = detect_crs_from_data(fc_info)
                default_srs = detected_crs.get('default', 'EPSG:4326')
                other_srs = detected_crs.get('other', ['EPSG:3857'])
                
            except Exception as e:
                logger.warning(f"Could not get metadata for {fc_name}: {e}")
                title = fc_name
                abstract = f"GEE FeatureCollection: {fc_name}"
                keywords = "GEE, Earth Engine, Vector"
                # Default to WGS84 if detection fails
                default_srs = 'EPSG:4326'
                other_srs = ['EPSG:3857']
            
            # Generate OtherSRS elements
            other_srs_xml = ""
            for srs in other_srs:
                other_srs_xml += f"            <OtherSRS>{srs}</OtherSRS>\n"
            
            capabilities_xml += f'''
        <FeatureType>
            <Name>{fc_name}</Name>
            <Title>{title}</Title>
            <Abstract>{abstract}</Abstract>
            <Keywords>{keywords}</Keywords>
            <DefaultSRS>{default_srs}</DefaultSRS>
{other_srs_xml}            <OutputFormats>
                <Format>application/json</Format>
                <Format>application/geojson</Format>
                <Format>text/xml</Format>
                <Format>application/gml+xml</Format>
                <Format>application/vnd.geo+json</Format>
            </OutputFormats>
            <DefaultStyle>
                <Name>default</Name>
                <Title>Default Style</Title>
                <Abstract>Default blue style for {fc_name}</Abstract>
                <OnlineResource xmlns:xlink="http://www.w3.org/1999/xlink" xlink:type="simple" xlink:href="http://localhost:8001/wfs?service=WFS&amp;version=1.1.0&amp;request=GetStyles&amp;typeName={fc_name}"/>
            </DefaultStyle>
            <OtherStyle>
                <Name>blue</Name>
                <Title>Blue Style</Title>
                <Abstract>Blue style for {fc_name}</Abstract>
                <OnlineResource xmlns:xlink="http://www.w3.org/1999/xlink" xlink:type="simple" xlink:href="http://localhost:8001/wfs?service=WFS&amp;version=1.1.0&amp;request=GetStyles&amp;typeName={fc_name}"/>
            </OtherStyle>
            <MetadataURL type="TC211">
                <Format>text/xml</Format>
                <OnlineResource xlink:type="simple" xlink:href="http://localhost:8001/wfs?service=WFS&amp;version=1.1.0&amp;request=DescribeFeatureType&amp;typeName={fc_name}"/>
            </MetadataURL>{bbox_xml}
        </FeatureType>'''
        
        capabilities_xml += '''
    </FeatureTypeList>
</wfs:WFS_Capabilities>'''
        
        return Response(
            content=capabilities_xml,
            media_type="application/xml",
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "*"
            }
        )
        
    except Exception as e:
        logger.error(f"Error generating WFS capabilities: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def transform_coordinates(features_list, source_srs, target_srs):
    """
    Transform coordinates from source SRS to target SRS
    Currently supports transformation from EPSG:4326 to EPSG:3857
    """
    import math

    if source_srs == 'EPSG:4326' and target_srs == 'EPSG:3857':
        # Transform from WGS84 to Web Mercator
        transformed_features = []

        for feature in features_list:
            new_feature = feature.copy()

            if 'geometry' in new_feature:
                geom = new_feature['geometry']

                if geom['type'] == 'Polygon':
                    # Transform polygon coordinates
                    new_coords = []
                    for ring in geom['coordinates']:
                        new_ring = []
                        for coord in ring:
                            lon, lat = coord[0], coord[1]
                            # Web Mercator transformation
                            x = lon * 20037508.34 / 180
                            y = math.log(math.tan((90 + lat) * math.pi / 360)) / (math.pi / 180) * 20037508.34 / 180
                            new_ring.append([x, y])
                        new_coords.append(new_ring)
                    geom['coordinates'] = new_coords

                elif geom['type'] == 'MultiPolygon':
                    # Transform MultiPolygon coordinates
                    new_coords = []
                    for polygon in geom['coordinates']:
                        new_polygon = []
                        for ring in polygon:
                            new_ring = []
                            for coord in ring:
                                lon, lat = coord[0], coord[1]
                                x = lon * 20037508.34 / 180
                                y = math.log(math.tan((90 + lat) * math.pi / 360)) / (math.pi / 180) * 20037508.34 / 180
                                new_ring.append([x, y])
                            new_polygon.append(new_ring)
                        new_coords.append(new_polygon)
                    geom['coordinates'] = new_coords

                elif geom['type'] == 'Point':
                    # Transform Point coordinates (single [x, y] pair)
                    lon, lat = geom['coordinates'][0], geom['coordinates'][1]
                    x = lon * 20037508.34 / 180
                    y = math.log(math.tan((90 + lat) * math.pi / 360)) / (math.pi / 180) * 20037508.34 / 180
                    geom['coordinates'] = [x, y]

                elif geom['type'] in ['LineString', 'MultiPoint', 'MultiLineString']:
                    # Transform other geometry types
                    new_coords = []
                    for coord in geom['coordinates']:
                        if isinstance(coord[0], list):  # Multi-coordinate geometry
                            new_ring = []
                            for c in coord:
                                lon, lat = c[0], c[1]
                                x = lon * 20037508.34 / 180
                                y = math.log(math.tan((90 + lat) * math.pi / 360)) / (math.pi / 180) * 20037508.34 / 180
                                new_ring.append([x, y])
                            new_coords.append(new_ring)
                        else:  # Single coordinate geometry
                            lon, lat = coord[0], coord[1]
                            x = lon * 20037508.34 / 180
                            y = math.log(math.tan((90 + lat) * math.pi / 360)) / (math.pi / 180) * 20037508.34 / 180
                            new_coords.append([x, y])

                    geom['coordinates'] = new_coords

                # Update geometry SRS
                geom['crs'] = {
                    "type": "name",
                    "properties": {
                        "name": f"urn:ogc:def:crs:{target_srs.replace('EPSG:', 'EPSG::')}"
                    }
                }

            transformed_features.append(new_feature)

        return transformed_features

    # For now, return original features if transformation not supported
    logger.warning(f"Coordinate transformation from {source_srs} to {target_srs} not implemented, returning original coordinates")
    return features_list

async def wfs_get_feature(typename: str, featureid: str, bbox: str, srsname: str,
                         outputformat: str, maxfeatures: int, startindex: int, sld: str = None):
    """
    WFS GetFeature response - Dynamic based on registered FeatureCollections
    """
    try:
        if not typename:
            raise HTTPException(status_code=400, detail="typename parameter is required")
        
        if typename not in FC_REGISTRY:
            raise HTTPException(status_code=404, detail=f"Feature type '{typename}' not found")
        
        # Get the FeatureCollection from GeoJSON API registry
        fc = FC_REGISTRY[typename]
        
        # Convert to list of features
        features_list = convert_fc_to_features_list(fc)
        
        # Apply filtering if needed
        if featureid:
            # Filter by specific feature ID
            features_list = [f for f in features_list if f.get('id') == featureid]
        
        if bbox:
            # Apply bounding box filter
            bbox_coords = [float(x) for x in bbox.split(',')]
            if len(bbox_coords) == 4:
                minx, miny, maxx, maxy = bbox_coords
                features_list = filter_by_bbox(features_list, minx, miny, maxx, maxy)
        
        # Apply pagination
        total_features = len(features_list)
        features_list = features_list[startindex:startindex + maxfeatures]
        
        # Format response based on output format
        if outputformat.lower() in ['application/json', 'application/geojson']:
            # Detect CRS for the response and handle SRS transformation
            try:
                fc = FC_REGISTRY[typename]
                fc_info = fc.getInfo()
                from gee_integration import detect_crs_from_data
                detected_crs = detect_crs_from_data(fc_info)
                source_srs = detected_crs.get('default', 'EPSG:4326')

                # Check if transformation is needed
                target_srs = srsname if srsname else 'EPSG:4326'
                if target_srs != source_srs:
                    # Transform coordinates from source to target SRS
                    logger.info(f"Transforming coordinates from {source_srs} to {target_srs}")
                    features_list = transform_coordinates(features_list, source_srs, target_srs)
                    response_srs = target_srs
                else:
                    response_srs = source_srs
            except Exception as e:
                logger.warning(f"Error during CRS detection/transformation: {e}")
                response_srs = 'EPSG:4326'

            # Return as GeoJSON with CRS information and styling
            geojson_response = {
                "type": "FeatureCollection",
                "features": features_list,
                "totalFeatures": total_features,
                "crs": {
                    "type": "name",
                    "properties": {
                        "name": f"urn:ogc:def:crs:{response_srs.replace('EPSG:', 'EPSG::')}"
                    }
                },
                "numberReturned": len(features_list),
                "numberMatched": total_features,
                "styles": {
                    "default": {
                        "name": "default",
                        "title": "Default Blue Style",
                        "abstract": "Blue transparent polygon with blue outline",
                        "url": f"http://localhost:8001/wfs?service=WFS&version=1.1.0&request=GetStyles&typeName={typename}"
                    }
                },
                "defaultStyle": "default"
            }
            return JSONResponse(content=geojson_response)
        
        elif outputformat.lower() in ['text/xml', 'application/gml+xml']:
            # Return as GML XML
            gml_xml = generate_gml_response(features_list, typename, total_features)
            return Response(
                content=gml_xml,
                media_type="application/gml+xml",
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                    "Access-Control-Allow-Headers": "*"
                }
            )
        
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported output format: {outputformat}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in WFS GetFeature: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def wfs_describe_feature_type(typename: str):
    """
    WFS DescribeFeatureType response - Dynamic based on registered FeatureCollections
    """
    try:
        if not typename:
            raise HTTPException(status_code=400, detail="typename parameter is required")
        
        if typename not in FC_REGISTRY:
            raise HTTPException(status_code=404, detail=f"Feature type '{typename}' not found")
        
        # Get the FeatureCollection from GeoJSON API registry
        fc = FC_REGISTRY[typename]
        
        # Convert to list of features to analyze properties
        features_list = convert_fc_to_features_list(fc)
        
        # Extract property schema from first feature
        properties_schema = {}
        if features_list:
            first_feature = features_list[0]
            if 'properties' in first_feature:
                for prop_name, prop_value in first_feature['properties'].items():
                    prop_type = type(prop_value).__name__
                    properties_schema[prop_name] = prop_type
        
        # Generate XSD schema
        xsd_schema = f'''<?xml version="1.0" encoding="UTF-8"?>
<xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema"
            xmlns:gml="http://www.opengis.net/gml"
            xmlns:{typename.lower()}="http://localhost:8001/wfs/{typename.lower()}"
            targetNamespace="http://localhost:8001/wfs/{typename.lower()}"
            elementFormDefault="qualified">
    <xsd:import namespace="http://www.opengis.net/gml" schemaLocation="http://schemas.opengis.net/gml/3.1.1/base/gml.xsd"/>
    
    <xsd:element name="{typename}" type="{typename.lower()}:{typename}Type" substitutionGroup="gml:_Feature"/>
    
    <xsd:complexType name="{typename}Type">
        <xsd:complexContent>
            <xsd:extension base="gml:AbstractFeatureType">
                <xsd:sequence>'''
        
        # Add property elements
        for prop_name, prop_type in properties_schema.items():
            xsd_type = "xsd:string"  # Default to string
            if prop_type in ['int', 'float']:
                xsd_type = f"xsd:{prop_type}"
            elif prop_type == 'bool':
                xsd_type = "xsd:boolean"
            
            xsd_schema += f'''
                    <xsd:element name="{prop_name}" type="{xsd_type}" minOccurs="0" maxOccurs="1"/>'''
        
        xsd_schema += '''
                </xsd:sequence>
            </xsd:extension>
        </xsd:complexContent>
    </xsd:complexType>
</xsd:schema>'''
        
        return Response(
            content=xsd_schema,
            media_type="application/xml",
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "*"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in WFS DescribeFeatureType: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def wfs_get_styles(typename: str):
    """
    WFS GetStyles response - Returns SLD styles for the feature type
    """
    try:
        if not typename:
            raise HTTPException(status_code=400, detail="typename parameter is required")
        
        if typename not in FC_REGISTRY:
            raise HTTPException(status_code=404, detail=f"Feature type '{typename}' not found")
        
        # Get the FeatureCollection from GeoJSON API registry
        fc = FC_REGISTRY[typename]
        
        # Convert to list of features to analyze geometry types
        features_list = convert_fc_to_features_list(fc)
        
        # Analyze geometry types to determine appropriate styles
        geometry_types = set()
        for feature in features_list:
            geometry = feature.get('geometry', {})
            geom_type = geometry.get('type', 'Unknown')
            geometry_types.add(geom_type)
        
        # Generate SLD styles based on geometry types
        from gee_integration import generate_sld_styles
        sld_styles = generate_sld_styles(typename, geometry_types)
        
        return Response(
            content=sld_styles,
            media_type="application/xml",
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "*"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in WFS GetStyles: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def convert_fc_to_features_list(fc):
    """
    Convert ee.FeatureCollection to list of features
    """
    try:
        # Get the FeatureCollection info
        fc_info = fc.getInfo()
        
        if fc_info.get('type') == 'FeatureCollection':
            features = fc_info.get('features', [])
            # Ensure each feature has proper structure
            for feature in features:
                if 'properties' not in feature:
                    feature['properties'] = {}
                if 'geometry' not in feature:
                    feature['geometry'] = {}
            return features
        elif fc_info.get('type') == 'Feature':
            # Ensure single feature has proper structure
            if 'properties' not in fc_info:
                fc_info['properties'] = {}
            if 'geometry' not in fc_info:
                fc_info['geometry'] = {}
            return [fc_info]
        else:
            # Handle geometry case
            return [{
                'type': 'Feature',
                'geometry': fc_info,
                'properties': {}
            }]
    except Exception as e:
        logger.error(f"Error converting FeatureCollection to features list: {e}")
        return []

def filter_by_bbox(features_list, minx, miny, maxx, maxy):
    """
    Filter features by bounding box
    """
    filtered_features = []
    
    for feature in features_list:
        geometry = feature.get('geometry', {})
        if geometry.get('type') == 'Point':
            coords = geometry.get('coordinates', [])
            if len(coords) >= 2:
                x, y = coords[0], coords[1]
                if minx <= x <= maxx and miny <= y <= maxy:
                    filtered_features.append(feature)
        elif geometry.get('type') in ['Polygon', 'MultiPolygon']:
            # Simple bounding box check for polygons
            # This is a simplified implementation
            filtered_features.append(feature)
        else:
            # For other geometry types, include by default
            filtered_features.append(feature)
    
    return filtered_features

def generate_gml_response(features_list, typename, total_features):
    """
    Generate GML XML response
    """
    gml_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<wfs:FeatureCollection xmlns:wfs="http://www.opengis.net/wfs"
                       xmlns:gml="http://www.opengis.net/gml"
                       xmlns:{typename.lower()}="http://localhost:8001/wfs/{typename.lower()}"
                       xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                       xsi:schemaLocation="http://www.opengis.net/wfs http://schemas.opengis.net/wfs/1.1.0/wfs.xsd
                                          http://www.opengis.net/gml http://schemas.opengis.net/gml/3.1.1/base/gml.xsd"
                       numberOfFeatures="{total_features}">'''
    
    for i, feature in enumerate(features_list):
        feature_id = feature.get('id', f"feature_{i}")
        geometry = feature.get('geometry', {})
        properties = feature.get('properties', {})
        
        gml_xml += f'''
    <gml:featureMember>
        <{typename.lower()}:{typename} gml:id="{feature_id}">'''
        
        # Add geometry
        if geometry.get('type') == 'Point':
            coords = geometry.get('coordinates', [])
            if len(coords) >= 2:
                gml_xml += f'''
            <gml:pointProperty>
                <gml:Point srsName="EPSG:4326">
                    <gml:pos>{coords[1]} {coords[0]}</gml:pos>
                </gml:Point>
            </gml:pointProperty>'''
        
        # Add properties
        for prop_name, prop_value in properties.items():
            gml_xml += f'''
            <{typename.lower()}:{prop_name}>{prop_value}</{typename.lower()}:{prop_name}>'''
        
        gml_xml += f'''
        </{typename.lower()}:{typename}>
    </gml:featureMember>'''
    
    gml_xml += '''
</wfs:FeatureCollection>'''
    
    return gml_xml

# =============================================================================
# WFS Cascading Endpoints
# =============================================================================

@app.get("/wfs/cascade")
@app.post("/wfs/cascade")
async def wfs_cascade_service(
    service: str = Query("WFS", description="Service type"),
    version: str = Query("1.1.0", description="WFS version"),
    request: str = Query("GetCapabilities", description="Request type"),
    cascaded_url: str = Query("", description="URL of the cascaded WFS service"),
    typename: str = Query("", description="Feature type name"),
    featureid: str = Query("", description="Feature ID"),
    bbox: str = Query("", description="Bounding box"),
    srsname: str = Query("EPSG:4326", description="Spatial reference system"),
    outputformat: str = Query("application/json", description="Output format"),
    maxfeatures: int = Query(1000, description="Maximum features to return"),
    startindex: int = Query(0, description="Start index for pagination")
):
    """
    WFS Cascading service for proxying external WFS services
    """
    try:
        if not cascaded_url:
            raise HTTPException(status_code=400, detail="cascaded_url parameter is required")
        
        # Build the cascaded request URL
        params = {
            'service': service,
            'version': version,
            'request': request,
            'typename': typename,
            'featureid': featureid,
            'bbox': bbox,
            'srsname': srsname,
            'outputformat': outputformat,
            'maxfeatures': maxfeatures,
            'startindex': startindex
        }
        
        # Remove empty parameters
        params = {k: v for k, v in params.items() if v}
        
        # Make request to cascaded service
        import requests
        response = requests.get(cascaded_url, params=params, timeout=30)
        
        if response.status_code == 200:
            # Return the response from the cascaded service
            content_type = response.headers.get('content-type', 'application/json')
            return Response(
                content=response.content,
                media_type=content_type,
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                    "Access-Control-Allow-Headers": "*"
                }
            )
        else:
            raise HTTPException(status_code=response.status_code, detail=f"Cascaded service error: {response.text}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in WFS cascade service: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# CSW (Catalog Service for Web) Endpoints
# =============================================================================

@app.get("/csw", response_class=Response)
async def csw_get_capabilities(
    service: str = Query("CSW", description="Service type"),
    request: str = Query("GetCapabilities", description="Request type"),
    version: str = Query("2.0.2", description="CSW version")
):
    """
    CSW GetCapabilities endpoint
    """
    try:
        from gee_integration import get_csw_capabilities
        xml_content = get_csw_capabilities()
        return Response(content=xml_content, media_type="application/xml")
    except Exception as e:
        logger.error(f"Error in CSW GetCapabilities: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/csw/records", response_class=Response)
async def csw_get_records(
    service: str = Query("CSW", description="Service type"),
    request: str = Query("GetRecords", description="Request type"),
    typeNames: str = Query("csw:Record", description="Record type"),
    constraint: Optional[str] = Query(None, description="Spatial or text constraint"),
    maxRecords: int = Query(100, description="Maximum records to return"),
    startPosition: int = Query(1, description="Starting position")
):
    """
    CSW GetRecords endpoint - Dynamic discovery of GEE assets
    """
    try:
        from gee_integration import get_csw_records
        xml_content = get_csw_records(constraint, maxRecords, startPosition)
        return Response(content=xml_content, media_type="application/xml")
    except Exception as e:
        logger.error(f"Error in CSW GetRecords: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/csw/records/{asset_id}")
async def csw_get_record_by_id(asset_id: str):
    """
    Get specific CSW record by GEE asset ID
    """
    try:
        from gee_integration import get_csw_record_by_id
        return get_csw_record_by_id(asset_id)
    except Exception as e:
        logger.error(f"Error getting CSW record for asset {asset_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 🧠 FeatureCollection Registry - stores ee objects in memory
# This registry is now dynamic and populated by user data via /fc/{fc_name} endpoints
FC_REGISTRY = {}

# 📋 List all available FeatureCollections
@app.get("/fc")
async def list_featurecollections():
    """List all available FeatureCollections."""
    return {
        "featurecollections": list(FC_REGISTRY.keys()),
        "count": len(FC_REGISTRY)
    }

# 🗑️ Clear all FeatureCollections (for testing/cleanup)
@app.delete("/fc")
async def clear_all_featurecollections():
    """Clear all FeatureCollections from registry."""
    global FC_REGISTRY
    cleared_count = len(FC_REGISTRY)
    FC_REGISTRY.clear()
    return {
        "message": f"Cleared {cleared_count} FeatureCollections",
        "count": 0
    }

# 🗑️ Delete specific FeatureCollection
@app.delete("/fc/{fc_name}")
async def delete_featurecollection(fc_name: str):
    """Delete a specific FeatureCollection from registry."""
    if fc_name not in FC_REGISTRY:
        raise HTTPException(status_code=404, detail=f"FeatureCollection '{fc_name}' not found")
    
    del FC_REGISTRY[fc_name]
    return {
        "message": f"FeatureCollection '{fc_name}' deleted successfully",
        "name": fc_name
    }

# 📥 GET FeatureCollection as GeoJSON (for GeoServer consumption)
@app.get("/fc/{fc_name}")
async def get_fc_featurecollection(fc_name: str):
    """Serve GeoJSON for FeatureCollection or Geometry."""
    if fc_name not in FC_REGISTRY:
        raise HTTPException(status_code=404, detail=f"FeatureCollection '{fc_name}' not found")

    try:
        fc = FC_REGISTRY[fc_name]

        # 🧮 If it's geometry, make a FeatureCollection for GeoJSON output
        if isinstance(fc, ee.geometry.Geometry):
            fc = ee.FeatureCollection([ee.Feature(fc)])

        geojson = fc.getInfo()
        return JSONResponse(content=geojson)

    except Exception as e:
        logger.error(f"Error getting FeatureCollection '{fc_name}': {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 📤 POST FeatureCollection (for notebook push)
@app.post("/fc/{fc_name}")
async def create_fc_featurecollection(fc_name: str, geojson_data: dict):
    """Create a new FeatureCollection from GeoJSON data."""
    try:
        # Convert GeoJSON to Earth Engine FeatureCollection
        if geojson_data.get("type") == "FeatureCollection":
            features = []
            for feature in geojson_data.get("features", []):
                if feature.get("type") == "Feature":
                    geometry = feature.get("geometry")
                    properties = feature.get("properties", {})
                    
                    # Convert GeoJSON geometry to EE geometry - support all OGC types
                    geom_type = geometry.get("type")
                    coords = geometry.get("coordinates", [])
                    
                    if geom_type == "Point":
                        ee_geom = ee.Geometry.Point(coords)
                    elif geom_type == "LineString":
                        ee_geom = ee.Geometry.LineString(coords)
                    elif geom_type == "Polygon":
                        ee_geom = ee.Geometry.Polygon(coords)
                    elif geom_type == "MultiPoint":
                        ee_geom = ee.Geometry.MultiPoint(coords)
                    elif geom_type == "MultiLineString":
                        ee_geom = ee.Geometry.MultiLineString(coords)
                    elif geom_type == "MultiPolygon":
                        ee_geom = ee.Geometry.MultiPolygon(coords)
                    elif geom_type == "GeometryCollection":
                        # Handle GeometryCollection by creating individual geometries
                        geometries = geometry.get("geometries", [])
                        ee_geometries = []
                        for nested_geom in geometries:
                            nested_coords = nested_geom.get("coordinates", [])
                            nested_type = nested_geom.get("type")
                            
                            if nested_type == "Point":
                                ee_geometries.append(ee.Geometry.Point(nested_coords))
                            elif nested_type == "LineString":
                                ee_geometries.append(ee.Geometry.LineString(nested_coords))
                            elif nested_type == "Polygon":
                                ee_geometries.append(ee.Geometry.Polygon(nested_coords))
                            elif nested_type == "MultiPoint":
                                ee_geometries.append(ee.Geometry.MultiPoint(nested_coords))
                            elif nested_type == "MultiLineString":
                                ee_geometries.append(ee.Geometry.MultiLineString(nested_coords))
                            elif nested_type == "MultiPolygon":
                                ee_geometries.append(ee.Geometry.MultiPolygon(nested_coords))
                        
                        # Create a single geometry from the collection
                        if ee_geometries:
                            # For simplicity, we'll create a FeatureCollection from the geometries
                            # This is a workaround since EE doesn't have a direct GeometryCollection equivalent
                            ee_geom = ee_geometries[0]  # Use first geometry as primary
                        else:
                            raise ValueError("Empty GeometryCollection")
                    else:
                        raise ValueError(f"Unsupported geometry type: {geom_type}")
                    
                    features.append(ee.Feature(ee_geom, properties))
            
            fc = ee.FeatureCollection(features)
            
        elif geojson_data.get("type") == "Feature":
            # Single feature - support all OGC geometry types
            geometry = geojson_data.get("geometry")
            properties = geojson_data.get("properties", {})
            
            geom_type = geometry.get("type")
            coords = geometry.get("coordinates", [])
            
            if geom_type == "Point":
                ee_geom = ee.Geometry.Point(coords)
            elif geom_type == "LineString":
                ee_geom = ee.Geometry.LineString(coords)
            elif geom_type == "Polygon":
                ee_geom = ee.Geometry.Polygon(coords)
            elif geom_type == "MultiPoint":
                ee_geom = ee.Geometry.MultiPoint(coords)
            elif geom_type == "MultiLineString":
                ee_geom = ee.Geometry.MultiLineString(coords)
            elif geom_type == "MultiPolygon":
                ee_geom = ee.Geometry.MultiPolygon(coords)
            elif geom_type == "GeometryCollection":
                # Handle GeometryCollection for single feature
                geometries = geometry.get("geometries", [])
                ee_geometries = []
                for nested_geom in geometries:
                    nested_coords = nested_geom.get("coordinates", [])
                    nested_type = nested_geom.get("type")
                    
                    if nested_type == "Point":
                        ee_geometries.append(ee.Geometry.Point(nested_coords))
                    elif nested_type == "LineString":
                        ee_geometries.append(ee.Geometry.LineString(nested_coords))
                    elif nested_type == "Polygon":
                        ee_geometries.append(ee.Geometry.Polygon(nested_coords))
                    elif nested_type == "MultiPoint":
                        ee_geometries.append(ee.Geometry.MultiPoint(nested_coords))
                    elif nested_type == "MultiLineString":
                        ee_geometries.append(ee.Geometry.MultiLineString(nested_coords))
                    elif nested_type == "MultiPolygon":
                        ee_geometries.append(ee.Geometry.MultiPolygon(nested_coords))
                
                if ee_geometries:
                    ee_geom = ee_geometries[0]  # Use first geometry as primary
                else:
                    raise ValueError("Empty GeometryCollection")
            else:
                raise ValueError(f"Unsupported geometry type: {geom_type}")
            
            fc = ee.FeatureCollection([ee.Feature(ee_geom, properties)])
            
        else:
            raise ValueError("Invalid GeoJSON format. Expected FeatureCollection or Feature.")
        
        # Store in registry
        FC_REGISTRY[fc_name] = fc
        
        return {
            "message": f"FeatureCollection '{fc_name}' created successfully",
            "name": fc_name,
            "type": "FeatureCollection",
            "count": fc.size().getInfo() if hasattr(fc, 'size') else 1
        }
        
    except Exception as e:
        logger.error(f"Error creating FeatureCollection '{fc_name}': {e}")
        raise HTTPException(status_code=400, detail=str(e))

# 🔄 PUT FeatureCollection (for updating existing)
@app.put("/fc/{fc_name}")
async def update_fc_featurecollection(fc_name: str, geojson_data: dict):
    """Update an existing FeatureCollection from GeoJSON data."""
    try:
        # Use the same logic as POST to create/update
        result = await create_fc_featurecollection(fc_name, geojson_data)
        result["message"] = f"FeatureCollection '{fc_name}' updated successfully"
        return result
        
    except Exception as e:
        logger.error(f"Error updating FeatureCollection '{fc_name}': {e}")
        raise HTTPException(status_code=400, detail=str(e))

# 🗑️ DELETE FeatureCollection
@app.delete("/fc/{fc_name}")
async def delete_fc_featurecollection(fc_name: str):
    """Delete a FeatureCollection."""
    if fc_name not in FC_REGISTRY:
        raise HTTPException(status_code=404, detail=f"FeatureCollection '{fc_name}' not found")
    
    try:
        del FC_REGISTRY[fc_name]
        return {
            "message": f"FeatureCollection '{fc_name}' deleted successfully",
            "name": fc_name
        }
        
    except Exception as e:
        logger.error(f"Error deleting FeatureCollection '{fc_name}': {e}")
        raise HTTPException(status_code=500, detail=str(e))



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
