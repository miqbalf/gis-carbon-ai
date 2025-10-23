"""
FastAPI Unified Authentication Middleware
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from starlette.types import ASGIApp
import jwt
import logging
import os
import sys
from typing import Optional, Dict, Any

# Add auth service to path
sys.path.append('/app/auth')
from unified_auth_service import auth_service, User, UserRole, get_user_by_token

logger = logging.getLogger(__name__)

class UnifiedAuthUser:
    def __init__(self, username: str, roles: list, permissions: dict):
        self.username = username
        self.roles = roles
        self.permissions = permissions

    def is_authenticated(self) -> bool:
        return self.username != "anonymous"

    def is_admin(self) -> bool:
        return "ROLE_ADMIN" in self.roles

    def has_role(self, role: str) -> bool:
        return role.upper() in [r.upper() for r in self.roles]

    def has_permission(self, service: str, permission: str) -> bool:
        service_perms = self.permissions.get(service, [])
        return "*" in service_perms or permission in service_perms

class UnifiedAuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        # Skip authentication for public endpoints
        if request.method == "OPTIONS" or self._is_public_path(request.url.path):
            request.state.user = UnifiedAuthUser(
                username="anonymous", 
                roles=["ROLE_ANONYMOUS"], 
                permissions={"geoserver": [], "django": [], "fastapi": [], "mapstore": []}
            )
            return await call_next(request)

        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization")
        token = None
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

        user = None
        if token:
            try:
                # Verify token using unified auth service
                unified_user = get_user_by_token(token)
                if unified_user:
                    user = UnifiedAuthUser(
                        username=unified_user.username,
                        roles=[role.value for role in unified_user.roles],
                        permissions=unified_user.permissions
                    )
                    logger.debug(f"Authenticated user: {user.username}, Roles: {user.roles}")
            except Exception as e:
                logger.warning(f"Token verification error: {e}")
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Invalid token", "code": "invalid_token"}
                )
        
        if user:
            request.state.user = user
        else:
            # Assign anonymous user
            request.state.user = UnifiedAuthUser(
                username="anonymous", 
                roles=["ROLE_ANONYMOUS"], 
                permissions={"geoserver": [], "django": [], "fastapi": [], "mapstore": []}
            )
            logger.debug("Assigned anonymous user to request state.")

        response = await call_next(request)
        return response

    def _is_public_path(self, path: str) -> bool:
        """Define paths that do not require authentication"""
        public_paths = [
            "/health",
            "/",
            "/token",
            "/public/tiles/",
            "/docs", "/redoc",
            "/openapi.json"
        ]
        for p in public_paths:
            if path.startswith(p):
                return True
        return False

# Dependency functions for FastAPI
async def get_current_user(request: Request) -> UnifiedAuthUser:
    """Get current authenticated user"""
    return request.state.user

async def get_current_authenticated_user(request: Request) -> UnifiedAuthUser:
    """Get current authenticated user (non-anonymous)"""
    user = request.state.user
    if not user.is_authenticated():
        raise HTTPException(status_code=401, detail="Authentication required")
    return user

async def get_current_admin_user(request: Request) -> UnifiedAuthUser:
    """Get current admin user"""
    user = request.state.user
    if not user.is_admin():
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

async def require_permission(service: str, permission: str):
    """Dependency to require specific permission"""
    async def permission_checker(request: Request):
        user = request.state.user
        if not user.has_permission(service, permission):
            raise HTTPException(
                status_code=403, 
                detail=f"Permission required: {service}.{permission}"
            )
        return user
    return permission_checker

# Service-specific permission checkers
async def require_geoserver_permission(permission: str):
    return await require_permission("geoserver", permission)

async def require_fastapi_permission(permission: str):
    return await require_permission("fastapi", permission)

async def require_analysis_permission():
    return await require_permission("fastapi", "analysis_tiles_read")
