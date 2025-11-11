from django.contrib import admin
from django import forms
from .models import WomenProduct, ElectronicProduct, ToyProduct, CustomUser, CartItem, WishlistItem, Order, OrderItem, Review


# ======================================================
# CUSTOM ADMIN FOR WOMEN PRODUCTS
# ======================================================
class WomenProductForm(forms.ModelForm):
    image_file = forms.ImageField(required=False, label="Upload Image")

    class Meta:
        model = WomenProduct
        fields = "__all__"


@admin.register(WomenProduct)
class WomenProductAdmin(admin.ModelAdmin):
    form = WomenProductForm
    list_display = ["name", "category", "price", "image_preview"]

    def image_preview(self, obj):
        return (
            f'<img src="{obj.image_url}" width="60" height="60" style="object-fit:cover;border-radius:6px;">'
            if obj.image_url else "No Image"
        )
    image_preview.allow_tags = True
    image_preview.short_description = "Image"

    # ✅ FIX: Assign uploaded image to model before saving
    def save_model(self, request, obj, form, change):
        uploaded_file = form.cleaned_data.get("image_file")
        if uploaded_file:
            obj.image_file = uploaded_file  # attach uploaded file to model
        super().save_model(request, obj, form, change)



# ======================================================
# CUSTOM ADMIN FOR ELECTRONICS
# ======================================================
class ElectronicProductForm(forms.ModelForm):
    image_file = forms.ImageField(required=False, label="Upload Image")

    class Meta:
        model = ElectronicProduct
        fields = "__all__"


@admin.register(ElectronicProduct)
class ElectronicProductAdmin(admin.ModelAdmin):
    form = ElectronicProductForm
    list_display = ["name", "category", "price", "image_preview"]

    def image_preview(self, obj):
        return (
            f'<img src="{obj.image_url}" width="60" height="60" style="object-fit:cover;border-radius:6px;">'
            if obj.image_url else "No Image"
        )
    image_preview.allow_tags = True
    image_preview.short_description = "Image"

    def save_model(self, request, obj, form, change):
        uploaded_file = form.cleaned_data.get("image_file")
        if uploaded_file:
            obj.image_file = uploaded_file
        super().save_model(request, obj, form, change)



# ======================================================
# CUSTOM ADMIN FOR TOYS
# ======================================================
class ToyProductForm(forms.ModelForm):
    image_file = forms.ImageField(required=False, label="Upload Image")

    class Meta:
        model = ToyProduct
        fields = "__all__"


@admin.register(ToyProduct)
class ToyProductAdmin(admin.ModelAdmin):
    form = ToyProductForm
    list_display = ["name", "category", "price", "image_preview"]

    def image_preview(self, obj):
        return (
            f'<img src="{obj.image_url}" width="60" height="60" style="object-fit:cover;border-radius:6px;">'
            if obj.image_url else "No Image"
        )
    image_preview.allow_tags = True
    image_preview.short_description = "Image"

    def save_model(self, request, obj, form, change):
        uploaded_file = form.cleaned_data.get("image_file")
        if uploaded_file:
            obj.image_file = uploaded_file
        super().save_model(request, obj, form, change)



# ======================================================
# REGISTER OTHER MODELS
# ======================================================
admin.site.register(CustomUser)
admin.site.register(CartItem)
admin.site.register(WishlistItem)
admin.site.register(Review)
admin.site.register(OrderItem)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'full_name', 'order_status', 'paid', 'created_at')
    list_filter = ('order_status', 'paid', 'created_at')
    list_editable = ('order_status', 'paid')
