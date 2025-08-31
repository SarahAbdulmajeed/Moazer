from django.urls import path
from . import views

app_name = "career_path"

urlpatterns = [
    path("", views.landing_view, name="landing"),           
    path("start/school/", views.start_school_view, name="start_school"),
    path("start/grad/", views.start_grad_view, name="start_grad"),
    path("list/", views.list_view, name="list"),
    path("<int:session_id>/q/<int:step>/", views.question_view, name="question"),
    path("<int:session_id>/result/", views.result_view, name="result"),
]
