from django.shortcuts import render , redirect, get_object_or_404
from django.http import HttpRequest, HttpResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import User, Group
from django.contrib.admin.views.decorators import staff_member_required
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
                is_approved=False
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

# Expert Related 

def experts_view(request):
    approved_experts = ExpertProfile.objects.filter(is_approved=True)
    pending_experts = None
    
    # If admin, bring all inactive experts 
    if request.user.is_staff or request.user.is_superuser:
        pending_experts = ExpertProfile.objects.filter(is_approved=False)

    # Filter
    specialization_id = request.GET.get("specialization")
    consultation_id = request.GET.get("consultation")

    if specialization_id:
        approved_experts = approved_experts.filter(specializations__id=specialization_id)
    if consultation_id:
        approved_experts = approved_experts.filter(consultation_types__id=consultation_id)



    return render(request, "accounts/experts.html", {"approved_experts": approved_experts,"pending_experts": pending_experts,"specializations": Specialization.objects.all(), "consultation_types": ConsultationType.objects.all(), "selected_spec": specialization_id, "selected_consult": consultation_id,})

@staff_member_required
def approve_expert(request, expert_id):
    expert = get_object_or_404(ExpertProfile, id=expert_id)
    expert.is_approved = True
    expert.save()
    return redirect("accounts:experts_view")

@staff_member_required
def deactivate_expert(request, expert_id):
    expert = get_object_or_404(ExpertProfile, id=expert_id)
    expert.is_approved = False
    expert.save()
    return redirect("accounts:experts_view")

def expert_detail_view(request, expert_id):
    expert = get_object_or_404(ExpertProfile, id=expert_id, is_approved=True)
    return render(request, "accounts/expert_detail.html", {"expert": expert})
