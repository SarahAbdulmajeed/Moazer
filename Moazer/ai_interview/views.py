from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404

from .models import (
    InterviewSession,
    SessionQuestion,
    InterviewAnswer,
    InterviewStatus,
)
from .ai_service import generate_questions, analyze_session

from subscriptions.services import (
    get_remaining_attempts,
    consume_attempt,
    PRODUCT_AI_INTERVIEW,
)


@login_required
def list_view(request):
    """
    List previous interview sessions for the current user.
    Also show remaining attempts (read-only) just for convenience.
    """
    items = InterviewSession.objects.filter(user=request.user).order_by("-created_at")
    remaining = get_remaining_attempts(request.user)  # int or None
    return render(request, "ai_interview/list.html", {"items": items, "remaining": remaining})


def start_view(request):
    """
    Start page:
      - POST: validate job title, try to consume 1 attempt, create session, generate 5 questions, redirect to Q1.
      - GET: render simple start form.
    """
    if request.method == "POST":
        job = (request.POST.get("job_title") or "").strip()
        if not job:
            messages.error(request, "الرجاء إدخال المسمى الوظيفي.")
            return redirect("ai_interview:start")

        # Consume 1 attempt before creating the session.
        # If user has no attempts, redirect them to plans page.
        ok = consume_attempt(request.user, amount=1, product_code=PRODUCT_AI_INTERVIEW)
        if not ok:
            messages.error(request, "انتهت محاولاتك. الرجاء الاشتراك بإحدى الباقات.")
            return redirect("subscriptions:plans")

        # Create a running session now that consumption succeeded
        s = InterviewSession.objects.create(
            user=request.user,
            job_title=job,
            status=InterviewStatus.RUNNING,
        )

        # Generate 5 questions (AI if available; fallback otherwise)
        qs = generate_questions(job_title=job, n=5)
        bulk = [SessionQuestion(session=s, order=i + 1, text=txt) for i, txt in enumerate(qs)]
        SessionQuestion.objects.bulk_create(bulk)

        return redirect("ai_interview:question", session_id=s.id, step=1)

    # GET
    return render(request, "ai_interview/start.html")


@login_required
@transaction.atomic
def question_view(request, session_id: int, step: int):
    """
    Single-question screen:
      - Shows question #step in the session.
      - Saves user's answer on POST and navigates to next step.
      - On last step, aggregates answers, runs AI analysis, marks session FINISHED, and redirects to result.
    """
    s = get_object_or_404(InterviewSession, pk=session_id, user=request.user)

    # Defensive: ensure questions exist (normally created in start_view)
    if s.questions.count() == 0:
        qs = generate_questions(job_title=s.job_title, n=5)
        bulk = [SessionQuestion(session=s, order=i + 1, text=txt) for i, txt in enumerate(qs)]
        SessionQuestion.objects.bulk_create(bulk)

    questions = list(s.questions.all())  # ordered by Meta
    total = len(questions)
    if not (1 <= step <= total):
        return redirect("ai_interview:question", session_id=s.id, step=1)

    q = questions[step - 1]

    if request.method == "POST":
        # Save or update this answer
        txt = (request.POST.get("answer") or "").strip()
        ans, _ = InterviewAnswer.objects.get_or_create(session=s, question=q)
        ans.answer = txt
        ans.save()

        # Move forward until last question
        if step < total:
            return redirect("ai_interview:question", session_id=s.id, step=step + 1)

        # Last step → aggregate answers and analyze
        qa_pairs = []
        for qq in questions:
            ans = InterviewAnswer.objects.filter(session=s, question=qq).first()
            qa_pairs.append({
                "order": qq.order,
                "question": qq.text,
                "answer": (ans.answer if ans else "") or "",
            })

        analysis = analyze_session(job_title=s.job_title, qa_pairs=qa_pairs)

        # Persist per-answer feedback
        per_answers = {a["order"]: a for a in analysis.get("answers", [])}
        for qq in questions:
            a = InterviewAnswer.objects.get(session=s, question=qq)
            fb = per_answers.get(qq.order, {})
            a.strengths = fb.get("strengths", "") or ""
            a.weaknesses = fb.get("weaknesses", "") or ""
            a.score = fb.get("score")
            a.save(update_fields=["strengths", "weaknesses", "score"])

        # Session-level summary
        sess = analysis.get("session", {})
        s.strengths = sess.get("strengths", "") or ""
        s.weaknesses = sess.get("weaknesses", "") or ""
        s.recommendation = sess.get("recommendation", "") or ""

        # If model forgot overall_score, compute from answers
        if sess.get("overall_score") is not None:
            s.overall_score = sess["overall_score"]
        else:
            # compute mean of existing scores
            vals = InterviewAnswer.objects.filter(session=s, score__isnull=False).values_list("score", flat=True)
            vals = list(vals)
            s.overall_score = round(sum(vals) / len(vals), 1) if vals else None

        s.status = InterviewStatus.FINISHED
        s.save(update_fields=["strengths", "weaknesses", "recommendation", "overall_score", "status"])

        return redirect("ai_interview:result", session_id=s.id)

    # Pre-fill previous answer if user navigated back
    prev = InterviewAnswer.objects.filter(session=s, question=q).first()
    ctx = {
        "s": s,
        "q": q,
        "step": step,
        "total": total,
        "prev_answer": prev.answer if prev else "",
    }
    return render(request, "ai_interview/question.html", ctx)


@login_required
def result_view(request, session_id: int):
    """
    Final result page showing:
      - job title, status, AI strengths/weaknesses/recommendation,
      - and Q/A log.
    """
    s = get_object_or_404(InterviewSession, pk=session_id, user=request.user)
    answers = (
        InterviewAnswer.objects.filter(session=s)
        .select_related("question")
        .order_by("question__order")
    )
    return render(request, "ai_interview/result.html", {"s": s, "answers": answers})
