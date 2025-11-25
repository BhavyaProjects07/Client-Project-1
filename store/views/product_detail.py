# views/product_detail.py
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Avg, Q, Prefetch
from django.contrib import messages

# Dynamic Product System imports
from store.models import (
    Product,
    ProductImage,
    ProductVariant,
    Category,
    Review,
)

# -----------------------------------------
# UNIVERSAL PRODUCT DETAIL VIEW (DYNAMIC)
# -----------------------------------------
def product_detail(request, product_id, slug=None):
    """
    Works for ANY product.
    Supports:
    - product variants
    - multiple images
    - reviews
    - similar products
    - SEO-friendly slug
    """
    # Fetch product + prefetch related stuff
    product = (
        Product.objects
        .select_related("category", "product_type")
        .prefetch_related(
            Prefetch("images", queryset=ProductImage.objects.all()),
            Prefetch("variants", queryset=ProductVariant.objects.all()),
        )
        .filter(id=product_id)
        .first()
    )

    if not product:
        return render(request, "404.html", status=404)

    # Slug mismatch → redirect to SEO-correct URL
    if slug and product.slug and slug != product.slug:
        return redirect("product_detail", product_id=product.id, slug=product.slug)

    # Main image
    primary_image = product.get_primary_image_url()

    # All images (except primary)
    gallery_images = product.images.all() if hasattr(product, "images") else []

    # Variants — size, color, etc.
    variants = product.variants.all() if hasattr(product, "variants") else []

    # Reviews for this product
    reviews = Review.objects.filter(product_id=product.id).order_by("-created_at")

    avg_rating = reviews.aggregate(r=Avg("rating"))["r"] or 0
    avg_rating = round(avg_rating, 1)

    # Similar products in same category
    similar_products_qs = (
        Product.objects
        .filter(category=product.category)
        .exclude(id=product.id)
        .select_related("category")
        .prefetch_related("images")
        .order_by("-id")[:12]
    )

    similar_products = []
    for p in similar_products_qs:
        similar_products.append({
            "id": p.id,
            "slug": p.slug,
            "name": p.name,
            "price": p.price,
            "image": p.get_primary_image_url(),
        })

    # User Wishlist check
    is_in_wishlist = False
    if request.user.is_authenticated:
        from store.models import WishlistItem
        is_in_wishlist = WishlistItem.objects.filter(
            user=request.user,
            product=product
        ).exists()


    context = {
        "product": product,
        "primary_image": primary_image,
        "gallery_images": gallery_images,
        "variants": variants,
        "reviews": reviews,
        "avg_rating": avg_rating,
        "similar_products": similar_products,
        "is_in_wishlist": is_in_wishlist,
    }

    return render(request, "product_detail.html", context)
