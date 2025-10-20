"""
Django Unified Authentication Integration
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.models import Group
from rest_framework_simplejwt.tokens import RefreshToken
import json
import logging
import sys
import os

# Add auth service to path (optional)
if '/app/auth' not in sys.path:
    sys.path.append('/app/auth')
auth_service = None
UserRole = None
authenticate_user = None
get_user_by_token = None
try:
    from unified_auth_service import auth_service as _auth_service, UserRole as _UserRole, authenticate_user as _authenticate_user, get_user_by_token as _get_user_by_token
    auth_service = _auth_service
    UserRole = _UserRole
    authenticate_user = _authenticate_user
    get_user_by_token = _get_user_by_token
except Exception:
    # unified_auth_service not available; endpoints will degrade gracefully
    pass

logger = logging.getLogger(__name__)

class UnifiedLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        # Authenticate using unified auth service if available
        if authenticate_user is None:
            logger.warning("Unified auth service not available")
            return Response({'message': 'Unified auth unavailable'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        user = authenticate_user(username, password)
        
        if user:
            # Create Django user if doesn't exist (custom User uses email as identifier)
            DjangoUser = get_user_model()
            django_user, created = DjangoUser.objects.get_or_create(
                email=user.email,
                defaults={
                    'name': getattr(user, 'username', '') or getattr(user, 'name', ''),
                    'is_active': getattr(user, 'is_active', True)
                }
            )
            
            # Update user groups based on roles
            django_user.groups.clear()
            for role in user.roles:
                group, _ = Group.objects.get_or_create(name=role.value)
                django_user.groups.add(group)
            
            # Generate unified token
            unified_token = auth_service.generate_token(user)
            
            # Generate Django JWT token
            refresh = RefreshToken.for_user(django_user)
            
            response_data = {
                'unified_token': unified_token,
                'django_token': str(refresh.access_token),
                'refresh_token': str(refresh),
                'user': {
                    'name': getattr(user, 'name', None) or getattr(user, 'username', None),
                    'email': user.email,
                    'roles': [role.value for role in user.roles],
                    'permissions': user.permissions
                },
                'message': 'Login successful'
            }
            
            logger.info(f"User {username} logged in successfully via unified auth")
            return Response(response_data, status=status.HTTP_200_OK)
        else:
            logger.warning(f"Failed login attempt for user: {username}")
            return Response({'message': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

class UnifiedUserView(APIView):
    permission_classes = [AllowAny]  # Token will be validated by middleware

    def get(self, request):
        # Check for unified token first
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer ') and get_user_by_token is not None:
            token = auth_header.split(' ')[1]
            user = get_user_by_token(token)
            
            if user:
                return Response({
                    'username': user.username,
                    'email': user.email,
                    'roles': [role.value for role in user.roles],
                    'permissions': user.permissions
                }, status=status.HTTP_200_OK)
        
        # Fallback to Django authentication
        if request.user.is_authenticated:
            roles = [group.name for group in request.user.groups.all()]
            return Response({
                'name': getattr(request.user, 'name', ''),
                'email': getattr(request.user, 'email', ''),
                'roles': roles,
                'permissions': {}  # Would need to map Django permissions
            }, status=status.HTTP_200_OK)
        
        return Response({'message': 'Not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)

class UnifiedLogoutView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            logout(request)
            logger.info("User logged out successfully via unified auth")
            return Response({'message': 'Logout successful'}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error during logout: {e}")
            return Response({'message': 'Logout failed'}, status=status.HTTP_400_BAD_REQUEST)

class RolePermissionView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get user's roles and permissions"""
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            user = get_user_by_token(token)
            
            if user:
                return Response({
                    'roles': [role.value for role in user.roles],
                    'permissions': user.permissions,
                    'service_roles': auth_service.get_service_roles(user, 'all') if auth_service else {}
                }, status=status.HTTP_200_OK)
        
        return Response({'message': 'Invalid token'}, status=status.HTTP_401_UNAUTHORIZED)

class GeoServerRolesXMLView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, username):
        shared_secret = os.environ.get('GEOSERVER_ROLE_SHARED_SECRET', '')
        if not shared_secret:
            return Response('<roles/>', status=200, content_type='application/xml')

        token = request.headers.get('X-Role-Secret', '') or request.GET.get('secret', '')
        if token != shared_secret:
            return Response('<roles/>', status=200, content_type='application/xml')

        DjangoUser = get_user_model()
        try:
            user = DjangoUser.objects.get(name=username)
        except DjangoUser.DoesNotExist:
            # fallback by email if username looks like email
            try:
                user = DjangoUser.objects.get(email=username)
            except DjangoUser.DoesNotExist:
                return Response('<roles/>', status=200, content_type='application/xml')

        roles = [group.name for group in user.groups.all()]
        # Always include ROLE_AUTHENTICATED for active users
        if user.is_active and 'ROLE_AUTHENTICATED' not in roles:
            roles.append('ROLE_AUTHENTICATED')

        xml_roles = ''.join([f'<role>{r}</role>' for r in roles])
        xml = f'<roles>{xml_roles}</roles>'
        return Response(xml, status=200, content_type='application/xml')
