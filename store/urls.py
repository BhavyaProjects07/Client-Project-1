from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path

from store import views   # loads from views/__init__.py


urlpatterns = [

    # ================================
    # HOME PAGE
    # ================================
    path('', views.home, name='home'),


    # ================================
    # AUTHENTICATION + OTP SYSTEM
    # ================================
    path('request-otp/', views.request_otp_view, name='request_otp'),
    path('verify-otp/', views.verify_otp_view, name='verify_otp'),
    path('logout/', views.logout_view, name='logout'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('new-password/', views.new_password, name='new_password'),


    # ================================
    # CART SYSTEM (Dynamic)
    # ================================
    path('cart/', views.view_cart, name='view_cart'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/add/<int:product_id>/<int:variation_id>/', views.add_to_cart, name='add_to_cart_variation'),
    path('cart/remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('update-cart/<int:item_id>/', views.update_cart_quantity, name='update_cart_quantity'),


    # ================================
    # WISHLIST (Dynamic)
    # ================================
    path('wishlist/', views.view_wishlist, name='view_wishlist'),
    path('wishlist/add/<int:product_id>/', views.add_to_wishlist, name='add_to_wishlist'),
    path('wishlist/remove/<int:item_id>/', views.remove_from_wishlist, name='remove_from_wishlist'),


    # ================================
    # CHECKOUT + PAYMENT
    # ================================
    path('checkout/', views.checkout_view, name='checkout'),
    path('payment/', views.payment_view, name='payment'),
    path('order-success/', views.order_success_view, name='order_success'),
    path('buy-now/<int:product_id>/', views.buy_now, name='buy_now'),
    path('buy-now/<int:product_id>/<int:variation_id>/', views.buy_now, name='buy_now_variation'),


    # ================================
    # ORDERS (CUSTOMER)
    # ================================
    path('my-orders/', views.my_orders_view, name='my_orders'),
    path('track-order/<int:order_id>/', views.track_order_view, name='track_order'),
    path('order/<int:order_id>/cancel/', views.cancel_order, name='cancel_order'),


    # ================================
    # REVIEWS (Dynamic)
    # ================================
    path('order/<int:order_id>/product/<int:product_id>/review/',
         views.submit_review,
         name='submit_review'),

    path('product/<int:product_id>/reviews/',
         views.product_reviews_view,
         name='product_reviews'),


    # ================================
    # PRODUCT DETAIL (Dynamic)
    # ================================
    path('product/<int:product_id>/<slug:slug>/', views.product_detail, name='product_detail'),
    path('product/<int:product_id>/', views.product_detail, name='product_detail_no_slug'),
    path("category/<slug:slug>/", views.category_products, name="category_products"),


    # ================================
    # ADMIN PANEL (Custom)
    # ================================
    path('admin-dashboard/', views.admin_dashboard_view, name='admin_dashboard'),
    path('admin-dashboard/order/<int:order_id>/', views.admin_order_detail, name='admin_order_detail'),

    path('admin-dashboard/order/<int:order_id>/update-status/',
     views.admin_update_order_status, name='admin_update_order_status'),

     path('admin-dashboard/order/<int:order_id>/update-payment/',
     views.admin_update_payment_status, name='admin_update_payment_status'),


    path('admin-verify/', views.admin_verify, name='admin_verify'),
    path('clear-admin-verify/', views.clear_admin_verify, name='clear_admin_verify'),


    # ================================
    # DELIVERY PANEL
    # ================================
    path('delivery-dashboard/', views.delivery_dashboard, name='delivery_dashboard'),
    path('delivery/order/<int:order_id>/', views.delivery_order_detail, name='delivery_order_detail'),
    path('delivery-verify/', views.delivery_verify, name='delivery_verify'),
    path('delivery/order/<int:order_id>/update-status/', 
     views.delivery_update_order_status, name='delivery_update_order_status'),

     path('delivery/order/<int:order_id>/update-payment/', 
     views.delivery_update_payment_status, name='delivery_update_payment_status'),

    path('delivery-profile/', views.delivery_profile, name='delivery_profile'),
    path('delivery-history/', views.delivery_order_history, name='delivery_order_history'),


    # ================================
    # MISC
    # ================================
    path('contact/', views.contact, name='contact'),
]

# MEDIA FILES (dev mode)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
