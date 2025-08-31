"""
Views for the 'Discover Your Path' feature.

Flow overview:
- landing_view: user chooses mode (School vs Grad).
- start_school_view: phase-1 generation for School mode (broad domains).
- start_grad_view: phase-1 generation for Grad mode (requires a university major).
- question_view: single-question workflow; expands into phase-2; finalizes and stores analysis.
- list_view: shows authenticated user's historical sessions.
- result_view: read-only details for a specific session (ownership enforced).

Wallet integration:
- A single attempt is consumed AFTER phase-1 questions have been generated successfully.
- Guests are allowed a single trial (tracked in the Django session).
"""

from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction

from .models import PathSession, PathQuestion, PathAnswer, PathStatus, PathMode
from .ai_service import (
    # SCHOOL mode
    generate_phase1_questions_school,
    pick_suggested_path_from_phase1,
    generate_phase2_questions_school,
    # GRAD mode
    generate_phase1_questions_grad,
    pick_subpath_within_major,
    generate_phase2_questions_grad,
    # Shared
    analyze_final_result,
)

from subscriptions.services import (
    get_remaining_attempts,
    consume_attempt,
    PRODUCT_CAREER_PATH,
)

# Tunable knobs
PHASE1_COUNT = 10
PHASE2_COUNT = 10
TOTAL = PHASE1_COUNT + PHASE2_COUNT


# --- Helpers -----------------------------------------------------------------------

def _ensure_session_key(request):
    """
    Guarantee a Django session key is available (used for guest ownership binding).
    """
    if not request.session.session_key:
        request.session.save()
    return request.session.session_key


def _trial_available_for_guest(request) -> bool:
    """
    Return True if a guest can still use the single free trial.
    We track this with a boolean flag in the Django session.
    """
    return (
        not request.user.is_authenticated
        and not request.session.get("career_path_trial_used", False)
    )


def _mark_guest_trial_used(request):
    """
    Mark the (guest) free trial as consumed in the current session.
    """
    request.session["career_path_trial_used"] = True
    request.session.modified = True


def _get_owned_session_or_404(request, session_id: int) -> PathSession:
    """
    Ownership-aware fetch:
    - Authenticated users: by FK = request.user.
    - Guests: by session key bound to the PathSession row.
    """
    if request.user.is_authenticated:
        return get_object_or_404(PathSession, pk=session_id, user=request.user)
    _ensure_session_key(request)
    return get_object_or_404(
        PathSession,
        pk=session_id,
        is_guest=True,
        guest_session_key=request.session.session_key,
    )


# --- Landing / Start ---------------------------------------------------------------

def landing_view(request):
    """
    Landing page where the user chooses between School and Grad modes.
    Shows remaining attempts for signed-in users.
    """
    remaining = get_remaining_attempts(request.user) if request.user.is_authenticated else None
    return render(request, "career_path/landing.html", {"remaining": remaining})


def start_school_view(request):
    """
    Start a School-mode session.
    - POST: generate phase-1 questions, create a session, consume 1 attempt (auth only), or mark guest trial.
    - GET: show a minimal CTA (and remaining attempts for signed-in users).
    """
    if request.method == "POST":
        # Authenticated path
        if request.user.is_authenticated:
            if (get_remaining_attempts(request.user) or 0) <= 0:
                messages.error(request, "انتهت محاولاتك. الرجاء الاشتراك بإحدى الباقات.")
                return redirect("subscriptions:plans")

            # Generate first to avoid charging the user on upstream failure.
            try:
                qs = generate_phase1_questions_school(PHASE1_COUNT)
            except Exception as e:
                messages.error(request, f"OpenAI error: {e}")
                return redirect("career_path:start_school")

            s = PathSession.objects.create(
                user=request.user,
                mode=PathMode.SCHOOL,
                status=PathStatus.RUNNING,
            )
            PathQuestion.objects.bulk_create(
                [PathQuestion(session=s, order=i + 1, phase=1, text=t) for i, t in enumerate(qs)]
            )
            # Now it's safe to consume 1 attempt
            consume_attempt(request.user, amount=1, product_code=PRODUCT_CAREER_PATH)
            return redirect("career_path:question", session_id=s.id, step=1)

        # Guest path (single trial)
        if not _trial_available_for_guest(request):
            messages.error(request, "انتهت التجربة المجانية. الرجاء الاشتراك بإحدى الباقات.")
            return redirect("subscriptions:plans")

        _ensure_session_key(request)
        try:
            qs = generate_phase1_questions_school(PHASE1_COUNT)
        except Exception as e:
            messages.error(request, f"OpenAI error: {e}")
            return redirect("career_path:start_school")

        s = PathSession.objects.create(
            is_guest=True,
            guest_session_key=request.session.session_key,
            mode=PathMode.SCHOOL,
            status=PathStatus.RUNNING,
        )
        PathQuestion.objects.bulk_create(
            [PathQuestion(session=s, order=i + 1, phase=1, text=t) for i, t in enumerate(qs)]
        )
        _mark_guest_trial_used(request)
        return redirect("career_path:question", session_id=s.id, step=1)

    # GET: show CTA and remaining attempts (if any)
    remaining = get_remaining_attempts(request.user) if request.user.is_authenticated else None
    return render(request, "career_path/start_school.html", {"remaining": remaining})


def start_grad_view(request):
    """
    Start a Grad-mode session (requires a 'major' field).
    - POST: validate major, generate phase-1 (within major), create a session, consume attempt or mark guest trial.
    - GET: simple form with 'major' input.
    """
    if request.method == "POST":
        major = (request.POST.get("major") or "").strip()
        if not major:
            messages.error(request, "الرجاء إدخال تخصصك الجامعي.")
            return redirect("career_path:start_grad")

        if request.user.is_authenticated:
            if (get_remaining_attempts(request.user) or 0) <= 0:
                messages.error(request, "انتهت محاولاتك. الرجاء الاشتراك بإحدى الباقات.")
                return redirect("subscriptions:plans")

            try:
                qs = generate_phase1_questions_grad(major, PHASE1_COUNT)
            except Exception as e:
                messages.error(request, f"OpenAI error: {e}")
                return redirect("career_path:start_grad")

            s = PathSession.objects.create(
                user=request.user,
                mode=PathMode.GRAD,
                major=major,
                status=PathStatus.RUNNING,
            )
            PathQuestion.objects.bulk_create(
                [PathQuestion(session=s, order=i + 1, phase=1, text=t) for i, t in enumerate(qs)]
            )
            consume_attempt(request.user, amount=1, product_code=PRODUCT_CAREER_PATH)
            return redirect("career_path:question", session_id=s.id, step=1)

        # Guest path (single trial)
        if not _trial_available_for_guest(request):
            messages.error(request, "انتهت التجربة المجانية. الرجاء الاشتراك بإحدى الباقات.")
            return redirect("subscriptions:plans")

        _ensure_session_key(request)
        try:
            qs = generate_phase1_questions_grad(major, PHASE1_COUNT)
        except Exception as e:
            messages.error(request, f"OpenAI error: {e}")
            return redirect("career_path:start_grad")

        s = PathSession.objects.create(
            is_guest=True,
            guest_session_key=request.session.session_key,
            mode=PathMode.GRAD,
            major=major,
            status=PathStatus.RUNNING,
        )
        PathQuestion.objects.bulk_create(
            [PathQuestion(session=s, order=i + 1, phase=1, text=t) for i, t in enumerate(qs)]
        )
        _mark_guest_trial_used(request)
        return redirect("career_path:question", session_id=s.id, step=1)

    # GET: render the 'major' input
    remaining = get_remaining_attempts(request.user) if request.user.is_authenticated else None
    return render(request, "career_path/start_grad.html", {"remaining": remaining})


# --- Question / Result -------------------------------------------------------------

@transaction.atomic
def question_view(request, session_id: int, step: int):
    """
    Single-question page:
    - Saves an answer on POST.
    - At the end of phase 1, classifies and generates phase-2 questions.
    - At the final step, runs the AI summary and marks the session FINISHED.
    """
    s = _get_owned_session_or_404(request, session_id)

    # Load current question set; phase-2 might be appended later.
    questions = list(s.questions.all())
    if not questions:
        messages.error(request, "لا توجد أسئلة في هذه الجلسة.")
        return redirect("career_path:landing")

    total = len(questions)
    step = max(1, min(step, total))
    q = questions[step - 1]

    if request.method == "POST":
        # Upsert the answer for the current question
        text = (request.POST.get("answer") or "").strip()
        ans, _ = PathAnswer.objects.get_or_create(session=s, question=q)
        ans.answer = text
        ans.save()

        # End of phase 1 and phase 2 hasn't been created yet
        if step == PHASE1_COUNT and total == PHASE1_COUNT:
            # Collect phase-1 answers in a single blob for classification
            phase1_answers = []
            for i in range(1, PHASE1_COUNT + 1):
                qq = next((x for x in questions if x.order == i), None)
                if not qq:
                    continue
                aa = PathAnswer.objects.filter(session=s, question=qq).first()
                phase1_answers.append(f"س{i}: {aa.answer if aa and aa.answer else ''}")
            joined_phase1 = "\n".join(phase1_answers)

            # Classify and generate phase-2 based on the mode
            try:
                if s.mode == PathMode.SCHOOL:
                    suggested = pick_suggested_path_from_phase1(joined_phase1)
                    qs2 = generate_phase2_questions_school(suggested, PHASE2_COUNT)
                else:
                    suggested = pick_subpath_within_major(s.major or "غير محدد", joined_phase1)
                    qs2 = generate_phase2_questions_grad(suggested, PHASE2_COUNT)
            except Exception as e:
                messages.error(request, f"تعذّر توليد المرحلة الثانية: {e}")
                return redirect("career_path:question", session_id=s.id, step=step)

            # Persist the chosen (sub)path and append phase-2 questions
            s.suggested_path = suggested
            s.save(update_fields=["suggested_path"])

            start_order = PHASE1_COUNT + 1
            PathQuestion.objects.bulk_create(
                [PathQuestion(session=s, order=start_order + i, phase=2, text=t) for i, t in enumerate(qs2)]
            )
            return redirect("career_path:question", session_id=s.id, step=step + 1)

        # If there are more questions, move forward
        questions = list(s.questions.all())
        total = len(questions)
        if step < total:
            return redirect("career_path:question", session_id=s.id, step=step + 1)

        # Final step: aggregate all answers and produce the final analysis
        all_answers = []
        for i in range(1, TOTAL + 1):
            qq = next((x for x in questions if x.order == i), None)
            if not qq:
                continue
            aa = PathAnswer.objects.filter(session=s, question=qq).first()
            all_answers.append(f"س{i}: {aa.answer if aa and aa.answer else ''}")
        joined = "\n".join(all_answers)

        try:
            result = analyze_final_result(s.suggested_path or "غير محدد", joined)
        except Exception as e:
            messages.error(request, f"تعذّر التحليل النهائي: {e}")
            return redirect("career_path:question", session_id=s.id, step=step)

        # Store final summary and close the session
        s.strengths = result.get("strengths", "")
        s.weaknesses = result.get("weaknesses", "")
        s.recommendation = result.get("recommendation", "")
        s.status = PathStatus.FINISHED
        s.save(update_fields=["strengths", "weaknesses", "recommendation", "status"])

        return redirect("career_path:result", session_id=s.id)

    # GET: prefill previous answer if user navigates back
    prev = PathAnswer.objects.filter(session=s, question=q).first()
    ctx = {
        "s": s,
        "q": q,
        "step": step,
        "total": max(len(questions), TOTAL),  # Keep progress bar stable at 20
        "prev_answer": prev.answer if prev else "",
    }
    return render(request, "career_path/question.html", ctx)


def list_view(request):
    """
    Authenticated users: show their historical sessions + remaining attempts.
    Guests: redirect to landing (they don't have a history).
    """
    if not request.user.is_authenticated:
        return redirect("career_path:landing")
    items = PathSession.objects.filter(user=request.user).order_by("-created_at")
    remaining = get_remaining_attempts(request.user)
    return render(request, "career_path/list.html", {"items": items, "remaining": remaining})


def result_view(request, session_id: int):
    """
    Read-only session details with ownership enforcement (auth vs guest).
    """
    s = _get_owned_session_or_404(request, session_id)
    answers = PathAnswer.objects.filter(session=s).select_related("question").order_by("question__order")
    return render(request, "career_path/result.html", {"s": s, "answers": answers})
