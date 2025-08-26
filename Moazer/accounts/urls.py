from . import views  
from django.urls import path 

app_name = "accounts"

urlpatterns = [ 
    path('login/', views.login_view, name='login_view'),
    path('registration/', views.registration_view, name='registration_view'),
    path('logout/', views.logout_view, name='logout_view'),
    path('experts/<int:user_id>/', views.expert_detail_view, name='expert_detail'),
] 