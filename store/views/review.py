from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count
from django.http import Http404

from store.models import Product, ProductVariant, Order, Review
from store.forms import ReviewForm


# ======================================================
# SUBMIT REVIEW (Dynamic Product System)
# ======================================================
@login_required
def submit_review(request, order_id, product_id):
    """
    User can submit a review ONLY IF:
    - The order belongs to them
    - The order is Delivered
    - The product exists in that order
    """

    # 1️⃣ Validate order
    order = get_object_or_404(
        Order,
        id=order_id,
        user=request.user,
        order_status="Delivered"
    )

    # 2️⃣ Validate product
    product = get_object_or_404(Product, id=product_id)

    # 3️⃣ Check if the product exists in the order
    order_product_ids = order.items.values_list("product_id", flat=True)
    if product_id not in order_product_ids:
        raise Http404("This product is not part of your delivered order.")

    # 4️⃣ Check if review already exists
    review = Review.objects.filter(
        user=request.user,
        product=product,
        order=order
    ).first()

    is_new_review = review is None

    if request.method == "POST":
        form = ReviewForm(request.POST, instance=review)
        if form.is_valid():
            review_obj = form.save(commit=False)
            review_obj.user = request.user
            review_obj.product = product
            review_obj.order = order
            review_obj.save()

            messages.success(
                request,
                "Your review has been submitted." if is_new_review else "Your review has been updated."
            )
            return redirect("my_orders")
    else:
        form = ReviewForm(instance=review)

    return render(request, "submit_review.html", {
        "form": form,
        "order": order,
        "product": product,
    })


# ======================================================
# PRODUCT REVIEWS PAGE
# ======================================================
def product_reviews_view(request, product_id):
    """
    Shows all reviews for a given product.
    """
    product = get_object_or_404(Product, id=product_id)

    reviews = Review.objects.filter(product=product).select_related("user").order_by("-created_at")

    # Product rating summary
    rating_summary = reviews.aggregate(
        avg_rating=Avg("rating"),
        total_reviews=Count("id")
    )

    return render(request, "product_reviews.html", {
        "product": product,
        "reviews": reviews,
        "rating_summary": rating_summary,
    })
