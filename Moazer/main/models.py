from django.db import models
from django.contrib.auth.models import AbstractUser
import uuid


class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ("student", "Student"),
        ("expert", "Expert"),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="student")
    gender = models.CharField(max_length=10, blank=True, null=True)
    dob = models.DateField(blank=True, null=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profiles/', blank=True, null=True)

    def __str__(self):
        return self.username



class StudentProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    stage = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return self.user.username



class ExpertProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    iban = models.CharField(max_length=34, blank=True, null=True)
    hourly_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    rating_avg = models.DecimalField(max_digits=3, decimal_places=1, default=0)
    rating_count = models.IntegerField(default=0)

    def __str__(self):
        return self.user.username
