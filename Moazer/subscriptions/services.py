from typing import Optional
from django.contrib.auth import get_user_model
from .models import Wallet

User = get_user_model()

PRODUCT_AI_INTERVIEW = "ai_interview"  # reuse this string everywhere
PRODUCT_CAREER_PATH = "career_path"

def get_remaining_attempts(user) -> Optional[int]:
    """
    Return the user's remaining attempts (int). If wallet missing, create one.
    """
    if not user.is_authenticated:
        return None
    w, _ = Wallet.objects.get_or_create(user=user)
    return w.total_attempts

def consume_attempt(user, amount: int = 1, product_code: str = PRODUCT_AI_INTERVIEW) -> bool:
    """
    Try to consume attempts; returns True on success.
    """
    if not user.is_authenticated:
        return False
    w, _ = Wallet.objects.get_or_create(user=user)
    return w.consume(product_code=product_code, n=amount)

def grant_plan(user, plan) -> None:
    """
    Grant attempts for a purchased plan (manual or after checkout).
    """
    w, _ = Wallet.objects.get_or_create(user=user)
    w.add_attempts(plan.attempts)
