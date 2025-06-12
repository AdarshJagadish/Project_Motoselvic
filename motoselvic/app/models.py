from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Q
from django.db.models.signals import post_save
from django.core.exceptions import ObjectDoesNotExist
from django.dispatch import receiver

# Logo Model
class Site(models.Model):
    name = models.CharField(max_length=25, default='Motoselvic', editable=True)
    logo = models.ImageField(blank=True, null=True, upload_to='images/Our_Logo/')

# Order Model
class Order(models.Model):
    STATUS_CHOICES = [
    ('Pending', 'Pending'),
    ('Confirmed', 'Confirmed'),
    ('Shipped', 'Shipped'),
    ('Out for Delivery', 'Out for Delivery'),
    ('Delivered', 'Delivered'),
    ('Cancelled', 'Cancelled'),
]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    order_date = models.DateTimeField(auto_now_add=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    payment_method = models.CharField(max_length=50, choices=[('COD', 'Cash on Delivery'), ('RAZORPAY', 'Razorpay')], default='COD')
    is_paid = models.BooleanField(default=False)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)

    # Use the saved address
    address = models.ForeignKey('Address', on_delete=models.SET_NULL, null=True, blank=True)

    # Store snapshot of full address at the time of order (in case address is changed later)
    shipping_full_name = models.CharField(max_length=100)
    shipping_email = models.EmailField()
    shipping_phone = models.CharField(max_length=15, blank=True, null=True)
    shipping_address_line = models.TextField()
    shipping_landmark = models.CharField(max_length=100, blank=True, null=True)
    shipping_city = models.CharField(max_length=100)
    shipping_state = models.CharField(max_length=100)
    shipping_postal_code = models.CharField(max_length=20)
    shipping_country = models.CharField(max_length=100)

    def __str__(self):
        return f"Order #{self.id} by {self.user.username}"

    def calculate_total_amount(self):
        self.total_amount = sum(item.quantity * item.price for item in self.items.all())
        self.save()



# Order Item Model
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('Product', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.product.name} ({self.quantity})"
    

class Payment(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Success', 'Success'),
        ('Failed', 'Failed'),
    ]
    order = models.OneToOneField(Order, on_delete=models.CASCADE)
    payment_id = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(auto_now_add=True)
    payment_method = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')

    def __str__(self):
        return f"Payment {self.payment_id} for Order {self.order.id}"


#User Profile
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=15, blank=True)
    profile_picture = models.ImageField(upload_to='images/users/profile_pics/', blank=True, null=True)
    is_active = models.BooleanField(default=True)  # New field to track activation status

    def __str__(self):
        return self.user.username

    @property
    def full_name(self):
        return f"{self.user.first_name} {self.user.last_name}"
    
# User Model for AI/ML Integration
class Users(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='ai_profile')
    vector_data = models.TextField(null=True, blank=True)  # JSON serialized vector

    def __str__(self):
        return self.user.username


# Bike Companies
class Company(models.Model):
    name = models.CharField(max_length=100, blank=True, unique=True)
    logo = models.ImageField(upload_to='images/Our_Logos/', blank=True, null=True)

    def __str__(self):
        return self.name

# Bike Models
class Bike(models.Model):
    company_name = models.ForeignKey(Company, to_field='name', on_delete=models.CASCADE)
    series_name = models.CharField(max_length=50, blank=True, null=True)
    model_name = models.CharField(max_length=30)
    cc = models.IntegerField()
    image = models.ImageField(upload_to='images/bike_images/', blank=True, null=True)
    super_bike = models.BooleanField(default=False, editable=False)

    def save(self, *args, **kwargs):
        self.super_bike = self.cc > 800
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.company_name.name} {self.series_name or ''} {self.model_name}".strip()

# Category Model
class Category(models.Model):
    name = models.CharField(max_length=100, blank=False, unique=True)

    def __str__(self):
        return self.name

# SubCategory Model
class SubCategory(models.Model):
    category = models.ForeignKey(Category, to_field='name', on_delete=models.CASCADE, related_name='subcategories')
    sub_category_name = models.CharField(max_length=100, unique=True, blank=False)

    def __str__(self):
        return self.sub_category_name

# Product Manufacture
class Manufacturer(models.Model):
    manufacturer_name = models.CharField(max_length=100, blank=False, default='Motoselvic', unique=True)

    def __str__(self):
        return self.manufacturer_name
    
# Size
class ProductSize(models.Model):
    size = models.CharField(max_length=10, unique=True)

    def __str__(self):
        return self.size

# Color
class ProductColor(models.Model):
    name = models.CharField(max_length=30, unique=True)
    hex_code = models.CharField(max_length=7, help_text="Hex color code like #000000", default='#000000', blank=True)

    def __str__(self):
        return self.name

# Product Model
class Product(models.Model):
    name = models.CharField(max_length=150)
    description = models.TextField(max_length=500, default='No description', editable=True)
    manufacturer = models.ForeignKey(Manufacturer, related_name='manufacturer', on_delete=models.CASCADE)
    bike_company = models.ForeignKey(Company, on_delete=models.CASCADE, blank=True, null=True, related_name='product')
    bike_model = models.ForeignKey(Bike, on_delete=models.CASCADE, blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    subcategory = models.ForeignKey(SubCategory, on_delete=models.CASCADE, blank=True, null=True)
    sizes = models.ManyToManyField(ProductSize, blank=True, related_name='products')
    colors = models.ManyToManyField(ProductColor, blank=True, related_name='products')
    mrp = models.DecimalField(max_digits=10, decimal_places=2, blank=False, null=False)
    price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    stock = models.PositiveIntegerField()
    is_trending = models.BooleanField(default=False)
    is_newarrived = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    rating=models.FloatField(default=0)
    vector_data=models.TextField(null=True)

    def save(self, *args, **kwargs):
        if self.price is None:
            self.price = self.mrp
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
    
    def get_main_image(self):
        main_img = self.images.filter(is_main=True).first()
        if main_img:
            return main_img
        return self.images.first()  # fallback to any image
    
    



# Product Image Model
class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='images/products/product_images/')
    color = models.ForeignKey(ProductColor, on_delete=models.SET_NULL, null=True, blank=True)
    size = models.ForeignKey(ProductSize, on_delete=models.SET_NULL, null=True, blank=True)
    is_main = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.product.name} Image - {self.color.name if self.color else 'No Color'}"
   



# Cart Model
class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return f"Cart - {self.user.username}"

    @property
    def total_amount(self):
        return sum(item.get_subtotal() for item in self.items.all())


# CartItem Model
class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    size = models.ForeignKey(ProductSize, null=True, blank=True, on_delete=models.SET_NULL)
    color = models.ForeignKey(ProductColor, null=True, blank=True, on_delete=models.SET_NULL)
    quantity = models.PositiveIntegerField(default=1)

    def get_subtotal(self):
        return self.product.price * self.quantity

    def __str__(self):
        return f"{self.product.name} (x{self.quantity})"


class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    phone = models.CharField(max_length=15)
    email = models.EmailField()
    address_line = models.TextField()
    landmark = models.CharField(max_length=100, blank=True, null=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)
    is_default = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user'], condition=Q(is_default=True), name='unique_default_address_per_user')
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name}, {self.city} - {self.pincode}"
    

    
# models.py

class ViewHistory(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    user = models.ForeignKey(Users, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-timestamp']
        unique_together = ('product', 'user')  # Prevent duplicate records (optional)

class SearchHistory(models.Model):
    query = models.CharField(max_length=255)
    user = models.ForeignKey(Users, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)

class Review(models.Model):
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    description = models.TextField()
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')  # Adjust if custom user
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)  # optional, for edits tracking

    def __str__(self):
        return f"{self.user} review for {self.product} - {self.rating} stars"