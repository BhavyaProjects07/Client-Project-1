from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import login, get_user_model,logout
from store.models import CustomUser, Product,OrderItem,Order
import firebase_admin
from firebase_admin import auth, credentials
import random
from django.db.models import Avg, Count
# Initialize Firebase
cred = credentials.Certificate("C:/Users/Dell/OneDrive/Desktop/Whole python/Django/Devki_Mart/Firebase Key/smssend-766b5-firebase-adminsdk-fbsvc-c784cb746c.json")
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

User = get_user_model()
otp_storage = {}  # Temporary OTP store

def home(request):
    wishlist_count = WishlistItem.objects.filter(user=request.user).count() if request.user.is_authenticated else 0
    query = request.GET.get('q')
    category = request.GET.get('category')

    products = Product.objects.annotate(
        average_rating=Avg('reviews__rating'),
        total_reviews=Count('reviews')
    )

    if query:
        products = products.filter(name__icontains=query)

    if category and category != 'all':
        products = products.filter(category__iexact=category)

    categories = ['all', 'fruits', 'vegetables', 'dairy', 'bakery', 'beverages', 'spices']

    return render(request, 'home.html', {
        'products': products,
        'active_category': category if category else 'all',
        'categories': categories,
        'wishlist_count': wishlist_count,
    })

def request_otp_view(request):
    if request.method == "POST":
        username = request.POST['username']
        email = request.POST['email']
        print(f"[DEBUG] Received Username: {username}, Email: {email}")

        try:
            user = User.objects.get(username=username, email=email)
            # ✅ User exists — Log them in directly
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")
            return redirect('/')
        except User.DoesNotExist:
            # ✅ New user — Send OTP
            otp = str(random.randint(100000, 999999))
            otp_storage[email] = {
                "otp": otp,
                "username": username
            }
            print(f"[DEBUG] OTP Generated: {otp} for Email: {email}")

            send_mail(
                subject="Your DevkiMart OTP Verification Code",
                message=f"Hi {username},\n\nYour OTP code is: {otp}",
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[email],
            )

            request.session['pending_email'] = email
            messages.success(request, f"OTP sent to {email}")
            return redirect('verify_otp')

    return redirect('/')

def verify_otp_view(request):
    if request.method == "POST":
        email = request.session.get('pending_email')
        entered_otp = request.POST.get('otp')

        # Debugging logs
        print(f"[DEBUG] Email from session: {email}")
        print(f"[DEBUG] Entered OTP: {entered_otp}")
        print(f"[DEBUG] OTP Storage: {otp_storage}")

        # Check if the OTP is valid
        data = otp_storage.get(email)
        if data:
            print(f"[DEBUG] Stored OTP: {data['otp']}")
        if data and data['otp'] == entered_otp:
            # Create or get the user
            username = data['username']
            user, created = CustomUser.objects.get_or_create(
                email=email,
                defaults={'username': username}
            )
            print(f"[DEBUG] OTP Matched for Email: {email}")
            # Log in the user
            login(request, user)
            messages.success(request, f"Welcome, {user.username}!")
            return redirect('/')  # Redirect to the home page
        else:
            messages.error(request, "Invalid or expired OTP.")
            return redirect('verify_otp')  # Redirect back to the OTP page

    return render(request, 'verify_otp.html')

# ✅ Logout View
def logout_view(request):
    logout(request)
    return redirect("/")




# cart system

from .models import CartItem, Product
from django.contrib.auth.decorators import login_required

@login_required
def add_to_cart(request, product_id):
    product = Product.objects.get(id=product_id)

    # Check if the product is already in the cart
    if CartItem.objects.filter(user=request.user, product=product).exists():
        messages.info(request, "This item is already in your cart.")
    else:
        CartItem.objects.create(user=request.user, product=product)
        messages.success(request, "Item added to cart.")

    # Redirect back to the wishlist page if the request came from there
    referer = request.META.get('HTTP_REFERER', '/')
    if 'wishlist' in referer:
        return redirect('view_wishlist')  # Redirect to the wishlist page
    return redirect('/')


@login_required
def view_cart(request):
    category = request.GET.get('category')
    categories = ['all', 'fruits', 'vegetables', 'dairy', 'bakery', 'beverages', 'spices']

    products = Product.objects.filter(category=category) if category else Product.objects.all()
    items = CartItem.objects.filter(user=request.user)
    total = sum(item.subtotal() for item in items)

    context = {
        'products': products,
        'items': items,
        'total': total,
        'active_category': category if category else 'all',
        'categories': categories,
    }
    return render(request, 'cart.html', context)


@login_required
def remove_from_cart(request, item_id):
    CartItem.objects.filter(id=item_id, user=request.user).delete()
    return redirect('view_cart')



from django.views.decorators.http import require_POST
from django.http import JsonResponse
import json
from .models import CartItem

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

        return JsonResponse({
            'success': True,
            'item_id': item_id,
            'quantity': cart_item.quantity
        })

    except CartItem.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Item not found'}, status=404)




from .models import WishlistItem
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404


def add_to_wishlist(request, product_id):
    product = Product.objects.get(id=product_id)

    if not request.user.is_authenticated:
        messages.error(request, "Please log in to add in the wishlist.")
        return redirect('/')

    # Check if already added
    if WishlistItem.objects.filter(user=request.user, product=product).exists():
        messages.info(request, "Item is already in your wishlist.")
    else:
        WishlistItem.objects.create(user=request.user, product=product)
        messages.success(request, "Item added to wishlist.")

    return redirect('/')

@login_required
def view_wishlist(request):
    wishlist_count = WishlistItem.objects.filter(user=request.user).count() if request.user.is_authenticated else 0
    items = WishlistItem.objects.filter(user=request.user)
    return render(request, 'wishlist.html', {'items': items,'wishlist_count': wishlist_count})

@login_required
def remove_from_wishlist(request, item_id):
    WishlistItem.objects.filter(id=item_id, user=request.user).delete()
    return redirect('view_wishlist')


def message_view(request):
    if not request.user.is_authenticated:
        messages.error(request, "Please log in to add in the wishlist.")
    else:
        messages.success(request, "Item added to wishlist...")
    return redirect('/')




# checkout system

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.contrib import messages
from django.conf import settings
from .models import CartItem, Order, OrderItem

@login_required
def checkout_view(request):
    items = CartItem.objects.filter(user=request.user)
    total = sum(item.subtotal() for item in items)

    if not items:
        messages.warning(request, "Your cart is empty.")
        return redirect('home')

    if request.method == "POST":
        request.session['checkout_info'] = {
            'full_name': request.POST['full_name'],
            'address': request.POST['address'],
            'city': request.POST['city'],
            'postal_code': request.POST['postal_code'],
            'phone_number': request.POST['phone_number'],
            'total': float(total)  # ✅ Convert Decimal to float here
        }
        return redirect('payment')

    return render(request, 'checkout.html', {'items': items, 'total': total})


@login_required
def payment_view(request):
    checkout_info = request.session.get('checkout_info')
    if not checkout_info:
        messages.error(request, "Shipping information missing.")
        return redirect('checkout')

    items = CartItem.objects.filter(user=request.user)
    total = checkout_info['total']

    if request.method == "POST":
        payment_method = request.POST.get('payment_method')

        # Allow only COD as the payment method
        if payment_method != 'cod':
            messages.error(request, "Invalid payment method. Only Cash on Delivery (COD) is available.")
            return redirect('payment')  # Redirect back to the payment page

        # Create the order for COD
        order = Order.objects.create(
            user=request.user,
            full_name=checkout_info['full_name'],
            address=checkout_info['address'],
            city=checkout_info['city'],
            postal_code=checkout_info['postal_code'],
            phone_number=checkout_info['phone_number'],
            paid=False,
            payment_method = payment_method  # Set to False for COD
        )

        # Create order items
        for item in items:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price=item.product.price
            )

        # Clear the cart
        items.delete()

        # Send confirmation email to the user
        send_mail(
            "Devki Mart - Order Confirmation",
            f"""Hi {order.full_name},

Your order has been placed successfully!

Order Details:
Name: {order.full_name}
Total: ₹{float(total)}

Address: {order.address}, {order.city}, {order.postal_code}
Phone: {order.phone_number}

Thank you for shopping with Devki Mart!
""",
            settings.EMAIL_HOST_USER,
            [request.user.email]
        )

        # Send notification email to the admin
        send_mail(
            f"🛒 New Order Received - Order #{order.id}",
            f"""New order placed by {request.user.username}.

Order Details:
Name: {order.full_name}
Email: {request.user.email}
Total: ₹{total}
Address: {order.address}, {order.city}, {order.postal_code}
Phone: {order.phone_number}
Order Date: {order.created_at.strftime('%d-%m-%Y %H:%M')}
Payment Method: {order.payment_method}
""",
            settings.EMAIL_HOST_USER,
            ['laptopuse01824x@gmail.com']  # Admin email
        )

        # Success message and redirect
        messages.success(request, "Order placed successfully! Confirmation sent to your email.")
        return redirect('order_success')

    return render(request, 'payment.html', {'total': total})
def order_success_view(request):
    return render(request, 'order_success.html')



def my_orders_view(request):
    if not request.user.is_authenticated:
        messages.error(request, "⚠️ Please log in to view your orders.")
        return redirect('home')  # or redirect to your login page

    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'my_orders.html', {'orders': orders})



from django.contrib.auth.decorators import user_passes_test
# admin panel dashboard
# ✅ Check if the user is staff/admin
def is_admin(user):
    return user.is_authenticated and user.is_staff


# ✅ Admin Dashboard View
@user_passes_test(is_admin)
def admin_dashboard_view(request):
    orders = Order.objects.all().order_by('-created_at')[:10]  # Last 10 orders
    total_orders = Order.objects.count()
    pending_orders = Order.objects.filter(order_status='Pending').count()
    delivered_orders = Order.objects.filter(order_status='Delivered').count()
    total_users = CustomUser.objects.count()

    return render(request, 'dashboard.html', {
        'orders': orders,
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'delivered_orders': delivered_orders,
        'total_users': total_users,
    })

# ✅ Update Order Status (POST only)
@user_passes_test(is_admin)
@require_POST
def update_order_status(request, order_id):
    order = Order.objects.get(id=order_id)
    new_status = request.POST.get('status')
    paid = request.POST.get('paid') == 'True'

    # Update order
    order.order_status = new_status
    order.paid = paid
    order.save()

    # Email templates by status
    status_messages = {
        "Shipped": f"Your order #{order.id} has been shipped. It's on the way! 🚚",
        "Delivered": f"Your order #{order.id} has been delivered successfully! 🎉"
    }

    if new_status in status_messages:
        send_mail(
            f"Order #{order.id} - {new_status}",
            f"Hello {order.full_name},\n\n{status_messages[new_status]}\n\nThanks,\nDevki Mart",
            settings.EMAIL_HOST_USER,
            [order.user.email]
        )

    messages.success(request, f"Order #{order.id} updated to {new_status}.")
    return redirect('admin_dashboard')


# ✅ Admin Order Detail View
@user_passes_test(is_admin)
def admin_order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'admin_order_detail.html', {'order': order})


def admin_order_detail(request, order_id):
    order = Order.objects.get(id=order_id)
    return render(request, 'order_detail.html', {'order': order})



@user_passes_test(is_admin)
@require_POST
def update_payment_status(request, order_id):
    paid_value = request.POST.get('paid')
    order = Order.objects.get(id=order_id)
    order.paid = True if paid_value == 'True' else False
    order.save()
    messages.success(request, f"Payment status for Order #{order.id} updated to {'Paid' if order.paid else 'Not Paid'}.")
    return redirect('admin_dashboard')


#Track Order View
@login_required
def track_order_view(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    tracking_steps = [
        {"label": "Order Placed", "completed": True},
        {"label": "Shipped", "completed": order.order_status in ['Shipped', 'Delivered']},
        {"label": "Out for Delivery", "completed": False},  # Optional step
        {"label": "Delivered", "completed": order.order_status == 'Delivered'},
    ]
    return render(request, 'track_order.html', {
        'order': order,
        'steps': tracking_steps
    })



# Review System
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Product, Order, OrderItem, Review
from .forms import ReviewForm


@login_required
def submit_review(request, order_id, product_id):
    order = get_object_or_404(Order, id=order_id, user=request.user, order_status='Delivered')
    product = get_object_or_404(Product, id=product_id)

    # Check if review already exists for this product by this user
    try:
        review = Review.objects.get(user=request.user, product=product)
        created = False
    except Review.DoesNotExist:
        review = None
        created = True

    if request.method == 'POST':
        form = ReviewForm(request.POST, instance=review)
        if form.is_valid():
            new_review = form.save(commit=False)
            new_review.user = request.user
            new_review.product = product
            new_review.save()
            if created:
                messages.success(request, "Thank you! Your review has been submitted.")
            else:
                messages.info(request, "Your review has been updated.")
            return redirect('my_orders')
    else:
        form = ReviewForm(instance=review)

    return render(request, 'submit_review.html', {
        'form': form,
        'product': product,
        'order': order,
    })


from django.shortcuts import render, get_object_or_404
from .models import Product, Review

def product_reviews_view(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    reviews = Review.objects.filter(product=product).select_related('user').order_by('-created_at')
    user_order = Order.objects.filter(user=request.user, order_status="Delivered", items__product=product).first() if request.user.is_authenticated else None

    return render(request, 'product_reviews.html', {
        'product': product,
        'reviews': reviews,
        'order': user_order,
    })
