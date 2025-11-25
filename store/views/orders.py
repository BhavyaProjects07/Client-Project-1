# store/views/orders.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, F
from store.models import Order, OrderItem, Product, ProductVariant


# ======================================================
# MY ORDERS (Customer Side)
# ======================================================
@login_required
def my_orders_view(request):
    """
    Show all orders for the logged-in user.
    Optimized for dynamic product system.
    """
    orders = (
        Order.objects.filter(user=request.user)
        .select_related("assigned_to")
        .order_by("-created_at")
        .prefetch_related(
            "items",
            "items__product",
            "items__variant",
            "items__product__images",
        )
    )

    return render(request, "my_orders.html", {"orders": orders})


# ======================================================
# TRACK ORDER
# ======================================================
@login_required
def track_order_view(request, order_id):
    """
    Detailed order tracking page.
    Includes dynamic product + variant data.
    """
    order = get_object_or_404(
        Order.objects.prefetch_related(
            "items",
            "items__product",
            "items__variant",
            "items__product__images",
        ),
        id=order_id,
        user=request.user
    )

    # Calculate total price of order
    subtotal = sum(item.total_price for item in order.items.all())

    return render(request, "track_order.html", {
        "order": order,
        "subtotal": subtotal,
    })


# ======================================================
# CANCEL ORDER
# ======================================================
@login_required
def cancel_order(request, order_id):
    """
    User can cancel ONLY if the order is still 'Pending pickup'.
    """
    order = get_object_or_404(Order, id=order_id, user=request.user)

    if order.order_status != "Pending pickup":
        messages.error(request, "This order cannot be cancelled now.")
        return redirect("track_order", order_id=order.id)

    order.order_status = "Cancelled"
    order.save()

    messages.success(request, "Your order has been cancelled successfully.")
    return redirect("track_order", order_id=order.id)

