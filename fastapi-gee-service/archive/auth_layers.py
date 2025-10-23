"""
Authentication and Layer Management for FastAPI GEE Service
Handles login vs non-login layers for both GeoServer and GEE results
"""

from fastapi import HTTPException, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
import redis
import json
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
import os

# Initialize Redis for session management
redis_client = redis.Redis(host='redis', port=6379, db=2, decode_responses=True)

# JWT Secret (should be in environment variables)
JWT_SECRET = os.getenv('JWT_SECRET', 'your-secret-key')
JWT_ALGORITHM = 'HS256'

# Security scheme
security = HTTPBearer()

class LayerAuthManager:
    """Manages authentication for different layer types"""
    
    def __init__(self):
        self.public_layers = {
            'geoserver': [
                'sample_geometries',  # Public GeoServer layers
                'public_boundaries'
            ],
            'gee': [
                'public_ndvi',        # Public GEE layers
                'public_landcover'
            ]
        }
        
        self.authenticated_layers = {
            'geoserver': [
                'private_analysis',   # Private GeoServer layers
                'user_projects'
            ],
            'gee': [
                'fcd_analysis',       # Private GEE analysis
                'carbon_calculation',
                'user_custom_analysis'
            ]
        }
    
    def is_public_layer(self, layer_type: str, layer_name: str) -> bool:
        """Check if a layer is public (no authentication required)"""
        return layer_name in self.public_layers.get(layer_type, [])
    
    def is_authenticated_layer(self, layer_type: str, layer_name: str) -> bool:
        """Check if a layer requires authentication"""
        return layer_name in self.authenticated_layers.get(layer_type, [])
    
    def get_user_layers(self, user_id: str, layer_type: str) -> List[str]:
        """Get user-specific layers"""
        user_layers_key = f"user_layers:{user_id}:{layer_type}"
        return redis_client.lrange(user_layers_key, 0, -1) or []
    
    def add_user_layer(self, user_id: str, layer_type: str, layer_name: str):
        """Add a layer to user's accessible layers"""
        user_layers_key = f"user_layers:{user_id}:{layer_type}"
        redis_client.lpush(user_layers_key, layer_name)
        redis_client.expire(user_layers_key, 86400)  # 24 hours

class JWTAuthManager:
    """JWT-based authentication manager"""
    
    @staticmethod
    def create_token(user_id: str, username: str, expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT token for user"""
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(hours=24)
        
        payload = {
            'user_id': user_id,
            'username': username,
            'exp': expire,
            'iat': datetime.utcnow()
        }
        
        return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    @staticmethod
    def verify_token(token: str) -> Dict[str, Any]:
        """Verify JWT token and return user info"""
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.JWTError:
            raise HTTPException(status_code=401, detail="Invalid token")
    
    @staticmethod
    def get_user_from_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
        """Extract user info from JWT token"""
        token = credentials.credentials
        return JWTAuthManager.verify_token(token)

class LayerAccessController:
    """Controls access to layers based on authentication"""
    
    def __init__(self):
        self.auth_manager = LayerAuthManager()
        self.jwt_manager = JWTAuthManager()
    
    async def check_layer_access(self, layer_type: str, layer_name: str, 
                               user: Optional[Dict[str, Any]] = None) -> bool:
        """Check if user has access to a specific layer"""
        
        # Public layers - no authentication required
        if self.auth_manager.is_public_layer(layer_type, layer_name):
            return True
        
        # Authenticated layers - require valid user
        if self.auth_manager.is_authenticated_layer(layer_type, layer_name):
            if not user:
                return False
            
            # Check if user has access to this specific layer
            user_layers = self.auth_manager.get_user_layers(user['user_id'], layer_type)
            return layer_name in user_layers or user.get('is_admin', False)
        
        # Default: require authentication for unknown layers
        return user is not None
    
    async def get_accessible_layers(self, layer_type: str, user: Optional[Dict[str, Any]] = None) -> List[str]:
        """Get list of layers accessible to user"""
        accessible_layers = []
        
        # Add public layers
        accessible_layers.extend(self.auth_manager.public_layers.get(layer_type, []))
        
        # Add authenticated layers if user is logged in
        if user:
            user_layers = self.auth_manager.get_user_layers(user['user_id'], layer_type)
            accessible_layers.extend(user_layers)
            
            # Add all authenticated layers for admin users
            if user.get('is_admin', False):
                accessible_layers.extend(self.auth_manager.authenticated_layers.get(layer_type, []))
        
        return list(set(accessible_layers))  # Remove duplicates

# Global instances
layer_auth_manager = LayerAuthManager()
jwt_auth_manager = JWTAuthManager()
layer_access_controller = LayerAccessController()

# Dependency functions for FastAPI
async def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[Dict[str, Any]]:
    """Get current user from JWT token (optional)"""
    if not credentials:
        return None
    
    try:
        return jwt_auth_manager.verify_token(credentials.credentials)
    except HTTPException:
        return None

async def require_auth(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Require authentication (mandatory)"""
    return jwt_auth_manager.verify_token(credentials.credentials)

async def check_layer_permission(layer_type: str, layer_name: str, 
                               user: Optional[Dict[str, Any]] = Depends(get_current_user)) -> bool:
    """Check if user has permission to access layer"""
    has_access = await layer_access_controller.check_layer_access(layer_type, layer_name, user)
    if not has_access:
        raise HTTPException(
            status_code=403, 
            detail=f"Access denied to layer {layer_name} of type {layer_type}"
        )
    return True
