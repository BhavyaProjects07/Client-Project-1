from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.conf import settings
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from store.models import (
    CustomUser,
    Product,
    ProductVariant,
    Order,
    OrderItem,
    DeliveryProfile,
)

# ======================================================
# DELIVERY PANEL SECURITY
# ======================================================
def secure_delivery(view_func):
    """
    Delivery panel security:
    - Must be logged in
    - Must be delivery boy/admin
    - Must enter verification code ONCE PER TAB
    """
    def wrapper(request, *args, **kwargs):

        # CASE A — User not logged in
        if not request.user.is_authenticated:
            messages.error(request, "Please login first, then click the dashboard link again.")
            return redirect("/")

        # CASE B — Not delivery boy and not admin
        if not request.user.is_delivery_boy and not request.user.is_staff:
            messages.error(request, "You are not authorized to access the delivery panel.")
            return redirect("/")

        # CASE C — Tab verification cookie missing → must verify
        if request.COOKIES.get("delivery_tab_verified") != "yes":
            return redirect(f"/delivery-verify/?next={request.path}")

        # CASE D — Make sure session flag exists (extra safety)
        if not request.session.get("delivery_verified", False):
            return redirect(f"/delivery-verify/?next={request.path}")

        return view_func(request, *args, **kwargs)

    return wrapper



# ======================================================
# DELIVERY VERIFY CODE
# ======================================================
def delivery_verify(request):
    next_url = request.GET.get("next", "/delivery-dashboard/")

    if request.method == "POST":
        code = request.POST.get("code")

        if code == settings.DELIVERY_VERIFY_CODE:

            # Session flag (expires when browser closes)
            request.session["delivery_verified"] = True
            request.session.set_expiry(0)

            # Cookie to detect tab closure
            response = redirect(next_url)
            response.set_cookie("delivery_tab_verified", "yes")

            return response

        messages.error(request, "Invalid delivery verification code.")
        return redirect(f"/delivery-verify/?next={next_url}")

    return render(request, "delievery_verify.html")

# ======================================================
# DELIVERY DASHBOARD
# ======================================================

@secure_delivery
def delivery_dashboard(request):
    delivery_count = CustomUser.objects.filter(is_delivery_boy=True).count()

    # Case 1: Only one delivery boy → show ALL orders
    if delivery_count == 1:
        orders = Order.objects.all().order_by("-created_at")
    else:
        # Case 2: Multiple delivery boys → show assigned orders
        orders = Order.objects.filter(assigned_to=request.user).order_by("-created_at")

    # Filters
    name_q = request.GET.get("name") or ""
    date_q = request.GET.get("date") or None

    if name_q:
        orders = orders.filter(full_name__icontains=name_q)

    if date_q:
        orders = orders.filter(created_at__date=date_q)

    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(orders, 5)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    today = timezone.now().date()

    return render(request, "delievery_dashboard.html", {
        "page_obj": page_obj,
        "orders": page_obj,
        "name_q": name_q,
        "date_q": date_q,
        "today_deliveries": orders.filter(created_at__date=today).count(),
        "delivered_today": orders.filter(created_at__date=today, order_status="Delivered").count(),
        "pending_deliveries": orders.filter(order_status="Pending pickup").count(),
    })


# ======================================================
# ORDER DETAILS
# ======================================================

@secure_delivery
def delivery_order_detail(request, order_id):

    delivery_count = CustomUser.objects.filter(is_delivery_boy=True).count()

    if delivery_count == 1:
        order = get_object_or_404(Order, id=order_id)
    else:
        order = get_object_or_404(Order, id=order_id, assigned_to=request.user)

    raw_items = order.items.select_related("product", "variant")

    items_for_template = []

    for it in raw_items:
        product = it.product
        variant = it.variant

        # Get product image
        if variant and variant.images.exists():
            image_url = variant.images.first().image.url
        elif hasattr(product, "thumbnail") and product.thumbnail:
            image_url = product.thumbnail.url
        else:
            image_url = ""

        items_for_template.append({
            "product_obj": product,
            "product_image": image_url,
            "variant": variant,
            "quantity": it.quantity,
            "price": it.price,
            "total_price": it.price * it.quantity,
        })

    return render(request, "delievery_order_detail.html", {
        "order": order,
        "order_items": items_for_template,
    })



# ======================================================
# UPDATE ORDER STATUS
# ======================================================

# ======================================================
# UPDATE ORDER STATUS
# ======================================================

@secure_delivery
def update_order_status(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    new_status = request.POST.get("order_status")

    if not new_status:
        return redirect("delivery_dashboard")

    order.order_status = new_status
    order.save()

    # get business name from DB
    from store.models import BusinessNameAndLogo
    business = BusinessNameAndLogo.objects.first()
    business_name = business.name if business else "Our Store"

    # Messages for customer
    messages_map = {
        "Pending pickup": f"Your order #{order.id} is being prepared for pickup. 📦",
        "Out for delivery": f"Your order #{order.id} is on the way! 🚚",
        "Delivered": f"Your order #{order.id} has been delivered successfully! 🎉",
        "Cancelled": f"Your order #{order.id} has been cancelled.",
    }

    if new_status in messages_map:
        text_msg = (
            f"Hello {order.full_name},\n\n"
            f"{messages_map[new_status]}\n\n"
            f"Thank you for ordering from {business_name}!"
        )

        html_msg = f"""
        <div style="font-family:Segoe UI;background:#f2f2f2;padding:30px;">
            <div style="max-width:600px;margin:auto;background:#fff;border-radius:12px;padding:25px;">
                <h2>Order Update — #{order.id}</h2>
                <p>Hello <strong>{order.full_name}</strong>,</p>
                <p>{messages_map[new_status]}</p>
                <p><strong>Payment:</strong> {"Paid" if order.paid else "Cash on Delivery"}</p>
            </div>
        </div>
        """

        # Send email through Brevo
        from store.email_service import send_brevo_email
        send_brevo_email(
            to=order.user.email,
            subject=f"Order #{order.id} — {new_status}",
            html_content=html_msg,
            text_content=text_msg
        )

    messages.success(request, f"Order status updated to {new_status}")
    return redirect("delivery_dashboard")


# ======================================================
# UPDATE PAYMENT STATUS
# ======================================================

@secure_delivery
def update_payment_status(request, order_id):

    order = get_object_or_404(Order, id=order_id)
    pay_value = request.POST.get("payment_status")

    if pay_value is None:
        return redirect("delivery_dashboard")

    is_paid = (pay_value == "Paid")
    order.paid = is_paid
    order.save()

    if is_paid:
        text_msg = (
            f"Hello {order.full_name},\n\n"
            f"Your payment for Order #{order.id} has been received successfully! ✔️\n\n"
        )

        html_msg = f"""
        <div style="font-family:Segoe UI;background:#f2f2f2;padding:30px;">
            <div style="max-width:600px;margin:auto;background:#fff;border-radius:12px;padding:25px;">
                <h2>Payment Confirmed — Order #{order.id}</h2>
                <p>Hello <strong>{order.full_name}</strong>,</p>
                <p>Your payment has been successfully confirmed! 🎉</p>
            </div>
        </div>
        """

        from store.email_service import send_brevo_email
        send_brevo_email(
            to=order.user.email,
            subject=f"Payment Confirmed — Order #{order.id}",
            html_content=html_msg,
            text_content=text_msg
        )

    messages.success(request, "Payment status updated successfully.")
    return redirect("delivery_dashboard")


# ======================================================
# DELIVERY HISTORY
# ======================================================

@secure_delivery
def delivery_order_history(request):

    orders = Order.objects.filter(
        assigned_to=request.user,
        order_status="Delivered"
    ).order_by("-created_at")

    total_revenue = sum(
        order.total_amount() for order in orders if order.paid
    )

    return render(request, "delievery_history_partial.html", {
        "orders": orders,
        "total_revenue": total_revenue
    })


# ======================================================
# DELIVERY PROFILE
# ======================================================

@secure_delivery
def delivery_profile(request):
    profile, created = DeliveryProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        request.user.first_name = request.POST.get("first_name")
        request.user.last_name = request.POST.get("last_name")
        request.user.save()

        profile.phone = request.POST.get("phone")
        profile.save()

        messages.success(request, "Profile updated successfully!")

    return render(request, "delievery_profile.html", {
        "profile": profile
    })
