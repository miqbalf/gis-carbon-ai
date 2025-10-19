from django.test import TestCase

# Create your tests here.
from django.test import TestCase
from django.urls import reverse

from django.contrib.auth import get_user_model

from .models import SatVerConfiguration, ProjectCarbon

class ListsatVerFilteredViewTest(TestCase):

    def setUp(self):
        # create the users
        user = get_user_model().objects.create_user(
                'test@example.com',
                'test123',
            )

        # Create test data
        self.project1 = ProjectCarbon.objects.create(name="Project 1")
        self.project2 = ProjectCarbon.objects.create(name="Project 2")
        self.sv1 = SatVerConfiguration.objects.create(
            project=self.project1,
            # ... other fields
            user=user,
            start_date_analysis = '2022-1-1',
            end_date_analysis = '2024-1-1',
            label= 'test13123'
        )
        self.sv2 = SatVerConfiguration.objects.create(
            project=self.project2,
            # ... other fields
            user = get_user_model().objects.create_user(
                'test@example2.com',
                'test123',
            ),
            start_date_analysis = '2022-1-1',
            end_date_analysis = '2024-1-1',
            label='test23123'
        )

    def test_filter_by_project(self):
        url = reverse('carbon-project-sv') + '?project=Project%201'  # URL-encode project name
        response = self.client.get(url)

        # Assert filtered results
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)  # Only one result expected
        self.assertEqual(response.data[0]['project_carbon'], self.project1.id)

    def test_no_filter(self):
        url = reverse('carbon-project-sv')
        response = self.client.get(url)

        # Assert all results
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)  # Both projects expected


