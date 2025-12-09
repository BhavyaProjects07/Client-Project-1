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
    from datetime import timedelta

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

    subtotal = sum(item.total_price() for item in order.items.all())


    # Expected delivery
    try:
        if hasattr(order, "get_delivery_days"):
            days = order.get_delivery_days()   # CALL THE FUNCTION
        else:
            days = 2
        expected_delivery = order.created_at + timedelta(days=days)
    except Exception as e:
        print("ERROR:", e)
        expected_delivery = None


    # -----------------------
    # SEND STEPS TO TEMPLATE
    # -----------------------
    steps = [
    {"label": "Order Placed", "completed": True},

    # Step 2: Packed (completed AFTER order leaves pending)
    {"label": "Packed", "completed": order.order_status in ["Out for delivery", "Delivered"]},

    # Step 3: Out for delivery
    {"label": "Out for delivery", "completed": order.order_status in ["Out for delivery", "Delivered"]},

    # Step 4: Delivered
    {"label": "Delivered", "completed": order.order_status == "Delivered"},
]


    return render(request, "track_order.html", {
        "order": order,
        "subtotal": subtotal,
        "expected_delivery": expected_delivery,
        "steps": steps,        # <<<<<<==== FIX
    })


# ======================================================
# CANCEL ORDER
# ======================================================


from django.conf import settings
import razorpay
from decouple import config
from store.email_service import send_brevo_email  # 👈 already used in your project

razorpay_client = razorpay.Client(
    auth=(
        config("RAZORPAY_KEY_ID_TEST"),
        config("RAZORPAY_KEY_SECRET_TEST")
    )
)


@login_required
def cancel_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    # ❌ Cannot cancel if not pending pickup
    if order.order_status != "Pending pickup":
        messages.error(request, "This order cannot be cancelled now.")
        return redirect("track_order", order_id=order.id)

    # 🔥 Online Payment Refund
    if order.paid and order.payment_method != "COD":
        try:
            refund = razorpay_client.payment.refund(order.payment_id, {
                "amount": int(order.total_amount() * 100),  # paise
                "speed": "normal"
            })

            order.refund_id = refund.get("id")
            order.refunded = True

            # 📩 Cancellation & Refund Email (Customer)
            customer_email = order.user.email
            if customer_email:
                html_msg = f"""
                <div style='font-family:Arial;padding:20px;background:#fff7e6;'>
                    <h2 style='color:#d9534f;'>Order Cancelled — #{order.id}</h2>
                    <p>Hello <strong>{order.full_name}</strong>,</p>
                    <p>Your prepaid order has been successfully cancelled.</p>
                    <p>Refund of <strong>₹{order.total_amount()}</strong> has been initiated.</p>
                    <p>It will be credited back to your original payment method within
                    <strong>2–7 working days</strong> by Razorpay.</p>
                    <p>Thank you for shopping with us!</p>
                </div>
                """

                text_msg = (
                    f"Order #{order.id} cancelled.\n"
                    f"Refund ₹{order.total_amount()} initiated and will be credited within 2–7 working days."
                )

                send_brevo_email(
                    to=customer_email,
                    subject=f"Order Cancelled — #{order.id}",
                    html_content=html_msg,
                    text_content=text_msg,
                )

        except Exception as e:
            print("Refund Error:", e)
            messages.error(request, "Refund failed! Contact support.")
            return redirect("track_order", order_id=order.id)

    # 💾 Now update order status
    order.order_status = "Cancelled"
    order.save()

    # 📩 NEW: Cancellation Email to Admin (for ALL cancellations: COD + Online)
    admin_email = getattr(settings, "ADMIN_EMAIL", None)
    if admin_email:
        if order.paid and order.payment_method != "COD":
            refund_line_html = f"<p>Refund of <strong>₹{order.total_amount()}</strong> has been initiated via Razorpay.</p>"
            refund_line_text = f"Refund ₹{order.total_amount()} has been initiated via Razorpay."
        else:
            refund_line_html = "<p>This was a Cash On Delivery order. No refund is required.</p>"
            refund_line_text = "COD order cancelled. No refund required."

        admin_html = f"""
        <div style='font-family:Arial;padding:20px;background:#f5f5f5;'>
            <h2>Order Cancelled — #{order.id}</h2>
            <p><strong>Customer:</strong> {order.full_name} ({order.user.email})</p>
            <p><strong>Phone:</strong> {order.phone_number}</p>
            <p><strong>Address:</strong> {order.address}, {order.city} - {order.postal_code}</p>
            <p><strong>Payment Method:</strong> {order.payment_method}</p>
            <p><strong>Paid:</strong> {"Yes" if order.paid else "No"}</p>
            {refund_line_html}
        </div>
        """

        admin_text = (
            f"Order #{order.id} has been cancelled.\n"
            f"Customer: {order.full_name} ({order.user.email})\n"
            f"Payment Method: {order.payment_method}\n"
            f"Paid: {'Yes' if order.paid else 'No'}\n"
            f"{refund_line_text}"
        )

        try:
            send_brevo_email(
                to=admin_email,
                subject=f"Order Cancelled — #{order.id}",
                html_content=admin_html,
                text_content=admin_text,
            )
        except Exception as e:
            print("Admin cancel email error:", e)

    messages.success(request, "Order cancelled successfully.")
    return redirect("track_order", order_id=order.id)
