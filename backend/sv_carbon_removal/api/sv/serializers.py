from fcd_gee.models import ProjectCarbon ,SatVerConfiguration, SHP_AOI
from rest_framework import serializers

class ProjectSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = ProjectCarbon
        fields = ['name', 'project_desc', 'project_type', 'id' ]

class SatVerSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = SatVerConfiguration
        fields = ['user','id','project', 'label', 'start_date_analysis',
                  'end_date_analysis', 'satellite_use', 'shp_aoi',
                  'tree_cover_forest_threshold', 'area_threshold_forest',
                  'is_include_thermal', 'historical_years_baseline',
                   'combination_selected', 'high_dense_threshold', 'med_dense_threshold',
                   'low_shrub_threshold', 'pca_scaling','region',            
                  ]
        
class ShpSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = SHP_AOI
        fields = ['id','file', 'description','file_name_prefix' ,'user', 'project']

# class ProjectRegistrationSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = ProjectCarbon
#         fields = ['name', 'project_desc', 'project_type' ]

#     def create(self, validated_data):
#         user = ProjectCarbon.objects.create_user(
#             email=validated_data['email'],
#             password=validated_data['password'],
#             # disable direct login - enable approval moderation
#             is_active=False,
#         )
#         return user