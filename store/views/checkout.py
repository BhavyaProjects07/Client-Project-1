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

        messages.success(request, "Order placed successfully!")
        return redirect("order_success")

    return render(request, "payment.html", {"total": total})


def order_success_view(request):
    return render(request, "order_success.html")
