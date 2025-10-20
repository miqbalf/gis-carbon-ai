"""
Django client for communicating with FastAPI GEE service
"""
import requests
import json
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

class FastAPIGEEClient:
    """
    Client for communicating with FastAPI GEE service
    """
    
    def __init__(self):
        self.base_url = getattr(settings, 'FASTAPI_GEE_URL', 'http://fastapi:8000')
        self.timeout = 300  # 5 minutes timeout for GEE processing
    
    def process_gee_analysis(self, project_id, analysis_type, parameters):
        """
        Send GEE analysis request to FastAPI service
        
        Args:
            project_id (str): Project identifier
            analysis_type (str): Type of analysis (fcd, hansen, classification, area_calc)
            parameters (dict): Analysis parameters
            
        Returns:
            dict: Analysis results
        """
        try:
            url = f"{self.base_url}/process-gee-analysis"
            payload = {
                "project_id": project_id,
                "analysis_type": analysis_type,
                "parameters": parameters
            }
            
            logger.info(f"Sending GEE analysis request to FastAPI: {url}")
            logger.info(f"Payload: {payload}")
            
            response = requests.post(
                url,
                json=payload,
                timeout=self.timeout,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"GEE analysis completed successfully for project {project_id}")
                return result
            else:
                logger.error(f"FastAPI returned error: {response.status_code} - {response.text}")
                raise Exception(f"FastAPI error: {response.status_code} - {response.text}")
                
        except requests.exceptions.Timeout:
            logger.error(f"Timeout waiting for GEE analysis for project {project_id}")
            raise Exception("GEE analysis timeout - processing took too long")
        except requests.exceptions.ConnectionError:
            logger.error(f"Could not connect to FastAPI service at {self.base_url}")
            raise Exception("FastAPI service unavailable")
        except Exception as e:
            logger.error(f"Error calling FastAPI: {str(e)}")
            raise Exception(f"FastAPI communication error: {str(e)}")
    
    def get_project_layers(self, project_id):
        """
        Get available layers for a project from FastAPI
        
        Args:
            project_id (str): Project identifier
            
        Returns:
            dict: Available layers
        """
        try:
            url = f"{self.base_url}/layers/{project_id}"
            
            response = requests.get(url, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"FastAPI returned error: {response.status_code} - {response.text}")
                raise Exception(f"FastAPI error: {response.status_code} - {response.text}")
                
        except Exception as e:
            logger.error(f"Error getting project layers: {str(e)}")
            raise Exception(f"FastAPI communication error: {str(e)}")
    
    def get_tile_url(self, project_id, layer, z, x, y, start_date=None, end_date=None):
        """
        Get tile URL from FastAPI service
        
        Args:
            project_id (str): Project identifier
            layer (str): Layer name
            z, x, y (int): Tile coordinates
            start_date, end_date (str): Date range (optional)
            
        Returns:
            str: Tile URL
        """
        try:
            url = f"{self.base_url}/tiles/{project_id}/{layer}/{z}/{x}/{y}"
            
            params = {}
            if start_date:
                params['start_date'] = start_date
            if end_date:
                params['end_date'] = end_date
            
            response = requests.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                # Return the tile URL
                return url
            else:
                logger.error(f"FastAPI returned error: {response.status_code} - {response.text}")
                raise Exception(f"FastAPI error: {response.status_code} - {response.text}")
                
        except Exception as e:
            logger.error(f"Error getting tile URL: {str(e)}")
            raise Exception(f"FastAPI communication error: {str(e)}")

# Global instance
fastapi_gee_client = FastAPIGEEClient()
