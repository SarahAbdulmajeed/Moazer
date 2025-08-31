from django.urls import path
from . import views

app_name = "ai_interview"

urlpatterns = [
    path("", views.list_view, name="list"),
    path("start/", views.start_view, name="start"),
    path("<int:session_id>/q/<int:step>/", views.question_view, name="question"),
    path("<int:session_id>/result/", views.result_view, name="result"),
]