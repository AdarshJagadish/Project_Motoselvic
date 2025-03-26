from django.urls import path
from .views import *

urlpatterns = [
    # Home
    path('', home_view, name='home'),  # This will fix the 404 error

    # Authentication
    path('signup/', signup_view, name='signup'),
    path('signin/', signin_view, name='signin'),
    path('forgot-password/', forgot_password, name='forgot_password'),
    path('logout/', logout_view, name='logout'),


    # User Dashboard
    path('dashboard/', user_dashboard, name='dashboard'),

    # Orders
    path('orders/', order_list, name='order_list'),
    path('orders/<int:order_id>/', order_detail, name='order_detail'),
    path('orders/<int:order_id>/cancel/', cancel_order, name='cancel_order'),

    # Addresses
    path('addresses/', address_list, name='address_list'),
    path('addresses/<int:address_id>/edit/', edit_address, name='edit_address'),

    # Payment Methods
    path('payments/', payment_methods, name='payment_methods'),
    path('payments/add/', add_payment_method, name='add_payment_method'),
    path('payments/<int:payment_id>/remove/', remove_payment_method, name='remove_payment_method'),

    # Cart
    path('cart/', cart_view, name='cart_view'),
    path('cart/add/<int:product_id>/', add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:item_id>/', remove_from_cart, name='remove_from_cart'),
]
