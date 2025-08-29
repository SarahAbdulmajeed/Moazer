from django.urls import path
from . import views

app_name = "subscriptions"

urlpatterns = [
    path("plans/", views.plans_view, name="plans"),
    path("subscribe/<int:plan_id>/", views.subscribe_view, name="subscribe"),
]