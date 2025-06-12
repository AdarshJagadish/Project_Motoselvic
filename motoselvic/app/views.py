from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.template.loader import render_to_string
from django.shortcuts import render, redirect, get_object_or_404,reverse
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required,user_passes_test
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.core.files.storage import FileSystemStorage 
from django.core.exceptions import ValidationError
from django.core.serializers import serialize
from django.core.mail import send_mail
from django.db.models import Q,Count
from .models import Product
from django.contrib import messages
from django.conf import settings
from .models import *
import random,datetime,json
from django.utils.timezone import now, timedelta
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.safestring import mark_safe
from django.urls import reverse
from django.core.paginator import Paginator
from django.db.models import Avg
from django.db import transaction

from sklearn.metrics.pairwise import cosine_similarity
from django.views.decorators.csrf import csrf_exempt
import razorpay
from django.views.decorators.http import require_POST


from .recommendation import *
from .vectorize import vectorize_product_with_reviews,vectorize_user_with_search,pd


def home(request):
    companies = Company.objects.all()
    categories = Category.objects.all()
    logo = Site.objects.first()

    all_active_products = Product.objects.filter(is_active=True)
    new_arrivals = all_active_products.filter(is_newarrived=True)[:5]
    trending_products = all_active_products.filter(is_trending=True)[:15]

    selected_brand = request.GET.get("brand")

    filtered_products = []
    related_products = []
    random_bike = None
    products = []
    recommended_products = []

    if selected_brand:
        filtered_products = list(
            Product.objects.filter(bike_company__name__iexact=selected_brand, is_active=True)
            .order_by('?')[:5]
        )
        products = []  # No general products when filtered by brand
    else:
        bikes_with_products = Bike.objects.filter(product__isnull=False).distinct()
        random_bike = bikes_with_products.order_by('?').first() if bikes_with_products.exists() else None
        if random_bike:
            related_products = Product.objects.filter(bike_model=random_bike, is_active=True)[:5]
        products = all_active_products[:5]

    if request.user.is_authenticated:
        try:
            custom_user = Users.objects.get(user=request.user)
            recommended_products = get_recommended_products(custom_user.vector_data, all_active_products, top_n=5)
        except Users.DoesNotExist:
            recommended_products = []

    context = {
        'companies': companies,
        'categories': categories,
        'products': products,
        'selected_brand': selected_brand,
        'filtered_products': filtered_products,
        'related_products': related_products,
        'logo': logo,
        'new_arrivals': new_arrivals,
        'trending_products': trending_products,
        'recommended_products': recommended_products,
    }

    return render(request, 'home/home.html', context)


def signup_view(request):
    if request.method == 'POST':
        print("POST data:", request.POST)  # Debug line
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if not username or not email or not password:
            print("Missing required signup fields")

        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already taken.')
            return redirect('signup')

        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered.')
            return redirect('signup')

        user = User.objects.create_user(username=username, email=email, password=password)
        user.save()

        # Signal will create UserProfile and Users (with vector_data)
        login(request, user)
        messages.success(request, 'Account created successfully!')
        return redirect('home')

    return render(request, 'auth/auth.html')


def signin_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        remember_me = request.POST.get('remember_me')
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            messages.error(request, "No user with that email!", extra_tags='login')
            return redirect('signin')
        # Check if user is inactive BEFORE authenticate
        if not user.userprofile.is_active:
            contact_url = reverse('contact')  # Make sure 'contact' is a valid URL name
            messages.error(
                request,
                mark_safe(
                    f"This account was <strong>deactivated</strong> by you or by the Admin. "
                    f"If this was not done by you, please <a href='{contact_url}' class='alert-link'>contact our support team</a>."
                ),
                extra_tags='login'
            )
            return redirect('signin')
        user_auth = authenticate(request, username=user.username, password=password)

        if user_auth:
            login(request, user_auth)
            # Remember Me Logic
            request.session.set_expiry(0 if not remember_me else 1209600)  # 0 = browser close, else 2 weeks
            # Role-based Redirect
            if user_auth.is_superuser:
                request.session['admin'] = user.username
                return redirect('admin_dashboard')
            else:
                request.session['user'] = user.username
                return redirect('home')
        else:
            messages.error(request, "Invalid credentials!", extra_tags='login')
            return redirect('signin')
    return render(request, 'auth/auth.html')


def forgot_password(request):
    if request.method == 'POST':
        email = request.POST.get('email')

        try:
            user = User.objects.get(email=email)
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            reset_link = request.build_absolute_uri(f"/reset-password/{uid}/{token}/")

            subject = 'Reset Your Motoselvic Password'
            message = render_to_string('emails/password_reset_email.html', {
                'user': user,
                'reset_link': reset_link,
            })

            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [email], fail_silently=False)
            messages.success(request, "Password reset link sent to your email.")
        except User.DoesNotExist:
            messages.error(request, "No account found with this email.")

        return redirect('forgot_password')

    return render(request, 'auth/forgotpassword.html', {'validlink': True})


def reset_password(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            password1 = request.POST.get('new_password1')
            password2 = request.POST.get('new_password2')

            if password1 != password2:
                messages.error(request, "Passwords do not match.")
            else:
                user.set_password(password1)
                user.save()
                messages.success(request, "Password successfully reset. Please log in.")
                return redirect('signin')

        return render(request, 'auth/reset_password.html', {'validlink': True})
    else:
        return render(request, 'auth/reset_password.html', {'validlink': False})

@login_required(login_url='signin')
def logout_view(request):
    logout(request)
    messages.info(request, "You have successfully logged out!", extra_tags='logout')
    return redirect('signin')


def product_list(request):
    products = Product.objects.all().select_related('category').prefetch_related('sizes', 'colors')
    logo = Site.objects.first()

    # Get the filters from the GET parameters
    category_id = request.GET.get('category')
    size_filter = request.GET.get('size')
    color_filter = request.GET.get('color')
    query = request.GET.get('query') or request.GET.get('q', '')
    query = query.strip()

    # Save search query for AI-based recommendation (if applicable)
    if query and request.user.is_authenticated:
        try:
            custom_user = request.user.users
            SearchHistory.objects.create(user=custom_user, query=query)
        except Users.DoesNotExist:
            pass  # If custom Users model is not found, skip logging

    # Apply category filter
    if category_id and category_id.isdigit():
        category_id = int(category_id)
        try:
            category = Category.objects.get(id=category_id)
            products = products.filter(category=category)
        except ObjectDoesNotExist:
            category_id = None

    if size_filter:
        products = products.filter(sizes__size=size_filter)

    if color_filter:
        products = products.filter(colors__name=color_filter)

    if query:
        products = products.filter(name__icontains=query)

    # Get dropdown values
    sizes = ProductSize.objects.all()
    colors = ProductColor.objects.all()
    categories = Category.objects.all()

    context = {
        'products': products,
        'sizes': sizes,
        'colors': colors,
        'categories': categories,
        'logo': logo,
        'query': query,
        'selected_category': category_id,
        'selected_size': size_filter,
        'selected_color': color_filter,
    }

    return render(request, 'product/product_list.html', context)

def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_active=True)
    logo = Site.objects.first()
    main_image = product.get_main_image()
    other_images = product.images.exclude(id=main_image.id) if main_image else []
    reviews = product.reviews.all().order_by('-created_at')
    avg_rating = reviews.aggregate(avg=Avg('rating'))['avg'] or 0

    # ----------- ViewHistory Save and Vector Update -----------
    if request.user.is_authenticated:
        try:
            custom_user = Users.objects.get(user=request.user)
        except Users.DoesNotExist:
            custom_user = None

        if custom_user:
            # Save view history
            ViewHistory.objects.update_or_create(
                user=custom_user,
                product=product,
                defaults={'timestamp': now()}
            )

            # Get viewed products and search queries
            viewed_names = ViewHistory.objects.filter(user=custom_user).values_list('product__name', flat=True)
            search_queries = SearchHistory.objects.filter(user=custom_user).values_list('query', flat=True)

            # Create DataFrame for vectorization
            data = [{
                'user_id': custom_user.user.id,
                'product': ', '.join(viewed_names),
                'search': ', '.join(search_queries)
            }]
            df = pd.DataFrame(data)

            # Generate vector and save
            vectors = vectorize_user_with_search(df)
            custom_user.vector_data = json.dumps(vectors[0].tolist())
            custom_user.save()

    # ----------- AI Similar Products -----------
    current_vector = json.loads(product.vector_data) if product.vector_data else None
    similar_products = []
    if current_vector:
        all_products = Product.objects.exclude(id=product.id).filter(vector_data__isnull=False, is_active=True)
        similarities = []
        for other in all_products:
            try:
                other_vector = json.loads(other.vector_data)
                sim = cosine_similarity([current_vector], [other_vector])[0][0]
                similarities.append((other, sim))
            except Exception:
                continue

        similarities.sort(key=lambda x: x[1], reverse=True)
        similar_products = [prod for prod, _ in similarities[:8]]

    return render(request, 'product/product_detail.html', {
        'product': product,
        'main_image': main_image,
        'other_images': other_images,
        'reviews': reviews,
        'avg_rating': avg_rating,
        'colors': product.colors.all(),
        'sizes': product.sizes.all(),
        'logo': logo,
        'similar_products': similar_products,
    })

@login_required
def addReview(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    user = request.user  # This is the Django User instance

    # Optional: check if user profile exists if needed, but use request.user in queries
    try:
        user_profile = Users.objects.get(user=user)
    except Users.DoesNotExist:
        messages.error(request, "User profile not found.")
        return redirect('product_detail', product_id=product_id)

    if request.method == "POST":
        rating = request.POST.get("rating")
        description = request.POST.get("description")

        # Use the Django User instance here
        if Review.objects.filter(user=user, product=product).exists():
            messages.error(request, "You have already reviewed this product.")
            return redirect('product_detail', product_id=product_id)

        Review.objects.create(
            user=user,  # Use User instance here
            product=product,
            rating=rating,
            description=description,
        )
        messages.success(request, "Your review has been submitted successfully.")
        return redirect('product_detail', product_id=product_id)

    return redirect('product_detail', product_id=product_id)


def search_product(request):
    query = request.GET.get('q', '').strip()

    if query:
        # Save search query to history if user is authenticated
        if request.user.is_authenticated:
            try:
                custom_user = request.user.users  # Your custom Users model
                SearchHistory.objects.create(user=custom_user, query=query)
            except Users.DoesNotExist:
                pass  # Skip if custom user model is missing

        # Search by product name or category
        products = Product.objects.filter(
            Q(name__icontains=query) | Q(category__name__icontains=query)
        )

        return render(request, 'product/product_list.html', {
            'products': products if products.exists() else [],
            'no_product_found': not products.exists(),
            'query': query
        })

    return redirect('home')



@login_required(login_url='signin')
def cart_view(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    cart_items = CartItem.objects.filter(cart=cart)
    logo = Site.objects.first()
    total = sum(item.product.price * item.quantity for item in cart_items)

    return render(request, 'cart/cart.html', {
        'cart_items': cart_items,
        'total': total,
        'logo': logo,
    })


@login_required
def add_to_cart(request, product_id):
    if request.method == 'POST':
        product = get_object_or_404(Product, id=product_id)
        quantity = int(request.POST.get('quantity', 1))

        # Look up size/color objects by name (or None)
        size_name = request.POST.get('size')
        color_name = request.POST.get('color')

        size_obj = None
        if size_name:
            size_obj = ProductSize.objects.filter(size=size_name).first()

        color_obj = None
        if color_name:
            color_obj = ProductColor.objects.filter(name=color_name).first()

        # Get or create the user's cart
        cart, _ = Cart.objects.get_or_create(user=request.user)

        # Check if requested quantity exceeds available stock
        if product.stock < quantity:
            messages.error(request, f"Sorry, only {product.stock} units of {product.name} are available.")
            return redirect('product_detail', product_id=product_id)  # Or wherever the product detail page is

        # Create or update the CartItem
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            size=size_obj,
            color=color_obj,
            defaults={'quantity': quantity}
        )

        if not created:
            # Check if adding to existing quantity exceeds stock
            if product.stock < cart_item.quantity + quantity:
                available_stock = product.stock - cart_item.quantity
                if available_stock <= 0:
                     messages.error(request, f"Not enough stock available for {product.name}.")
                else:
                    messages.error(request, f"Only {available_stock} more units of {product.name} can be added to your cart.")
                return redirect('cart')

            cart_item.quantity += quantity
            cart_item.save()
            messages.info(request, f'Updated quantity of {product.name} in your cart.')
        else:
            messages.success(request, f'Added {product.name} to your cart.')

        return redirect('cart')  # Redirect to cart page
    else:
        return redirect('cart')


@login_required
def update_cart_item(request, item_id):
    if request.method == 'POST':
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
        action = request.POST.get('action')
        product = cart_item.product  # Get the product

        if action == 'increment':
            # Check if incrementing exceeds stock
            if product.stock <= cart_item.quantity:
                messages.error(request, f"Maximum available quantity reached for {product.name}.")
                return redirect('cart')

            cart_item.quantity += 1
        elif action == 'decrement':
            cart_item.quantity = max(1, cart_item.quantity - 1)  # Ensure quantity doesn't go below 1
        else:
            try:
                new_quantity = int(request.POST.get('quantity', cart_item.quantity))
                if new_quantity < 1:
                    new_quantity = 1
                # Validate against stock
                if product.stock < new_quantity:
                    messages.error(request, f"Only {product.stock} units of {product.name} are available.")
                    return redirect('cart')
                cart_item.quantity = new_quantity
            except ValueError:
                pass  # Handle invalid quantity input (e.g., non-integer)

        cart_item.save()

        return redirect('cart')

    return redirect('cart')


@login_required
def remove_from_cart(request, item_id):
    if request.method == 'POST':
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
        cart_item.delete()

    return redirect('cart')


@login_required
def checkout_view(request):
    logo = Site.objects.first()
    categories = Category.objects.all()
    delivery_charge = 40

    try:
        cart = Cart.objects.get(user=request.user)
    except Cart.DoesNotExist:
        messages.error(request, "Your cart is empty.")
        return redirect('cart')

    cart_items = cart.items.select_related('product').all()
    if not cart_items:
        messages.error(request, "Your cart is empty.")
        return redirect('cart')

    # **NEW: Stock Validation Before Checkout**
    for item in cart_items:
        if item.product.stock < item.quantity:
            messages.error(request, f"Sorry, {item.product.name} is now out of stock or has insufficient quantity. Please update your cart.")
            return redirect('cart')

    for item in cart_items:
        item.total_price = item.product.price * item.quantity

    subtotal = sum(item.total_price for item in cart_items)
    grand_total = subtotal + delivery_charge

    saved_addresses = Address.objects.filter(user=request.user)

    if request.method == 'POST':
        use_saved = request.POST.get('use_saved_address') == 'on'
        selected_address_id = request.POST.get('saved_address')
        is_default = request.POST.get('is_default') == 'on'

        payment_method = request.POST.get('payment_method')  # NEW: Get payment method

        if use_saved and selected_address_id:
            try:
                address = Address.objects.get(id=selected_address_id, user=request.user)
            except Address.DoesNotExist:
                messages.error(request, "Selected address not found.")
                return redirect('checkout')

            full_name = f"{address.first_name} {address.last_name}"
            email = address.email
            phone = address.phone
            address_line = address.address_line
            landmark = address.landmark
            city = address.city
            state = address.state
            postal_code = address.pincode
            country = address.country

        else:
            first_name = request.POST.get('first_name')
            last_name = request.POST.get('last_name')
            phone = request.POST.get('phone')
            email = request.POST.get('email')
            address_line = request.POST.get('address_line')
            landmark = request.POST.get('landmark')
            city = request.POST.get('city')
            state = request.POST.get('state')
            postal_code = request.POST.get('postal_code')
            country = request.POST.get('country')

            if not all([first_name, last_name, phone, email, address_line, city, state, postal_code, country]):
                messages.error(request, "Please fill in all required address fields.")
                return redirect('checkout')

            address = Address(
                user=request.user,
                first_name=first_name,
                last_name=last_name,
                phone=phone,
                email=email,
                address_line=address_line,
                landmark=landmark,
                city=city,
                state=state,
                country=country,
                pincode=postal_code,
                is_default=is_default
            )
            address.save()

            full_name = f"{first_name} {last_name}"

        # --------- Payment method logic ----------
        if payment_method == 'COD':
            # **Deduct Stock on Order Placement**
            with transaction.atomic():
                try:
                    for item in cart_items:
                        product = item.product
                        # Refresh the product instance to get the most up-to-date stock
                        product = Product.objects.select_for_update().get(pk=product.pk)
                        if product.stock < item.quantity:
                            messages.error(request, f"Sorry, {item.product.name} is now out of stock or has insufficient quantity. Please update your cart.")
                            return redirect('cart')
                        product.stock -= item.quantity
                        product.save()

                    order = Order.objects.create(
                        user=request.user,
                        total_amount=grand_total,
                        shipping_full_name=full_name,
                        shipping_email=email,
                        shipping_phone=phone,
                        shipping_address_line=address_line,
                        shipping_landmark=landmark,
                        shipping_city=city,
                        shipping_state=state,
                        shipping_postal_code=postal_code,
                        shipping_country=country,
                        payment_method='COD',
                        status='Pending',
                        is_paid=False,
                        address=address,  # Save FK to Address object or None
                    )
                    for item in cart_items:
                        OrderItem.objects.create(
                            order=order,
                            product=item.product,
                            quantity=item.quantity,
                            price=item.product.price,
                        )
                    cart.items.all().delete()
                    messages.success(request, "Order placed successfully with Cash on Delivery!")
                    return redirect('order_success', order_id=order.id)

                except Exception as e:
                    messages.error(request, f"An error occurred during order processing: {e}")
                    return redirect('checkout')

        elif payment_method == 'RAZORPAY':
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

            # Format amount like template: two decimals, then convert to integer paise
            amount_str = f"{grand_total:.2f}"  # e.g. '123.45'
            amount_int = int(float(amount_str) * 100)  # e.g. 12345 paise

            # Create Razorpay order
            razorpay_order = client.order.create({
                "amount": amount_int,  # amount in paise
                "currency": "INR",
                "payment_capture": "1"
            })

            # Temporarily save order details in session or context
            request.session['order_data'] = {
                'user_id': request.user.id,
                'total_amount': float(grand_total),  # convert Decimal to float
                'full_name': full_name,
                'email': email,
                'address_line': address_line,
                'city': city,
                'state': state,
                'postal_code': postal_code,
                'country': country,
                'phone': phone,
                'landmark': landmark,
                'cart_items': [
                    (item.product.id, item.quantity, float(item.product.price))  # convert Decimal to float
                    for item in cart_items
                ],
                'razorpay_order_id': razorpay_order['id'],
                'address_id': address.id if address else None,
            }


            context = {
                'razorpay_order_id': razorpay_order['id'],
                'razorpay_merchant_key': settings.RAZORPAY_KEY_ID,
                'amount': grand_total,
                'currency': 'INR',
                'logo': logo,
                'categories': categories,
            }
            return render(request, 'payment/razorpay_checkout.html', context)


        else:
            messages.error(request, "Please select a valid payment method.")
            return redirect('checkout')

    default_address = saved_addresses.filter(is_default=True).first()

    return render(request, 'checkout/checkout.html', {
        'cart_items': cart_items,
        'cart_total': grand_total,
        'subtotal': subtotal,
        'delivery_charge': delivery_charge,
        'logo': logo,
        'categories': categories,
        'saved_addresses': saved_addresses,
        'default_address': default_address,
    })
            

@csrf_exempt
@login_required
def razorpay_payment_verify(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

        params_dict = {
            'razorpay_order_id': data.get('razorpay_order_id'),
            'razorpay_payment_id': data.get('razorpay_payment_id'),
            'razorpay_signature': data.get('razorpay_signature')
        }

        try:
            # Verify the payment signature to ensure payment integrity
            client.utility.verify_payment_signature(params_dict)

            order_data = request.session.get('order_data')
            if not order_data:
                return JsonResponse({'status': 'fail', 'message': 'Session expired. Please try again.'})

            user = request.user

            # Create order instance with snapshot of shipping info
            order = Order.objects.create(
                user=user,
                total_amount=order_data['total_amount'],
                shipping_full_name=order_data['full_name'],
                shipping_email=order_data['email'],
                shipping_phone=order_data['phone'],
                shipping_address_line=order_data['address_line'],
                shipping_landmark=order_data.get('landmark', ''),
                shipping_city=order_data['city'],
                shipping_state=order_data['state'],
                shipping_postal_code=order_data['postal_code'],
                shipping_country=order_data['country'],
                payment_method='RAZORPAY',
                status='Pending',
                is_paid=True,
                razorpay_payment_id=data.get('razorpay_payment_id'),
                address=None,  # Since order snapshot used, no FK needed here
            )

            # Create order items from saved cart items data
            for product_id, quantity, price in order_data['cart_items']:
                product = Product.objects.get(id=product_id)
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=quantity,
                    price=price,
                )

            # Clear user's cart items properly
            try:
                cart = Cart.objects.get(user=user)
                cart.items.all().delete()
            except Cart.DoesNotExist:
                pass

            # Clear order_data from session
            del request.session['order_data']

            # Return success with URL to payment success page
            return JsonResponse({
                'status': 'success',
                'redirect_url': redirect('payment_success', order_id=order.id).url
            })

        except razorpay.errors.SignatureVerificationError:
            return JsonResponse({'status': 'fail', 'message': 'Payment verification failed.'})

        except Exception as e:
            # Log error in real app
            return JsonResponse({'status': 'fail', 'message': f'An error occurred: {str(e)}'})

    return JsonResponse({'status': 'fail', 'message': 'Invalid request method.'})

@csrf_exempt
@login_required
def razorpay_payment_success(request):
    if request.method == "POST":
        data = request.POST

        # Razorpay payment details
        razorpay_payment_id = data.get('razorpay_payment_id')
        razorpay_order_id = data.get('razorpay_order_id')
        razorpay_signature = data.get('razorpay_signature')

        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

        # Verify signature
        params_dict = {
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature
        }

        try:
            client.utility.verify_payment_signature(params_dict)
        except razorpay.errors.SignatureVerificationError:
            return JsonResponse({'error': 'Payment verification failed'}, status=400)

        # Fetch order data from session
        order_data = request.session.get('order_data')
        if not order_data or order_data.get('razorpay_order_id') != razorpay_order_id:
            return JsonResponse({'error': 'Order data not found or mismatch'}, status=400)

        # Create Order
        user = request.user
        order = Order.objects.create(
            user=user,
            total_amount=order_data['total_amount'],
            shipping_full_name=order_data['full_name'],
            shipping_email=order_data['email'],
            shipping_phone=order_data['phone'],
            shipping_address_line=order_data['address_line'],
            shipping_landmark=order_data.get('landmark', ''),
            shipping_city=order_data['city'],
            shipping_state=order_data['state'],
            shipping_postal_code=order_data['postal_code'],
            shipping_country=order_data['country'],
            payment_method='RAZORPAY',
            status='Paid',
            is_paid=True,
            razorpay_payment_id=razorpay_payment_id,
            address=Address.objects.filter(
                user=user,
                address_line=order_data['address_line'],
                city=order_data['city'],
                postal_code=order_data['postal_code']
            ).first(),  # or None
        )

        # Create OrderItems
        for product_id, quantity, price in order_data['cart_items']:
            product = Product.objects.get(id=product_id)
            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=quantity,
                price=price,
            )

        # Clear Cart
        Cart.objects.filter(user=user).delete()

        # Clean session
        del request.session['order_data']

        return JsonResponse({'success': True, 'order_id': order.id})

    return JsonResponse({'error': 'Invalid request method'}, status=405)
razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

@login_required
def payment_success(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    method = request.GET.get('method', order.payment_method or 'Unknown')
    payment_id = request.GET.get('payment_id', f'{method}-{order.id}')

    with transaction.atomic():
        # Deduct stock here for Razorpay
        for item in order.items.all():

            product = Product.objects.select_for_update().get(pk=item.product.pk)
            if product.stock < item.quantity:
                messages.error(request, f"{product.name} is unexpectedly out of stock. Please contact support.")
                return redirect('cart')
            product.stock -= item.quantity
            product.save()

        payment, created = Payment.objects.get_or_create(
            order=order,
            defaults={
                'payment_method': method,
                'amount': order.total_amount,
                'payment_id': payment_id,
                'status': 'Success',
                'payment_date': timezone.now(),
            }
        )

        if not created:
            payment.payment_method = method
            payment.amount = order.total_amount
            payment.payment_id = payment_id
            payment.status = 'Success'
            payment.payment_date = timezone.now()
            payment.save()

        order.is_paid = True
        order.status = 'Pending'
        order.save()

    return redirect('order_success', order_id=order.id)

@login_required
def order_success(request, order_id):
    logo = Site.objects.first()
    categories = Category.objects.all()

    order = get_object_or_404(Order, id=order_id, user=request.user)

    if order.payment_method == 'COD' and not order.is_paid:
        with transaction.atomic():
            for item in order.items.select_related('product'):
                product = Product.objects.select_for_update().get(pk=item.product.pk)
                if product.stock < item.quantity:
                    messages.error(request, f"{product.name} is out of stock. Contact support.")
                    return redirect('home')
                product.stock -= item.quantity
                product.save()

            order.is_paid = True
            order.status = 'Pending'
            order.save()

            Payment.objects.create(
                order=order,
                payment_method='COD',
                amount=order.total_amount,
                status='Success',
                payment_id=f"COD-{order.id}",
                payment_date=timezone.now(),
            )
            messages.success(request, f"Order #{order.id} placed successfully!")
    else:
        order.status = 'Pending'
        order.save()

    return render(request, 'checkout/order_success.html', {
        'order': order,
        'order_items': order.items.select_related('product').all(),  # ✅ PASS THIS
        'logo': logo,
        'categories': categories,
    })


@require_POST
@login_required
def cancel_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    if order.status in ['Cancelled', 'Delivered']:
        messages.warning(request, "This order cannot be cancelled.")
        return redirect('order_detail', order_id=order.id)

    with transaction.atomic():
        order.status = 'Cancelled'
        order.save()

        for item in order.items.select_related('product'):
            product = Product.objects.select_for_update().get(pk=item.product.pk)
            product.stock += item.quantity
            product.save()

    return redirect('order_detail', order_id=order.id)

@login_required
def order_detail_view(request, order_id):
    logo = Site.objects.first()
    order = get_object_or_404(Order, id=order_id, user=request.user)
    order_items = OrderItem.objects.filter(order=order).select_related('product')

    statuses = ['Pending', 'Confirmed', 'Shipped', 'Out for Delivery', 'Delivered', 'Cancelled']
    current_index = statuses.index(order.status) if order.status in statuses else -1
    max_index = len(statuses) - 1

    # Calculate progress percentage for the progress bar
    progress_percent = (current_index / max_index) * 100 if max_index > 0 and current_index >= 0 else 0

    context = {
        'logo': logo,
        'order': order,
        'order_items': order_items,
        'statuses': statuses,
        'current_index': current_index,
        'progress_percent': progress_percent,
    }
    return render(request, 'dashboard/order_detail.html', context)

@login_required
def user_dashboard(request):
    logo = Site.objects.first()
    profile = get_object_or_404(UserProfile, user=request.user)
    addresses = Address.objects.filter(user=request.user)
    orders = Order.objects.filter(user=request.user).order_by('-order_date')
    return render(request, 'dashboard/profile.html', {
        'profile': profile,
        'orders': orders,
        'logo':logo,
        'addresses': addresses,
    })

@login_required
def add_address(request):
    logo = Site.objects.first()
    if request.method == 'POST':
        data = request.POST
        is_default = data.get('is_default') == 'on'

        if is_default:
            Address.objects.filter(user=request.user, is_default=True).update(is_default=False)

        Address.objects.create(
            user=request.user,
            first_name=data['first_name'],
            last_name=data['last_name'],
            phone=data['phone'],
            email=data['email'],
            address_line=data['address_line'],
            landmark=data.get('landmark'),
            city=data['city'],
            state=data['state'],
            country=data['country'],
            pincode=data['pincode'],
            is_default=is_default,
        )
        messages.success(request, "Address added successfully!")
        return redirect('user_dashboard')

    return render(request, 'dashboard/address_form.html', {
        'title': 'Add New Address',
        'logo': 'logo',
        'button_label': 'Save Address',
        'address': {}
    })

@login_required
def edit_address(request, address_id):
    address = get_object_or_404(Address, id=address_id, user=request.user)
    logo = Site.objects.first()

    if request.method == 'POST':
        data = request.POST
        is_default = data.get('is_default') == 'on'

        if is_default and not address.is_default:
            Address.objects.filter(user=request.user, is_default=True).update(is_default=False)

        address.first_name = data['first_name']
        address.last_name = data['last_name']
        address.phone = data['phone']
        address.email = data['email']
        address.address_line = data['address_line']
        address.landmark = data.get('landmark')
        address.city = data['city']
        address.state = data['state']
        address.country = data['country']
        address.pincode = data['pincode']
        address.is_default = is_default
        address.save()

        messages.success(request, "Address updated successfully!")
        return redirect('user_dashboard')

    return render(request, 'dashboard/address_form.html', {
        'title': 'Edit Address',
        'logo': 'logo',
        'button_label': 'Update Address',
        'address': address
    })

@login_required
def delete_address(request, address_id):
    address = get_object_or_404(Address, id=address_id, user=request.user)
    address.delete()
    messages.success(request, 'Address deleted.')
    return redirect('edit_profile')

@login_required
def set_default_address(request, address_id):
    Address.objects.filter(user=request.user, is_default=True).update(is_default=False)
    Address.objects.filter(id=address_id, user=request.user).update(is_default=True)
    messages.success(request, 'Default address updated.')
    return redirect('user_dashboard')

@login_required
def edit_profile(request):
    logo = Site.objects.first()
    profile = get_object_or_404(UserProfile, user=request.user)
    addresses = Address.objects.filter(user=request.user)

    if request.method == 'POST':
        phone_number = request.POST.get('phone_number')
        profile_picture = request.FILES.get('profile_picture')
        full_name = request.POST.get('full_name')  # only if you add this field in form

        if full_name:
            profile.full_name = full_name
        if phone_number:
            profile.phone_number = phone_number
        if profile_picture:
            profile.profile_picture = profile_picture

        profile.save()
        messages.success(request, "Profile updated successfully!")
        return redirect('user_dashboard')  # No context dict here

    return render(request, 'dashboard/edit_profile.html', {
        'logo': logo,
        'profile': profile,
        'addresses': addresses
    })


def contact(req):
    cat=Category.objects.all()
    if req.method == "POST":
        name = req.POST["name"]
        email = req.POST["email"]
        message = req.POST["message"]

        send_mail(
            subject=f"New Contact Form Submission from {name}",
            message=f"Name: {name}\nEmail: {email}\n\nMessage:\n{message}",
            from_email=email,
            recipient_list=["contact.adarshjagadish@gmail.com"], 
            fail_silently=True,
        )

        messages.success(req, "Your message has been sent successfully!")
        return redirect(contact )  
    return render(req,'contact/contact.html',{"cat":cat})


# # # # # # # # # # # # # # # # # # #--------------------------------------------------------- # # # # # # # # # # # # # # # # # # #
#                                    ********************** ADMIN PANEL **********************                                     #
# # # # # # # # # # # # # # # # # # #--------------------------------------------------------- # # # # # # # # # # # # # # # # # # #


def is_admin(user):
    return user.is_superuser

@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    total_products = Product.objects.count()
    total_orders = Order.objects.count()
    total_users = User.objects.count()
    pending_orders = Order.objects.filter(status='pending').count()

    last_7_days = [now().date() - timedelta(days=i) for i in reversed(range(7))]
    chart_labels = [d.strftime("%a") for d in last_7_days]
    chart_data = [
        Order.objects.filter(order_date__date=d).count()
        for d in last_7_days
    ]

    recent_orders = Order.objects.select_related('user').order_by('-order_date')[:5]

    context = {
        'total_products': total_products,
        'total_orders': total_orders,
        'total_users': total_users,
        'pending_orders': pending_orders,
        'chart_labels': json.dumps(chart_labels),
        'chart_data': json.dumps(chart_data),
        'recent_orders': recent_orders,
    }

    return render(request, 'admin_panel/dashboard.html', context)

def admin_manage_products(request):
    products = Product.objects.all()
    categories = Category.objects.all()

    print("GET parameters:", request.GET.dict())  # Debug: print all GET params

    selected_category = request.GET.get('category')
    status = request.GET.get('status')
    search_query = request.GET.get('search')

    print(f"Raw Search query: {search_query}")

    # Strip whitespace from search query to avoid search mismatches
    if search_query:
        search_query = search_query.strip()
        print(f"Stripped Search query: '{search_query}'")

    # Filter by category
    if selected_category and selected_category.isdigit():
        products = products.filter(subcategory__category__id=int(selected_category))
        print(f"Filtered by category id: {selected_category}")

    # Filter by status
    if status == 'active':
        products = products.filter(is_active=True)
        print("Filtered by status: active")
    elif status == 'inactive':
        products = products.filter(is_active=False)
        print("Filtered by status: inactive")

    # Extended search: name, description, manufacturer
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(manufacturer__manufacturer_name__icontains=search_query)
        )
        print(f"Filtered products count after search: {products.count()}")

        for p in products:
            print(f"Matched Product: {p.name}, Manufacturer: {p.manufacturer.manufacturer_name}")

    # Important: add order_by to avoid pagination warning
    products = products.order_by('id')

    # Pagination
    paginator = Paginator(products, 10)
    page = request.GET.get('page')
    products = paginator.get_page(page)

    context = {
        'products': products,
        'categories': categories,
        'selected_category': selected_category,
        'status': status,
        'search_query': search_query,
    }

    return render(request, 'admin_panel/product/manage_products.html', context)

# Add New Product View
@user_passes_test(lambda u: u.is_superuser)
def admin_add_product(request):
    manufacturers = Manufacturer.objects.all()
    categories = Category.objects.all()
    subcategories = SubCategory.objects.select_related('category').all()
    bike_companies = Company.objects.all()
    bike_models = Bike.objects.all()
    colors = ProductColor.objects.all()
    sizes = ProductSize.objects.all()

    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        price = float(request.POST.get('price', 0))
        mrp = float(request.POST.get('mrp', 0))
        stock = int(request.POST.get('stock', 0))
        is_active = request.POST.get('is_active') == 'on'
        is_trending = request.POST.get('is_trending') == 'on'
        is_newarrived = request.POST.get('is_newarrived') == 'on'

        manufacturer_id = request.POST.get('manufacturer')
        category_id = request.POST.get('category')
        subcategory_id = request.POST.get('subcategory')
        bike_company_name = request.POST.get('bike_company') or None  # company name string
        bike_model_id = request.POST.get('bike_model') or None

        product = Product.objects.create(
            name=name,
            description=description,
            price=price,
            mrp=mrp,
            stock=stock,
            is_active=is_active,
            is_trending=is_trending,
            is_newarrived=is_newarrived,
            manufacturer_id=manufacturer_id,
            category_id=category_id,
            subcategory_id=subcategory_id,
            bike_company=bike_company_name,  # assign by company name string
            bike_model_id=bike_model_id,
        )

        # Handle ManyToMany colors and sizes
        color_ids = request.POST.getlist('colors')
        size_ids = request.POST.getlist('sizes')
        product.colors.set(color_ids)
        product.sizes.set(size_ids)

        messages.success(request, f'Product "{product.name}" added successfully.')
        return redirect('admin_product_management')

    context = {
        'manufacturers': manufacturers,
        'categories': categories,
        'subcategories': subcategories,
        'bike_companies': bike_companies,
        'bike_models': bike_models,
        'colors': colors,
        'sizes': sizes,
    }
    return render(request, 'admin_panel/product/add_product.html', context)

@user_passes_test(lambda u: u.is_superuser)
def get_subcategories(request, category_id):
    # Filter on the related Category's id, not category_id field
    subs = SubCategory.objects.filter(category__id=category_id) \
                              .values('id', 'sub_category_name')
    return JsonResponse({'subcategories': list(subs)})

def admin_edit_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    colors = ProductColor.objects.all()
    sizes = ProductSize.objects.all()
    manufacturers = Manufacturer.objects.all()
    categories = Category.objects.all()
    subcategories = SubCategory.objects.select_related('category').all()
    bike_companies = Company.objects.all()
    bike_models = Bike.objects.all()

    if request.method == 'POST':
        # Basic fields
        product.name = request.POST.get('name', product.name)
        product.description = request.POST.get('description', product.description)
        product.price = request.POST.get('price', product.price)
        product.mrp = request.POST.get('mrp', product.mrp)
        product.stock = request.POST.get('quantity', product.stock)
        product.is_active = True if request.POST.get('is_active') == 'on' else False
        product.is_trending = True if request.POST.get('is_trending') == 'on' else False
        product.is_newarrived = True if request.POST.get('is_newarrived') == 'on' else False

        # ForeignKey fields
        product.manufacturer_id = request.POST.get('manufacturer', product.manufacturer_id)
        product.category_id = request.POST.get('category', product.category_id)
        product.subcategory_id = request.POST.get('subcategory', product.subcategory_id)
        bike_company_id = request.POST.get('bike_company')
        product.bike_company_id = bike_company_id if bike_company_id else None
        bike_model_id = request.POST.get('bike_model')
        product.bike_model_id = bike_model_id if bike_model_id else None

        product.save()

        # ManyToMany: Colors
        selected_color_ids = request.POST.getlist('colors')
        product.colors.set(selected_color_ids)

        # ManyToMany: Sizes
        selected_size_ids = request.POST.getlist('sizes')
        product.sizes.set(selected_size_ids)

        messages.success(request, f'Product "{product.name}" updated successfully.')
        return redirect('admin_edit_product', product_id=product.id)

    context = {
        'product': product,
        'categories': categories,
        'subcategories': subcategories,
        'manufacturers': manufacturers,
        'colors': colors,
        'sizes': sizes,
        'bike_companies': bike_companies,
        'bike_models': bike_models,
    }
    return render(request, 'admin_panel/product/edit_product.html', context)

# Delete Product View
@user_passes_test(lambda u: u.is_superuser)
def admin_delete_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    product.delete()

    messages.success(request, "Product deleted successfully!")
    return redirect('admin_product_management')  # Redirect to product list

@user_passes_test(lambda u: u.is_superuser)
def admin_add_product_image(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if request.method == 'POST':
        images = request.FILES.getlist('images')  # Changed from get() to getlist()
        is_main = request.POST.get('is_main') == 'on'

        for index, image in enumerate(images):
            # Set the first image as main only if 'is_main' was checked
            make_main = is_main and index == 0
            if make_main:
                ProductImage.objects.filter(product=product, is_main=True).update(is_main=False)

            ProductImage.objects.create(product=product, image=image, is_main=make_main)

        messages.success(request, f"{len(images)} image(s) uploaded successfully.")
        return redirect('admin_manage_product_images', product_id=product.id)

    return render(request, 'admin_panel/product/add_product_images.html', {'product': product})

@user_passes_test(lambda u: u.is_superuser)
def admin_manage_product_images(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    images = ProductImage.objects.filter(product=product)
    return render(request, 'admin_panel/product/manage_product_images.html', {
        'product': product,
        'images': images
    })

@user_passes_test(lambda u: u.is_superuser)
def admin_delete_product_image(request, image_id):
    image = get_object_or_404(ProductImage, id=image_id)
    product_id = image.product.id
    image.image.delete()
    image.delete()
    messages.success(request, "Product image deleted.")
    return redirect('admin_manage_product_images', product_id=product_id)

@user_passes_test(lambda u: u.is_superuser)
def admin_set_main_product_image(request, image_id):
    image = get_object_or_404(ProductImage, id=image_id)
    product = image.product
    ProductImage.objects.filter(product=product).update(is_main=False)
    image.is_main = True
    image.save()
    messages.success(request, "Main image updated.")
    return redirect('admin_manage_product_images', product_id=product.id)


# Admin Bike & Model Management
# --- Company Management ---
@user_passes_test(lambda u: u.is_superuser)
def admin_manage_companies(request):
    companies = Company.objects.all()
    return render(request, 'admin_panel/bike/manage_companies.html', {'companies': companies})

@user_passes_test(lambda u: u.is_superuser)
def admin_add_company(request):
    if request.method == 'POST':
        name = request.POST.get('name').strip()
        logo = request.FILES.get('logo')

        if not name:
            messages.error(request, 'Company name is required.')
            return redirect('admin_add_company')

        if Company.objects.filter(name=name).exists():
            messages.error(request, 'Company with this name already exists.')
            return redirect('admin_add_company')

        company = Company(name=name)
        if logo:
            company.logo = logo
        company.save()
        messages.success(request, f'Company "{name}" added successfully.')
        return redirect('admin_manage_companies')

    return render(request, 'admin_panel/bike/edit_company.html', {'company': None})

@user_passes_test(lambda u: u.is_superuser)
def admin_edit_company(request, company_id):
    company = get_object_or_404(Company, id=company_id)

    if request.method == 'POST':
        name = request.POST.get('name').strip()
        logo = request.FILES.get('logo')

        if not name:
            messages.error(request, 'Company name is required.')
            return redirect('admin_edit_company', company_id=company_id)

        if Company.objects.filter(name=name).exclude(id=company_id).exists():
            messages.error(request, 'Another company with this name already exists.')
            return redirect('admin_edit_company', company_id=company_id)

        company.name = name
        if logo:
            company.logo = logo
        company.save()
        messages.success(request, f'Company "{name}" updated successfully.')
        return redirect('admin_manage_companies')

    return render(request, 'admin_panel/bike/edit_company.html', {'company': company})

@user_passes_test(lambda u: u.is_superuser)
def admin_delete_company(request, company_id):
    company = get_object_or_404(Company, id=company_id)
    if request.method == 'POST' or request.method == 'GET':
        company.delete()
        messages.success(request, f'Company "{company.name}" deleted successfully.')
        return redirect('admin_manage_companies')


# --- Bike Model Management ---
@user_passes_test(lambda u: u.is_superuser)
def admin_manage_bike_models(request):
    bikes = Bike.objects.select_related('company_name').all()
    return render(request, 'admin_panel/bike/manage_bike_models.html', {'bikes': bikes})

@user_passes_test(lambda u: u.is_superuser)
def admin_add_bike_model(request):
    companies = Company.objects.all()
    if request.method == 'POST':
        company_id = request.POST.get('company_name')
        series_name = request.POST.get('series_name', '').strip()
        model_name = request.POST.get('model_name').strip()
        cc = request.POST.get('cc')
        image = request.FILES.get('image')

        if not company_id or not model_name or not cc:
            messages.error(request, 'Company, model name and CC are required.')
            return redirect('admin_add_bike_model')

        try:
            cc = int(cc)
            if cc < 0:
                raise ValueError()
        except ValueError:
            messages.error(request, 'CC must be a positive integer.')
            return redirect('admin_add_bike_model')

        company = get_object_or_404(Company, id=company_id)
        bike = Bike(company_name=company, series_name=series_name or None,
                    model_name=model_name, cc=cc)

        if image:
            bike.image = image
        bike.save()
        messages.success(request, f'Bike model "{model_name}" added successfully.')
        return redirect('admin_manage_bike_models')

    return render(request, 'admin_panel/bike/edit_bike_model.html', {'bike': None, 'companies': companies})

@user_passes_test(lambda u: u.is_superuser)
def admin_edit_bike_model(request, bike_id):
    bike = get_object_or_404(Bike, id=bike_id)
    companies = Company.objects.all()

    if request.method == 'POST':
        company_id = request.POST.get('company_name')
        series_name = request.POST.get('series_name', '').strip()
        model_name = request.POST.get('model_name').strip()
        cc = request.POST.get('cc')
        image = request.FILES.get('image')

        if not company_id or not model_name or not cc:
            messages.error(request, 'Company, model name and CC are required.')
            return redirect('admin_edit_bike_model', bike_id=bike_id)

        try:
            cc = int(cc)
            if cc < 0:
                raise ValueError()
        except ValueError:
            messages.error(request, 'CC must be a positive integer.')
            return redirect('admin_edit_bike_model', bike_id=bike_id)

        company = get_object_or_404(Company, id=company_id)

        bike.company_name = company
        bike.series_name = series_name or None
        bike.model_name = model_name
        bike.cc = cc
        if image:
            bike.image = image
        bike.save()
        messages.success(request, f'Bike model "{model_name}" updated successfully.')
        return redirect('admin_manage_bike_models')

    return render(request, 'admin_panel/bike/edit_bike_model.html', {'bike': bike, 'companies': companies})

@user_passes_test(lambda u: u.is_superuser)
def admin_delete_bike_model(request, bike_id):
    bike = get_object_or_404(Bike, id=bike_id)
    if request.method == 'POST' or request.method == 'GET':
        bike.delete()
        messages.success(request, f'Bike model "{bike.model_name}" deleted successfully.')
        return redirect('admin_manage_bike_models')
    

# Admin Category & Manufacturer Management
# --- Category Management ---
@user_passes_test(lambda u: u.is_superuser)
def admin_manage_categories(request):
    categories = Category.objects.all()
    return render(request, 'admin_panel/category/manage_categories.html', {'categories': categories})

@user_passes_test(lambda u: u.is_superuser)
def admin_add_category(request):
    if request.method == 'POST':
        name = request.POST.get('name').strip()
        if not name:
            messages.error(request, 'Category name is required.')
            return redirect('admin_add_category')
        if Category.objects.filter(name=name).exists():
            messages.error(request, 'Category with this name already exists.')
            return redirect('admin_add_category')
        Category.objects.create(name=name)
        messages.success(request, f'Category "{name}" added successfully.')
        return redirect('admin_manage_categories')
    return render(request, 'admin_panel/category/edit_category.html', {'category': None})

@user_passes_test(lambda u: u.is_superuser)
def admin_edit_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    if request.method == 'POST':
        name = request.POST.get('name').strip()
        if not name:
            messages.error(request, 'Category name is required.')
            return redirect('admin_edit_category', category_id=category_id)
        if Category.objects.filter(name=name).exclude(id=category_id).exists():
            messages.error(request, 'Another category with this name already exists.')
            return redirect('admin_edit_category', category_id=category_id)
        category.name = name
        category.save()
        messages.success(request, f'Category "{name}" updated successfully.')
        return redirect('admin_manage_categories')
    return render(request, 'admin_panel/category/edit_category.html', {'category': category})

@user_passes_test(lambda u: u.is_superuser)
def admin_delete_category(request, category_id):
    if request.method == 'POST':
        category = get_object_or_404(Category, id=category_id)
        category.delete()
        messages.success(request, f'Category "{category.name}" deleted successfully.')
    return redirect('admin_manage_categories')


# --- SubCategory Management ---
@user_passes_test(lambda u: u.is_superuser)
def admin_manage_subcategories(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    subcategories = category.subcategories.all()
    return render(request, 'admin_panel/category/manage_subcategories.html', {'category': category, 'subcategories': subcategories})

@user_passes_test(lambda u: u.is_superuser)
def admin_add_subcategory(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    if request.method == 'POST':
        name = request.POST.get('sub_category_name').strip()
        if not name:
            messages.error(request, 'SubCategory name is required.')
            return redirect('admin_add_subcategory', category_id=category_id)
        if SubCategory.objects.filter(sub_category_name=name).exists():
            messages.error(request, 'SubCategory with this name already exists.')
            return redirect('admin_add_subcategory', category_id=category_id)
        SubCategory.objects.create(category=category, sub_category_name=name)
        messages.success(request, f'SubCategory "{name}" added to "{category.name}".')
        return redirect('admin_manage_subcategories', category_id=category_id)
    return render(request, 'admin_panel/category/edit_subcategory.html', {'subcategory': None, 'category': category})

@user_passes_test(lambda u: u.is_superuser)
def admin_edit_subcategory(request, subcategory_id):
    subcategory = get_object_or_404(SubCategory, id=subcategory_id)
    if request.method == 'POST':
        name = request.POST.get('sub_category_name').strip()
        if not name:
            messages.error(request, 'SubCategory name is required.')
            return redirect('admin_edit_subcategory', subcategory_id=subcategory_id)
        if SubCategory.objects.filter(sub_category_name=name).exclude(id=subcategory_id).exists():
            messages.error(request, 'Another SubCategory with this name already exists.')
            return redirect('admin_edit_subcategory', subcategory_id=subcategory_id)
        subcategory.sub_category_name = name
        subcategory.save()
        messages.success(request, f'SubCategory "{name}" updated successfully.')
        return redirect('admin_manage_subcategories', category_id=subcategory.category.id)
    return render(request, 'admin_panel/category/edit_subcategory.html', {'subcategory': subcategory, 'category': subcategory.category})

@user_passes_test(lambda u: u.is_superuser)
def admin_delete_subcategory(request, subcategory_id):
    subcategory = get_object_or_404(SubCategory, id=subcategory_id)
    category_id = subcategory.category.id
    if request.method == 'POST' or request.method == 'GET':
        subcategory.delete()
        messages.success(request, f'SubCategory "{subcategory.sub_category_name}" deleted successfully.')
        return redirect('admin_manage_subcategories', category_id=category_id)


# --- Manufacturer Management ---
@user_passes_test(lambda u: u.is_superuser)
def admin_manage_manufacturers(request):
    manufacturers = Manufacturer.objects.all()
    return render(request, 'admin_panel/product/manage_manufacturers.html', {'manufacturers': manufacturers})

@user_passes_test(lambda u: u.is_superuser)
def admin_add_manufacturer(request):
    if request.method == 'POST':
        name = request.POST.get('manufacturer_name').strip()
        if not name:
            messages.error(request, 'Manufacturer name is required.')
            return redirect('admin_add_manufacturer')
        if Manufacturer.objects.filter(manufacturer_name=name).exists():
            messages.error(request, 'Manufacturer with this name already exists.')
            return redirect('admin_add_manufacturer')
        Manufacturer.objects.create(manufacturer_name=name)
        messages.success(request, f'Manufacturer "{name}" added successfully.')
        return redirect('admin_manage_manufacturers')
    return render(request, 'admin_panel/product/edit_manufacturer.html', {'manufacturer': None})

@user_passes_test(lambda u: u.is_superuser)
def admin_edit_manufacturer(request, manufacturer_id):
    manufacturer = get_object_or_404(Manufacturer, id=manufacturer_id)
    if request.method == 'POST':
        name = request.POST.get('manufacturer_name').strip()
        if not name:
            messages.error(request, 'Manufacturer name is required.')
            return redirect('admin_edit_manufacturer', manufacturer_id=manufacturer_id)
        if Manufacturer.objects.filter(manufacturer_name=name).exclude(id=manufacturer_id).exists():
            messages.error(request, 'Another manufacturer with this name already exists.')
            return redirect('admin_edit_manufacturer', manufacturer_id=manufacturer_id)
        manufacturer.manufacturer_name = name
        manufacturer.save()
        messages.success(request, f'Manufacturer "{name}" updated successfully.')
        return redirect('admin_manage_manufacturers')
    return render(request, 'admin_panel/product/edit_manufacturer.html', {'manufacturer': manufacturer})

@user_passes_test(lambda u: u.is_superuser)
def admin_delete_manufacturer(request, manufacturer_id):
    manufacturer = get_object_or_404(Manufacturer, id=manufacturer_id)
    if request.method == 'POST' or request.method == 'GET':
        manufacturer.delete()
        messages.success(request, f'Manufacturer "{manufacturer.manufacturer_name}" deleted successfully.')
        return redirect('admin_manage_manufacturers')
    

# Admin Manage Orders
@user_passes_test(lambda u: u.is_superuser)
def admin_manage_orders(request):
    orders = Order.objects.all().order_by('-order_date')
    return render(request, 'admin_panel/order/manage_orders.html', {'orders': orders})

@user_passes_test(lambda u: u.is_superuser)
def admin_order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(Order.STATUS_CHOICES):
            order.status = new_status
            order.save()
            messages.success(request, f"Order status updated to {new_status}")
        else:
            messages.error(request, "Invalid status selected.")
        return redirect('admin_order_detail', order_id=order.id)

    context = {
        'order': order,
        'items': order.items.all(),
        'status_choices': Order.STATUS_CHOICES,
    }
    return render(request, 'admin_panel/order/order_detail.html', context)

@user_passes_test(lambda u: u.is_superuser)
def admin_delete_order(request, order_id):
    if request.method == 'POST':
        order = get_object_or_404(Order, id=order_id)
        order.delete()
        messages.success(request, f'Order #{order_id} deleted successfully.')
    return redirect('admin_manage_orders')


# Admin Site Settings
@user_passes_test(lambda u: u.is_superuser)
def admin_site_settings(request):
    site = Site.objects.first()  # Assuming only one site config object

    if request.method == 'POST':
        name = request.POST.get('name').strip()
        logo = request.FILES.get('logo')

        if not site:
            site = Site.objects.create(name=name)
        else:
            site.name = name
            if logo:
                site.logo = logo
            site.save()

        messages.success(request, "Site settings updated successfully.")
        return redirect('admin_site_settings')

    return render(request, 'admin_panel/site_settings.html', {'site': site})



# # Admin User Management
@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_manage_users(request):
    users = User.objects.all().select_related('userprofile')
    return render(request, 'admin_panel/user/user_list.html', {'users': users})


@login_required
@user_passes_test(lambda u: u.is_superuser)
def toggle_user_activation(request, user_id):
    user = get_object_or_404(User, id=user_id)

    if user == request.user:
        messages.warning(request, "You cannot deactivate your own account.")
        return redirect('admin_manage_users')

    profile, created = UserProfile.objects.get_or_create(user=user)

    new_status = not profile.is_active
    profile.is_active = new_status
    user.is_active = new_status  # Reflect this on Django auth system
    profile.save()
    user.save()

    messages.success(request, f"User '{user.username}' has been {'activated' if new_status else 'deactivated'}.")
    return redirect('admin_manage_users')


@login_required
@user_passes_test(lambda u: u.is_superuser)
def delete_user(request, user_id):
    user = get_object_or_404(User, id=user_id)

    if user == request.user:
        messages.warning(request, "You cannot delete your own account.")
        return redirect('admin_manage_users')

    if request.method == 'POST':
        username = user.username
        user.delete()
        messages.success(request, f"User '{username}' has been deleted.")
        return redirect('admin_manage_users')

    return render(request, 'admin_panel/user/user_confirm_delete.html', {'user': user})



# # # # # # # # # # # # # # # # # # #--------------------------------------------------------- # # # # # # # # # # # # # # # # # # #
#                                    ********************** ADMIN PANEL **********************                                     #
# # # # # # # # # # # # # # # # # # #--------------------------------------------------------- # # # # # # # # # # # # # # # # # # #