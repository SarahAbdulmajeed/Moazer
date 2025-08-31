from django.shortcuts import render , redirect
from django.http import HttpRequest, HttpResponse
from django.contrib.auth.models import Group



def home_view(request: HttpRequest):
    for name in ["Students", "Experts"]:
     Group.objects.get_or_create(name=name)

    # Students Counts 
    students_count = Group.objects.get(name="Students").user_set.count()

    # Experts Counts 
    experts_count = Group.objects.get(name="Experts").user_set.count()

    return render(request, "main/index.html",{"students_count": students_count, "experts_count": experts_count})

def about_us_view(request: HttpRequest):
    return render(request, "main/about_us.html")

