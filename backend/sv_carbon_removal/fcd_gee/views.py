'''
THIS IS ONLY FOR TESTING
'''
from django.shortcuts import render

# generic base view
from django.views.generic import TemplateView 
from django.conf import settings

#folium
import folium
from folium import plugins

import os

#gee
import ee

import geemap

# Trigger the authentication flow. if you want to user json, please comment this
# ee.Authenticate()

service_account = 'iqbalpythonapi@bukit30project.iam.gserviceaccount.com'
credentials = ee.ServiceAccountCredentials(service_account, os.path.join(os.path.dirname(__file__),'bukit30project-4d92e5b46ea7.json'))

# Initialize the library.
# ee.Initialize(project='bukit30project')
ee.Initialize(credentials)


#home
class home(TemplateView):
    template_name = 'index.html'

    # Define a method for displaying Earth Engine image tiles on a folium map.
    def get_context_data(self, **kwargs):

        figure = folium.Figure()
        
        #create Folium Object
        m = folium.Map(
            location=[28.5973518, 83.54495724],
            zoom_start=8
        )

        #add map to figure
        m.add_to(figure)

        
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
       
        #GEE raster data to TileLayer
        folium.raster_layers.TileLayer(
                    tiles = map_id_dict['tile_fetcher'].url_format,
                    attr = 'Google Earth Engine',
                    name = 'NDVI',
                    overlay = True,
                    control = True
                    ).add_to(m)


        landsat9_coll = ee.ImageCollection("LANDSAT/LC09/C02/T1_L2")

        import os
        AOIsmaller_shp = os.path.join(settings.MEDIA_ROOT,'axis.shp')
        AOI = geemap.shp_to_ee(AOIsmaller_shp)

        # #create visual boundary color only
        empty = ee.Image().byte()
        AOIm = empty.paint(AOI,0,3)

        # vis_AOI = {'color': 'a01c1cff', 'width': 4, 'lineType': 'solid', 'fillColor': '96646400'}

        #add the map to the the folium map
        map_id_dict_aoi = ee.Image(AOIm).getMapId({})

        #GEE raster data to TileLayer
        folium.raster_layers.TileLayer(
                    tiles = map_id_dict_aoi['tile_fetcher'].url_format,
                    attr = 'Google Earth Engine -other',
                    name = 'AOI',
                    overlay = True,
                    control = True
                    ).add_to(m)

        # Map.addLayer(AOIm,{},'AOI')
        
        #Styling 
        vis_paramsNDVI = {
            'min': 0,
            'max': 9000,
            'palette': [ 'FE8374', 'C0E5DE', '3A837C','034B48',]}        

        #add Layer control
        m.add_child(folium.LayerControl())
       
        #figure 
        figure.render()
         
        #return map
        return {"map": figure}