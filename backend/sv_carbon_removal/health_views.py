from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json

@csrf_exempt
@require_http_methods(["GET"])
def health_check(request):
    """
    Simple health check endpoint for Docker
    """
    return JsonResponse({
        'status': 'healthy',
        'service': 'django-backend',
        'version': '1.0.0'
    })
