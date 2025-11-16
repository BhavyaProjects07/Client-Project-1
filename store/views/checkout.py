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



# ======================================================
# CHECKOUT SYSTEM
# ======================================================


from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

@login_required
def checkout_view(request):
    Allowed_pinCodes = [
        248001, 248002, 248003, 248004, 248005, 248006,
        248007, 248008, 248009, 248012, 248013, 248014,
        248015, 248018, 248021, 248046, 248071, 248095
    ]

    buy_now_data = request.session.get('buy_now')
    items = CartItem.objects.filter(user=request.user)

    # 🧠 Case 1: Buy Now checkout
    if buy_now_data:
        from store.models import WomenProduct, ElectronicProduct, ToyProduct

        product = None
        if buy_now_data['product_type'] == 'women':
            product = WomenProduct.objects.filter(id=buy_now_data['product_id']).first()
        elif buy_now_data['product_type'] == 'electronic':
            product = ElectronicProduct.objects.filter(id=buy_now_data['product_id']).first()
        elif buy_now_data['product_type'] == 'toy':
            product = ToyProduct.objects.filter(id=buy_now_data['product_id']).first()

        if not product:
            messages.error(request, "Product not found.")
            return redirect('home')

        total = float(product.price)
        temp_item = {
            'product': product,
            'product_type': buy_now_data['product_type'],
            'quantity': 1,
            'price': product.price,
            'size': buy_now_data.get('size'),
            'color': buy_now_data.get('color'),
            'fabric': buy_now_data.get('fabric'),
        }
        context_items = [temp_item]

    # 🛒 Case 2: Normal cart checkout
    else:
        if not items:
            messages.warning(request, "Your cart is empty.")
            return redirect('home')
        total = sum(item.subtotal() for item in items)
        context_items = items

    # ✅ Handle POST request (form submission)
    if request.method == "POST":
        postal_code = request.POST.get('postal_code')

        # Check if postal code is numeric before conversion
        try:
            postal_code = int(postal_code)
        except (TypeError, ValueError):
            messages.warning(request, "Please enter a valid postal code.")
            return render(request, 'checkout.html', {'items': context_items, 'total': total})

        # ❌ Check if postal code is not in allowed list
        if postal_code not in Allowed_pinCodes:
            messages.warning(request, "Not deliverable at this pincode.")
            return render(request, 'checkout.html', {'items': context_items, 'total': total})

        # 📞 Phone Number Validation (Indian numbers must start with 6,7,8,9)
        phone_number = request.POST.get('phone_number', '')

        # Remove spaces just in case
        phone_number = phone_number.strip()

        if (
            not phone_number.isdigit() or 
            len(phone_number) != 10 or 
            phone_number[0] not in ['6', '7', '8', '9']
        ):
            messages.error(request, "Enter a valid number.")
            return redirect('checkout')


        # ✅ Save checkout info and redirect to payment
        request.session['checkout_info'] = {
            'full_name': request.POST['full_name'],
            'address': request.POST['address'],
            'city': request.POST['city'],
            'postal_code': postal_code,
            'phone_number': request.POST['phone_number'],
            'total': float(total),
        }
        return redirect('payment')

    return render(request, 'checkout.html', {'items': context_items, 'total': total})



from django.urls import reverse   # <-- ADD THIS AT TOP WITH OTHER IMPORTS

@login_required
def payment_view(request):
    checkout_info = request.session.get('checkout_info')
    if not checkout_info:
        messages.error(request, "Missing checkout info.")
        return redirect('checkout')

    buy_now_data = request.session.get('buy_now')
    cart_items = CartItem.objects.filter(user=request.user)
    total = checkout_info['total']

    if request.method == "POST":
        # Create Order
        order = Order.objects.create(
            user=request.user,
            full_name=checkout_info['full_name'],
            address=checkout_info['address'],
            city=checkout_info['city'],
            postal_code=checkout_info['postal_code'],
            phone_number=checkout_info['phone_number'],
            payment_method="Cash On Delivery",
            paid=False
        )

        item_details = ""               # plaintext item list for customer email
        admin_items_rows = []           # list of HTML rows for admin table

        # Case 1: Buy Now
        if buy_now_data:
            product = None
            if buy_now_data['product_type'] == 'women':
                product = WomenProduct.objects.filter(id=buy_now_data['product_id']).first()
            elif buy_now_data['product_type'] == 'electronic':
                product = ElectronicProduct.objects.filter(id=buy_now_data['product_id']).first()
            elif buy_now_data['product_type'] == 'toy':
                product = ToyProduct.objects.filter(id=buy_now_data['product_id']).first()

            if product:
                OrderItem.objects.create(
                    order=order,
                    product_type=buy_now_data['product_type'],
                    product_id=product.id,
                    quantity=1,
                    price=product.price,
                    size=buy_now_data.get('size'),
                    color=buy_now_data.get('color'),
                    fabric=buy_now_data.get('fabric')
                )
                item_details += f"- {product.name} (x1) - ₹{product.price}\n"
                admin_items_rows.append(
                    f"<tr>"
                    f"<td>{product.name}</td>"
                    f"<td>{buy_now_data.get('product_type')}</td>"
                    f"<td>1</td>"
                    f"<td>₹{product.price:.2f}</td>"
                    f"</tr>"
                )

            request.session.pop('buy_now', None)

        # Case 2: Normal Cart Checkout
        else:
            for item in cart_items:
                product = item.get_product()
                if not product:
                    continue

                if product.available_stock >= item.quantity:
                    product.available_stock -= item.quantity
                    product.save()
                else:
                    messages.warning(request, f"Not enough stock for {product.name}.")
                    continue

                OrderItem.objects.create(
                    order=order,
                    product_type=item.product_type,
                    product_id=item.product_id,
                    quantity=item.quantity,
                    price=product.price,
                    size=item.size,
                    color=item.color,
                    fabric=item.fabric
                )

                item_details += f"- {product.name} (x{item.quantity}) - ₹{product.price}\n"
                admin_items_rows.append(
                    f"<tr>"
                    f"<td>{product.name}</td>"
                    f"<td>{item.product_type}</td>"
                    f"<td>{item.quantity}</td>"
                    f"<td>₹{product.price:.2f}</td>"
                    f"</tr>"
                )

            cart_items.delete()

        # ---------- Prepare emails ----------
        customer_subject = f"Order Confirmation #{order.id} - Sona Enterprises"

        # DEFINE CUSTOMER_BODY (TEXT VERSION)
        customer_body = (
            f"Hello {order.full_name},\n\n"
            f"Your order #{order.id} has been placed successfully!\n\n"
            f"ORDER DETAILS:\n"
            f"Customer Name: {order.full_name}\n"
            f"Email: {request.user.email}\n"
            f"Phone: {order.phone_number}\n"
            f"Address: {order.address}, {order.city}, {order.postal_code}\n\n"
            f"Payment Method: {order.payment_method}\n"
            f"Order Items:\n{item_details}\n"
            f"Total Amount: ₹{total}\n\n"
            f"Thank you for shopping with Sona Enterprises!\n"
            f"We'll notify you when your order ships.\n\n"
            f"- Team Sona Enterprises"
        )

        # ⭐ BEAUTIFUL CUSTOMER HTML TEMPLATE
        customer_html = f"""
        <div style="font-family:'Segoe UI',sans-serif;background:#f5f5f5;padding:30px;">
            <div style="max-width:600px;margin:auto;background:white;border-radius:12px;padding:25px;">
                <h2 style="color:#333;">🎉 Thank you for your order, {order.full_name}!</h2>

                <p style="font-size:15px;color:#555;">
                    Your order <strong>#{order.id}</strong> has been placed successfully.
                </p>

                <h3 style="color:#333;margin-top:25px;">📦 Order Summary</h3>

                <table style="width:100%;border-collapse:collapse;">
                    <tr><td><strong>Name:</strong></td><td>{order.full_name}</td></tr>
                    <tr><td><strong>Email:</strong></td><td>{request.user.email}</td></tr>
                    <tr><td><strong>Phone:</strong></td><td>{order.phone_number}</td></tr>
                    <tr><td><strong>Address:</strong></td><td>{order.address}, {order.city}, {order.postal_code}</td></tr>
                    <tr><td><strong>Payment Method:</strong></td><td>{order.payment_method}</td></tr>
                </table>

                <h3 style="color:#333;margin-top:25px;">🛍 Order Items</h3>
                <pre style="background:#fafafa;padding:12px;border-radius:8px;border:1px solid #eee;font-size:14px;">{item_details}</pre>

                <h2 style="color:#333;margin-top:25px;">Total Amount: ₹{total}</h2>

                <p style="font-size:14px;color:#777;margin-top:25px;">
                    We'll notify you once your order is shipped.<br><br>
                    Thank you for choosing <strong>Sona Enterprises</strong> ❤️
                </p>
            </div>
        </div>
        """

        # ADMIN TEMPLATE
        admin_subject = f"NEW ORDER #{order.id} - Sona Enterprises"
        admin_order_url = request.build_absolute_uri(reverse('admin_order_detail', args=[order.id]))

        admin_html = f"""
        <div style="font-family:'Segoe UI',sans-serif;background:#f3f3f3;padding:30px;">
            <div style="max-width:700px;margin:auto;background:white;border-radius:12px;padding:25px;">
                <h2 style="color:#333;">New Order Received — #{order.id}</h2>

                <p><strong>Customer:</strong> {order.full_name} &lt;{request.user.email}&gt;</p>
                <p><strong>Phone:</strong> {order.phone_number}</p>
                <p><strong>Address:</strong> {order.address}, {order.city} — {order.postal_code}</p>
                <p><strong>Payment:</strong> {order.payment_method}</p>

                <h3 style="margin-top:25px;">🛒 Items Ordered</h3>

                <table style="width:100%;border-collapse:collapse;">
                    <tr style="background:#f7f7f7;">
                        <th>Product</th><th>Type</th><th>Qty</th><th>Price</th>
                    </tr>
                    {''.join(admin_items_rows)}
                    <tr>
                        <td colspan="3" align="right"><strong>Total</strong></td>
                        <td><strong>₹{total}</strong></td>
                    </tr>
                </table>

                <p style="margin-top:18px;">
                    <strong>Admin Panel Link:</strong><br>
                    {admin_order_url}
                </p>

                <p style="font-size:13px;color:#666;">Automated system — Sona Enterprises.</p>
            </div>
        </div>
        """

        admin_text = (
            f"New Order #{order.id}\nCustomer: {order.full_name}\nEmail: {request.user.email}\nTotal: ₹{total}\n"
        )

        # ---------- SEND EMAILS WITH BREVO ----------
        from store.email_service import send_brevo_email

        # Customer email
        send_brevo_email(
            to=request.user.email,
            subject=customer_subject,
            html_content=customer_html,
            text_content=customer_body
        )

        # Admin email
        admin_email = getattr(settings, 'ADMIN_EMAIL', None)
        if admin_email:
            send_brevo_email(
                to=admin_email,
                subject=admin_subject,
                html_content=admin_html,
                text_content=admin_text
            )

        messages.success(request, "Order placed successfully! A confirmation email has been sent.")
        return redirect('order_success')

    return render(request, 'payment.html', {'total': total})


def order_success_view(request):
    return render(request, 'order_success.html')