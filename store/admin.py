from django.contrib import admin
from django import forms
from django.utils.html import format_html
from ckeditor.widgets import CKEditorWidget
from .models import (
    WomenProduct,
    ElectronicProduct,
    ToyProduct,
    CustomUser,
    CartItem,
    WishlistItem,
    Order,
    OrderItem,
    Review,
    DeliveryProfile,
    BusinessNameAndLogo
)

# ======================================================
# WOMEN PRODUCTS ADMIN
# ======================================================

# ======================================================
# WOMEN PRODUCTS ADMIN
# ======================================================

class WomenProductForm(forms.ModelForm):
    description = forms.CharField(widget=CKEditorWidget(), required=False)

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

# ======================================================
# ELECTRONIC PRODUCTS ADMIN
# ======================================================

class ElectronicProductForm(forms.ModelForm):
    description = forms.CharField(widget=CKEditorWidget(), required=False)

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
    description = forms.CharField(widget=CKEditorWidget(), required=False)

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

from django.contrib import admin
from .models import CustomUser

@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ("username", "email", "is_staff", "is_delivery_boy", "is_active")
    list_filter = ("is_staff", "is_delivery_boy", "is_active")
    list_editable = ("is_staff", "is_delivery_boy", "is_active")
    ordering = ("-date_joined",)
    search_fields = ("username", "email")

admin.site.register(CartItem)
admin.site.register(WishlistItem)
admin.site.register(OrderItem)
admin.site.register(Review)


# ======================================================
# ORDER ADMIN
# ======================================================

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'full_name', 'order_status', 'paid', 'created_at', 'assigned_to')
    list_filter = ('order_status', 'paid', 'created_at')
    list_editable = ('order_status', 'paid')

    # Show only delivery boys in assigned_to dropdown
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "assigned_to":
            from store.models import CustomUser
            kwargs["queryset"] = CustomUser.objects.filter(is_delivery_boy=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


admin.site.register(DeliveryProfile)
admin.site.register(BusinessNameAndLogo)