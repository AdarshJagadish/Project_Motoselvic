from django.contrib import admin
from .models import Order, OrderItem, Address, PaymentMethod, Product, Cart, CartItem

# Order Admin
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1  # Number of empty rows for adding new items.

class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'status', 'total_amount', 'order_date')
    list_filter = ('status', 'order_date')
    search_fields = ('user__username', 'status')
    inlines = [OrderItemInline]

# Address Admin
class AddressAdmin(admin.ModelAdmin):
    list_display = ('user', 'city', 'state', 'postal_code', 'country')
    search_fields = ('user__username', 'city', 'state')

# Payment Method Admin
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ('user', 'type', 'details')
    search_fields = ('user__username', 'type')

# Product Admin
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'stock')
    search_fields = ('name',)
    list_filter = ('price',)

# Cart Admin
class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 1  # Number of empty rows for adding new items.

class CartAdmin(admin.ModelAdmin):
    list_display = ('user',)
    search_fields = ('user__username',)
    inlines = [CartItemInline]

# Registering all models
admin.site.register(Order, OrderAdmin)
admin.site.register(Address, AddressAdmin)
admin.site.register(PaymentMethod, PaymentMethodAdmin)
admin.site.register(Product, ProductAdmin)
admin.site.register(Cart, CartAdmin)