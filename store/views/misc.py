from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import login, get_user_model, logout
from django.db.models import Avg, Count
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required, user_passes_test
import random, json

# Import all models
from store.models import (
    CustomUser,BusinessNameAndLogo
)
from store.forms import ReviewForm

User = get_user_model()



def contact(request):
    business = BusinessNameAndLogo.objects.first()
    if request.method == "POST":
        name = request.POST.get("name")
        email = request.POST.get("email")
        subject = request.POST.get("subject")
        message = request.POST.get("message")

        # Send contact message to admin email
        from store.email_service import send_brevo_email

        admin_email = getattr(settings, 'ADMIN_EMAIL', None)
        if admin_email:
            subject = f"New Contact Message from {name}"
            html_content = f"""
                <div style="font-family:Arial;padding:20px;">
                    <h2>Contact Message</h2>
                    <p><strong>Name:</strong> {name}</p>
                    <p><strong>Email:</strong> {email}</p>
                    <p><strong>Message:</strong><br>{message}</p>
                </div>
            """
            text_content = f"Name: {name}\nEmail: {email}\nMessage:\n{message}\nSubject: {subject}"

            send_brevo_email(to=admin_email, subject=subject, html_content=html_content, text_content=text_content)

        messages.success(request, "Your message has been sent. We'll get back to you soon!")
        return redirect("contact")

    return render(request, "contact.html", {
        "business": business
    })