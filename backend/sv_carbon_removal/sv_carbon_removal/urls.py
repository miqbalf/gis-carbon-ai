"""
URL configuration for sv_carbon_removal project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include, re_path

from api.urls import router

from django.conf import settings
from django.conf.urls.static import static

from rest_framework_simplejwt import views as jwt_views

from api.people.view_api import (
                                # login_user, 
                                 LogoutView, 
                                #  logout_user,
                                )

# from api.sv.view_api import (ListsatVerFiltered)
from api.sv.view_api import (satVerViewSet, FCDViewSet)
from health_views import health_check

urlpatterns = [
    path('', include(router.urls)),
    path('api/auth/', include('api.auth.urls')),
    path('health/', health_check, name='health'),
    path('admin/', admin.site.urls),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    # path('logout/', logout_user, name='logout'),
    path('logout/',LogoutView.as_view(), name ='logout'),
    # path('login/',login_user, name='login'),

    #adding jwt auth
    path('token/', 
          jwt_views.TokenObtainPairView.as_view(), 
          name ='token_obtain_pair'),
    path('token/refresh/', 
          jwt_views.TokenRefreshView.as_view(), 
          name ='token_refresh'),

    path('run-sv/', FCDViewSet.as_view(), 
          name='run-satver'),

    # path('gee/', include('fcd_gee.urls', namespace='fcd_gee')),

    # path('projects_sv_conf/<str:project_carbon>', ListsatVerFiltered.as_view(), name='carbon-project-sv'),
    # re_path('^projects_sv_conf/(?P<project_carbon>.+)/$', ListsatVerFiltered.as_view()),
    
    # Default delete based on 'id'
    path('projects_sv_conf/<int:pk>/', satVerViewSet.as_view({'delete': 'destroy'}), name='sv_conf_delete-id'),
    
    path('projects_sv_conf/delete/<str:label>', satVerViewSet.as_view({'delete': 'delete_by_label'
                                                                              }), name='sv_conf_delete-label'),
    
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)