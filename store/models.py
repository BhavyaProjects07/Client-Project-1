# store/models.py
from django.db import models
from django.conf import settings
from django.db.models import Avg
from cloudinary.models import CloudinaryField
from django.utils.text import slugify
from django.contrib.postgres.fields import JSONField  # If using Postgres. If not, use models.JSONField (Django 3.1+)
from django.urls import reverse
from .utils import format_description
from django.core.validators import MinValueValidator

User = settings.AUTH_USER_MODEL


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        abstract = True


class Category(TimestampedModel):
    """Flexible categories. Admin adds categories (electronics, women, toys, grocery...)"""
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    description = models.TextField(blank=True, null=True)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="children")

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class ProductType(TimestampedModel):
    """
    Optional grouping for product templates (e.g. 'Clothing', 'Electronics', 'Grocery').
    ProductType can define which attributes are available by default.
    """
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    description = models.TextField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Product(TimestampedModel):
    """
    Single product table for all categories/types.
    Client in admin will create Category -> Product (no code changes).
    """
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=320, blank=True, db_index=True)
    sku = models.CharField(max_length=64, blank=True, null=True, help_text="Optional SKU or product code")
    product_type = models.ForeignKey(ProductType, on_delete=models.SET_NULL, null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="products")
    description = models.TextField(blank=True, null=True)
    description_html = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    old_price = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    featured = models.BooleanField(default=False)
    available_stock = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    main_image = CloudinaryField('image', folder='products', blank=True, null=True)

    class Meta:
        ordering = ["-featured", "-created_at"]
        indexes = [
            models.Index(fields=['slug']),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)[:200]
            # ensure unique slug by appending id later if needed
            self.slug = base
        # format description -> description_html (use your util)
        if self.description:
            if '<' not in self.description:
                self.description_html = format_description(self.description)
            else:
                self.description_html = self.description
        else:
            self.description_html = ""
        super().save(*args, **kwargs)
        # ensure slug uniqueness: append id if duplicate
        if not self.slug.endswith(f"-{self.id}"):
            qs = Product.objects.filter(slug=self.slug).exclude(pk=self.pk)
            if qs.exists():
                self.slug = f"{self.slug}-{self.id}"
                super().save(update_fields=['slug'])

    def get_primary_image_url(self):
        if self.main_image:
            return getattr(self.main_image, 'url', '')
        first = self.images.order_by('order').first()
        if first:
            return getattr(first.image, 'url', '')
        return ""

    def average_rating(self):
        return self.reviews.aggregate(avg_rating=Avg('rating'))['avg_rating'] or 0

    def review_count(self):
        return self.reviews.count()

    def get_absolute_url(self):
        return reverse("product_detail", kwargs={"slug": self.slug, "pk": self.pk})

    def __str__(self):
        return self.name


class ProductImage(TimestampedModel):
    product = models.ForeignKey(Product, related_name='images', on_delete=models.CASCADE)
    image = CloudinaryField('image', folder='products')
    alt_text = models.CharField(max_length=255, blank=True, null=True)
    order = models.PositiveIntegerField(default=0)
    is_primary = models.BooleanField(default=False)

    class Meta:
        ordering = ["order"]

    def save(self, *args, **kwargs):
        if self.is_primary:
            # unset other primary flags for the same product
            ProductImage.objects.filter(product=self.product, is_primary=True).update(is_primary=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Image {self.id} for {self.product.name}"


# Attributes (custom fields) system
ATTRIBUTE_TYPE_CHOICES = [
    ('text', 'Text'),
    ('number', 'Number'),
    ('boolean', 'Boolean'),
    ('choice', 'Choice (one of choices)'),
    ('multichoice', 'Multiple Choice'),
]


class ProductAttribute(TimestampedModel):
    """
    Define attributes (custom fields) that can be attached to products.
    Admin can create attributes and optionally attach to ProductType.
    Example: Size, Color, Material, Capacity, Expiry Date, Ingredients.
    """
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, blank=True)
    attribute_type = models.CharField(max_length=20, choices=ATTRIBUTE_TYPE_CHOICES, default='text')
    product_type = models.ForeignKey(ProductType, on_delete=models.SET_NULL, null=True, blank=True, related_name="attributes")
    # for choice fields store comma-separated options (admin can set)
    choices = models.TextField(blank=True, null=True, help_text="Comma separated choices for choice/multichoice types")
    required = models.BooleanField(default=False)

    class Meta:
        unique_together = ("slug", "product_type")
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_choices_list(self):
        if not self.choices:
            return []
        return [c.strip() for c in self.choices.split(",") if c.strip()]

    def __str__(self):
        return self.name


class ProductAttributeValue(TimestampedModel):
    """
    Stores attribute values per product. Value saved as text (flexible).
    """
    product = models.ForeignKey(Product, related_name="attribute_values", on_delete=models.CASCADE)
    attribute = models.ForeignKey(ProductAttribute, on_delete=models.CASCADE)
    value = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ("product", "attribute")

    def __str__(self):
        return f"{self.product.name} — {self.attribute.name}: {self.value}"


class ProductVariant(TimestampedModel):
    """
    Simple variant model (size/color combos). Variants can override price and stock.
    variant_options stored as JSON like {"size":"M","color":"Red"}.
    """
    product = models.ForeignKey(Product, related_name='variants', on_delete=models.CASCADE)
    sku = models.CharField(max_length=120, blank=True, null=True)
    variant_options = models.JSONField(blank=True, null=True, default=dict)
    price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)], blank=True, null=True, help_text="Optional override price")
    stock = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("product", "sku")

    def display_price(self):
        return self.price if self.price is not None else self.product.price

    def __str__(self):
        nice = ", ".join(f"{k}:{v}" for k, v in (self.variant_options or {}).items())
        return f"{self.product.name} — {nice or self.sku or 'Default'}"


# Keep existing models like CustomUser, CartItem, Wishlist Item etc. but updated to reference the new Product.
from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    is_verified = models.BooleanField(default=False)
    is_delivery_boy = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self):
        return f"{self.username} - {self.email}"


# Example CartItem adapted to new system
class CartItem(TimestampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, null=True, blank=True, on_delete=models.CASCADE)
    variant = models.ForeignKey(ProductVariant, null=True, blank=True, on_delete=models.SET_NULL)
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)
    

    def subtotal(self):
        price = self.variant.display_price() if self.variant else (self.product.price if self.product else 0)
        return price * self.quantity
    def total_price(self):
        return self.subtotal()


    def __str__(self):
        return f"{self.user.username} — {self.product.name if self.product else 'Unknown'} x {self.quantity}"

# ======================================================
# WISHLIST SYSTEM (Dynamic Version)
# ======================================================
from django.contrib.auth import get_user_model
from django.db import models
from .models import Product, ProductVariant

User = get_user_model()

class WishlistItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)

    # Optional variant (size/color/etc.)
    variant = models.ForeignKey(ProductVariant, null=True, blank=True, on_delete=models.SET_NULL)

    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product', 'variant')

    def __str__(self):
        if self.variant:
            return f"{self.user.username} - {self.product.name} ({self.variant.variant_options})"
        return f"{self.user.username} - {self.product.name}"


# ======================================================
# ORDER SYSTEM (Dynamic Version)
# ======================================================
ORDER_STATUS_CHOICES = [
    ('Pending pickup', 'Pending pickup'),
    ('Out for delivery', 'Out for delivery'),
    ('Delivered', 'Delivered'),
    ('Cancelled', 'Cancelled'),
]

class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    full_name = models.CharField(max_length=100)
    address = models.TextField()
    city = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=10)
    phone_number = models.CharField(max_length=15)

    payment_method = models.CharField(max_length=50, default='Cash On Delivery')
    paid = models.BooleanField(default=False)

    order_status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='Pending pickup')
    created_at = models.DateTimeField(auto_now_add=True)

    assigned_to = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="delivery_orders"
    )

    def __str__(self):
        return f"Order #{self.pk} by {self.user.username}"

    def total_amount(self):
        return sum(item.total_price() for item in self.items.all())



class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)

    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variant = models.ForeignKey(ProductVariant, null=True, blank=True, on_delete=models.SET_NULL)

    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)  # snapshot of price at purchase

    def total_price(self):
        return self.quantity * self.price

    def __str__(self):
        if self.variant:
            return f"{self.product.name} ({self.variant.variant_options})"
        return f"{self.product.name}"


class Review(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variant = models.ForeignKey(ProductVariant, null=True, blank=True, on_delete=models.SET_NULL)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, null=True, blank=True)

    rating = models.IntegerField()
    comment = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product', 'variant')

    def __str__(self):
        if self.variant:
            return f"Review by {self.user.username} on {self.product.name} ({self.variant.variant_options})"
        return f"Review by {self.user.username} on {self.product.name}"


class DeliveryProfile(models.Model):
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="delivery_profile"
    )
    phone = models.CharField(max_length=15, blank=True, null=True)
    first_name = models.CharField(max_length=50, blank=True, null=True)
    last_name = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} Profile"
    

class BusinessNameAndLogo(models.Model):
    business_name = models.CharField(max_length=255)
    logo = CloudinaryField('logo', folder='business_logos', blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    contact_email = models.EmailField(blank=True, null=True)
    contact_phone = models.CharField(max_length=15, blank=True, null=True)
    allowed_pincodes = models.JSONField(default=list, blank=True, null=True)

    def __str__(self):
        return self.business_name
