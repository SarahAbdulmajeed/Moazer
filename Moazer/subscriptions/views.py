import decimal
import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, redirect, get_object_or_404
from .models import Plan, SubscriptionPurchase
from .services import grant_plan
from .services import create_moyasar_invoice
from django.urls import reverse

from .models import Plan, SubscriptionPurchase
from .payments import create_invoice

MOYASAR_API = "https://api.moyasar.com/v1"

from .forms import PlanForm

@login_required
def plans_view(request):
    """
    Show available plans. Each plan has a 'Pay with Moyasar' button.
    Show available plans. If admin: allow adding new plans directly.§
    """
    plans = Plan.objects.order_by("price_sar")

    form = None
    if request.user.is_staff:
        if request.method == "POST":
            form = PlanForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, "تمت إضافة الباقة بنجاح.")
                return redirect("subscriptions:plans")
        else:
            form = PlanForm()

    return render(request, "subscriptions/plans.html", {
        "plans": plans,
        "form": form,
        "is_admin": request.user.is_staff,
    })

@login_required
def subscribe_view(request, plan_id: int):
    """
    Legacy TEMP action (no payment). Keep it for backups/smoke tests.
    """
    plan = get_object_or_404(Plan, pk=plan_id)
    try:
        inv = create_moyasar_invoice(request.user, plan)
        pay_url = inv.get("invoice_url") or inv.get("url") or inv.get("source", {}).get("company", {}).get("url")
        if not pay_url:
            messages.error(request, "تعذّر قراءة رابط الدفع من استجابة ميسّر.")
            return redirect("subscriptions:plans")
        return redirect(pay_url)
    except Exception as e:
        messages.error(request, f"تعذّر إنشاء الفاتورة: {e}")
        return redirect("subscriptions:plans")


@login_required
def create_invoice_and_redirect(request, plan_id: int):
    if request.method != "POST":
        return redirect("subscriptions:plans")

    plan = get_object_or_404(Plan, pk=plan_id)

    amount_halalas = int(decimal.Decimal(plan.price_sar) * 100)

    # ✅ رابط مطلق للـ callback
    callback_url = request.build_absolute_uri(reverse("subscriptions:callback"))
    description = f"خطة: {plan.name} — {plan.attempts} محاولة"

    try:
        resp = requests.post(
            f"{MOYASAR_API}/invoices",
            auth=(settings.MOYASAR_SECRET_KEY, ""),
            json={
                "amount": amount_halalas,
                "currency": "SAR",
                "description": description,
                "callback_url": callback_url,
                "metadata": {
                    "user_id": request.user.id,
                    "plan_id": plan.id,
                    "mode": "attempts-topup",
                },
            },
            timeout=20,
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        messages.error(request, f"تعذّر إنشاء الفاتورة: {e}")
        return redirect("subscriptions:plans")

    data = resp.json() or {}
    invoice_id = data.get("id")
    invoice_url = data.get("url")

    if not invoice_id or not invoice_url:
        messages.error(request, "استجابة غير متوقعة من بوابة الدفع.")
        return redirect("subscriptions:plans")

    SubscriptionPurchase.objects.get_or_create(
        invoice_id=invoice_id,
        defaults={
            "user": request.user,
            "plan": plan,
            "status": data.get("status", "created"),
            "amount_sar": plan.price_sar,
        },
    )

    return redirect(invoice_url)

@login_required
def callback_view(request):
    """
    User returns here after paying (or canceling).
    We read ?id=<invoice_id>, verify with Moyasar, and grant attempts if paid.
    """
    invoice_id = request.GET.get("id", "").strip()
    if not invoice_id:
        messages.error(request, "المعرف غير موجود في الرابط.")
        return redirect("subscriptions:plans")

    # Fetch invoice details from Moyasar
    try:
        resp = requests.get(
            f"{MOYASAR_API}/invoices/{invoice_id}",
            auth=(settings.MOYASAR_SECRET_KEY, ""),
            timeout=15,
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        messages.error(request, f"فشل التحقق من الفاتورة: {e}")
        return redirect("subscriptions:plans")

    data = resp.json() or {}
    status = data.get("status")

    # Find local purchase row
    purchase = get_object_or_404(SubscriptionPurchase, invoice_id=invoice_id, user=request.user)

    # Update status
    if status and purchase.status != status:
        purchase.status = status
        purchase.save(update_fields=["status"])

    # Grant attempts once if paid
    if status == "paid" and not purchase.granted:
        grant_plan(request.user, purchase.plan)
        purchase.granted = True
        purchase.save(update_fields=["granted"])
        messages.success(request, f"تم الدفع بنجاح! أضفنا {purchase.plan.attempts} محاولة إلى محفظتك.")
        return redirect("subscriptions:plans")

    if status == "paid" and purchase.granted:
        messages.info(request, "هذه الفاتورة سبق تمت معالجتها ومنح المحاولات.")
        return redirect("subscriptions:plans")

    # Not paid (e.g., failed, canceled, pending)
    messages.warning(request, f"حالة الفاتورة: {status or 'غير معروفة'}.")
    return redirect("subscriptions:plans")

@staff_member_required
def delete_plan_view(request, plan_id: int):
    """
    Admin-only: delete a subscription plan.
    """
    plan = get_object_or_404(Plan, pk=plan_id)
    plan.delete()
    messages.success(request, f"تم حذف الباقة ({plan.name}) بنجاح.")
    return redirect("subscriptions:plans")
