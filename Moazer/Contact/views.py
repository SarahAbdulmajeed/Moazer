from django.shortcuts import render, redirect
from .models import ContactMessage
from django.contrib.auth.decorators import login_required
from django.contrib import messages

def contact_view(request):
    if request.method == "POST":
        name = request.POST.get("name")
        email = request.POST.get("email")
        message = request.POST.get("message")

        ContactMessage.objects.create(
            name=name,
            email=email,
            message=message
        )
        messages.success(request, "تم إرسال رسالتك بنجاح!")
        return redirect("contact:contact") 

    user = request.user if request.user.is_authenticated else None

    context = {
        "user": user
    }
    return render(request, "contact/contact.html", context)
