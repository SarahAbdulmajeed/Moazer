from django.urls import path
from . import views

app_name = "consultations"

urlpatterns = [
    path("", views.list_view, name="list_view"),
    path("experts/", views.experts_stub_view, name="experts_stub"),  # ← صفحة الخبراء المؤقتة
    path("create/<int:expert_id>/", views.create_view, name="create_view"),
    path("<int:consultation_id>/", views.detail_view, name="detail_view"),
    path("<int:consultation_id>/messages/", views.messages_partial_view, name="messages_partial"),
    path("<int:consultation_id>/rate/", views.rate_view, name="rate_view"),
]