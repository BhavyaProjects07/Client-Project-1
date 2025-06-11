from django.contrib import admin
from store.models import Product, CustomUser , CartItem , WishlistItem , Order, OrderItem , Review# Import only the models

# Register your models here.
admin.site.register(Product)
admin.site.register(CustomUser)
admin.site.register(CartItem)
admin.site.register(WishlistItem)  
admin.site.register(Review)
admin.site.register(OrderItem)

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'full_name', 'order_status', 'created_at']
    list_editable = ['order_status']
    list_filter = ['order_status', 'created_at']