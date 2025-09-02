from django.urls import path
from . import views

app_name = "subscriptions"

urlpatterns = [
    path("plans/", views.plans_view, name="plans"),
    path("subscribe/<int:plan_id>/", views.subscribe_view, name="subscribe"),
    path("pay/<int:plan_id>/", views.create_invoice_and_redirect, name="pay"),
    path("callback/", views.callback_view, name="callback"),
]