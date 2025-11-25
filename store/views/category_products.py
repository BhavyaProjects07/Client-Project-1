# views/category_products.py

from django.shortcuts import redirect, get_object_or_404
from store.models import Category  # your dynamic category model

def category_products(request, slug):
    """
    Redirects user to home page while pointing to the category block.
    This avoids needing category_products.html.
    """
    category = get_object_or_404(Category, slug=slug)

    # Redirect to home with category anchor
    return redirect(f"/#category-{category.slug}")
