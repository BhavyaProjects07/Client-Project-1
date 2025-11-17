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


from django.contrib.auth.decorators import user_passes_test, login_required
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from store.models import (
    CustomUser, Order, WomenProduct, ElectronicProduct, ToyProduct
)


# ✅ Admin Check



from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import redirect
from django.conf import settings

from django.shortcuts import redirect
from django.contrib import messages

def secure_admin(view_func):
    def wrapper(request, *args, **kwargs):

        # 1️⃣ Check login first
        if not request.user.is_authenticated:
            return redirect(f"/request-otp/?next={request.path}")

        # 2️⃣ Check staff/admin
        if not request.user.is_staff:
            messages.error(request, "You are not allowed to access admin panel.")
            return redirect("/")

        # 3️⃣ Tab verification using JS flag
        # If NOT verified in Django session → redirect to verification page
        if not request.session.get("admin_verified"):
            return redirect(f"/admin-verify/?next={request.path}")

        return view_func(request, *args, **kwargs)

    return wrapper


def is_admin(user):
    return user.is_authenticated and user.is_staff


# ✅ Admin Dashboard Overview
from django.core.paginator import Paginator

@secure_admin
def admin_dashboard_view(request):
    search_email = request.GET.get('q', '').strip()
    page_number = request.GET.get('page', 1)

    # Base queryset
    orders_list = Order.objects.all().order_by('-created_at')

    # If searching
    if search_email:
        orders_list = orders_list.filter(user__email__icontains=search_email)
        if not orders_list.exists():
            messages.warning(request, f"No orders found for email: {search_email}")

    # Pagination — 10 orders per page
    paginator = Paginator(orders_list, 10)
    orders = paginator.get_page(page_number)

    # Summary stats
    total_orders = Order.objects.count()
    pending_orders = Order.objects.filter(order_status='Pending').count()
    shipped_orders = Order.objects.filter(order_status='Shipped').count()
    delivered_orders = Order.objects.filter(order_status='Delivered').count()
    total_users = CustomUser.objects.count()

    return render(request, 'dashboard.html', {
        'orders': orders,
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'shipped_orders': shipped_orders,
        'delivered_orders': delivered_orders,
        'total_users': total_users,
        'search_email': search_email,
    })



from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, get_object_or_404
from datetime import timedelta

@secure_admin
def admin_order_detail(request, order_id):
    from store.models import Order, OrderItem, WomenProduct, ToyProduct, ElectronicProduct

    order = get_object_or_404(Order, id=order_id)
    order_items = order.items.all()

    # Compute total per item + ensure product names are accessible
    for item in order_items:
        product = None
        try:
            if item.product_type == 'women':
                product = WomenProduct.objects.get(id=item.product_id)
            elif item.product_type == 'toy':
                product = ToyProduct.objects.get(id=item.product_id)
            elif item.product_type == 'electronic':
                product = ElectronicProduct.objects.get(id=item.product_id)
        except:
            product = None

        item.product_obj = product
        item.total_price = item.quantity * item.price

    expected_delivery = order.created_at + timedelta(days=2)

    return render(request, 'order_detail.html', {
        'order': order,
        'order_items': order_items,
        'expected_delivery': expected_delivery
    })

# ✅ Update Order Status
@secure_admin
def update_order_status(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    new_status = request.POST.get('status')
    paid_status = request.POST.get('paid')

    if new_status:
        order.order_status = new_status
    if paid_status is not None:
        order.paid = (paid_status == 'True')
    order.save()

    # Send email notification on certain status changes
    status_messages = {
        "Shipped": f"Your order #{order.id} has been shipped. 🚚",
        "Delivered": f"Your order #{order.id} has been delivered successfully! 🎉",
    }

    if new_status in status_messages:
        # TEXT VERSION
        text_message = (
            f"Hello {order.full_name},\n\n"
            f"{status_messages[new_status]}\n\n"
            f"Thank you for shopping with Sona Enterprises!"
        )

        # BEAUTIFUL HTML TEMPLATE
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
                    Thank you for shopping with <strong>Sona Enterprises</strong> ❤️<br>
                    We hope to serve you again soon!
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

    messages.success(request, f"Order #{order.id} updated to {new_status}.")
    return redirect('admin_dashboard')



# Update Payment Status (separate action)
@secure_admin
def update_payment_status(request, order_id):
    """
    Update payment status (Paid / Not Paid) from the dashboard.
    """
    order = get_object_or_404(Order, id=order_id)

    if request.method == 'POST':
        paid_value = request.POST.get('paid')

        if paid_value == 'True':
            order.paid = True
        elif paid_value == 'False':
            order.paid = False

        order.save()

        # ------------------------------------------------------
        # OPTIONAL EMAIL NOTIFICATION WHEN PAYMENT IS MARKED PAID
        # ------------------------------------------------------
        if paid_value == 'True':  # Only send when paid
            text_message = (
                f"Hello {order.full_name},\n\n"
                f"We have received your payment for Order #{order.id}.\n"
                f"Your order will now continue processing.\n\n"
                f"Thank you for shopping with Sona Enterprises!"
            )

            html_message = f"""
            <div style="font-family:'Segoe UI',sans-serif;background:#f4f4f4;padding:30px;">
                <div style="max-width:600px;margin:auto;background:white;
                            border-radius:12px;padding:25px;">
                    
                    <h2 style="color:#333;">💰 Payment Received</h2>

                    <p style="font-size:15px;color:#555;">
                        Hello <strong>{order.full_name}</strong>,
                        <br><br>
                        We have successfully received your payment for:
                    </p>

                    <div style="margin-top:15px;padding:12px;background:#fafafa;
                                border-radius:8px;border:1px solid #eee;">
                        <p style="margin:0;font-size:14px;">
                            <strong>Order ID:</strong> #{order.id}<br>
                            <strong>Payment Status:</strong> Paid<br>
                            <strong>Delivery Status:</strong> {order.order_status}
                        </p>
                    </div>

                    <p style="font-size:14px;color:#777;margin-top:20px;">
                        Thank you for trusting <strong>Sona Enterprises</strong> ❤️<br>
                        Your items will be shipped soon!
                    </p>

                </div>
            </div>
            """

            from store.email_service import send_brevo_email
            send_brevo_email(
                to=order.user.email,
                subject=f"Payment Received for Order #{order.id}",
                html_content=html_message,
                text_content=text_message
            )

        messages.success(request, f"✅ Payment status for Order #{order.id} updated successfully!")

    return redirect('admin_order_detail', order_id=order.id)


from django.conf import settings

def admin_verify(request):
    next_url = request.GET.get("next", "/")

    if request.method == "POST":
        code = request.POST.get("code")

        if code == settings.ADMIN_VERIFY_CODE:

            # Django session flag
            request.session["admin_verified"] = True

            # Add a JS flag for this tab
            response = redirect(next_url)
            response.set_cookie("admin_tab_verified", "yes")

            return response

        else:
            messages.error(request, "Invalid admin security code.")
            return redirect(f"/admin-verify/?next={next_url}")

    return render(request, "admin_verify.html")


def clear_admin_verify(request):
    request.session["admin_verified"] = False
    return JsonResponse({"status": "cleared"})
