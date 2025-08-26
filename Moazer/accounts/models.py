from django.db import models
from django.contrib.auth.models import User


class StudentProfile(models.Model):
    STAGES = (
        ('middle', 'المتوسطة'),
        ('high', 'الثانوية'),
        ('diploma', 'الدبلوم'),
        ('bachelor', 'البكالوريوس'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    birth_date = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=[('male', 'ذكر'), ('female', 'أنثى')])
    phone = models.CharField(max_length=20)
    city = models.CharField(max_length=100)
    avatar = models.ImageField(upload_to='avatars/', default="images/default.png")
    bio = models.TextField(blank=True, null=True)
    study_stage = models.CharField(max_length=20, choices=STAGES)
    created_at = models.DateTimeField(auto_now_add=True)

class Specialization(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name = "تخصص"
        verbose_name_plural = "التخصصات"

class ConsultationType(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name = "نوع استشارة"
        verbose_name_plural = "أنواع الاستشارات"

class ExpertProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    birth_date = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=[('male', 'ذكر'), ('female', 'أنثى')])
    phone = models.CharField(max_length=20)
    city = models.CharField(max_length=100)
    avatar = models.ImageField(upload_to='avatars/', default="images/default.png")
    bio = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # Relationship
    specializations = models.ManyToManyField(Specialization, blank=True)
    consultation_types = models.ManyToManyField(ConsultationType, blank=True)

