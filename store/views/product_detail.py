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



from django.shortcuts import render, get_object_or_404
from store.models import WomenProduct  # Adjust model name as per your setup

def women_product_detail(request, product_id):
    product = get_object_or_404(WomenProduct, id=product_id)

    # 🧠 Smart category-based dynamic attributes
    extra_details = {}

    category = product.category.lower()

    # 👡 Footwear
    if category == "footwear":
        extra_details = {
            "UK Size": getattr(product, 'uk_size', 'Available in all sizes'),
            "Material": getattr(product, 'material', 'High-quality leather / synthetic'),
            "Color": getattr(product, 'color', 'Various shades'),
            "Occasion": getattr(product, 'occasion', 'Casual / Party / Daily Wear'),
        }

    # 👚 Tops / Kurtis


    # 🧵 Saree
    elif category == "sarees":
        extra_details = {
            "Fabric": getattr(product, 'fabric', 'Silk / Cotton / Georgette'),
            "Color": getattr(product, 'color', 'Multiple color options'),
            "Work Type": getattr(product, 'work_type', 'Embroidery / Printed / Handwoven'),
            "Border Type": getattr(product, 'border_type', 'Zari / Plain / Lace'),
            "Blouse Included": getattr(product, 'blouse', 'Yes'),
            "Occasion": getattr(product, 'occasion', 'Wedding / Festive / Daily'),
        }

    # 💍 Accessories
    elif category in ["accessory", "accessories", "jewellery", "bag", "handbag", "scarf"]:
        extra_details = {
            "Material": getattr(product, 'material', 'Metal / Fabric / Leather'),
            "Color": getattr(product, 'color', 'Various shades available'),
            "Brand": getattr(product, 'brand', 'Local / Branded'),
            "Occasion": getattr(product, 'occasion', 'Casual / Party / Traditional'),
            "Care Instructions": getattr(product, 'care', 'Clean with dry cloth only'),
        }

    # 🧥 Default fallback
    else:
        extra_details = {
            "Material": getattr(product, 'material', 'High-quality fabric'),
            "Color": getattr(product, 'color', 'Assorted'),
            "Occasion": getattr(product, 'occasion', 'Everyday wear'),
        }
    related_products = WomenProduct.objects.order_by('-id')[:5]

    context = {
        'product': product,
        'extra_details': extra_details,
        'related_products': related_products,
    }

    return render(request, 'women_product_detail.html', context)


from django.shortcuts import render, get_object_or_404
from store.models import ElectronicProduct

def electronic_product_detail(request, product_id):
    product = get_object_or_404(ElectronicProduct, id=product_id)

    extra_details = {}
    category = product.category.lower()

    # 📱 Mobile Phones
    if "mobile" in category or "smartphone" in category:
        extra_details = {
            "Brand": getattr(product, 'brand', 'Various Brands'),
            "Model": getattr(product, 'model', 'Latest Model'),
            "RAM": getattr(product, 'ram', '4GB / 6GB / 8GB'),
            "Storage": getattr(product, 'storage', '64GB / 128GB / 256GB'),
            "Battery": getattr(product, 'battery', '4000mAh / 5000mAh'),
            "Camera": getattr(product, 'camera', '48MP / 64MP / 108MP'),
            "Warranty": getattr(product, 'warranty', '1 Year Manufacturer Warranty'),
        }

    # 💻 Laptops / Desktops
    elif "laptop" in category or "desktop" in category:
        extra_details = {
            "Processor": getattr(product, 'processor', 'Intel i5 / i7 or AMD Ryzen'),
            "RAM": getattr(product, 'ram', '8GB / 16GB DDR4'),
            "Storage": getattr(product, 'storage', '512GB SSD / 1TB HDD'),
            "Graphics": getattr(product, 'graphics', 'Integrated / NVIDIA / AMD'),
            "Display": getattr(product, 'display', 'Full HD / 4K'),
            "Warranty": getattr(product, 'warranty', '1 Year Warranty'),
        }

    # 🎧 Accessories (Earphones, Speakers, etc.)
    elif "accessory" in category or "speaker" in category or "headphone" in category:
        extra_details = {
            "Connectivity": getattr(product, 'connectivity', 'Bluetooth / Wired'),
            "Battery Life": getattr(product, 'battery_life', 'Up to 20 hours'),
            "Brand": getattr(product, 'brand', 'Premium Quality'),
            "Warranty": getattr(product, 'warranty', '6 Months / 1 Year'),
            "Color": getattr(product, 'color', 'Multiple color options'),
        }

    # ⚙️ Default Fallback
    else:
        extra_details = {
            "Brand": getattr(product, 'brand', 'Trusted Brand'),
            "Color": getattr(product, 'color', 'Standard Colors'),
            "Warranty": getattr(product, 'warranty', '1 Year Warranty'),
        }

    related_products = ElectronicProduct.objects.order_by('-id')[:5]

    context = {
        'product': product,
        'extra_details': extra_details,
        'related_products': related_products,
    }

    return render(request, 'electronic_product_detail.html', context)




from django.shortcuts import render, get_object_or_404
from store.models import ToyProduct

def toy_product_detail(request, product_id):
    product = get_object_or_404(ToyProduct, id=product_id)

    extra_details = {}
    category = product.category.lower()

    # 🧩 Educational Toys
    if "educational" in category or "learning" in category:
        extra_details = {
            "Age Group": getattr(product, 'age_group', '3+ years'),
            "Material": getattr(product, 'material', 'Non-toxic Plastic / Wood'),
            "Skills Developed": getattr(product, 'skills', 'Motor Skills / Logical Thinking'),
            "Color": getattr(product, 'color', 'Multi-color'),
            "Safety": getattr(product, 'safety', 'BIS Certified / Child Safe'),
        }

    # 🚗 Cars, Robots, Action Toys
    elif "car" in category or "robot" in category or "action" in category:
        extra_details = {
            "Material": getattr(product, 'material', 'High-Quality Plastic'),
            "Battery Operated": getattr(product, 'battery_operated', 'Yes'),
            "Remote Control": getattr(product, 'remote_control', 'Included' if hasattr(product, 'remote_control') else 'No'),
            "Color": getattr(product, 'color', 'Multiple Options'),
            "Warranty": getattr(product, 'warranty', '6 Months'),
        }

    # 🧸 Soft Toys / Dolls
    elif "soft" in category or "doll" in category or "plush" in category:
        extra_details = {
            "Material": getattr(product, 'material', 'Soft Cotton / Plush'),
            "Color": getattr(product, 'color', 'Various colors available'),
            "Washable": getattr(product, 'washable', 'Yes'),
            "Age Group": getattr(product, 'age_group', '1+ years'),
        }

    # ⚙️ Default Fallback
    else:
        extra_details = {
            "Material": getattr(product, 'material', 'High-quality materials'),
            "Color": getattr(product, 'color', 'Multicolor'),
            "Recommended Age": getattr(product, 'age_group', '3+ years'),
        }

    related_products = ToyProduct.objects.order_by('-id')[:5]

    context = {
        'product': product,
        'extra_details': extra_details,
        'related_products': related_products,
    }

    return render(request, 'toy_product_detail.html', context)

