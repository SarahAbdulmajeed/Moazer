from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Plan
from .services import grant_plan

@login_required
def plans_view(request):
    """
    Show available plans. For now, clicking "subscribe" will grant attempts directly.
    Later you swap the button to go to a checkout page and call grant_plan after success.
    """
    plans = Plan.objects.order_by("price_sar")
    return render(request, "subscriptions/plans.html", {"plans": plans})

@login_required
def subscribe_view(request, plan_id: int):
    """
    TEMP action: instantly grant attempts (no payment).
    Replace with payment flow later (e.g., return redirect to checkout).
    """
    plan = get_object_or_404(Plan, pk=plan_id)
    grant_plan(request.user, plan)
    messages.success(request, f"تم إضافة {plan.attempts} محاولة إلى محفظتك.")
    return redirect("subscriptions:plans")
