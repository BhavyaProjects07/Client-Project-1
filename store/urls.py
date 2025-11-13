from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path
from store import views

urlpatterns = [
    path('', views.home, name='home'),
    path('request-otp/', views.request_otp_view, name='request_otp'),
    path('verify-otp/', views.verify_otp_view, name='verify_otp'),  # Ensure this is correctly defined
    path('logout/', views.logout_view, name='logout'),
    path('cart/', views.view_cart, name='view_cart'),
    path('cart/add/<str:product_type>/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('update-cart/<int:item_id>/', views.update_cart_quantity, name='update_cart_quantity'),
    path('wishlist/', views.view_wishlist, name='view_wishlist'),
    path('wishlist/add/<str:product_type>/<int:product_id>/', views.add_to_wishlist, name='add_to_wishlist'),
    path('wishlist/remove/<int:item_id>/', views.remove_from_wishlist, name='remove_from_wishlist'),
    path('checkout/', views.checkout_view, name='checkout'),
    path('order-success/', views.order_success_view, name='order_success'),
    path('payment/', views.payment_view, name='payment'),
    path('my-orders/', views.my_orders_view, name='my_orders'),
    path('admin-dashboard/', views.admin_dashboard_view, name='admin_dashboard'),
path('admin-dashboard/order/<int:order_id>/', views.admin_order_detail, name='admin_order_detail'),
path('admin-dashboard/order/<int:order_id>/update-status/', views.update_order_status, name='update_order_status'),
path('admin-dashboard/order/<int:order_id>/update-payment/', views.update_payment_status, name='update_payment_status'),

    path('track-order/<int:order_id>/', views.track_order_view, name='track_order'),
    path('order/<int:order_id>/<str:product_type>/<int:product_id>/review/', views.submit_review, name='submit_review'),

    path('product/<str:product_type>/<int:product_id>/reviews/', views.product_reviews_view, name='product_reviews'),

    path('women/product/<int:product_id>/', views.women_product_detail, name='women_product_detail'),
    path('buy-now/<str:product_type>/<int:product_id>/', views.buy_now, name='buy_now'),
    path('toy/product/<int:product_id>/', views.toy_product_detail, name='toy_product_detail'),
    path('electronic/product/<int:product_id>/', views.electronic_product_detail, name='electronic_product_detail'),

]

# if settings.DEBUG:
#     urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
