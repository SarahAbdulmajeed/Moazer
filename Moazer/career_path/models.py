from django.db import models
from django.conf import settings

User = settings.AUTH_USER_MODEL

class PathStatus(models.TextChoices):
    RUNNING = "RUNNING", "جارية"
    FINISHED = "FINISHED", "منتهية"

class PathMode(models.TextChoices):
    SCHOOL = "SCHOOL", "طلاب المدارس/المقبلون على الجامعة"
    GRAD   = "GRAD",   "الخريجون/المقبلون على الوظيفة"

class PathSession(models.Model):
    """
    Represents one end-to-end 'Discover Your Path' session.

    Authenticated user:
        - 'user' is set, 'is_guest' is False, 'guest_session_key' empty.

    Guest user (trial):
        - 'user' is NULL, 'is_guest' is True, and 'guest_session_key' stores
          the Django session key to authorize access to this session later.

    Status:
        - 'RUNNING' while asking questions
        - 'FINISHED' once final analysis is stored
    """
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, null=True, blank=True,
        related_name="path_sessions"
    )
    guest_session_key = models.CharField(max_length=64, blank=True, default="")
    is_guest = models.BooleanField(default=False)

    mode = models.CharField(max_length=10, choices=PathMode.choices, default=PathMode.SCHOOL)

    status = models.CharField(
        max_length=20,
        choices=PathStatus.choices,   
        default=PathStatus.RUNNING
    )    
    major = models.CharField(max_length=120, blank=True)

    suggested_path = models.CharField(max_length=100, blank=True)

    strengths = models.TextField(blank=True)
    weaknesses = models.TextField(blank=True)
    recommendation = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def owned_by_request(self, request) -> bool:
        """
        Authorization helper:
        - If the request is authenticated, ensure the same owner.
        - If guest, match the saved guest_session_key with the current session.
        """
        if request.user.is_authenticated:
            return self.user_id == request.user.id
        return (
            self.is_guest
            and self.guest_session_key
            and self.guest_session_key == getattr(request.session, "session_key", None)
        )


class PathQuestion(models.Model):
    """
    A single question within a session.

    'phase' distinguishes:
        1 => general discovery (first 10)
        2 => specialization for the predicted path (second 10)
    """
    session = models.ForeignKey(PathSession, on_delete=models.CASCADE, related_name="questions")
    order = models.PositiveIntegerField()
    text = models.TextField()
    phase = models.PositiveIntegerField(default=1) # 1=general, 2=specialized

    class Meta:
        unique_together = ("session", "order")
        ordering = ["order"]


class PathAnswer(models.Model):
    """
    User's answer to a specific question in a session.
    Each (session, question) pair is unique.
    """
    session = models.ForeignKey(PathSession, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(PathQuestion, on_delete=models.CASCADE)
    answer = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("session", "question")