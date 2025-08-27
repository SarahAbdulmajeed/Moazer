from . import views  
from django.urls import path
from django.shortcuts import render


app_name = "main"

urlpatterns = [ 
		#path(URL Route*, View*)
    path('', views.home_view, name='home_view'),
    path('about/', views.about_us_view, name='about_us_view'), 

] 