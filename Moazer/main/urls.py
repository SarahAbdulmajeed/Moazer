from . import views  
from django.urls import path
from django.shortcuts import render
from .forms import UserForm, ExpertProfileForm, StudentProfileForm

app_name = "main"

urlpatterns = [ 
		#path(URL Route*, View*)
    path('', views.home_view, name='home_view'),
    path('delete-profile/', views.delete_profile, name='delete_profile'),

    path('profile/', views.profile_view, name='profile'), 
    path('test-student/', lambda r: render(
        r, "main/student_profile.html",
        {"u_form": UserForm(), "s_form": StudentProfileForm()}
    )),
    path('test-expert/', lambda r: render(
        r, "main/expert_profile.html",
        {"u_form": UserForm(), "e_form": ExpertProfileForm()}
    )),
] 