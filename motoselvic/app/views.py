from django.shortcuts import render, redirect,get_object_or_404
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.core.mail import send_mail
from django.contrib import messages
from .models import *




def home_view(request):
    return render(request, 'home.html')

# Signup View
def signup_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists!")
            return render(request, 'auth.html')
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already exists!")
            return render(request, 'auth.html')
        
        user = User.objects.create_user(username=username, email=email, password=password)
        user.save()
        messages.success(request, "Signup successful! Please log in.")
        return redirect('signin')
    return render(request, 'auth.html')

# Signin View
def signin_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        try:
            user = User.objects.get(email=email)
            user_auth = authenticate(request, username=user.username, password=password)
            if user_auth is not None:
                login(request, user_auth)
                messages.success(request, "Login successful!")
                return redirect('home')
            else:
                return HttpResponse(f"Debug: Login failed. Auth: {user_auth}, Username: {user.username}, Password: {password}")
        except User.DoesNotExist:
            return HttpResponse("Debug: User does not exist.")
    return render(request, 'auth.html')

# Forgot Password View
def forgot_password(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            user = User.objects.get(email=email)
            # Generate a password reset link (example logic, secure with token in production)
            reset_link = f"http://yourdomain.com/reset-password/{user.id}/"
            send_mail(
                'Password Reset Request',
                f'Click the following link to reset your password: {reset_link}',
                'admin@yourdomain.com',
                [email],
                fail_silently=False,
            )
            messages.success(request, "Password reset link sent to your email.")
            return render(request, 'forgotpassword.html')
        except User.DoesNotExist:
            messages.error(request, "No account found with this email!")
            return render(request, 'forgotpassword.html')
    return render(request, 'forgotpassword.html')

# Logout View
@login_required(login_url='signin')
def logout_view(request):
    logout(request)
    messages.success(request, "You have successfully logged out!")
    return redirect('signin')  # Redirect to the signin page after logout












# User Dashboard
def user_dashboard(request):
    orders = Order.objects.filter(user=request.user)
    addresses = Address.objects.filter(user=request.user)
    payments = PaymentMethod.objects.filter(user=request.user)
    return render(request, 'profile.html', {'orders': orders, 'addresses': addresses, 'payments': payments})

# Orders Management
def order_list(request):
    orders = Order.objects.filter(user=request.user)
    return render(request, 'order-details.html', {'orders': orders})

def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'order-details.html', {'order': order})

def cancel_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    if order.status == "Pending":
        order.status = "Cancelled"
        order.save()
        messages.success(request, "Order cancelled successfully!")
    return redirect('order_detail', order_id=order.id)

# Address Management
@login_required(login_url='signin')  # Redirect to login if not authenticated
def address_list(request):
    user = request.user  # Get the logged-in user
    addresses = Address.objects.filter(user=user)  # Fetch user's addresses
    return render(request, 'edit-address.html', {'addresses': addresses})

def edit_address(request, address_id):
    address = get_object_or_404(Address, id=address_id, user=request.user)
    if request.method == 'POST':
        address.address_line = request.POST.get('address_line')
        address.city = request.POST.get('city')
        address.state = request.POST.get('state')
        address.postal_code = request.POST.get('postal_code')
        address.country = request.POST.get('country')
        address.save()
        messages.success(request, "Address updated successfully!")
        return redirect('address_list')
    return render(request, 'edit-address.html', {'address': address})

# Payment Methods
def payment_methods(request):
    payments = PaymentMethod.objects.filter(user=request.user)
    return render(request, 'add-payment.html', {'payments': payments})

def add_payment_method(request):
    if request.method == 'POST':
        PaymentMethod.objects.create(
            user=request.user,
            type=request.POST.get('payment_type'),
            details=request.POST.get('payment_details')
        )
        messages.success(request, "Payment method added successfully!")
        return redirect('payment_methods')
    return render(request, 'add-payment.html')

def remove_payment_method(request, payment_id):
    payment = get_object_or_404(PaymentMethod, id=payment_id, user=request.user)
    payment.delete()
    messages.success(request, "Payment method removed successfully!")
    return redirect('payment_methods')

# Cart Management
def cart_view(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    return render(request, 'cart.html', {'cart': cart})

def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
    cart_item.quantity += 1
    cart_item.save()
    return redirect('cart_view')

def remove_from_cart(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    cart_item.delete()
    return redirect('cart_view')
