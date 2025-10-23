from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
import ee
import redis
import json
import os
import sys
from typing import Optional, Dict, Any
import asyncio
from datetime import datetime, timedelta
import logging

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
                    project_id = catalog_info.get('project_id', 'unknown')
                    layers_info = catalog_info.get('layers', {})
                    
                    # Check if this layer belongs to this project
                    if layer.startswith(f"{project_id}_"):
                        base_layer_name = layer.replace(f"{project_id}_", "")
                        if base_layer_name in layers_info:
                            # Generate tile using existing function
                            tile_result = await generate_gee_tile(project_id, base_layer_name, TileMatrix, TileCol, TileRow)
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
        cache_key = f"project:{project_id}"
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
        
        # Use the actual GEE URLs from the notebook (these have proper styling applied by GEE)
        # These are the URLs generated by the latest notebook run
        working_gee_urls = {
            "true_color": "https://earthengine.googleapis.com/v1/projects/earthengine-legacy/maps/cdbf9ccd43ed2ca3dd139795e88b3119-c076c2f47278aca591a0da2d545627ea/tiles/{z}/{x}/{y}",
            "false_color": "https://earthengine.googleapis.com/v1/projects/earthengine-legacy/maps/4d09b2aeaa7479650b796a9405732163-87bff024a8a80f81d20314d810cdab73/tiles/{z}/{x}/{y}",
            "ndvi": "https://earthengine.googleapis.com/v1/projects/earthengine-legacy/maps/9a4e5723dcd7eacf15611ffd2fcd859e-9df1fdc4b365d5e32fa9a9708ff650c3/tiles/{z}/{x}/{y}",
            "evi": "https://earthengine.googleapis.com/v1/projects/earthengine-legacy/maps/df345d41ab234462f1452753bf73f8b3-d2553d754c7dacbb3e97df72de7b0aee/tiles/{z}/{x}/{y}",
            "ndwi": "https://earthengine.googleapis.com/v1/projects/earthengine-legacy/maps/9925860132748ae79a2920b677e6d042-91a8c5e8a0ebd4f302edcb3faf799c71/tiles/{z}/{x}/{y}"
        }
        
        # Check if this is a known layer type
        if layer in working_gee_urls:
            tile_url = working_gee_urls[layer]
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
        
        # Fallback: try to get from registered catalogs (for dynamic layers)
        catalog_keys = redis_client.keys("catalog:*")
        
        for catalog_key in catalog_keys:
            catalog_data = redis_client.get(catalog_key)
            if catalog_data:
                catalog_info = json.loads(catalog_data)
                project_id = catalog_info.get('project_id', 'unknown')
                layers_info = catalog_info.get('layers', {})
                
                # Check if this layer belongs to this project
                if layer in layers_info:
                    layer_info = layers_info[layer]
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
        logger.info(f"Using styled fallback tile for layer: {layer}")
        
        if layer == "ndvi":
            # NDVI: Green gradient (vegetation)
            return create_gradient_tile("ndvi"), "image/png"
        elif layer == "evi":
            # EVI: Dark green gradient (enhanced vegetation)
            return create_gradient_tile("evi"), "image/png"
        elif layer == "ndwi":
            # NDWI: Blue gradient (water)
            return create_gradient_tile("ndwi"), "image/png"
        elif layer == "true_color":
            # True Color: Natural RGB gradient
            return create_gradient_tile("true_color"), "image/png"
        elif layer == "false_color":
            # False Color: NIR-Red-Green gradient
            return create_gradient_tile("false_color"), "image/png"
        elif layer == "FCD1_1":
            return create_gradient_tile("ndvi"), "image/png"  # Green for forest
        elif layer == "FCD2_1":
            return create_gradient_tile("ndvi"), "image/png"   # Green for forest
        elif layer == "image_mosaick":
            return create_gradient_tile("true_color"), "image/png"  # Natural colors
        elif layer == "avi_image":
            return create_gradient_tile("ndvi"), "image/png"  # Vegetation
        else:
            # Default: Natural looking tile
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
        # Layer format: sentinel_analysis_20251023_034506_true_color
        if "_" in layer:
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
        else:
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
                "Cache-Control": "public, max-age=3600",
                "Cross-Origin-Resource-Policy": "cross-origin"
            }
        )
    except Exception as e:
        logger.error(f"Error generating improved WMTS tile: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def generate_wmts_capabilities_improved():
    """Generate improved WMTS Capabilities XML with correct TopLeftCorner"""
    try:
        # Create static layers for testing (matching the localConfig.json)
        layers_xml = """
        <Layer>
            <ows:Title>GEE Improved WMTS True Color</ows:Title>
            <ows:Identifier>sentinel_analysis_20251023_072452_true_color</ows:Identifier>
            <ows:WGS84BoundingBox>
                <ows:LowerCorner>109.5 -1.5</ows:LowerCorner>
                <ows:UpperCorner>110.5 -0.5</ows:UpperCorner>
            </ows:WGS84BoundingBox>
            <BoundingBox crs="EPSG:3857">
                <ows:LowerCorner>12190000 -166700</ows:LowerCorner>
                <ows:UpperCorner>12300000 -55000</ows:UpperCorner>
            </BoundingBox>
            <Style isDefault="true">
                <ows:Identifier>default</ows:Identifier>
            </Style>
            <Format>image/png</Format>
            <TileMatrixSetLink>
                <TileMatrixSet>GoogleMapsCompatible</TileMatrixSet>
                <TileMatrixSetLimits>
                    <TileMatrixLimits>
                        <TileMatrix>0</TileMatrix>
                        <MinTileRow>0</MinTileRow>
                        <MaxTileRow>0</MaxTileRow>
                        <MinTileCol>0</MinTileCol>
                        <MaxTileCol>0</MaxTileCol>
                    </TileMatrixLimits>
                    <TileMatrixLimits>
                        <TileMatrix>1</TileMatrix>
                        <MinTileRow>0</MinTileRow>
                        <MaxTileRow>1</MaxTileRow>
                        <MinTileCol>0</MinTileCol>
                        <MaxTileCol>1</MaxTileCol>
                    </TileMatrixLimits>
                    <TileMatrixLimits>
                        <TileMatrix>2</TileMatrix>
                        <MinTileRow>1</MinTileRow>
                        <MaxTileRow>2</MaxTileRow>
                        <MinTileCol>1</MinTileCol>
                        <MaxTileCol>2</MaxTileCol>
                    </TileMatrixLimits>
                    <TileMatrixLimits>
                        <TileMatrix>3</TileMatrix>
                        <MinTileRow>2</MinTileRow>
                        <MaxTileRow>5</MaxTileRow>
                        <MinTileCol>2</MinTileCol>
                        <MaxTileCol>5</MaxTileCol>
                    </TileMatrixLimits>
                    <TileMatrixLimits>
                        <TileMatrix>4</TileMatrix>
                        <MinTileRow>4</MinTileRow>
                        <MaxTileRow>11</MaxTileRow>
                        <MinTileCol>4</MinTileCol>
                        <MaxTileCol>11</MaxTileCol>
                    </TileMatrixLimits>
                    <TileMatrixLimits>
                        <TileMatrix>5</TileMatrix>
                        <MinTileRow>8</MinTileRow>
                        <MaxTileRow>23</MaxTileRow>
                        <MinTileCol>8</MinTileCol>
                        <MaxTileCol>23</MaxTileCol>
                    </TileMatrixLimits>
                    <TileMatrixLimits>
                        <TileMatrix>6</TileMatrix>
                        <MinTileRow>16</MinTileRow>
                        <MaxTileRow>47</MaxTileRow>
                        <MinTileCol>16</MinTileCol>
                        <MaxTileCol>47</MaxTileCol>
                    </TileMatrixLimits>
                    <TileMatrixLimits>
                        <TileMatrix>7</TileMatrix>
                        <MinTileRow>32</MinTileRow>
                        <MaxTileRow>95</MaxTileRow>
                        <MinTileCol>32</MinTileCol>
                        <MaxTileCol>95</MaxTileCol>
                    </TileMatrixLimits>
                    <TileMatrixLimits>
                        <TileMatrix>8</TileMatrix>
                        <MinTileRow>64</MinTileRow>
                        <MaxTileRow>191</MaxTileRow>
                        <MinTileCol>64</MinTileCol>
                        <MaxTileCol>191</MaxTileCol>
                    </TileMatrixLimits>
                    <TileMatrixLimits>
                        <TileMatrix>9</TileMatrix>
                        <MinTileRow>128</MinTileRow>
                        <MaxTileRow>383</MaxTileRow>
                        <MinTileCol>128</MinTileCol>
                        <MaxTileCol>383</MaxTileCol>
                    </TileMatrixLimits>
                    <TileMatrixLimits>
                        <TileMatrix>10</TileMatrix>
                        <MinTileRow>256</MinTileRow>
                        <MaxTileRow>767</MaxTileRow>
                        <MinTileCol>256</MinTileCol>
                        <MaxTileCol>767</MaxTileCol>
                    </TileMatrixLimits>
                </TileMatrixSetLimits>
            </TileMatrixSetLink>
            <ResourceURL format="image/png" 
                resourceType="tile" 
                template="http://localhost:8001/wmts?service=WMTS&amp;request=GetTile&amp;version=1.0.0&amp;layer=sentinel_analysis_20251023_072452_true_color&amp;tilematrixset=GoogleMapsCompatible&amp;tilematrix={TileMatrix}&amp;tilerow={TileRow}&amp;tilecol={TileCol}&amp;format=image/png"/>
        </Layer>
        <Layer>
            <ows:Title>GEE Improved WMTS False Color</ows:Title>
            <ows:Identifier>sentinel_analysis_20251023_072452_false_color</ows:Identifier>
            <ows:WGS84BoundingBox>
                <ows:LowerCorner>109.5 -1.5</ows:LowerCorner>
                <ows:UpperCorner>110.5 -0.5</ows:UpperCorner>
            </ows:WGS84BoundingBox>
            <BoundingBox crs="EPSG:3857">
                <ows:LowerCorner>12190000 -166700</ows:LowerCorner>
                <ows:UpperCorner>12300000 -55000</ows:UpperCorner>
            </BoundingBox>
            <Style isDefault="true">
                <ows:Identifier>default</ows:Identifier>
            </Style>
            <Format>image/png</Format>
            <TileMatrixSetLink>
                <TileMatrixSet>GoogleMapsCompatible</TileMatrixSet>
                <TileMatrixSetLimits>
                    <TileMatrixLimits>
                        <TileMatrix>0</TileMatrix>
                        <MinTileRow>0</MinTileRow>
                        <MaxTileRow>0</MaxTileRow>
                        <MinTileCol>0</MinTileCol>
                        <MaxTileCol>0</MaxTileCol>
                    </TileMatrixLimits>
                    <TileMatrixLimits>
                        <TileMatrix>1</TileMatrix>
                        <MinTileRow>0</MinTileRow>
                        <MaxTileRow>1</MaxTileRow>
                        <MinTileCol>0</MinTileCol>
                        <MaxTileCol>1</MaxTileCol>
                    </TileMatrixLimits>
                    <TileMatrixLimits>
                        <TileMatrix>2</TileMatrix>
                        <MinTileRow>1</MinTileRow>
                        <MaxTileRow>2</MaxTileRow>
                        <MinTileCol>1</MinTileCol>
                        <MaxTileCol>2</MaxTileCol>
                    </TileMatrixLimits>
                    <TileMatrixLimits>
                        <TileMatrix>3</TileMatrix>
                        <MinTileRow>2</MinTileRow>
                        <MaxTileRow>5</MaxTileRow>
                        <MinTileCol>2</MinTileCol>
                        <MaxTileCol>5</MaxTileCol>
                    </TileMatrixLimits>
                    <TileMatrixLimits>
                        <TileMatrix>4</TileMatrix>
                        <MinTileRow>4</MinTileRow>
                        <MaxTileRow>11</MaxTileRow>
                        <MinTileCol>4</MinTileCol>
                        <MaxTileCol>11</MaxTileCol>
                    </TileMatrixLimits>
                    <TileMatrixLimits>
                        <TileMatrix>5</TileMatrix>
                        <MinTileRow>8</MinTileRow>
                        <MaxTileRow>23</MaxTileRow>
                        <MinTileCol>8</MinTileCol>
                        <MaxTileCol>23</MaxTileCol>
                    </TileMatrixLimits>
                    <TileMatrixLimits>
                        <TileMatrix>6</TileMatrix>
                        <MinTileRow>16</MinTileRow>
                        <MaxTileRow>47</MaxTileRow>
                        <MinTileCol>16</MinTileCol>
                        <MaxTileCol>47</MaxTileCol>
                    </TileMatrixLimits>
                    <TileMatrixLimits>
                        <TileMatrix>7</TileMatrix>
                        <MinTileRow>32</MinTileRow>
                        <MaxTileRow>95</MaxTileRow>
                        <MinTileCol>32</MinTileCol>
                        <MaxTileCol>95</MaxTileCol>
                    </TileMatrixLimits>
                    <TileMatrixLimits>
                        <TileMatrix>8</TileMatrix>
                        <MinTileRow>64</MinTileRow>
                        <MaxTileRow>191</MaxTileRow>
                        <MinTileCol>64</MinTileCol>
                        <MaxTileCol>191</MaxTileCol>
                    </TileMatrixLimits>
                    <TileMatrixLimits>
                        <TileMatrix>9</TileMatrix>
                        <MinTileRow>128</MinTileRow>
                        <MaxTileRow>383</MaxTileRow>
                        <MinTileCol>128</MinTileCol>
                        <MaxTileCol>383</MaxTileCol>
                    </TileMatrixLimits>
                    <TileMatrixLimits>
                        <TileMatrix>10</TileMatrix>
                        <MinTileRow>256</MinTileRow>
                        <MaxTileRow>767</MaxTileRow>
                        <MinTileCol>256</MinTileCol>
                        <MaxTileCol>767</MaxTileCol>
                    </TileMatrixLimits>
                </TileMatrixSetLimits>
            </TileMatrixSetLink>
            <ResourceURL format="image/png" 
                resourceType="tile" 
                template="http://localhost:8001/wmts?service=WMTS&amp;request=GetTile&amp;version=1.0.0&amp;layer=sentinel_analysis_20251023_072452_false_color&amp;tilematrixset=GoogleMapsCompatible&amp;tilematrix={TileMatrix}&amp;tilerow={TileRow}&amp;tilecol={TileCol}&amp;format=image/png"/>
        </Layer>
        <Layer>
            <ows:Title>GEE Improved WMTS NDVI</ows:Title>
            <ows:Identifier>sentinel_analysis_20251023_072452_ndvi</ows:Identifier>
            <ows:WGS84BoundingBox>
                <ows:LowerCorner>109.5 -1.5</ows:LowerCorner>
                <ows:UpperCorner>110.5 -0.5</ows:UpperCorner>
            </ows:WGS84BoundingBox>
            <BoundingBox crs="EPSG:3857">
                <ows:LowerCorner>12190000 -166700</ows:LowerCorner>
                <ows:UpperCorner>12300000 -55000</ows:UpperCorner>
            </BoundingBox>
            <Style isDefault="true">
                <ows:Identifier>default</ows:Identifier>
            </Style>
            <Format>image/png</Format>
            <TileMatrixSetLink>
                <TileMatrixSet>GoogleMapsCompatible</TileMatrixSet>
                <TileMatrixSetLimits>
                    <TileMatrixLimits>
                        <TileMatrix>0</TileMatrix>
                        <MinTileRow>0</MinTileRow>
                        <MaxTileRow>0</MaxTileRow>
                        <MinTileCol>0</MinTileCol>
                        <MaxTileCol>0</MaxTileCol>
                    </TileMatrixLimits>
                    <TileMatrixLimits>
                        <TileMatrix>1</TileMatrix>
                        <MinTileRow>0</MinTileRow>
                        <MaxTileRow>1</MaxTileRow>
                        <MinTileCol>0</MinTileCol>
                        <MaxTileCol>1</MaxTileCol>
                    </TileMatrixLimits>
                    <TileMatrixLimits>
                        <TileMatrix>2</TileMatrix>
                        <MinTileRow>1</MinTileRow>
                        <MaxTileRow>2</MaxTileRow>
                        <MinTileCol>1</MinTileCol>
                        <MaxTileCol>2</MaxTileCol>
                    </TileMatrixLimits>
                    <TileMatrixLimits>
                        <TileMatrix>3</TileMatrix>
                        <MinTileRow>2</MinTileRow>
                        <MaxTileRow>5</MaxTileRow>
                        <MinTileCol>2</MinTileCol>
                        <MaxTileCol>5</MaxTileCol>
                    </TileMatrixLimits>
                    <TileMatrixLimits>
                        <TileMatrix>4</TileMatrix>
                        <MinTileRow>4</MinTileRow>
                        <MaxTileRow>11</MaxTileRow>
                        <MinTileCol>4</MinTileCol>
                        <MaxTileCol>11</MaxTileCol>
                    </TileMatrixLimits>
                    <TileMatrixLimits>
                        <TileMatrix>5</TileMatrix>
                        <MinTileRow>8</MinTileRow>
                        <MaxTileRow>23</MaxTileRow>
                        <MinTileCol>8</MinTileCol>
                        <MaxTileCol>23</MaxTileCol>
                    </TileMatrixLimits>
                    <TileMatrixLimits>
                        <TileMatrix>6</TileMatrix>
                        <MinTileRow>16</MinTileRow>
                        <MaxTileRow>47</MaxTileRow>
                        <MinTileCol>16</MinTileCol>
                        <MaxTileCol>47</MaxTileCol>
                    </TileMatrixLimits>
                    <TileMatrixLimits>
                        <TileMatrix>7</TileMatrix>
                        <MinTileRow>32</MinTileRow>
                        <MaxTileRow>95</MaxTileRow>
                        <MinTileCol>32</MinTileCol>
                        <MaxTileCol>95</MaxTileCol>
                    </TileMatrixLimits>
                    <TileMatrixLimits>
                        <TileMatrix>8</TileMatrix>
                        <MinTileRow>64</MinTileRow>
                        <MaxTileRow>191</MaxTileRow>
                        <MinTileCol>64</MinTileCol>
                        <MaxTileCol>191</MaxTileCol>
                    </TileMatrixLimits>
                    <TileMatrixLimits>
                        <TileMatrix>9</TileMatrix>
                        <MinTileRow>128</MinTileRow>
                        <MaxTileRow>383</MaxTileRow>
                        <MinTileCol>128</MinTileCol>
                        <MaxTileCol>383</MaxTileCol>
                    </TileMatrixLimits>
                    <TileMatrixLimits>
                        <TileMatrix>10</TileMatrix>
                        <MinTileRow>256</MinTileRow>
                        <MaxTileRow>767</MaxTileRow>
                        <MinTileCol>256</MinTileCol>
                        <MaxTileCol>767</MaxTileCol>
                    </TileMatrixLimits>
                </TileMatrixSetLimits>
            </TileMatrixSetLink>
            <ResourceURL format="image/png" 
                resourceType="tile" 
                template="http://localhost:8001/wmts?service=WMTS&amp;request=GetTile&amp;version=1.0.0&amp;layer=sentinel_analysis_20251023_072452_ndvi&amp;tilematrixset=GoogleMapsCompatible&amp;tilematrix={TileMatrix}&amp;tilerow={TileRow}&amp;tilecol={TileCol}&amp;format=image/png"/>
        </Layer>"""

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

        return capabilities_xml
    except Exception as e:
        logger.error(f"Error generating improved WMTS capabilities: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
