# store/views/admin_panel.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.conf import settings
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from store.email_service import send_brevo_email  # keep your existing email helper

# Dynamic models (new)
from store.models import (
    CustomUser,
    Product,
    ProductVariant,
    Category,
    Order,
    OrderItem,
    CartItem,
    WishlistItem,
    Review,
    DeliveryProfile,
    BusinessNameAndLogo,
)

User = get_user_model()


# -------------------------
# Admin guards
# -------------------------
def secure_admin(view_func):
    def wrapper(request, *args, **kwargs):
        # 1) must be logged in
        if not request.user.is_authenticated:
            return redirect(f"/request-otp/?next={request.path}")

        # 2) must be staff
        if not request.user.is_staff:
            messages.error(request, "You are not allowed to access admin panel.")
            return redirect("/")

        # 3) session verification guard (extra JS tab flag)
        if not request.session.get("admin_verified"):
            return redirect(f"/admin-verify/?next={request.path}")

        return view_func(request, *args, **kwargs)
    return wrapper


def is_admin(user):
    return user.is_authenticated and user.is_staff


# -------------------------
# Admin dashboard overview
# -------------------------
@secure_admin
def admin_dashboard_view(request):
    q = request.GET.get('q', '').strip()
    page = request.GET.get('page', 1)

    orders_qs = Order.objects.select_related('user', 'assigned_to').order_by('-created_at')

    if q:
        # search by email, username, order id
        if q.isdigit():
            orders_qs = orders_qs.filter(id=int(q))
        else:
            orders_qs = orders_qs.filter(
                (User.objects.filter(email__icontains=q).exists() and
                 (Order.objects.filter(user__email__icontains=q).values_list('id', flat=True))) or []
            )  # fallback to filtering by email below

            # simpler robust filter:
            orders_qs = Order.objects.filter(
                user__email__icontains=q
            ).order_by('-created_at')

        if not orders_qs.exists():
            messages.warning(request, f"No orders found for: {q}")

    paginator = Paginator(orders_qs, 10)
    orders_page = paginator.get_page(page)

    # Stats
    total_orders = Order.objects.count()
    total_users = CustomUser.objects.count()
    total_products = Product.objects.count()
    total_categories = Category.objects.count()

    # low stock products (example: stock <=5)
    low_stock = ProductVariant.objects.filter(stock__lte=5).select_related('product')[:10]

    # revenue (simple: sum of paid orders)
    revenue = 0
    paid_orders = Order.objects.filter(paid=True)
    for o in paid_orders:
        revenue += (o.total_amount() if hasattr(o, 'total_amount') else sum([it.price * it.quantity for it in o.items.all()]))

    context = {
        'orders': orders_page,
        'total_orders': total_orders,
        'total_users': total_users,
        'total_products': total_products,
        'total_categories': total_categories,
        'low_stock': low_stock,
        'revenue': revenue,
        'search_query': q,
    }
    return render(request, 'dashboard.html', context)


# -------------------------
# Admin order detail
# -------------------------
@secure_admin
def admin_order_detail(request, order_id):
    order = get_object_or_404(Order.objects.select_related('user', 'assigned_to'), id=order_id)
    order_items = order.items.select_related('product', 'variant').all()

    # Attach product/variant safe attributes for template
    items_for_template = []
    for it in order_items:
        product = getattr(it, 'product', None)
        variant = getattr(it, 'variant', None)
        name = product.name if product else "Unknown product"
        variant_label = variant.variant_options if variant and variant.variant_options else None
        price_snapshot = it.price
        qty = it.quantity
        total_price = price_snapshot * qty
        items_for_template.append({
            'id': it.id,
            'name': name,
            'product': product,
            'variant': variant,
            'variant_label': variant_label,
            'price': price_snapshot,
            'quantity': qty,
            'total_price': total_price,
        })

    expected_delivery = order.created_at + timedelta(days=2)

    return render(request, 'order_detail.html', {
        'order': order,
        'order_items': items_for_template,
        'expected_delivery': expected_delivery
    })


# -------------------------
# Update order status
# -------------------------
@secure_admin
def admin_update_order_status(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    if request.method != "POST":
        messages.error(request, "Invalid request method.")
        return redirect('admin_order_detail', order_id=order.id)

    new_status = request.POST.get('status')
    paid_flag = request.POST.get('paid')

    # Basic validation - ensure provided status is in choices
    allowed_statuses = [choice[0] for choice in Order._meta.get_field('order_status').choices]
    if new_status and new_status in allowed_statuses:
        order.order_status = new_status

    if paid_flag is not None:
        order.paid = (paid_flag == 'True' or paid_flag == 'true' or paid_flag == '1')

    order.save()

    # send notifications for important transitions
    notifications = {
        "Out for delivery": f"Your order #{order.id} is out for delivery 🚚",
        "Delivered": f"Your order #{order.id} has been delivered. 🎉",
        "Cancelled": f"Your order #{order.id} has been cancelled.",
    }

    if new_status in notifications:
        text_message = f"Hello {order.full_name},\n\n{notifications[new_status]}\n\nThank you for shopping with us!"
        html_message = f"""
            <div style="font-family:Arial,sans-serif;padding:20px;background:#f7f7f7;">
              <div style="max-width:600px;margin:auto;background:white;padding:20px;border-radius:8px;">
                <h2>Order Update — #{order.id}</h2>
                <p>{notifications[new_status]}</p>
                <p><strong>Order ID:</strong> #{order.id}</p>
                <p><strong>Status:</strong> {new_status}</p>
                <p><strong>Payment:</strong> {"Paid" if order.paid else "Cash on Delivery"}</p>
              </div>
            </div>
        """
        try:
            send_brevo_email(
                to=order.user.email,
                subject=f"Order Update — #{order.id} — {new_status}",
                html_content=html_message,
                text_content=text_message
            )
        except Exception:
            # do not block admin action on email failure
            pass

    messages.success(request, f"Order #{order.id} updated.")
    return redirect('admin_order_detail', order_id=order.id)


# -------------------------
# Update payment status (separate endpoint)
# -------------------------
@secure_admin
def admin_update_payment_status(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    if request.method != "POST":
        messages.error(request, "Invalid request method.")
        return redirect('admin_order_detail', order_id=order.id)

    paid_value = request.POST.get('paid')
    if paid_value in ('True', 'true', '1'):
        order.paid = True
    elif paid_value in ('False', 'false', '0'):
        order.paid = False
    order.save()

    if order.paid:
        # optional email notification
        try:
            text_message = f"Hello {order.full_name},\n\nWe received payment for Order #{order.id}."
            html_message = f"<div><p>We received payment for Order #{order.id}.</p></div>"
            send_brevo_email(
                to=order.user.email,
                subject=f"Payment received — Order #{order.id}",
                html_content=html_message,
                text_content=text_message
            )
        except Exception:
            pass

    messages.success(request, f"Payment status updated for Order #{order.id}.")
    return redirect('admin_order_detail', order_id=order.id)


# -------------------------
# Admin verify + clear
# -------------------------
def admin_verify(request):
    next_url = request.GET.get("next", "/")

    if request.method == "POST":
        code = request.POST.get("code")
        if code and code == getattr(settings, "ADMIN_VERIFY_CODE", ""):
            request.session["admin_verified"] = True
            response = redirect(next_url)
            response.set_cookie("admin_tab_verified", "yes")
            return response
        messages.error(request, "Invalid admin security code.")
        return redirect(f"/admin-verify/?next={next_url}")

    return render(request, "admin_verify.html")


def clear_admin_verify(request):
    request.session["admin_verified"] = False
    return JsonResponse({"status": "cleared"})
