# 🔐 MapStore Centralized Authentication Architecture

## 🎯 **Authentication Flow Overview**

```
User → MapStore Login → JWT Token → All Services
```

### **User Perspective:**
1. User opens MapStore: `http://localhost:8082/mapstore`
2. User logs in through MapStore's built-in authentication
3. MapStore generates JWT token
4. All services (Django, GeoServer, FastAPI) validate this token
5. User gets access to authenticated layers across all services

## 🏗️ **Architecture Design**

```
┌─────────────────────────────────────────────────────────────┐
│                    MapStore (Auth Hub)                      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │   Login Form    │  │  JWT Generator  │  │ Auth Plugin │ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
└─────────────────────┬───────────────────────────────────────┘
                      │ JWT Token
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                All Services (Token Validators)              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────┐ │
│  │   Django    │  │  GeoServer  │  │   FastAPI   │  │ ... │ │
│  │   REST API  │  │   WMS/WFS   │  │ Tile Service│  │     │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────┘ │
└─────────────────────────────────────────────────────────────┘
```

## 🔧 **Implementation Strategy**

### **1. MapStore Authentication Configuration**

#### **MapStore localConfig.json:**
```json
{
  "authentication": {
    "type": "local",
    "loginForm": {
      "enabled": true,
      "title": "GIS Carbon AI Login"
    },
    "jwt": {
      "secret": "your-jwt-secret-key",
      "expiration": 86400,
      "algorithm": "HS256"
    }
  },
  "services": {
    "django": {
      "url": "http://localhost:8000",
      "authEndpoint": "/api/auth/validate-token/"
    },
    "geoserver": {
      "url": "http://localhost:8080/geoserver",
      "authEndpoint": "/rest/security/validate-token"
    },
    "fastapi": {
      "url": "http://localhost:8001",
      "authEndpoint": "/auth/validate-token"
    }
  }
}
```

### **2. Django Authentication Integration**

#### **Django JWT Validation:**
```python
# backend/sv_carbon_removal/api/auth/jwt_validator.py
import jwt
from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

class MapStoreJWTAuthentication(BaseAuthentication):
    def authenticate(self, request):
        token = self.get_token_from_request(request)
        if not token:
            return None
        
        try:
            payload = jwt.decode(
                token, 
                settings.MAPSTORE_JWT_SECRET, 
                algorithms=['HS256']
            )
            user_id = payload.get('user_id')
            username = payload.get('username')
            
            # Get or create user from Django
            from django.contrib.auth.models import User
            user, created = User.objects.get_or_create(
                username=username,
                defaults={'id': user_id}
            )
            
            return (user, token)
            
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed('Token expired')
        except jwt.JWTError:
            raise AuthenticationFailed('Invalid token')
    
    def get_token_from_request(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        if auth_header and auth_header.startswith('Bearer '):
            return auth_header.split(' ')[1]
        return None
```

### **3. GeoServer Authentication Integration**

#### **GeoServer JWT Filter:**
```java
// GeoServer JWT Authentication Filter
public class MapStoreJWTAuthenticationFilter implements AuthenticationFilter {
    
    private String jwtSecret = "your-jwt-secret-key";
    
    @Override
    public boolean authenticate(HttpServletRequest request, 
                              HttpServletResponse response) {
        String token = extractToken(request);
        if (token == null) {
            return false;
        }
        
        try {
            Claims claims = Jwts.parser()
                .setSigningKey(jwtSecret)
                .parseClaimsJws(token)
                .getBody();
            
            String username = claims.getSubject();
            // Create GeoServer user session
            SecurityContextHolder.getContext()
                .setAuthentication(new UsernamePasswordAuthenticationToken(
                    username, null, getAuthorities(username)
                ));
            
            return true;
        } catch (JwtException e) {
            return false;
        }
    }
    
    private String extractToken(HttpServletRequest request) {
        String authHeader = request.getHeader("Authorization");
        if (authHeader != null && authHeader.startsWith("Bearer ")) {
            return authHeader.substring(7);
        }
        return null;
    }
}
```

### **4. FastAPI Authentication Integration**

#### **FastAPI JWT Middleware:**
```python
# fastapi-gee-service/middleware/mapstore_auth.py
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer
import jwt
import os

security = HTTPBearer()

class MapStoreJWTMiddleware:
    def __init__(self, app):
        self.app = app
        self.jwt_secret = os.getenv('MAPSTORE_JWT_SECRET', 'your-jwt-secret-key')
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            request = Request(scope, receive)
            token = self.extract_token(request)
            
            if token and not self.validate_token(token):
                response = HTTPException(status_code=401, detail="Invalid token")
                # Handle unauthorized access
                
        await self.app(scope, receive, send)
    
    def extract_token(self, request: Request):
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            return auth_header.split(" ")[1]
        return None
    
    def validate_token(self, token: str) -> bool:
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
            return True
        except jwt.ExpiredSignatureError:
            return False
        except jwt.JWTError:
            return False
```

## 🔄 **Unified Authentication Flow**

### **Step 1: User Login in MapStore**
```javascript
// MapStore Login Component
const loginUser = async (username, password) => {
    try {
        // Validate credentials with Django
        const response = await fetch('http://localhost:8000/api/auth/login/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        
        if (response.ok) {
            const data = await response.json();
            
            // Generate JWT token in MapStore
            const token = generateJWTToken(data.user);
            
            // Store token in MapStore session
            localStorage.setItem('mapstore_token', token);
            
            // Update all service configurations with token
            updateServiceConfigurations(token);
            
            return { success: true, token };
        }
    } catch (error) {
        return { success: false, error: error.message };
    }
};
```

### **Step 2: Token Propagation to All Services**
```javascript
// MapStore Service Configuration Update
const updateServiceConfigurations = (token) => {
    // Update Django service
    window.ConfigUtils.setConfigProp('services.django.authToken', token);
    
    // Update GeoServer service
    window.ConfigUtils.setConfigProp('services.geoserver.authToken', token);
    
    // Update FastAPI service
    window.ConfigUtils.setConfigProp('services.fastapi.authToken', token);
    
    // Refresh layer access
    refreshLayerAccess();
};
```

### **Step 3: Layer Access Control**
```javascript
// MapStore Layer Access Control
const refreshLayerAccess = async () => {
    const token = localStorage.getItem('mapstore_token');
    
    // Get accessible layers from FastAPI
    const response = await fetch('http://localhost:8001/layers/accessible', {
        headers: { 'Authorization': `Bearer ${token}` }
    });
    
    const accessibleLayers = await response.json();
    
    // Update MapStore catalog with accessible layers
    updateCatalogServices(accessibleLayers);
};
```

## 🛡️ **Security Implementation**

### **1. JWT Token Structure**
```json
{
  "user_id": "123",
  "username": "user@example.com",
  "roles": ["user", "analyst"],
  "permissions": {
    "geoserver": ["read", "write"],
    "gee": ["read", "analyze"],
    "django": ["read", "write", "admin"]
  },
  "exp": 1640995200,
  "iat": 1640908800
}
```

### **2. Service-Specific Permissions**
```python
# Permission checking in each service
def check_permission(user_permissions, service, action):
    service_perms = user_permissions.get(service, [])
    return action in service_perms

# Example usage
if check_permission(user_permissions, 'gee', 'analyze'):
    # Allow GEE analysis
    pass
else:
    # Deny access
    raise PermissionError("Insufficient permissions for GEE analysis")
```

## 📋 **Implementation Checklist**

### **MapStore Configuration:**
- [ ] Configure JWT authentication in localConfig.json
- [ ] Set up login form customization
- [ ] Implement token storage and management
- [ ] Create service configuration updates

### **Django Integration:**
- [ ] Implement JWT validation middleware
- [ ] Update authentication classes
- [ ] Create token validation endpoint
- [ ] Update user permissions system

### **GeoServer Integration:**
- [ ] Implement JWT authentication filter
- [ ] Configure security rules
- [ ] Update WMS/WFS authentication
- [ ] Test layer access control

### **FastAPI Integration:**
- [ ] Implement JWT middleware
- [ ] Update authentication dependencies
- [ ] Create token validation endpoint
- [ ] Update layer access control

### **Testing:**
- [ ] Test login flow in MapStore
- [ ] Verify token propagation
- [ ] Test layer access control
- [ ] Verify logout functionality

## 🎯 **Benefits of This Approach**

1. **Single Sign-On**: User logs in once in MapStore
2. **Unified Experience**: Consistent authentication across all services
3. **Centralized Management**: All auth logic in MapStore
4. **Secure**: JWT tokens with proper validation
5. **Scalable**: Easy to add new services
6. **User-Friendly**: Familiar MapStore login interface

This approach ensures that users have a seamless experience where they log in once in MapStore and get access to all authenticated layers across Django, GeoServer, and FastAPI services.
