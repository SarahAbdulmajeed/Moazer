from django.urls import path
from . import views

app_name = "contact"
urlpatterns = [
    path('contact/', views.contact_view, name='contact'),
    path('admin-messages/', views.contact_messages_view, name='admin_messages'),
    path('admin-messages/reply/<int:message_id>/', views.reply_message_view, name='reply_message')

]