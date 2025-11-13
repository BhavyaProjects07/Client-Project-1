from django.contrib import admin
from django import forms
from django.utils.html import format_html

from .models import (
    WomenProduct,
    ElectronicProduct,
    ToyProduct,
    CustomUser,
    CartItem,
    WishlistItem,
    Order,
    OrderItem,
    Review
)

# ======================================================
# WOMEN PRODUCTS ADMIN
# ======================================================

class WomenProductForm(forms.ModelForm):
    class Meta:
        model = WomenProduct
        fields = "__all__"


@admin.register(WomenProduct)
class WomenProductAdmin(admin.ModelAdmin):
    form = WomenProductForm
    list_display = ["name", "category", "price", "image_preview"]

    def image_preview(self, obj):
        if obj.image and hasattr(obj.image, 'url'):
            return format_html(
                '<img src="{}" width="60" height="60" style="object-fit:cover;border-radius:6px;">',
                obj.image.url
            )
        return "No Image"

    image_preview.short_description = "Image"


# ======================================================
# ELECTRONIC PRODUCTS ADMIN
# ======================================================

class ElectronicProductForm(forms.ModelForm):
    class Meta:
        model = ElectronicProduct
        fields = "__all__"


@admin.register(ElectronicProduct)
class ElectronicProductAdmin(admin.ModelAdmin):
    form = ElectronicProductForm
    list_display = ["name", "category", "price", "image_preview"]

    def image_preview(self, obj):
        if obj.image and hasattr(obj.image, 'url'):
            return format_html(
                '<img src="{}" width="60" height="60" style="object-fit:cover;border-radius:6px;">',
                obj.image.url
            )
        return "No Image"

    image_preview.short_description = "Image"


# ======================================================
# TOY PRODUCTS ADMIN
# ======================================================

class ToyProductForm(forms.ModelForm):
    class Meta:
        model = ToyProduct
        fields = "__all__"


@admin.register(ToyProduct)
class ToyProductAdmin(admin.ModelAdmin):
    form = ToyProductForm
    list_display = ["name", "category", "price", "image_preview"]

    def image_preview(self, obj):
        if obj.image and hasattr(obj.image, 'url'):
            return format_html(
                '<img src="{}" width="60" height="60" style="object-fit:cover;border-radius:6px;">',
                obj.image.url
            )
        return "No Image"

    image_preview.short_description = "Image"


# ======================================================
# REGISTER OTHER MODELS
# ======================================================

admin.site.register(CustomUser)
admin.site.register(CartItem)
admin.site.register(WishlistItem)
admin.site.register(OrderItem)
admin.site.register(Review)


# ======================================================
# ORDER ADMIN
# ======================================================

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'full_name', 'order_status', 'paid', 'created_at')
    list_filter = ('order_status', 'paid', 'created_at')
    list_editable = ('order_status', 'paid')
