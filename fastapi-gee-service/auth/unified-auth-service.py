"""
Unified Authentication Service for GIS Carbon AI
Handles authentication across GeoServer, Django, FastAPI, and MapStore
"""

import jwt
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class UserRole(Enum):
    ANONYMOUS = "ROLE_ANONYMOUS"
    AUTHENTICATED = "ROLE_AUTHENTICATED"
    ANALYST = "ROLE_ANALYST"
    ADMIN = "ROLE_ADMIN"

@dataclass
class User:
    username: str
    email: str
    roles: List[UserRole]
    permissions: Dict[str, List[str]]
    is_active: bool = True
    created_at: datetime = None

class UnifiedAuthService:
    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.token_expiry = timedelta(hours=24)
        
        # Load role configuration
        with open('/app/auth/unified-roles-config.json', 'r') as f:
            self.role_config = json.load(f)
    
    def create_user(self, username: str, email: str, roles: List[UserRole]) -> User:
        """Create a new user with specified roles"""
        permissions = self._calculate_permissions(roles)
        
        user = User(
            username=username,
            email=email,
            roles=roles,
            permissions=permissions,
            created_at=datetime.utcnow()
        )
        
        logger.info(f"Created user {username} with roles: {[role.value for role in roles]}")
        return user
    
    def _calculate_permissions(self, roles: List[UserRole]) -> Dict[str, List[str]]:
        """Calculate permissions based on user roles"""
        permissions = {
            "geoserver": [],
            "django": [],
            "fastapi": [],
            "mapstore": []
        }
        
        for role in roles:
            role_name = role.value
            role_config = next(
                (r for r in self.role_config["unified_roles"]["system_roles"] if r["name"] == role_name),
                None
            )
            
            if role_config:
                for service, perms in role_config["permissions"].items():
                    if perms == ["*"]:
                        permissions[service] = ["*"]
                    else:
                        permissions[service].extend(perms)
        
        return permissions
    
    def generate_token(self, user: User) -> str:
        """Generate JWT token for user"""
        payload = {
            "sub": user.username,
            "email": user.email,
            "roles": [role.value for role in user.roles],
            "permissions": user.permissions,
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + self.token_expiry
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        logger.info(f"Generated token for user {user.username}")
        return token
    
    def verify_token(self, token: str) -> Optional[User]:
        """Verify JWT token and return user"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            user = User(
                username=payload["sub"],
                email=payload["email"],
                roles=[UserRole(role) for role in payload["roles"]],
                permissions=payload["permissions"]
            )
            
            logger.info(f"Verified token for user {user.username}")
            return user
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None
    
    def check_permission(self, user: User, service: str, permission: str) -> bool:
        """Check if user has specific permission for a service"""
        if not user.is_active:
            return False
        
        service_perms = user.permissions.get(service, [])
        
        # Check for wildcard permission
        if "*" in service_perms:
            return True
        
        # Check for specific permission
        return permission in service_perms
    
    def get_service_roles(self, user: User, service: str) -> List[str]:
        """Get service-specific roles for a user"""
        unified_roles = [role.value for role in user.roles]
        service_mappings = self.role_config["service_mappings"].get(service, {})
        
        service_roles = []
        for unified_role in unified_roles:
            if unified_role in service_mappings:
                mapped_roles = service_mappings[unified_role].split(',')
                service_roles.extend(mapped_roles)
        
        return list(set(service_roles))  # Remove duplicates
    
    def create_service_token(self, user: User, service: str) -> str:
        """Create service-specific token with appropriate roles"""
        service_roles = self.get_service_roles(user, service)
        
        payload = {
            "sub": user.username,
            "email": user.email,
            "roles": service_roles,
            "service": service,
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + self.token_expiry
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        logger.info(f"Generated {service} token for user {user.username}")
        return token

# Global authentication service instance
auth_service = UnifiedAuthService(
    secret_key="gis-carbon-ai-unified-auth-secret-2024",
    algorithm="HS256"
)

# Predefined users for testing
TEST_USERS = {
    "anonymous": User(
        username="anonymous",
        email="anonymous@example.com",
        roles=[UserRole.ANONYMOUS],
        permissions=auth_service._calculate_permissions([UserRole.ANONYMOUS])
    ),
    "demo_user": User(
        username="demo_user",
        email="demo@example.com",
        roles=[UserRole.AUTHENTICATED],
        permissions=auth_service._calculate_permissions([UserRole.AUTHENTICATED])
    ),
    "analyst": User(
        username="analyst",
        email="analyst@example.com",
        roles=[UserRole.AUTHENTICATED, UserRole.ANALYST],
        permissions=auth_service._calculate_permissions([UserRole.AUTHENTICATED, UserRole.ANALYST])
    ),
    "admin": User(
        username="admin",
        email="admin@example.com",
        roles=[UserRole.ADMIN],
        permissions=auth_service._calculate_permissions([UserRole.ADMIN])
    )
}

def authenticate_user(username: str, password: str) -> Optional[User]:
    """Authenticate user with username/password"""
    # Simple password check (in production, use proper password hashing)
    if username in TEST_USERS and password == f"{username}123":
        return TEST_USERS[username]
    return None

def get_user_by_token(token: str) -> Optional[User]:
    """Get user by JWT token"""
    return auth_service.verify_token(token)
