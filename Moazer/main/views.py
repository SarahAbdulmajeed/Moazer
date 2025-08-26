from django.shortcuts import render , redirect
from django.http import HttpRequest, HttpResponse
from django.contrib.auth.decorators import login_required

def home_view(request: HttpRequest):
    return render(request, "main/index.html")

def about_us_view(request: HttpRequest):
    return render(request, "main/about_us.html")