'''
THIS IS ONLY FOR TESTING
'''

from people.models import User

from django.conf import settings

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated


from rest_framework.permissions import AllowAny

# from .serializers import GroupSerializer, UserSerializer, UserRegistrationSerializer

class HomeView(APIView):
    # permission_classes = (IsAuthenticated, )
    #authentication_classes=( SessionAuthentication, )
    permission_classes = [IsAuthenticated]
    def get(self, request):
        content = {'message': 'Welcome to the  \
                   Authentication page using React Js and Django!'}
        return Response(content)
    

#folium
import folium
from folium import plugins

import os

#gee
import ee

# Trigger the authentication flow. if you want to user json, please comment this
# ee.Authenticate()

service_account = 'iqbalpythonapi@bukit30project.iam.gserviceaccount.com'
credentials = ee.ServiceAccountCredentials(service_account, os.path.join(os.path.dirname(__file__),'bukit30project-4d92e5b46ea7.json'))

# Initialize the library.
# ee.Initialize(project='bukit30project')
ee.Initialize(credentials)

import geemap

# viewSet url gee
class gee_example(APIView):
    permission_classes = [AllowAny, ]
    
    def get(self, request):
        #select the Dataset Here's used the MODIS data
        dataset = (ee.ImageCollection('MODIS/006/MOD13Q1')
                    .filter(ee.Filter.date('2019-07-01', '2019-11-30'))
                    .first())
        modisndvi = dataset.select('NDVI')

        #Styling 
        vis_paramsNDVI = {
            'min': 0,
            'max': 9000,
            'palette': [ 'FE8374', 'C0E5DE', '3A837C','034B48',]}

        
        #add the map to the the folium map
        map_id_dict = ee.Image(modisndvi).getMapId(vis_paramsNDVI)
        
        tiles = map_id_dict['tile_fetcher'].url_format

        AOIsmaller_shp = os.path.join(settings.MEDIA_ROOT,'axis.shp')
        AOI = geemap.shp_to_ee(AOIsmaller_shp)

        # #create visual boundary color only
        empty = ee.Image().byte()
        AOIm = empty.paint(AOI,0,3)

        #add the map to the the folium map
        map_id_dict_aoi = ee.Image(AOIm).getMapId({})

        tiles_aoi = map_id_dict_aoi['tile_fetcher'].url_format

        content = {'message':     tiles, 'messages2': tiles_aoi }
        return Response(content)

    
    
