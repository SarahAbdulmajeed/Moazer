from django.db import models
from django.conf import settings

User = settings.AUTH_USER_MODEL

class ConsultationStatus(models.TextChoices):
    NEW = "NEW", "جديدة"
    PENDING = "PENDING", "بانتظار قبول الخبير"
    ACTIVE = "ACTIVE", "نشطة"
    COMPLETED = "COMPLETED", "مكتملة"
    CLOSED = "CLOSED", "مغلقة"

class ConsultationTypeChoices(models.TextChoices):
    STUDY_PATH   = "STUDY_PATH",   "اختيار المسار الدراسي"
    CAREER_PATH  = "CAREER_PATH",  "اختيار المسار المهني"
    INTERVIEW    = "INTERVIEW",    "الاستعداد لمقابلة شخصية"
    CV_REVIEW    = "CV_REVIEW",    "مراجعة سيرة ذاتية"
    GENERAL      = "GENERAL",      "استفسار عام"


class Consultation(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="student_consultations")
    expert  = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="expert_consultations")
    type    = models.CharField(max_length=20, choices=ConsultationTypeChoices.choices, default=ConsultationTypeChoices.GENERAL)
    title   = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status  = models.CharField(max_length=20, choices=ConsultationStatus.choices, default=ConsultationStatus.NEW)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class ChatMessage(models.Model):
    consultation = models.ForeignKey(Consultation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

class Attachment(models.Model):
    consultation = models.ForeignKey(Consultation, on_delete=models.CASCADE, related_name="attachments")
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    file = models.FileField(upload_to="attachments/")
    created_at = models.DateTimeField(auto_now_add=True)

class ConsultationRating(models.Model):
    consultation = models.OneToOneField(Consultation, on_delete=models.CASCADE, related_name="rating")
    stars = models.IntegerField()  # 1..5
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
