import re
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from .models import *
from django.contrib import messages
from django.db.models import Q
from django.utils.crypto import get_random_string
from django.utils import timezone
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings

def index(request):
    inventory = Inventory.objects.all()
    category = Category.objects.all()
    context = {
        'inventory': inventory,
        'categories': category
    }
    return render(request, "index.html", context)

def about(request):
    return render(request, 'about.html')

def category(request, pk):
    category = Category.objects.get(pk=pk)
    inventory = Inventory.objects.filter(product__category=category)
    context = {
        'inventory': inventory,
        'current_category': category,
    }
    return render(request, 'category.html', context)

def shop(request):
    inventory = Inventory.objects.all()
    context = {
        'inventory': inventory,
    }
    return render(request, 'shop.html', context)

def contact(request):
    return render(request, 'contact.html')

def order_complete(request):
    return render(request, 'order_complete.html')

def product(request, pk):
    inventory = Inventory.objects.get(pk=pk)
    context = {
        'inventory': inventory
    }
    return render(request, 'product_detail.html', context)


# --------- AUTHENTICATION AND AUTHORIZATION SECTION ---------

def is_password_strong(password):
    # Password constraint: at least 8 characters, containing at least one uppercase letter, one lowercase letter, one digit, and one special character
    if (
        len(password) < 8
        or not re.search(r"[A-Z]", password)
        or not re.search(r"[a-z]", password)
        or not re.search(r"\d", password)
    ):
        return False
    return True

def user_login(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request, username=email, password=password)
        if user is not None:
            login(request, user)
            if hasattr(user, 'customer'):  # Check if the user is a customer
                messages.success(request, 'Customer LogIn Success!')
                return redirect('dashboard')  # Redirect to customer dashboard
            elif hasattr(user, 'seller'):  # Check if the user is a seller
                messages.success(request, 'Seller LogIn Success!')
                return redirect('s_index')  # Redirect to seller dashboard
        else:
            messages.error(request, 'LogIn Failed! Please check your credentials.')
            return render(request, 'login.html')

    return render(request,'login.html')

def register(request):
    try:
        if request.method == 'POST':
            first_name = request.POST['fname']
            last_name = request.POST['lname']
            email = request.POST['email']
            phone = request.POST['phone']
            password = request.POST['password']
            confirm_password = request.POST['confirm_password']

            if password != confirm_password:
                messages.error(request, 'Passwords Do Not Match!')
                return render(request, 'register.html')

            if not is_password_strong(password):
                messages.error(request, 'Passwords Is Too Weak. Use at least 8 characters including uppercase and lowercase letters, digits, and special characters!')
                return render(request, 'register.html')

            user = User.objects.create_user(username=email,
                                            first_name=first_name,
                                            last_name=last_name,
                                            email=email,
                                            password=password)
            customer = Customer.objects.create(user=user, 
                                            first_name=first_name, 
                                            last_name=last_name,
                                            email=email, 
                                            phone=phone, 
                                            password=password)
            
            user = authenticate(username=email, password=password)
            login(request, user)
            messages.success(request, 'Your Account Has Been Registered Successfully!')
            return redirect('index')
    except:
        messages.error(request, 'Account Was Not Created! Try Again')
        return render(request, 'register.html')
    return render(request, 'register.html')

@login_required
def signout(request):
    logout(request)
    return redirect('/')

# --------- AUTHENTICATION AND AUTHORIZATION END ---------


# ---------------- USER SECTION ----------------

@login_required
def dashboard(request):
    customer = request.user.customer
    orders = OrderDetail.objects.filter(order__customer=customer)
    context = {
        'customer': customer,
        'orders': orders
    }
    return render(request, "dashboard.html", context)

@login_required
def edit_profile(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        address = request.POST.get('address')
        customer = request.user.customer
        customer.first_name = first_name
        customer.last_name = last_name
        customer.email = email
        customer.phone = phone
        customer.address = address
        customer.save()
        messages.success(request, 'Profile updated successfully!')
    return redirect('dashboard')

@login_required
def change_password(request):
    if request.method == 'POST':
        old_password = request.POST.get('oldPassword')
        new_password = request.POST.get('newPassword')

        # Check if the new password meets the strength requirements
        if not is_password_strong(new_password):
            messages.error(request, 'Passwords Is Too Weak. Use at least 8 characters including uppercase and lowercase letters, digits, and special characters!')
            return redirect('dashboard')

        customer = request.user.customer
        if customer.password == old_password:
            customer.password = new_password 
            customer.save()
            messages.success(request, 'Password changed successfully!')
        else:
            messages.error(request, 'Old password is incorrect. Please try again.')
    return redirect('dashboard')

class CustomTokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        return (
            str(user.pk) + user.password + str(timestamp)
        )

def forgot_password(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            user = User.objects.get(email=email)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = CustomTokenGenerator().make_token(user)
            reset_password_url = request.build_absolute_uri('/reset_password/{}/{}/'.format(uid, token))
            email_subject = 'Reset Your Password'

            # Render both HTML and plain text versions of the email
            email_body_html = render_to_string('reset_password_email.html', {
                'reset_password_url': reset_password_url,
                'user': user,
            })
            email_body_text = "Click the following link to reset your password: {}".format(reset_password_url)

            # Create an EmailMultiAlternatives object to send both HTML and plain text versions
            email = EmailMultiAlternatives(
                email_subject,
                email_body_text,
                settings.EMAIL_HOST_USER,
                [email],
            )
            email.attach_alternative(email_body_html, 'text/html')  # Attach HTML version
            email.send(fail_silently=False)

            messages.success(request, 'An email has been sent to your email address with instructions on how to reset your password.')
            return redirect('login')
        except User.DoesNotExist:
            messages.error(request, "User with this email does not exist.")
    return render(request, 'forgot_password.html')

def reset_password(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
        customer = Customer.objects.get(user=user)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and CustomTokenGenerator().check_token(user, token):
        if request.method == 'POST':
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')

            if not is_password_strong(new_password):
                messages.error(request, 'Passwords Is Too Weak. Use at least 8 characters including uppercase and lowercase letters, digits, and special characters!')
                return render(request, 'reset_password.html')
            
            if new_password == confirm_password:
                customer.password = new_password
                user.set_password(new_password)
                user.save()
                customer.save()
                messages.success(request, "Password reset successfully. You can now login with your new password.")
                return redirect('login')
            else:
                messages.error(request, "Passwords do not match.")
        return render(request, 'reset_password.html')
    else:
        messages.error(request, "Invalid reset link. Please try again or request a new reset link.")
        return redirect('login')
 
# ---------------- USER END ----------------   


# ---------------- WISHLIST SECTION ----------------

@login_required
def wishlist(request):
    customer = request.user.customer
    wishlist = Wishlist.objects.filter(customer=customer)
    inventory = Inventory.objects.all()
    context = {
        'wishlist': wishlist,
        'inventory': inventory,
        }
    return render(request, 'wishlist.html', context)

@login_required
def add_to_wishlist(request, pk):
    try:
        inventory = Inventory.objects.get(pk=pk)
        product = inventory.product
        customer = request.user.customer
        wishlist, created = Wishlist.objects.get_or_create(customer=customer, product=product)
        wishlist.save()
        if created:
            messages.success(request, f'Item added to wishlist.')
        else:
            messages.success(request, f'Item already in wishlist.')
        return redirect('wishlist')
    except:
        messages.error(request, 'You Must Sign In to Add Items To Wishlist.')
        return redirect('login')

@login_required
def delete_item_in_wishlist(request, pk):
    customer = request.user.customer
    inventory = get_object_or_404(Inventory, pk=pk)
    product = inventory.product
    wishlist = Wishlist.objects.get(customer=customer, product=product)
    wishlist.delete()
    return redirect('wishlist')

# ---------------- WISHLIST END ----------------


# ---------------- CART SECTION ----------------

@login_required
def cart(request):
    customer = request.user.customer
    cart_items = Cart.objects.filter(customer=customer)
    inventory = Inventory.objects.all()
    total_price = sum(item.product.retail_price * item.quantity for item in cart_items)
    context = {
    'cart_items': cart_items,
    'inventory': inventory,
    'total_price': total_price,
    }

    return render(request, 'cart.html', context)

@login_required
def add_to_cart(request):
    try:
        if request.method == 'POST':
            inventory_id = request.POST.get('inventory_id')
            quantity = request.POST.get('quantity')
            print(inventory_id)
            print(quantity)

            if inventory_id and quantity:
                try:
                    inventory = Inventory.objects.get(pk=inventory_id)
                    product = inventory.product
                    customer = request.user.customer
                    cart_item, created = Cart.objects.get_or_create(customer=customer, product=product)
                    cart_item.quantity += int(quantity)
                    cart_item.save()
                    messages.success(request, f'{quantity} item(s) added to cart.')
                except Product.DoesNotExist:
                    messages.error(request, 'Product does not exist.')
            else:
                messages.error(request, 'Invalid request.')

        return redirect('cart')
    except:
        messages.error(request, 'You Must Sign In to Add Items To Cart.')
        return redirect('login')

@login_required
def remove_from_cart(request):
    if request.method == 'POST':
        inventory_id = request.POST.get('inventory_id')
        if inventory_id:
            try:
                inventory = Inventory.objects.get(pk=inventory_id)
                product = inventory.product
                customer = request.user.customer
                cart_item = Cart.objects.get(customer=customer, product=product)
                if cart_item.quantity > 1:
                    cart_item.quantity -= 1
                    cart_item.save()
                else:
                    cart_item.delete()
            except Product.DoesNotExist:
                messages.error(request, 'Product does not exist.')
        else:
            messages.error(request, 'Invalid request.')

    return redirect('cart')

@login_required
def delete_item_in_cart(request, id):
    customer = request.user.customer
    inventory = get_object_or_404(Inventory, pk=id)
    product = inventory.product
    cart_item = Cart.objects.get(customer=customer, product=product)
    cart_item.delete()
    return redirect('cart')

# ---------------- CART END ----------------


# ------------------- ORDER SECTION --------------------

@login_required
def checkout(request):
    customer = request.user.customer
    cart_items = Cart.objects.filter(customer=customer)
    total_price = sum(item.product.retail_price * item.quantity for item in cart_items)
    if request.method == 'POST':
        total_price = request.POST.get('total_price')
    return render(request, "checkout.html", {'customer': customer,'cart_items': cart_items, 'total_price': total_price, 'STRIPE_PUBLIC_KEY': settings.STRIPE_PUBLIC_KEY})

def generate_transaction_id(payment_method):
    if payment_method == 'Cash On Delivery':
        timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
        random_string = get_random_string(length=6)
        transaction_id = f'COD-{timestamp}-{random_string}'
        return transaction_id
    else:
        return None

@login_required
def place_order(request):
    try:
        if request.method == 'POST':
            payment_method = request.POST.get('payment')
            address = request.POST.get('address')
            if len(address) > 5:
                customer = request.user.customer
                cart_items = Cart.objects.filter(customer=customer)
                total = sum(item.product.retail_price * item.quantity for item in cart_items)
                order = Order.objects.create(customer=customer, delivery_address=address, total_amount=total)
                
                # payment_method = 'Cash On Delivery'
                transaction_id = generate_transaction_id(payment_method)
                payment = Payment.objects.create(transaction_id=transaction_id, order=order, amount=total, payment_method=payment_method)
                
                for cart_item in cart_items:
                    item = Inventory.objects.get(product=cart_item.product)
                    if cart_item.quantity <= item.quantity_in_stock:
                        OrderDetail.objects.create(order=order, product=cart_item.product, quantity=cart_item.quantity, price=cart_item.product.retail_price)
                        item.quantity_in_stock -= cart_item.quantity
                        item.save()
                        cart_item.product.save()
                cart_items.delete()
                # order_confirmation(customer.email, )
                messages.success(request, 'Your Order Has Been Placed!')
            else:
                messages.error(request, 'Invalid Address')
                return redirect('checkout')
        return redirect('order_complete')
    except Exception as e:
        messages.error(request, f'Sorry! Your Order Was Not Placed: {e}')
        return redirect('cart')

@login_required
def order_details(request, pk):
    customer = request.user.customer
    order = OrderDetail.objects.get(pk=pk)
    subtotal = order.price * order.quantity
    context = {
        'customer': customer,
        'order': order,
        'subtotal': subtotal,
    }
    return render(request, "order_detail.html", context)

# ------------------- ORDER END --------------------











