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
from .models import (
    CustomUser, WomenProduct, ElectronicProduct, ToyProduct,
    CartItem, WishlistItem, Order, OrderItem, Review
)
from .forms import ReviewForm

User = get_user_model()
otp_storage = {}  # Temporary OTP storage

# ======================================================
# HOME VIEW
# ======================================================

from django.db.models import Avg
from .models import WomenProduct, ElectronicProduct, ToyProduct, Review, WishlistItem
from django.db.models import Avg
from django.shortcuts import render
from .models import WomenProduct, ElectronicProduct, ToyProduct, Review, WishlistItem

def home(request):
    wishlist_count = WishlistItem.objects.filter(user=request.user).count() if request.user.is_authenticated else 0

    # ✅ Existing query for WOMEN section
    query = request.GET.get('q')
    category = request.GET.get('category')
    product_type = request.GET.get('type', 'women')  # default to women

    # ✅ New queries for ELECTRONICS and TOYS sections
    query_electronic = request.GET.get('q_electronic')
    query_toy = request.GET.get('q_toy')

    # ✅ Map models by type
    model_map = {
        'women': WomenProduct,
        'electronic': ElectronicProduct,
        'toy': ToyProduct,
    }

    ProductModel = model_map.get(product_type, WomenProduct)

    # ✅ Fetch all product types
    women_products = WomenProduct.objects.all()
    electronics_products = ElectronicProduct.objects.all()
    toys_products = ToyProduct.objects.all()

    # ✅ Attach product_type to each product
    for p in women_products:
        p.product_type = 'women'
    for p in electronics_products:
        p.product_type = 'electronic'
    for p in toys_products:
        p.product_type = 'toy'

    # ✅ Active product list (for WOMEN section)
    products = ProductModel.objects.all()

    # ✅ WOMEN Search filter (existing)
    if query:
        products = products.filter(name__icontains=query)

    # ✅ Category filter (existing)
    if category and category != 'all':
        products = products.filter(category__iexact=category)

    # ✅ ELECTRONICS search filter (new)
    if query_electronic:
        electronics_products = electronics_products.filter(name__icontains=query_electronic)

    # ✅ TOYS search filter (new)
    if query_toy:
        toys_products = toys_products.filter(name__icontains=query_toy)

    # ✅ Compute average rating & review count for active type
    for product in products:
        reviews = Review.objects.filter(product_type=product_type, product_id=product.id)
        product.average_rating = reviews.aggregate(avg=Avg('rating'))['avg'] or 0
        product.total_reviews = reviews.count()

    # ✅ Ratings for other sections
    for product in women_products:
        reviews = Review.objects.filter(product_type='women', product_id=product.id)
        product.average_rating = reviews.aggregate(avg=Avg('rating'))['avg'] or 0
        product.total_reviews = reviews.count()

    for product in electronics_products:
        reviews = Review.objects.filter(product_type='electronic', product_id=product.id)
        product.average_rating = reviews.aggregate(avg=Avg('rating'))['avg'] or 0
        product.total_reviews = reviews.count()

    for product in toys_products:
        reviews = Review.objects.filter(product_type='toy', product_id=product.id)
        product.average_rating = reviews.aggregate(avg=Avg('rating'))['avg'] or 0
        product.total_reviews = reviews.count()

    # ✅ Categories for filtering (Women)
    categories = [choice[0] for choice in ProductModel.CATEGORY_CHOICES]
    categories.insert(0, 'all')

    # ✅ Render everything
    return render(request, 'home.html', {
        'products': products,
        'women_products': women_products,
        'electronics_products': electronics_products,
        'toys_products': toys_products,
        'active_category': category if category else 'all',
        'categories': categories,
        'wishlist_count': wishlist_count,
        'product_type': product_type,
    })


# ======================================================
# OTP LOGIN SYSTEM
# ======================================================

def request_otp_view(request):
    if request.method == "POST":
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')

        # Check if user already exists
        user = User.objects.filter(email=email).first()

        if user:
            # Existing user: require password check before OTP
            if not user.check_password(password):
                messages.error(request, "Incorrect password. Please try again.")
                return redirect('/')
            otp = str(random.randint(100000, 999999))
            otp_storage[email] = {"otp": otp, "username": user.username, "password": password}

            send_mail(
                subject="Login OTP - Sona Enterprises",
                message=f"Hi {user.username},\n\nYour login OTP is: {otp}\n\nUse this to access your account securely.",
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[email],
            )
            request.session['pending_email'] = email
            messages.success(request, f"Login OTP sent to {email}")
            return redirect('verify_otp')

        else:
            # New user: create OTP and store password for verification
            otp = str(random.randint(100000, 999999))
            otp_storage[email] = {"otp": otp, "username": username, "password": password}

            send_mail(
                subject="Account Verification OTP - Sona Enterprises",
                message=f"Hi {username},\n\nYour OTP for registration is: {otp}\n\nUse this to verify and activate your account.",
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[email],
            )
            request.session['pending_email'] = email
            messages.success(request, f"OTP sent to {email} for account verification.")
            return redirect('verify_otp')

    return redirect('/')

def verify_otp_view(request):
    if request.method == "POST":
        email = request.session.get('pending_email')
        entered_otp = request.POST.get('otp')
        data = otp_storage.get(email)

        if not data:
            messages.error(request, "OTP expired or invalid. Please request again.")
            return redirect('request_otp')

        if data['otp'] == entered_otp:
            username = data['username']
            password = data['password']

            user, created = CustomUser.objects.get_or_create(email=email, defaults={'username': username})
            user.set_password(password)
            user.is_verified = True
            user.save()

            login(request, user)
            messages.success(request, f"Welcome back, {user.username}!" if not created else f"Account created successfully for {user.username}!")
            otp_storage.pop(email, None)
            return redirect('/')
        else:
            messages.error(request, "Invalid OTP. Please try again.")
            return redirect('verify_otp')

    return render(request, 'verify_otp.html')

def logout_view(request):
    logout(request)
    return redirect("/")


# ======================================================
# CART SYSTEM
# ======================================================

@login_required
def add_to_cart(request, product_type, product_id):
    CartItem.objects.create(
        user=request.user,
        product_type=product_type,
        product_id=product_id
    )
    messages.success(request, "Item added to cart.")
    return redirect('/')


@login_required
def view_cart(request):
    items = CartItem.objects.filter(user=request.user)
    total = sum(item.subtotal() for item in items)
    return render(request, 'cart.html', {'items': items, 'total': total})


@login_required
def remove_from_cart(request, item_id):
    CartItem.objects.filter(id=item_id, user=request.user).delete()
    return redirect('view_cart')


@require_POST
def update_cart_quantity(request, item_id):
    if not request.user.is_authenticated:
        return JsonResponse({'success': False}, status=401)

    try:
        data = json.loads(request.body)
        action = data.get('action')
        cart_item = CartItem.objects.get(id=item_id, user=request.user)

        if action == "increase":
            cart_item.quantity += 1
        elif action == "decrease" and cart_item.quantity > 1:
            cart_item.quantity -= 1
        cart_item.save()

        return JsonResponse({'success': True, 'item_id': item_id, 'quantity': cart_item.quantity})
    except CartItem.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Item not found'}, status=404)


# ======================================================
# WISHLIST SYSTEM
# ======================================================

@login_required
def add_to_wishlist(request, product_type, product_id):
    if WishlistItem.objects.filter(
        user=request.user, product_type=product_type, product_id=product_id
    ).exists():
        messages.info(request, "Item already in your wishlist.")
    else:
        WishlistItem.objects.create(
            user=request.user, product_type=product_type, product_id=product_id
        )
        messages.success(request, "Item added to wishlist.")
    return redirect('/')



def view_wishlist(request):

    if not request.user.is_authenticated:
        messages.warning(request, "⚠️ Please login to view your wishlist.")
        return redirect('home')
    wishlist_count = WishlistItem.objects.filter(user=request.user).count() if request.user.is_authenticated else 0
    items = WishlistItem.objects.filter(user=request.user)
    return render(request, 'wishlist.html', {'items': items,'wishlist_count': wishlist_count})

@login_required
def remove_from_wishlist(request, item_id):
    WishlistItem.objects.filter(id=item_id, user=request.user).delete()
    return redirect('view_wishlist')


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
        from .models import WomenProduct, ElectronicProduct, ToyProduct

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

        phone_number = request.POST.get('phone_number', '')
        if not phone_number.isdigit() or len(phone_number) != 10:
            messages.error(request, "Please enter a valid 10-digit phone number.")
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



from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.urls import reverse
from django.conf import settings
from django.core.mail import send_mail, EmailMultiAlternatives
import logging

logger = logging.getLogger(__name__)

# models imports
from store.models import CartItem, Order, OrderItem, WomenProduct, ElectronicProduct, ToyProduct

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

            # Clear buy_now session data
            request.session.pop('buy_now', None)

        # Case 2: Normal Cart Checkout
        else:
            for item in cart_items:
                product = item.get_product()
                if not product:
                    continue

                # stock check and decrement
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

            # clear user's cart
            cart_items.delete()

        # ---------- Prepare emails ----------
        # Customer (plaintext)
        customer_subject = f"Order Confirmation #{order.id} - Sona Enterprises"
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

        from_email = getattr(settings, 'EMAIL_HOST_USER', None) or getattr(settings, 'DEFAULT_FROM_EMAIL', None) or 'no-reply@example.com'

        # Admin email address (set ADMIN_EMAIL in settings or fallback)
        admin_email = getattr(settings, 'ADMIN_EMAIL', None) or getattr(settings, 'DEFAULT_FROM_EMAIL', None) or getattr(settings, 'EMAIL_HOST_USER', None)
        if not admin_email:
            logger.warning("No admin email configured in settings.ADMIN_EMAIL/DEFAULT_FROM_EMAIL/EMAIL_HOST_USER")

        # Admin email (HTML + plaintext)
        admin_subject = f"NEW ORDER #{order.id} - Sona Enterprises"
        # Build admin HTML table
        admin_table_rows = "".join(admin_items_rows) or "<tr><td colspan='4'>No items</td></tr>"

        admin_order_url = None
        try:
            admin_order_url = request.build_absolute_uri(reverse('admin_order_detail', args=[order.id]))
        except Exception:
            admin_order_url = "Admin order page not available"

        admin_html = f"""
        <html>
        <body>
        <h2>New Order Received — #{order.id}</h2>
        <p><strong>Customer:</strong> {order.full_name} &lt;{request.user.email}&gt;</p>
        <p><strong>Phone:</strong> {order.phone_number}</p>
        <p><strong>Shipping Address:</strong> {order.address}, {order.city} — {order.postal_code}</p>
        <p><strong>Payment Method:</strong> {order.payment_method}</p>

        <h3>Items</h3>
        <table border="0" cellpadding="6" cellspacing="0" style="border-collapse:collapse;width:100%;max-width:800px;">
          <thead>
            <tr style="background:#f7f7f7;">
              <th align="left">Product</th>
              <th align="left">Type</th>
              <th align="center">Qty</th>
              <th align="right">Unit Price</th>
            </tr>
          </thead>
          <tbody>
            {admin_table_rows}
          </tbody>
          <tfoot>
            <tr>
              <td colspan="3" align="right" style="padding-top:12px;"><strong>Total</strong></td>
              <td align="right" style="padding-top:12px;"><strong>₹{total}</strong></td>
            </tr>
          </tfoot>
        </table>

        <p style="margin-top:18px;">
          <a href="{admin_order_url}">View order in admin dashboard</a>
        </p>

        <p style="color:#666;font-size:13px;margin-top:24px;">This is an automated message from Sona Enterprises.</p>
        </body>
        </html>
        """

        admin_text = (
            f"NEW ORDER #{order.id}\n\n"
            f"Customer: {order.full_name} <{request.user.email}>\n"
            f"Phone: {order.phone_number}\n"
            f"Address: {order.address}, {order.city} - {order.postal_code}\n\n"
            f"Payment Method: {order.payment_method}\n\n"
            f"Items:\n"
            + item_details +
            f"\nTotal: ₹{total}\n\n"
            f"Admin link: {admin_order_url}\n"
        )

        # ---------- Send emails ----------
        # Send customer email (plaintext)
        try:
            send_mail(
                customer_subject,
                customer_body,
                from_email,
                [request.user.email],
                fail_silently=False,
            )
        except Exception as e:
            logger.exception("Failed to send order confirmation email to customer: %s", e)

        # Send admin email (HTML + text)
        if admin_email:
            try:
                msg = EmailMultiAlternatives(
                    subject=admin_subject,
                    body=admin_text,
                    from_email=from_email,
                    to=[admin_email],
                )
                msg.attach_alternative(admin_html, "text/html")
                msg.send(fail_silently=False)
            except Exception as e:
                logger.exception("Failed to send order notification to admin: %s", e)

        messages.success(request, "Order placed successfully! A confirmation email has been sent.")
        return redirect('order_success')

    return render(request, 'payment.html', {'total': total})



def order_success_view(request):
    return render(request, 'order_success.html')


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
# ADMIN DASHBOARD + ORDER MANAGEMENT (FINAL VERSION)
# ======================================================

from django.contrib.auth.decorators import user_passes_test, login_required
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from .models import (
    CustomUser, Order, WomenProduct, ElectronicProduct, ToyProduct
)


# ✅ Admin Check
def is_admin(user):
    return user.is_authenticated and user.is_staff


# ✅ Admin Dashboard Overview
@user_passes_test(is_admin)
def admin_dashboard_view(request):
    search_email = request.GET.get('q', '').strip()

    # If admin searches by email, filter orders for that user
    if search_email:
        orders = Order.objects.filter(user__email__icontains=search_email).order_by('-created_at')
        if not orders.exists():
            messages.warning(request, f"No orders found for email: {search_email}")
    else:
        orders = Order.objects.all().order_by('-created_at')[:10]  # default recent 10

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


from datetime import timedelta
# ✅ Admin Order Detail (supports all product types)
def admin_order_detail(request, order_id):
    from store.models import Order, OrderItem

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
            
        except Exception:
            product = None

        # Attach for template use
        item.product_obj = product
        item.total_price = item.quantity * item.price

    expected_delivery = order.created_at + timedelta(days=2)

    return render(request, 'order_detail.html', {
        'order': order,
        'order_items': order_items,
        'expected_delivery': expected_delivery
    })

# ✅ Update Order Status
@user_passes_test(is_admin)
@require_POST
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
        send_mail(
            subject=f"Order #{order.id} - {new_status}",
            message=f"Hello {order.full_name},\n\n{status_messages[new_status]}\n\nThank you for shopping with us!",
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[order.user.email],
        )

    messages.success(request, f"Order #{order.id} updated to {new_status}.")
    return redirect('admin_dashboard')


# Update Payment Status (separate action)
@user_passes_test(is_admin)
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
        messages.success(request, f"✅ Payment status for Order #{order.id} updated successfully!")

    return redirect('admin_order_detail', order_id=order.id)


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

# ======================================================
# REVIEW SYSTEM
# ======================================================

@login_required
def submit_review(request, order_id, product_type, product_id):
    order = get_object_or_404(Order, id=order_id, user=request.user, order_status='Delivered')

    try:
        review = Review.objects.get(user=request.user, product_type=product_type, product_id=product_id)
        created = False
    except Review.DoesNotExist:
        review = None
        created = True

    if request.method == 'POST':
        form = ReviewForm(request.POST, instance=review)
        if form.is_valid():
            new_review = form.save(commit=False)
            new_review.user = request.user
            new_review.product_type = product_type
            new_review.product_id = product_id
            new_review.order = order
            new_review.save()
            messages.success(request, "Your review has been submitted." if created else "Your review has been updated.")
            return redirect('my_orders')
    else:
        form = ReviewForm(instance=review)

    return render(request, 'submit_review.html', {'form': form, 'order': order})


def product_reviews_view(request, product_type, product_id):
    reviews = Review.objects.filter(product_type=product_type, product_id=product_id).select_related('user')
    return render(request, 'product_reviews.html', {'reviews': reviews})




# views for each product detail :

# 1st for women product

from django.shortcuts import render, get_object_or_404
from .models import WomenProduct  # Adjust model name as per your setup

def women_product_detail(request, product_id):
    product = get_object_or_404(WomenProduct, id=product_id)

    # 🧠 Smart category-based dynamic attributes
    extra_details = {}

    category = product.category.lower()

    # 👡 Footwear
    if category == "footwear":
        extra_details = {
            "UK Size": getattr(product, 'uk_size', 'Available in all sizes'),
            "Material": getattr(product, 'material', 'High-quality leather / synthetic'),
            "Color": getattr(product, 'color', 'Various shades'),
            "Occasion": getattr(product, 'occasion', 'Casual / Party / Daily Wear'),
        }

    # 👚 Tops / Kurtis


    # 🧵 Saree
    elif category == "sarees":
        extra_details = {
            "Fabric": getattr(product, 'fabric', 'Silk / Cotton / Georgette'),
            "Color": getattr(product, 'color', 'Multiple color options'),
            "Work Type": getattr(product, 'work_type', 'Embroidery / Printed / Handwoven'),
            "Border Type": getattr(product, 'border_type', 'Zari / Plain / Lace'),
            "Blouse Included": getattr(product, 'blouse', 'Yes'),
            "Occasion": getattr(product, 'occasion', 'Wedding / Festive / Daily'),
        }

    # 💍 Accessories
    elif category in ["accessory", "accessories", "jewellery", "bag", "handbag", "scarf"]:
        extra_details = {
            "Material": getattr(product, 'material', 'Metal / Fabric / Leather'),
            "Color": getattr(product, 'color', 'Various shades available'),
            "Brand": getattr(product, 'brand', 'Local / Branded'),
            "Occasion": getattr(product, 'occasion', 'Casual / Party / Traditional'),
            "Care Instructions": getattr(product, 'care', 'Clean with dry cloth only'),
        }

    # 🧥 Default fallback
    else:
        extra_details = {
            "Material": getattr(product, 'material', 'High-quality fabric'),
            "Color": getattr(product, 'color', 'Assorted'),
            "Occasion": getattr(product, 'occasion', 'Everyday wear'),
        }
    related_products = WomenProduct.objects.order_by('-id')[:5]

    context = {
        'product': product,
        'extra_details': extra_details,
        'related_products': related_products,
    }

    return render(request, 'women_product_detail.html', context)


from django.shortcuts import render, get_object_or_404
from store.models import ElectronicProduct

def electronic_product_detail(request, product_id):
    product = get_object_or_404(ElectronicProduct, id=product_id)

    extra_details = {}
    category = product.category.lower()

    # 📱 Mobile Phones
    if "mobile" in category or "smartphone" in category:
        extra_details = {
            "Brand": getattr(product, 'brand', 'Various Brands'),
            "Model": getattr(product, 'model', 'Latest Model'),
            "RAM": getattr(product, 'ram', '4GB / 6GB / 8GB'),
            "Storage": getattr(product, 'storage', '64GB / 128GB / 256GB'),
            "Battery": getattr(product, 'battery', '4000mAh / 5000mAh'),
            "Camera": getattr(product, 'camera', '48MP / 64MP / 108MP'),
            "Warranty": getattr(product, 'warranty', '1 Year Manufacturer Warranty'),
        }

    # 💻 Laptops / Desktops
    elif "laptop" in category or "desktop" in category:
        extra_details = {
            "Processor": getattr(product, 'processor', 'Intel i5 / i7 or AMD Ryzen'),
            "RAM": getattr(product, 'ram', '8GB / 16GB DDR4'),
            "Storage": getattr(product, 'storage', '512GB SSD / 1TB HDD'),
            "Graphics": getattr(product, 'graphics', 'Integrated / NVIDIA / AMD'),
            "Display": getattr(product, 'display', 'Full HD / 4K'),
            "Warranty": getattr(product, 'warranty', '1 Year Warranty'),
        }

    # 🎧 Accessories (Earphones, Speakers, etc.)
    elif "accessory" in category or "speaker" in category or "headphone" in category:
        extra_details = {
            "Connectivity": getattr(product, 'connectivity', 'Bluetooth / Wired'),
            "Battery Life": getattr(product, 'battery_life', 'Up to 20 hours'),
            "Brand": getattr(product, 'brand', 'Premium Quality'),
            "Warranty": getattr(product, 'warranty', '6 Months / 1 Year'),
            "Color": getattr(product, 'color', 'Multiple color options'),
        }

    # ⚙️ Default Fallback
    else:
        extra_details = {
            "Brand": getattr(product, 'brand', 'Trusted Brand'),
            "Color": getattr(product, 'color', 'Standard Colors'),
            "Warranty": getattr(product, 'warranty', '1 Year Warranty'),
        }

    related_products = ElectronicProduct.objects.order_by('-id')[:5]

    context = {
        'product': product,
        'extra_details': extra_details,
        'related_products': related_products,
    }

    return render(request, 'electronic_product_detail.html', context)




from django.shortcuts import render, get_object_or_404
from store.models import ToyProduct

def toy_product_detail(request, product_id):
    product = get_object_or_404(ToyProduct, id=product_id)

    extra_details = {}
    category = product.category.lower()

    # 🧩 Educational Toys
    if "educational" in category or "learning" in category:
        extra_details = {
            "Age Group": getattr(product, 'age_group', '3+ years'),
            "Material": getattr(product, 'material', 'Non-toxic Plastic / Wood'),
            "Skills Developed": getattr(product, 'skills', 'Motor Skills / Logical Thinking'),
            "Color": getattr(product, 'color', 'Multi-color'),
            "Safety": getattr(product, 'safety', 'BIS Certified / Child Safe'),
        }

    # 🚗 Cars, Robots, Action Toys
    elif "car" in category or "robot" in category or "action" in category:
        extra_details = {
            "Material": getattr(product, 'material', 'High-Quality Plastic'),
            "Battery Operated": getattr(product, 'battery_operated', 'Yes'),
            "Remote Control": getattr(product, 'remote_control', 'Included' if hasattr(product, 'remote_control') else 'No'),
            "Color": getattr(product, 'color', 'Multiple Options'),
            "Warranty": getattr(product, 'warranty', '6 Months'),
        }

    # 🧸 Soft Toys / Dolls
    elif "soft" in category or "doll" in category or "plush" in category:
        extra_details = {
            "Material": getattr(product, 'material', 'Soft Cotton / Plush'),
            "Color": getattr(product, 'color', 'Various colors available'),
            "Washable": getattr(product, 'washable', 'Yes'),
            "Age Group": getattr(product, 'age_group', '1+ years'),
        }

    # ⚙️ Default Fallback
    else:
        extra_details = {
            "Material": getattr(product, 'material', 'High-quality materials'),
            "Color": getattr(product, 'color', 'Multicolor'),
            "Recommended Age": getattr(product, 'age_group', '3+ years'),
        }

    related_products = ToyProduct.objects.order_by('-id')[:5]

    context = {
        'product': product,
        'extra_details': extra_details,
        'related_products': related_products,
    }

    return render(request, 'toy_product_detail.html', context)




@login_required
def buy_now(request, product_type, product_id):
    """Direct purchase from product detail page"""
    product = None
    if product_type == 'women':
        product = WomenProduct.objects.filter(id=product_id).first()
    elif product_type == 'electronic':
        product = ElectronicProduct.objects.filter(id=product_id).first()
    elif product_type == 'toy':
        product = ToyProduct.objects.filter(id=product_id).first()

    if not product:
        messages.error(request, "Product not found.")
        return redirect('home')

    # Extract size/color/fabric from form
    size = request.POST.get('size')
    color = request.POST.get('color')
    fabric = request.POST.get('fabric')

    # Temporarily store product info in session
    request.session['buy_now'] = {
        'product_type': product_type,
        'product_id': product.id,
        'size': size,
        'color': color,
        'fabric': fabric,
        'price': float(product.price),
    }

    return redirect('checkout')


