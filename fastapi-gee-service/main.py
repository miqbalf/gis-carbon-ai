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
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

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

@app.get("/wmts")
@app.head("/wmts")
async def wmts_capabilities(SERVICE: str = Query("WMTS"), REQUEST: str = Query("GetCapabilities")):
    """
    WMTS GetCapabilities endpoint
    """
    if SERVICE.upper() != "WMTS" or REQUEST.upper() != "GETCAPABILITIES":
        raise HTTPException(status_code=400, detail="Invalid request")

    # Build dynamic layers from registered projects
    layers_xml = ""
    try:
        project_keys = redis_client.keys("project:*")
        
        for project_key in project_keys:
            project_data = redis_client.get(project_key)
            if project_data:
                project_info = json.loads(project_data)
                project_id = project_info.get('project_id', 'unknown')
                layers = project_info.get('layers', {})
                
                for layer_name, layer_info in layers.items():
                    full_layer_name = f"{project_id}_{layer_name}"
                    layer_title = layer_info.get('name', layer_name)
                    
                    layers_xml += f"""
            <Layer>
                <ows:Title>{layer_title}</ows:Title>
                <ows:Identifier>{full_layer_name}</ows:Identifier>
                <ResourceURL format="image/png"
                    template="http://fastapi:8000/wmts/{full_layer_name}/{{TileMatrix}}/{{TileCol}}/{{TileRow}}.png"/>
                <TileMatrixSetLink>
                    <TileMatrixSet>GoogleMapsCompatible</TileMatrixSet>
                </TileMatrixSetLink>
            </Layer>"""
    except Exception as e:
        logger.warning(f"Could not load registered layers for WMTS: {e}")
        # Fallback to default layer
        layers_xml = """
            <Layer>
                <ows:Title>GEE Analysis Layer</ows:Title>
                <ows:Identifier>gee_analysis</ows:Identifier>
                <ResourceURL format="image/png"
                    template="http://fastapi:8000/wmts/gee_analysis/{{TileMatrix}}/{{TileCol}}/{{TileRow}}.png"/>
                <TileMatrixSetLink>
                    <TileMatrixSet>GoogleMapsCompatible</TileMatrixSet>
                </TileMatrixSetLink>
            </Layer>"""

    # Build complete WMTS capabilities
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Capabilities xmlns="http://www.opengis.net/wmts/1.0"
    xmlns:ows="http://www.opengis.net/ows/1.1"
    xmlns:xlink="http://www.w3.org/1999/xlink"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:schemaLocation="http://www.opengis.net/wmts/1.0
    http://schemas.opengis.net/wmts/1.0/wmtsGetCapabilities_response.xsd">
    <ows:ServiceIdentification>
        <ows:Title>FastAPI WMTS Proxy for GEE</ows:Title>
        <ows:ServiceType>OGC WMTS</ows:ServiceType>
    </ows:ServiceIdentification>
    <ows:OperationsMetadata>
        <ows:Operation name="GetCapabilities">
            <ows:DCP>
                <ows:HTTP>
                    <ows:Get xlink:href="http://fastapi:8000/wmts"/>
                </ows:HTTP>
            </ows:DCP>
        </ows:Operation>
        <ows:Operation name="GetTile">
            <ows:DCP>
                <ows:HTTP>
                    <ows:Get xlink:href="http://fastapi:8000/wmts"/>
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
    return Response(xml, media_type="application/xml")


@app.get("/wmts/{layer}/{z}/{x}/{y}.png")
@app.head("/wmts/{layer}/{z}/{x}/{y}.png")
async def get_wmts_tile(layer: str, z: int, x: int, y: int):
    """
    WMTS tile endpoint
    """
    try:
        # Check if this is a registered layer (format: project_id_layer_name)
        if '_' in layer:
            # Split by the last underscore to get project_id and layer_name
            parts = layer.split('_')
            if len(parts) >= 3:  # At least project_id_layer_name
                project_id = '_'.join(parts[:-1])  # Everything except the last part
                base_layer_name = parts[-1]  # The last part is the layer name
                
                logger.info(f"WMTS tile request: project_id={project_id}, layer={base_layer_name}, z={z}, x={x}, y={y}")
                
                # Try to find the layer in registered projects
                project_key = f"project:{project_id}"
                project_data = redis_client.get(project_key)
                
                if project_data:
                    project_info = json.loads(project_data)
                    layers_info = project_info.get('layers', {})
                    
                    if base_layer_name in layers_info:
                        # Generate tile using the existing function
                        tile_data = await generate_gee_tile("gee", base_layer_name, z, x, y)
                        return Response(content=tile_data, media_type="image/png")
                    else:
                        logger.warning(f"Layer {base_layer_name} not found in project {project_id}")
                else:
                    logger.warning(f"Project {project_id} not found in cache")
        
        # Fallback: try to generate tile anyway
        logger.info(f"Fallback: generating tile for layer={layer}, z={z}, x={x}, y={y}")
        tile_data = await generate_gee_tile("gee", layer, z, x, y)
        return Response(content=tile_data, media_type="image/png")
        
    except Exception as e:
        logger.error(f"Error generating WMTS tile: {e}")
        # Return a placeholder tile
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
    """
    try:
        # Get layers from registered projects
        default_layers = []
        
        # Try to get layers from registered projects
        try:
            # Get all project keys from Redis
            project_keys = redis_client.keys("project:*")
            
            for project_key in project_keys:
                project_data = redis_client.get(project_key)
                if project_data:
                    project_info = json.loads(project_data)
                    project_id = project_info.get('project_id', 'unknown')
                    layers = project_info.get('layers', {})
                    
                    for layer_name, layer_info in layers.items():
                        # Create layer entry for search
                        layer_entry = {
                            "name": f"{project_id}_{layer_name}",
                            "title": layer_info.get('name', layer_name),
                            "description": layer_info.get('description', f'{layer_name} from {project_id}'),
                            "type": "wms",
                            "url": f"http://localhost:8001/wms?service=WMS&version=1.3.0&request=GetMap&layers={project_id}_{layer_name}&bbox={{bbox}}&width={{width}}&height={{height}}&crs={{crs}}&format=image/png"
                        }
                        default_layers.append(layer_entry)
        except Exception as e:
            logger.warning(f"Could not load registered layers: {e}")
        
        # If no registered layers found, use default fallback layers
        if not default_layers:
            default_layers = [
                {
                    "name": "FCD1_1",
                    "title": "Forest Cover Density 1-1",
                    "description": "Primary Forest Cover Density layer",
                    "type": "tile",
                    "url": "http://localhost:8001/tiles/gee/{z}/{x}/{y}?layer=FCD1_1"
                },
                {
                    "name": "FCD2_1", 
                    "title": "Forest Cover Density 2-1",
                    "description": "Secondary Forest Cover Density layer",
                    "type": "tile",
                    "url": "http://localhost:8001/tiles/gee/{z}/{x}/{y}?layer=FCD2_1"
                },
                {
                    "name": "image_mosaick",
                    "title": "Image Mosaic",
                    "description": "Satellite image mosaic",
                    "type": "tile", 
                    "url": "http://localhost:8001/tiles/gee/{z}/{x}/{y}?layer=image_mosaick"
                },
                {
                    "name": "avi_image",
                    "title": "AVI Image", 
                    "description": "Advanced Vegetation Index",
                    "type": "tile",
                    "url": "http://localhost:8001/tiles/gee/{z}/{x}/{y}?layer=avi_image"
                }
            ]
        
        # Filter layers based on search query
        if q:
            filtered_layers = [
                layer for layer in default_layers 
                if q.lower() in layer["name"].lower() or 
                   q.lower() in layer["title"].lower() or
                   q.lower() in layer["description"].lower()
            ]
        else:
            filtered_layers = default_layers
            
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
    """
    try:
        # Check if this is a GetRecords request (POST with XML body)
        if request == "GetRecords" or (request_body and "GetRecords" in request_body):
            # Return GetRecords response with our layers
            getrecords_response = """<?xml version="1.0" encoding="UTF-8"?>
<csw:GetRecordsResponse xmlns:csw="http://www.opengis.net/cat/csw/2.0.2" 
                        xmlns:dc="http://purl.org/dc/elements/1.1/" 
                        xmlns:dct="http://purl.org/dc/terms/"
                        xmlns:ows="http://www.opengis.net/ows"
                        version="2.0.2">
    <csw:SearchStatus timestamp="2025-10-21T16:00:00Z" status="complete"/>
    <csw:SearchResults numberOfRecordsMatched="4" numberOfRecordsReturned="4" nextRecord="0" recordSchema="http://www.opengis.net/cat/csw/2.0.2">
        <csw:Record>
            <dc:identifier>FCD1_1</dc:identifier>
            <dc:title>Forest Cover Density 1-1</dc:title>
            <dc:type>dataset</dc:type>
            <dc:description>Primary Forest Cover Density layer</dc:description>
            <dc:subject>Forest, Cover, Density</dc:subject>
            <dct:references scheme="OGC:WMS">http://localhost:8001/wms?service=WMS&amp;version=1.3.0&amp;request=GetMap&amp;layers=FCD1_1&amp;styles=&amp;crs=EPSG:3857&amp;bbox=-20037508.34,-20037508.34,20037508.34,20037508.34&amp;width=256&amp;height=256</dct:references>
        </csw:Record>
        <csw:Record>
            <dc:identifier>FCD2_1</dc:identifier>
            <dc:title>Forest Cover Density 2-1</dc:title>
            <dc:type>dataset</dc:type>
            <dc:description>Secondary Forest Cover Density layer</dc:description>
            <dc:subject>Forest, Cover, Density</dc:subject>
            <dct:references scheme="OGC:WMS">http://localhost:8001/wms?service=WMS&amp;version=1.3.0&amp;request=GetMap&amp;layers=FCD2_1&amp;styles=&amp;crs=EPSG:3857&amp;bbox=-20037508.34,-20037508.34,20037508.34,20037508.34&amp;width=256&amp;height=256</dct:references>
        </csw:Record>
        <csw:Record>
            <dc:identifier>image_mosaick</dc:identifier>
            <dc:title>Image Mosaic</dc:title>
            <dc:type>dataset</dc:type>
            <dc:description>Satellite image mosaic</dc:description>
            <dc:subject>Satellite, Image, Mosaic</dc:subject>
            <dct:references scheme="OGC:WMS">http://localhost:8001/wms?service=WMS&amp;version=1.3.0&amp;request=GetMap&amp;layers=image_mosaick&amp;styles=&amp;crs=EPSG:3857&amp;bbox=-20037508.34,-20037508.34,20037508.34,20037508.34&amp;width=256&amp;height=256</dct:references>
        </csw:Record>
        <csw:Record>
            <dc:identifier>avi_image</dc:identifier>
            <dc:title>AVI Image</dc:title>
            <dc:type>dataset</dc:type>
            <dc:description>Advanced Vegetation Index</dc:description>
            <dc:subject>Vegetation, Index, AVI</dc:subject>
            <dct:references scheme="OGC:WMS">http://localhost:8001/wms?service=WMS&amp;version=1.3.0&amp;request=GetMap&amp;layers=avi_image&amp;styles=&amp;crs=EPSG:3857&amp;bbox=-20037508.34,-20037508.34,20037508.34,20037508.34&amp;width=256&amp;height=256</dct:references>
        </csw:Record>
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
        <ows:Title>GEE Analysis Service</ows:Title>
        <ows:Abstract>Google Earth Engine Analysis Layers</ows:Abstract>
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
@app.head("/wms")
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
    """
    try:
        if request == "GetCapabilities":
            # Build dynamic WMS capabilities with registered layers
            layers_xml = ""
            
            try:
                # Get all project keys from Redis
                project_keys = redis_client.keys("project:*")
                
                for project_key in project_keys:
                    project_data = redis_client.get(project_key)
                    if project_data:
                        project_info = json.loads(project_data)
                        project_id = project_info.get('project_id', 'unknown')
                        layers = project_info.get('layers', {})
                        
                        for layer_name, layer_info in layers.items():
                            full_layer_name = f"{project_id}_{layer_name}"
                            layer_title = layer_info.get('name', layer_name)
                            layer_description = layer_info.get('description', f'{layer_name} from {project_id}')
                            
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
                logger.warning(f"Could not load registered layers for WMS: {e}")
                # Fallback to default layers
                layers_xml = """
            <Layer queryable="1">
                <Name>FCD1_1</Name>
                <Title>Forest Cover Density 1-1</Title>
                <Abstract>Primary Forest Cover Density layer</Abstract>
                <CRS>EPSG:3857</CRS>
                <CRS>EPSG:4326</CRS>
                <BoundingBox CRS="EPSG:3857" minx="-20037508.34" miny="-20037508.34" maxx="20037508.34" maxy="20037508.34"/>
            </Layer>
            <Layer queryable="1">
                <Name>FCD2_1</Name>
                <Title>Forest Cover Density 2-1</Title>
                <Abstract>Secondary Forest Cover Density layer</Abstract>
                <CRS>EPSG:3857</CRS>
                <CRS>EPSG:4326</CRS>
                <BoundingBox CRS="EPSG:3857" minx="-20037508.34" miny="-20037508.34" maxx="20037508.34" maxy="20037508.34"/>
            </Layer>"""
            
            # Build complete WMS capabilities
            wms_capabilities = f"""<?xml version="1.0" encoding="UTF-8"?>
<WMS_Capabilities version="1.3.0" xmlns="http://www.opengis.net/wms" xmlns:xlink="http://www.w3.org/1999/xlink">
    <Service>
        <Name>WMS</Name>
        <Title>GEE Analysis WMS Service</Title>
        <Abstract>Google Earth Engine Analysis Layers via WMS</Abstract>
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
        
        elif request == "GetMap":
            # For GetMap requests, handle registered layers
            if layers:
                layer_name = layers.split(',')[0]  # Take first layer
                
                # Check if this is a registered layer (format: project_id_layer_name)
                if '_' in layer_name:
                    try:
                        # Try to find the layer in registered projects
                        project_keys = redis_client.keys("project:*")
                        
                        for project_key in project_keys:
                            project_data = redis_client.get(project_key)
                            if project_data:
                                project_info = json.loads(project_data)
                                project_id = project_info.get('project_id', 'unknown')
                                layers_info = project_info.get('layers', {})
                                
                                # Check if this layer belongs to this project
                                if layer_name.startswith(f"{project_id}_"):
                                    base_layer_name = layer_name.replace(f"{project_id}_", "")
                                    if base_layer_name in layers_info:
                                        layer_info = layers_info[base_layer_name]
                                        
                                        # Get the GEE tile URL from the layer info
                                        tile_url = layer_info.get('tile_url', '')
                                        if tile_url:
                                            # Parse bbox to get zoom level and tile coordinates
                                            bbox_parts = bbox.split(',')
                                            if len(bbox_parts) == 4:
                                                minx, miny, maxx, maxy = map(float, bbox_parts)
                                                
                                                # Calculate zoom level from bbox
                                                import math
                                                zoom = max(0, min(18, int(math.log2(20037508.34 * 2 / (maxx - minx)))))
                                                
                                                # Calculate tile coordinates
                                                n = 2.0 ** zoom
                                                tile_x = int((minx + 20037508.34) / (40075016.68 / n))
                                                tile_y = int((20037508.34 - maxy) / (40075016.68 / n))
                                                
                                                # Replace placeholders in GEE tile URL
                                                gee_tile_url = tile_url.replace('{z}', str(zoom)).replace('{x}', str(tile_x)).replace('{y}', str(tile_y))
                                                
                                                try:
                                                    # Use the existing generate_gee_tile function instead of direct GEE URL
                                                    # This will handle authentication and proper tile generation
                                                    tile_data = await generate_gee_tile("gee", base_layer_name, zoom, tile_x, tile_y)
                                                    return Response(content=tile_data, media_type="image/png")
                                                except Exception as e:
                                                    logger.warning(f"Error generating tile for {base_layer_name}: {e}")
                                                    
                                            # Fallback: return a colored tile indicating the layer type
                                            if 'ndvi' in base_layer_name.lower():
                                                return Response(content=create_colored_tile(0, 150, 0, 255), media_type="image/png")
                                            elif 'evi' in base_layer_name.lower():
                                                return Response(content=create_colored_tile(0, 100, 0, 255), media_type="image/png")
                                            elif 'ndwi' in base_layer_name.lower():
                                                return Response(content=create_colored_tile(0, 0, 150, 255), media_type="image/png")
                                            else:
                                                return Response(content=create_colored_tile(100, 100, 100, 255), media_type="image/png")
                    except Exception as e:
                        logger.warning(f"Error processing registered layer {layer_name}: {e}")
                
                # Fallback for non-registered layers
                bbox_parts = bbox.split(',')
                if len(bbox_parts) == 4:
                    minx, miny, maxx, maxy = map(float, bbox_parts)
                    import math
                    zoom = max(0, min(18, int(math.log2(20037508.34 * 2 / (maxx - minx)))))
                    tile_x = int((minx + 20037508.34) / (40075016.68 / (2.0 ** zoom)))
                    tile_y = int((20037508.34 - maxy) / (40075016.68 / (2.0 ** zoom)))
                    
                    try:
                        tile_data = await generate_gee_tile("gee", layer_name, zoom, tile_x, tile_y)
                        return Response(content=tile_data, media_type="image/png")
                    except Exception as e:
                        logger.warning(f"Error generating tile for {layer_name}: {e}")
            
            # Final fallback: return a simple colored tile
            return Response(content=create_colored_tile(128, 128, 128, 255), media_type="image/png")
        
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported request: {request}")
        
    except Exception as e:
        logger.error(f"Error in WMS service: {e}")
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
        
        # Store in Redis
        cache_key = f"project:{project_id}"
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

async def generate_gee_tile(project_id: str, layer: str, z: int, x: int, y: int, 
                          start_date: Optional[str] = None, end_date: Optional[str] = None) -> bytes:
    """
    Generate a GEE tile for the given parameters
    """
    try:
        logger.info(f"Generating tile for project={project_id}, layer={layer}, z={z}, x={x}, y={y}")
        
        # Try to get the actual GEE tile URL from registered projects
        project_keys = redis_client.keys("project:*")
        
        for project_key in project_keys:
            project_data = redis_client.get(project_key)
            if project_data:
                project_info = json.loads(project_data)
                layers_info = project_info.get('layers', {})
                
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
                                    return response.content
                                else:
                                    logger.warning(f"GEE tile request failed: {response.status_code}")
                        except Exception as e:
                            logger.warning(f"Error fetching GEE tile: {e}")
        
        # Fallback: return a colored tile based on layer type
        logger.info(f"Using fallback colored tile for layer: {layer}")
        
        if layer == "ndvi":
            return create_colored_tile(0, 150, 0, 255)  # Green for NDVI
        elif layer == "evi":
            return create_colored_tile(0, 100, 0, 255)  # Dark green for EVI
        elif layer == "ndwi":
            return create_colored_tile(0, 0, 150, 255)  # Blue for NDWI
        elif layer == "true_color":
            return create_colored_tile(100, 100, 100, 255)  # Gray for true color
        elif layer == "false_color":
            return create_colored_tile(150, 100, 50, 255)  # Brown for false color
        elif layer == "FCD1_1":
            return create_colored_tile(0, 100, 0, 255)  # Green
        elif layer == "FCD2_1":
            return create_colored_tile(0, 80, 0, 255)   # Dark green
        elif layer == "image_mosaick":
            return create_colored_tile(0, 0, 255, 255)  # Blue
        elif layer == "avi_image":
            return create_colored_tile(255, 0, 0, 255)  # Red
        else:
            # Default gray tile
            return create_colored_tile(128, 128, 128, 255)  # Gray
        
    except Exception as e:
        logger.error(f"Error in generate_gee_tile: {e}")
        # Return a transparent tile on error
        return create_colored_tile(0, 0, 0, 0)  # Transparent

def create_colored_tile(r: int, g: int, b: int, a: int) -> bytes:
    """
    Create a simple colored PNG tile
    """
    # Simple 256x256 PNG with solid color
    # This is a minimal PNG structure
    import struct
    
    # PNG signature
    png_signature = b'\x89PNG\r\n\x1a\n'
    
    # IHDR chunk
    ihdr_data = struct.pack('>IIBBBBB', 256, 256, 8, 6, 0, 0, 0)  # 256x256, RGBA
    ihdr_crc = struct.pack('>I', 0x0a1a0a0d)  # CRC for IHDR
    ihdr_chunk = b'IHDR' + ihdr_data + ihdr_crc
    
    # IDAT chunk (simplified - just solid color)
    # For a real implementation, you'd create proper PNG data
    idat_data = b'\x78\x9c\x63\x00\x01\x00\x00\x05\x00\x01\x0d\x0a\x2d\xb4'
    idat_crc = struct.pack('>I', 0x00000000)  # CRC for IDAT
    idat_chunk = b'IDAT' + idat_data + idat_crc
    
    # IEND chunk
    iend_chunk = b'IEND\xaeB`\x82'
    
    return png_signature + ihdr_chunk + idat_chunk + iend_chunk

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
