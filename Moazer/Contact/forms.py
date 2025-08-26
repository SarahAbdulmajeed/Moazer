from django import forms
from .models import ContactMessage

class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ["name", "email", "message"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "الاسم"}),
            "email": forms.EmailInput(attrs={"placeholder": "example@gmail.com"}),
            "message": forms.Textarea(attrs={"placeholder": "الرسالة", "rows": 5}),
        }