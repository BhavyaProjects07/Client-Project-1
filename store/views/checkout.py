from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.http import JsonResponse
from django.db.models import Sum
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from store.models import CustomUser
from store.models import (
    Product,
    ProductVariant,
    CartItem,
    Order,
    OrderItem,
    BusinessNameAndLogo
)

import razorpay
import os
from dotenv import load_dotenv

from decouple import config

# Razorpay client
RAZORPAY_KEY_ID = config("RAZORPAY_KEY_ID_LIVE")
RAZORPAY_KEY_SECRET = config("RAZORPAY_KEY_SECRET_LIVE")

razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))


@login_required
def checkout_view(request):
    business = BusinessNameAndLogo.objects.first()
    allowed_pincodes = business.allowed_pincodes if business and business.allowed_pincodes else []

    buy_now = request.session.get("buy_now")
    items = CartItem.objects.filter(user=request.user)

    if buy_now:
        product = get_object_or_404(Product, id=buy_now["product_id"])
        variant = None
        if buy_now.get("variant_id"):
            variant = ProductVariant.objects.filter(id=buy_now["variant_id"]).first()
        price = variant.display_price() if variant else product.price
        total = float(price)
        context_items = [{
            "product": product,
            "variant": variant,
            "quantity": 1,
            "price": price,
        }]
    else:
        if not items:
            messages.warning(request, "Your cart is empty.")
            return redirect("home")
        total = sum(item.subtotal() for item in items)
        context_items = items

    if request.method == "POST":
        postal_code = request.POST.get("postal_code", "")
        try: postal_code = int(postal_code)
        except:
            messages.warning(request, "Please enter a valid postal code.")
            return render(request, "checkout.html", {"items": context_items, "total": total})

        if postal_code not in allowed_pincodes:
            messages.warning(request, "This pincode is not serviceable.")
            return render(request, "checkout.html", {"items": context_items, "total": total})

        phone_number = request.POST.get("phone_number", "").strip()
        if not (phone_number.isdigit() and len(phone_number) == 10 and phone_number[0] in "6789"):
            messages.error(request, "Enter a valid phone number.")
            return redirect("checkout")

        request.session["checkout_info"] = {
            "full_name": request.POST["full_name"],
            "address": request.POST["address"],
            "city": request.POST["city"],
            "postal_code": postal_code,
            "phone_number": phone_number,
            "total": float(total),
        }

        return redirect("payment")

    return render(request, "checkout.html", {
        "items": context_items,
        "total": total,
        "busness": business,
    })


@login_required
def payment_view(request):
    checkout_info = request.session.get("checkout_info")
    if not checkout_info:
        messages.error(request, "Missing checkout information.")
        return redirect("checkout")

    total = checkout_info["total"]
    return render(request, "payment.html", {
        "total": total,
        "razorpay_key": RAZORPAY_KEY_ID
    })


# ======================
# CREATE Razorpay Order (AJAX)
# ======================
@csrf_exempt
@login_required
def razorpay_create_order(request):
    try:
        if request.method != "POST":
            return JsonResponse({"success": False, "error": "Invalid request"}, status=400)

        checkout_info = request.session.get("checkout_info")
        if not checkout_info:
            return JsonResponse({"success": False, "error": "Session expired"}, status=400)

        # ✔ Safe number conversion
        from decimal import Decimal
        total = Decimal(str(checkout_info["total"]))
        total_paise = int(total * 100)

        print("Creating Razorpay Order: ", total_paise)  # DEBUG

        # ✔ Create Razorpay order successfully
        razorpay_order = razorpay_client.order.create({
            "amount": total_paise,
            "currency": "INR",
            "payment_capture": 1,
            "notes": {"customer": request.user.username}
        })

        print("Razorpay Order Created: ", razorpay_order)  # DEBUG

        return JsonResponse({
            "success": True,
            "order_id": razorpay_order["id"],
            "amount": total_paise,
            "razorpay_key": RAZORPAY_KEY_ID
        })

    except Exception as e:
        print("RAZORPAY ERROR (create order):", str(e))  # DEBUG LOGGING
        return JsonResponse({"success": False, "error": str(e)})



# ======================
# VERIFY PAYMENT + CREATE ORDER
# ======================
from decimal import Decimal
@csrf_exempt
@login_required
def payment_verify_view(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Invalid request"}, status=400)

    data = request.POST
    rp_order_id = data.get("razorpay_order_id")
    rp_payment_id = data.get("razorpay_payment_id")
    rp_signature = data.get("razorpay_signature")

    try:
        razorpay_client.utility.verify_payment_signature({
            "razorpay_order_id": rp_order_id,
            "razorpay_payment_id": rp_payment_id,
            "razorpay_signature": rp_signature
        })
        print("Signature Verified!")  # DEBUG

        # Confirm payment status from Razorpay server
        payment_info = razorpay_client.payment.fetch(rp_payment_id)
        print("Razorpay Payment Data:", payment_info) # DEBUG

        if payment_info.get("status") != "captured":
            print("Payment not captured automatically, capturing now...") # DEBUG
            razorpay_client.payment.capture(rp_payment_id, int(Decimal(str(request.session['checkout_info']['total'])) * 100))

    except Exception as e:
        print("Signature ERROR:", str(e)) # DEBUG
        return JsonResponse({"success": False, "error": "Signature verification failed"})


    buy_now = request.session.get("buy_now")
    checkout_info = request.session.get("checkout_info")
    cart_items = CartItem.objects.filter(user=request.user)
    total = checkout_info["total"]

    # Create order now only after success
    order = Order.objects.create(
        user=request.user,
        full_name=checkout_info["full_name"],
        address=checkout_info["address"],
        city=checkout_info["city"],
        postal_code=checkout_info["postal_code"],
        phone_number=checkout_info["phone_number"],
        payment_method="card/upi",
        paid=True,
        razorpay_order_id=rp_order_id,
        payment_id=rp_payment_id,
    )

    items_for_email = []
    admin_rows = []

    # BUY NOW
    if buy_now:
        product = get_object_or_404(Product, id=buy_now["product_id"])
        variant = None
        if buy_now.get("variant_id"):
            variant = ProductVariant.objects.filter(id=buy_now["variant_id"]).first()

        price = variant.display_price() if variant else product.price
        OrderItem.objects.create(order=order, product=product, variant=variant, quantity=1, price=price)
        if variant:
            variant.stock -= 1
            variant.save()
        else:
            product.available_stock -= 1
            product.save()

        items_for_email.append(f"- {product.name} (x1) — ₹{price}")
        admin_rows.append(f"<tr><td>{product.name}</td><td>1</td><td>₹{price}</td></tr>")

        request.session.pop("buy_now", None)

    else:
        for item in cart_items:
            p = item.product
            v = item.variant
            price = v.display_price() if v else p.price

            OrderItem.objects.create(order=order, product=p, variant=v, quantity=item.quantity, price=price)
            if v:
                v.stock -= item.quantity
                v.save()
            else:
                p.available_stock -= item.quantity
                p.save()

            items_for_email.append(f"- {p.name} (x{item.quantity}) — ₹{price}")
            admin_rows.append(f"<tr><td>{p.name}</td><td>{item.quantity}</td><td>₹{price}</td></tr>")

        cart_items.delete()

    # SEND EMAILS — your exact original logic
    from store.email_service import send_brevo_email
    from django.conf import settings
    admin_email = settings.ADMIN_EMAIL

    admin_order_link = request.build_absolute_uri(
        reverse("admin_order_detail", args=[order.id])
    )

    admin_html = f"""
    <h2>📦 New Order Received</h2>

    <p><strong>Order ID:</strong> #{order.id}</p>

    <h3>👤 Customer Details</h3>
    <p>
    <strong>Name:</strong> {order.full_name}<br>
    <strong>Phone:</strong> {order.phone_number}<br>
    <strong>Email:</strong> {order.user.email}<br>
    <strong>Address:</strong> {order.address}, {order.city}, {order.postal_code}
    </p>

    <h3>🛒 Order Items</h3>

    <table border="1" cellpadding="8" cellspacing="0" style="border-collapse:collapse;width:100%">
    <tr>
    <th>Product</th>
    <th>Qty</th>
    <th>Price</th>
    </tr>
    {''.join(admin_rows)}
    </table>

    <h3>💰 Total Amount: ₹{total}</h3>

    <br>

    <a href="{admin_order_link}"
    style="
    background:#ff8c00;
    color:white;
    padding:12px 20px;
    border-radius:8px;
    text-decoration:none;
    font-weight:600;
    ">
    View Order in Admin Panel
    </a>

    <p style="margin-top:20px;color:#555">
    This is an automated notification from Devki Mart.
    </p>
    """

    # Only send if admin_email exists
    if admin_email:
        try:
            send_brevo_email(to=admin_email, subject="New", html_content=admin_html, text_content="New order received.")

        except Exception as e:
            print("Brevo admin email error:", e)
    else:
        print("ADMIN_EMAIL not set – skipping admin email")

    customer_items_html = "".join(
        [f"<li>{line}</li>" for line in items_for_email]
    )

    customer_html = f"""
    <div style="font-family:Arial, sans-serif; padding:20px; background:#f7f7f7;">
        <div style="max-width:600px; margin:auto; background:white; padding:25px; border-radius:10px;">

            <h2 style="color:#ff8c00;">🎉 Order Confirmed!</h2>
            <p>Hi <strong>{order.full_name}</strong>,</p>

            <p>Thank you for shopping with <strong>Sona Enterprises</strong>!  
            Your order has been successfully placed.</p>

            <h3>📦 Order Details</h3>
            <p><strong>Order ID:</strong> #{order.id}</p>

            <h3>🛒 Items Ordered:</h3>
            <ul style="padding-left:20px; line-height:1.6;">
                {customer_items_html}
            </ul>

            <h3>💰 Total Amount: ₹{total}</h3>

            <h3>📍 Delivery Details:</h3>
            <p>
            <strong>Name:</strong> {order.full_name} <br>
            <strong>Phone:</strong> {order.phone_number} <br>
            <strong>Address:</strong> {order.address}, {order.city}, {order.postal_code}
            </p>

            <p>This is a Cash On Delivery order. You will receive updates as your order progresses.</p>

            <p style="margin-top:30px;">Thank you for choosing us! 😊</p>

            <hr style="border:none; border-top:1px solid #ddd; margin:25px 0;">
            <p style="font-size:12px; color:#555;">This is an automated email from Sona Enterprises.</p>
        </div>
    </div>
    """
    customer_email = request.user.email
    if customer_email:
        try:
            send_brevo_email(to=customer_email, subject=f"Order #{order.id} Successful!", html_content=customer_html, text_content="Order placed successfully.")
        except Exception as e:
            print("Brevo customer email error:", e)
    else:
        print("Customer email missing – skipping customer email send")


    delivery_boys = CustomUser.objects.filter(is_delivery_boy=True)

    if delivery_boys.count() == 1:
        delivery_boy = delivery_boys.first()
        delivery_email = delivery_boy.email

        if delivery_email:
            link = request.build_absolute_uri(
                f"/delivery/order/{order.id}/"
            )

            subject = f"New Order Assigned — Order #{order.id}"

            text_content = (
                f"Hello {delivery_boy.username},\n\n"
                f"You have been assigned a new order.\n"
                f"Order ID: #{order.id}\n"
                f"Customer: {order.full_name}\n"
                f"Delivery Address: {order.address}, {order.city}, {order.postal_code}\n\n"
                f"Open Dashboard: {link}\n\n"
                "Thank you!"
            )

            html_content = f"""
            <div style="font-family:Arial;padding:16px;background:#f7f7f7;">
              <div style="max-width:600px;background:white;padding:20px;border-radius:8px;">
                <h2>New Order Assigned — #{order.id}</h2>
                <p><strong>Customer:</strong> {order.full_name}</p>
                <p><strong>Address:</strong> {order.address}, {order.city}</p>
                <p><strong>Postal Code:</strong> {order.postal_code}</p>
                <p><strong>Phone:</strong> {order.phone_number}</p>
                <br>
                <a href="{link}" 
                   style="background:#f59e0b;color:white;padding:10px 16px;border-radius:6px;text-decoration:none;">
                   Open Delivery Dashboard
                </a>
              </div>
            </div>
            """

            try:
                send_brevo_email(
                    to=delivery_email,
                    subject=subject,
                    html_content=html_content,
                    text_content=text_content
                )
            except Exception as e:
                print("Delivery boy email error:", e)

    return JsonResponse({"success": True})




from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from store.models import Product, ProductVariant, CartItem, Order, OrderItem
from django.conf import settings


@login_required
def cod_order_view(request):
    checkout_info = request.session.get("checkout_info")
    if not checkout_info:
        messages.error(request, "Missing checkout data")
        return redirect("checkout")

    buy_now = request.session.get("buy_now")
    cart_items = CartItem.objects.filter(user=request.user)
    total = checkout_info["total"]

    # Create COD order
    order = Order.objects.create(
        user=request.user,
        full_name=checkout_info["full_name"],
        address=checkout_info["address"],
        city=checkout_info["city"],
        postal_code=checkout_info["postal_code"],
        phone_number=checkout_info["phone_number"],
        payment_method="COD",
        paid=False
    )

    items_for_email = []

    if buy_now:
        product = get_object_or_404(Product, id=buy_now["product_id"])
        variant = None
        if buy_now.get("variant_id"):
            variant = ProductVariant.objects.filter(id=buy_now["variant_id"]).first()

        price = variant.display_price() if variant else product.price

        OrderItem.objects.create(order=order, product=product, variant=variant, quantity=1, price=price)

        # Stock update
        if variant:
            variant.stock -= 1
            variant.save()
        else:
            product.available_stock -= 1
            product.save()

        items_for_email.append(f"- {product.name} (x1) — ₹{price}")

        request.session.pop("buy_now", None)

    else:
        for item in cart_items:
            p = item.product
            v = item.variant
            price = v.display_price() if v else p.price

            OrderItem.objects.create(order=order, product=p, variant=v, quantity=item.quantity, price=price)

            if v:
                v.stock -= item.quantity
                v.save()
            else:
                p.available_stock -= item.quantity
                p.save()

            items_for_email.append(f"- {p.name} (x{item.quantity}) — ₹{price}")

        cart_items.delete()

    # ======================
    # ✉ SEND EMAIL — Amazon Style
    # ======================
    from store.email_service import send_brevo_email

    admin_email = settings.ADMIN_EMAIL
    customer_email = request.user.email

    # Items Table
    rows_html = "".join(
        f"""
        <tr>
            <td style='padding:6px 10px;border-bottom:1px solid #eee;'>{line.split(' (')[0][2:]}</td>
            <td style='padding:6px 10px;border-bottom:1px solid #eee;'>{line.split('x')[1].split(')')[0]}</td>
            <td style='padding:6px 10px;border-bottom:1px solid #eee;text-align:right;'>{line.split('— ')[1]}</td>
        </tr>
        """
        for line in items_for_email
    )

    customer_html = f"""
    <div style="font-family:Arial, sans-serif;max-width:600px;margin:auto;background:#fff;border-radius:10px;
    padding:25px;border:1px solid #ddd;">
        
        <div style="text-align:center;margin-bottom:20px;">
            <h2 style="color:#ff8800;font-size:24px;">Order Confirmed 🎉</h2>
            <p>Hello <strong>{order.full_name}</strong>,</p>
            <p>Thank you for shopping with <b>Devki Mart</b>!</p>
        </div>

        <p><strong>Order ID:</strong> #{order.id}</p>
        <p><strong>Payment Method:</strong> Cash On Delivery</p>

        <h3 style="margin-top:20px;font-size:16px;color:#111;">Ordered Items</h3>
        <table width="100%" cellpadding="0" cellspacing="0" style="margin-top:10px;border-collapse:collapse;">
            <tr style="background:#fff7e6;color:#111;font-weight:bold;">
                <td style="padding:10px;">Product</td>
                <td style="padding:10px;">Qty</td>
                <td style="padding:10px;text-align:right;">Price</td>
            </tr>
            {rows_html}
        </table>

        <h3 style="text-align:right;margin-top:15px;">
            Total: <span style="color:#ff8c00;font-size:22px;">₹{total}</span>
        </h3>

        <h3 style="margin-top:20px;">Delivery Address</h3>
        <p>
            {order.full_name} <br>
            {order.address}, {order.city} <br>
            {order.postal_code} <br>
            📞 {order.phone_number}
        </p>

        <a href="{request.build_absolute_uri(reverse('my_orders'))}"
           style="display:inline-block;margin-top:20px;padding:12px 20px;background:#ff8c00;color:white;
           font-size:16px;border-radius:6px;text-decoration:none;">
           Track My Order 🚚
        </a>

        <p style="font-size:12px;color:#777;margin-top:20px;text-align:center;">
            This is an automated email from Devki Mart.
        </p>
    </div>
    """


        # 📩 SEND EMAIL TO DELIVERY BOY IF ONLY ONE EXISTS
    from store.models import CustomUser
    delivery_boys = CustomUser.objects.filter(is_delivery_boy=True)

    if delivery_boys.count() == 1:
        delivery_boy = delivery_boys.first()
        delivery_email = delivery_boy.email

        if delivery_email:
            link = request.build_absolute_uri(
                f"/delivery/order/{order.id}/"
            )

            subject = f"New Order Assigned — Order #{order.id}"

            text_content = (
                f"Hello {delivery_boy.username},\n\n"
                f"You have been assigned a new order.\n"
                f"Order ID: #{order.id}\n"
                f"Customer: {order.full_name}\n"
                f"Delivery Address: {order.address}, {order.city}, {order.postal_code}\n\n"
                f"Open Dashboard: {link}\n\n"
                "Thank you!"
            )

            html_content = f"""
            <div style="font-family:Arial;padding:16px;background:#f7f7f7;">
              <div style="max-width:600px;background:white;padding:20px;border-radius:8px;">
                <h2>New Order Assigned — #{order.id}</h2>
                <p><strong>Customer:</strong> {order.full_name}</p>
                <p><strong>Address:</strong> {order.address}, {order.city}</p>
                <p><strong>Postal Code:</strong> {order.postal_code}</p>
                <p><strong>Phone:</strong> {order.phone_number}</p>
                <br>
                <a href="{link}" 
                   style="background:#f59e0b;color:white;padding:10px 16px;border-radius:6px;text-decoration:none;">
                   Open Delivery Dashboard
                </a>
              </div>
            </div>
            """

            try:
                send_brevo_email(
                    to=delivery_email,
                    subject=subject,
                    html_content=html_content,
                    text_content=text_content
                )
            except Exception as e:
                print("Delivery boy email error:", e)


    if customer_email:
        try:
            send_brevo_email(
                to=customer_email, 
                subject=f"Order #{order.id} Confirmed 🎉", 
                html_content=customer_html,
                text_content=f"Your order #{order.id} has been successfully placed!"
            )
        except Exception as e:
            print("Customer email error:", e)

    # Admin email notification
    if admin_email:
        try:
            send_brevo_email(
                to=admin_email,
                subject=f"NEW COD Order #{order.id}",
                html_content=f"<p>COD Order #{order.id} placed by {order.full_name}</p>",
                text_content="A new order has been received in Devki Mart."
            )
        except Exception as e:
            print("Admin email error:", e)

    # Clear only checkout session
    request.session.pop("checkout_info", None)

    return redirect("order_success")



def order_success_view(request):
    return render(request, "order_success.html")
