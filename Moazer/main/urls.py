from . import views  
from django.urls import path 

app_name = "main"

urlpatterns = [ 
		#path(URL Route*, View*)
    path('', views.home_view, name='home_view'),
    path('profile/', views.profile_view, name='profile'), 
] 