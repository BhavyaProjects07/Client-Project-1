from django.contrib import admin
from django import forms
from django.utils.html import format_html
from ckeditor.widgets import CKEditorWidget

from .models import (
    Category,
    ProductType,
    Product,
    ProductImage,
    ProductVariant,
    ProductAttribute,
    WishlistItem,
    Order,
    OrderItem,
    Review,
    CustomUser,
    DeliveryProfile,
    BusinessNameAndLogo,
)

# ======================================================
# PRODUCT IMAGE INLINE
# ======================================================

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    readonly_fields = ("preview",)

    def preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="60" style="border-radius:6px;">',
                obj.image.url
            )
        return "No Image"

    preview.short_description = "Preview"


# ======================================================
# VARIANT INLINE
# ======================================================

class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    readonly_fields = ("formatted_options",)

    def formatted_options(self, obj):
        if obj.variant_options:
            return ", ".join([f"{k}: {v}" for k, v in obj.variant_options.items()])
        return "—"

    formatted_options.short_description = "Variant Options"


# ======================================================
# PRODUCT ADMIN FORM
# ======================================================

class ProductAdminForm(forms.ModelForm):
    description = forms.CharField(widget=CKEditorWidget(), required=False)

    class Meta:
        model = Product
        fields = "__all__"


# ======================================================
# PRODUCT ADMIN
# ======================================================

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    form = ProductAdminForm
    inlines = [ProductImageInline, ProductVariantInline]

    list_display = (
        "name",
        "product_type",
        "category",
        "price",
        "available_stock",   # FIXED → replaced stock
        "thumbnail",
        "created_at",
    )

    list_filter = ("product_type", "category", "created_at")
    search_fields = ("name", "description", "category__name", "product_type__name")

    def thumbnail(self, obj):
        url = obj.get_primary_image_url()
        if url:
            return format_html(
                '<img src="{}" width="60" style="border-radius:6px;">',
                url
            )
        return "—"

    thumbnail.short_description = "Image"


# ======================================================
# CATEGORY ADMIN
# ======================================================

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at")
    search_fields = ("name",)
    ordering = ("name",)


# ======================================================
# PRODUCT TYPE ADMIN
# ======================================================

@admin.register(ProductType)
class ProductTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at")
    search_fields = ("name",)
    ordering = ("name",)


# ======================================================
# PRODUCT ATTRIBUTE ADMIN
# ======================================================

@admin.register(ProductAttribute)
class ProductAttributeAdmin(admin.ModelAdmin):
    list_display = ("name", "attribute_type", "product_type", "created_at")
    search_fields = ("name",)
    list_filter = ("attribute_type", "product_type")


# ======================================================
# CUSTOM USER ADMIN
# ======================================================

@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ("username", "email", "is_staff", "is_delivery_boy", "is_active")
    list_filter = ("is_staff", "is_delivery_boy", "is_active")
    search_fields = ("username", "email")
    list_editable = ("is_staff", "is_delivery_boy", "is_active")


# ======================================================
# ORDER ITEM INLINE
# ======================================================

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product", "variant", "quantity", "price")


# ======================================================
# ORDER ADMIN
# ======================================================

# inside admin.py
from store.email_service import send_brevo_email

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id", "user", "full_name", "order_status", "paid",
        "created_at", "assigned_to", "total_amount",
    )
    list_filter = ("order_status", "paid", "payment_method", "created_at")
    search_fields = ("full_name", "user__username", "user__email", "id")
    readonly_fields = ("created_at",)
    inlines = [OrderItemInline]

    # Allow only delivery boys
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "assigned_to":
            kwargs["queryset"] = CustomUser.objects.filter(is_delivery_boy=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    # 🚀 SEND EMAIL WHEN ORDER ASSIGNED
    def save_model(self, request, obj, form, change):
        # Detect assignment change
        if change and "assigned_to" in form.changed_data:
            if obj.assigned_to:   # delivery boy exists
                delivery_boy = obj.assigned_to

                # Delivery dashboard URL
                link = request.build_absolute_uri(
                    f"/delivery/order/{obj.id}/"
                )

                # email content
                subject = f"New Order Assigned — Order #{obj.id}"
                text = (
                    f"Hello {delivery_boy.username},\n\n"
                    f"You have been assigned a new order.\n"
                    f"Order ID: #{obj.id}\n"
                    f"Customer: {obj.full_name}\n"
                    f"Delivery Address: {obj.address}, {obj.city}\n\n"
                    f"Open Dashboard: {link}\n\n"
                    "Thank you!"
                )

                html = f"""
                <div style="font-family:Arial;padding:16px;background:#f7f7f7;">
                  <div style="max-width:600px;background:white;padding:20px;border-radius:8px;">
                    <h2>New Order Assigned — #{obj.id}</h2>
                    <p><strong>Customer:</strong> {obj.full_name}</p>
                    <p><strong>Address:</strong> {obj.address}, {obj.city}</p>
                    <p><strong>Postal Code:</strong> {obj.postal_code}</p>
                    <p><strong>Phone:</strong> {obj.phone_number}</p>
                    <br>
                    <a href="{link}" 
                       style="background:#f59e0b;color:white;padding:10px 16px;border-radius:6px;text-decoration:none;">
                       Open Delivery Dashboard
                    </a>
                  </div>
                </div>
                """

                # Send email (using your Brevo helper)
                try:
                    send_brevo_email(
                        to=delivery_boy.email,
                        subject=subject,
                        text_content=text,
                        html_content=html
                    )
                except Exception as e:
                    print("Delivery Email Error:", e)

        super().save_model(request, obj, form, change)


# ======================================================
# REVIEW ADMIN
# ======================================================

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("product", "user", "rating", "created_at")
    list_filter = ("rating", "created_at")
    search_fields = ("user__username", "product__name", "comment")


# ======================================================
# WISHLIST ADMIN
# ======================================================

@admin.register(WishlistItem)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ("user", "product", "variant", "added_at")
    list_filter = ("added_at",)
    search_fields = ("user__username", "product__name")


# ======================================================
# DELIVERY PROFILE ADMIN
# ======================================================

@admin.register(DeliveryProfile)
class DeliveryProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "phone", "first_name", "last_name")
    search_fields = ("user__username", "phone", "first_name", "last_name")


# ======================================================
# BUSINESS NAME & LOGO
# ======================================================

@admin.register(BusinessNameAndLogo)
class BusinessNameAndLogoAdmin(admin.ModelAdmin):
    list_display = ("business_name", "logo")
    search_fields = ("business_name",)
