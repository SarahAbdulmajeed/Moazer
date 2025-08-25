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

# -------------------------------------------------------------------
# List consultations for the current user.
# - If the user is the expert (placeholder logic by username), show
#   consultations where they are assigned as expert.
# - Otherwise, show consultations created by the student.
# -------------------------------------------------------------------
@login_required
def list_view(request):
    # TODO: Replace this placeholder check with your real role/permission logic.
    is_expert = (request.user.username == "expert")

    if is_expert:
        qs = Consultation.objects.filter(expert=request.user).order_by("-updated_at")
    else:
        qs = Consultation.objects.filter(student=request.user).order_by("-updated_at")

    return render(request, "consultations/list.html", {"items": qs, "is_expert": is_expert})


# -------------------------------------------------------------------
# Create a consultation for a specific expert (expert_id comes via URL).
# - The expert is selected from the experts list page (outside this app).
# - Supports multi-file attachments via input name="files" (multiple).
# - On success, redirects to the consultation detail page.
# -------------------------------------------------------------------
@login_required
def create_view(request, expert_id: int):
    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        description = request.POST.get("description", "").strip()
        ctype = request.POST.get("type")

        if not title or not ctype:
            messages.error(request, "الرجاء تعبئة الحقول المطلوبة.")
            return redirect("consultations:create_view", expert_id=expert_id)

        # Create the consultation in 'PENDING' state until expert accepts.
        cons = Consultation.objects.create(
            student=request.user,
            expert_id=expert_id,
            title=title,
            description=description,
            type=ctype,
            status=ConsultationStatus.PENDING,  # awaiting expert decision
        )

        # Handle multiple attachments, if any.
        for f in request.FILES.getlist("files"):
            Attachment.objects.create(
                consultation=cons,
                uploaded_by=request.user,
                file=f,
            )

        messages.success(request, "تم إنشاء الاستشارة.")
        return redirect("consultations:detail_view", consultation_id=cons.id)

    # Provide type choices to the template for the select field.
    return render(
        request,
        "consultations/create.html",
        {"ctype_choices": ConsultationTypeChoices.choices},
    )


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

    # Authorization: only participants can access.
    if c.student_id != request.user.id and c.expert_id != request.user.id:
        messages.error(request, "غير مسموح.")
        return redirect("consultations:list_view")
    
    # Convenience flag used by the template and actions below.
    is_expert = (request.user.id == c.expert_id)

    if request.method == "POST":
        action = request.POST.get("action")

        # Send a chat message (empty messages are ignored).
        if action == "send_message":
            text = request.POST.get("message", "").strip()
            if text:
                ChatMessage.objects.create(consultation=c, sender=request.user, content=text)
            return redirect("consultations:detail_view", consultation_id=c.id)

        # Student ends → go to rating (star-only page).
        if action == "end_consultation":
            if request.user.id != c.student_id:
                messages.error(request, "فقط الطالب يمكنه إنهاء الاستشارة.")
                return redirect("consultations:detail_view", consultation_id=c.id)
            return redirect("consultations:rate_view", consultation_id=c.id)

        # Expert accepts → move to ACTIVE.
        if action == "expert_accept" and is_expert and c.status == ConsultationStatus.PENDING:
            c.status = ConsultationStatus.ACTIVE
            c.save(update_fields=["status"])
            return redirect("consultations:detail_view", consultation_id=c.id)
        
        # Expert rejects → move to CLOSED (allowed from NEW/PENDING).
        if action == "expert_reject" and is_expert and c.status in [ConsultationStatus.PENDING, ConsultationStatus.NEW]:
            c.status = ConsultationStatus.CLOSED
            c.save(update_fields=["status"])
            return redirect("consultations:detail_view", consultation_id=c.id)
        
        # Expert ends immediately (no rating flow for expert).
        if action == "expert_end" and is_expert:
                c.status = ConsultationStatus.COMPLETED
                c.save(update_fields=["status"])
                messages.success(request, "تم إنهاء الاستشارة من طرف الخبير.")
                return redirect("consultations:detail_view", consultation_id=c.id)
        
    return render(
        request,
        "consultations/detail.html",
        {"c": c, "is_expert": is_expert},
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
# Temporary experts list (stub) to test the flow without the real experts page.
# - Lists users whose username contains 'expert'.
# - Each card links to create_view(expert_id).
# -------------------------------------------------------------------
from django.contrib.auth import get_user_model
@login_required
def experts_stub_view(request):
    """
    صفحة خبراء مؤقتة للاختبار :

    """
    U = get_user_model()
    experts = U.objects.filter(username__icontains="expert").order_by("id")
    return render(request, "consultations/experts_stub.html", {"experts": experts})


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
