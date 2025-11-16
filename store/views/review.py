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
