from django.shortcuts import render, redirect,get_object_or_404
from .models import ContactMessage
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.mail import send_mail
from django.conf import settings


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

@staff_member_required
def contact_messages_view(request):
    messages_list = ContactMessage.objects.all().order_by('-created_at')
    context = {
        "messages_list": messages_list
    }
    return render(request, "contact/admin_messages.html", context)

def reply_message_view(request, message_id):
    msg = get_object_or_404(ContactMessage, id=message_id)
    
    if request.method == "POST":
        reply_text = request.POST.get("reply_text", "")
        if reply_text.strip() == "":
            messages.error(request, "الرجاء كتابة نص الرد قبل الإرسال.")
            return redirect("contact:admin_messages")
        
        subject = "رد على رسالتك"
        recipient = [msg.email]

        send_mail(
            subject,
            reply_text,  
            settings.DEFAULT_FROM_EMAIL,
            recipient,
            fail_silently=False,
        )

        messages.success(request, f"تم إرسال الرد إلى {msg.email}")
        return redirect("contact:admin_messages")
