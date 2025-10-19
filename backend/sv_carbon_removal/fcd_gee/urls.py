from django.urls import path
from rest_framework_simplejwt import views as jwt_views

from .viewset import ( HomeView,gee_example, #LogoutView, login_user, logout_user, register_user,
                         )

from .views import home

app_name = 'fcd_gee'

urlpatterns = [
    #adding jwt auth
    
    path('' ,home.as_view()),
    path('url_tiles/', gee_example.as_view())
]