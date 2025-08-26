from django.shortcuts import render , redirect
from django.http import HttpRequest, HttpResponse
from .forms import UserForm, StudentProfileForm, ExpertProfileForm
from .models import StudentProfile, ExpertProfile



def home_view(request: HttpRequest):
	return HttpResponse("Hello World!")


def profile_view(request):
    if not request.user.is_authenticated:
        return render(request, "main/visitor.html")
    user = request.user
    role = user.role 

    if role == "student":
        student_profile, _ = StudentProfile.objects.get_or_create(user=user)
        if request.method == "POST":
            u_form = UserForm(request.POST, request.FILES, instance=user)
            s_form = StudentProfileForm(request.POST, instance=student_profile)
            if u_form.is_valid() and s_form.is_valid():
                u_form.save()
                s_form.save()
                return redirect('profile')
        else:
            u_form = UserForm(instance=user)
            s_form = StudentProfileForm(instance=student_profile)
        return render(request, "main/student_profile.html", {"u_form": u_form, "s_form": s_form})

    elif role == "expert":
        expert_profile, _ = ExpertProfile.objects.get_or_create(user=user)
        if request.method == "POST":
            u_form = UserForm(request.POST, request.FILES, instance=user)
            e_form = ExpertProfileForm(request.POST, instance=expert_profile)
            if u_form.is_valid() and e_form.is_valid():
                u_form.save()
                e_form.save()
                return redirect('profile')
        else:
            u_form = UserForm(instance=user)
            e_form = ExpertProfileForm(instance=expert_profile)
        return render(request, "main/expert_profile.html", {"u_form": u_form, "e_form": e_form})

    else:
        return render(request, "main/visitor.html")
    
def delete_profile(request):
    if request.method == "POST" and request.user.is_authenticated:
        user = request.user
        user.delete()   
        return redirect('main:home_view') 
    return redirect('main:profile')

