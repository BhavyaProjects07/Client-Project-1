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



#✅ Delivery Personnel Secure Access Decorator
def secure_delivery(view_func):
    def wrapper(request, *args, **kwargs):

        # 1️⃣ User must be logged in
        if not request.user.is_authenticated:
            return redirect(f"/request-otp/?next={request.path}")

        # 2️⃣ User must be delivery boy OR admin
        if not request.user.is_delivery_boy and not request.user.is_staff:
            messages.error(request, "You are not authorized for the delivery panel.")
            return redirect("/")

        # 3️⃣ Require delivery verification
        if not request.session.get("delivery_verified"):
            return redirect(f"/delivery-verify/?next={request.path}")

        return view_func(request, *args, **kwargs)

    return wrapper

def delivery_verify(request):
    next_url = request.GET.get("next", "/delivery-dashboard/")

    if request.method == "POST":
        code = request.POST.get("code")

        if code == settings.DELIVERY_VERIFY_CODE:
            request.session["delivery_verified"] = True
            return redirect(next_url)

        messages.error(request, "Invalid delivery verification code.")
        return redirect(f"/delivery-verify/?next={next_url}")

    return render(request, "delievery_verify.html")



@secure_delivery
def delivery_dashboard(request):
    from store.models import Order, CustomUser

    # Count delivery boys
    delivery_count = CustomUser.objects.filter(is_delivery_boy=True).count()

    # Case 1: Only one delivery boy → show ALL orders
    if delivery_count == 1:
        orders = Order.objects.all().order_by('-created_at')
    else:
        # Case 2: Multiple → show only assigned orders
        orders = Order.objects.filter(assigned_to=request.user).order_by('-created_at')

    # Search filters
    name_q = request.GET.get("name")
    date_q = request.GET.get("date")

    if name_q:
        orders = orders.filter(full_name__icontains=name_q)

    if date_q:
        orders = orders.filter(created_at__date=date_q)

    return render(request, "delievery_dashboard.html", {
        "orders": orders,
        "name_q": name_q,
        "date_q": date_q,
    })



@secure_delivery
def delivery_order_detail(request, order_id):
    from store.models import Order, CustomUser

    delivery_count = CustomUser.objects.filter(is_delivery_boy=True).count()

    if delivery_count == 1:
        order = get_object_or_404(Order, id=order_id)
    else:
        order = get_object_or_404(Order, id=order_id, assigned_to=request.user)

    order_items = order.items.all()

    return render(request, "delievery_order_detail.html", {
        "order": order,
        "order_items": order_items,
    })


@secure_delivery
def update_order_status(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    new_status = request.POST.get("order_status")

    if not new_status:
        return redirect("delivery_dashboard")

    order.order_status = new_status
    order.save()

    # Messages sent to customer based on new status
    status_messages = {
        "Pending pickup": f"Your order #{order.id} is being prepared for pickup. 📦",
        "Out for delivery": f"Your order #{order.id} is out for delivery! 🚚 It will arrive soon.",
        "Delivered": f"Your order #{order.id} has been delivered successfully! 🎉",
        "Return initiated": f"Return request for your order #{order.id} has been initiated. 🔄",
    }

    # Only send messages for defined statuses
    if new_status in status_messages:

        # 📨 TEXT VERSION
        text_message = (
            f"Hello {order.full_name},\n\n"
            f"{status_messages[new_status]}\n\n"
            f"Thank you for choosing Sona Enterprises!"
        )

        # ✨ HTML VERSION (same style as admin)
        html_message = f"""
        <div style="font-family:'Segoe UI', sans-serif; background:#f2f2f2; padding:30px;">
            <div style="max-width:600px; margin:auto; background:white; border-radius:12px; padding:25px;">
                
                <h2 style="color:#333; margin-bottom:10px;">
                    Order Update — #{order.id}
                </h2>

                <p style="font-size:16px; color:#555;">
                    Hello <strong>{order.full_name}</strong>,
                </p>

                <p style="font-size:15px; color:#444;">
                    {status_messages[new_status]}
                </p>

                <div style="margin-top:20px; padding:15px; background:#fafafa; border-radius:8px;">
                    <p style="margin:0; font-size:14px;">
                        <strong>Order ID:</strong> #{order.id}<br>
                        <strong>Status:</strong> {new_status}<br>
                        <strong>Payment:</strong> {"Paid" if order.paid else "Cash on Delivery"}
                    </p>
                </div>

                <p style="font-size:14px; color:#777; margin-top:25px;">
                    Thank you for choosing <strong>Sona Enterprises</strong> ❤️<br>
                    We're always happy to serve you!
                </p>
            </div>
        </div>
        """

        # ---- SEND USING BREVO ----
        from store.email_service import send_brevo_email

        send_brevo_email(
            to=order.user.email,  
            subject=f"Order #{order.id} - {new_status}",
            html_content=html_message,
            text_content=text_message
        )

    messages.success(request, f"Order updated to {new_status}")
    return redirect("delivery_dashboard")


@secure_delivery
def update_payment_status(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    payment_status = request.POST.get("payment_status")

    if payment_status is None:
        return redirect("delivery_dashboard")

    paid_value = (payment_status == "Paid")
    order.paid = paid_value
    order.save()

    # Send email only when payment completed
    if paid_value:
        text_message = (
            f"Hello {order.full_name},\n\n"
            f"Your payment for Order #{order.id} has been successfully received. ✔️\n\n"
            f"Thank you for choosing Sona Enterprises!"
        )

        html_message = f"""
        <div style="font-family:'Segoe UI', sans-serif; background:#f2f2f2; padding:30px;">
            <div style="max-width:600px; margin:auto; background:white; border-radius:12px; padding:25px;">
                
                <h2 style="color:#333; margin-bottom:10px;">
                    Payment Confirmation — Order #{order.id}
                </h2>

                <p style="font-size:16px; color:#555;">
                    Hello <strong>{order.full_name}</strong>,
                </p>

                <p style="font-size:15px; color:#444;">
                    Your payment for the order has been successfully confirmed! 🎉
                </p>

                <div style="margin-top:20px; padding:15px; background:#fafafa; border-radius:8px;">
                    <p style="margin:0; font-size:14px;">
                        <strong>Order ID:</strong> #{order.id}<br>
                        <strong>Status:</strong> {order.order_status}<br>
                        <strong>Payment:</strong> Paid
                    </p>
                </div>

                <p style="font-size:14px; color:#777; margin-top:25px;">
                    Thank you for trusting <strong>Sona Enterprises</strong> ❤️
                </p>
            </div>
        </div>
        """

        from store.email_service import send_brevo_email

        send_brevo_email(
            to=order.user.email,
            subject=f"Payment Confirmed — Order #{order.id}",
            html_content=html_message,
            text_content=text_message
        )

    messages.success(request, "Payment status updated")
    return redirect("delivery_dashboard")


@secure_delivery
def delivery_order_history(request):
    orders = Order.objects.filter(
        assigned_to=request.user,
        order_status="Delivered"
    ).order_by("-created_at")

    total_revenue = sum(order.total_price for order in orders if order.paid)

    return render(request, "delievery_history_partial.html", {
        "orders": orders,
        "total_revenue": total_revenue
    })

from store.models import DeliveryProfile
@secure_delivery
def delivery_profile(request):
    # Auto-create profile if missing
    profile, created = DeliveryProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        first = request.POST.get("first_name")
        last = request.POST.get("last_name")
        phone = request.POST.get("phone")

        # Update CustomUser fields
        request.user.first_name = first
        request.user.last_name = last
        request.user.save()

        # Update DeliveryProfile fields
        profile.phone_number = phone
        profile.save()

        messages.success(request, "Profile updated successfully!")
    
    return render(request, "delievery_profile.html", {
        "profile": profile
    })
