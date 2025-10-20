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
    Get available layers for a project
    """
    try:
        # This would typically query your database for project configuration
        # For now, return a default set of layers
        layers = {
            "FCD1_1": {"name": "Forest Cover Density 1-1", "description": "Primary FCD layer"},
            "FCD2_1": {"name": "Forest Cover Density 2-1", "description": "Secondary FCD layer"},
            "image_mosaick": {"name": "Image Mosaic", "description": "Satellite image mosaic"},
            "avi_image": {"name": "AVI Image", "description": "Advanced Vegetation Index"},
        }
        
        return {"project_id": project_id, "layers": layers}
        
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
        
    except Exception as e:
        logger.error(f"Error processing GEE analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

async def generate_gee_tile(project_id: str, layer: str, z: int, x: int, y: int, 
                          start_date: Optional[str] = None, end_date: Optional[str] = None) -> bytes:
    """
    Generate a GEE tile for the given parameters
    """
    try:
        # This is a simplified version - you would integrate your existing GEE logic here
        # For now, return a placeholder tile
        
        # Example GEE processing (you would adapt this from your existing code)
        if layer == "FCD1_1":
            # Use your existing FCD calculation logic
            dataset = (ee.ImageCollection('MODIS/006/MOD13Q1')
                      .filter(ee.Filter.date('2019-07-01', '2019-11-30'))
                      .first())
            image = dataset.select('NDVI')
        else:
            # Default to a simple NDVI image
            image = ee.Image('MODIS/006/MOD13Q1/2019_07_01').select('NDVI')
        
        # Get map ID for tile generation
        vis_params = {
            'min': 0,
            'max': 9000,
            'palette': ['FE8374', 'C0E5DE', '3A837C', '034B48']
        }
        
        map_id_dict = image.getMapId(vis_params)
        tile_url = map_id_dict['tile_fetcher'].url_format
        
        # In a real implementation, you would fetch the actual tile from GEE
        # For now, return a placeholder
        import requests
        response = requests.get(tile_url.format(z=z, x=x, y=y))
        
        if response.status_code == 200:
            return response.content
        else:
            # Return a transparent tile if GEE tile is not available
            return b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x01\x00\x00\x00\x01\x00\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xdb\x00\x00\x00\x00IEND\xaeB`\x82'
        
    except Exception as e:
        logger.error(f"Error in generate_gee_tile: {e}")
        # Return a transparent tile on error
        return b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x01\x00\x00\x00\x01\x00\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xdb\x00\x00\x00\x00IEND\xaeB`\x82'

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
