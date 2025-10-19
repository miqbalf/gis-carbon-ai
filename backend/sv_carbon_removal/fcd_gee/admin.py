from django.contrib import admin
from .models import ProjectCarbon, SatVerConfiguration, SHP_AOI

# Register your models here.
admin.site.register(ProjectCarbon)
admin.site.register(SatVerConfiguration)
admin.site.register(SHP_AOI)