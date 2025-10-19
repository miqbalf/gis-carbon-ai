from rest_framework import viewsets, status
from rest_framework.response import Response
from django.http import JsonResponse  # Use JsonResponse for JSON responses
from django.db import IntegrityError
from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import ListAPIView
from rest_framework.filters import SearchFilter
# from rest_framework.views import APIView
from adrf.views import APIView
from rest_framework.exceptions import ParseError

from fcd_gee.models import ProjectCarbon, SatVerConfiguration, SHP_AOI
from .serializers import SatVerSerializer, ProjectSerializer, ShpSerializer

from fcd_gee.fcd_run import async_var_assignment, run_fcd, get_hansen_historical, classifying_lu, calc_area_zone

class projectViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = ProjectCarbon.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]

class satVerViewSet(viewsets.ModelViewSet):
    # queryset = SatVerConfiguration.objects.all()
    serializer_class = SatVerSerializer
    permission_classes = [IsAuthenticated]
    queryset = SatVerConfiguration.objects.all()

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response({'message': 'Resource created successfully'}, status=status.HTTP_201_CREATED, headers=headers)
        except IntegrityError as e:
            error_message = str(e)
            return Response({'error': error_message}, status=status.HTTP_400_BAD_REQUEST)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def destroy(self, request, *args, **kwargs):
        # Default destroy method for deleting based on 'id'
        return super().destroy(request, *args, **kwargs)
    
    def delete_by_label(self, request, *args, **kwargs):
        label = self.kwargs.get('label')

        # Assuming you want to delete based on the field 'kind'
        queryset = SatVerConfiguration.objects.filter(label=label)

        if not queryset.exists():
            return Response({'detail': 'No matching instances found'}, status=status.HTTP_404_NOT_FOUND)

        # Delete all instances that match the filter
        queryset.delete()

        return Response({'detail': 'Instances deleted successfully'}, status=status.HTTP_204_NO_CONTENT) 

    def get_queryset(self):
        
        project_name = self.request.query_params.get('project')
        queryset = self.queryset.filter(project__name=project_name) if project_name else self.queryset
        return queryset
    
class ShpViewSet(viewsets.ModelViewSet):
    serializer_class = ShpSerializer
    permission_classes = [IsAuthenticated]
    queryset = SHP_AOI.objects.all()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_queryset(self):
        project_name = self.request.query_params.get('project')
        queryset = self.queryset.filter(project__name=project_name) if project_name else self.queryset
        return queryset
    
class FCDViewSet(APIView):
    permission_classes = [IsAuthenticated]

    async def post(self, request):
        try:
            payload_data = request.data  # Access the parsed data
            config = await async_var_assignment(payload_data['config'])
            gee_fcd = await run_fcd(config)

            gee_url = gee_fcd['all_tiles_aoi']
            fcd_calc_run = gee_fcd['fcd_calc_run']

            hansen_historical = await get_hansen_historical(config)
            gfc = hansen_historical['gfc']
            minLoss = hansen_historical['minLoss']

            class_fcd_hansen = await classifying_lu(config, gfc, minLoss, FCD2_1 = fcd_calc_run['FCD2_1'], FCD1_1=fcd_calc_run['FCD1_1'],
                                      FCD1_2=fcd_calc_run['FCD1_2'],FCD2_2=fcd_calc_run['FCD2_2'])
            
            class_tiles = class_fcd_hansen['class_tiles']
            legend_class = class_fcd_hansen['legend_class']
            all_zone_image = class_fcd_hansen['all_zone_image']

            # adding new key to the existing dict, to add new item class_tiles (final fcd_hansen class)
            gee_url['class_tiles'] = class_tiles

            pca_scale = gee_fcd['pca_scale']

            # adding area in the response
            calc_area = await calc_area_zone(config, payload_data['config'], pca_scale, calc_image=all_zone_image)

            # Process payload_data
            content = {
                        'gee_url':gee_url, 
                       'centroid_AOI':config['centroid_AOI'],
                       'legend_class': legend_class,
                       'areas_id': calc_area,
                       }
            
            return JsonResponse(content)
        except ParseError as e:
            return JsonResponse({'error': str(e)}, status=500)
        
