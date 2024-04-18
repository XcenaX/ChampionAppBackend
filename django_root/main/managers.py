from django.contrib.auth.base_user import BaseUserManager
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.hashers import make_password

class CustomUserManager(BaseUserManager):
    """
    Custom user model manager where email is the unique identifiers
    for authentication instead of usernames.
    """

    def create_user(self, username, password, **extra_fields):
        """
        Create and save a user with the given username and password.
        """
        user = self.model(username=username, **extra_fields)
        user.set_password(password)        
        user.save()
        return user

    def create_superuser(self, username, password, **extra_fields):
        """
        Create and save a SuperUser with the given email and password.
        """
        user = self.model(username=username, is_superuser=True, is_staff=True, password=password)
        user.set_password(password)        
        user.save()
        return user
