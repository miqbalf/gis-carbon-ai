from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView

from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import UserSerializer, UserRegistrationSerializer

from people.models import User

from django.contrib.auth import authenticate, login, logout

class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

## THIS SET OF LOGIN LOGOUT THAT PREVIOUSLY USE WITH BASIC AUTH AS WELL
# @api_view(['POST'])
# @permission_classes([AllowAny])
# def login_user(request):
#     email = request.data.get('email')
#     password = request.data.get('password')

#     user = authenticate(email=email, password=password)

#     if user:
#         login(request, user)
#         refresh = RefreshToken.for_user(user)

#         # if user.is_superuser:
#         #     groups.append("admin")

        
#         return Response({
#             "sub": str(user.id),
#             'access': str(refresh.access_token),
#             'refresh': str(refresh),
#         }, status=status.HTTP_200_OK)
#     return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

# # example with using logout(request) from django auth
# @api_view(['POST'])
# def logout_user(request):
#     logout(request)
#     return Response({"message": "User logged out successfully."}, status=status.HTTP_200_OK)

# #this one for logout from token
class LogoutView(APIView):
     permission_classes = (IsAuthenticated,)
     def post(self, request):
          
          try:
               refresh_token = request.data["refresh_token"]
               token = RefreshToken(refresh_token)
               token.blacklist()
               return Response(status=status.HTTP_205_RESET_CONTENT)
          except Exception as e:
               return Response(status=status.HTTP_400_BAD_REQUEST)

## TRY WITH existing auth login django and implement registration process
@api_view(['POST'])
@permission_classes([AllowAny])
def register_user(request):
    if request.method == 'POST':
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            # Create the user account using the serializer data
            serializer.save()
            return Response({"message": "User registered successfully."}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    return Response({"message": "Invalid request method."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

