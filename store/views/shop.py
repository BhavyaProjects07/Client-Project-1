from django.shortcuts import render
from django.core.paginator import Paginator
from django.db.models import Q, Avg, Min, Max
from store.models import Product, Category
import re


def shop_view(request):

    products = (
        Product.objects
        .select_related("category")
        .prefetch_related("images")
        .annotate(avg_rating=Avg("reviews__rating"))
        .order_by("-created_at")
    )

    # -------------------------
    # GET PARAMETERS
    # -------------------------
    search_q = request.GET.get("q", "").strip()
    category_slug = request.GET.get("category")
    min_price = request.GET.get("min_price")
    max_price = request.GET.get("max_price")

    # -------------------------
    # SMART SEARCH LOGIC
    # -------------------------
    # -------------------------
# SMART SEARCH LOGIC (STRICT AND MATCH)
# -------------------------
    if search_q:
        query = search_q.lower()

        # -------- Price Extraction --------
        under_match = re.search(r'under\s+(\d+)', query)
        if under_match:
            max_price = under_match.group(1)

        above_match = re.search(r'above\s+(\d+)', query)
        if above_match:
            min_price = above_match.group(1)

        between_match = re.search(r'between\s+(\d+)\s+and\s+(\d+)', query)
        if between_match:
            min_price = between_match.group(1)
            max_price = between_match.group(2)

        # Remove stop words
        stop_words = ["for", "the", "and", "with", "in", "on"]
        keywords = [
            word for word in re.findall(r'\w+', query)
            if word not in stop_words and not word.isdigit()
        ]

        # AND-based filtering
        for word in keywords:
            products = products.filter(
                Q(name__icontains=word) |
                Q(description__icontains=word) |
                Q(category__name__icontains=word)
            )

    # -------------------------
    # CATEGORY FILTER
    # -------------------------
    if category_slug:
        products = products.filter(category__slug=category_slug)

    # -------------------------
    # PRICE FILTER
    # -------------------------
    if min_price:
        try:
            products = products.filter(price__gte=float(min_price))
        except ValueError:
            pass

    if max_price:
        try:
            products = products.filter(price__lte=float(max_price))
        except ValueError:
            pass

    # -------------------------
    # PAGINATION
    # -------------------------
    paginator = Paginator(products, 12)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # -------------------------
    # SIDEBAR DATA
    # -------------------------
    categories = Category.objects.filter(parent__isnull=True)

    price_range = Product.objects.aggregate(
        min=Min("price"),
        max=Max("price")
    )

    context = {
        "page_obj": page_obj,
        "categories": categories,
        "search_query": search_q,
        "selected_category": category_slug,
        "min_price": min_price,
        "max_price": max_price,
        "price_range": price_range,
    }

    return render(request, "shop.html", context)