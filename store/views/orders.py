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


from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from store.models import Order, WomenProduct, ElectronicProduct, ToyProduct

@login_required
def my_orders_view(request):
    orders = Order.objects.filter(user=request.user).prefetch_related('items')

    for order in orders:
        valid_items = []
        for item in order.items.all():
            product = None

            if item.product_type == 'women':
                product = WomenProduct.objects.filter(id=item.product_id).first()
            elif item.product_type == 'electronic':
                product = ElectronicProduct.objects.filter(id=item.product_id).first()
            elif item.product_type == 'toy':
                product = ToyProduct.objects.filter(id=item.product_id).first()

            # Attach the product dynamically only if it exists
            if product:
                item.product = product
                valid_items.append(item)

        order.items_valid = valid_items  # ✅ safe list for template

    return render(request, 'my_orders.html', {'orders': orders})



# ======================================================
# CUSTOMER SIDE — TRACK ORDER VIEW
# ======================================================

@login_required
def track_order_view(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    tracking_steps = [
        {"label": "Order Placed", "completed": True},
        {"label": "Shipped", "completed": order.order_status in ['Shipped', 'Delivered']},
        {"label": "Out for Delivery", "completed": order.order_status in ['Out for Delivery', 'Delivered']},
        {"label": "Delivered", "completed": order.order_status == 'Delivered'},
    ]

    return render(request, 'track_order.html', {
        'order': order,
        'steps': tracking_steps
    })


@login_required
def cancel_order(request, order_id):
    from store.models import Order

    order = get_object_or_404(Order, id=order_id, user=request.user)

    # Only allow cancel from Pending pickup
    if order.order_status != "Pending pickup":
        messages.error(request, "Order cannot be cancelled at this stage.")
        return redirect("track_order", order_id=order_id)

    # Update order status
    order.order_status = "Cancelled"
    order.save()

    # ----- SEND EMAIL NOTIFICATION -----
    try:
        from store.email_service import send_brevo_email

        subject = f"Order #{order.id} Cancelled"
        text_msg = f"Your order #{order.id} has been cancelled successfully."

        html_msg = f"""
        <div style="font-family:'Segoe UI',sans-serif;padding:20px;background:#f8f8f8;">
            <div style="max-width:600px;margin:auto;background:white;padding:25px;border-radius:10px;">
                <h2 style="color:#d9534f;">Order Cancelled</h2>
                <p>Hello {order.full_name},</p>
                <p>Your order <strong>#{order.id}</strong> has been cancelled.</p>
                <p>If you didn’t perform this action, please contact support immediately.</p>
                <p style="margin-top:20px;color:#888;font-size:13px;">
                    Sona Enterprises — Secure & Trusted Shopping
                </p>
            </div>
        </div>
        """

        send_brevo_email(
            to=order.user.email,
            subject=subject,
            html_content=html_msg,
            text_content=text_msg
        )
    except:
        pass

    messages.success(request, "Order cancelled successfully.")
    return redirect("my_orders")
