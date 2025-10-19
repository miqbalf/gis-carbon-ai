from django.db import models

from django.conf import settings

from datetime import datetime, timedelta

import os

def two_years_ago():
    return datetime.now() - timedelta(days=730)

# Create your models here.
class ProjectCarbon(models.Model):
    id = models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')
    name = models.CharField(unique=True, max_length=30, blank=False, null=False, verbose_name='Project Name')
    project_desc = models.TextField(blank=True, null=True, verbose_name= 'Project Description')
    project_type = models.CharField(max_length=30, blank=False, null=False, default='agroforestry', verbose_name='Project Type')

    def __str__(self):
        return self.name

def user_upload_path(instance, filename):
    # Get the user's username
    name = instance.user.name if instance.user else 'unknown_user'
    file_prefix = instance.file_name_prefix

    # Get the file's extension
    _, extension = os.path.splitext(filename)

    # Construct the new filename
    new_filename = f'{file_prefix}_{name}{extension}'

    # Return the final path
    return os.path.join('uploads/', new_filename)

class SHP_AOI(models.Model):
    id = models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')
    file = models.FileField(upload_to=user_upload_path)
    description = models.CharField(max_length=255, blank=True, null=True)
    file_name_prefix = models.CharField(max_length=30, blank=False, null=False, default='AOI', verbose_name='Prefix name')

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        default=None
    )

    project = models.ForeignKey(ProjectCarbon, on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        # Check if the user is authenticated before saving the file
        if self.user and self.user.is_authenticated:
            super().save(*args, **kwargs)
        else:
            raise ValueError("Only authenticated users can upload files.")

    def __str__(self):
        return self.file.name
    

class SatVerConfiguration(models.Model):
    '''Model for the configuration of satellite verification / assessment GEE'''
    # user field, to relate the configuration with the user that created
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        default=None
    )
    id = models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')
    project = models.ForeignKey(ProjectCarbon, on_delete=models.CASCADE)
    label = models.CharField(max_length=50, unique=True, blank=False, null=False)
    start_date_analysis = models.DateField(default=two_years_ago) # some logic when we use datetime.now --> without paranthesis
    end_date_analysis = models.DateField(default=datetime.now, editable=True, blank=False, null=False)
    satellite_use = models.CharField(max_length=20)
    shp_aoi = models.ForeignKey(SHP_AOI, on_delete=models.CASCADE)
    
    # Hansen
    tree_cover_forest_threshold = models.IntegerField(default=30, blank=False, null=False, verbose_name='Hansen TreeCover Threshold')
    area_threshold_forest = models.DecimalField(default=0.25, blank = False, null=False, max_digits=4, decimal_places=2, verbose_name='Forest definition minimum area')
    is_include_thermal = models.BooleanField(default=False, blank=False, null=False, verbose_name='Is the data include thermal index')
    historical_years_baseline = models.IntegerField(default=2013, blank=False, null=False, verbose_name='historical years - rule')


    # FCD
    FCD_CHOICES = [
        (12, 'FCD 12'),
        (22, 'FCD 22'),
        (21, 'FCD 21'),
        (11, 'FCD 11'),
    ]

    combination_selected = models.IntegerField(choices=FCD_CHOICES, default=21)
    high_dense_threshold = models.IntegerField(default=65, blank=False, null=False, verbose_name='High density Forest Threshold')
    med_dense_threshold = models.IntegerField(default=45, blank=False, null=False, verbose_name='Med density Forest Threshold')
    low_shrub_threshold = models.IntegerField(default=25, blank=False, null=False, verbose_name='Low density Forest Threshold')

    pca_scaling = models.IntegerField(default=1, blank=False,null=False, verbose_name='add a scaling, higher is less detailed')
    region = models.CharField(max_length=10, default='africa', verbose_name='region selection')

    def __unicode__(self):
        return self.id
    
    def __str__(self):
        return self.label
    
    class Meta:
        constraints = [
            # models.UniqueConstraint(fields=['start_date_analysis', 'end_date_analysis'], name='unique_start_end_combination'), # this is unique contraints, we dont need
            models.CheckConstraint(check=models.Q(start_date_analysis__lt=models.F('end_date_analysis')), name='start_date_before_end_date'),
            models.CheckConstraint(check=models.Q(historical_years_baseline__lt=2022), name='no_more_than_2022'),        
        ]   