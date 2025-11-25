# store/views/wishlist.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from store.models import Product, WishlistItem


# ===================================================================
# ❤️ ADD TO WISHLIST
# ===================================================================
@login_required
def add_to_wishlist(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    exists = WishlistItem.objects.filter(
        user=request.user,
        product=product
    ).exists()

    if exists:
        messages.info(request, "This item is already in your wishlist.")
    else:
        WishlistItem.objects.create(
            user=request.user,
            product=product
        )
        messages.success(request, "Added to wishlist ❤️")

    return redirect("view_wishlist")


# ===================================================================
# ❤️ VIEW WISHLIST
# ===================================================================
@login_required
def view_wishlist(request):
    items = WishlistItem.objects.filter(user=request.user).select_related("product")
    count = items.count()

    return render(request, "wishlist.html", {
        "items": items,
        "wishlist_count": count,
    })


# ===================================================================
# ❌ REMOVE FROM WISHLIST
# ===================================================================
@login_required
def remove_from_wishlist(request, item_id):
    WishlistItem.objects.filter(id=item_id, user=request.user).delete()
    messages.success(request, "Removed from wishlist.")
    return redirect("view_wishlist")
