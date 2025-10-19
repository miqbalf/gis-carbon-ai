from rest_framework import routers

from api.people import view_api as view_api_people
from api.sv import view_api as view_api_sv

router = routers.DefaultRouter()
router.register(r'users', view_api_people.UserViewSet)
router.register(r'projects', view_api_sv.projectViewSet)
router.register(r'projects_sv_conf',view_api_sv.satVerViewSet, basename='carbon-project-sv')
router.register(r'shp_aoi', view_api_sv.ShpViewSet)
