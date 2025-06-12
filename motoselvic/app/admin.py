from django.contrib import admin
from .models import *

# Inline for Order Items
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1

# Order Admin
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'status', 'total_amount', 'order_date')
    list_filter = ('status', 'order_date')
    search_fields = ('user__username', 'status')
    inlines = [OrderItemInline]
    readonly_fields = ('order_date',)



# Product Admin
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'subcategory', 'price', 'stock')
    search_fields = ('name',)
    list_filter = ('category', 'subcategory', 'price')
    filter_horizontal = ('sizes', 'colors')  # 👈 This enables a better multi-select UI

# Product Image Admin
@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ('product', 'image', 'color', 'size', 'is_main')
    search_fields = ('product__name', 'color__name', 'size__size')
    list_filter = ('color', 'size', 'is_main')


# Category Admin
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

# SubCategory Admin
@admin.register(SubCategory)
class SubCategoryAdmin(admin.ModelAdmin):
    list_display = ('sub_category_name', 'category')
    search_fields = ('sub_category_name', 'category__name')

# CartItem Inline Admin
class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 1  # This defines how many empty forms will be shown by default

# Cart Admin
@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user',)
    search_fields = ('user__username',)
    inlines = [CartItemInline]  # Add CartItem inline form here

# CartItem Admin
@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('product', 'cart', 'quantity')

# OrderItem Admin
@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('product_name', 'order', 'quantity', 'price')

    def product_name(self, obj):
        return obj.product.name  # Assuming 'product' is a ForeignKey to Product model

    product_name.admin_order_field = 'product__name'  # Allow sorting by product name

# Company Admin
@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

# Bike Admin
@admin.register(Bike)
class BikeAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'series_name', 'model_name', 'cc', 'super_bike')
    search_fields = ('company_name__name', 'model_name', 'series_name')
    list_filter = ('company_name', 'super_bike')

# Manufacturer Admin
@admin.register(Manufacturer)
class ManufacturerAdmin(admin.ModelAdmin):
    list_display = ('manufacturer_name',)
    search_fields = ('manufacturer_name',)

# Product Size Admin
@admin.register(ProductSize)
class ProductSizeAdmin(admin.ModelAdmin):
    list_display = ('size',)
    search_fields = ('size',)

# Product Color Admin
@admin.register(ProductColor)
class ProductColorAdmin(admin.ModelAdmin):
    list_display = ('name', 'hex_code')
    search_fields = ('name',)

# User Profile Admin
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone_number')
    search_fields = ('user__username',)

# Site Logo and Name Admin
@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display = ('name', 'logo')
