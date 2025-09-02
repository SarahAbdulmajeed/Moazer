# subscriptions/payments.py
import requests
from django.conf import settings

class MoyasarError(Exception):
    pass

def create_invoice(plan, user, callback_url):
    """
    Creates a Moyasar invoice using SECRET KEY (Basic Auth).
    Amount is in halalas (SAR * 100).
    """
    amount = int(round(float(plan.price_sar) * 100))
    payload = {
        "amount": amount,
        "currency": "SAR",
        "description": f"Plan {plan.name} - {plan.attempts} attempts",
        "callback_url": callback_url,
        "metadata": {
            "user_id": user.id,
            "plan_id": plan.id,
        },
    }

    # حارس أخير قبل الإرسال
    sk = settings.MOYASAR_SECRET_KEY
    if not sk or len(sk) < 25:
        raise MoyasarError("Invalid MOYASAR_SECRET_KEY (empty/too short).")

    try:
        resp = requests.post(
            f"{settings.MOYASAR_API_BASE}/invoices",
            json=payload,
            auth=(sk, ""),      # Basic Auth = (secret_key, "")
            timeout=20,
        )
        # لو فيه خطأ من ميسر، اطبعي جسم الرد ليساعدنا
        if resp.status_code >= 400:
            raise MoyasarError(f"{resp.status_code} {resp.text}")
        return resp.json()
    except requests.RequestException as e:
        # DNS/شبكة… إلخ
        raise MoyasarError(str(e)) from e
