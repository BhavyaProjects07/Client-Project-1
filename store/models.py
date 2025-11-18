from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db.models import Avg
from cloudinary.models import CloudinaryField

from .utils import format_description   # we will use this for auto-formatting


# ======================================================
# BASE PRODUCT MODEL (Shared by all products)
# ======================================================
class BaseProduct(models.Model):
    description = models.TextField(blank=True, null=True)       # raw text from client
    description_html = models.TextField(blank=True, null=True)  # auto-generated formatted HTML

    class Meta:
        abstract = True   # no DB table created for this model

    def save(self, *args, **kwargs):
        if self.description:
            # Prevent double-formatting: only format if raw has NO HTML tags
            if '<' not in self.description:
                self.description_html = format_description(self.description)
            else:
                self.description_html = self.description
        else:
            self.description_html = ""
        super().save(*args, **kwargs)


# ======================================================
# WOMEN PRODUCTS MODEL
# ======================================================
class WomenProduct(BaseProduct):
    CATEGORY_CHOICES = [
        ('sarees', 'Sarees'),
        ('accessories', 'Accessories'),
        ('footwear', 'Footwear'),
    ]

    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = CloudinaryField('image', folder='women')
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='sarees')
    available_stock = models.PositiveIntegerField(default=10)

    def __str__(self):
        return self.name

    def average_rating(self):
        return self.reviews.aggregate(avg_rating=Avg('rating'))['avg_rating'] or 0

    def review_count(self):
        return self.reviews.count()


# ======================================================
# ELECTRONIC PRODUCTS MODEL
# ======================================================
class ElectronicProduct(BaseProduct):
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
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = CloudinaryField('image', folder='electronics')
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='mobiles')
    available_stock = models.PositiveIntegerField(default=10)

    def __str__(self):
        return self.name


# ======================================================
# TOY PRODUCTS MODEL
# ======================================================
class ToyProduct(BaseProduct):
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
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = CloudinaryField('image', folder='toys')
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='action_figures')
    available_stock = models.PositiveIntegerField(default=10)

    def __str__(self):
        return self.name

# ======================================================
# CUSTOM USER MODEL
# ======================================================
class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    is_verified = models.BooleanField(default=False)

    is_delivery_boy = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]   # username still required but not for login

    def __str__(self):
        return f"{self.username} - {self.email}"



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
    ('Pending pickup', 'Pending pickup'),
    ('Out for delivery', 'Out for delivery'),
    ('Delivered', 'Delivered'),
    ('Cancelled', 'Cancelled'),
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

    order_status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='Pending pickup')
    created_at = models.DateTimeField(auto_now_add=True)
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="delivery_orders"
    )

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



class ContactMessage(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message from {self.name} - {self.subject}"
    


class DeliveryProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name="delivery_profile")
    phone = models.CharField(max_length=15, blank=True, null=True)
    first_name = models.CharField(max_length=50, blank=True, null=True)
    last_name = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} Profile"


from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=CustomUser)
def create_delivery_profile(sender, instance, created, **kwargs):
    if created and instance.is_delivery_boy:
        DeliveryProfile.objects.create(user=instance)

@receiver(post_save, sender=CustomUser)
def save_delivery_profile(sender, instance, **kwargs):
    if instance.is_delivery_boy:
        instance.delivery_profile.save()




class BusinessNameAndLogo(models.Model):
    business_name = models.CharField(max_length=255)
    logo = CloudinaryField('logo', folder='business')

    def __str__(self):
        return self.business_name