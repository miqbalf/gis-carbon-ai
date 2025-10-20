import os
import ee
import geemap

from gee_lib.osi.fcd.main_fcd import FCDCalc
from gee_lib.osi.hansen.historical_loss import HansenHistorical
from gee_lib.osi.classifying.assign_zone import AssignClassZone
from gee_lib.osi.area_calc.main import CalcAreaClass
from django.conf import settings

from .models import SatVerConfiguration

service_account = os.environ.get('SERVICE_ACCOUNT', 'earth-engine-land-eligibility@ee-iwansetiawan.iam.gserviceaccount.com')
# credentials = ee.ServiceAccountCredentials(service_account, os.path.join(os.path.dirname(__file__),'bukit30project-4d92e5b46ea7.json'))
# location_credention = os.path.join(os.path.dirname(__file__), 'bukit30project-4d92e5b46ea7.json')
location_credention = os.environ.get('GCP_CREDENTIAL_PATH', '/usr/src/app/user_id.json')

from google.auth.transport.requests import Request

from datetime import datetime, timedelta

credentials = ee.ServiceAccountCredentials(
    service_account,
    location_credention
)

try:
    ee.Initialize(credentials)
except Exception as e:
    print(f"Error during Earth Engine initialization: {e}")
    # make sure just do command terminal ntpdate ntp.ubuntu.com
    
    if 'invalid_grant' in str(e):
        print("Invalid JWT error. Refreshing credentials.")
        
        # Manually refresh the credentials by recreating them with a new expiration time
        expiration_time = datetime.utcnow() + timedelta(minutes=60)
        # credentials = ee.ServiceAccountCredentials(service_account, location_credention, expiration_time=expiration_time)
        
        # Manually refresh the credentials
        credentials.refresh(Request())
        
        # Update the Earth Engine credentials with the refreshed credentials
        ee.data.set_earthengine_credentials(credentials)
        
        print("Credentials refreshed successfully.")
    else:
        # Handle other exceptions
        pass

import zipfile
import tempfile
import json

import geopandas as gpd

def convert_to_serializable(obj):
    if isinstance(obj, (ee.Geometry, ee.Image, ee.FeatureCollection)):
        # Convert Earth Engine objects to JSON-serializable format
        return obj.getInfo()
    elif isinstance(obj, gpd.GeoDataFrame):
        # Convert GeoDataFrame to JSON-serializable format
        return json.loads(obj.to_json())

    # Add other custom conversions if needed

    return obj

async def unzip_file(zip_file):
    """Extracts files from a zip archive without the top-level parent folder.

    Args:
        zip_file (str): The path to the zip file.
        destination (str): The path to the destination directory.
    """

    temp_dir = tempfile.mkdtemp()

    with zipfile.ZipFile(zip_file, 'r') as zip_ref:
        for file_info in zip_ref.infolist():
            # Skip directories to avoid extracting the parent folder
            if file_info.is_dir():
                continue

            # Extract the file, removing the top-level parent folder from the path
            file_path = file_info.filename
            base_filename = os.path.basename(file_path)  # Get the base filename
            extracted_path = os.path.join(temp_dir, base_filename)  # Construct full path without parent folder

            # Create any necessary parent directories
            os.makedirs(os.path.dirname(extracted_path), exist_ok=True)

            with open(extracted_path, 'wb') as outfile:
                outfile.write(zip_ref.read(file_info))

    return temp_dir

from asgiref.sync import sync_to_async
from fcd_gee.models import SatVerConfiguration

import warnings

import sys

async def async_var_assignment(conf_label):
    try:
        labelquery = await sync_to_async(SatVerConfiguration.objects.get)(label=conf_label) ## example that already exist in the db and we filterbased on this\
        file_location_conf = await sync_to_async(lambda: labelquery.shp_aoi.file)()
        print(file_location_conf, flush=True)
        temp_dir = await unzip_file(file_location_conf.path)

        # TEST VARIABLE TO GEE FROM DJANGO
        start_date = labelquery.start_date_analysis
        end_date = labelquery.end_date_analysis

        # for planet labs image
        region = labelquery.region # or you can use 'asia'

        # cloud cover threshold, max per image, in image collection
        cloud_cover_threshold = 40

        # input shp region based on the AOI, relative path to our collab folder content
        # AOIt_shp = '/content/drive/MyDrive/shp_local/AOI_AXIS_BIG.shp'

        list_files_tmp = os.listdir(temp_dir)
        shp_tmp_text = [f for f in list_files_tmp if '.shp' in f][0]
        AOIt_shp = os.path.join(temp_dir, shp_tmp_text)

        AOIt_shp_plot = geemap.shp_to_ee(AOIt_shp)
        crs_input = 'EPSG:4326'

        AOI = AOIt_shp_plot
        pca_scaling = labelquery.pca_scaling  # 1 meaning that 1 x pixel size of spatial resolution e.g., Planet Labs 1 x 5, Sentinel 1 x 10, Landsat 1 x 30
        tileScale = 1 # increase this if user memory limit occur, see: https://gis.stackexchange.com/questions/373250/understanding-tilescale-in-earth-engine

        I_satellite = labelquery.satellite_use

        #NDWI water limit
        ndwi_hi_sentinel = 0.05 # for Sentinel
        ndwi_hi_landsat = 0.1 # for landsat
        ndwi_hi_planet = -0.2 # for Planet Labs

        ndwi_hi = 0.1
        if I_satellite == 'Landsat':
            ndwi_hi = ndwi_hi_landsat
        elif I_satellite == 'Sentinel':
            ndwi_hi = ndwi_hi_sentinel
        elif I_satellite == 'Planet':
            ndwi_hi = ndwi_hi_planet

        ######## HANSEN Tree Cover and Tree Cover Loss Input - Historical Data Check (10 Years Rule) ###################################################
        # Hansen 10 years rule and Forest - Tree Cover Hansen
        # define tree cover minimum that classified as forest e.g., Indonesia > 30%, hence 30
        tree_cover_forest = labelquery.tree_cover_forest_threshold # this will be in percent, let's say, forest is > 30% if you put 30
        area_threshold_forest = labelquery.area_threshold_forest
        # pixel_number = 3 #define minimum mapping unit classified as forest, 1 pixel for landsat 30mx30, 3 pixel is forest ~> 0.27 Ha
        
        import math
        pixel_number = math.ceil(float(area_threshold_forest)/(30*30/10000))
        
        historical_years_baseline = labelquery.historical_years_baseline
        # year_start_loss = 13 #define start year to track as 10 years rule (e.g., 2012 to 2022 (track 10 years rule), hence 12. format= 00->2000, 12->2012)
        year_start_loss = historical_years_baseline - 2000

        ## FCD Threshold
        # high_forest = 65
        high_forest = labelquery.high_dense_threshold
        # yrf_forest = 45
        yrf_forest = labelquery.med_dense_threshold

        # shrub_grass = 25
        shrub_grass = labelquery.low_shrub_threshold

        # output Band Names
        band_name_image = 'Class'

        #for area id in shapefile that identified the data, and will converted into raster
        OID = 'id'  #IMPORTANT TO CHECK OID based on the column ID
        #############################################
        ##################################################################################
        ### Masking and overlay and area helper Make an image out of the AOI area attribute -> convert featurecollection into raster (image) for overlaying tools
        AOI_img = AOI.filter(ee.Filter.notNull([OID])).reduceToImage(
            properties= [OID],
            reducer= ee.Reducer.first()
        )

        gdf = gpd.read_file(AOIt_shp)

        # warning from the 'centroids' operation
        warnings.filterwarnings("ignore", category=UserWarning, message="Geometry is in a geographic CRS")

        # Get the centroids of the polygons
        centroids = gdf.geometry.centroid

        centroids_dict = [{'lat': point.y, 'lon': point.x} for point in centroids]

        # Convert centroids_dict to JSON-serializable format
        centroids_serializable = json.loads(json.dumps(centroids_dict, default=convert_to_serializable))
        
        # Print the result
        print(centroids_dict)

        centroid_AOI = centroids_serializable

        config = {
            'I_satellite': I_satellite,
            'pca_scaling':pca_scaling,
            'tileScale': tileScale,
            'AOI': AOI,
            'IsThermal': False,
            'cloud_cover_threshold': cloud_cover_threshold, # for landsat collection
            'date_start_end':[start_date,end_date],
            'ndwi_hi':ndwi_hi,
            'tree_cover_forest': tree_cover_forest,
            'pixel_number': pixel_number,
            'year_start_loss': year_start_loss,
            'high_forest': high_forest,
            'yrf_forest': yrf_forest,
            'shrub_grass': shrub_grass,
            'AOI_img': AOI_img,
            'centroid_AOI': centroid_AOI,
            'region': region,
            'fcd_selected': labelquery.combination_selected,
            'band_name_image': band_name_image,
        }

        # temporary
        labelquery = config

    except SatVerConfiguration.DoesNotExist:
        print('labelquery object is not found')
        labelquery = None
    return labelquery

async def run_fcd(config):
    classFCD = FCDCalc(config)
    fcd_calc_run = classFCD.fcd_calc()

    fcd_mapviz = {'min':0 ,'max':80, 'palette':['ff4c16', 'ffd96c', '39a71d']}

    all_mapviz = {
        'image_mosaick': {"bands":["red","green","blue"],"min":0,"max":0.1,"gamma":1},
        'avi_image': {},
        'bsi_image': {},
        'si_image': {},

        'avi_norm': {'min':0,'max':100},
        'si_norm': {'min':0,'max':100},
        'ti_norm': {'min':0,'max':100},
        
        'svi1' :{'min':0,'max':100},
        'svi2' :{'min':0,'max':100},
        'ssi1' :{'min':0,'max':100},
        'ssi2' :{'min':0,'max':100},

        'FCD1_1': fcd_mapviz,
        'FCD2_1': fcd_mapviz,
        'FCD1_2': fcd_mapviz,
        'FCD2_2': fcd_mapviz,
    }
    
    # identify mapID
    all_mapid = {k: ee.Image(v).getMapId(all_mapviz[k]) for k,v in fcd_calc_run.items() if k in all_mapviz}
    # map_id_dict_aoi = ee.Image(FCD2_1).getMapId(fcd_mapviz)

    # tiles_aoi = map_id_dict_aoi['tile_fetcher'].url_format
    all_tiles_aoi = {k: v['tile_fetcher'].url_format for k,v in all_mapid.items()}
    print(all_tiles_aoi)

    pca_scale = fcd_calc_run['pca_scale']

    return {
            'all_tiles_aoi':all_tiles_aoi, 
            'fcd_calc_run':fcd_calc_run,
            'pca_scale': pca_scale
            }

async def get_hansen_historical(config):
    hansen_class = HansenHistorical(config)
    tcl = hansen_class.initiate_tcl()
    gfc = tcl['gfc']
    minLoss = tcl['minLoss']

    return {'tcl':tcl,
            'gfc':gfc,
            'minLoss': minLoss}

async def classifying_lu(config, gfc, minLoss, FCD2_1 = None, FCD1_1=None,
                                      FCD1_2=None,FCD2_2=None):
    # we will re-adding the kwargs FCD2_1, this just listed the option (empty var will be as None), 
    # and the selection actually based on the config['fcd_selected']
    assignClass = AssignClassZone(config, FCD2_1 = FCD2_1, FCD1_1=FCD1_1,
                                      FCD1_2=FCD1_2,FCD2_2=FCD2_2)
    class_fcd = assignClass.assigning_fcd_class(gfc, minLoss)
    all_zone = class_fcd['all_zone']
    vis_params = class_fcd['vis_param_merged']
    legend_class = class_fcd['legend_class']

    class_mapid = ee.Image(all_zone).getMapId(vis_params)
    class_tiles = class_mapid['tile_fetcher'].url_format

    return {'class_tiles': class_tiles,
            'legend_class':legend_class,
            'all_zone_image': all_zone}

from datetime import datetime

import time

current_date = datetime.now().strftime('%Y-%m-%d')
# print(current_date)

async def calc_area_zone(config, name_folder, pca_scale, calc_image=None):
    class_calc_area = CalcAreaClass(config, calc_image=calc_image)
    run_calc = class_calc_area.run_calc_per_id()
    # geemap.ee_export_image_to_drive(
    #     calc_image, description=f'result_exported_{config["I_satellite"]}', folder=f"gee_mapbox_result/{current_date}_{name_folder}", scale=5, region=config['AOI'].geometry(), # let's force and test, later we need to separate this into a feature when user want to export the result
    #                                                 # here we make the default, everything will be exported after run one time in calc_area_zone
    # )

    # Define export parameters
    export_params = {
        'image': calc_image,
        'description': f'result_exported_{config["I_satellite"]}_at{current_date}_project{name_folder}_{pca_scale}m',
        'scale': pca_scale,  # Adjust scale as needed
        'region': config['AOI'].geometry(),
        # 'folder': 'gee_result',  # Specify the Google Drive folder to export to
        'assetId': f'projects/ee-iwansetiawan/assets/result_exported_{config["I_satellite"]}_at{current_date}_project{name_folder}_{pca_scale}m'
        # 'assetId': f'users/muhfirdausiqbal/exported_{config["I_satellite"]}_at{current_date}_project{name_folder}_{pca_scale}m'
        # 'assetId': f'projects/bukit30project/exported_{config["I_satellite"]}_at{current_date}_project{name_folder}_{pca_scale}m'
        # 'fileFormat': 'GeoTIFF',  # Format of the exported file
    }

    # Export the image
    # task = ee.batch.Export.image.toDrive(**export_params)
    task = ee.batch.Export.image.toAsset(**export_params)
    task.start()

    # Monitor the task
    print('Exporting image to Asset...')
    while task.status()['state'] in ['READY', 'RUNNING']:
        print(task.status())
        time.sleep(5)  # Wait for 5 seconds before checking the status again
    print('Export completed:', task.status())

    return run_calc

