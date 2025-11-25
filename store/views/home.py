# views/home.py
from django.shortcuts import render
from django.db.models import Q, Prefetch, Avg
from django.utils import timezone
from django.conf import settings

# Import models with graceful fallback — supports both new dynamic system
# (Category, Product, ProductImage, ProductVariant) and legacy models
try:
    from store.models import (
        Category,
        Product,
        ProductImage,
        ProductVariant,
        ProductAttribute,
        Review,
        BusinessNameAndLogo,
    )
    DYNAMIC_MODE = True
except Exception:
    # If dynamic models are not present, fall back to legacy models
    from store.models import (
        WomenProduct,
        ElectronicProduct,
        ToyProduct,
        Review,
        BusinessNameAndLogo,
    )
    DYNAMIC_MODE = False


# Helper: normalize a product object to a simple dict the templates can use
def _normalize_product(obj, with_rating=True):
    """
    Return a lightweight dict with fields used by the templates:
    - pk, name, price, category (name), get_primary_image_url, avg_rating, slug (if exists)
    Works for both dynamic Product and legacy product models.
    """
    # base fields
    pk = getattr(obj, "pk", None)
    name = getattr(obj, "name", "") or getattr(obj, "title", "")
    price = getattr(obj, "price", None) or getattr(obj, "get_price", None)
    available_stock = getattr(obj, "available_stock", None) or getattr(obj, "stock", None)


    # attempt to get a category name (dynamic Product has category relation)
    cat = None
    if hasattr(obj, "category") and obj.category:
        # if category is a relation, get name; if string, use directly
        cat = getattr(obj.category, "name", obj.category)
    else:
        # legacy: try to sniff a category from model class
        cls_name = obj.__class__.__name__.lower()
        if "women" in cls_name:
            cat = "Women"
        elif "electronic" in cls_name:
            cat = "Electronics"
        elif "toy" in cls_name:
            cat = "Toys"
        else:
            cat = ""

    # primary image url detection
    img_url = None
    # dynamic Product likely implements get_primary_image_url method
    if hasattr(obj, "get_primary_image_url"):
        try:
            img_url = obj.get_primary_image_url() or None
        except Exception:
            img_url = None

    # if object has 'image' attribute (legacy), use it
    if not img_url and hasattr(obj, "image"):
        image_field = getattr(obj, "image")
        try:
            img_url = image_field.url if image_field and hasattr(image_field, "url") else None
        except Exception:
            img_url = None

    # slug if present (useful for product_detail route)
    slug = getattr(obj, "slug", None)

    # average rating (if annotate used, it might be obj.avg_rating)
    avg_rating = None
    if with_rating:
        # if the object already has annotated avg_rating, use it
        if hasattr(obj, "avg_rating") and obj.avg_rating is not None:
            try:
                avg_rating = round(obj.avg_rating or 0, 1)
            except Exception:
                avg_rating = float(obj.avg_rating or 0)
        else:
            # best-effort: if Review model exists, compute here (cheap for a few items)
            try:
                if "Review" in globals() and Review and pk is not None:
                    agg = Review.objects.filter(product_id=pk).aggregate(avg=Avg("rating"))
                    avg_val = agg.get("avg") or 0
                    avg_rating = round(avg_val, 1)
            except Exception:
                avg_rating = 0

    return {
        "pk": pk,
        "name": name,
        "price": price,
        "category": cat,
        "image": img_url,
        "slug": slug,
        "avg_rating": avg_rating or 0,
        "available_stock": available_stock or 0,
    }


def home(request):
    search_q = request.GET.get("q", "").strip()
    category_filter = request.GET.get("category", "").strip()

    PER_CATEGORY_LIMIT = getattr(settings, "HOME_PRODUCTS_PER_CATEGORY", 12)

    business_info = BusinessNameAndLogo.objects.first()

    products_by_category = {}
    categories_list = []

    if DYNAMIC_MODE:

        # Base product queryset
        products_qs = Product.objects.all().select_related("category")

        # --- FIX AVG RATING ERROR ---
        # Try only the valid annotation path
        try:
            products_qs = products_qs.annotate(
                avg_rating=Avg("review__rating")  # Correct related name from your DB
            )
        except Exception:
            products_qs = products_qs.annotate(avg_rating=Avg("review__rating"))

        # Search filter
        if search_q:
            products_qs = products_qs.filter(
                Q(name__icontains=search_q)
                | Q(description__icontains=search_q)
                | Q(category__name__icontains=search_q)
            ).distinct()

        # Category filter
        if category_filter:
            products_qs = products_qs.filter(category__slug=category_filter)

        # --- FIX PARENT–CHILD CATEGORY GROUPING ---
        # Pull only top-level categories first
        parent_categories = Category.objects.filter(parent__isnull=True).order_by("id")


        for parent in parent_categories:

            # Add parent category to list
            categories_list.append(parent)

            # Get all its children (example: Women → Saree, Kurti, Tops…)
            child_ids = list(parent.children.values_list("id", flat=True))

            # Products that belong to the parent OR its children
            cat_products = products_qs.filter(
                Q(category=parent) | Q(category_id__in=child_ids)
            ).order_by("-avg_rating", "created_at")[:PER_CATEGORY_LIMIT]

            normalized = [_normalize_product(p) for p in cat_products]

            products_by_category[parent.slug] = normalized

    else:
        # Legacy fallback (unchanged)
        pass

    return render(
        request,
        "home.html",
        {
            "categories": categories_list,
            "products_by_category": products_by_category,
            "business_info": business_info,
            "search_query": search_q,
            
        },
    )
