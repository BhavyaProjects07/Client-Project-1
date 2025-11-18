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
otp_storage = {}  # Temporary OTP storage

# ======================================================
# HOME VIEW
# ======================================================

from django.db.models import Avg
from store.models import WomenProduct, ElectronicProduct, ToyProduct, Review, WishlistItem
from django.db.models import Avg
from django.shortcuts import render
from store.models import WomenProduct, ElectronicProduct, ToyProduct, Review, WishlistItem,BusinessNameAndLogo

def home(request):
    wishlist_count = WishlistItem.objects.filter(user=request.user).count() if request.user.is_authenticated else 0

    # -----------------------------
    # EXISTING QUERIES
    # -----------------------------
    query = request.GET.get('q')
    category = request.GET.get('category')
    product_type = request.GET.get('type', 'women')

    query_electronic = request.GET.get('q_electronic')
    query_toy = request.GET.get('q_toy')

    # -----------------------------
    # MODEL MAP
    # -----------------------------
    model_map = {
        'women': WomenProduct,
        'electronic': ElectronicProduct,
        'toy': ToyProduct,
    }

    ProductModel = model_map.get(product_type, WomenProduct)

    # -----------------------------
    # PRODUCT FETCH
    # -----------------------------
    women_products = WomenProduct.objects.all()
    electronics_products = ElectronicProduct.objects.all()
    toys_products = ToyProduct.objects.all()
    business_info = BusinessNameAndLogo.objects.first()


    # Attach product_type to each product
    for p in women_products:
        p.product_type = 'women'
    for p in electronics_products:
        p.product_type = 'electronic'
    for p in toys_products:
        p.product_type = 'toy'

    # ACTIVE SECTION PRODUCTS (women by default)
    products = ProductModel.objects.all()

# -----------------------------------
# WOMEN SEARCH (Advanced Word Search)
# -----------------------------------
    no_results_women = False

    if query:
        search_words = query.split()
        for word in search_words:
            products = products.filter(name__icontains=word)

        if not products.exists():
            no_results_women = True

    # CATEGORY FILTER
    if category and category != 'all':
        products = products.filter(category__iexact=category)
        if not products.exists():
            no_results_women = True


    # -----------------------------------
    # ELECTRONICS SEARCH (Advanced Word Search)
    # -----------------------------------
    no_results_electronics = False

    if query_electronic:
        search_words = query_electronic.split()
        for word in search_words:
            electronics_products = electronics_products.filter(name__icontains=word)

        if not electronics_products.exists():
            no_results_electronics = True


    # -----------------------------------
    # TOYS SEARCH (Advanced Word Search)
    # -----------------------------------
    no_results_toys = False

    if query_toy:
        search_words = query_toy.split()
        for word in search_words:
            toys_products = toys_products.filter(name__icontains=word)

        if not toys_products.exists():
            no_results_toys = True


    # -----------------------------
    # RATING CALCULATIONS
    # -----------------------------
    for product in products:
        reviews = Review.objects.filter(product_type=product_type, product_id=product.id)
        product.average_rating = reviews.aggregate(avg=Avg('rating'))['avg'] or 0
        product.total_reviews = reviews.count()

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

    # -----------------------------
    # CATEGORY LIST (Women)
    # -----------------------------
    categories = [choice[0] for choice in ProductModel.CATEGORY_CHOICES]
    categories.insert(0, 'all')

    # -----------------------------
    # RETURN
    # -----------------------------
    return render(request, 'home.html', {
        'products': products,
        'women_products': women_products,
        'electronics_products': electronics_products,
        'toys_products': toys_products,

        'no_results_women': no_results_women,
        'no_results_electronics': no_results_electronics,
        'no_results_toys': no_results_toys,

        'active_category': category if category else 'all',
        'categories': categories,
        'wishlist_count': wishlist_count,
        'product_type': product_type,
        'business_info': business_info,
    })