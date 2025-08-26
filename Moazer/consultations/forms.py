from django import forms
from django.contrib.auth import get_user_model
from .models import Consultation, ChatMessage, Attachment, ConsultationRating, ConsultationTypeChoices

User = get_user_model()

class ConsultationCreateForm(forms.ModelForm):
    expert = forms.ModelChoiceField(queryset=User.objects.all(), required=False, label="الخبير (اختياري)")
    class Meta:
        model = Consultation
        fields = ["type", "title", "description", "expert"]
        labels = {"type": "نوع الاستشارة", "title": "عنوان الاستشارة", "description": "التفاصيل"}
        widgets = {
            "type": forms.Select(choices=ConsultationTypeChoices.choices, attrs={"class": "form-select"}),
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }

class MessageForm(forms.ModelForm):
    class Meta:
        model = ChatMessage
        fields = ["content"]
        labels = {"content": "رسالتك"}
        widgets = {"content": forms.Textarea(attrs={"class": "form-control", "rows": 2})}

class AttachmentForm(forms.ModelForm):
    class Meta:
        model = Attachment
        fields = ["file"]
        labels = {"file": "ملف"}
        widgets = {"file": forms.ClearableFileInput(attrs={"class": "form-control"})}

class CloseRateForm(forms.ModelForm):
    class Meta:
        model = ConsultationRating
        fields = ["stars", "comment"]
        labels = {"stars": "التقييم (1-5)", "comment": "تعليقك"}
        widgets = {
            "stars": forms.NumberInput(attrs={"class": "form-control", "min": 1, "max": 5}),
            "comment": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }
