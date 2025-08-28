from django.shortcuts import render, redirect,get_object_or_404
from .models import ContactMessage
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.mail import send_mail
from django.conf import settings






def contact_view(request):
    if request.method == "POST":
        if request.user.is_authenticated:
            # للمسجل
            name = request.user.get_full_name() or request.user.username
            email = request.user.email
        else:
            # للزائر
            name = request.POST.get("name", "").strip()
            email = request.POST.get("email", "").strip()

        message_text = request.POST.get("message", "").strip()

        if not message_text:
            messages.error(request, "الرجاء كتابة الرسالة قبل الإرسال.")
            return redirect(request.path)

        if not request.user.is_authenticated and (not name or not email):
            messages.error(request, "الرجاء كتابة الاسم والبريد الإلكتروني.")
            return redirect(request.path)

        ContactMessage.objects.create(
            name=name,
            email=email,
            message=message_text
        )

        messages.success(request, "تم إرسال رسالتك بنجاح!")
        return redirect(request.path)

    return render(request, "contact/contact.html", {"user": request.user if request.user.is_authenticated else None})


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



