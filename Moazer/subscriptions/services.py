from typing import Optional
from django.contrib.auth import get_user_model
from .models import Wallet
import requests
from django.conf import settings

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

class MoyasarError(Exception):
    pass

def create_moyasar_invoice(user, plan) -> dict:
    """
    Create an invoice in Moyasar using Secret Key via Basic Auth.
    Returns the JSON response. Raises MoyasarError on failure.
    """
    url = f"{settings.MOYASAR_API_BASE}/invoices"
    payload = {
        "amount": int(plan.price_sar * 100),  # هللة
        "currency": "SAR",
        "description": f"Plan {plan.name} - {plan.attempts} attempts",
        "callback_url": settings.MOYASAR_CALLBACK_URL,
        # "redirect_url": "http://127.0.0.1:8000/subscriptions/thanks/",
        "metadata": {
            "user_id": user.id,
            "plan_id": plan.id,
        },
    }

    try:
        # أهم سطر: auth=(SECRET_KEY, "")
        r = requests.post(url, json=payload, auth=(settings.MOYASAR_SECRET_KEY, ""))
        if r.status_code >= 400:
            # اطبع الرد للمساعدة
            raise MoyasarError(f"{r.status_code} {r.text}")
        return r.json()
    except requests.RequestException as e:
        raise MoyasarError(str(e)) from e