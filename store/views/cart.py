# store/views/cart.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.db import transaction
import json

from store.models import Product, CartItem , ProductVariant


# ===================================================================
# 🛒 ADD TO CART (Dynamic Product System)
# ===================================================================
@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    # Check if a variant was selected
    variant_id = request.POST.get("variant_id")
    variant = None

    if variant_id:
        variant = get_object_or_404(
            ProductVariant,
            id=variant_id,
            product=product
        )

    # Check if item already exists in cart
    existing = CartItem.objects.filter(
        user=request.user,
        product=product,
        variant=variant
    ).first()

    if existing:
        existing.quantity += 1
        existing.save()
        messages.success(request, "Quantity updated in your cart.")
    else:
        CartItem.objects.create(
            user=request.user,
            product=product,
            variant=variant,
            quantity=1
        )
        messages.success(request, "Item added to cart.")

    return redirect("view_cart")


# ===================================================================
# 🛒 VIEW CART
# ===================================================================
@login_required
def view_cart(request):
    items = CartItem.objects.filter(user=request.user).select_related("product")

    total = sum(item.total_price() for item in items)

    return render(request, "cart.html", {
        "items": items,
        "total": total,
    })


# ===================================================================
# ❌ REMOVE FROM CART
# ===================================================================
@login_required
def remove_from_cart(request, item_id):
    CartItem.objects.filter(id=item_id, user=request.user).delete()
    messages.success(request, "Item removed from cart.")
    return redirect("view_cart")


# ===================================================================
# 🔄 UPDATE QUANTITY (AJAX)
# ===================================================================
@require_POST
@login_required
def update_cart_quantity(request, item_id):
    """Increase/decrease quantity dynamically using AJAX"""

    try:
        data = json.loads(request.body)
        action = data.get("action")

        item = CartItem.objects.get(id=item_id, user=request.user)

        if action == "increase":
            item.quantity += 1
        elif action == "decrease":
            if item.quantity > 1:
                item.quantity -= 1

        item.save()

        return JsonResponse({
            "success": True,
            "item_id": item_id,
            "quantity": item.quantity,
            "item_total": item.total_price()
        })

    except CartItem.DoesNotExist:
        return JsonResponse({"success": False, "error": "Item not found."}, status=404)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)


# ===================================================================
# 🛍 BUY NOW (1-click Checkout)
# ===================================================================
@login_required
def buy_now(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    variant_id = request.POST.get("variant_id")
    variant = None

    if variant_id:
        variant = get_object_or_404(ProductVariant, id=variant_id, product=product)

    request.session["buy_now"] = {
        "product_id": product.id,
        "variant_id": variant.id if variant else None,
        "name": product.name,
        "price": float(variant.display_price() if variant else product.price),
    }

    return redirect("checkout")
