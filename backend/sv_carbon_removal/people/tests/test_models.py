'''
Test for the models
'''

from django.test import TestCase
from django.contrib.auth import get_user_model

class ModelTests(TestCase):
    '''Test model'''

    def test_create_user_with_email_successful(self):
        '''test creating a user with an email if successful'''
        email = 'test@example.com'
        password = 'testpass1234'
        user = get_user_model().objects.create_user(
            email=email,
            password=password,
        )

        self.assertEqual(user.email, email)
        self.assertTrue(user.check_password(password))

    def test_create_superuser(self):
        '''test creating a superuser'''
        user = get_user_model().objects.create_superuser(
            'test@example.com',
            'test123',
        )

        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)