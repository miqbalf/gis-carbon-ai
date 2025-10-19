'''
Database models for people -> user (email) and password
'''

from django.db import models
from django.contrib.auth.models import Group, User
from PIL import Image

from django.contrib.auth.models import (AbstractUser, Permission, UserManager,
                                        AbstractBaseUser, BaseUserManager, PermissionsMixin)
from django.db.models import Q

from django.contrib.auth import get_user_model

from django.utils import timezone
from django.utils.translation import gettext_lazy as _

class UserManager(BaseUserManager):
    '''Manager for user'''

    '''Create, save and return a new user'''
    def create_user(self, email, password=None, **extra_fields):
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_superuser(self, email, password):
        '''create and return a superuser'''
        user = self.create_user(email,password)
        user.is_active = True
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)

        return user

class User(AbstractBaseUser, PermissionsMixin): # choose the AbstractBaseUser instead of AbstractUser since we only need a fewer object inherited
    '''User in the system'''
    email = models.EmailField(max_length=255, unique=True)
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    date_joined = models.DateTimeField(_("date joined"), default=timezone.now)

    # use the user manager to manage of user -> create the user
    objects = UserManager()

    USERNAME_FIELD = 'email' # change the login method only use email