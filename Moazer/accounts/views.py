from django.shortcuts import render , redirect, get_object_or_404
from django.http import HttpRequest, HttpResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import User, Group
from django.contrib.admin.views.decorators import staff_member_required
from .models import StudentProfile, ExpertProfile, Specialization, ConsultationType
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from subscriptions.services import get_remaining_attempts
from django.contrib.auth.decorators import user_passes_test


def login_view(request: HttpRequest):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        # Check username
        user = authenticate(request, username=username, password=password)

        if user is not None:
            # Expert: Inactivate Account
            expert_profile = getattr(user, "expertprofile", None)
            if expert_profile and not expert_profile.is_approved:
                messages.error(request, "حسابك كخبير بانتظار التفعيل من الإدارة. لا يمكنك تسجيل الدخول حالياً.")
                return redirect("accounts:login_view")

            # Deleted Account (Experts)
            if expert_profile and getattr(expert_profile, "is_deleted", False):
                messages.error(request, "هذا الحساب تم حذفه. لا يمكنك تسجيل الدخول.")
                return redirect("accounts:login_view")

            # Deleted Account (Students)
            student_profile = getattr(user, "studentprofile", None)
            if student_profile and getattr(student_profile, "is_deleted", False):
                messages.error(request, "هذا الحساب تم حذفه. لا يمكنك تسجيل الدخول.")
                return redirect("accounts:login_view")


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

        # Passwords match check
        if password1 != password2:
            return render(request, "accounts/registration.html", {
                "error": "كلمة المرور غير متطابقة",
                "specializations": Specialization.objects.all(),
                "consultation_types": ConsultationType.objects.all(),
            })

        # Username unique check
        if User.objects.filter(username=username).exists():
            messages.error(request, "اسم المستخدم مستخدم مسبقاً")
            return render(request, "accounts/registration.html", {
                "specializations": Specialization.objects.all(),
                "consultation_types": ConsultationType.objects.all(),
            })

        # Email unique check
        if User.objects.filter(email=email).exists():
            messages.error(request, "البريد الإلكتروني مستخدم مسبقاً")
            return render(request, "accounts/registration.html", {
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

        avatar_file = request.FILES.get("avatar")

        # Student registration
        if user_type == "student":
            student_data = {
                "user": user,
                "birth_date": request.POST.get("birth_date"),
                "gender": request.POST.get("gender"),
                "phone": request.POST.get("phone"),
                "city": request.POST.get("city"),
                "bio": request.POST.get("bio"),
                "study_stage": request.POST.get("study_stage"),
            }
            if avatar_file:
                student_data["avatar"] = avatar_file

            StudentProfile.objects.create(**student_data)

            group = Group.objects.get(name="Students")
            user.groups.add(group)

        # Expert registration
        elif user_type == "expert":
            expert_data = {
                "user": user,
                "birth_date": request.POST.get("birth_date"),
                "gender": request.POST.get("gender"),
                "phone": request.POST.get("phone"),
                "city": request.POST.get("city"),
                "bio": request.POST.get("bio"),
                "is_approved": False,
                "iban_number": request.POST.get("iban_number"),
                "consultation_price": request.POST.get("consultation_price") or 0,
            }
            if avatar_file:
                expert_data["avatar"] = avatar_file

            expert = ExpertProfile.objects.create(**expert_data)

            # Connect relationships
            specs = request.POST.getlist("specializations")
            consults = request.POST.getlist("consultation_types")
            expert.specializations.set(specs)
            expert.consultation_types.set(consults)

            group = Group.objects.get(name="Experts")
            user.groups.add(group)

        messages.success(request, "تم إنشاء الحساب بنجاح ")
        return redirect("accounts:login_view")

    return render(request, "accounts/registration.html", {
        "specializations": Specialization.objects.all(),
        "consultation_types": ConsultationType.objects.all(),
    })

def logout_view(request):
    logout(request)
    messages.success(request, "تم تسجيل الخروج بنجاح")
    return redirect("accounts:login_view")  # رجع المستخدم لصفحة تسجيل الدخول

@login_required
def profile_view(request):
    user = request.user

    # Choose Profile Type
    try:
        profile = StudentProfile.objects.get(user=user)
        profile_type = "student"
    except StudentProfile.DoesNotExist:
        try:
            profile = ExpertProfile.objects.get(user=user)
            profile_type = "expert"
        except ExpertProfile.DoesNotExist:
            messages.error(request, "لا يوجد بروفايل لهذا المستخدم.")
            return redirect("main:home_view")

    # Update Informations 
    if request.method == "POST":
        # User Module - Update Information 
        user.first_name = request.POST.get("first_name")
        user.last_name = request.POST.get("last_name")
        user.email = request.POST.get("email")
        user.save()

        # Update Profile Information 
        profile.birth_date = request.POST.get("birth_date")
        profile.gender = request.POST.get("gender")
        profile.phone = request.POST.get("phone")
        profile.city = request.POST.get("city")
        profile.bio = request.POST.get("bio")

        avatar_file = request.FILES.get("avatar")
        if avatar_file:
            profile.avatar = avatar_file

        if profile_type == "student":
            profile.study_stage = request.POST.get("study_stage")
        elif profile_type == "expert":
            profile.specializations.set(request.POST.getlist("specializations"))
            profile.consultation_types.set(request.POST.getlist("consultation_types"))
            profile.consultation_price = request.POST.get("consultation_price") or 0
            profile.iban_number = request.POST.get("iban_number")

        profile.save()
        messages.success(request, "تم حفظ التغييرات بنجاح")
        return redirect("accounts:profile")

    context = {
        "profile": profile,
        "profile_type": profile_type,
        "all_specializations": Specialization.objects.all() if profile_type == "expert" else [],
        "all_consultation_types": ConsultationType.objects.all() if profile_type == "expert" else [],
    }
    return render(request, "accounts/profile.html", context)


@login_required
def delete_profile(request):
    if request.method == "POST":
        user = request.user
        
        # Mark profile deleted
        profile = getattr(user, "expertprofile", None) or getattr(user, "studentprofile", None)
        if profile:
            profile.is_deleted = True
            if hasattr(profile, "is_approved"):
                profile.is_approved = False
            profile.save()
            
        # Logout user
        logout(request)
        messages.success(request, "تم حذف حسابك بنجاح")
        return redirect("main:home_view")

    return redirect("accounts:profile_view")
 
def experts_view(request):
    """
    Experts list view with separate filters for each category:
    - Approved experts (visible to all).
    - Pending experts (only for admin).
    - Deleted experts (only for admin).
    """

    # Base queries
    approved_experts = ExpertProfile.objects.filter(is_approved=True, is_deleted=False)
    pending_experts = None
    deleted_experts = None

    if request.user.is_staff or request.user.is_superuser:
        pending_experts = ExpertProfile.objects.filter(is_approved=False, is_deleted=False)
        deleted_experts = ExpertProfile.objects.filter(is_deleted=True)

    # Filters for approved experts
    specialization_id = request.GET.get("specialization_approved")
    consultation_id = request.GET.get("consultation_approved")
    if specialization_id:
        approved_experts = approved_experts.filter(specializations__id=specialization_id)
    if consultation_id:
        approved_experts = approved_experts.filter(consultation_types__id=consultation_id)

    # Filters for pending experts
    specialization_id_p = request.GET.get("specialization_pending")
    consultation_id_p = request.GET.get("consultation_pending")
    if pending_experts is not None:
        if specialization_id_p:
            pending_experts = pending_experts.filter(specializations__id=specialization_id_p)
        if consultation_id_p:
            pending_experts = pending_experts.filter(consultation_types__id=consultation_id_p)

    # Filters for deleted experts
    specialization_id_d = request.GET.get("specialization_deleted")
    consultation_id_d = request.GET.get("consultation_deleted")
    if deleted_experts is not None:
        if specialization_id_d:
            deleted_experts = deleted_experts.filter(specializations__id=specialization_id_d)
        if consultation_id_d:
            deleted_experts = deleted_experts.filter(consultation_types__id=consultation_id_d)

    return render(
        request,
        "accounts/experts.html",
        {
            "approved_experts": approved_experts,
            "pending_experts": pending_experts,
            "deleted_experts": deleted_experts,
            "specializations": Specialization.objects.all(),
            "consultation_types": ConsultationType.objects.all(),
            "selected_spec": specialization_id,
            "selected_consult": consultation_id,
            "selected_spec_p": specialization_id_p,
            "selected_consult_p": consultation_id_p,
            "selected_spec_d": specialization_id_d,
            "selected_consult_d": consultation_id_d,
        }
    )

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

from django.http import Http404


def expert_detail_view(request, expert_id):
    expert = get_object_or_404(ExpertProfile, id=expert_id)

    # If expert is deleted or not approved and user is not admin → show error page
    if (expert.is_deleted or not expert.is_approved) and not request.user.is_staff:
        return render(request, "main/error.html")

    return render(request, "accounts/expert_detail.html", {"expert": expert})

# -------------------------------------------------------
# Admin-only: Show all students with filters
# -------------------------------------------------------
# Only allow staff (admin) to access this view
@user_passes_test(lambda u: u.is_staff)
def students_view(request):
    qs = StudentProfile.objects.filter(is_deleted=False).select_related("user").order_by("-created_at")

    # Apply filters
    stage = request.GET.get("stage")
    if stage:
        qs = qs.filter(study_stage=stage)

    city = request.GET.get("city")
    if city:
        qs = qs.filter(city__icontains=city)

    # Distinct cities for dropdown
    cities = StudentProfile.objects.values_list("city", flat=True).distinct()

    # Attach attempts count for each student 
    students_data = []
    for s in qs:
        attempts = get_remaining_attempts(s.user)  # fetch current attempts for this student
        students_data.append({
            "profile": s,
            "attempts": attempts or 0,   # default to 0 if None
        })

    return render(
        request,
        "accounts/students.html",
        {
            "students": students_data,
            "stages": StudentProfile.STAGES,
            "selected_stage": stage,
            "cities": cities,
            "selected_city": city,
        }
    )
