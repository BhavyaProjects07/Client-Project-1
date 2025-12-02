from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.urls import reverse

from store.models import (
    Product,
    ProductVariant,
    CartItem,
    Order,
    OrderItem,BusinessNameAndLogo
)


# ============================
# CHECKOUT PAGE
# ============================

@login_required
def checkout_view(request):

    business = BusinessNameAndLogo.objects.first()
    allowed_pincodes = business.allowed_pincodes if business and business.allowed_pincodes else []

    buy_now = request.session.get("buy_now")
    items = CartItem.objects.filter(user=request.user)

    # ---------- BUY NOW ----------
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
        # ---------- NORMAL CART ----------
        if not items:
            messages.warning(request, "Your cart is empty.")
            return redirect("home")

        total = sum(item.subtotal() for item in items)
        context_items = items

    # ---------- FORM SUBMIT ----------
    if request.method == "POST":

        postal_code = request.POST.get("postal_code", "")
        try:
            postal_code = int(postal_code)
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
    })



# ============================
# PAYMENT PAGE
# ============================

@login_required
def payment_view(request):
    checkout_info = request.session.get("checkout_info")
    if not checkout_info:
        messages.error(request, "Missing checkout information.")
        return redirect("checkout")

    buy_now = request.session.get("buy_now")
    cart_items = CartItem.objects.filter(user=request.user)
    total = checkout_info["total"]

    if request.method == "POST":
        # Create order
        order = Order.objects.create(
            user=request.user,
            full_name=checkout_info["full_name"],
            address=checkout_info["address"],
            city=checkout_info["city"],
            postal_code=checkout_info["postal_code"],
            phone_number=checkout_info["phone_number"],
            payment_method="Cash On Delivery",
            paid=False,
        )

        items_for_email = []
        admin_rows = []

        # ---------------------------------------------------
        # BUY NOW
        # ---------------------------------------------------
        if buy_now:
            product = get_object_or_404(Product, id=buy_now["product_id"])
            variant = None

            if buy_now.get("variant_id"):
                variant = ProductVariant.objects.filter(id=buy_now["variant_id"]).first()

            price = variant.display_price() if variant else product.price

            OrderItem.objects.create(
                order=order,
                product=product,
                variant=variant,
                quantity=1,
                price=price
            )

            items_for_email.append(f"- {product.name} (x1) — ₹{price}")
            admin_rows.append(
                f"<tr><td>{product.name}</td><td>1</td><td>₹{price}</td></tr>"
            )

            request.session.pop("buy_now", None)

        # ---------------------------------------------------
        # NORMAL CART
        # ---------------------------------------------------
        else:
            for item in cart_items:
                product = item.product
                variant = item.variant

                price = variant.display_price() if variant else product.price

                # reduce stock
                if variant:
                    if variant.stock < item.quantity:
                        messages.warning(request, f"Not enough stock for {product.name}.")
                        continue
                    variant.stock -= item.quantity
                    variant.save()
                else:
                    if product.available_stock < item.quantity:
                        messages.warning(request, f"Not enough stock for {product.name}.")
                        continue
                    product.available_stock -= item.quantity
                    product.save()

                # create order item
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    variant=variant,
                    quantity=item.quantity,
                    price=price
                )

                items_for_email.append(f"- {product.name} (x{item.quantity}) — ₹{price}")
                admin_rows.append(
                    f"<tr><td>{product.name}</td><td>{item.quantity}</td><td>₹{price}</td></tr>"
                )

            cart_items.delete()

        # Emails (you already have Brevo service) → unchanged
        # SEND CUSTOMER + ADMIN EMAIL HERE

        # ============================
# SEND ADMIN NOTIFICATION EMAIL
# ============================

        from django.urls import reverse
        from email_service import send_brevo_email

        admin_email = "youradmin@gmail.com"   # change to your admin email

        dashboard_link = request.build_absolute_uri(
            reverse("delivery_dashboard")  # your admin dashboard url name
        )

        admin_html = f"""
        <h2>📦 New Order Received</h2>

        <p><strong>Order ID:</strong> #{order.id}</p>

        <h3>👤 Customer Details</h3>
        <p>
        <strong>Name:</strong> {order.full_name}<br>
        <strong>Phone:</strong> {order.phone_number}<br>
        <strong>Address:</strong> {order.address}, {order.city}, {order.postal_code}<br>
        <strong>Email:</strong> {order.user.email}
        </p>

        <h3>🛒 Order Items</h3>

        <table border="1" cellspacing="0" cellpadding="8" style="border-collapse: collapse;">
            <tr>
                <th>Product</th>
                <th>Qty</th>
                <th>Price (₹)</th>
            </tr>
            {''.join(admin_rows)}
        </table>

        <h3>💰 Total Amount: ₹{total}</h3>

        <br>
        <a href="{dashboard_link}"
        style="background:#ff8c00;color:white;padding:10px 18px;border-radius:6px;text-decoration:none">
        Open Delivery Dashboard
        </a>

        <p style="margin-top:20px;">This is an automated message from Sona Enterprises.</p>
        """

        send_brevo_email(
            to=admin_email,
            subject=f"New Order Received #{order.id}",
            html_content=admin_html
        )



        # ============================
        # SEND CUSTOMER ORDER EMAIL
        # ============================

        customer_email = order.user.email

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

        send_brevo_email(
            to=customer_email,
            subject=f"Your Order #{order.id} Has Been Placed Successfully!",
            html_content=customer_html
        )



        messages.success(request, "Order placed successfully!")
        return redirect("order_success")

    return render(request, "payment.html", {"total": total})


def order_success_view(request):
    return render(request, "order_success.html")
