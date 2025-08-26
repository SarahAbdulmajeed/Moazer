from . import views  
from django.urls import path 

app_name = "accounts"

urlpatterns = [ 
    path('login/', views.login_view, name='login_view'),
    path('registration/', views.registration_view, name='registration_view'),
    path('experts/', views.experts_view, name='experts_view'),
    path('experts/', views.experts_view, name='experts_view'),
    path('experts/approve/<int:expert_id>', views.approve_expert, name='approve_expert'),
    path('experts/deactivate/<int:expert_id>', views.deactivate_expert, name='deactivate_expert'),
    path('expert/<int:expert_id>', views.expert_detail_view, name='expert_detail_view'),
    path('logout/', views.logout_view, name='logout_view'),
] 