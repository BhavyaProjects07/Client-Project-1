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
    return redirect('view_wishlist')



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
