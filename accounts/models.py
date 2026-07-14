from django.db import models

# Create your models here.
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('resident', 'Resident')
    )

    role = models.CharField(max_length=200, choices=ROLE_CHOICES)

    def __str__(self):
        return self.username