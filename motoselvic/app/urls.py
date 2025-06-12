from django.urls import path
from .views import *

urlpatterns = [
    # Home
    path('', home, name='home'),

    # Authentication
    path('signup/', signup_view, name='signup'),
    path('signin/', signin_view, name='signin'),
    path('forgot-password/', forgot_password, name='forgot_password'),
    path('reset-password/<uidb64>/<token>/', reset_password, name='reset_password'),
    path('logout/', logout_view, name='logout'),

    # Cart
    path('cart/', cart_view, name='cart'),  # Corrected name
    path('product/<int:product_id>/add_to_cart/', add_to_cart, name='add_to_cart'),
    path('cart/update/<int:item_id>/', update_cart_item, name='update_cart_item'),
    path('cart/remove/<int:item_id>/', remove_from_cart, name='remove_from_cart'),

    # Checkout
    path('checkout/', checkout_view, name='checkout'),
    path('payment/verify/', razorpay_payment_verify, name='razorpay_payment_verify'),
    path('payment/success/<int:order_id>/', payment_success, name='payment_success'),

    # Order
    path('orders/<int:order_id>/cancel/', cancel_order, name='cancel_order'),
    path('order/success/<int:order_id>/', order_success, name='order_success'),
    path('order/<int:order_id>/', order_detail_view, name='order_detail'),

    # Products
    path('products/', product_list, name='product_list'),
    path('product/<int:product_id>/', product_detail, name='product_detail'),

    #Review
    path('product/<int:product_id>/add_review/', addReview, name='add_review'),

    # User Dashboard (Profile)
    path('dashboard/', user_dashboard, name='user_dashboard'),
    path('dashboard/edit-profile/', edit_profile, name='edit_profile'),
    path('dashboard/add-address/', add_address, name='add_address'),
    path('dashboard/edit-address/<int:address_id>/', edit_address, name='edit_address'),
    path('dashboard/delete-address/<int:address_id>/', delete_address, name='delete_address'),
    path('dashboard/set-default-address/<int:address_id>/', set_default_address, name='set_default_address'),

    # Search
    path('search/', search_product, name='search_product'),

    # Contact
    path('contact', contact, name='contact'),

   # Admin Dashboard and Products
    path('admin_panel/admin_dashboard/', admin_dashboard, name='admin_dashboard'),
    # Product Management (Main)
    path('admin_panel/admin_products/', admin_manage_products, name='admin_product_management'),
    path('admin_panel/admin_products/add/', admin_add_product, name='admin_add_product'),
    path('admin_panel/admin_products/edit/<int:product_id>/', admin_edit_product, name='admin_edit_product'),
    path('admin_panel/admin_products/delete/<int:product_id>/', admin_delete_product, name='admin_delete_product'),
    path('admin_panel/get-subcategories/<int:category_id>/', get_subcategories, name='get_subcategories'),

    # Product Image Management
    path('admin_panel/admin_products/<int:product_id>/images/', admin_manage_product_images, name='admin_manage_product_images'),
    path('admin_panel/admin_products/<int:product_id>/images/add/', admin_add_product_image, name='admin_add_product_image'),
    path('admin_panel/admin_products/image/<int:image_id>/delete/', admin_delete_product_image, name='admin_delete_product_image'),
    path('admin_panel/admin_products/image/<int:image_id>/set-main/', admin_set_main_product_image, name='admin_set_main_image'),

    # Companies
    path('admin_panel/admin_companies/', admin_manage_companies, name='admin_manage_companies'),
    path('admin_panel/admin_companies/add/', admin_add_company, name='admin_add_company'),
    path('admin_panel/admin_companies/edit/<int:company_id>/', admin_edit_company, name='admin_edit_company'),
    path('admin_panel/admin_companies/delete/<int:company_id>/', admin_delete_company, name='admin_delete_company'),

    # Bike Models
    path('admin_panel/admin_bike_models/', admin_manage_bike_models, name='admin_manage_bike_models'),
    path('admin_panel/admin_bike_models/add/', admin_add_bike_model, name='admin_add_bike_model'),
    path('admin_panel/admin_bike_models/edit/<int:bike_id>/', admin_edit_bike_model, name='admin_edit_bike_model'),
    path('admin_panel/admin_bike_models/delete/<int:bike_id>/', admin_delete_bike_model, name='admin_delete_bike_model'),

    # Categories & SubCategories
    path('admin_panel/admin_categories/', admin_manage_categories, name='admin_manage_categories'),
    path('admin_panel/admin_categories/add/', admin_add_category, name='admin_add_category'),
    path('admin_panel/admin_categories/edit/<int:category_id>/', admin_edit_category, name='admin_edit_category'),
    path('admin_panel/admin_categories/delete/<int:category_id>/', admin_delete_category, name='admin_delete_category'),

    path('admin_panel/admin_categories/<int:category_id>/subcategories/', admin_manage_subcategories, name='admin_manage_subcategories'),
    path('admin_panel/admin_categories/<int:category_id>/subcategories/add/', admin_add_subcategory, name='admin_add_subcategory'),
    path('admin_panel/admin_subcategories/edit/<int:subcategory_id>/', admin_edit_subcategory, name='admin_edit_subcategory'),
    path('admin_panel/admin_subcategories/delete/<int:subcategory_id>/', admin_delete_subcategory, name='admin_delete_subcategory'),

    # Manufacturers
    path('admin_panel/admin_manufacturers/', admin_manage_manufacturers, name='admin_manage_manufacturers'),
    path('admin_panel/admin_manufacturers/add/', admin_add_manufacturer, name='admin_add_manufacturer'),
    path('admin_panel/admin_manufacturers/edit/<int:manufacturer_id>/', admin_edit_manufacturer, name='admin_edit_manufacturer'),
    path('admin_panel/admin_manufacturers/delete/<int:manufacturer_id>/', admin_delete_manufacturer, name='admin_delete_manufacturer'),

    # Orders
    path('admin_panel/admin_orders/', admin_manage_orders, name='admin_manage_orders'),
    path('admin_panel/admin_orders/<int:order_id>/', admin_order_detail, name='admin_order_detail'),
    path('admin_panel/admin_orders/<int:order_id>/delete/', admin_delete_order, name='admin_delete_order'),

    # Site Settings
    path('admin_panel/admin_site_settings/', admin_site_settings, name='admin_site_settings'),

    # User Management
    path('admin_panel/admin_users/', admin_manage_users, name='admin_manage_users'),
    path('admin_panel/admin_users/toggle/<int:user_id>/', toggle_user_activation, name='toggle_user_activation'),
    path('admin_panel/admin_users/delete/<int:user_id>/', delete_user, name='delete_user'),

]
