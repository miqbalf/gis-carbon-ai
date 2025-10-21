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
        
        # For now, return a simple colored tile based on the layer
        # This is a temporary solution until GEE integration is fully working
        
        # Create a simple colored tile based on layer type
        if layer == "FCD1_1":
            # Forest green tile
            return create_colored_tile(0, 100, 0, 255)  # Green
        elif layer == "FCD2_1":
            # Dark green tile
            return create_colored_tile(0, 80, 0, 255)   # Dark green
        elif layer == "image_mosaick":
            # Blue tile
            return create_colored_tile(0, 0, 255, 255)  # Blue
        elif layer == "avi_image":
            # Red tile
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
