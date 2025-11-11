from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db.models import Avg
from decouple import config
import base64
import requests
from decouple import config

import base64, requests, certifi, time
from decouple import config

IMAGEKIT_UPLOAD_URL = "https://upload.imagekit.io/api/v1/files/upload"
IMAGEKIT_PUBLIC_KEY = config("IMAGEKIT_PUBLIC_KEY")
IMAGEKIT_PRIVATE_KEY = config("IMAGEKIT_PRIVATE_KEY")

def upload_to_imagekit(file, folder="/products"):
    """
    Reliable ImageKit uploader using HTTPS + retry.
    Works perfectly even on Windows with TLS 1.3.
    """
    try:
        # Prepare base64 payload
        file.seek(0)
        file_base64 = base64.b64encode(file.read()).decode("utf-8")

        payload = {
            "file": file_base64,
            "fileName": file.name,
            "folder": folder,
            "useUniqueFileName": "true"
        }

        # Basic Auth
        auth = (IMAGEKIT_PUBLIC_KEY, IMAGEKIT_PRIVATE_KEY)

        # Try twice if needed
        for attempt in range(2):
            try:
                resp = requests.post(
                    IMAGEKIT_UPLOAD_URL,
                    data=payload,
                    auth=auth,
                    timeout=40,
                    verify=certifi.where(),  # ✅ Force cert verification
                )
                if resp.status_code in [200, 201]:
                    url = resp.json().get("url")
                    if url:
                        print(f"✅ Uploaded to ImageKit: {url}")
                        return url
                    else:
                        print(f"⚠️ Upload succeeded but no URL returned: {resp.text}")
                        return None
                else:
                    print(f"⚠️ ImageKit HTTP {resp.status_code}: {resp.text}")
            except requests.exceptions.SSLError as ssl_err:
                print(f"🔄 SSL error on attempt {attempt+1}, retrying: {ssl_err}")
                time.sleep(2)
            except requests.exceptions.RequestException as re:
                print(f"⚠️ Request error: {re}")
                time.sleep(2)

        print("❌ ImageKit upload failed after retries.")
        return None

    except Exception as e:
        print(f"❌ Unexpected ImageKit error: {e}")
        return None


# ======================================================
# WOMEN PRODUCTS MODEL
# ======================================================
class WomenProduct(models.Model):
    CATEGORY_CHOICES = [
        
        ('sarees', 'Sarees'),

        ('accessories', 'Accessories'),
        ('footwear', 'Footwear'),
    ]

    name = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image_url = models.URLField(blank=True, null=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='tops')
    available_stock = models.PositiveIntegerField(default=10)
    def save(self, *args, **kwargs):
        # upload to ImageKit only if admin added image manually
        image_file = getattr(self, "image_file", None)
        if image_file and not self.image_url:
            uploaded_url = upload_to_imagekit(image_file, folder="/women")
            if uploaded_url:
                self.image_url = uploaded_url
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def average_rating(self):
        return self.reviews.aggregate(avg_rating=Avg('rating'))['avg_rating'] or 0

    def review_count(self):
        return self.reviews.count()


# ======================================================
# ELECTRONIC PRODUCTS MODEL
# ======================================================
class ElectronicProduct(models.Model):
    CATEGORY_CHOICES = [
        ('mobiles', 'Mobiles & Smartphones'),
        ('laptops', 'Laptops'),
        ('televisions', 'Televisions'),
        ('headphones', 'Headphones & Earbuds'),
        ('smartwatches', 'Smartwatches'),
        ('accessories', 'Electronic Accessories'),
        ('appliances', 'Home Appliances'),
        ('gaming', 'Gaming Consoles'),
        ('cameras', 'Cameras'),
    ]

    name = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image_url = models.URLField(blank=True, null=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='mobiles')
    available_stock = models.PositiveIntegerField(default=10)
    def save(self, *args, **kwargs):
        image_file = getattr(self, "image_file", None)
        if image_file and not self.image_url:
            uploaded_url = upload_to_imagekit(image_file, folder="/electronics")
            if uploaded_url:
                self.image_url = uploaded_url
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


# ======================================================
# TOY PRODUCTS MODEL
# ======================================================
class ToyProduct(models.Model):
    CATEGORY_CHOICES = [
        ('action_figures', 'Action Figures'),
        ('educational', 'Educational Toys'),
        ('soft_toys', 'Soft Toys'),
        ('dolls', 'Dolls'),
        ('puzzles', 'Puzzles'),
        ('remote_control', 'Remote Control Toys'),
        ('building_sets', 'Building & Construction Sets'),
        ('outdoor', 'Outdoor Toys'),
        ('vehicles', 'Toy Cars & Vehicles'),
    ]

    name = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image_url = models.URLField(blank=True, null=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='action_figures')
    available_stock = models.PositiveIntegerField(default=10)
    def save(self, *args, **kwargs):
        image_file = getattr(self, "image_file", None)
        if image_file and not self.image_url:
            uploaded_url = upload_to_imagekit(image_file, folder="/toys")
            if uploaded_url:
                self.image_url = uploaded_url
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

# ======================================================
# CUSTOM USER MODEL
# ======================================================
class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return self.username


# ======================================================
# CART SYSTEM
# ======================================================
class CartItem(models.Model):
    PRODUCT_TYPE_CHOICES = [
        ('women', 'Women Product'),
        ('electronic', 'Electronic Product'),
        ('toy', 'Toy Product'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    product_type = models.CharField(max_length=20, choices=PRODUCT_TYPE_CHOICES, null=True, blank=True)
    product_id = models.PositiveIntegerField(null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)

    # ✅ Variant fields for fashion products
    size = models.CharField(max_length=20, blank=True, null=True)
    color = models.CharField(max_length=50, blank=True, null=True)
    fabric = models.CharField(max_length=50, blank=True, null=True)
    
    added_at = models.DateTimeField(auto_now_add=True)

    def get_product(self):
        if self.product_type == 'women':
            return WomenProduct.objects.filter(id=self.product_id).first()
        elif self.product_type == 'electronic':
            return ElectronicProduct.objects.filter(id=self.product_id).first()
        elif self.product_type == 'toy':
            return ToyProduct.objects.filter(id=self.product_id).first()
        return None

    def subtotal(self):
        product = self.get_product()
        return self.quantity * (product.price if product else 0)

    def __str__(self):
        product = self.get_product()
        return f"{product.name if product else 'Unknown'} ({self.size or 'Default'}, {self.color or 'N/A'}) x {self.quantity}"


# ======================================================
# WISHLIST SYSTEM
# ======================================================
from django.contrib.auth import get_user_model
User = get_user_model()

class WishlistItem(models.Model):
    PRODUCT_TYPE_CHOICES = [
        ('women', 'Women Product'),
        ('electronic', 'Electronic Product'),
        ('toy', 'Toy Product'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product_type = models.CharField(max_length=20, choices=PRODUCT_TYPE_CHOICES, null=True, blank=True)
    product_id = models.PositiveIntegerField(null=True, blank=True)

    # ✅ Variant fields
    size = models.CharField(max_length=20, blank=True, null=True)
    color = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        unique_together = ('user', 'product_type', 'product_id', 'size', 'color')

    def get_product(self):
        if self.product_type == 'women':
            return WomenProduct.objects.filter(id=self.product_id).first()
        elif self.product_type == 'electronic':
            return ElectronicProduct.objects.filter(id=self.product_id).first()
        elif self.product_type == 'toy':
            return ToyProduct.objects.filter(id=self.product_id).first()
        return None

    def __str__(self):
        product = self.get_product()
        return f"{self.user.username} - {product.name if product else 'Unknown'} ({self.size or 'Default'})"

    PRODUCT_TYPE_CHOICES = [
        ('women', 'Women Product'),
        ('electronic', 'Electronic Product'),
        ('toy', 'Toy Product'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product_type = models.CharField(max_length=20, choices=PRODUCT_TYPE_CHOICES, null=True, blank=True)
    product_id = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        unique_together = ('user', 'product_type', 'product_id')

    def get_product(self):
        if self.product_type == 'women':
            return WomenProduct.objects.filter(id=self.product_id).first()
        elif self.product_type == 'electronic':
            return ElectronicProduct.objects.filter(id=self.product_id).first()
        elif self.product_type == 'toy':
            return ToyProduct.objects.filter(id=self.product_id).first()
        return None

    def __str__(self):
        product = self.get_product()
        return f"{self.user.username} - {product.name if product else 'Unknown'}"


# ======================================================
# ORDER SYSTEM
# ======================================================
ORDER_STATUS_CHOICES = [
    ('Pending', 'Pending'),
    ('Shipped', 'Shipped'),
    ('Out for Delivery', 'Out for Delivery'),
    ('Delivered', 'Delivered'),
]


PAYMENT_STATUS_CHOICES = [
    ('Paid', 'Paid'),
    ('Not Paid', 'Not Paid'),
    
]

class Order(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=100)
    address = models.TextField()
    city = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=10)
    phone_number = models.CharField(max_length=15)
    payment_method = models.CharField(max_length=50, default='Cash On Delivery')

    # ✅ Corrected field — no string choices, Boolean only
    paid = models.BooleanField(default=False)

    order_status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order #{self.pk} by {self.user.username}"

    def total_amount(self):
        return sum(item.total_price() for item in self.items.all())


class OrderItem(models.Model):
    PRODUCT_TYPE_CHOICES = [
        ('women', 'Women Product'),
        ('electronic', 'Electronic Product'),
        ('toy', 'Toy Product'),
    ]

    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product_type = models.CharField(max_length=20, choices=PRODUCT_TYPE_CHOICES, null=True, blank=True)
    product_id = models.PositiveIntegerField(null=True, blank=True)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    # ✅ Variant fields
    size = models.CharField(max_length=20, blank=True, null=True)
    color = models.CharField(max_length=50, blank=True, null=True)
    fabric = models.CharField(max_length=50, blank=True, null=True)

    def get_product(self):
        if self.product_type == 'women':
            return WomenProduct.objects.filter(id=self.product_id).first()
        elif self.product_type == 'electronic':
            return ElectronicProduct.objects.filter(id=self.product_id).first()
        elif self.product_type == 'toy':
            return ToyProduct.objects.filter(id=self.product_id).first()
        return None

    def total_price(self):
        return self.quantity * self.price

    def __str__(self):
        product = self.get_product()
        return f"{product.name if product else 'Unknown'} ({self.size or 'Default'}, {self.color or 'N/A'})"

    PRODUCT_TYPE_CHOICES = [
        ('women', 'Women Product'),
        ('electronic', 'Electronic Product'),
        ('toy', 'Toy Product'),
    ]

    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product_type = models.CharField(max_length=20, choices=PRODUCT_TYPE_CHOICES, null=True, blank=True)
    product_id = models.PositiveIntegerField(null=True, blank=True)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def get_product(self):
        if self.product_type == 'women':
            return WomenProduct.objects.filter(id=self.product_id).first()
        elif self.product_type == 'electronic':
            return ElectronicProduct.objects.filter(id=self.product_id).first()
        elif self.product_type == 'toy':
            return ToyProduct.objects.filter(id=self.product_id).first()
        return None

    def total_price(self):
        return self.quantity * self.price

    def __str__(self):
        product = self.get_product()
        return product.name if product else 'Unknown Product'


# ======================================================
# REVIEW SYSTEM
class Review(models.Model):
    PRODUCT_TYPE_CHOICES = [
        ('women', 'Women Product'),
        ('electronic', 'Electronic Product'),
        ('toy', 'Toy Product'),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    product_type = models.CharField(max_length=20, choices=PRODUCT_TYPE_CHOICES, null=True, blank=True)
    product_id = models.PositiveIntegerField(null=True, blank=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, null=True, blank=True)
    rating = models.IntegerField()
    comment = models.TextField()

    # ✅ Variant fields
    size = models.CharField(max_length=20, blank=True, null=True)
    color = models.CharField(max_length=50, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product_type', 'product_id', 'size', 'color')

    def get_product(self):
        if self.product_type == 'women':
            return WomenProduct.objects.filter(id=self.product_id).first()
        elif self.product_type == 'electronic':
            return ElectronicProduct.objects.filter(id=self.product_id).first()
        elif self.product_type == 'toy':
            return ToyProduct.objects.filter(id=self.product_id).first()
        return None

    def __str__(self):
        product = self.get_product()
        return f"Review by {self.user.username} on {product.name if product else 'Unknown'} ({self.size or 'Default'})"

    PRODUCT_TYPE_CHOICES = [
        ('women', 'Women Product'),
        ('electronic', 'Electronic Product'),
        ('toy', 'Toy Product'),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    product_type = models.CharField(max_length=20, choices=PRODUCT_TYPE_CHOICES, null=True, blank=True)
    product_id = models.PositiveIntegerField(null=True, blank=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, null=True, blank=True)
    rating = models.IntegerField()
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product_type', 'product_id')

    def get_product(self):
        if self.product_type == 'women':
            return WomenProduct.objects.filter(id=self.product_id).first()
        elif self.product_type == 'electronic':
            return ElectronicProduct.objects.filter(id=self.product_id).first()
        elif self.product_type == 'toy':
            return ToyProduct.objects.filter(id=self.product_id).first()
        return None

    def __str__(self):
        product = self.get_product()
        return f"Review by {self.user.username} on {product.name if product else 'Unknown'}"
