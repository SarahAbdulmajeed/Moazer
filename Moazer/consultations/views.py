from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.template.loader import render_to_string
from django.http import HttpResponse, HttpResponseForbidden
from .models import (
    Consultation,
    ChatMessage,
    Attachment,
    ConsultationRating,
    ConsultationStatus,
    ConsultationTypeChoices,
)
from django.contrib.auth import get_user_model
from accounts.models import ExpertProfile, StudentProfile  

def is_student(user) -> bool:
    """
    Check if user is a student via Group('Students') OR profile existence.
    """
    return (
        user.groups.filter(name="Students").exists()
        or StudentProfile.objects.filter(user=user).exists()
    )

def is_expert(user) -> bool:
    """
    Check if user is an expert via Group('Experts') OR profile existence.
    """
    return (
        user.groups.filter(name="Experts").exists()
        or ExpertProfile.objects.filter(user=user).exists()
    )

# -------------------------------------------------------------------
# List consultations for the current user.
# - If the user is the expert (placeholder logic by username), show
#   consultations where they are assigned as expert.
# - Otherwise, show consultations created by the student.
# -------------------------------------------------------------------

@login_required
def list_view(request):
    """
    List consultations filtered by actual role (student vs expert).
    """
    if is_expert(request.user):
        qs = Consultation.objects.filter(expert=request.user).order_by("-updated_at")
        role_flag = True
    else:
        # default to student-view (إن لم يكن خبير)
        qs = Consultation.objects.filter(student=request.user).order_by("-updated_at")
        role_flag = False

    # Filter based on status
    status = request.GET.get("status")
    if status:
        qs = qs.filter(status=status)

    # Filter based on type
    ctype = request.GET.get("type")
    if ctype:
        qs = qs.filter(type=ctype)

    qs = qs.order_by("-updated_at")


    return render(request, "consultations/list.html", {"items": qs, "is_expert": role_flag, "status_choices": ConsultationStatus.choices, "ctype_choices": ConsultationTypeChoices.choices, "selected_status": status, "selected_type": ctype})

# -------------------------------------------------------------------
# Create a consultation for a specific expert (expert_id comes via URL).
# - The expert is selected from the experts list page (outside this app).
# - Supports multi-file attachments via input name="files" (multiple).
# - On success, redirects to the consultation detail page.
# -------------------------------------------------------------------
@login_required
def create_view(request, expert_id: int):
    """
    Create a consultation for a specific expert (must be a student).
    """
    # Only students can create a consultation
    if not is_student(request.user):
        messages.error(request, "فقط الطالب يمكنه طلب استشارة.")
        return redirect("consultations:list_view")

    # Ensure expert_id belongs to a real expert (by profile/group)
    expert_profile = ExpertProfile.objects.filter(user_id=expert_id).select_related("user").first()
    if not expert_profile:
        messages.error(request, "المستخدم المحدد ليس خبيرًا.")
        return redirect("consultations:list_view")

    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        description = request.POST.get("description", "").strip()
        ctype = request.POST.get("type")

        if not title or not ctype:
            messages.error(request, "الرجاء تعبئة الحقول المطلوبة.")
            return redirect("consultations:create_view", expert_id=expert_id)

        cons = Consultation.objects.create(
            student=request.user,
            expert_id=expert_id,
            title=title,
            description=description,
            type=ctype,
            status=ConsultationStatus.PENDING,
            price_at_booking=expert_profile.consultation_price,
        )

        for f in request.FILES.getlist("files"):
            Attachment.objects.create(consultation=cons, uploaded_by=request.user, file=f)

        messages.success(request, "تم إنشاء الاستشارة.")
        return redirect("consultations:detail_view", consultation_id=cons.id)

    return render(request, "consultations/create.html", {"ctype_choices": ConsultationTypeChoices.choices})

# -------------------------------------------------------------------
# Consultation detail + chat thread.
# - Only the student or the assigned expert can view.
# - Handles:
#   * send_message       → append a ChatMessage
#   * end_consultation   → student ends; redirects to rating page
#   * expert_accept      → expert moves to ACTIVE
#   * expert_reject      → expert closes
#   * expert_end         → expert marks as COMPLETED (no rating)
# -------------------------------------------------------------------
@login_required
def detail_view(request, consultation_id: int):
    c = get_object_or_404(Consultation, pk=consultation_id)

    # Only participants may view
    if c.student_id != request.user.id and c.expert_id != request.user.id:
        messages.error(request, "غير مسموح.")
        return redirect("consultations:list_view")

    user_is_expert = (request.user.id == c.expert_id)
    user_is_student = (request.user.id == c.student_id)

    # Flags for template (avoid string-membership bugs in template)
    allow_student_end = (user_is_student and c.status == ConsultationStatus.ACTIVE)
    allow_expert_end = (user_is_expert and c.status in [ConsultationStatus.ACTIVE, ConsultationStatus.PENDING])
    allow_expert_decide = (user_is_expert and c.status == ConsultationStatus.PENDING)

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "send_message":
            text = request.POST.get("message", "").strip()
            if text:
                ChatMessage.objects.create(consultation=c, sender=request.user, content=text)
            return redirect("consultations:detail_view", consultation_id=c.id)

        if action == "end_consultation":
            if not user_is_student:
                messages.error(request, "فقط الطالب يمكنه إنهاء الاستشارة.")
                return redirect("consultations:detail_view", consultation_id=c.id)
            return redirect("consultations:rate_view", consultation_id=c.id)

        if action == "expert_accept" and allow_expert_decide:
            c.status = ConsultationStatus.ACTIVE
            c.save(update_fields=["status"])
            return redirect("consultations:detail_view", consultation_id=c.id)

        if action == "expert_reject" and allow_expert_decide:
            c.status = ConsultationStatus.CLOSED
            c.save(update_fields=["status"])
            return redirect("consultations:detail_view", consultation_id=c.id)

        if action == "expert_end" and allow_expert_end:
            c.status = ConsultationStatus.COMPLETED
            c.save(update_fields=["status"])
            messages.success(request, "تم إنهاء الاستشارة من طرف الخبير.")
            return redirect("consultations:detail_view", consultation_id=c.id)

    return render(
        request,
        "consultations/detail.html",
        {
            "c": c,
            "is_expert": user_is_expert,
            "allow_student_end": allow_student_end,
            "allow_expert_end": allow_expert_end,
            "allow_expert_decide": allow_expert_decide,
        },
    )

# -------------------------------------------------------------------
# Rating page (stars only, no comment).
# - Only the student can rate.
# - On submit: upsert rating to 1..5 and mark consultation COMPLETED.
# - Uses minimal validation to prevent DB integrity errors.
# -------------------------------------------------------------------
@login_required
def rate_view(request, consultation_id: int):
    """
    Star-only rating endpoint.
    - Only the student who owns the consultation can rate.
    - Accepts a POST with 'rating' ∈ {1..5}.
    - Upserts ConsultationRating, then marks the consultation as COMPLETED.
    """
    consultation = get_object_or_404(Consultation, pk=consultation_id)

    # Authorization guard: only the student may rate
    if request.user.id != consultation.student_id:
        messages.error(request, "فقط الطالب يقيّم الاستشارة.")
        return redirect("consultations:detail_view", consultation_id=consultation.id)

    if request.method == "POST":
        # Extract and validate rating (server-side safety)
        val = request.POST.get("rating")
        if val not in {"1", "2", "3", "4", "5"}:
            messages.error(request, "اختَر تقييمًا من 1 إلى 5.")
            return redirect("consultations:rate_view", consultation_id=consultation.id)

        stars = int(val)

        # Upsert rating; using defaults ensures 'stars' is never NULL on create
        ConsultationRating.objects.update_or_create(
            consultation=consultation,
            defaults={"stars": stars, "comment": ""},  # comment intentionally empty
        )

        # Mark consultation as completed
        consultation.status = ConsultationStatus.COMPLETED
        consultation.save(update_fields=["status"])

        messages.success(request, "تم إنهاء الاستشارة وتسجيل التقييم.")
        return redirect("consultations:detail_view", consultation_id=consultation.id)

    # GET → render the star picker page
    return render(request, "consultations/rate.html", {"c": consultation})


# -------------------------------------------------------------------
# Lightweight polling endpoint that returns only the chat messages HTML.
# - Used by detail page to refresh the chat box via JS without full reload.
# - Returns 403 if the current user is not a participant.
# -------------------------------------------------------------------
@login_required
def messages_partial_view(request, consultation_id: int):
    c = get_object_or_404(Consultation, pk=consultation_id)
    # Authorization: only participants can poll the messages.
    if c.student_id != request.user.id and c.expert_id != request.user.id:
        return HttpResponseForbidden("Forbidden")

    html = render_to_string("consultations/messages.html", {"c": c}, request=request)
    return HttpResponse(html)

@login_required
def overview_view(request):
    """
    صفحة مختصرة تعرض:
      - آخر الاستشارات (5 عناصر)
      - قائمة خبراء مختصرة (5 عناصر)
    وتحت كل قسم زر "المزيد".
    """
    user_is_expert = is_expert(request.user)

    if user_is_expert:
        cons_qs = Consultation.objects.filter(expert=request.user)
    else:
        cons_qs = Consultation.objects.filter(student=request.user)

    cons_qs = cons_qs.order_by("-updated_at")[:5]

    experts_qs = (
        ExpertProfile.objects
        .filter(is_approved=True)
        .select_related("user")
        .prefetch_related("specializations", "consultation_types")
        .order_by("-rating_avg", "-rating_count", "user__id")[:5]
    )

    context = {
        "is_expert": user_is_expert,
        "consultations_preview": cons_qs,
        "experts_preview": experts_qs,
    }
    return render(request, "consultations/overview.html", context)