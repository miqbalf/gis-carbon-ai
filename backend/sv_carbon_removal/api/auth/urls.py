"""
Unified Authentication URLs
"""

from django.urls import path
from . import unified_auth

urlpatterns = [
    # Unified authentication endpoints
    path('unified-login/', unified_auth.UnifiedLoginView.as_view(), name='unified-login'),
    path('unified-logout/', unified_auth.UnifiedLogoutView.as_view(), name='unified-logout'),
    path('unified-user/', unified_auth.UnifiedUserView.as_view(), name='unified-user'),
    path('role-permissions/', unified_auth.RolePermissionView.as_view(), name='role-permissions'),
    
    # Legacy endpoints (for backward compatibility)
    path('login/', unified_auth.UnifiedLoginView.as_view(), name='login'),
    path('logout/', unified_auth.UnifiedLogoutView.as_view(), name='logout'),
    path('user/', unified_auth.UnifiedUserView.as_view(), name='user'),
    # GeoServer role service (XML)
    path('geoserver/roles/<str:username>/', unified_auth.GeoServerRolesXMLView.as_view(), name='geoserver-roles'),
]
