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
otp_storage = {}



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
    return redirect('view_cart')


@login_required
def view_cart(request):
    if not request.user.is_authenticated:
        messages.warning(request, "⚠️ Please login to view your cart.")
        return redirect('home')
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