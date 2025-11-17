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
    CustomUser, WomenProduct, ElectronicProduct, ToyProduct,
    CartItem, WishlistItem, Order, OrderItem, Review
)
from store.forms import ReviewForm

User = get_user_model()
otp_storage = {}



# ======================================================
# AUTHENTICATION WITH OTP VIEWS
# ======================================================

from django.contrib.auth import authenticate
def request_otp_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")

        # Check if user exists by EMAIL (email is the real unique identifier)
        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            user = None

        # ------------------------------------------
        # 1️⃣ EXISTING USER → LOGIN DIRECTLY
        # ------------------------------------------
        if user:
            # Authenticate with email (because USERNAME_FIELD = email)
            auth_user = authenticate(request, username=email, password=password)

            if auth_user:
                login(request, auth_user)
                request.session.set_expiry(60 * 60 * 24 * 15)   # 15 days
                messages.success(request, f"Welcome back, {auth_user.username}!")
                return redirect("/")
            else:
                messages.error(request, "Incorrect password. Please try again.")
                return redirect("/")

        # ------------------------------------------
        # 2️⃣ NEW USER → OTP REQUIRED
        # ------------------------------------------
        otp = str(random.randint(100000, 999999))
        otp_storage[email] = {
            "otp": otp,
            "username": username,
            "password": password
        }

        # Send OTP via Brevo
        try:
            from store.email_service import send_brevo_email

            subject = "Account Verification OTP - Sona Enterprises"
            text_content = f"Hi {username}, your OTP is {otp}"
            html_content = f"""
                <p>Hi {username},</p>
                <p>Your OTP is <strong>{otp}</strong></p>
            """

            send_brevo_email(
                to=email,
                subject=subject,
                html_content=html_content,
                text_content=text_content
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).exception(f"Failed to send OTP: {e}")

        request.session["pending_email"] = email
        messages.success(request, f"OTP sent to {email}")
        return redirect("verify_otp")

    return redirect("/")



def verify_otp_view(request):
    # Read mode (default = login/signup)
    otp_mode = request.session.get("otp_mode", "login")

    if request.method == "POST":
        entered_otp = request.POST.get("otp")

        # -----------------------------------------------------
        # 🔹 FORGOT PASSWORD — RESET MODE OTP VERIFICATION
        # -----------------------------------------------------
        if otp_mode == "reset":
            email = request.session.get("reset_email")
            correct_otp = request.session.get("reset_otp")

            if not email or not correct_otp:
                messages.error(request, "OTP expired or invalid. Please try again.")
                return redirect("forgot_password")

            if str(entered_otp) == str(correct_otp):
                # Clear OTP from session
                request.session.pop("reset_otp", None)
                request.session["otp_mode"] = None

                # Redirect to new password page
                messages.success(request, "OTP verified! Please set your new password.")
                return redirect("new_password")

            else:
                messages.error(request, "Incorrect OTP. Please try again.")
                return redirect("verify_otp")

        # -----------------------------------------------------
        # 🔹 NORMAL LOGIN / SIGNUP OTP LOGIC
        # -----------------------------------------------------
        email = request.session.get("pending_email")
        data = otp_storage.get(email)

        if not data:
            messages.error(request, "OTP expired or invalid. Please request again.")
            return redirect("request_otp")

        if data["otp"] == entered_otp:
            username = data["username"]
            password = data["password"]

            user, created = CustomUser.objects.get_or_create(
                email=email,
                defaults={"username": username}
            )

            user.set_password(password)
            user.is_verified = True
            user.save()

            login(request, user)
            request.session.set_expiry(60 * 60 * 24 * 15)   # 15 days

            messages.success(
                request,
                f"Welcome back, {user.username}!"
                if not created else f"Account created successfully for {user.username}!"
            )

            otp_storage.pop(email, None)
            return redirect("/")
        else:
            messages.error(request, "Invalid OTP. Please try again.")
            return redirect("verify_otp")

    return render(request, "verify_otp.html")


def logout_view(request):
    logout(request)
    return redirect("/")


def forgot_password(request):
    if request.method == "POST":
        email = request.POST.get("email")

        # Check if email exists
        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            messages.error(request, "No account found with this email.")
            return redirect("forgot_password")

        # Generate OTP
        otp = random.randint(100000, 999999)

        request.session["reset_email"] = email
        request.session["reset_otp"] = str(otp)
        request.session["otp_mode"] = "reset"

        # Send OTP using Brevo
        from store.email_service import send_brevo_email

        subject = "Reset Password OTP - Sona Enterprises"
        html = f"""
            <div style="font-family:Arial;padding:20px;">
                <h2>Reset Password Request</h2>
                <p>Your OTP for resetting your password is:</p>
                <h1>{otp}</h1>
                <p>This OTP is valid for 10 minutes.</p>
            </div>
        """
        text = f"Your reset OTP is {otp}"

        send_brevo_email(to=email, subject=subject, html_content=html, text_content=text)

        messages.success(request, "OTP sent to your email.")
        return redirect("verify_otp")

    return render(request, "forgot_password.html")



def new_password(request):
    reset_email = request.session.get("reset_email")

    if not reset_email:
        messages.error(request, "Unauthorized access.")
        return redirect("forgot_password")

    user = CustomUser.objects.get(email=reset_email)

    if request.method == "POST":
        p1 = request.POST.get("new_password")
        p2 = request.POST.get("confirm_password")

        if p1 != p2:
            messages.error(request, "Passwords do not match.")
            return redirect("new_password")

        user.set_password(p1)
        user.save()

        # Clear session
        for key in ["reset_email", "reset_otp", "otp_mode"]:
            request.session.pop(key, None)

        login(request, user)
        request.session.set_expiry(60 * 60 * 24 * 15)   # 15 days  # now login AFTER reset success

        messages.success(request, "Password updated successfully!")
        return redirect("home")

    return render(request, "new_password.html")
