from django.shortcuts import render , redirect
from django.http import HttpRequest, HttpResponse

def home_view(request: HttpRequest):
    return render(request, "main/index.html")

def about_us_view(request: HttpRequest):
    return render(request, "main/about_us.html")

