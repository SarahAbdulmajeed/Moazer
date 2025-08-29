from django.db import models
from django.conf import settings

User = settings.AUTH_USER_MODEL


class InterviewStatus(models.TextChoices):
    NEW = "NEW", "جديدة"
    RUNNING = "RUNNING", "جارية"
    FINISHED = "FINISHED", "منتهية"


class InterviewSession(models.Model):
    """
    One interview session per owner.
    If user is authenticated -> 'user' is set.
    If guest -> 'user' is NULL and we store 'guest_session_key' for auth.
    """
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="interview_sessions",
        null=True, blank=True  # <-- allow guest sessions
    )
    guest_session_key = models.CharField(max_length=64, blank=True, default="")
    is_guest = models.BooleanField(default=False)

    job_title = models.CharField(max_length=200)
    status = models.CharField(max_length=10, choices=InterviewStatus.choices, default=InterviewStatus.NEW)

    # Final AI summary (filled when the session finishes)
    strengths = models.TextField(blank=True)
    weaknesses = models.TextField(blank=True)
    recommendation = models.TextField(blank=True)

    overall_score = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def owned_by_request(self, request) -> bool:
        """
        Authorization helper:
        - Auth user owns by user FK.
        - Guest owns by matching session_key.
        """
        if request.user.is_authenticated:
            return self.user_id == request.user.id
        return self.is_guest and self.guest_session_key and self.guest_session_key == getattr(request.session, "session_key", None)


class SessionQuestion(models.Model):
    session = models.ForeignKey(InterviewSession, on_delete=models.CASCADE, related_name="questions")
    order = models.PositiveIntegerField()
    text = models.TextField()

    class Meta:
        ordering = ["order"]
        unique_together = ("session", "order")

class InterviewAnswer(models.Model):
    """
    User's answer for a specific session question.
    """
    session = models.ForeignKey(InterviewSession, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(SessionQuestion, on_delete=models.CASCADE)
    answer = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    strengths = models.TextField(blank=True)   # what was good in this answer
    weaknesses = models.TextField(blank=True)  # what to improve in this answer
    score = models.PositiveSmallIntegerField(null=True, blank=True)  # 1..5

    class Meta:
        unique_together = ("session", "question")             # One answer per question in a session