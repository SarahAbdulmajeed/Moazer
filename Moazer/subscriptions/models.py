from django.db import models
from django.conf import settings

User = settings.AUTH_USER_MODEL

class Plan(models.Model):
    """
    A simple prepaid plan that grants a fixed number of attempts.
    You can later add price/stripe_product_id/etc.
    """
    name = models.CharField(max_length=100, unique=True)
    attempts = models.PositiveIntegerField(default=5)
    price_sar = models.DecimalField(max_digits=8, decimal_places=2, default=0)  # optional

    def __str__(self):
        return f"{self.name} ({self.attempts} attempts)"

class Wallet(models.Model):
    """
    Per-user wallet for attempts that can be spent on any product.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="wallet")
    total_attempts = models.IntegerField(default=0)

    def __str__(self):
        return f"Wallet({self.user_id})={self.total_attempts}"

    def add_attempts(self, n: int):
        self.total_attempts = (self.total_attempts or 0) + int(n)
        self.save(update_fields=["total_attempts"])

    def has_attempts(self, n: int = 1) -> bool:
        return (self.total_attempts or 0) >= n

    def consume(self, product_code: str, n: int = 1) -> bool:
        """
        Atomically consume attempts and write a usage log.
        """
        if not self.has_attempts(n):
            return False
        self.total_attempts -= n
        self.save(update_fields=["total_attempts"])
        UsageLog.objects.create(user=self.user, product_code=product_code, amount=n)
        return True

class UsageLog(models.Model):
    """
    Simple audit trail of attempts consumption.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="usage_logs")
    product_code = models.CharField(max_length=50)  # e.g., "ai_interview"
    amount = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
