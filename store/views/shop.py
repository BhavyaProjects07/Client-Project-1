from django.shortcuts import render
from django.core.paginator import Paginator
from django.db.models import Q, Avg, Min, Max
from store.models import Product, Category


def shop_view(request):
    products = (
        Product.objects
        .select_related("category")
        .prefetch_related("images")
        .annotate(avg_rating=Avg("reviews__rating"))
        .order_by("-created_at")
    )

    # -------------------------
    # Filters
    # -------------------------
    search_q = request.GET.get("q", "").strip()
    category_slug = request.GET.get("category")
    min_price = request.GET.get("min_price")
    max_price = request.GET.get("max_price")

    if search_q:
        products = products.filter(
            Q(name__icontains=search_q) |
            Q(description__icontains=search_q)
        )

    if category_slug:
        products = products.filter(category__slug=category_slug)

    if min_price:
        products = products.filter(price__gte=min_price)

    if max_price:
        products = products.filter(price__lte=max_price)

    # -------------------------
    # Pagination
    # -------------------------
    paginator = Paginator(products, 12)  # 12 per page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Sidebar Data
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