from django.shortcuts import render , redirect
from django.http import HttpRequest, HttpResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User, Group
from .models import StudentProfile, ExpertProfile, Specialization, ConsultationType
from django.contrib import messages

def login_view(request: HttpRequest):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        # Check username
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, "تم تسجيل الدخول بنجاح ")
            return redirect("main:home_view") 
        else:
            messages.error(request, "اسم المستخدم أو كلمة المرور غير صحيحة")

    return render(request, "accounts/login.html")


def registration_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password1 = request.POST.get("password1")
        password2 = request.POST.get("password2")
        user_type = request.POST.get("user_type")

        # Password Check 
        if password1 != password2:
            return render(request, "accounts/registration.html", {
                "error": "كلمة المرور غير متطابقة",
                "specializations": Specialization.objects.all(),
                "consultation_types": ConsultationType.objects.all(),
            })

        # Create user 
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password1,
            first_name=request.POST.get("first_name"),
            last_name=request.POST.get("last_name")
        )

        if user_type == "student":
            StudentProfile.objects.create(
                user=user,
                birth_date=request.POST.get("birth_date"),
                gender=request.POST.get("gender"),
                phone=request.POST.get("phone"),
                city=request.POST.get("city"),
                avatar=request.FILES.get("avatar"),
                bio=request.POST.get("bio"),
                study_stage=request.POST.get("study_stage"),
            )
            group = Group.objects.get(name="Students")
            user.groups.add(group)

        elif user_type == "expert":
            expert = ExpertProfile.objects.create(
                user=user,
                birth_date=request.POST.get("birth_date"),
                gender=request.POST.get("gender"),
                phone=request.POST.get("phone"),
                city=request.POST.get("city"),
                avatar=request.FILES.get("avatar"),
                bio=request.POST.get("bio"),
            )

            # Connect Relationship
            specs = request.POST.getlist("specializations")
            consults = request.POST.getlist("consultation_types")
            expert.specializations.set(specs)
            expert.consultation_types.set(consults)
            group = Group.objects.get(name="Experts")
            user.groups.add(group)

        return redirect("accounts:login_view")

    return render(request, "accounts/registration.html", {
        "specializations": Specialization.objects.all(),
        "consultation_types": ConsultationType.objects.all(),
    })

def logout_view(request):
    logout(request)
    messages.success(request, "تم تسجيل الخروج بنجاح")
    return redirect("accounts:login_view")  # رجع المستخدم لصفحة تسجيل الدخول
