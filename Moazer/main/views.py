from django.shortcuts import render , redirect
from django.http import HttpRequest, HttpResponse
from django.contrib.auth.models import Group
from django.db.models import Count,Sum
from django.utils import timezone
import datetime
from django.db.models.functions import TruncMonth

from career_path.models import PathSession
from ai_interview.models import InterviewSession
from consultations.models import Consultation

def home_view(request: HttpRequest):
    for name in ["Students", "Experts"]:
        Group.objects.get_or_create(name=name)

    user = request.user
    group_name = user.groups.first().name if user.groups.exists() else None
    context = {"group_name": group_name}

    if group_name == "Students":
        context.update({
            "total_paths": PathSession.objects.filter(user=user).count(),
            "total_interviews": InterviewSession.objects.filter(user=user).count(),
            "total_consultations": Consultation.objects.filter(student=user).count(),
            "last_path": PathSession.objects.filter(user=user).order_by("-created_at").first(),
            "last_interview": InterviewSession.objects.filter(user=user).order_by("-created_at").first(),
        })

    elif group_name == "Experts":
        context.update({
            "total_consultations": Consultation.objects.filter(expert=user).count(),
            "active_consultations": Consultation.objects.filter(expert=user, status="ACTIVE").count(),
            "completed_consultations": Consultation.objects.filter(expert=user, status="COMPLETED").count(),
        })

        today = timezone.now().date().replace(day=1)
        months = [today - datetime.timedelta(days=30*i) for i in range(5, -1, -1)]
        labels = [m.strftime("%b %Y") for m in months]
        income_data = []

        for m in months:
            next_month = (m + datetime.timedelta(days=32)).replace(day=1)
            total_income = (
                Consultation.objects.filter(expert=user, created_at__gte=m, created_at__lt=next_month)
                .aggregate(total=Sum("price_at_booking"))["total"] or 0
            )
            income_data.append(float(total_income))

        context.update({
            "income_labels": labels,
            "income_data": income_data,
        })

        consultation_stats = (
            Consultation.objects.filter(expert=user)
            .values("type")
            .annotate(total=Count("id"))
        )
        consultation_labels = [
            dict(Consultation._meta.get_field("type").choices).get(c["type"], c["type"])
            for c in consultation_stats
        ]
        consultation_data = [c["total"] for c in consultation_stats]

        context.update({
            "consultation_labels": consultation_labels,
            "consultation_data": consultation_data,
        })

    if user.is_staff or user.is_superuser:
        students_group = Group.objects.get(name="Students")
        experts_group = Group.objects.get(name="Experts")

        context.update({
            "platform_total_consultations": Consultation.objects.count(),
            "platform_total_paths": PathSession.objects.count(),
            "platform_total_interviews": InterviewSession.objects.count(),
            "platform_total_students": students_group.user_set.count(),
            "platform_total_experts": experts_group.user_set.count(),
        })

        today = timezone.now().date().replace(day=1) 
        months = [today - datetime.timedelta(days=30*i) for i in range(5, -1, -1)]
        labels = [m.strftime("%b %Y") for m in months]

        students_data = []
        experts_data = []

        for m in months:
            next_month = (m + datetime.timedelta(days=32)).replace(day=1)
            students_count = students_group.user_set.filter(
                date_joined__gte=m, date_joined__lt=next_month
            ).count()
            experts_count = experts_group.user_set.filter(
                date_joined__gte=m, date_joined__lt=next_month
            ).count()
            students_data.append(students_count)
            experts_data.append(experts_count)

        context.update({
            "growth_labels": labels,
            "growth_students": students_data,
            "growth_experts": experts_data,
        })

    return render(request, "main/index.html", context)

def error_view(request: HttpRequest):
    return render(request, "main/error.html")