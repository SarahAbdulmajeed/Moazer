from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Plan
from .services import grant_plan
from .forms import PlanForm

@login_required
def plans_view(request):
    """
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
    TEMP action: instantly grant attempts (no payment).
    Replace with payment flow later (e.g., return redirect to checkout).
    """
    plan = get_object_or_404(Plan, pk=plan_id)
    grant_plan(request.user, plan)
    messages.success(request, f"تم إضافة {plan.attempts} محاولة إلى محفظتك.")
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
