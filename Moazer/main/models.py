from django.db import models
from django.contrib.auth.models import AbstractUser
import uuid
from multiselectfield import MultiSelectField


class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ("student", "Student"),
        ("expert", "Expert"),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="student")
    gender = models.CharField(max_length=10, blank=True, default="")
    dob = models.DateField(blank=True, null=True)
    phone = models.CharField(max_length=15, blank=True, default="")
    city = models.CharField(max_length=100, blank=True, default="")
    bio = models.TextField(blank=True, default="")
    profile_picture = models.ImageField(upload_to="profiles/", blank=True, null=True)

    def __str__(self):
        return self.username


class StudentProfile(models.Model):
    STAGE_CHOICES = (
        ("middle", "متوسط"),
        ("high", "ثانوي"),
        ("university", "جامعي"),
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    stage = models.CharField(max_length=50, choices=STAGE_CHOICES, blank=True, null=True)

    def __str__(self):
        return self.user.username

    class Meta:
        verbose_name = "Student Profile"
        verbose_name_plural = "Student Profiles"


class ExpertProfile(models.Model):
    SPECIALTY_CHOICES = (
        ("academic_guidance", "إرشاد أكاديمي"),
        ("career_guidance", "توجيه مهني"),
        ("self_development", "تطوير الذات"),
        ("cv_writing", "كتابة السيرة الذاتية"),
    )

    CONSULTATION_CHOICES = (
        ("career_path", "اختيار المسار المهني"),
        ("study_path", "اختيار المسار الدراسي"),
        ("university_choices", "مراجعة خيارات التخصصات الجامعية"),
        ("general_inquiry", "استفسار عام"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    iban = models.CharField(max_length=34, blank=True, default="")
    hourly_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    specialties = MultiSelectField(choices=SPECIALTY_CHOICES, blank=True, null=True)
    consultation_types = MultiSelectField(choices=CONSULTATION_CHOICES, blank=True, null=True)
    rating_avg = models.DecimalField(max_digits=3, decimal_places=1, default=0)
    rating_count = models.IntegerField(default=0)

    def __str__(self):
        return self.user.username

    class Meta:
        verbose_name = "Expert Profile"
        verbose_name_plural = "Expert Profiles"
